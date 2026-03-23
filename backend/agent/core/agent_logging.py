import logging
from typing import List


class _AgentLogFilter(logging.Filter):
    BENIGN_ERROR_PATTERNS: List[str] = [
        "Already subscribed to track",
        "Timeout waiting for pending track",
        "TimeoutError",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno != logging.ERROR:
            return True

        msg = record.getMessage() or ""

        if any(pattern in msg for pattern in self.BENIGN_ERROR_PATTERNS):
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"

        if (
            "Error calling handler" in msg
            and "stream_edge_transport" in msg
            and "TrackPublished" in msg
        ):
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"

        return True


def install_agent_log_filters() -> None:
    target_loggers = [
        "vision_agents.core.events.manager",
        "getstream.video.rtc.tracks",
    ]

    for logger_name in target_loggers:
        log = logging.getLogger(logger_name)
        log.addFilter(_AgentLogFilter())
