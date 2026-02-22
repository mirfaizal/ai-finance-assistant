"""
RAG Retriever

High-level interface for retrieving document context from Pinecone before
passing a query to the LLM.  Agents call ``get_rag_context()`` and receive
a ready-to-inject prompt string.

Graceful degradation: if Pinecone is not configured the function returns an
empty string and the agent answers from the LLM's training knowledge alone.
"""

from __future__ import annotations

from .pinecone_store import query_similar
from src.utils.logging import get_logger

logger = get_logger(__name__)

_SCORE_THRESHOLD = 0.75     # ignore low-relevance matches
_MAX_CONTEXT_CHARS = 2000   # total context budget injected into prompts


def get_rag_context(
    query: str,
    top_k: int = 3,
    agent_filter: str | None = None,
    score_threshold: float = _SCORE_THRESHOLD,
) -> str:
    """
    Retrieve relevant document chunks from Pinecone and format them as a
    grounding context string ready to be injected into an LLM prompt.

    Parameters
    ----------
    query : str
        The user's question.
    top_k : int
        Maximum number of chunks to include (default 3).
    agent_filter : str | None
        If provided, filters results to chunks tagged with this agent name
        (e.g. ``"finance_qa"``).  Uses Pinecone metadata filter
        ``{"agent": agent_filter}``.
    score_threshold : float
        Minimum similarity score to include a chunk (0–1, default 0.75).

    Returns
    -------
    str
        Formatted RAG context string, or "" if nothing relevant is found.

    Example return value
    --------------------
    [Retrieved knowledge base context]

    [1] (score: 0.91) An ETF (Exchange-Traded Fund) is a type of investment
        fund that is traded on stock exchanges, much like stocks...
        Source: finance-basics | etf-101

    [2] (score: 0.83) Index funds track a market index such as the S&P 500...
    """
    if not query or not query.strip():
        return ""

    filter_meta = {"agent": agent_filter} if agent_filter else None
    matches = query_similar(
        query_text=query,
        top_k=top_k,
        filter_metadata=filter_meta,
    )

    # Filter by score threshold
    relevant = [m for m in matches if m["score"] >= score_threshold]
    if not relevant:
        logger.debug("RAG: no matches above threshold %.2f for query=%s", score_threshold, query[:60])
        return ""

    lines: list[str] = ["[Retrieved knowledge base context]\n"]
    total_chars = 0

    for i, match in enumerate(relevant, start=1):
        text     = (match["text"] or "").strip()
        score    = match["score"]
        meta     = match.get("metadata", {})
        source   = meta.get("source", "—")
        doc_id   = match.get("id", "—")

        # Respect context budget
        if total_chars >= _MAX_CONTEXT_CHARS:
            break
        remaining = _MAX_CONTEXT_CHARS - total_chars
        if len(text) > remaining:
            text = text[:remaining] + " … [truncated]"

        lines.append(f"[{i}] (score: {score:.2f}) {text}")
        lines.append(f"    Source: {source} | {doc_id}")
        lines.append("")
        total_chars += len(text)

    context = "\n".join(lines)
    logger.info(
        "RAG: injecting %d chunk(s) (%d chars) for query=%s",
        len(relevant), total_chars, query[:60]
    )
    return context


def should_use_rag(question: str) -> bool:
    """
    Heuristic: return True if the question is likely to benefit from RAG
    (i.e. it asks for conceptual / definitional knowledge that may be in
    the knowledge base, but is NOT obviously a real-time query).

    Examples that return True
    -------------------------
    - "What is the difference between a Roth and Traditional IRA?"
    - "Explain dollar-cost averaging"
    - "How does compound interest work?"
    """
    q = question.lower()
    # Skip RAG for real-time signals (Tavily handles those)
    realtime_signals = ["today", "current price", "latest", "right now", "breaking"]
    if any(s in q for s in realtime_signals):
        return False
    # Trigger RAG for conceptual / definitional questions
    rag_signals = [
        "what is", "what are", "explain", "define", "how does", "how do",
        "difference between", "compare", "meaning of", "tell me about",
        "describe", "overview", "example of", "why is", "why do",
    ]
    return any(s in q for s in rag_signals)
