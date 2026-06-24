from collections.abc import Generator


def chunk_document_stream(
    text_generator: Generator[str, None, None],
    chunk_size_chars: int = 1000000,
    overlap_chars: int = 100000,
) -> list[str]:
    """
    Groups streamed text sections into chunks of approx chunk_size_chars,
    maintaining overlap_chars between consecutive chunks.
    
    Args:
        text_generator: Generator yielding strings.
        chunk_size_chars: Target character size for chunks (~250,000 tokens).
        overlap_chars: Overlap character size between chunks (~25,000 tokens).
        
    Returns:
        List of chunk strings.
    """
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len: int = 0

    for segment in text_generator:
        if not segment:
            continue

        # Safe split of large segments if they exceed chunk_size_chars
        sub_segments: list[str] = []
        if len(segment) > chunk_size_chars:
            lines = segment.splitlines(keepends=True)
            temp_seg: list[str] = []
            temp_len: int = 0
            for line in lines:
                if temp_len + len(line) > chunk_size_chars:
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

                # Overlap calculation
                overlap_text = chunk_text[-overlap_chars:] if len(chunk_text) > overlap_chars else chunk_text
                current_chunk = [overlap_text, sub_seg]
                current_len = len(overlap_text) + sub_len
            else:
                current_chunk.append(sub_seg)
                current_len += sub_len

    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks
