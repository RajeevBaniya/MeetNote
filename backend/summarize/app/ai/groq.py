import re
import json
import httpx
import logging
from typing import Any
from app.core.config import get_groq_api_key, get_groq_model

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def call_groq_api(messages: list[dict[str, str]], max_tokens: int = 1000) -> str:
    """Invoke Groq LLM API with the provided messages payload."""
    api_key = get_groq_api_key()
    model_name = get_groq_model()
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(GROQ_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
    return str(data["choices"][0]["message"]["content"])


async def generate_summary(transcript: str, instruction: str) -> str:
    """Invoke Groq LLM API to generate a summary of the transcript."""
    prompt = (
        f"{instruction}\n\n"
        f"Here is the meeting transcript to summarize:\n\n"
        f"{transcript}\n\n"
        f"Please provide a well-structured summary based on the instruction above."
    ).strip()
    
    try:
        return await call_groq_api(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
    except Exception as exc:
        logger.error("Groq summary generation failed: %s", exc, exc_info=exc)
        raise RuntimeError("Failed to generate summary") from exc


async def extract_structured_data(transcript: str) -> dict[str, Any]:
    """Invoke Groq LLM API to extract action items, decisions, deadlines, and participants."""
    prompt = (
        "Analyze the following meeting transcript and extract structured information.\n"
        "Return ONLY a valid JSON object with no additional text or explanation.\n\n"
        "The JSON must have this exact structure:\n"
        "{\n"
        '  "actionItems": [\n'
        '    { "task": "string", "assignee": "string or null", "dueDate": "string or null" }\n'
        "  ],\n"
        '  "decisions": [\n'
        '    { "decision": "string", "context": "string or null" }\n'
        "  ],\n"
        '  "deadlines": [\n'
        '    { "item": "string", "date": "string", "owner": "string or null" }\n'
        "  ],\n"
        '  "participants": ["string"]\n'
        "}\n\n"
        "If no items found for a category, return an empty array.\n"
        "Extract participant names from the transcript based on who spoke or was mentioned.\n\n"
        f"Meeting transcript:\n{transcript}"
    ).strip()
    
    try:
        response_text = await call_groq_api(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
        )
        return parse_structured_response(response_text)
    except Exception as exc:
        logger.error("Structured extraction failed: %s", exc, exc_info=exc)
        return get_empty_structured_data()


def parse_structured_response(response: str) -> dict[str, Any]:
    """Parse JSON payload out of the raw LLM completions text block."""
    try:
        # Regex matching first '{' to last '}' to extract raw JSON
        match = re.search(r"\{[\s\S]*\}", response)
        if not match:
            return get_empty_structured_data()
            
        parsed = json.loads(match.group(0))
        return {
            "actionItems": parsed.get("actionItems") if isinstance(parsed.get("actionItems"), list) else [],
            "decisions": parsed.get("decisions") if isinstance(parsed.get("decisions"), list) else [],
            "deadlines": parsed.get("deadlines") if isinstance(parsed.get("deadlines"), list) else [],
            "participants": parsed.get("participants") if isinstance(parsed.get("participants"), list) else [],
        }
    except Exception:
        return get_empty_structured_data()


def get_empty_structured_data() -> dict[str, Any]:
    """Return default empty keys for structured response items."""
    return {
        "actionItems": [],
        "decisions": [],
        "deadlines": [],
        "participants": [],
    }


async def generate_meeting_summary(
    transcript: str,
    instruction: str,
    extract_structured: bool = True,
) -> tuple[str, dict[str, Any]]:
    """Generate summary text and optional structured fields from raw meeting transcript."""
    import asyncio
    
    summary_task = generate_summary(transcript, instruction)
    
    if not extract_structured:
        summary_text = await summary_task
        return summary_text, get_empty_structured_data()
        
    structured_task = extract_structured_data(transcript)
    
    summary_text, structured_data = await asyncio.gather(
        summary_task,
        structured_task,
    )
    
    return summary_text, structured_data
