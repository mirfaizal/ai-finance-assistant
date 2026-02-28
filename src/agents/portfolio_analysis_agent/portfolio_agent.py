"""Core logic for the Portfolio Analysis Agent.

Enhancements
------------
- Pinecone RAG context for diversification frameworks and allocation guidelines.
- LangSmith tracing via @traceable decorator
- Reads SQLite holdings injected by the orchestrator for personalised analysis.
"""

from __future__ import annotations

import json as _json
import re as _re
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

    Accepts two input shapes:

    1. Legacy format (from PortfolioInput UI)::

        {"assets": [{"symbol": "AAPL", "allocation": 0.25}, ...]}

    2. SQLite holdings format (injected by orchestrator via _portfolio_with_holdings)::

        {
            "assets": [],          # always empty in this path
            "question": "...\\n\\nCurrent paper-portfolio holdings from database:\\n[{...}]"
        }

    In case 2 the holdings JSON block is parsed and rendered as a personalised
    prompt so the agent gives specific advice instead of generic guidance.
    """
    assets: list[dict] = portfolio.get("assets", [])
    question: str = portfolio.get("question", "")

    # ── Try to extract SQLite holdings injected into the question string ───────
    sqlite_holdings: list[dict] = []
    holdings_match = _re.search(
        r"Current paper-portfolio holdings from database:\s*(\[.*?\])",
        question,
        _re.S,
    )
    if holdings_match:
        try:
            sqlite_holdings = _json.loads(holdings_match.group(1))
        except Exception:
            pass

    # ── SQLite holdings path — personalised analysis ───────────────────────────
    if sqlite_holdings:
        # Extract just the user's original question (before the injected block)
        user_question = question.split("\n\n")[0].strip()
        lines: list[str] = [
            f"The user's question: {user_question}",
            "",
            "Their actual paper-trading portfolio (from the database):",
        ]
        for h in sqlite_holdings:
            ticker = h.get("ticker", "?")
            shares = h.get("shares", 0)
            avg_cost = h.get("avg_cost", 0)
            lines.append(f"  • {ticker}: {shares} share(s) at average cost ${avg_cost:.2f}")
        lines.append(
            "\nUsing ONLY these actual holdings, provide a personalised educational analysis "
            "that covers:\n"
            "1. Sector/industry concentration (e.g. both stocks in same sector?)\n"
            "2. Missing asset classes (bonds, international, commodities, REITs)\n"
            "3. Specific diversification suggestions with example tickers or ETFs\n"
            "4. Concentration risk given the number and size of positions\n"
            "Do NOT give generic 'from scratch' advice — the user already has real positions. "
            "Reference their specific tickers by name."
        )
        return "\n".join(lines)

    # ── Legacy assets[] path ───────────────────────────────────────────────────
    if not assets:
        return (
            "The user has submitted an empty or unspecified portfolio. "
            "Please provide general educational guidance on how to think about "
            "building a diversified portfolio from scratch."
        )

    lines = ["Portfolio submitted for educational analysis:\n"]
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
        gracefully.  May also contain a ``"question"`` key with SQLite holdings
        injected by the orchestrator for personalised analysis.

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
