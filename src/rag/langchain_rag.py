"""
LangChain RAG Module — `ai-finance-rag` Pinecone Index
=======================================================

Builds a **LangChain ConversationalRetrievalChain** backed by the existing
`ai-finance-rag` Pinecone index so that agents can retrieve grounded context
**and** maintain multi-turn chat history in one call.

Public API
----------
``get_langchain_retriever(k=3)``
    Return a LangChain VectorStoreRetriever that pulls the top-k similar
    chunks from Pinecone.

``get_qa_chain()``
    Return a cached ``ConversationalRetrievalChain`` wired to ChatOpenAI +
    the Pinecone retriever.  Returns ``None`` with a warning log if Pinecone
    or OpenAI credentials are unavailable.

``invoke_chain(question, chat_history)``
    Convenience wrapper: calls ``get_qa_chain()`` and returns a normalised
    ``{"answer": str, "sources": list[str]}`` dict.  Falls back gracefully if
    the chain is not available.

Environment variables required
------------------------------
  PINECONE_API_KEY   — Pinecone API key
  PINECONE_INDEX     — index name (default: "ai-finance-rag")
  OPENAI_API_KEY     — used for ChatOpenAI + OpenAIEmbeddings
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_INDEX = "ai-finance-rag"
_EMBEDDING_MODEL = "text-embedding-ada-002"
_NAMESPACE = "finance-docs"


# ── Lazy vectorstore factory ──────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_vectorstore():
    """
    Build and return a ``langchain_pinecone.PineconeVectorStore`` backed by
    the configured ``ai-finance-rag`` index.

    Returns ``None`` if credentials are missing or packages are not installed.
    """
    try:
        from langchain_openai import OpenAIEmbeddings          # noqa: PLC0415
        from langchain_pinecone import PineconeVectorStore     # noqa: PLC0415
        from pinecone import Pinecone                          # noqa: PLC0415
    except ImportError as exc:
        logger.warning(
            "LangChain RAG: required packages not installed (%s). "
            "Run: pip install langchain langchain-pinecone langchain-openai",
            exc,
        )
        return None

    pinecone_key = os.getenv("PINECONE_API_KEY", "").strip()
    openai_key   = os.getenv("OPENAI_API_KEY", "").strip()
    index_name   = os.getenv("PINECONE_INDEX", _DEFAULT_INDEX).strip()

    if not pinecone_key:
        logger.warning("LangChain RAG: PINECONE_API_KEY not set — RAG chain unavailable.")
        return None
    if not openai_key:
        logger.warning("LangChain RAG: OPENAI_API_KEY not set — RAG chain unavailable.")
        return None

    try:
        pc    = Pinecone(api_key=pinecone_key)
        index = pc.Index(index_name)

        embeddings = OpenAIEmbeddings(
            model=_EMBEDDING_MODEL,
            openai_api_key=openai_key,
        )

        vectorstore = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            namespace=_NAMESPACE,
        )
        logger.info("LangChain RAG: PineconeVectorStore ready (index=%s)", index_name)
        return vectorstore

    except Exception as exc:
        logger.warning("LangChain RAG: failed to build vectorstore — %s", exc)
        return None


# ── Public helpers ────────────────────────────────────────────────────────────

def get_langchain_retriever(k: int = 3):
    """
    Return a LangChain ``VectorStoreRetriever`` for the Pinecone index.

    Parameters
    ----------
    k : int
        Number of top similar chunks to retrieve (default 3).

    Returns
    -------
    VectorStoreRetriever | None
    """
    vectorstore = _get_vectorstore()
    if vectorstore is None:
        return None
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )


@lru_cache(maxsize=1)
def get_qa_chain():
    """
    Build and cache a ``ConversationalRetrievalChain`` from ChatOpenAI +
    the Pinecone retriever.

    The chain is configured with:
    - ``return_source_documents=True``  — callers can surface citations
    - ``verbose=False``                 — keep logs clean

    Returns
    -------
    ConversationalRetrievalChain | None
        ``None`` if the vectorstore or LLM cannot be initialised.
    """
    try:
        from langchain.chains import ConversationalRetrievalChain  # noqa: PLC0415
        from langchain_openai import ChatOpenAI                    # noqa: PLC0415
    except ImportError as exc:
        logger.warning("LangChain RAG: langchain not installed — %s", exc)
        return None

    retriever = get_langchain_retriever(k=3)
    if retriever is None:
        logger.warning("LangChain RAG: retriever unavailable — QA chain not created.")
        return None

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_key:
        logger.warning("LangChain RAG: OPENAI_API_KEY not set — QA chain unavailable.")
        return None

    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=openai_key,
        )

        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            return_source_documents=True,
            verbose=False,
        )
        logger.info("LangChain RAG: ConversationalRetrievalChain created successfully.")
        return qa_chain

    except Exception as exc:
        logger.warning("LangChain RAG: failed to create QA chain — %s", exc)
        return None


def invoke_chain(
    question: str,
    chat_history: list[tuple[str, str]] | None = None,
) -> dict:
    """
    Convenience wrapper around ``get_qa_chain()``.

    Parameters
    ----------
    question : str
        The user's question.
    chat_history : list[tuple[str, str]] | None
        List of ``(human_message, ai_message)`` tuples from prior turns.
        Pass ``[]`` or ``None`` for a fresh conversation.

    Returns
    -------
    dict
        ``{"answer": str, "sources": list[str], "source_documents": list}``
        On error or unavailable chain, returns answer from a best-effort
        fallback with empty sources.

    Examples
    --------
    >>> history = []
    >>> result = invoke_chain("What is an ETF?", history)
    >>> history.append(("What is an ETF?", result["answer"]))
    >>> result2 = invoke_chain("How do they differ from mutual funds?", history)
    """
    if chat_history is None:
        chat_history = []

    qa_chain = get_qa_chain()
    if qa_chain is None:
        logger.warning("LangChain RAG: QA chain not available; returning empty answer.")
        return {"answer": "", "sources": [], "source_documents": []}

    try:
        result = qa_chain.invoke({
            "question": question,
            "chat_history": chat_history,
        })

        answer    = result.get("answer", "")
        source_docs = result.get("source_documents", [])

        sources = []
        for doc in source_docs:
            source_name = doc.metadata.get("source", "Unknown source")
            if source_name not in sources:
                sources.append(source_name)

        logger.info(
            "LangChain RAG: answered question (first 80 chars): %s | sources=%s",
            answer[:80],
            sources,
        )
        return {
            "answer":           answer,
            "sources":          sources,
            "source_documents": source_docs,
        }

    except Exception as exc:
        logger.warning("LangChain RAG: invoke_chain failed — %s", exc)
        return {"answer": "", "sources": [], "source_documents": []}
