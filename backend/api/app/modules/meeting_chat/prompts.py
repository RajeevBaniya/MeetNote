import os
from functools import lru_cache

PROMPTS_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "prompts",
        "meeting_chat"
    )
)


@lru_cache(maxsize=16)
def get_system_prompt() -> str:
    """Load and cache system_prompt.txt content from the prompts directory."""
    path = os.path.join(PROMPTS_DIR, "system_prompt.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
