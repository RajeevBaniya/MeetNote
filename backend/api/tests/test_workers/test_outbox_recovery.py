# ruff: noqa: E402
import asyncio
import uuid
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import AsyncGenerator

# Add backend_api path to sys.path
backend_api_path = Path(__file__).resolve().parent.parent.parent
if str(backend_api_path) not in sys.path:
    sys.path.insert(0, str(backend_api_path))


from app.db.base import engine
from app.db.session import async_session_factory
from app.db.models import MeetingOutbox
from app.core.database_setup import ensure_database_schema
from app.core.test_helpers import setup_test_services
from app.workers.outbox_worker import (
    recover_stuck_outbox_tasks,
    process_outbox_task,
)
from sqlalchemy import select, text
import pytest


@pytest.fixture(autouse=True)
async def cleanup_db_pool() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


async def clear_outbox_table() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM meeting_outbox"))


async def test_startup_recovery_of_stuck_processing_rows() -> None:
    print("Running: test_startup_recovery_of_stuck_processing_rows...")
    await clear_outbox_table()

    now = datetime.now(timezone.utc)
    stuck_time = now - timedelta(minutes=20)
    recent_time = now - timedelta(minutes=5)

    async with async_session_factory() as session:
        async with session.begin():
            # Task 1: Stuck in 'processing' (> 15 mins) -> Should recover
            task1 = MeetingOutbox(
                id=uuid.uuid4(),
                event_type="meeting_cleanup",
                payload={"meeting_id": str(uuid.uuid4()), "ended_at": now.isoformat(), "requester_id": str(uuid.uuid4())},
                status="processing",
                processing_started_at=stuck_time,
                attempts=1,
            )
            # Task 2: Active in 'processing' (< 15 mins) -> Should NOT recover
            task2 = MeetingOutbox(
                id=uuid.uuid4(),
                event_type="meeting_cleanup",
                payload={"meeting_id": str(uuid.uuid4()), "ended_at": now.isoformat(), "requester_id": str(uuid.uuid4())},
                status="processing",
                processing_started_at=recent_time,
                attempts=2,
            )
            # Task 3: Normal 'pending' -> Should NOT alter
            task3 = MeetingOutbox(
                id=uuid.uuid4(),
                event_type="meeting_cleanup",
                payload={"meeting_id": str(uuid.uuid4()), "ended_at": now.isoformat(), "requester_id": str(uuid.uuid4())},
                status="pending",
                attempts=0,
            )
            session.add_all([task1, task2, task3])

    recovered_count = await recover_stuck_outbox_tasks()
    assert recovered_count == 1, f"Expected 1 task recovered, got {recovered_count}"

    async with async_session_factory() as session:
        t1 = (await session.execute(select(MeetingOutbox).where(MeetingOutbox.id == task1.id))).scalar_one()
        t2 = (await session.execute(select(MeetingOutbox).where(MeetingOutbox.id == task2.id))).scalar_one()
        t3 = (await session.execute(select(MeetingOutbox).where(MeetingOutbox.id == task3.id))).scalar_one()

        assert t1.status == "pending", f"Task 1 status expected 'pending', got {t1.status}"
        assert t1.processing_started_at is None, "Task 1 processing_started_at should be cleared"
        assert t1.attempts == 1, "Task 1 attempts must NOT be incremented during recovery"

        assert t2.status == "processing", f"Task 2 status expected 'processing', got {t2.status}"
        assert t2.processing_started_at == recent_time

        assert t3.status == "pending", f"Task 3 status expected 'pending', got {t3.status}"

    print("PASS: Startup recovery of stuck processing rows behaves correctly.")


async def test_redis_failure_retry() -> None:
    print("Running: test_redis_failure_retry...")
    await clear_outbox_table()

    mocks = setup_test_services()
    # Mock Redis to raise connection error
    mocks["cache"].delete_keys.side_effect = Exception("Redis connection refused")

    now = datetime.now(timezone.utc)
    meeting_id = uuid.uuid4()
    requester_id = uuid.uuid4()

    async with async_session_factory() as session:
        async with session.begin():
            task = MeetingOutbox(
                id=uuid.uuid4(),
                event_type="meeting_cleanup",
                payload={
                    "meeting_id": str(meeting_id),
                    "ended_at": now.isoformat(),
                    "requester_id": str(requester_id),
                },
                status="pending",
                attempts=0,
            )
            session.add(task)

    # Simulate single iteration of the worker
    async with async_session_factory() as session:
        # 1. Fetch task
        stmt = (
            select(MeetingOutbox)
            .where(
                MeetingOutbox.status.in_(["pending", "failed"]),
                MeetingOutbox.attempts < MeetingOutbox.max_attempts,
            )
            .with_for_update(skip_locked=True)
        )
        task_item = (await session.execute(stmt)).scalar_one()
        task_item.status = "processing"
        task_item.processing_started_at = datetime.now(timezone.utc)
        task_item.attempts += 1
        await session.commit()
        task_id = task_item.id

    status = "completed"
    error_msg = None
    try:
        async with async_session_factory() as session:
            task_res = await session.execute(
                select(MeetingOutbox).where(MeetingOutbox.id == task_id)
            )
            task_item = task_res.scalar_one()
            await process_outbox_task(task_item)
    except Exception as exc:
        status = "failed"
        error_msg = str(exc)

    assert status == "failed", "Expected task processing to fail due to Redis error"
    assert error_msg is not None
    assert "Redis connection refused" in error_msg

    # Finalize status
    async with async_session_factory() as session:
        task_res = await session.execute(
            select(MeetingOutbox).where(MeetingOutbox.id == task_id)
        )
        task_item = task_res.scalar_one()
        task_item.processing_started_at = None
        task_item.status = status
        task_item.error_message = error_msg
        await session.commit()

    async with async_session_factory() as session:
        db_task = (await session.execute(select(MeetingOutbox).where(MeetingOutbox.id == task_id))).scalar_one()
        assert db_task.status == "failed"
        assert db_task.attempts == 1
        assert db_task.processing_started_at is None
        assert db_task.error_message is not None
        assert "Redis connection refused" in db_task.error_message

    print("PASS: Redis failure successfully triggers a failure state and retry path.")


