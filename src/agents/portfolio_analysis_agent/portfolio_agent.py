"""Core logic for the Portfolio Analysis Agent.

Enhancements
------------
- Pinecone RAG context for diversification frameworks and allocation guidelines.
- LangSmith tracing via @traceable decorator
"""

from __future__ import annotations

from typing import Any

from .client import get_client, MODEL, TEMPERATURE
from .prompts import SYSTEM_PROMPT
from src.utils.logging import get_logger
from src.utils.tracing import traceable
from src.rag.retriever import get_rag_context

logger = get_logger(__name__)

# Maximum total allocation deviation allowed before we warn in the prompt
_ALLOCATION_WARN_THRESHOLD = 0.05


def _build_portfolio_prompt(portfolio: dict[str, Any]) -> str:
    """
    Convert a portfolio dict into a human-readable prompt string.

    Expected input shape::

        {
            "assets": [
                {"symbol": "AAPL", "allocation": 0.25},
                {"symbol": "VTI",  "allocation": 0.40},
                {"symbol": "BND",  "allocation": 0.35},
            ]
        }

    The function is intentionally lenient — it handles missing keys and partial
    data gracefully so the agent can still provide educational feedback.
    """
    assets: list[dict] = portfolio.get("assets", [])

    if not assets:
        return (
            "The user has submitted an empty or unspecified portfolio. "
            "Please provide general educational guidance on how to think about "
            "building a diversified portfolio from scratch."
        )

    lines: list[str] = ["Portfolio submitted for educational analysis:\n"]

    total_allocation = 0.0
    for item in assets:
        symbol = item.get("symbol") or item.get("name") or "Unknown"
        allocation = item.get("allocation")

        if allocation is None:
            lines.append(f"  • {symbol}: allocation not specified")
        else:
            try:
                pct = float(allocation) * 100
                lines.append(f"  • {symbol}: {pct:.1f}%")
                total_allocation += float(allocation)
            except (TypeError, ValueError):
                lines.append(f"  • {symbol}: invalid allocation value ({allocation!r})")

    lines.append(f"\nTotal declared allocation: {total_allocation * 100:.1f}%")

    if abs(total_allocation - 1.0) > _ALLOCATION_WARN_THRESHOLD and total_allocation > 0:
        lines.append(
            f"Note: allocations sum to {total_allocation * 100:.1f}%, "
            "not 100% — please factor this into the analysis."
        )

    lines.append(
        "\nProvide a general educational analysis covering: "
        "asset-class diversification, concentration risk, inferred risk profile, "
        "and any notable observations. Do not give personalised investment advice."
    )

    return "\n".join(lines)


@traceable(name="portfolio_analysis_agent", run_type="chain", tags=["portfolio"])
def analyze_portfolio(portfolio: dict[str, Any]) -> str:
    """
    Send a portfolio for general educational analysis.

    Parameters
    ----------
    portfolio : dict
        A dictionary describing the portfolio.  Must contain an ``"assets"`` key
        with a list of holdings, each having at least a ``"symbol"`` and an
        ``"allocation"`` (float, 0–1).  Missing or partial data is handled
        gracefully.

    Returns
    -------
    str
        The model's educational analysis as plain text.

    Raises
    ------
    TypeError
        If *portfolio* is not a dict.
    """
    if not isinstance(portfolio, dict):
        raise TypeError(f"portfolio must be a dict, got {type(portfolio).__name__!r}.")

    user_prompt = _build_portfolio_prompt(portfolio)
    logger.info("Portfolio agent analysing portfolio with %d asset(s).", len(portfolio.get("assets", [])))

    # ── RAG context for diversification / allocation frameworks ───────────────────
    question = portfolio.get("question", "portfolio diversification and risk")
    rag_context = get_rag_context(question, top_k=3, agent_filter="portfolio_analysis")
    system_content = SYSTEM_PROMPT + (f"\n\n{rag_context}" if rag_context else "")

    client = get_client()

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_prompt},
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
    )

    answer = response.choices[0].message.content
    logger.info("Portfolio agent returning analysis (first 80 chars): %s", answer[:80])
    return answer
