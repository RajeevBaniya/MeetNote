class MeetingChatPermissionError(Exception):
    """Exception raised when a user is not authorized to access the meeting chat."""
    pass


class MeetingChatNotFoundError(Exception):
    """Exception raised when the requested meeting is not found."""
    pass


class MeetingChatUnavailableError(ValueError):
    """Exception raised when chat is not available for the meeting."""
    pass

