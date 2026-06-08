from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
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
        # TODO: Implement full file size validation and parsing logic inside extractor service.
        # This calls the extractor service boundary.
        extracted_content = extract_document_text(
            filename=transcript.filename,
            mimetype=transcript.content_type or "",
            file_bytes=content_bytes,
        )
        
        # Helper to get file type matching Express getFileType
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
