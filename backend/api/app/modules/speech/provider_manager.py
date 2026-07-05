import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set
from redis.asyncio import Redis

from app.state.client import get_redis
from app.modules.speech.registry import ProviderRegistry, ProviderRegistryEntry
from app.modules.speech.providers import BaseSpeechProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """Singleton manager responsible for session-scoped speech provider allocation,

    hybrid state caching, dynamic failover, least-active load balancing, and async recovery.
    """

    _instance: Optional["ProviderManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Prevent re-initialization if already initialized
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.registry = ProviderRegistry()
        self._session_affinity: Dict[str, str] = {}
        self._local_lock = asyncio.Lock()

        # In-memory provider state caches (complemented by Redis)
        self._cooldown_expiry: Dict[str, float] = {}
        self._quota_exhausted: Set[str] = set()
        self._last_failure_time: Dict[str, float] = {}
        self._consecutive_failures: Dict[str, int] = {}
        self._active_sessions: Dict[str, int] = {}

        # Metric counters (abstractions to be integrated with Prometheus later)
        self._metrics = {
            "provider_selections": {},
            "active_sessions": {},
            "failovers": 0,
            "provider_latency": {},
            "provider_errors": {},
            "cooldown_count": {},
            "recovery_count": {},
        }

        self._health_check_task: Optional[asyncio.Task] = None
        self._initialized = True

    async def initialize(self) -> None:
        """Initializes dependencies and synchronizes state with Redis on startup."""
        redis = await get_redis()
        # Synchronize active session counts from Redis into local cache
        for entry in self.registry.get_entries():
            key = f"speech:provider:active_sessions:{entry.name}"
            val = await redis.get(key)
            self._active_sessions[entry.name] = int(val) if val else 0

    def start_cooldown_scheduler(self) -> None:
        """Starts the background asynchronous recovery task (typically invoked by the main server loop)."""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._run_cooldown_recovery_scheduler())
            logger.info("Asynchronous cooldown recovery scheduler started.")

    async def stop_cooldown_scheduler(self) -> None:
        """Stops the background asynchronous recovery task cleanly."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Asynchronous cooldown recovery scheduler stopped.")

    async def get_metrics(self) -> Dict[str, Any]:
        """Exposes raw metrics for external monitoring integrations."""
        async with self._local_lock:
            # Sync active session counts to metrics
            self._metrics["active_sessions"] = dict(self._active_sessions)
            return dict(self._metrics)

    async def allocate_provider(self, session_id: str) -> BaseSpeechProvider:
        """Allocates the highest-priority healthy provider for the session using least-active load balancing."""
        async with self._local_lock:
            redis = await get_redis()
            entries = self.registry.get_entries()

            # Filter candidates by health status, enabling dynamic load balancing
            candidates: List[ProviderRegistryEntry] = []
            for entry in entries:
                if not entry.enabled:
                    continue

                # Check if cooling down or quota exhausted
                is_on_cooldown = await self._is_cooling_down(redis, entry.name)
                is_quota_hit = entry.name in self._quota_exhausted

                if not is_on_cooldown and not is_quota_hit:
                    candidates.append(entry)

            if not candidates:
                # Emergency fallback: Allocate GetStream (the final net)
                fallback_entry = self.registry.get_entry("GetStream")
                if not fallback_entry:
                    raise RuntimeError("Emergency fallback GetStream provider configuration missing in registry")
                allocated_entry = fallback_entry
            else:
                # Group candidate providers by implementation class to balance among keys of same type (e.g. Deepgram1/2/3)
                best_candidate = candidates[0]
                same_class_candidates = [
                    c for c in candidates if c.provider_class_name == best_candidate.provider_class_name
                ]

                if len(same_class_candidates) > 1:
                    # Select the candidate with the least active sessions (least-active load balancing)
                    least_active_entry = same_class_candidates[0]
                    min_sessions = float("inf")
                    for c in same_class_candidates:
                        # Query active sessions globally from Redis (with local fallback)
                        redis_sessions_val = await redis.get(f"speech:provider:active_sessions:{c.name}")
                        sessions = int(redis_sessions_val) if redis_sessions_val else self._active_sessions.get(c.name, 0)
                        if sessions < min_sessions:
                            min_sessions = sessions
                            least_active_entry = c
                    allocated_entry = least_active_entry
                else:
                    allocated_entry = best_candidate

            # Instantiate and map affinity
            provider = self.registry.create_provider_instance(allocated_entry.name)
            if not provider:
                raise RuntimeError(f"Failed to instantiate provider: {allocated_entry.name}")

            # Store affinity locally and globally in Redis
            self._session_affinity[session_id] = allocated_entry.name
            await redis.set(f"speech:session:allocation:{session_id}", allocated_entry.name, ex=28800)  # 8 hours TTL

            # Increment active session counters
            await redis.incr(f"speech:provider:active_sessions:{allocated_entry.name}")
            self._active_sessions[allocated_entry.name] = self._active_sessions.get(allocated_entry.name, 0) + 1

            # Update metrics
            self._metrics["provider_selections"][allocated_entry.name] = (
                self._metrics["provider_selections"].get(allocated_entry.name, 0) + 1
            )

            logger.info("Allocated provider %s for session %s", allocated_entry.name, session_id)
            return provider

    async def get_provider(self, session_id: str) -> BaseSpeechProvider:
        """Retrieves the currently allocated provider for the session, or allocates a new one if not mapped."""
        async with self._local_lock:
            redis = await get_redis()
            provider_name = self._session_affinity.get(session_id)

            if not provider_name:
                # Sync check with Redis for session affinity mapping
                redis_name = await redis.get(f"speech:session:allocation:{session_id}")
                if redis_name:
                    provider_name = redis_name
                    self._session_affinity[session_id] = provider_name

            if provider_name:
                provider = self.registry.create_provider_instance(provider_name)
                if provider:
                    return provider

        # Fallback to fresh allocation if no affinity exists
        return await self.allocate_provider(session_id)

    async def fail_provider(self, session_id: str) -> BaseSpeechProvider:
        """Handles provider failure by putting the active provider on cooldown and performing session failover."""
        async with self._local_lock:
            redis = await get_redis()
            failed_name = self._session_affinity.get(session_id)

            if not failed_name:
                redis_name = await redis.get(f"speech:session:allocation:{session_id}")
                failed_name = redis_name

            if failed_name:
                logger.warning("Failing provider %s for session %s", failed_name, session_id)
                entry = self.registry.get_entry(failed_name)
                cooldown_seconds = entry.cooldown_seconds if entry else 300

                # Decrement active sessions counter
                await redis.decr(f"speech:provider:active_sessions:{failed_name}")
                self._active_sessions[failed_name] = max(0, self._active_sessions.get(failed_name, 0) - 1)

                # Set cooldown flag locally and in Redis
                self._cooldown_expiry[failed_name] = time.time() + cooldown_seconds
                await redis.set(f"speech:provider:cooldown:{failed_name}", "1", ex=cooldown_seconds)

                # Update state metadata
                self._last_failure_time[failed_name] = time.time()
                self._consecutive_failures[failed_name] = self._consecutive_failures.get(failed_name, 0) + 1

                # Update metrics
                self._metrics["failovers"] += 1
                self._metrics["cooldown_count"][failed_name] = (
                    self._metrics["cooldown_count"].get(failed_name, 0) + 1
                )
                self._metrics["provider_errors"][failed_name] = (
                    self._metrics["provider_errors"].get(failed_name, 0) + 1
                )

                # Clear session affinity maps
                self._session_affinity.pop(session_id, None)
                await redis.delete(f"speech:session:allocation:{session_id}")

        # Trigger re-allocation (guarantees session affinity failover)
        return await self.allocate_provider(session_id)

    async def release_provider(self, session_id: str) -> None:
        """Releases the session allocation affinity cleanly, decrementing active counters."""
        async with self._local_lock:
            redis = await get_redis()
            name = self._session_affinity.pop(session_id, None)
            if not name:
                redis_name = await redis.get(f"speech:session:allocation:{session_id}")
                name = redis_name

            if name:
                await redis.decr(f"speech:provider:active_sessions:{name}")
                self._active_sessions[name] = max(0, self._active_sessions.get(name, 0) - 1)
                await redis.delete(f"speech:session:allocation:{session_id}")
                logger.info("Released provider affinity %s for session %s", name, session_id)

    async def _is_cooling_down(self, redis: Redis, name: str) -> bool:
        # Check local cache first
        now = time.time()
        expiry = self._cooldown_expiry.get(name, 0)
        if expiry > now:
            return True

        # Fallback sync check to Redis
        redis_cooldown = await redis.get(f"speech:provider:cooldown:{name}")
        if redis_cooldown:
            # Sync back to local in-memory cache
            self._cooldown_expiry[name] = now + 10  # temporary buffer
            return True

        return False

    async def _run_cooldown_recovery_scheduler(self) -> None:
        """Asynchronous background loop checking cooling down providers and running circuit-breaker recovery pings."""
        while True:
            try:
                await asyncio.sleep(5)  # poll recovery status every 5 seconds
                redis = await get_redis()
                entries = self.registry.get_entries()

                for entry in entries:
                    if not entry.enabled or entry.name == "GetStream":
                        continue

                    # Check if cooldown is finished locally/globally
                    now = time.time()
                    expiry = self._cooldown_expiry.get(entry.name, 0)
                    redis_cooldown = await redis.get(f"speech:provider:cooldown:{entry.name}")

                    if expiry <= now and not redis_cooldown:
                        # Check if it was previously cooling down
                        if entry.name in self._cooldown_expiry or entry.name in self._quota_exhausted:
                            # Run asynchronous non-blocking circuit-breaker recovery health check
                            passed = await self._ping_provider(entry.name)
                            async with self._local_lock:
                                if passed:
                                    # Clear cooldown/quota status
                                    self._cooldown_expiry.pop(entry.name, None)
                                    self._quota_exhausted.discard(entry.name)
                                    self._consecutive_failures[entry.name] = 0
                                    self._metrics["recovery_count"][entry.name] = (
                                        self._metrics["recovery_count"].get(entry.name, 0) + 1
                                    )
                                    logger.info("Provider %s successfully recovered and marked HEALTHY", entry.name)
                                else:
                                    # Renew cooldown if health check fails
                                    cooldown_seconds = entry.cooldown_seconds
                                    self._cooldown_expiry[entry.name] = time.time() + cooldown_seconds
                                    await redis.set(f"speech:provider:cooldown:{entry.name}", "1", ex=cooldown_seconds)
                                    logger.warning("Provider %s failed recovery health check, cooldown renewed.", entry.name)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in cooldown recovery scheduler loop")

    async def _ping_provider(self, name: str) -> bool:
        """Simulated non-blocking ping verification for Phase 3 unit testing."""
        # Check if config API key exists
        entry = self.registry.get_entry(name)
        if not entry or not entry.enabled:
            return False
        # Simulating non-blocking ping delay
        await asyncio.sleep(0.01)
        return True
