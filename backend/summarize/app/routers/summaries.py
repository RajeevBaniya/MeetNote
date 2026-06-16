from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.middleware.auth import get_current_user_id
from app.db.session import get_session
from app.schemas.summary import (
    SummaryListResponse,
    SummaryDetailResponse,
    DeleteResponse,
    SummaryUpdateRequest,
    SummaryResponse,
)
from app.services.summaries import (
    list_summaries,
    get_summary_by_id,
    update_summary,
    delete_summary,
)

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


@router.get("", response_model=SummaryListResponse)
async def get_all_summaries(
    skip: int = 0,
    take: int = 20,
    search: str = "",
    dateFrom: str | None = None,
    dateTo: str | None = None,
    meetingType: str | None = None,
    meetingId: UUID | None = None,
    uploadOnly: bool = False,
    tags: list[str] = Query(default=[]),
    sortBy: str = "created_at",
    sortOrder: str = "desc",
    current_user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> SummaryListResponse:
    """Retrieve and filter saved summaries for the current user."""
    try:
        # Parse dates if supplied
        parsed_date_from: date | None = None
        parsed_date_to: date | None = None
        if dateFrom:
            parsed_date_from = date.fromisoformat(dateFrom)
        if dateTo:
            parsed_date_to = date.fromisoformat(dateTo)
            
        # TODO: Implement database search logic in summaries service.
        # This calls the summaries query service.
        items = await list_summaries(
            session=db,
            user_id=current_user_id,
            skip=skip,
            take=take,
            search=search,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            meeting_type=meetingType,
            meeting_id=meetingId,
            upload_only=uploadOnly,
            tags=tags,
            sort_by=sortBy,
            sort_order=sortOrder,
        )
        items_validated = [SummaryResponse.model_validate(item) for item in items] if items else []
        return SummaryListResponse(success=True, items=items_validated)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list summaries: {str(exc)}",
        )


@router.get("/{id}", response_model=SummaryDetailResponse)
async def get_summary(
    id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> SummaryDetailResponse:
    """Retrieve details of a specific saved summary by ID."""
    try:
        item = await get_summary_by_id(db, id, current_user_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found",
            )
        return SummaryDetailResponse(success=True, item=SummaryResponse.model_validate(item))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get summary: {str(exc)}",
        )


@router.put("/{id}", response_model=SummaryDetailResponse)
async def update_saved_summary(
    id: UUID,
    request: SummaryUpdateRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> SummaryDetailResponse:
    """Update details of a saved summary."""
    try:
        # Filter request body to only allowed fields matching Express PUT filter
        raw_data = request.model_dump(exclude_unset=True)
        
        updated = await update_summary(db, id, current_user_id, raw_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found",
            )
        return SummaryDetailResponse(success=True, item=SummaryResponse.model_validate(updated))
    except HTTPException:
        raise
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update summary: {str(exc)}",
        )


@router.delete("/{id}", response_model=DeleteResponse)
async def delete_saved_summary(
    id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> DeleteResponse:
    """Delete a saved summary from Postgres."""
    try:
        # TODO: Implement db delete in summaries service.
        ok = await delete_summary(db, id, current_user_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found",
            )
        return DeleteResponse(success=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete summary: {str(exc)}",
        )
