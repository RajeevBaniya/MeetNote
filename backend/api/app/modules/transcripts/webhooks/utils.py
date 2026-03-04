from uuid import UUID


def parse_meeting_id(call_cid: str) -> UUID | None:
    if ":" not in call_cid:
        return None
    _, raw_id = call_cid.split(":", 1)
    try:
        return UUID(raw_id)
    except ValueError:
        return None

