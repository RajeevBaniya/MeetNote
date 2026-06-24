from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobChunkProgressModel, JobModel
from app.db.session import get_session
from app.middleware.auth import get_current_user_id

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobStatusResponse(BaseModel):
    jobId: str = Field(..., serialization_alias="jobId")
    status: str
    progressPercentage: int = Field(..., serialization_alias="progressPercentage")
    currentStage: str = Field(..., serialization_alias="currentStage")
    totalChunks: int = Field(..., serialization_alias="totalChunks")
    completedChunks: int = Field(..., serialization_alias="completedChunks")
    estimatedRemainingChunks: int = Field(..., serialization_alias="estimatedRemainingChunks")
    failureReason: str | None = Field(..., serialization_alias="failureReason")
    resultSummaryId: str | None = Field(None, serialization_alias="resultSummaryId")

    class Config:
        populate_by_name = True


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> Any:
    """Retrieve the progress and status metadata of an active asynchronous job."""
    # Query job details
    stmt = select(JobModel).where(
        JobModel.id == job_id,
        JobModel.user_id == current_user_id,
    )
    result = await db.execute(stmt)
    job = result.scalars().first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Calculate chunk metadata
    stmt_chunks = select(
        func.count(JobChunkProgressModel.id),
        func.count(JobChunkProgressModel.id).filter(JobChunkProgressModel.status == "COMPLETED")
    ).where(JobChunkProgressModel.job_id == job_id)

    chunks_result = await db.execute(stmt_chunks)
    total_chunks, completed_chunks = chunks_result.one()

    # Map stage strings
    status_lower = job.status.lower()
    current_stage = status_lower

    estimated_remaining = max(0, total_chunks - completed_chunks)

    return {
        "jobId": str(job.id),
        "status": job.status,
        "progressPercentage": job.progress_percentage,
        "currentStage": current_stage,
        "totalChunks": total_chunks,
        "completedChunks": completed_chunks,
        "estimatedRemainingChunks": estimated_remaining,
        "failureReason": job.failure_reason,
        "resultSummaryId": str(job.result_summary_id) if job.result_summary_id else None,
    }
