import os
import re
import json
import logging
import asyncio
from typing import Any
from app.core.config import GEMINI_API_KEY_SUMMEREASE, GEMINI_MODEL_SUMMEREASE
from app.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


async def call_gemini_api(prompt: str, max_tokens: int = 1000) -> str:
    """Invoke native Google Gemini API with the provided prompt."""
    api_key = GEMINI_API_KEY_SUMMEREASE
    model_name = GEMINI_MODEL_SUMMEREASE
    client = GeminiClient(api_key, model_name)
    return await client.generate_content(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.7,
        timeout=30.0,
    )


async def generate_summary(transcript: str, instruction: str) -> str:
    """Invoke Gemini LLM API to generate a summary of the transcript."""
    template = get_prompt_template("default_summary_prompt.txt")
    prompt = template.format(instruction=instruction, transcript=transcript)
    
    try:
        return await call_gemini_api(
            prompt=prompt,
            max_tokens=1000,
        )
    except Exception as exc:
        logger.error("Gemini summary generation failed: %s", exc, exc_info=exc)
        raise RuntimeError("Failed to generate summary") from exc


async def extract_structured_data(transcript: str) -> dict[str, Any]:
    """Invoke Gemini LLM API to extract action items, decisions, deadlines, and participants."""
    template = get_prompt_template("extract_structured_prompt.txt")
    prompt = template.format(transcript=transcript)
    
    try:
        response_text = await call_gemini_api(
            prompt=prompt,
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
    summary_text = await generate_summary(transcript, instruction)
    
    if not extract_structured:
        return summary_text, get_empty_structured_data()
        
    # Introduce 1-second delay to avoid parallel request rate-limiting on Gemini key
    await asyncio.sleep(1.0)
    structured_data = await extract_structured_data(transcript)
    
    return summary_text, structured_data


PROMPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
)


def get_prompt_template(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


async def call_gemini_api_json(prompt: str, max_tokens: int = 2500) -> str:
    """Invoke native Google Gemini API requesting application/json response."""
    api_key = GEMINI_API_KEY_SUMMEREASE
    model_name = GEMINI_MODEL_SUMMEREASE
    client = GeminiClient(api_key, model_name)
    return await client.generate_content(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.2,
        timeout=60.0,
    )


async def generate_chunk_summary_single_pass(transcript: str, instruction: str) -> dict[str, Any]:
    """Generate summary and extract structured data in a single pass to save API cost and latency."""
    template = get_prompt_template("chunk_summary_prompt.txt")
    prompt = template.format(instruction=instruction, transcript=transcript)
    
    response_text = await call_gemini_api_json(prompt, max_tokens=2500)
    match = re.search(r"\{[\s\S]*\}", response_text)
    json_str = match.group(0) if match else response_text
    parsed = json.loads(json_str)
    return {
        "summary": parsed.get("summary") or "No summary generated for this chunk.",
        "actionItems": parsed.get("actionItems") if isinstance(parsed.get("actionItems"), list) else [],
        "decisions": parsed.get("decisions") if isinstance(parsed.get("decisions"), list) else [],
        "deadlines": parsed.get("deadlines") if isinstance(parsed.get("deadlines"), list) else [],
        "participants": parsed.get("participants") if isinstance(parsed.get("participants"), list) else [],
    }


async def merge_chunk_summaries(summaries: list[str], instruction: str) -> str:
    """Merge multiple chunk summaries into a final coherent summary."""
    joined_summaries = "\n\n".join(
        [f"Chunk {i+1} Summary:\n{s}" for i, s in enumerate(summaries)]
    )
    template = get_prompt_template("merge_summary_prompt.txt")
    prompt = template.format(instruction=instruction, summaries=joined_summaries)
    
    try:
        return await call_gemini_api(prompt, max_tokens=2500)
    except Exception as exc:
        logger.error("Failed to merge chunk summaries: %s", exc, exc_info=exc)
        return "\n\n".join(summaries)


def merge_structured_data(chunks_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Merges and deduplicates structured data arrays from multiple chunks."""
    merged: dict[str, Any] = {
        "actionItems": [],
        "decisions": [],
        "deadlines": [],
        "participants": set(),
    }
    
    seen_tasks = set()
    seen_decisions = set()
    seen_deadlines = set()
    
    for data in chunks_data:
        for p in data.get("participants", []):
            if isinstance(p, str) and p.strip():
                merged["participants"].add(p.strip())
                
        for item in data.get("actionItems", []):
            if not isinstance(item, dict):
                continue
            task = item.get("task", "")
            if not task:
                continue
            task_clean = task.strip().lower()
            if task_clean not in seen_tasks:
                seen_tasks.add(task_clean)
                merged["actionItems"].append({
                    "task": task.strip(),
                    "assignee": item.get("assignee"),
                    "dueDate": item.get("dueDate"),
                })
                
        for dec in data.get("decisions", []):
            if not isinstance(dec, dict):
                continue
            decision = dec.get("decision", "")
            if not decision:
                continue
            dec_clean = decision.strip().lower()
            if dec_clean not in seen_decisions:
                seen_decisions.add(dec_clean)
                merged["decisions"].append({
                    "decision": decision.strip(),
                    "context": dec.get("context"),
                })
                
        for dl in data.get("deadlines", []):
            if not isinstance(dl, dict):
                continue
            item_desc = dl.get("item", "")
            if not item_desc:
                continue
            dl_clean = item_desc.strip().lower()
            if dl_clean not in seen_deadlines:
                seen_deadlines.add(dl_clean)
                merged["deadlines"].append({
                    "item": item_desc.strip(),
                    "date": dl.get("date"),
                    "owner": dl.get("owner"),
                })
                
    return {
        "actionItems": merged["actionItems"],
        "decisions": merged["decisions"],
        "deadlines": merged["deadlines"],
        "participants": sorted(list(merged["participants"])),
    }

