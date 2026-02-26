from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "conversations.db"


class QuizStore:
    """SQLite-backed quiz & coins store for Daily Quiz persistence."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or _DEFAULT_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS quizzes (
                    question_id TEXT PRIMARY KEY,
                    answer_index INTEGER NOT NULL,
                    session_id TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS coins (
                    session_id TEXT PRIMARY KEY,
                    coins INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id TEXT NOT NULL,
                    session_id TEXT,
                    selected_index INTEGER NOT NULL,
                    correct INTEGER NOT NULL,
                    awarded INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                );
            """)

    def store_question(self, question_id: str, answer_index: int, session_id: Optional[str]) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO quizzes (question_id, answer_index, session_id, created_at) VALUES (?,?,?,?)",
                (question_id, int(answer_index), session_id, now),
            )

    def get_answer_index(self, question_id: str) -> Optional[int]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT answer_index FROM quizzes WHERE question_id=?", (question_id,)
            ).fetchone()
        return int(row[0]) if row else None

    def award_coins(self, session_id: str, amount: int) -> int:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT coins FROM coins WHERE session_id=?", (session_id,)
            ).fetchone()
            if row:
                new = int(row[0]) + int(amount)
                conn.execute(
                    "UPDATE coins SET coins=?, updated_at=? WHERE session_id=?",
                    (new, now, session_id),
                )
            else:
                new = int(amount)
                conn.execute(
                    "INSERT INTO coins (session_id, coins, updated_at) VALUES (?,?,?)",
                    (session_id, new, now),
                )
        return new

    def get_coins(self, session_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT coins FROM coins WHERE session_id=?", (session_id,)).fetchone()
        return int(row[0]) if row else 0

    def store_answer(self, question_id: str, session_id: str, selected_index: int, correct: bool, awarded: int) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO answers (question_id, session_id, selected_index, correct, awarded, timestamp) VALUES (?,?,?,?,?,?)",
                (question_id, session_id, int(selected_index), int(bool(correct)), int(awarded), now),
            )

    def get_history(self, session_id: Optional[str] = None, last_n: int = 50) -> list[dict]:
        with self._connect() as conn:
            if session_id:
                rows = conn.execute(
                    "SELECT question_id, selected_index, correct, awarded, timestamp FROM answers WHERE session_id=? ORDER BY timestamp DESC LIMIT ?",
                    (session_id, last_n),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT question_id, session_id, selected_index, correct, awarded, timestamp FROM answers ORDER BY timestamp DESC LIMIT ?",
                    (last_n,),
                ).fetchall()
        return [dict(r) for r in rows]

    def get_answered_pool_ids(self, session_id: str) -> list[str]:
        """Return list of pool question_ids already answered in this session."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT question_id FROM answers WHERE session_id=?",
                (session_id,),
            ).fetchall()
        return [r[0] for r in rows]
