"""
Memory Synthesizer Agent

Compresses a conversation history list into a rolling plain-text summary.
Called by the orchestrator when session turn-count exceeds a threshold (default 5).

Usage
-----
    from src.agents.memory_synthesizer_agent import synthesize_memory

    summary = synthesize_memory(history)
    # history is a list of {"role": "user"|"assistant", "content": "..."}
"""
from __future__ import annotations

from typing import List, Dict

from src.utils.logging import get_logger
from src.utils.tracing import traceable
from .client import get_client, MODEL, TEMPERATURE
from .prompts import SYSTEM_PROMPT

logger = get_logger(__name__)


def _format_history_for_synthesis(history: List[Dict[str, str]]) -> str:
    """Format history into a readable transcript for the LLM."""
    lines = []
    for entry in history:
        role = entry.get("role", "unknown").capitalize()
        # Skip previously compressed summary rows — include them as-is at the top
        if entry.get("role") == "summary":
            lines.append(f"[Previous summary]: {entry['content']}")
        else:
            lines.append(f"{role}: {entry['content']}")
    return "\n".join(lines)


@traceable(name="memory_synthesizer_agent", run_type="chain", tags=["memory", "synthesizer"])
def synthesize_memory(history: List[Dict[str, str]]) -> str:
    """
    Compress *history* into a concise memory summary paragraph.

    Parameters
    ----------
    history : list of {"role": str, "content": str}
        The conversation turns to compress. Typically the last 10+ messages.

    Returns
    -------
    str
        A 2–4 sentence plain-text memory summary.
    """
    if not history:
        return ""

    if len(history) < 2:
        # Nothing meaningful to compress
        return history[0].get("content", "")

    logger.info("Memory synthesizer: compressing %d history entries", len(history))

    transcript = _format_history_for_synthesis(history)
    user_prompt = f"Please summarise this conversation history:\n\n{transcript}"

    client = get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=TEMPERATURE,
        max_tokens=400,
    )

    summary = response.choices[0].message.content.strip()
    logger.info("Memory synthesizer: produced %d-char summary", len(summary))
    return summary
