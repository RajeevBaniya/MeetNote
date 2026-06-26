import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.config import (
    SUMMEREASE_INGESTION_INTERVAL_SECONDS,
    SUMMEREASE_RECOVERY_INTERVAL_SECONDS,
    SUMMEREASE_TOKEN_REFRESH_INTERVAL,
    SUMMEREASE_CHUNK_SIZE_CHARS,
    SUMMEREASE_CHUNK_OVERLAP_CHARS,
)
from app.core.storage import download_file_bytes, delete_file
from app.db.session import async_session_factory
from app.db.models import JobModel, JobChunkProgressModel, SummaryModel
from app.services.extractor import extract_document_text
from app.services.chunker import chunk_document_stream
from app.ai.gemini import (
    generate_chunk_summary_single_pass,
    merge_chunk_summaries,
    merge_structured_data,
)

logger = logging.getLogger(__name__)


class DocumentProcessingWorker:
    """
    Background worker that polls, processes, and manages chunked document processing jobs.
    """

    def __init__(self) -> None:
        self.polling_task: asyncio.Task | None = None
        self.recovery_task: asyncio.Task | None = None
        self.running: bool = False

    def start(self) -> None:
        """Starts background worker loops."""
        if self.running:
            return
        self.running = True
        self.polling_task = asyncio.create_task(self._poll_loop())
        self.recovery_task = asyncio.create_task(self._recovery_loop())
        logger.info("background_worker_started")

    async def stop(self) -> None:
        """Stops background worker loops gracefully."""
        self.running = False
        tasks = []
        if self.polling_task:
            self.polling_task.cancel()
            tasks.append(self.polling_task)
        if self.recovery_task:
            self.recovery_task.cancel()
            tasks.append(self.recovery_task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("background_worker_stopped")

    async def _poll_loop(self) -> None:
        """Main loop that continuously polls and runs pending jobs."""
        while self.running:
            try:
                job_processed = await self._poll_and_process()
                # If a job was processed, poll again immediately; otherwise wait configured interval
                if not job_processed:
                    await asyncio.sleep(SUMMEREASE_INGESTION_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("poll_loop_iteration_failed")
                await asyncio.sleep(SUMMEREASE_INGESTION_INTERVAL_SECONDS)

    async def _recovery_loop(self) -> None:
        """Periodic loop to recover stale stuck jobs."""
        while self.running:
            try:
                # Run recovery periodically
                await self._recover_stale_jobs()
                await asyncio.sleep(SUMMEREASE_RECOVERY_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("recovery_loop_iteration_failed")
                await asyncio.sleep(SUMMEREASE_TOKEN_REFRESH_INTERVAL)

    async def _poll_and_process(self) -> bool:
        """
        Polls for a PENDING or PENDING-like job, locks it, and runs processing.
        Returns True if a job was found and processed, False otherwise.
        """
        async with async_session_factory() as db:
            # Select first pending job using Postgres FOR UPDATE SKIP LOCKED row locking
            stmt = (
                select(JobModel)
                .where(JobModel.status == "PENDING")
                .order_by(JobModel.created_at.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            result = await db.execute(stmt)
            job = result.scalars().first()

            if not job:
                return False

            logger.info("job_locked_for_processing job_id=%s", job.id)
            job.status = "PROCESSING"
            job.updated_at = datetime.now(timezone.utc)
            await db.commit()
            
            # Start job processing task
            # We process inside a try-catch to update DB status appropriately on failure
            try:  
                await self._process_job(job.id)
            except Exception as err:
                logger.exception("job_execution_failed job_id=%s", job.id)
                # Re-fetch job to update status to FAILED safely
                async with async_session_factory() as error_db:
                    update_stmt = (
                        update(JobModel)
                        .where(JobModel.id == job.id)
                        .values(
                            status="FAILED",
                            failure_reason=str(err),
                            updated_at=datetime.now(timezone.utc)
                        )
                    )
                    await error_db.execute(update_stmt)
                    await error_db.commit()
            return True

    async def _process_job(self, job_id: uuid.UUID) -> None:
        """Runs the chunk extraction, LLM summarization, and compilation logic for a job."""
        logger.info("processing_job_started job_id=%s", job_id)
        
        upload_path = None
        try:
            async with async_session_factory() as db:
                stmt = select(JobModel).where(JobModel.id == job_id).options(selectinload(JobModel.chunks))
                result = await db.execute(stmt)
                job = result.scalars().first()
                if not job:
                    logger.error("job_not_found job_id=%s", job_id)
                    return

                upload_path = job.upload_path
                file_name = job.file_name or ""
                instruction = job.instruction or "Summarize the key points and action items."
                user_id = job.user_id

            if not upload_path:
                raise ValueError("Job missing upload_path")

            async with async_session_factory() as db:
                stmt_chunks = select(JobChunkProgressModel).where(JobChunkProgressModel.job_id == job_id).order_by(JobChunkProgressModel.chunk_index.asc())
                chunks_res = await db.execute(stmt_chunks)
                existing_chunks = chunks_res.scalars().all()

            chunks_to_process: Sequence[JobChunkProgressModel] = []
            if existing_chunks:
                logger.info("resuming_job_from_existing_chunks job_id=%s chunk_count=%d", job_id, len(existing_chunks))
                chunks_to_process = existing_chunks
            else:
                logger.info("initializing_document_chunks job_id=%s", job_id)
                
                # Download file from R2
                try:
                    file_bytes = await download_file_bytes(upload_path)
                except Exception as e:
                    raise RuntimeError(f"Failed to download object {upload_path} from storage: {e}")
                    
                mimetype = "application/pdf" if file_name.lower().endswith(".pdf") else \
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if file_name.lower().endswith(".docx") else "text/plain"
                           
                full_text = extract_document_text(file_name, mimetype, file_bytes)
                chunk_texts = chunk_document_stream(
                    (t for t in [full_text]),
                    chunk_size_chars=SUMMEREASE_CHUNK_SIZE_CHARS,
                    overlap_chars=SUMMEREASE_CHUNK_OVERLAP_CHARS,
                )
                
                if not chunk_texts:
                    raise ValueError("Could not extract any content from the document file.")

                async with async_session_factory() as db:
                    for idx, text_content in enumerate(chunk_texts):
                        chunk_model = JobChunkProgressModel(
                            id=uuid.uuid4(),
                            job_id=job_id,
                            chunk_index=idx,
                            status="PENDING",
                            summary=text_content,
                        )
                        db.add(chunk_model)
                    await db.commit()

                async with async_session_factory() as db:
                    stmt_chunks = select(JobChunkProgressModel).where(JobChunkProgressModel.job_id == job_id).order_by(JobChunkProgressModel.chunk_index.asc())
                    chunks_res = await db.execute(stmt_chunks)
                    chunks_to_process = chunks_res.scalars().all()

            total_chunks = len(chunks_to_process)
            logger.info("total_chunks_to_process job_id=%s count=%d", job_id, total_chunks)

            for idx, chunk in enumerate(chunks_to_process):
                if chunk.status == "COMPLETED":
                    continue

                logger.info("processing_chunk job_id=%s index=%d/%d", job_id, chunk.chunk_index, total_chunks)
                
                raw_text = chunk.summary or ""
                
                async with async_session_factory() as db:
                    await db.execute(
                        update(JobChunkProgressModel)
                        .where(JobChunkProgressModel.id == chunk.id)
                        .values(status="PROCESSING", updated_at=datetime.now(timezone.utc))
                    )
                    await db.commit()

                # Retry logic for transient Gemini failures is handled inside
                # generate_chunk_summary_single_pass via the AI layer.
                # Permanent failures (400/401/403/404) raise immediately.
                try:
                    result_data = await generate_chunk_summary_single_pass(raw_text, instruction)
                except Exception as exc:
                    logger.error("chunk_failed job_id=%s index=%d err=%s", job_id, chunk.chunk_index, exc)
                    async with async_session_factory() as db:
                        await db.execute(
                            update(JobChunkProgressModel)
                            .where(JobChunkProgressModel.id == chunk.id)
                            .values(
                                status="FAILED",
                                error=str(exc),
                                retry_count=chunk.retry_count + 1,
                                updated_at=datetime.now(timezone.utc),
                            )
                        )
                        await db.commit()
                    raise

                # Update chunk with output on success
                async with async_session_factory() as db:
                    await db.execute(
                        update(JobChunkProgressModel)
                        .where(JobChunkProgressModel.id == chunk.id)
                        .values(
                            status="COMPLETED",
                            summary=result_data["summary"],
                            action_items=result_data["actionItems"],
                            decisions=result_data["decisions"],
                            deadlines=result_data["deadlines"],
                            participants=result_data["participants"],
                            updated_at=datetime.now(timezone.utc),
                        )
                    )
                    await db.commit()

                # Update overall job progress
                completed_count = idx + 1
                progress_pct = int((completed_count / total_chunks) * 90)  # Reserve final 10% for merge stage
                
                async with async_session_factory() as db:
                    await db.execute(
                        update(JobModel)
                        .where(JobModel.id == job_id)
                        .values(
                            progress_percentage=progress_pct,
                            updated_at=datetime.now(timezone.utc),
                        )
                    )
                    await db.commit()

            # 4. Merge results
            logger.info("merging_job_results job_id=%s", job_id)
            
            # Load all completed chunks data
            async with async_session_factory() as db:
                stmt_all_chunks = select(JobChunkProgressModel).where(
                    JobChunkProgressModel.job_id == job_id
                ).order_by(JobChunkProgressModel.chunk_index.asc())
                chunks_res = await db.execute(stmt_all_chunks)
                all_chunks = chunks_res.scalars().all()

            chunk_summaries = [c.summary for c in all_chunks if c.summary]
            chunks_structured = [
                {
                    "participants": c.participants or [],
                    "actionItems": c.action_items or [],
                    "decisions": c.decisions or [],
                    "deadlines": c.deadlines or [],
                }
                for c in all_chunks
            ]

            # Call merge services
            final_summary_text = await merge_chunk_summaries(chunk_summaries, instruction)
            merged_structured = merge_structured_data(chunks_structured)

            # 5. Create final SummaryModel record
            async with async_session_factory() as db:
                summary_record = SummaryModel(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    title=file_name,
                    transcript=None,  # We don't save the raw multi-megabyte transcript in a single row
                    summary=final_summary_text,
                    instruction=instruction,
                    meeting_title=f"Summary of {file_name}",
                    meeting_date=datetime.now(timezone.utc).date(),
                    meeting_type="Large Document",
                    participants=merged_structured["participants"],
                    action_items=merged_structured["actionItems"],
                    decisions=merged_structured["decisions"],
                    deadlines=merged_structured["deadlines"],
                    tags=[],
                )
                db.add(summary_record)
                await db.commit()
                
                # Re-fetch to get id
                summary_id = summary_record.id

            # 6. Complete job & link summary ID
            async with async_session_factory() as db:
                await db.execute(
                    update(JobModel)
                    .where(JobModel.id == job_id)
                    .values(
                        status="COMPLETED",
                        progress_percentage=100,
                        completed_at=datetime.now(timezone.utc),
                        result_summary_id=summary_id,
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()

            logger.info("job_completed_successfully job_id=%s summary_id=%s", job_id, summary_id)
        finally:
            # 7. Always delete object from storage in finally block
            if upload_path:
                try:
                    await delete_file(upload_path)
                    logger.info("temporary_uploaded_file_cleaned path=%s", upload_path)
                    async with async_session_factory() as db:
                        await db.execute(
                            update(JobModel)
                            .where(JobModel.id == job_id)
                            .values(
                                file_deleted_at=datetime.now(timezone.utc),
                                updated_at=datetime.now(timezone.utc),
                            )
                        )
                        await db.commit()
                except Exception:
                    logger.exception("failed_to_delete_upload_file path=%s", upload_path)

    async def _recover_stale_jobs(self) -> None:
        """Finds jobs stuck in PROCESSING for more than 2 hours and resets them to PENDING."""
        stale_threshold = datetime.now(timezone.utc) - timedelta(hours=2)
        logger.info("running_stale_jobs_recovery threshold=%s", stale_threshold)
        
        async with async_session_factory() as db:
            stmt = select(JobModel).where(
                JobModel.status == "PROCESSING",
                JobModel.updated_at < stale_threshold,
            )
            result = await db.execute(stmt)
            stale_jobs = result.scalars().all()

        recovered_count = 0
        for job in stale_jobs:
            logger.warning("recovering_stale_job job_id=%s status=PROCESSING -> PENDING", job.id)
            async with async_session_factory() as db:
                await db.execute(
                    update(JobModel)
                    .where(JobModel.id == job.id)
                    .values(
                        status="PENDING",
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()
            recovered_count += 1
            
        if recovered_count > 0:
            logger.info("stale_jobs_recovery_completed count=%d", recovered_count)
