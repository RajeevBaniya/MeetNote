from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class TranscriptEntry:
    speaker: str
    text: str
    timestamp: Optional[Any] = None