async def test_stream_failure_retry() -> None:
    print("Running: test_stream_failure_retry...")
    await clear_outbox_table()

    mocks = setup_test_services()
    # Mock Stream API to raise error
    mocks["stream"].end_call.side_effect = Exception("Stream call termination timeout")

    now = datetime.now(timezone.utc)
    meeting_id = uuid.uuid4()
    requester_id = uuid.uuid4()

    async with async_session_factory() as session:
        async with session.begin():
            task = MeetingOutbox(
                id=uuid.uuid4(),
                event_type="meeting_cleanup",
                payload={
                    "meeting_id": str(meeting_id),
                    "ended_at": now.isoformat(),
                    "requester_id": str(requester_id),
                },
                status="pending",
                attempts=0,
            )
            session.add(task)

    # Simulate worker polling loop
    async with async_session_factory() as session:
        stmt = (
            select(MeetingOutbox)
            .where(
                MeetingOutbox.status.in_(["pending", "failed"]),
                MeetingOutbox.attempts < MeetingOutbox.max_attempts,
            )
            .with_for_update(skip_locked=True)
        )
        task_item = (await session.execute(stmt)).scalar_one()
        task_item.status = "processing"
        task_item.processing_started_at = datetime.now(timezone.utc)
        task_item.attempts += 1
        await session.commit()
        task_id = task_item.id

    status = "completed"
    error_msg = None
    try:
        async with async_session_factory() as session:
            task_res = await session.execute(
                select(MeetingOutbox).where(MeetingOutbox.id == task_id)
            )
            task_item = task_res.scalar_one()
            await process_outbox_task(task_item)
    except Exception as exc:
        status = "failed"
        error_msg = str(exc)

    assert status == "failed", "Expected task processing to fail due to Stream error"

    # Finalize status
    async with async_session_factory() as session:
        task_res = await session.execute(
            select(MeetingOutbox).where(MeetingOutbox.id == task_id)
        )
        task_item = task_res.scalar_one()
        task_item.processing_started_at = None
        task_item.status = status
        task_item.error_message = error_msg
        await session.commit()

    async with async_session_factory() as session:
        db_task = (await session.execute(select(MeetingOutbox).where(MeetingOutbox.id == task_id))).scalar_one()
        assert db_task.status == "failed"
        assert db_task.attempts == 1
        assert db_task.error_message is not None
        assert "Stream call termination timeout" in db_task.error_message

    print("PASS: Stream failure successfully triggers a failure state and retry path.")


