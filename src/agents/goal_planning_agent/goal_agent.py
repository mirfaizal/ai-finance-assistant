"""Core logic for the Goal Planning Agent.

Enhancements
------------
- Pinecone RAG context for goal-planning frameworks and budgeting strategies.
- LangSmith tracing via @traceable decorator
"""

from __future__ import annotations

from typing import Any

from .client import get_client, MODEL, TEMPERATURE
from .prompts import SYSTEM_PROMPT
from src.utils.logging import get_logger
from src.utils.tracing import traceable
from src.rag.retriever import get_rag_context, should_use_rag

logger = get_logger(__name__)


def _build_goals_prompt(goals: dict[str, Any]) -> str:
    """
    Convert a goals dict into a human-readable prompt.

    Accepted keys (all optional):
    - ``question``       : str  — free-text goal question
    - ``goals``          : list — e.g. [{"name": "Emergency fund", "timeline": "1 year", "amount": 10000}]
    - ``income``         : str  — described income level (e.g. "mid-range", "$80k/year")
    - ``time_horizon``   : str  — overall planning horizon (e.g. "10 years")
    - ``current_savings``: str  — general savings description
    """
    if not goals:
        return (
            "The user has not provided specific goal details. "
            "Please provide general educational guidance on how to think about "
            "setting financial goals, budgeting, building an emergency fund, "
            "and planning for retirement."
        )

    lines: list[str] = ["Financial goals submitted for educational guidance:\n"]

    if question := goals.get("question"):
        lines.append(f"User question: {question}\n")

    if goal_list := goals.get("goals"):
        lines.append("Goals:")
        for g in goal_list:
            name = g.get("name", "Unnamed goal")
            timeline = g.get("timeline", "unspecified timeline")
            amount = g.get("amount")
            amt_str = f"  target: ${amount:,.0f}" if amount else ""
            lines.append(f"  • {name} — {timeline}{amt_str}")
        lines.append("")

    for key, label in [
        ("income", "Income level"),
        ("current_savings", "Current savings"),
        ("time_horizon", "Overall time horizon"),
    ]:
        if val := goals.get(key):
            lines.append(f"{label}: {val}")

    lines.append(
        "\nProvide general educational guidance on goal prioritisation, budgeting "
        "frameworks, saving strategies, and relevant planning concepts. "
        "Do not give personalised financial advice."
    )
    return "\n".join(lines)


@traceable(name="goal_planning_agent", run_type="chain", tags=["goals"])
def plan_goals(goals: dict[str, Any]) -> str:
    """
    Provide general educational guidance based on user-supplied financial goals.

    Parameters
    ----------
    goals : dict
        A dict describing the user's financial goals.  All keys are optional
        (``question``, ``goals``, ``income``, ``time_horizon``, ``current_savings``).
        An empty dict triggers a general educational overview.

    Returns
    -------
    str
        Educational goal-planning guidance as plain text.

    Raises
    ------
    TypeError
        If *goals* is not a dict.
    """
    if not isinstance(goals, dict):
        raise TypeError(f"goals must be a dict, got {type(goals).__name__!r}.")

    user_prompt = _build_goals_prompt(goals)
    logger.info("Goal agent processing goals dict with keys: %s", list(goals.keys()))

    # ── RAG context for budgeting / goal-planning frameworks ──────────────────────
    question = goals.get("question", user_prompt[:200])
    rag_context = get_rag_context(question, top_k=3, agent_filter="goal_planning")
    system_content = SYSTEM_PROMPT + (f"\n\n{rag_context}" if rag_context else "")

    client = get_client()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ],
        temperature=TEMPERATURE,
    )

    answer = response.choices[0].message.content
    logger.info("Goal agent answer (first 80 chars): %s", answer[:80])
    return answer
