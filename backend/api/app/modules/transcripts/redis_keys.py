from uuid import UUID


TRANSCRIPT_SEGMENT_THRESHOLD = 500
CHUNK_LOCK_TTL_SECONDS = 60
ACTIVE_MEETING_TTL_SECONDS = 3600
POST_MEETING_TTL_SECONDS = 6 * 60 * 60


def live_key(meeting_id: UUID) -> str:
    return f"transcript_live:{meeting_id}"


def buffer_key(meeting_id: UUID) -> str:
    return f"transcript_buffer:{meeting_id}"


def chunks_key(meeting_id: UUID) -> str:
    return f"summary_chunks:{meeting_id}"


def lock_key(meeting_id: UUID) -> str:
    return f"chunk_lock:{meeting_id}"


def seen_key(meeting_id: UUID) -> str:
    return f"transcript_seen:{meeting_id}"


def segments_key(meeting_id: UUID) -> str:
    return f"transcript:segments:{meeting_id}"


def left_users_key(meeting_id: UUID) -> str:
    return f"meeting:left_users:{meeting_id}"


def seq_key(meeting_id: UUID) -> str:
    return f"transcript:seq:{meeting_id}"
