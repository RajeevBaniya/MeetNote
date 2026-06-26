import asyncio
import json
import logging
import math
import os
import re
from typing import Any

from app.ai.llm_gateway import llm_gateway
from app.core.config import (
    SUMMEREASE_CHARS_PER_TOKEN,
    SUMMEREASE_CHUNK_SUMMARY_MAX_TOKENS,
    SUMMEREASE_DIRECT_SUMMARY_MAX_TOKENS,
    SUMMEREASE_MERGE_GROUP_SIZE,
    SUMMEREASE_MERGE_INPUT_TOKEN_THRESHOLD,
    SUMMEREASE_MERGE_MAX_TOKENS,
)

logger = logging.getLogger(__name__)

PROMPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
)


def get_prompt_template(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


async def call_gemini_api(prompt: str, max_tokens: int) -> str:
    return await llm_gateway.generate_content(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.7,
        timeout=60.0,
    )


async def call_gemini_api_json(prompt: str, max_tokens: int) -> str:
    return await llm_gateway.generate_content(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.2,
        timeout=90.0,
    )


async def generate_summary(transcript: str, instruction: str) -> str:
    """Generate a prose summary of a document or transcript."""
    template = get_prompt_template("default_summary_prompt.txt")
    prompt = template.format(instruction=instruction, transcript=transcript)

    try:
        return await call_gemini_api(prompt, max_tokens=SUMMEREASE_DIRECT_SUMMARY_MAX_TOKENS)
    except Exception as exc:
        logger.error("summary_generation_failed err=%s", exc, exc_info=exc)
        raise RuntimeError("Failed to generate summary") from exc


async def extract_structured_data(transcript: str, instruction: str) -> dict[str, Any]:
    """Extract action items, decisions, deadlines, and participants from a document."""
    template = get_prompt_template("extract_structured_prompt.txt")
    prompt = template.format(transcript=transcript, instruction=instruction)

    try:
        response_text = await call_gemini_api_json(
            prompt, max_tokens=SUMMEREASE_CHUNK_SUMMARY_MAX_TOKENS
        )
        return parse_structured_response(response_text)
    except Exception as exc:
        logger.error("structured_extraction_failed err=%s", exc, exc_info=exc)
        return get_empty_structured_data()


def parse_structured_response(response: str) -> dict[str, Any]:
    """Parse a JSON payload from a raw LLM response string."""
    try:
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

    await asyncio.sleep(1.0)
    structured_data = await extract_structured_data(transcript, instruction)

    return summary_text, structured_data


async def generate_chunk_summary_single_pass(
    transcript: str, instruction: str
) -> dict[str, Any]:
    """Generate a summary and extract structured data from one document section."""
    template = get_prompt_template("chunk_summary_prompt.txt")
    prompt = template.format(instruction=instruction, transcript=transcript)

    response_text = await call_gemini_api_json(
        prompt, max_tokens=SUMMEREASE_CHUNK_SUMMARY_MAX_TOKENS
    )
    match = re.search(r"\{[\s\S]*\}", response_text)
    json_str = match.group(0) if match else response_text
    parsed = json.loads(json_str)
    return {
        "summary": parsed.get("summary") or "No summary generated for this section.",
        "actionItems": parsed.get("actionItems") if isinstance(parsed.get("actionItems"), list) else [],
        "decisions": parsed.get("decisions") if isinstance(parsed.get("decisions"), list) else [],
        "deadlines": parsed.get("deadlines") if isinstance(parsed.get("deadlines"), list) else [],
        "participants": parsed.get("participants") if isinstance(parsed.get("participants"), list) else [],
    }


def _estimate_tokens(text: str) -> int:
    """Estimate token count using the configured chars-per-token approximation."""
    return len(text) // SUMMEREASE_CHARS_PER_TOKEN


def _build_merge_prompt(
    summaries: list[str],
    instruction: str,
    is_final_level: bool,
) -> str:
    """Build a merge prompt for the given group of summaries."""
    chunk_count = len(summaries)
    numbered = "\n\n".join(
        [f"Section {i + 1} Summary:\n{s}" for i, s in enumerate(summaries)]
    )

    if is_final_level:
        merge_level_note = (
            "This is the final consolidation pass. "
            "Produce the complete, comprehensive final output that a reader would use as the definitive summary of the document."
        )
    else:
        merge_level_note = (
            "This is an intermediate consolidation pass covering a subset of the document. "
            "Preserve every specific fact, name, number, date, decision, risk, and obligation — "
            "this output will be consolidated again with other sections in a subsequent pass."
        )

    template = get_prompt_template("merge_summary_prompt.txt")
    return template.format(
        chunk_count=chunk_count,
        instruction=instruction,
        merge_level_note=merge_level_note,
        summaries=numbered,
    )


async def _merge_group(
    summaries: list[str],
    instruction: str,
    is_final_level: bool,
) -> str:
    """Execute one merge call for a group of summaries."""
    prompt = _build_merge_prompt(summaries, instruction, is_final_level)
    return await call_gemini_api(prompt, max_tokens=SUMMEREASE_MERGE_MAX_TOKENS)


async def merge_chunk_summaries(summaries: list[str], instruction: str) -> str:
    """
    Hierarchically merge chunk summaries until one final summary remains.

    Algorithm:
    1. Estimate total input tokens for a flat merge of all summaries.
    2. If the estimate fits within SUMMEREASE_MERGE_INPUT_TOKEN_THRESHOLD, merge in one call.
    3. Otherwise, split into groups of SUMMEREASE_MERGE_GROUP_SIZE, merge each group
       independently (intermediate pass), then recurse on the results.

    This produces a dynamic recursion depth — one level for small documents,
    multiple levels for documents with hundreds of chunks. No fixed depth is assumed.
    """
    if not summaries:
        return ""

    if len(summaries) == 1:
        return summaries[0]

    estimated_input_tokens = _estimate_tokens(" ".join(summaries))

    total_groups = math.ceil(len(summaries) / SUMMEREASE_MERGE_GROUP_SIZE)
    fits_in_one_call = estimated_input_tokens <= SUMMEREASE_MERGE_INPUT_TOKEN_THRESHOLD

    if fits_in_one_call:
        logger.info(
            "merge_single_pass summary_count=%d estimated_tokens=%d",
            len(summaries),
            estimated_input_tokens,
        )
        return await _merge_group(summaries, instruction, is_final_level=True)

    logger.info(
        "merge_hierarchical summary_count=%d estimated_tokens=%d groups=%d",
        len(summaries),
        estimated_input_tokens,
        total_groups,
    )

    level_results: list[str] = []
    for group_index in range(0, len(summaries), SUMMEREASE_MERGE_GROUP_SIZE):
        group = summaries[group_index: group_index + SUMMEREASE_MERGE_GROUP_SIZE]
        merged = await _merge_group(group, instruction, is_final_level=False)
        level_results.append(merged)
        logger.info(
            "merge_group_complete group=%d/%d size=%d",
            group_index // SUMMEREASE_MERGE_GROUP_SIZE + 1,
            total_groups,
            len(group),
        )

    return await merge_chunk_summaries(level_results, instruction)


def merge_structured_data(chunks_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge and deduplicate structured data from multiple document sections."""
    merged: dict[str, Any] = {
        "actionItems": [],
        "decisions": [],
        "deadlines": [],
        "participants": set(),
    }

    seen_tasks: set[str] = set()
    seen_decisions: set[str] = set()
    seen_deadlines: set[str] = set()

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
