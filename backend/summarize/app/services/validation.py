import os

from app.core.config import SUMMEREASE_MAX_FILE_SIZE, SUMMEREASE_SUPPORTED_EXTENSIONS


class FileValidationError(ValueError):
    """Exception raised when file validation fails (e.g., extension not supported)."""
    pass

class FileSizeLimitError(FileValidationError):
    """Exception raised when file size limit is exceeded."""
    pass

def validate_uploaded_file(filename: str, mimetype: str, size: int) -> None:
    """
    Centralized validation for uploaded files.
    Validates file size and file extension/type.
    """
    # 1. Validate File Size
    if size > SUMMEREASE_MAX_FILE_SIZE:
        max_mb = int(SUMMEREASE_MAX_FILE_SIZE / (1024 * 1024))
        raise FileSizeLimitError(f"File too large. Maximum size: {max_mb}MB")

    # 2. Validate Extension / Type
    _, ext = os.path.splitext(filename.lower())
    if ext not in SUMMEREASE_SUPPORTED_EXTENSIONS:
        allowed_str = ", ".join(SUMMEREASE_SUPPORTED_EXTENSIONS)
        raise FileValidationError(f"Unsupported file type. Allowed: {allowed_str}")
