"""
Pinecone Vector Store Wrapper

Handles:
  - Connecting to a Pinecone index
  - Generating OpenAI embeddings for documents / queries
  - Upserting document chunks into the index
  - Querying for top-k relevant chunks

The index is expected to exist in Pinecone already.  Use the
``upsert_documents()`` function to populate it from any text source.

Environment variables required
-------------------------------
  PINECONE_API_KEY   — your Pinecone API key
  PINECONE_INDEX     — name of the Pinecone index (default: "ai-finance-rag")
  OPENAI_API_KEY     — used for generating text-embedding-ada-002 embeddings

Graceful degradation
--------------------
If either key is missing or the pinecone / openai packages are not installed,
every call returns an empty result and logs a warning.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)

# ── Defaults ────────────────────────────────────────────────────────────────────
_DEFAULT_INDEX = "ai-finance-rag"
_EMBEDDING_MODEL = "text-embedding-ada-002"
_EMBEDDING_DIM = 1536          # ada-002 dimension
_TOP_K_DEFAULT = 3
_NAMESPACE = "finance-docs"    # Pinecone namespace


# ── Lazy client factories ────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_pinecone_index():
    """Return a connected Pinecone Index object (cached)."""
    try:
        from pinecone import Pinecone  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "pinecone package is not installed. "
            "Run: pip install 'pinecone>=3.0.0'"
        ) from exc

    api_key = os.getenv("PINECONE_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "PINECONE_API_KEY is not set. Add it to your .env file."
        )

    index_name = os.getenv("PINECONE_INDEX", _DEFAULT_INDEX).strip()
    pc = Pinecone(api_key=api_key)

    try:
        index = pc.Index(index_name)
        logger.info("Connected to Pinecone index: %s", index_name)
        return index
    except Exception as exc:
        # Try to create the index if it does not exist (best-effort).
        logger.info("Pinecone index '%s' not found; attempting to create it.", index_name)
        # Try several call signatures to handle different pinecone SDK versions.
        creation_errors = []
        try:
            # Preferred new-style call: name + dimension + metric + spec
            spec = {"serverless": {}}
            pc.create_index(index_name, dimension=_EMBEDDING_DIM, metric="cosine", spec=spec)
            index = pc.Index(index_name)
            logger.info("Created and connected to Pinecone index (signature A): %s", index_name)
            return index
        except Exception as exc_a:
            creation_errors.append(exc_a)
        try:
            # Older style: positional dimension then spec
            spec = {"serverless": {}}
            pc.create_index(index_name, _EMBEDDING_DIM, spec)
            index = pc.Index(index_name)
            logger.info("Created and connected to Pinecone index (signature B): %s", index_name)
            return index
        except Exception as exc_b:
            creation_errors.append(exc_b)
        try:
            # Fallback: minimal create (some SDKs accept name+dimension only)
            pc.create_index(index_name, _EMBEDDING_DIM)
            index = pc.Index(index_name)
            logger.info("Created and connected to Pinecone index (signature C): %s", index_name)
            return index
        except Exception as exc_c:
            creation_errors.append(exc_c)

        # If we reach here, all creation attempts failed; show the first underlying error.
        logger.warning("Pinecone index creation attempts failed: %s", creation_errors[0])
        raise ConnectionError(
            f"Could not connect to or create Pinecone index '{index_name}'. "
            "Ensure PINECONE_INDEX is correct, your Pinecone API key has project access, "
            "and your Pinecone project supports creating indexes via the API. "
            "See logs for details."
        ) from creation_errors[0]


@lru_cache(maxsize=1)
def _get_embedding_client():
    """Return an OpenAI client for generating embeddings (cached)."""
    try:
        from openai import OpenAI  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("openai package is not installed.") from exc

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


# ── Embedding helper ─────────────────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """
    Generate an embedding vector for *text* using OpenAI ada-002.

    Parameters
    ----------
    text : str
        Text to embed (will be truncated at 8 000 chars if too long).

    Returns
    -------
    list[float]
        1 536-dimensional embedding vector.
    """
    text = text.strip()[:8000]   # ada-002 token limit safety
    client = _get_embedding_client()
    response = client.embeddings.create(
        model=_EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


# ── Upsert ────────────────────────────────────────────────────────────────────────

def upsert_documents(
    documents: list[dict],
    namespace: str = _NAMESPACE,
) -> int:
    """
    Embed and upsert a list of documents into Pinecone.

    Parameters
    ----------
    documents : list[dict]
        Each dict must have:
          - ``id``      (str) — unique document / chunk ID
          - ``text``    (str) — text to embed
          - ``metadata`` (dict, optional) — arbitrary metadata to store

    namespace : str
        Pinecone namespace to use.

    Returns
    -------
    int
        Number of vectors upserted, or 0 on failure.

    Example
    -------
    >>> upsert_documents([
    ...     {"id": "etf-101", "text": "An ETF is a basket of securities...",
    ...      "metadata": {"source": "finance-basics", "agent": "finance_qa"}},
    ... ])
    """
    if not documents:
        return 0
    try:
        index = _get_pinecone_index()
        vectors = []
        for doc in documents:
            doc_id   = doc["id"]
            text     = doc["text"]
            metadata = doc.get("metadata", {})
            metadata["text"] = text          # store raw text for retrieval
            vector = embed_text(text)
            vectors.append({"id": doc_id, "values": vector, "metadata": metadata})

        index.upsert(vectors=vectors, namespace=namespace)
        logger.info("Pinecone: upserted %d vectors (namespace=%s)", len(vectors), namespace)
        return len(vectors)

    except (EnvironmentError, ImportError):
        logger.warning("Pinecone not configured; skipping upsert.")
        return 0
    except Exception as exc:
        logger.warning("Pinecone upsert failed: %s", exc)
        return 0


# ── Query ─────────────────────────────────────────────────────────────────────────

def query_similar(
    query_text: str,
    top_k: int = _TOP_K_DEFAULT,
    namespace: str = _NAMESPACE,
    filter_metadata: Optional[dict] = None,
) -> list[dict]:
    """
    Query Pinecone for chunks most similar to *query_text*.

    Parameters
    ----------
    query_text : str
        The user's question or search phrase.
    top_k : int
        Number of top results to return (default 3).
    namespace : str
        Pinecone namespace to search in.
    filter_metadata : dict, optional
        Pinecone metadata filter (e.g. ``{"agent": "finance_qa"}``).

    Returns
    -------
    list[dict]
        List of matches, each with keys: ``id``, ``score``, ``text``,
        ``metadata``.  Returns [] on any failure.
    """
    if not query_text or not query_text.strip():
        return []
    try:
        index = _get_pinecone_index()
        query_vector = embed_text(query_text)

        kwargs: dict = {
            "vector": query_vector,
            "top_k": top_k,
            "namespace": namespace,
            "include_metadata": True,
        }
        if filter_metadata:
            kwargs["filter"] = filter_metadata

        response = index.query(**kwargs)
        matches = response.get("matches", [])

        results = []
        for match in matches:
            metadata = match.get("metadata", {})
            results.append({
                "id":       match.get("id"),
                "score":    match.get("score", 0.0),
                "text":     metadata.get("text", ""),
                "metadata": metadata,
            })

        logger.info(
            "Pinecone: retrieved %d matches for query=%s",
            len(results), query_text[:60]
        )
        return results

    except (EnvironmentError, ImportError):
        logger.warning(
            "Pinecone not configured; RAG context unavailable. "
            "Set PINECONE_API_KEY and PINECONE_INDEX in .env to enable."
        )
        return []
    except Exception as exc:
        logger.warning("Pinecone query failed [query=%s]: %s", query_text[:60], exc)
        return []
