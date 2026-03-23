from agent.utils.question_normalization import normalize_question_text


def clean_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    cleaned = text.strip()
    if not cleaned:
        return ""
    return cleaned


__all__ = ["clean_text", "normalize_question_text"]

