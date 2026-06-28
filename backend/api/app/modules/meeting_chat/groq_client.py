import logging
import httpx

from app.modules.meeting_chat.llm_providers import register_llm_provider

logger = logging.getLogger(__name__)


class GroqClient:
    """Standardized client for Groq API completion generation."""

    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("api_key must not be empty")
        self.api_key = api_key.strip()
        self.model_name = model_name.strip()

    async def generate_content(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: float = 30.0,
    ) -> str:
        """Call native Groq chat completions endpoint."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("No choices returned from Groq")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if content is None:
            raise RuntimeError("No text returned from Groq")

        return str(content).strip()


register_llm_provider("groq", GroqClient)
