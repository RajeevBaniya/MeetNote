import json
import logging
import asyncio
from typing import Any, List, Optional

from redis.asyncio import Redis

from agent.config.agent_constants import AgentConstants
from agent.config.env_loader import GEMINI_API_KEY
from agent.core.assistant_context import fetch_summary_chunks_text
from agent.core.assistant_http_mixin import AssistantHttpMixin
from agent.core.assistant_intent_mixin import AssistantIntentMixin
from agent.core.transcript_types import TranscriptEntry
from agent.core.gemini_client import GeminiClient
from agent.redis.assistant_redis_controls import (
    is_cooldown_active,
    remember_last_question,
    should_skip_duplicate_question,
)
from agent.utils.question_normalization import normalize_question_text

logger = logging.getLogger(__name__)



class AssistantCore(AssistantHttpMixin, AssistantIntentMixin):
    def __init__(
        self,
        meeting_id: str,
        api_base_url: str,
        redis: Optional[Redis] = None,
    ) -> None:
        self.meeting_id = meeting_id
        self.api_base_url = api_base_url.rstrip("/")
        self.redis = redis

        self.transcript: List[TranscriptEntry] = []
        self.is_active: bool = False
        self.pending_question: Optional[str] = None
        self.assistant_active: bool = False
        self._token: Optional[str] = None
        self.host_db_id: Optional[str] = None

    async def reload_host_id(self) -> Optional[str]:
        redis_key = f"meeting:host_id:{self.meeting_id}"
        if self.redis:
            try:
                cached_host = await self.redis.get(redis_key)
                if cached_host:
                    self.host_db_id = str(cached_host)
                    return self.host_db_id
            except Exception as exc:
                logger.warning("Redis host_id cache read failed: %s", exc)

        try:
            db_host = await self.get_host_id_from_db()
            if db_host:
                self.host_db_id = db_host
                if self.redis:
                    try:
                        await self.redis.set(redis_key, db_host)
                    except Exception as exc:
                        logger.warning("Failed to repopulate Redis host_id cache: %s", exc)
                return db_host
        except Exception as exc:
            logger.error("Failed to reload host_id from DB: %s", exc)

        return None

    def set_call_active(self, active: bool) -> None:
        self.is_active = active

    async def is_assistant_enabled(self) -> bool:
        if self.redis is None:
            return True

        try:
            key = f"{AgentConstants.ASSISTANT_ENABLED_KEY_PREFIX}{self.meeting_id}"
            value = await self.redis.get(key)
            return bool(value != "0")
        except Exception as exc:
            logger.debug(
                "Redis assistant-enabled check failed for meeting_id=%s: %s",
                self.meeting_id,
                exc,
                exc_info=True,
            )
            return True

    async def handle_transcript(
        self,
        speaker: str,
        text: str,
        timestamp: Optional[Any] = None,
    ) -> None:
        if not await self.is_assistant_enabled():
            logger.info(
                "Assistant disabled for meeting %s, skipping transcript",
                self.meeting_id,
            )
            return

        cleaned_text = self._validate_and_clean_text(text)
        if not cleaned_text:
            return

        speaker_id = speaker or "unknown"

        if self._is_assistant_speaker(speaker_id):
            logger.debug("Ignoring assistant's own message")
            return

        self._append_to_transcript(speaker_id, cleaned_text, timestamp)
        logger.info("transcript_received speaker_id=%s", speaker_id)
        logger.debug("transcript_text speaker_id=%s text=%s", speaker_id, cleaned_text)

        transcript_lower = cleaned_text.lower().strip()

        if await self._handle_pending_question_response(transcript_lower, speaker_id):
            return

        if await self._handle_deactivation(transcript_lower):
            return

        question = await self._handle_activation(transcript_lower, cleaned_text)

        if not self.assistant_active:
            return

        if question and len(question) >= AgentConstants.MIN_QUESTION_LENGTH:
            await self._process_question(question)

    def _validate_and_clean_text(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""

        cleaned = text.strip()
        if len(cleaned) == 0:
            return ""

        return cleaned

    def _is_assistant_speaker(self, speaker_id: str) -> bool:
        return speaker_id in (
            AgentConstants.SYSTEM_USER_ID,
            AgentConstants.SYSTEM_DISPLAY_NAME,
        )

    def _append_to_transcript(
        self,
        speaker: str,
        text: str,
        timestamp: Optional[Any],
    ) -> None:
        entry = TranscriptEntry(
            speaker=speaker,
            text=text,
            timestamp=timestamp,
        )
        self.transcript.append(entry)

    async def _fetch_recent_transcript_context(self) -> tuple[str, list[dict]]:
        if not self.redis:
            return "", []
        try:
            segments_key = f"transcript:segments:{self.meeting_id}"
            raw_segments = await self.redis.lrange(segments_key, -AgentConstants.ASSISTANT_CONTEXT_TRANSCRIPT_SEGMENTS, -1)
            if not raw_segments:
                return "", []

            corrected_key = f"transcript:corrected_segments:{self.meeting_id}"
            raw_corrections = await self.redis.hgetall(corrected_key) or {}
            
            corrections = {}
            for k, v in raw_corrections.items():
                key_str = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                val_str = v.decode("utf-8") if isinstance(v, bytes) else str(v)
                corrections[key_str] = val_str

            lines = []
            valid_segments = []
            for raw in raw_segments:
                try:
                    data = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode("utf-8"))
                except Exception:
                    continue
                seg_id = data.get("segment_id")
                speaker = data.get("speaker_name") or data.get("speaker_id") or "Speaker"
                
                text = corrections.get(str(seg_id)) if seg_id else None
                if not text:
                    text = data.get("text") or ""
                
                if text.strip():
                    lines.append(f"{speaker}: {text.strip()}")
                    data["resolved_text"] = text.strip()
                    valid_segments.append(data)
            return "\n".join(lines), valid_segments
        except Exception as exc:
            logger.warning("Failed to fetch recent transcript context: %s", exc)
            return "", []

    async def _process_question(self, question: str) -> None:
        logger.info(
            "Processing question for meeting %s: %s",
            self.meeting_id,
            question[:100],
        )

        if await is_cooldown_active(self.redis, self.meeting_id):
            logger.debug("Assistant cooldown active, ignoring question trigger")
            return

        normalized = normalize_question_text(question)
        if await should_skip_duplicate_question(self.redis, self.meeting_id, normalized):
            logger.debug("Duplicate question ignored for meeting %s", self.meeting_id)
            return

        try:
            transcript_history, retrieved_segments = await self._fetch_recent_transcript_context()
            if not transcript_history or len(transcript_history) < AgentConstants.MIN_TRANSCRIPT_LENGTH:
                self.pending_question = None
                ok = await self._send_with_cooldown(
                    "There is not enough meeting history yet to answer that."
                )
                if ok and normalized:
                    await remember_last_question(
                        self.redis, self.meeting_id, normalized
                    )
                return

            ext_approved = False
            if self.redis:
                try:
                    val = await self.redis.get(f"assistant:ext_approved:{self.meeting_id}")
                    ext_approved = val == "1"
                except Exception as exc:
                    logger.warning("Failed to check ext_approved in Redis: %s", exc)

            reply = await self._build_reply_async(question, external_approved=ext_approved)
            
            if not ext_approved and reply.strip() == "[EXTERNAL_KNOWLEDGE_REQUIRED]":
                if self.redis:
                    try:
                        await self.redis.set(f"assistant:pending_q:{self.meeting_id}", question, ex=300)
                    except Exception as exc:
                        logger.warning("Failed to set pending_q in Redis: %s", exc)
                self.pending_question = question
                prompt_msg = "Answering this question requires external knowledge. Would you like me to use external knowledge? (Yes/No)"
                await self._send_with_cooldown(prompt_msg)
                logger.info("ext_knowledge_requested meeting_id=%s", self.meeting_id)
                return

            ok = await self._send_with_cooldown(reply)
            if ok and normalized:
                await remember_last_question(self.redis, self.meeting_id, normalized)
            elif not ok:
                await self._send_with_cooldown(AgentConstants.FALLBACK_REPLY_MESSAGE)
        except Exception:
            logger.exception("Assistant response failed for meeting %s", self.meeting_id)
            try:
                await self._send_with_cooldown(AgentConstants.FALLBACK_REPLY_MESSAGE)
            except Exception:
                pass

    def _has_sufficient_context(self) -> bool:
        return True

    async def _build_reply_async(self, question: str, external_approved: bool = False) -> str:
        api_key = GEMINI_API_KEY
        if not api_key:
            logger.error("GEMINI_API_KEY env variable is not set")
            return "Assistant is temporarily unavailable."

        try:
            chunks_text = await fetch_summary_chunks_text(self.redis, self.meeting_id)
            transcript_history, retrieved_segments = await self._fetch_recent_transcript_context()

            # Format chunks with segment_id headers explicitly
            formatted_transcript_parts = []
            for seg in retrieved_segments:
                seg_id = seg.get("segment_id")
                speaker = seg.get("speaker_name") or seg.get("speaker_id") or "Speaker"
                text = seg.get("resolved_text") or ""
                formatted_transcript_parts.append(
                    f'[CHUNK chunk_id="{seg_id}" speaker="{speaker}"]\n"{text}"'
                )
            formatted_transcript = "\n\n".join(formatted_transcript_parts)

            # Load prompts from text files
            from pathlib import Path
            prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
            if external_approved:
                prompt_file = prompts_dir / "assistant_external_allowed.txt"
            else:
                prompt_file = prompts_dir / "assistant_context_only.txt"

            if not prompt_file.exists():
                raise FileNotFoundError(f"Required prompt file not found: {prompt_file}")
            prompt_template = prompt_file.read_text(encoding="utf-8")

            prompt = prompt_template.format(
                summary_chunks=chunks_text or "No summary chunks available yet.",
                recent_transcript=formatted_transcript or "No transcript history available yet.",
                question=question
            )

            client = GeminiClient(api_key, AgentConstants.GEMINI_MODEL_NAME)
            reply = await client.generate_content(
                prompt=prompt,
                max_tokens=400,
                temperature=0.0,
                timeout=AgentConstants.AGENT_REPLY_TIMEOUT_SECONDS,
            )

            # CITATION VALIDATION
            valid_chunk_ids = {str(seg.get("segment_id")) for seg in retrieved_segments if seg.get("segment_id")}
            
            import re
            citation_pattern = re.compile(r'\[([a-zA-Z0-9-]+)\]')
            citations_found = citation_pattern.findall(reply)
            
            # Reject any chunk_id not present in context set
            valid_citations = [c for c in citations_found if c in valid_chunk_ids]
            unique_valid = list(dict.fromkeys(valid_citations))
            
            citation_mapping = {chunk_id: idx + 1 for idx, chunk_id in enumerate(unique_valid)}
            
            def replace_citation(match: re.Match) -> str:
                cid = match.group(1)
                if cid in citation_mapping:
                    return f"[{citation_mapping[cid]}]"
                return ""  # Strip unsupplied citation
                
            validated_reply = citation_pattern.sub(replace_citation, reply)
            return validated_reply

        except asyncio.TimeoutError:
            logger.error("Gemini API request timed out for meeting %s", self.meeting_id)
            return "Assistant is temporarily unavailable."
        except Exception:
            logger.exception("Gemini API request failed for meeting %s", self.meeting_id)
            return "Assistant is temporarily unavailable."

