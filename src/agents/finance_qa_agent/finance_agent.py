"""Core logic for the Finance Q&A Agent.

Enhancements
------------
- Tavily real-time web search for current-affairs / live-data questions
- Pinecone RAG context injection for conceptual / definitional questions
- LangSmith tracing via @traceable decorator
"""

from datetime import date

from .client import get_client, MODEL, TEMPERATURE
from .prompts import SYSTEM_PROMPT
from src.utils.logging import get_logger
from src.utils.tracing import traceable
from src.tools.web_search import web_search, is_realtime_query
from src.rag.retriever import get_rag_context, should_use_rag

logger = get_logger(__name__)


@traceable(name="finance_qa_agent", run_type="chain", tags=["finance", "qa"])
def ask_finance_agent(question: str) -> str:
    """
    Answer a financial education question using:
      1. Tavily web search (if the question needs real-time data)
      2. Pinecone RAG context (if the question is conceptual / definitional)
      3. OpenAI GPT model

    Parameters
    ----------
    question : str
        A financial education question from the user.

    Returns
    -------
    str
        The model's response as plain text.
    """
    if not question or not question.strip():
        raise ValueError("Question must be a non-empty string.")

    logger.info("Finance agent received question: %s", question)

    # ── 1. Real-time context via Tavily ──────────────────────────────────────
    web_context = ""
    if is_realtime_query(question):
        logger.info("Finance agent: triggering Tavily search for real-time data")
        web_context = web_search(question)

    # ── 2. RAG context from Pinecone ─────────────────────────────────────────
    rag_context = ""
    if should_use_rag(question):
        logger.info("Finance agent: fetching RAG context from Pinecone")
        rag_context = get_rag_context(question, top_k=3, agent_filter="finance_qa")

    # ── 3. Build enriched system message ─────────────────────────────────────
    today = date.today().strftime("%B %d, %Y")
    system_content = SYSTEM_PROMPT + f"\n\nToday's date is {today}."
    if rag_context:
        system_content += f"\n\n{rag_context}"
    if web_context:
        system_content += (
            f"\n\n{web_context}"
            "\n\nCRITICAL: The web search results above are live and up-to-date. "
            "You MUST use them as your primary source of truth and answer based on "
            "what they say. Do NOT rely on your training data when web results are "
            "available — training data may be outdated."
        )

    client = get_client()
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": question.strip()},
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
    )

    answer = response.choices[0].message.content
    logger.info("Finance agent returning answer (first 80 chars): %s", answer[:80])
    return answer
