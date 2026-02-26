"""Seed Pinecone index with Financial Academy content and quiz bank.

Run as a script or import individual seed functions from other tooling.

Requirements: set PINECONE_API_KEY, PINECONE_INDEX, OPENAI_API_KEY in environment.

Namespaces
----------
finance-docs  — academy course content (paragraphs from markdown files)
quiz-pool     — pre-written quiz questions from the quiz bank
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from src.rag.pinecone_store import upsert_documents
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Namespace for pre-written quiz questions
_QUIZ_NAMESPACE = "quiz-pool"


def load_markdown_files(dir_path: str) -> List[dict]:
    p = Path(dir_path)
    docs = []
    if not p.exists():
        logger.warning("Seed directory does not exist: %s", dir_path)
        return docs
    for md in sorted(p.glob("*.md")):
        text = md.read_text(encoding='utf-8')
        # split into paragraphs / sections
        parts = [s.strip() for s in text.split('\n\n') if s.strip()]
        for i, part in enumerate(parts, start=1):
            doc_id = f"{md.stem}-{i}"
            docs.append({
                "id": doc_id,
                "text": part,
                "metadata": {
                    "source": "financial-academy",
                    "doc":    md.stem,         # matches slug used by /academy/course/{slug}
                    "agent":  "finance_qa",
                    "type":   "course",
                },
            })
    return docs


def seed_from_directory(dir_path: str = "data/academy") -> int:
    """Upsert academy markdown content into the finance-docs namespace."""
    docs = load_markdown_files(dir_path)
    # Fallback: packaged academy content inside src/rag/academy (bundled in image)
    if not docs:
        fallback = Path(__file__).resolve().parent / "academy"
        if fallback.exists():
            logger.info("Falling back to bundled academy at %s", fallback)
            docs = load_markdown_files(str(fallback))
    if not docs:
        logger.warning("No documents to upsert from %s", dir_path)
        return 0
    count = upsert_documents(docs)  # default namespace = finance-docs
    logger.info("Seeded %d course chunks from %s", count, dir_path)
    return count


def seed_quiz_pool() -> int:
    """Upsert the curated quiz bank into the quiz-pool namespace."""
    from src.rag.quiz_bank import build_pinecone_docs  # local import to avoid circular deps

    docs = build_pinecone_docs()
    if not docs:
        logger.warning("Quiz bank is empty; nothing to upsert.")
        return 0
    count = upsert_documents(docs, namespace=_QUIZ_NAMESPACE)
    logger.info("Seeded %d quiz questions into namespace '%s'", count, _QUIZ_NAMESPACE)
    return count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed Pinecone with Financial Academy content and quiz bank"
    )
    parser.add_argument("--dir", default="data/academy", help="Directory with academy markdown files")
    parser.add_argument("--quiz", action="store_true", help="Also seed the quiz bank")
    args = parser.parse_args()

    n = seed_from_directory(args.dir)
    print(f"Upserted {n} course vectors")

    if args.quiz:
        q = seed_quiz_pool()
        print(f"Upserted {q} quiz question vectors")
