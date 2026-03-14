def clean_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    cleaned = text.strip()
    if not cleaned:
        return ""
    return cleaned

