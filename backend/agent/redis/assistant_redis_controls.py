from typing import Optional

from redis.asyncio import Redis

from agent.config.agent_constants import AgentConstants


def _cooldown_key(meeting_id: str) -> str:
    return f"{AgentConstants.ASSISTANT_COOLDOWN_KEY_PREFIX}{meeting_id}"


def _last_question_key(meeting_id: str) -> str:
    return f"{AgentConstants.ASSISTANT_LAST_QUESTION_KEY_PREFIX}{meeting_id}"


async def is_cooldown_active(redis: Optional[Redis], meeting_id: str) -> bool:
    if redis is None:
        return False
    try:
        value = await redis.get(_cooldown_key(meeting_id))
        return value is not None and value != ""
    except Exception:
        return False


async def set_cooldown_after_response(redis: Optional[Redis], meeting_id: str) -> None:
    if redis is None:
        return
    try:
        await redis.set(
            _cooldown_key(meeting_id),
            "1",
            ex=AgentConstants.ASSISTANT_COOLDOWN_SECONDS,
        )
    except Exception:
        pass


async def should_skip_duplicate_question(
    redis: Optional[Redis],
    meeting_id: str,
    normalized: str,
) -> bool:
    if redis is None or not normalized:
        return False
    try:
        prev = await redis.get(_last_question_key(meeting_id))
        return prev == normalized
    except Exception:
        return False


async def remember_last_question(
    redis: Optional[Redis],
    meeting_id: str,
    normalized: str,
) -> None:
    if redis is None or not normalized:
        return
    try:
        await redis.set(
            _last_question_key(meeting_id),
            normalized,
            ex=AgentConstants.ASSISTANT_LAST_QUESTION_TTL_SECONDS,
        )
    except Exception:
        pass
