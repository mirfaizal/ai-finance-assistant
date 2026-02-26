"""Seed Pinecone index with Financial Academy content.

Run as a script or import `seed_from_directory()` from other tooling.

Requirements: set PINECONE_API_KEY, PINECONE_INDEX, OPENAI_API_KEY in environment.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from src.rag.pinecone_store import upsert_documents
from src.utils.logging import get_logger

logger = get_logger(__name__)


def load_markdown_files(dir_path: str) -> List[dict]:
    p = Path(dir_path)
    docs = []
    if not p.exists():
        logger.warning("Seed directory does not exist: %s", dir_path)
        return docs
    for md in sorted(p.glob("*.md")):
        text = md.read_text(encoding='utf-8')
        # split into paragraphs
        parts = [s.strip() for s in text.split('\n\n') if s.strip()]
        for i, part in enumerate(parts, start=1):
            doc_id = f"{md.stem}-{i}"
            docs.append({
                "id": doc_id,
                "text": part,
                "metadata": {"source": "financial-academy", "doc": md.stem, "agent": "finance_qa"},
            })
    return docs


def seed_from_directory(dir_path: str = "data/academy") -> int:
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
    count = upsert_documents(docs)
    logger.info("Seeded %d document chunks from %s", count, dir_path)
    return count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed Pinecone with Financial Academy markdown files")
    parser.add_argument("--dir", default="data/academy", help="Directory with markdown files")
    args = parser.parse_args()
    n = seed_from_directory(args.dir)
    print(f"Upserted {n} vectors")
