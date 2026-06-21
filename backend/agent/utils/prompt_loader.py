import os

PROMPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
)


def get_agent_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Agent prompt template file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()
