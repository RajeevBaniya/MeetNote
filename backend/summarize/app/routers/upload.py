import os
import uuid
import anyio
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.auth import get_current_user_id
from app.db.session import get_session
from app.core.config import get_upload_dir
from app.db.models import JobModel
from app.services.extractor import extract_document_text

router = APIRouter(prefix="/api/upload", tags=["upload"])


class UploadResponse(BaseModel):
    message: str
    content: str
    fileType: str
    originalName: str


@router.post("", response_model=UploadResponse)
async def upload_transcript(
    transcript: UploadFile = File(..., alias="transcript"),
) -> UploadResponse:
    """Upload and extract text transcript from .txt, .pdf, or .docx file."""
    if not transcript or not transcript.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded",
        )
    
    try:
        content_bytes = await transcript.read()
        extracted_content = extract_document_text(
            filename=transcript.filename,
            mimetype=transcript.content_type or "",
            file_bytes=content_bytes,
        )
        
        ext = transcript.filename.split(".")[-1].lower() if "." in transcript.filename else ""
        file_type = "unknown"
        if ext == "txt":
            file_type = "text"
        elif ext in ("pdf", "docx"):
            file_type = ext
            
        return UploadResponse(
            message="File uploaded successfully",
            content=extracted_content or "",
            fileType=file_type,
            originalName=transcript.filename,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/stream")
async def upload_stream(
    transcript: UploadFile = File(..., alias="transcript"),
    instruction: str = Query(default="Summarize the key points and action items."),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
):
    """Stream upload file to local disk and initialize an async processing job."""
    if not transcript or not transcript.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded",
        )
    
    job_id = uuid.uuid4()
    upload_dir = get_upload_dir()
    file_path = os.path.join(upload_dir, f"{job_id}.tmp")
    
    try:
        file_size = 0
        async with await anyio.open_file(file_path, "wb") as f:
            while True:
                chunk = await transcript.read(65536)  # 64KB blocks
                if not chunk:
                    break
                file_size += len(chunk)
                await f.write(chunk)
                
        # Validate supported format
        ext = os.path.splitext(transcript.filename.lower())[1]
        if ext not in (".txt", ".pdf", ".docx"):
            if os.path.exists(file_path):
                os.remove(file_path)
            raise ValueError("Unsupported file type. Allowed: .txt, .pdf, .docx")
            
        new_job = JobModel(
            id=job_id,
            user_id=current_user_id,
            status="PENDING",
            progress_percentage=0,
            file_name=transcript.filename,
            file_size=file_size,
            file_path=file_path,
            upload_path=file_path,
            instruction=instruction,
        )
        db.add(new_job)
        await db.commit()
        
        return {
            "jobId": str(job_id),
            "status": "PENDING",
            "progressPercentage": 0,
            "fileName": transcript.filename,
            "fileSize": file_size,
        }
    except ValueError as val_err:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload stream failed: {str(exc)}",
        )

