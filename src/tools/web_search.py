"""
Tavily Web Search Tool

Provides real-time web search capability to all agents via the Tavily API.
Used for current affairs, today's news, live stock prices, economic data, etc.

Usage
-----
    from src.tools.web_search import web_search, is_realtime_query

    if is_realtime_query(question):
        context = web_search(question)

Graceful degradation
--------------------
If TAVILY_API_KEY is not set, or the tavily-python package is missing,
every call returns an empty string and logs a warning — agents continue
to answer from the LLM's training knowledge without crashing.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
_MAX_RESULTS = 5
_SEARCH_DEPTH = "basic"      # "basic" (faster) | "advanced" (deeper, costs more)
_MAX_CONTENT_CHARS = 500     # truncate each result's content snippet

# Keywords that signal the user likely needs fresh / real-time information.
_REALTIME_SIGNALS = [
    "today", "current", "latest", "right now", "this week",
    "this month", "this year", "2024", "2025", "2026",
    "who is", "who leads", "president", "prime minister",
    "price of", "stock price", "what is the rate", "rate today",
    "inflation today", "fed rate", "interest rate today",
    "market today", "s&p today", "nasdaq today", "dow today",
    "breaking", "recent", "news", "headline", "just announced",
    "earnings today", "ipo today",
]


# ── Client factory (cached) ─────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_tavily_client():
    """Return a cached TavilyClient.  Raises clear errors on misconfiguration."""
    try:
        from tavily import TavilyClient  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "tavily-python is not installed. "
            "Run: pip install 'tavily-python>=0.3.0'"
        ) from exc

    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "TAVILY_API_KEY is not set. "
            "Add it to your .env file:  TAVILY_API_KEY=tvly-..."
        )
    return TavilyClient(api_key=api_key)


# ── Public helpers ──────────────────────────────────────────────────────────────

def web_search(
    query: str,
    max_results: int = _MAX_RESULTS,
    search_depth: str = _SEARCH_DEPTH,
) -> str:
    """
    Search the web using Tavily and return a formatted context string.

    The returned string is designed to be injected directly into an LLM
    system or user prompt as grounding context.

    Parameters
    ----------
    query : str
        Search query, e.g. "Who is the current US president?" or
        "S&P 500 closing price today".
    max_results : int
        Maximum number of results to include (default 5).
    search_depth : str
        "basic" (fast, cheaper) or "advanced" (deeper, costs more API credits).

    Returns
    -------
    str
        Formatted search results, or an empty string if Tavily is unavailable
        or the search fails (agents fall back to LLM training knowledge).
    """
    if not query or not query.strip():
        return ""

    try:
        client = _get_tavily_client()
        response = client.search(
            query=query.strip(),
            search_depth=search_depth,
            max_results=max_results,
        )

        results = response.get("results", [])
        if not results:
            logger.info("Tavily: no results for query=%s", query[:60])
            return ""

        lines: list[str] = [
            f"[Real-time web search results for: «{query}»]\n"
        ]
        for i, r in enumerate(results, start=1):
            title   = r.get("title", "No title").strip()
            url     = r.get("url", "").strip()
            content = r.get("content", "").strip()
            if len(content) > _MAX_CONTENT_CHARS:
                content = content[:_MAX_CONTENT_CHARS] + " … [truncated]"
            lines.append(f"[{i}] {title}")
            if url:
                lines.append(f"    Source: {url}")
            if content:
                lines.append(f"    {content}")
            lines.append("")

        result_text = "\n".join(lines)
        logger.info(
            "Tavily: returned %d results for query=%s", len(results), query[:60]
        )
        return result_text

    except EnvironmentError:
        # API key not configured — degrade gracefully
        logger.warning(
            "Tavily API key not configured; skipping real-time search. "
            "Set TAVILY_API_KEY in .env to enable live data."
        )
        return ""
    except Exception as exc:
        logger.warning("Tavily search failed [query=%s]: %s", query[:60], exc)
        return ""


def is_realtime_query(question: str) -> bool:
    """
    Return True if the question likely requires up-to-date / live information.

    Used by agents to decide whether to trigger a Tavily search before
    forwarding the question to the LLM.

    Examples that return True
    -------------------------
    - "Who is the president of the USA?"
    - "What is the S&P 500 today?"
    - "Latest inflation numbers"
    - "Breaking financial news"
    """
    q = question.lower()
    return any(signal in q for signal in _REALTIME_SIGNALS)


def finance_search(topic: str, context_hint: str = "") -> str:
    """
    Convenience wrapper: build a finance-focused Tavily query and search.

    Parameters
    ----------
    topic : str
        High-level topic to search (e.g. "S&P 500 performance today").
    context_hint : str
        Optional extra context to sharpen the query (e.g. "macro economics").

    Returns
    -------
    str
        Formatted search results or empty string.
    """
    query = f"{topic} {context_hint} finance".strip() if context_hint else topic
    return web_search(query, max_results=3)
