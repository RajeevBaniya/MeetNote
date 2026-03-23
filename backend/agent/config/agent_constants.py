class AgentConstants:
    SYSTEM_USER_ID: str = "system:assistant"
    SYSTEM_DISPLAY_NAME: str = "Assistant"

    STREAM_CALL_TYPE: str = "default"
    ASSISTANT_ENABLED_KEY_PREFIX: str = "assistant_enabled:"
    ASSISTANT_COOLDOWN_KEY_PREFIX: str = "assistant:cooldown:"
    ASSISTANT_LAST_QUESTION_KEY_PREFIX: str = "assistant:last_question:"

    JWT_EXPIRY_MINUTES: int = 60
    HTTP_TIMEOUT_SECONDS: float = 5.0
    HTTP_MAX_RETRIES: int = 2

    MIN_QUESTION_LENGTH: int = 3
    MIN_TRANSCRIPT_LENGTH: int = 50
    MAX_QUESTION_LENGTH: int = 200
    MAX_HISTORY_LENGTH: int = 500
    RECENT_TRANSCRIPT_LIMIT: int = 50
    ASSISTANT_CONTEXT_TRANSCRIPT_SEGMENTS: int = 40

    ASSISTANT_COOLDOWN_SECONDS: int = 5
    ASSISTANT_LAST_QUESTION_TTL_SECONDS: int = 30

    FALLBACK_REPLY_MESSAGE: str = (
        "Sorry, I couldn't process that. Please try again."
    )

