from collections.abc import Generator

from app.core.config import SUMMEREASE_CHUNK_OVERLAP_CHARS, SUMMEREASE_CHUNK_SIZE_CHARS


def chunk_document_stream(
    text_generator: Generator[str, None, None],
    chunk_size_chars: int = SUMMEREASE_CHUNK_SIZE_CHARS,
    overlap_chars: int = SUMMEREASE_CHUNK_OVERLAP_CHARS,
) -> list[str]:
    """
    Split a stream of text sections into overlapping chunks sized for the AI pipeline.

    Chunk size and overlap are derived from token targets defined in config.py using
    a character-per-token approximation (default: 4 chars/token for English prose).
    When a model-specific tokenizer becomes available, update SUMMEREASE_CHARS_PER_TOKEN
    and SUMMEREASE_CHUNK_TARGET_TOKENS in config.py — this function requires no changes.

    Args:
        text_generator: Generator yielding strings (document sections or full text).
        chunk_size_chars: Maximum characters per chunk. Defaults to config value.
        overlap_chars: Characters shared between consecutive chunks. Defaults to config value.

    Returns:
        List of chunk strings in document order.
    """
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len: int = 0

    for segment in text_generator:
        if not segment:
            continue

        sub_segments: list[str] = []
        if len(segment) > chunk_size_chars:
            lines = segment.splitlines(keepends=True)
            temp_seg: list[str] = []
            temp_len: int = 0
            for line in lines:
                if len(line) > chunk_size_chars:
                    if temp_seg:
                        sub_segments.append("".join(temp_seg))
                        temp_seg = []
                        temp_len = 0
                    for i in range(0, len(line), chunk_size_chars):
                        sub_segments.append(line[i : i + chunk_size_chars])
                elif temp_len + len(line) > chunk_size_chars:
                    if temp_seg:
                        sub_segments.append("".join(temp_seg))
                    temp_seg = [line]
                    temp_len = len(line)
                else:
                    temp_seg.append(line)
                    temp_len += len(line)
            if temp_seg:
                sub_segments.append("".join(temp_seg))
        else:
            sub_segments = [segment]

        for sub_seg in sub_segments:
            sub_len = len(sub_seg)
            if current_len + sub_len > chunk_size_chars and current_chunk:
                chunk_text = "".join(current_chunk)
                chunks.append(chunk_text)

                overlap_text = (
                    chunk_text[-overlap_chars:]
                    if len(chunk_text) > overlap_chars
                    else chunk_text
                )
                current_chunk = [overlap_text, sub_seg]
                current_len = len(overlap_text) + sub_len
            else:
                current_chunk.append(sub_seg)
                current_len += sub_len

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks
