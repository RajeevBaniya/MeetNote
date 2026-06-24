import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import delete_file, upload_file_bytes
from app.db.models import JobModel
from app.db.session import get_session
from app.middleware.auth import get_current_user_id
from app.services.extractor import extract_document_text
from app.services.validation import (
    FileSizeLimitError,
    FileValidationError,
    validate_uploaded_file,
)

router = APIRouter(prefix="/api/upload", tags=["upload"])


class UploadResponse(BaseModel):
    message: str
    content: str
    fileType: str
    originalName: str


class UploadConfigResponse(BaseModel):
    maxFileSize: int
    supportedExtensions: list[str]


@router.get("/config", response_model=UploadConfigResponse)
async def get_upload_config() -> UploadConfigResponse:
    """Retrieve the maximum upload file size and allowed extensions."""
    from app.core.config import (
        SUMMEREASE_MAX_FILE_SIZE,
        SUMMEREASE_SUPPORTED_EXTENSIONS,
    )
    return UploadConfigResponse(
        maxFileSize=SUMMEREASE_MAX_FILE_SIZE,
        supportedExtensions=SUMMEREASE_SUPPORTED_EXTENSIONS,
    )


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
        file_size = len(content_bytes)

        # 1. Strict validation of actual read byte size
        validate_uploaded_file(transcript.filename, transcript.content_type or "", file_size)

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
    except FileSizeLimitError as size_err:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(size_err),
        )
    except (FileValidationError, ValueError) as val_err:
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
    """Stream upload file and initialize an async processing job."""
    if not transcript or not transcript.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded",
        )

    job_id = uuid.uuid4()
    object_name = f"uploads/{job_id}.tmp"

    try:
        file_bytes = await transcript.read()
        file_size = len(file_bytes)

        # 1. Strict validation of actual read byte size
        validate_uploaded_file(transcript.filename, transcript.content_type or "", file_size)

        # 2. Only upload and create database entry after size validation passes
        await upload_file_bytes(file_bytes, object_name)

        new_job = JobModel(
            id=job_id,
            user_id=current_user_id,
            status="PENDING",
            progress_percentage=0,
            file_name=transcript.filename,
            file_size=file_size,
            file_path=object_name,
            upload_path=object_name,
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
    except FileSizeLimitError as size_err:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(size_err),
        )
    except (FileValidationError, ValueError) as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        try:
            await delete_file(object_name)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload stream failed: {str(exc)}",
        )