async def test_dead_letter_transition() -> None:
    print("Running: test_dead_letter_transition...")
    await clear_outbox_table()

    mocks = setup_test_services()
    mocks["stream"].end_call.side_effect = Exception("Fatal third-party error")

    now = datetime.now(timezone.utc)
    meeting_id = uuid.uuid4()
    requester_id = uuid.uuid4()

    async with async_session_factory() as session:
        async with session.begin():
            # Already failed 4 times
            task = MeetingOutbox(
                id=uuid.uuid4(),
                event_type="meeting_cleanup",
                payload={
                    "meeting_id": str(meeting_id),
                    "ended_at": now.isoformat(),
                    "requester_id": str(requester_id),
                },
                status="failed",
                attempts=4,
                max_attempts=5,
            )
            session.add(task)

    # 5th attempt: Poll and execute
    async with async_session_factory() as session:
        stmt = (
            select(MeetingOutbox)
            .where(
                MeetingOutbox.status.in_(["pending", "failed"]),
                MeetingOutbox.attempts < MeetingOutbox.max_attempts,
            )
            .with_for_update(skip_locked=True)
        )
        task_item = (await session.execute(stmt)).scalar_one()
        task_item.status = "processing"
        task_item.processing_started_at = datetime.now(timezone.utc)
        task_item.attempts += 1
        await session.commit()
        task_id = task_item.id

    status = "completed"
    error_msg = None
    try:
        async with async_session_factory() as session:
            task_res = await session.execute(
                select(MeetingOutbox).where(MeetingOutbox.id == task_id)
            )
            task_item = task_res.scalar_one()
            await process_outbox_task(task_item)
    except Exception as exc:
        status = "failed"
        error_msg = str(exc)

    # Finalize status to dead_letter
    async with async_session_factory() as session:
        task_res = await session.execute(
            select(MeetingOutbox).where(MeetingOutbox.id == task_id)
        )
        task_item = task_res.scalar_one()
        task_item.processing_started_at = None
        if status == "failed" and task_item.attempts >= task_item.max_attempts:
            task_item.status = "dead_letter"
        else:
            task_item.status = status
        task_item.error_message = error_msg
        await session.commit()

    async with async_session_factory() as session:
        db_task = (await session.execute(select(MeetingOutbox).where(MeetingOutbox.id == task_id))).scalar_one()
        assert db_task.status == "dead_letter"
        assert db_task.attempts == 5
        assert db_task.processing_started_at is None
        assert db_task.error_message is not None
        assert "Fatal third-party error" in db_task.error_message

        # Verify it is no longer picked up by polling query
        stmt = (
            select(MeetingOutbox)
            .where(
                MeetingOutbox.status.in_(["pending", "failed"]),
                MeetingOutbox.attempts < MeetingOutbox.max_attempts,
            )
        )
        t_res = (await session.execute(stmt)).scalar_one_or_none()
        assert t_res is None, "Dead-letter rows must never be picked up by the polling query!"

    print("PASS: Task safely transitioned to 'dead_letter' status on final retry failure.")


async def test_worker_crash_and_process_restart_recovery_path() -> None:
    print("Running: test_worker_crash_and_process_restart_recovery_path...")
    await clear_outbox_table()

    now = datetime.now(timezone.utc)
    stuck_time = now - timedelta(minutes=20)
    meeting_id = uuid.uuid4()
    requester_id = uuid.uuid4()

    async with async_session_factory() as session:
        async with session.begin():
            # Simulate a worker crash leaving a row in status='processing'
            task = MeetingOutbox(
                id=uuid.uuid4(),
                event_type="meeting_cleanup",
                payload={
                    "meeting_id": str(meeting_id),
                    "ended_at": now.isoformat(),
                    "requester_id": str(requester_id),
                },
                status="processing",
                processing_started_at=stuck_time,
                attempts=1,
            )
            session.add(task)

    # 1. Startup recovery runs
    recovered_count = await recover_stuck_outbox_tasks()
    assert recovered_count == 1, "Should recover stuck crashed task"

    # 2. Verify recovered task is reset to pending
    async with async_session_factory() as session:
        db_task = (await session.execute(select(MeetingOutbox).where(MeetingOutbox.id == task.id))).scalar_one()
        assert db_task.status == "pending"
        assert db_task.processing_started_at is None

    # 3. Simulate restarted worker polling and executing it only once
    setup_test_services() # successful mocks
    async with async_session_factory() as session:
        stmt = (
            select(MeetingOutbox)
            .where(
                MeetingOutbox.status.in_(["pending", "failed"]),
                MeetingOutbox.attempts < MeetingOutbox.max_attempts,
            )
            .with_for_update(skip_locked=True)
        )
        task_item = (await session.execute(stmt)).scalar_one()
        task_item.status = "processing"
        task_item.processing_started_at = datetime.now(timezone.utc)
        task_item.attempts += 1
        await session.commit()
        task_id = task_item.id

    status = "completed"
    try:
        async with async_session_factory() as session:
            task_res = await session.execute(
                select(MeetingOutbox).where(MeetingOutbox.id == task_id)
            )
            task_item = task_res.scalar_one()
            await process_outbox_task(task_item)
    except Exception:
        status = "failed"

    # Finalize
    async with async_session_factory() as session:
        task_res = await session.execute(
            select(MeetingOutbox).where(MeetingOutbox.id == task_id)
        )
        task_item = task_res.scalar_one()
        task_item.processing_started_at = None
        task_item.status = status
        await session.commit()

    async with async_session_factory() as session:
        db_task = (await session.execute(select(MeetingOutbox).where(MeetingOutbox.id == task_id))).scalar_one()
        assert db_task.status == "completed"
        assert db_task.attempts == 2

        # Verify no further work is selected
        stmt = (
            select(MeetingOutbox)
            .where(
                MeetingOutbox.status.in_(["pending", "failed"]),
                MeetingOutbox.attempts < MeetingOutbox.max_attempts,
            )
        )
        t_res = (await session.execute(stmt)).scalar_one_or_none()
        assert t_res is None, "Recovered task must only execute once and complete successfully."

    print("PASS: Worker crash and process restart recovery path verified successfully.")


async def main() -> None:
    print("Running database schema ensure...")
    await ensure_database_schema(engine)
    print("Database schema ensure completed.")

    await test_startup_recovery_of_stuck_processing_rows()
    await test_redis_failure_retry()
    await test_stream_failure_retry()
    await test_dead_letter_transition()
    await test_worker_crash_and_process_restart_recovery_path()

    print("\nALL RELIABILITY VERIFICATIONS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())
