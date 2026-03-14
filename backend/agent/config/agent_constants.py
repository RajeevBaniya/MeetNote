class AgentConstants:
    SYSTEM_USER_ID: str = "system:assistant"
    SYSTEM_DISPLAY_NAME: str = "Assistant"

    STREAM_CALL_TYPE: str = "default"
    ASSISTANT_ENABLED_KEY_PREFIX: str = "assistant_enabled:"

    JWT_EXPIRY_MINUTES: int = 60
    HTTP_TIMEOUT_SECONDS: float = 5.0
    HTTP_MAX_RETRIES: int = 2

    MIN_QUESTION_LENGTH: int = 3
    MIN_TRANSCRIPT_LENGTH: int = 50
    MAX_QUESTION_LENGTH: int = 200
    MAX_HISTORY_LENGTH: int = 500
    RECENT_TRANSCRIPT_LIMIT: int = 50

