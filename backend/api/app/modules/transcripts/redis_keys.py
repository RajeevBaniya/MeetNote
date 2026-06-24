from uuid import UUID


def live_key(meeting_id: UUID) -> str:
    return f"transcript_live:{meeting_id}"


def buffer_key(meeting_id: UUID) -> str:
    return f"transcript_buffer:{meeting_id}"


def chunks_key(meeting_id: UUID) -> str:
    return f"summary_chunks:{meeting_id}"


def chunks_initialized_key(meeting_id: UUID) -> str:
    return f"summary_chunks_initialized:{meeting_id}"


def lock_key(meeting_id: UUID) -> str:
    return f"chunk_lock:{meeting_id}"


def seen_key(meeting_id: UUID) -> str:
    return f"transcript_seen:{meeting_id}"


def speakers_key(meeting_id: UUID) -> str:
    return f"transcript:speakers:{meeting_id}"


def segments_key(meeting_id: UUID) -> str:
    return f"transcript:segments:{meeting_id}"


def left_users_key(meeting_id: UUID) -> str:
    return f"meeting:left_users:{meeting_id}"


def seq_key(meeting_id: UUID) -> str:
    return f"transcript:seq:{meeting_id}"


def correction_queue_key() -> str:
    return "transcript_correction_queue"


def corrected_segments_key(meeting_id: UUID) -> str:
    return f"transcript:corrected_segments:{meeting_id}"
