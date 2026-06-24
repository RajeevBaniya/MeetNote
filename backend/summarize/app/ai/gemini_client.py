import logging

import httpx

logger = logging.getLogger(__name__)


class GeminiClient:
    """Standardized client for Google Gemini API content generation."""

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
        """Call native Google Gemini API generateContent endpoint."""
        # Align URL structure with the appropriate API version
        if "beta" in self.model_name or "gemini-1.5" in self.model_name or "1.5" in self.model_name:
            base_url = "https://generativelanguage.googleapis.com/v1beta"
        else:
            base_url = "https://generativelanguage.googleapis.com/v1"

        url = f"{base_url}/models/{self.model_name}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("No generation candidates returned from Gemini")
        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        if not parts:
            raise RuntimeError("No text parts returned from Gemini")

        return str(parts[0].get("text") or "").strip()
