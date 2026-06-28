import logging
import time
from dataclasses import dataclass
from uuid import UUID

from app.core.config import (
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_MODEL_NAME,
    MAX_TRANSCRIPT_CHUNKS_PER_QUERY,
    MAX_SUMMARY_CHUNKS_PER_QUERY,
    TRANSCRIPT_NEIGHBOR_WINDOW,
    MAX_EXPANDED_TRANSCRIPT_SEGMENTS,
)
from app.core.gemini_client import GeminiClient
from app.core.metrics import incr
from app.modules.meeting_chat.constants import (
    CHAT_MODE_INACTIVE,
    CHAT_MODE_TRANSCRIPT_AND_SUMMARY,
    CHAT_MODE_TRANSCRIPT_ONLY,
    CHAT_MODE_SUMMARY_ONLY,
    METRIC_CHAT_DURATION_MS_TOTAL,
    METRIC_CHAT_FAILURES_TOTAL,
    METRIC_CHAT_FALLBACK_TOTAL,
    METRIC_CHAT_REQUESTS_TOTAL,
    RESPONSE_MODE_HYBRID,
    RESPONSE_MODE_SUMMARY,
    RESPONSE_MODE_TRANSCRIPT,
    RESPONSE_MODE_UNAVAILABLE,
)
from app.modules.meeting_chat.exceptions import (
    MeetingChatPermissionError,
    MeetingChatNotFoundError,
    MeetingChatUnavailableError,
)
from app.modules.meeting_chat.llm_gateway import llm_gateway as default_llm_gateway
from app.modules.meeting_chat.prompts import get_system_prompt
from app.modules.meeting_chat.repository import MeetingChatRepositoryInterface

logger = logging.getLogger(__name__)

PROMPT_HISTORY_LIMIT = 20


@dataclass
class ChatResult:
    response: str
    response_mode: str
    transcript_chunks_used: int
    summary_chunks_used: int


def _derive_response_mode(
    transcript_chunks_used: int,
    summary_chunks_used: int,
) -> str:
    if transcript_chunks_used > 0 and summary_chunks_used > 0:
        return RESPONSE_MODE_HYBRID
    if transcript_chunks_used > 0:
        return RESPONSE_MODE_TRANSCRIPT
    if summary_chunks_used > 0:
        return RESPONSE_MODE_SUMMARY
    return RESPONSE_MODE_UNAVAILABLE


