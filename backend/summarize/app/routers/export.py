import re
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.middleware.auth import get_current_user_id
from app.services.summaries import get_summary_by_id
from app.services.exporter import generate_pdf, generate_docx

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/pdf/{id}")
async def export_pdf(
    id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> Response:
    """Export meeting summary details as a formatted PDF file."""
    try:
        summary = await get_summary_by_id(db, id, current_user_id)
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this summary.",
            )
            
        summary_data = {
            "meetingTitle": summary.meeting_title,
            "meetingDate": summary.meeting_date,
            "meetingType": summary.meeting_type,
            "participants": summary.participants or [],
            "location": summary.location,
            "tags": summary.tags or [],
            "summary": summary.summary,
            "actionItems": summary.action_items or [],
            "decisions": summary.decisions or [],
            "deadlines": summary.deadlines or [],
            "extractedParticipants": summary.extracted_participants or [],
        }
        
        pdf_bytes = generate_pdf(summary_data)
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Generated PDF is empty or invalid",
            )
            
        meeting_title = summary.meeting_title or "Meeting-Notes"
        clean_title = re.sub(r'[^a-zA-Z0-9\s-]', '', meeting_title)
        clean_title = re.sub(r'[\s-]+', '-', clean_title).strip('-')
        if not clean_title:
            clean_title = "Meeting-Notes"
            
        date_str = "unknown"
        if summary.meeting_date:
            date_str = summary.meeting_date.strftime("%Y-%m-%d")
            
        filename = f"{clean_title}-Summary-{date_str}.pdf"
        
        headers = {
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
        }
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers=headers,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(exc)}",
        )


@router.get("/word/{id}")
async def export_word(
    id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> Response:
    """Export meeting summary details as a formatted Word (.docx) file."""
    try:
        summary = await get_summary_by_id(db, id, current_user_id)
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this summary.",
            )
            
        summary_data = {
            "meetingTitle": summary.meeting_title,
            "meetingDate": summary.meeting_date,
            "meetingType": summary.meeting_type,
            "participants": summary.participants or [],
            "location": summary.location,
            "tags": summary.tags or [],
            "summary": summary.summary,
            "actionItems": summary.action_items or [],
            "decisions": summary.decisions or [],
            "deadlines": summary.deadlines or [],
            "extractedParticipants": summary.extracted_participants or [],
        }
        
        word_bytes = generate_docx(summary_data)
        if not word_bytes or len(word_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Generated Word document is empty or invalid",
            )
            
        meeting_title = summary.meeting_title or "Meeting-Notes"
        clean_title = re.sub(r'[^a-zA-Z0-9\s-]', '', meeting_title)
        clean_title = re.sub(r'[\s-]+', '-', clean_title).strip('-')
        if not clean_title:
            clean_title = "Meeting-Notes"
            
        date_str = "unknown"
        if summary.meeting_date:
            date_str = summary.meeting_date.strftime("%Y-%m-%d")
            
        filename = f"{clean_title}-Summary-{date_str}.docx"
        
        headers = {
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
        }
        return Response(
            content=word_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Word document: {str(exc)}",
        )

