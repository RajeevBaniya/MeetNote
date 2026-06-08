from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.middleware.auth import get_current_user_id
from app.db.session import get_session
from app.schemas.summary import SummaryGenerateRequest, SummaryGenerateResponse, StructuredData
from app.ai.groq import generate_meeting_summary
from app.services.summaries import save_summary

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.post("/generate", response_model=SummaryGenerateResponse)
async def generate(
    request: SummaryGenerateRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
) -> SummaryGenerateResponse:
    """Generate summary text and structured fields from meeting transcript."""
    if not request.transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcript is required",
        )
    if not request.instruction.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instruction is required",
        )
        
    try:
        # TODO: Implement full LLM client execution inside the AI service.
        # This calls the AI service boundary.
        should_extract = request.extractStructured is not False
        summary_text, structured = await generate_meeting_summary(
            transcript=request.transcript,
            instruction=request.instruction,
            extract_structured=should_extract,
        )
        
        saved_id: UUID | None = None
        if request.persist is not False:
            # TODO: Implement db insert inside summaries service.
            # This calls the summaries service boundary.
            saved = await save_summary(
                session=db,
                user_id=current_user_id,
                transcript=request.transcript,
                summary=summary_text,
                instruction=request.instruction,
                title=request.title,
                meeting_title=request.meetingTitle,
                meeting_date=request.meetingDate,  # Parsed inside service
                meeting_type=request.meetingType,
                participants=request.participants,
                location=request.location,
                tags=request.tags,
                action_items=structured.get("actionItems"),
                decisions=structured.get("decisions"),
                deadlines=structured.get("deadlines"),
                extracted_participants=structured.get("participants"),
                meeting_id=request.meetingId,
            )
            saved_id = saved.id if saved else None
            
        return SummaryGenerateResponse(
            success=True,
            summary=summary_text,
            structured=StructuredData(
                actionItems=structured.get("actionItems", []),
                decisions=structured.get("decisions", []),
                deadlines=structured.get("deadlines", []),
                participants=structured.get("participants", []),
            ),
            savedId=saved_id,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(exc)}",
        )
