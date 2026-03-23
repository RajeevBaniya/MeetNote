import string


def normalize_question_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    lowered = text.lower().strip()
    table = str.maketrans("", "", string.punctuation)
    cleaned = lowered.translate(table)
    return " ".join(cleaned.split())
