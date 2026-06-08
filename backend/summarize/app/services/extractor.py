import io
import os
from abc import ABC, abstractmethod
from pypdf import PdfReader
import mammoth

SUPPORTED_EXTENSIONS = [".txt", ".pdf", ".docx"]
SUPPORTED_MIME_TYPES = [
    "text/plain",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class BaseDocumentExtractor(ABC):
    """Abstract base class to allow modular swapping of parsing engines."""

    @abstractmethod
    def extract(self, file_bytes: bytes) -> str:
        """Parse raw document file bytes and return extracted string text."""
        pass


class PDFDocumentExtractor(BaseDocumentExtractor):
    """PDF text extractor using pypdf."""

    def extract(self, file_bytes: bytes) -> str:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text_list = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_list.append(page_text)
            return "\n".join(text_list).strip()
        except Exception as exc:
            raise ValueError(f"Failed to parse PDF file: {str(exc)}") from exc


class DocxDocumentExtractor(BaseDocumentExtractor):
    """Word DOCX text extractor using mammoth."""

    def extract(self, file_bytes: bytes) -> str:
        try:
            result = mammoth.extract_raw_text(io.BytesIO(file_bytes))
            return result.value.strip()
        except Exception as exc:
            raise ValueError(f"Failed to parse DOCX file: {str(exc)}") from exc


class PlainTextDocumentExtractor(BaseDocumentExtractor):
    """Plain text decoder."""

    def extract(self, file_bytes: bytes) -> str:
        try:
            return file_bytes.decode("utf-8", errors="ignore").strip()
        except Exception as exc:
            raise ValueError(f"Failed to parse text file: {str(exc)}") from exc


def get_extractor(filename: str, mimetype: str) -> BaseDocumentExtractor | None:
    """Return appropriate extractor instance based on file extensions or mimetypes."""
    name_lower = filename.lower()
    _, ext = os.path.splitext(name_lower)
    
    if ext == ".pdf" or mimetype == "application/pdf":
        return PDFDocumentExtractor()
    elif ext == ".docx" or mimetype == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return DocxDocumentExtractor()
    elif ext == ".txt" or mimetype == "text/plain":
        return PlainTextDocumentExtractor()
        
    return None


def extract_document_text(filename: str, mimetype: str, file_bytes: bytes) -> str:
    """Validate and extract raw transcript text from uploaded document files."""
    # Validate File Size
    if len(file_bytes) > MAX_FILE_SIZE:
        max_mb = int(MAX_FILE_SIZE / (1024 * 1024))
        raise ValueError(f"File too large. Maximum size: {max_mb}MB")
        
    # Validate File Type
    extractor = get_extractor(filename, mimetype)
    if not extractor:
        allowed_str = ", ".join(SUPPORTED_EXTENSIONS)
        raise ValueError(f"Unsupported file type. Allowed: {allowed_str}")
        
    text = extractor.extract(file_bytes)
    
    if not text or len(text.strip()) == 0:
        raise ValueError("Could not extract text from file. The file may be empty or corrupted.")
        
    return text