class MeetingChatService:
    def __init__(
        self,
        repository: MeetingChatRepositoryInterface,
        llm_gateway=default_llm_gateway,
    ) -> None:
        self.repository = repository
        self.llm_gateway = llm_gateway

    async def get_chat_status(self, meeting_id: UUID, user_id: UUID) -> dict[str, object]:
        """Check if AI Chat is available for the meeting and return capabilities."""
        if not await self.repository.check_user_membership(meeting_id, user_id):
            raise MeetingChatPermissionError("Not authorized to access this meeting chat")

        meeting = await self.repository.get_meeting(meeting_id)
        if not meeting:
            raise MeetingChatNotFoundError("Meeting not found")

        has_transcript = await self.repository.has_transcript_records(meeting_id)
        transcript_ready = await self.repository.has_transcript_chunks(meeting_id)
        has_summary = await self.repository.has_summary_chunks(meeting_id)
        summary_ready = has_summary

        if meeting.is_active:
            chat_mode = CHAT_MODE_INACTIVE
            is_available = False
        else:
            if transcript_ready and summary_ready:
                chat_mode = CHAT_MODE_TRANSCRIPT_AND_SUMMARY
            elif transcript_ready:
                chat_mode = CHAT_MODE_TRANSCRIPT_ONLY
            elif summary_ready:
                chat_mode = CHAT_MODE_SUMMARY_ONLY
            else:
                chat_mode = CHAT_MODE_INACTIVE
            is_available = chat_mode != CHAT_MODE_INACTIVE

        return {
            "is_available": is_available,
            "has_transcript": has_transcript,
            "has_summary": has_summary,
            "transcript_ready": transcript_ready,
            "summary_ready": summary_ready,
            "chat_mode": chat_mode,
        }

    async def get_chat_history(self, meeting_id: UUID, user_id: UUID) -> list[dict[str, str]]:
        """Fetch chat history for the user and meeting, returning role and content."""
        status = await self.get_chat_status(meeting_id, user_id)
        if not status["is_available"]:
            raise MeetingChatUnavailableError("AI Chat is not available for this meeting")
        messages = await self.repository.get_chat_history(meeting_id, user_id)
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def get_chat_response(
        self,
        meeting_id: UUID,
        user_id: UUID,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatResult:
        """Embeds the query, retrieves RAG context, and requests a response from the LLM."""
        status = await self.get_chat_status(meeting_id, user_id)
        if not status["is_available"]:
            raise MeetingChatUnavailableError("AI Chat is not available for this meeting")

        request_start = time.monotonic()
        provider_used = self.llm_gateway.primary_name
        fallback_used = False
        success = False
        transcript_chunks_count = 0
        summary_chunks_count = 0

        try:
            # 1. Embed query
            embed_client = GeminiClient(GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL_NAME)
            query_emb = await embed_client.embed_content(message)

            # 2. Retrieve chunks based on chat mode
            context_parts: list[str] = []
            chat_mode = str(status["chat_mode"])

            if chat_mode in (CHAT_MODE_TRANSCRIPT_ONLY, CHAT_MODE_TRANSCRIPT_AND_SUMMARY):
                transcript_chunks = await self.repository.search_transcript_chunks(
                    meeting_id, query_emb, limit=MAX_TRANSCRIPT_CHUNKS_PER_QUERY
                )
                transcript_chunks_count = len(transcript_chunks)
                if transcript_chunks:
                    matching_sequences = []
                    legacy_texts = []
                    
                    # Resolve sequence for each chunk (directly or via fallback text lookup)
                    for c in transcript_chunks:
                        if c.sequence is not None:
                            matching_sequences.append((c.sequence, c.text_content))
                        else:
                            legacy_texts.append(c.text_content)
                            
                    if legacy_texts:
                        legacy_matches = await self.repository.find_transcript_sequences_by_texts(
                            meeting_id, legacy_texts
                        )
                        # Build text to sequence mapping
                        text_to_seq = {m["text_content"]: m["sequence"] for m in legacy_matches}
                        for c in transcript_chunks:
                            if c.sequence is None and c.text_content in text_to_seq:
                                seq = text_to_seq[c.text_content]
                                matching_sequences.append((seq, c.text_content))
                                # Lazily self-heal chunk record in the database
                                try:
                                    await self.repository.update_chunk_sequence(meeting_id, c.text_content, seq)
                                except Exception as exc:
                                    logger.warning("Failed to lazily update sequence for chunk: %s", exc)

                    # Prioritized neighbor expansion (up to context budget)
                    selected_sequences = set()
                    for seq, _ in matching_sequences:
                        # Generate neighbors for the matching sequence S
                        neighbors = list(range(max(1, seq - TRANSCRIPT_NEIGHBOR_WINDOW), seq + TRANSCRIPT_NEIGHBOR_WINDOW + 1))
                        for n in neighbors:
                            if n in selected_sequences:
                                continue
                            if len(selected_sequences) < MAX_EXPANDED_TRANSCRIPT_SEGMENTS:
                                selected_sequences.add(n)
                            else:
                                break

                    if selected_sequences:
                        expanded_segments = await self.repository.get_transcript_segments_by_sequences(
                            meeting_id, sorted(list(selected_sequences))
                        )
                        seq_to_text = {s.sequence: (s.speaker_name or "Unknown Speaker", s.text_content) for s in expanded_segments}
                        
                        # Populate from matched chunks if any selected sequence is missing from DB segments
                        for c in transcript_chunks:
                            if c.sequence in selected_sequences and c.sequence not in seq_to_text:
                                seq_to_text[c.sequence] = (c.speaker_name or "Unknown Speaker", c.text_content)
                        
                        lines = []
                        for seq in sorted(list(selected_sequences)):
                            if seq in seq_to_text:
                                spk, txt = seq_to_text[seq]
                                lines.append(f"[{spk}]: {txt}")
                        
                        if lines:
                            transcript_text = "\n".join(lines)
                        else:
                            transcript_text = "\n".join(
                                f"[{c.speaker_name or 'Unknown Speaker'}]: {c.text_content}"
                                for c in transcript_chunks
                            )
                    else:
                        # Fallback if no sequences could be resolved
                        transcript_text = "\n".join(
                            f"[{c.speaker_name or 'Unknown Speaker'}]: {c.text_content}"
                            for c in transcript_chunks
                        )
                    context_parts.append(f"Transcript Context:\n{transcript_text}")

            if chat_mode in (CHAT_MODE_SUMMARY_ONLY, CHAT_MODE_TRANSCRIPT_AND_SUMMARY):
                summary_chunks = await self.repository.search_summary_chunks(
                    meeting_id, query_emb, limit=MAX_SUMMARY_CHUNKS_PER_QUERY
                )
                summary_chunks_count = len(summary_chunks)
                if summary_chunks:
                    summary_text = "\n".join(f"- {c.text_content}" for c in summary_chunks)
                    context_parts.append(f"Summary Context:\n{summary_text}")

            context = "\n\n".join(context_parts) if context_parts else "No context retrieved."

            # 3. Load most recent history for prompt injection
            db_messages = await self.repository.get_chat_history(meeting_id, user_id)
            recent_messages = db_messages[-PROMPT_HISTORY_LIMIT:]
            formatted_history = "\n".join(
                f"{'User' if msg.role == 'user' else 'Assistant'}: {msg.content}"
                for msg in recent_messages
            )

            meeting = await self.repository.get_meeting(meeting_id)
            meeting_title = meeting.title if meeting else "Unknown Meeting"

            system_prompt = get_system_prompt()
            prompt = system_prompt.format(
                meeting_title=meeting_title,
                context=context,
                chat_history=formatted_history,
                query=message,
            )

            # 4. Track whether the gateway fell back before and after the call
            was_healthy_before = self.llm_gateway.primary_healthy
            response_text = await self.llm_gateway.generate_content(prompt)
            still_healthy_after = self.llm_gateway.primary_healthy

            if was_healthy_before and not still_healthy_after:
                fallback_used = True
                provider_used = self.llm_gateway.fallback_name

            # 5. Persist both the user message and assistant response
            await self.repository.save_chat_message(meeting_id, user_id, "user", message)
            await self.repository.save_chat_message(meeting_id, user_id, "assistant", response_text)

            success = True

            response_mode = _derive_response_mode(transcript_chunks_count, summary_chunks_count)
            return ChatResult(
                response=response_text,
                response_mode=response_mode,
                transcript_chunks_used=transcript_chunks_count,
                summary_chunks_used=summary_chunks_count,
            )

        except Exception:
            incr(METRIC_CHAT_FAILURES_TOTAL)
            raise

        finally:
            latency_ms = int((time.monotonic() - request_start) * 1000)
            response_mode_logged = _derive_response_mode(transcript_chunks_count, summary_chunks_count)

            incr(METRIC_CHAT_REQUESTS_TOTAL)
            incr(METRIC_CHAT_DURATION_MS_TOTAL, latency_ms)
            if fallback_used:
                incr(METRIC_CHAT_FALLBACK_TOTAL)

            logger.info(
                "meeting_chat_request",
                extra={
                    "meeting_id": str(meeting_id),
                    "user_id": str(user_id),
                    "provider_used": provider_used,
                    "fallback_used": fallback_used,
                    "response_mode": response_mode_logged,
                    "transcript_chunks_used": transcript_chunks_count,
                    "summary_chunks_used": summary_chunks_count,
                    "latency_ms": latency_ms,
                    "success": success,
                },
            )
