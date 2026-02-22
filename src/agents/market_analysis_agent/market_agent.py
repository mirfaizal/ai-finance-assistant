"""Core logic for the Market Analysis Agent.

Enhancements
------------
- Tavily web search: live index levels, sector moves, macro data.
- LangSmith tracing via @traceable decorator
"""

from __future__ import annotations

from typing import Any

from .client import get_client, MODEL, TEMPERATURE
from .prompts import SYSTEM_PROMPT
from src.utils.logging import get_logger
from src.utils.tracing import traceable
from src.tools.web_search import web_search, is_realtime_query

logger = get_logger(__name__)


def _build_market_prompt(data: dict[str, Any] | None) -> str:
    """
    Convert optional market data into a human-readable prompt.

    Accepts an optional dict with any of the following keys (all optional):
    - ``question``   : str  — a free-text market question
    - ``indices``    : list — e.g. [{"name": "S&P 500", "value": 5200, "change_pct": -0.5}]
    - ``sectors``    : list — e.g. [{"name": "Technology", "change_pct": 1.2}]
    - ``macro``      : dict — e.g. {"inflation": "3.2%", "fed_rate": "5.25%"}
    """
    if not data:
        return (
            "The user did not provide specific market data. "
            "Please provide a general educational overview of current market concepts, "
            "key indices, sector dynamics, and macroeconomic factors that typically "
            "influence financial markets."
        )

    lines: list[str] = ["Market data submitted for educational analysis:\n"]

    if question := data.get("question"):
        lines.append(f"User question: {question}\n")

    if indices := data.get("indices"):
        lines.append("Indices:")
        for idx in indices:
            name = idx.get("name", "Unknown")
            value = idx.get("value", "N/A")
            chg = idx.get("change_pct", "N/A")
            lines.append(f"  • {name}: {value}  ({chg}%)")
        lines.append("")

    if sectors := data.get("sectors"):
        lines.append("Sector performance:")
        for sector in sectors:
            name = sector.get("name", "Unknown")
            chg = sector.get("change_pct", "N/A")
            lines.append(f"  • {name}: {chg}%")
        lines.append("")

    if macro := data.get("macro"):
        lines.append("Macroeconomic indicators:")
        for k, v in macro.items():
            lines.append(f"  • {k}: {v}")
        lines.append("")

    lines.append(
        "Provide a general educational analysis covering: market trends, sector "
        "dynamics, macroeconomic context, and any notable observations. "
        "Do not give personalised investment advice."
    )
    return "\n".join(lines)


@traceable(name="market_analysis_agent", run_type="chain", tags=["market"])
def analyze_market(data: dict[str, Any] | None = None) -> str:
    """
    Provide a general educational analysis of market conditions.

    If the question (or data dict) requests live / current information,
    Tavily automatically fetches real-time market data before the LLM call.

    Parameters
    ----------
    data : dict | None
        Optional market data dict.  All keys are optional:
        ``question``, ``indices``, ``sectors``, ``macro``.
        Pass ``None`` or an empty dict for a general market overview.

    Returns
    -------
    str
        Educational market analysis as plain text.

    Raises
    ------
    TypeError
        If *data* is provided but is not a dict.
    """
    if data is not None and not isinstance(data, dict):
        raise TypeError(f"data must be a dict or None, got {type(data).__name__!r}.")

    user_prompt = _build_market_prompt(data)
    logger.info("Market agent analysing data keys: %s", list(data.keys()) if data else [])

    # ── Real-time market data via Tavily ──────────────────────────────────────────
    web_context = ""
    question = (data or {}).get("question", "")
    if question and is_realtime_query(question):
        logger.info("Market agent: triggering Tavily search for live market data")
        web_context = web_search(f"{question} stock market", max_results=4)
    elif not data:   # general overview — always fetch a fresh market snapshot
        web_context = web_search("stock market overview today S&P 500 performance", max_results=3)

    system_content = SYSTEM_PROMPT
    if web_context:
        system_content += f"\n\n{web_context}\n\nUse the above real-time data in your analysis."

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
    logger.info("Market agent answer (first 80 chars): %s", answer[:80])
    return answer
