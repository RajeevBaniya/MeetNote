import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from app.core.database_setup import ensure_database_schema
from app.db.base import engine
from app.db.models import MeetingTranscriptChunk, MeetingSummaryChunk, MeetingTranscript
from app.db.session import async_session_factory
from app.modules.meeting_chat.repository import MeetingChatRepository
from app.modules.meeting_chat.service import MeetingChatService
from app.modules.meeting_chat.exceptions import MeetingChatPermissionError


@pytest.fixture(scope="module")
def event_loop():
    """Share a single event loop across all tests in this module to prevent pool socket mismatch."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_meeting_chat_pipeline():
    try:
        await ensure_database_schema(engine)

        meeting_id = uuid.uuid4()
        user_id = uuid.uuid4()
        unauthorized_user_id = uuid.uuid4()

        async with async_session_factory() as session:
            async with session.begin():
                # Create users
                await session.execute(
                    text(
                        "INSERT INTO users (id, email, hashed_password, is_active, created_at) "
                        "VALUES (:id, :email, :hashed_password, true, NOW())"
                    ),
                    {"id": user_id, "email": f"chat-user-{uuid.uuid4()}@example.com", "hashed_password": "hash"}
                )
                await session.execute(
                    text(
                        "INSERT INTO users (id, email, hashed_password, is_active, created_at) "
                        "VALUES (:id, :email, :hashed_password, true, NOW())"
                    ),
                    {"id": unauthorized_user_id, "email": f"unauth-user-{uuid.uuid4()}@example.com", "hashed_password": "hash"}
                )

                # Create an ended meeting
                await session.execute(
                    text(
                        "INSERT INTO meetings (id, host_id, original_host_id, current_host_id, title, join_code, passcode, is_active, created_at, ended_at) "
                        "VALUES (:id, :host_id, :host_id, :host_id, 'Chat Test Meeting', 'abc-def-ghij', '123456', false, NOW(), NOW())"
                    ),
                    {"id": meeting_id, "host_id": user_id}
                )

        async with async_session_factory() as session:
            repo = MeetingChatRepository(session)
            service = MeetingChatService(repo)

            # Test Permission Validation
            assert await repo.check_user_membership(meeting_id, user_id) is True
            assert await repo.check_user_membership(meeting_id, unauthorized_user_id) is False

            with pytest.raises(MeetingChatPermissionError):
                await service.get_chat_status(meeting_id, unauthorized_user_id)

            # Test status when no transcripts/summaries exist
            status = await service.get_chat_status(meeting_id, user_id)
            assert status["is_available"] is False
            assert status["chat_mode"] == "unavailable"
            assert status["has_transcript"] is False
            assert status["has_summary"] is False

        mock_vector = [0.1] * 768

        # Insert transcript records and chunk embeddings
        async with async_session_factory() as session:
            async with session.begin():
                session.add(MeetingTranscript(
                    id=uuid.uuid4(),
                    meeting_id=meeting_id,
                    sequence=1,
                    speaker_id=str(user_id),
                    speaker_name="Alice",
                    text_content="We decided to launch the product in Q3.",
                    timestamp=datetime.now(timezone.utc)
                ))

                session.add(MeetingTranscriptChunk(
                    id=uuid.uuid4(),
                    meeting_id=meeting_id,
                    sequence=1,
                    speaker_name="Alice",
                    text_content="We decided to launch the product in Q3.",
                    text_hash="hash1",
                    is_active=True,
                    embedding=mock_vector
                ))

        mock_embed_client = AsyncMock()
        mock_embed_client.embed_content = AsyncMock(return_value=mock_vector)

        # Test Transcript-only retrieval state
        with patch("app.modules.meeting_chat.service.GeminiClient", return_value=mock_embed_client):
            async with async_session_factory() as session:
                repo = MeetingChatRepository(session)
                mock_gateway = AsyncMock()
                mock_gateway.primary_name = "gemini"
                mock_gateway.primary_healthy = True
                mock_gateway.generate_content = AsyncMock(return_value="Mocked LLM Response")
                service = MeetingChatService(repo, llm_gateway=mock_gateway)

                status = await service.get_chat_status(meeting_id, user_id)
                assert status["is_available"] is True
                assert status["chat_mode"] == "transcript"
                assert status["has_transcript"] is True
                assert status["has_summary"] is False

                await service.get_chat_response(
                    meeting_id=meeting_id,
                    user_id=user_id,
                    message="When is launch?",
                    history=[]
                )
                called_prompt = mock_gateway.generate_content.call_args[0][0]
                assert "Transcript Context:" in called_prompt
                assert "[Alice]: We decided to launch" in called_prompt
                assert "Summary Context:" not in called_prompt

        # Add summary chunk embedding to test Transcript + Summary state
        async with async_session_factory() as session:
            async with session.begin():
                session.add(MeetingSummaryChunk(
                    id=uuid.uuid4(),
                    meeting_id=meeting_id,
                    text_content="The team finalized the product launch for Q3.",
                    text_hash="hash2",
                    embedding=mock_vector
                ))

        with patch("app.modules.meeting_chat.service.GeminiClient", return_value=mock_embed_client):
            async with async_session_factory() as session:
                repo = MeetingChatRepository(session)
                mock_gateway = AsyncMock()
                mock_gateway.primary_name = "gemini"
                mock_gateway.primary_healthy = True
                mock_gateway.generate_content = AsyncMock(return_value="Mocked LLM Response")
                service = MeetingChatService(repo, llm_gateway=mock_gateway)

                status = await service.get_chat_status(meeting_id, user_id)
                assert status["is_available"] is True
                assert status["chat_mode"] == "transcript_and_summary"
                assert status["has_transcript"] is True
                assert status["has_summary"] is True

                await service.get_chat_response(
                    meeting_id=meeting_id,
                    user_id=user_id,
                    message="When is launch?",
                    history=[]
                )
                called_prompt = mock_gateway.generate_content.call_args[0][0]
                assert "Transcript Context:" in called_prompt
                assert "[Alice]: We decided to launch" in called_prompt
                assert "Summary Context:" in called_prompt
                assert "- The team finalized" in called_prompt

        # Mark transcript chunk as inactive to test Summary-only state
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("UPDATE meeting_transcript_chunks SET is_active = false WHERE meeting_id = :id"),
                    {"id": meeting_id}
                )

        with patch("app.modules.meeting_chat.service.GeminiClient", return_value=mock_embed_client):
            async with async_session_factory() as session:
                repo = MeetingChatRepository(session)
                mock_gateway = AsyncMock()
                mock_gateway.primary_name = "gemini"
                mock_gateway.primary_healthy = True
                mock_gateway.generate_content = AsyncMock(return_value="Mocked LLM Response")
                service = MeetingChatService(repo, llm_gateway=mock_gateway)

                status = await service.get_chat_status(meeting_id, user_id)
                assert status["is_available"] is True
                assert status["chat_mode"] == "summary"
                assert status["has_transcript"] is True
                assert status["has_summary"] is True

                await service.get_chat_response(
                    meeting_id=meeting_id,
                    user_id=user_id,
                    message="When is launch?",
                    history=[]
                )
                called_prompt = mock_gateway.generate_content.call_args[0][0]
                assert "Summary Context:" in called_prompt
                assert "- The team finalized" in called_prompt
                assert "Transcript Context:" not in called_prompt

        # Verify chat history persistence
        async with async_session_factory() as session:
            repo = MeetingChatRepository(session)
            service = MeetingChatService(repo)

            await repo.save_chat_message(meeting_id, user_id, "user", "Hello assistant")
            await repo.save_chat_message(meeting_id, user_id, "assistant", "Hello user")

            history = await repo.get_chat_history(meeting_id, user_id)
            assert len(history) == 2
            assert history[0].role == "user"
            assert history[0].content == "Hello assistant"
            assert history[1].role == "assistant"
            assert history[1].content == "Hello user"

            history_service = await service.get_chat_history(meeting_id, user_id)
            assert len(history_service) == 2
            assert history_service[0]["role"] == "user"
            assert history_service[1]["role"] == "assistant"

            history_unauth = await repo.get_chat_history(meeting_id, unauthorized_user_id)
            assert len(history_unauth) == 0

        # Verify cleanup worker transcript expiration
        from app.workers.meeting_cleanup_worker import _expire_old_transcripts

        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("UPDATE meeting_transcript_chunks SET is_active = true WHERE meeting_id = :id"),
                    {"id": meeting_id}
                )

        async with async_session_factory() as session:
            res_trans = await session.execute(
                text("SELECT COUNT(*) FROM meeting_transcripts WHERE meeting_id = :id"),
                {"id": meeting_id}
            )
            assert res_trans.scalar() > 0
            res_chunk = await session.execute(
                text("SELECT COUNT(*) FROM meeting_transcript_chunks WHERE meeting_id = :id"),
                {"id": meeting_id}
            )
            assert res_chunk.scalar() > 0

        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("UPDATE meetings SET ended_at = NOW() - INTERVAL '8 days' WHERE id = :id"),
                    {"id": meeting_id}
                )

        await _expire_old_transcripts()

        async with async_session_factory() as session:
            res_trans = await session.execute(
                text("SELECT COUNT(*) FROM meeting_transcripts WHERE meeting_id = :id"),
                {"id": meeting_id}
            )
            assert res_trans.scalar() == 0
            res_chunk = await session.execute(
                text("SELECT COUNT(*) FROM meeting_transcript_chunks WHERE meeting_id = :id"),
                {"id": meeting_id}
            )
            assert res_chunk.scalar() == 0

        # Cleanup database test records
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("DELETE FROM meetings WHERE id = :id"),
                    {"id": meeting_id}
                )
                await session.execute(
                    text("DELETE FROM users WHERE id IN (:user_id, :unauth_id)"),
                    {"user_id": user_id, "unauth_id": unauthorized_user_id}
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_meeting_isolation():
    try:
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        meeting_a = uuid.uuid4()
        meeting_b = uuid.uuid4()
        mock_vector = [0.1] * 768

        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("INSERT INTO users (id, email, hashed_password, is_active, created_at) VALUES (:id, :email, 'hash', true, NOW())"),
                    {"id": user_a, "email": f"user-a-{uuid.uuid4()}@example.com"}
                )
                await session.execute(
                    text("INSERT INTO users (id, email, hashed_password, is_active, created_at) VALUES (:id, :email, 'hash', true, NOW())"),
                    {"id": user_b, "email": f"user-b-{uuid.uuid4()}@example.com"}
                )

                await session.execute(
                    text("INSERT INTO meetings (id, host_id, original_host_id, current_host_id, title, join_code, passcode, is_active, created_at, ended_at) VALUES (:id, :host_id, :host_id, :host_id, 'Meeting A', :join_code, '123456', false, NOW(), NOW())"),
                    {"id": meeting_a, "host_id": user_a, "join_code": f"abc-{str(uuid.uuid4())[:8]}"}
                )
                await session.execute(
                    text("INSERT INTO meetings (id, host_id, original_host_id, current_host_id, title, join_code, passcode, is_active, created_at, ended_at) VALUES (:id, :host_id, :host_id, :host_id, 'Meeting B', :join_code, '123456', false, NOW(), NOW())"),
                    {"id": meeting_b, "host_id": user_b, "join_code": f"abc-{str(uuid.uuid4())[:8]}"}
                )

                session.add(MeetingTranscript(
                    id=uuid.uuid4(),
                    meeting_id=meeting_a,
                    sequence=1,
                    speaker_id=str(user_a),
                    speaker_name="Speaker A",
                    text_content="This is Meeting A transcript chunk",
                    timestamp=datetime.now(timezone.utc)
                ))
                session.add(MeetingTranscript(
                    id=uuid.uuid4(),
                    meeting_id=meeting_b,
                    sequence=1,
                    speaker_id=str(user_b),
                    speaker_name="Speaker B",
                    text_content="This is Meeting B transcript chunk",
                    timestamp=datetime.now(timezone.utc)
                ))

                session.add(MeetingTranscriptChunk(
                    id=uuid.uuid4(),
                    meeting_id=meeting_a,
                    sequence=1,
                    speaker_name="Speaker A",
                    text_content="This is Meeting A transcript chunk",
                    text_hash="hash-a",
                    is_active=True,
                    embedding=mock_vector
                ))
                session.add(MeetingTranscriptChunk(
                    id=uuid.uuid4(),
                    meeting_id=meeting_b,
                    sequence=1,
                    speaker_name="Speaker B",
                    text_content="This is Meeting B transcript chunk",
                    text_hash="hash-b",
                    is_active=True,
                    embedding=mock_vector
                ))

        mock_embed_client = AsyncMock()
        mock_embed_client.embed_content = AsyncMock(return_value=mock_vector)

        with patch("app.modules.meeting_chat.service.GeminiClient", return_value=mock_embed_client):
            async with async_session_factory() as session:
                repo = MeetingChatRepository(session)
                mock_gateway = AsyncMock()
                mock_gateway.primary_name = "gemini"
                mock_gateway.primary_healthy = True
                mock_gateway.generate_content = AsyncMock(return_value="Mocked LLM Response")
                service = MeetingChatService(repo, llm_gateway=mock_gateway)

                status_a = await service.get_chat_status(meeting_a, user_a)
                assert status_a["is_available"] is True
                assert status_a["chat_mode"] == "transcript"

                await service.get_chat_response(
                    meeting_id=meeting_a,
                    user_id=user_a,
                    message="Semantically identical search query",
                    history=[]
                )

                called_prompt = mock_gateway.generate_content.call_args[0][0]
                assert "This is Meeting A transcript chunk" in called_prompt
                assert "This is Meeting B transcript chunk" not in called_prompt

                with pytest.raises(MeetingChatPermissionError):
                    await service.get_chat_status(meeting_b, user_a)

                with pytest.raises(MeetingChatPermissionError):
                    await service.get_chat_response(meeting_b, user_a, "Query", [])

        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("DELETE FROM meetings WHERE id IN (:id_a, :id_b)"),
                    {"id_a": meeting_a, "id_b": meeting_b}
                )
                await session.execute(
                    text("DELETE FROM users WHERE id IN (:user_a, :user_b)"),
                    {"user_a": user_a, "user_b": user_b}
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_meeting_chat_neighbor_expansion_and_budget():
    meeting_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_vector = [0.1] * 768

    try:
        await ensure_database_schema(engine)
        
        async with async_session_factory() as session:
            async with session.begin():
                # Setup user & meeting
                await session.execute(
                    text("INSERT INTO users (id, email, hashed_password, is_active, created_at) VALUES (:id, :email, 'hash', true, NOW())"),
                    {"id": user_id, "email": f"test-user-{uuid.uuid4()}@example.com"}
                )
                await session.execute(
                    text("INSERT INTO meetings (id, host_id, original_host_id, current_host_id, title, join_code, passcode, is_active, created_at, ended_at) VALUES (:id, :host_id, :host_id, :host_id, 'Neighbor Test', 'abc-def-1234', '123456', false, NOW(), NOW())"),
                    {"id": meeting_id, "host_id": user_id}
                )

                # Insert 5 segments
                for seq in range(1, 6):
                    session.add(MeetingTranscript(
                        id=uuid.uuid4(),
                        meeting_id=meeting_id,
                        sequence=seq,
                        speaker_id=str(user_id),
                        speaker_name="Bob",
                        text_content=f"This is segment {seq}",
                        timestamp=datetime.now(timezone.utc)
                    ))

                # Insert chunks for seq 3 and 4
                session.add(MeetingTranscriptChunk(
                    id=uuid.uuid4(),
                    meeting_id=meeting_id,
                    sequence=3,
                    speaker_name="Bob",
                    text_content="This is segment 3",
                    text_hash="hash-3",
                    is_active=True,
                    embedding=mock_vector
                ))
                session.add(MeetingTranscriptChunk(
                    id=uuid.uuid4(),
                    meeting_id=meeting_id,
                    sequence=4,
                    speaker_name="Bob",
                    text_content="This is segment 4",
                    text_hash="hash-4",
                    is_active=True,
                    embedding=mock_vector
                ))

        mock_embed_client = AsyncMock()
        mock_embed_client.embed_content = AsyncMock(return_value=mock_vector)

        with patch("app.modules.meeting_chat.service.GeminiClient", return_value=mock_embed_client):
            async with async_session_factory() as session:
                repo = MeetingChatRepository(session)
                mock_gateway = AsyncMock()
                mock_gateway.primary_name = "gemini"
                mock_gateway.primary_healthy = True
                mock_gateway.generate_content = AsyncMock(return_value="Response")
                service = MeetingChatService(repo, llm_gateway=mock_gateway)

                # Test with Window=1 (seq 3 -> [2,3,4]; seq 4 -> [3,4,5] -> deduplicated [2,3,4,5])
                with patch("app.modules.meeting_chat.service.TRANSCRIPT_NEIGHBOR_WINDOW", 1):
                    with patch("app.modules.meeting_chat.service.MAX_EXPANDED_TRANSCRIPT_SEGMENTS", 10):
                        await service.get_chat_response(meeting_id, user_id, "Find segments", [])
                        called_prompt = mock_gateway.generate_content.call_args[0][0]
                        assert "This is segment 2" in called_prompt
                        assert "This is segment 3" in called_prompt
                        assert "This is segment 4" in called_prompt
                        assert "This is segment 5" in called_prompt
                        assert "This is segment 1" not in called_prompt

                # Test with Window=1 and Budget=2 (should limit to 2 segments)
                with patch("app.modules.meeting_chat.service.TRANSCRIPT_NEIGHBOR_WINDOW", 1):
                    with patch("app.modules.meeting_chat.service.MAX_EXPANDED_TRANSCRIPT_SEGMENTS", 2):
                        mock_gateway.generate_content.reset_mock()
                        await service.get_chat_response(meeting_id, user_id, "Find segments", [])
                        called_prompt2 = mock_gateway.generate_content.call_args[0][0]
                        
                        # Verify the prompt contains exactly 2 segment texts
                        segment_hits = [f"This is segment {i}" in called_prompt2 for i in range(1, 6)]
                        assert sum(segment_hits) == 2

    finally:
        # Cleanup
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(text("DELETE FROM meetings WHERE id = :id"), {"id": meeting_id})
                await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await engine.dispose()


@pytest.mark.asyncio
async def test_meeting_chat_legacy_self_healing():
    meeting_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_vector = [0.1] * 768

    try:
        await ensure_database_schema(engine)
        
        async with async_session_factory() as session:
            async with session.begin():
                # Setup user & meeting
                await session.execute(
                    text("INSERT INTO users (id, email, hashed_password, is_active, created_at) VALUES (:id, :email, 'hash', true, NOW())"),
                    {"id": user_id, "email": f"test-user-{uuid.uuid4()}@example.com"}
                )
                await session.execute(
                    text("INSERT INTO meetings (id, host_id, original_host_id, current_host_id, title, join_code, passcode, is_active, created_at, ended_at) VALUES (:id, :host_id, :host_id, :host_id, 'Self Healing Test', 'abc-def-2345', '123456', false, NOW(), NOW())"),
                    {"id": meeting_id, "host_id": user_id}
                )

                # Insert segment at sequence 12
                session.add(MeetingTranscript(
                    id=uuid.uuid4(),
                    meeting_id=meeting_id,
                    sequence=12,
                    speaker_id=str(user_id),
                    speaker_name="Alice",
                    text_content="Specific keyword for legacy chunk.",
                    timestamp=datetime.now(timezone.utc)
                ))

                # Insert legacy chunk with sequence=None
                session.add(MeetingTranscriptChunk(
                    id=uuid.uuid4(),
                    meeting_id=meeting_id,
                    sequence=None,
                    speaker_name="Alice",
                    text_content="Specific keyword for legacy chunk.",
                    text_hash="legacy-hash",
                    is_active=True,
                    embedding=mock_vector
                ))

        mock_embed_client = AsyncMock()
        mock_embed_client.embed_content = AsyncMock(return_value=mock_vector)

        with patch("app.modules.meeting_chat.service.GeminiClient", return_value=mock_embed_client):
            async with async_session_factory() as session:
                repo = MeetingChatRepository(session)
                mock_gateway = AsyncMock()
                mock_gateway.primary_name = "gemini"
                mock_gateway.primary_healthy = True
                mock_gateway.generate_content = AsyncMock(return_value="Response")
                service = MeetingChatService(repo, llm_gateway=mock_gateway)

                # Assert sequence is currently None in the DB
                res_before = await session.execute(
                    text("SELECT sequence FROM meeting_transcript_chunks WHERE text_hash = 'legacy-hash'")
                )
                assert res_before.scalar() is None

                # Query to trigger RAG search, fallback text lookup, and self-healing lazy update
                await service.get_chat_response(meeting_id, user_id, "Querying legacy chunk", [])

                # Verify sequence has healed to 12 in the DB!
                # Start a new transaction to read updated DB state
                async with async_session_factory() as session2:
                    res_after = await session2.execute(
                        text("SELECT sequence FROM meeting_transcript_chunks WHERE text_hash = 'legacy-hash'")
                    )
                    assert res_after.scalar() == 12

    finally:
        # Cleanup
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(text("DELETE FROM meetings WHERE id = :id"), {"id": meeting_id})
                await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await engine.dispose()


@pytest.mark.asyncio
async def test_meeting_chat_boundary_crossing_overlap():
    from app.modules.rag.service import process_rag_ingestion_job
    meeting_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_vector = [0.1] * 768

    try:
        await ensure_database_schema(engine)
        
        async with async_session_factory() as session:
            async with session.begin():
                # Setup user & meeting
                await session.execute(
                    text("INSERT INTO users (id, email, hashed_password, is_active, created_at) VALUES (:id, :email, 'hash', true, NOW())"),
                    {"id": user_id, "email": f"test-user-{uuid.uuid4()}@example.com"}
                )
                await session.execute(
                    text("INSERT INTO meetings (id, host_id, original_host_id, current_host_id, title, join_code, passcode, is_active, created_at, ended_at) VALUES (:id, :host_id, :host_id, :host_id, 'Overlap Test', 'abc-def-3456', '123456', false, NOW(), NOW())"),
                    {"id": meeting_id, "host_id": user_id}
                )

                # Segment 1
                session.add(MeetingTranscript(
                    id=uuid.uuid4(),
                    meeting_id=meeting_id,
                    sequence=1,
                    speaker_id=str(user_id),
                    speaker_name="Alice",
                    text_content="We will implement Speech Gateway next week.",
                    timestamp=datetime.now(timezone.utc)
                ))
                # Segment 2
                session.add(MeetingTranscript(
                    id=uuid.uuid4(),
                    meeting_id=meeting_id,
                    sequence=2,
                    speaker_id=str(user_id),
                    speaker_name="Alice",
                    text_content="Let's make sure SFU is scalable.",
                    timestamp=datetime.now(timezone.utc)
                ))

        mock_gemini = AsyncMock()
        mock_gemini.embed_content = AsyncMock(return_value=mock_vector)

        # Ingest Segment 1 and Segment 2 with Overlap = 1
        with patch("app.modules.rag.service.TRANSCRIPT_CHUNK_OVERLAP", 1):
            async with async_session_factory() as session:
                async with session.begin():
                    # Segment 1 (no previous segment)
                    await process_rag_ingestion_job(
                        session=session,
                        client=mock_gemini,
                        meeting_id=meeting_id,
                        chunk_type="transcript",
                        text_content="We will implement Speech Gateway next week.",
                        speaker_name="Alice",
                        sequence=1
                    )
                    # Segment 2 (prepends Segment 1)
                    await process_rag_ingestion_job(
                        session=session,
                        client=mock_gemini,
                        meeting_id=meeting_id,
                        chunk_type="transcript",
                        text_content="Let's make sure SFU is scalable.",
                        speaker_name="Alice",
                        sequence=2
                    )

        # Verify that process_rag_ingestion_job prepended segment 1 text for segment 2 embedding call
        calls = mock_gemini.embed_content.call_args_list
        assert calls[0][0][0] == "[Alice]: We will implement Speech Gateway next week."
        assert calls[1][0][0] == "[Alice]: We will implement Speech Gateway next week.\n[Alice]: Let's make sure SFU is scalable."

        # Verify that meeting_transcripts table remains clean and unmodified
        async with async_session_factory() as session:
            res = await session.execute(
                text("SELECT text_content FROM meeting_transcripts WHERE meeting_id = :id ORDER BY sequence ASC"),
                {"id": meeting_id}
            )
            rows = res.scalars().all()
            assert rows[0] == "We will implement Speech Gateway next week."
            assert rows[1] == "Let's make sure SFU is scalable."

    finally:
        # Cleanup
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(text("DELETE FROM meetings WHERE id = :id"), {"id": meeting_id})
                await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await engine.dispose()

