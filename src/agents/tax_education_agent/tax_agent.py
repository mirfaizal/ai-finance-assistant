"""Core logic for the Tax Education Agent.

Enhancements
------------
- Pinecone RAG context for tax law, IRS rules, and deduction frameworks.
- LangSmith tracing via @traceable decorator
"""

from __future__ import annotations

from .client import get_client, MODEL, TEMPERATURE
from .prompts import SYSTEM_PROMPT
from src.utils.logging import get_logger
from src.utils.tracing import traceable
from src.rag.retriever import get_rag_context, should_use_rag

logger = get_logger(__name__)


@traceable(name="tax_education_agent", run_type="chain", tags=["tax"])
def explain_tax_concepts(query: str) -> str:
    """
    Explain general tax concepts based on the user's question.

    Parameters
    ----------
    query : str
        A tax-related educational question (e.g. "What is the difference between
        a tax deduction and a tax credit?").

    Returns
    -------
    str
        Educational explanation as plain text.

    Raises
    ------
    ValueError
        If *query* is empty or whitespace-only.
    TypeError
        If *query* is not a string.
    """
    if not isinstance(query, str):
        raise TypeError(f"query must be a str, got {type(query).__name__!r}.")
    if not query.strip():
        raise ValueError("query must be a non-empty string.")

    logger.info("Tax agent received query: %s", query[:80])

    # ── RAG context for tax law and IRS rules ──────────────────────────────────────
    rag_context = get_rag_context(query, top_k=3, agent_filter="tax_education")
    system_content = SYSTEM_PROMPT + (f"\n\n{rag_context}" if rag_context else "")

    client = get_client()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": query.strip()},
        ],
        temperature=TEMPERATURE,
    )

    answer = response.choices[0].message.content
    logger.info("Tax agent answer (first 80 chars): %s", answer[:80])
    return answer
