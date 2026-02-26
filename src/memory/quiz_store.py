"""
SQLite-backed quiz & coins store for the Daily Quiz feature.

Schema
------
quizzes : question_id TEXT PK, answer_index INTEGER, session_id TEXT, created_at TEXT
coins   : session_id TEXT PK, coins INTEGER, updated_at TEXT
answers : id INTEGER PK, question_id TEXT, session_id TEXT, selected_index INTEGER,
          correct INTEGER, awarded INTEGER, timestamp TEXT

Usage
-----
    store = QuizStore()
    store.store_question("q123", answer_index=2, session_id="sess-abc")
    correct_idx = store.get_answer_index("q123")
    new_balance = store.award_coins("sess-abc", 10)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "conversations.db"


class QuizStore:
    """Thread-safe SQLite store for quiz questions, answers, and coin balances."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialise the QuizStore and create database tables if they do not exist.

        Parameters
        ----------
        db_path : Path, optional
            Absolute path to the SQLite database file.  Defaults to
            ``data/conversations.db`` alongside the project root.
        """
        self.db_path = Path(db_path or _DEFAULT_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        """Return a new WAL-mode SQLite connection with Row factory enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        """Create the quizzes, coins, and answers tables if they do not exist."""
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
        """
        Persist a quiz question and its correct answer index.

        Called when a question is served to the user so that ``/quiz/answer``
        can later look up the correct index without embedding it in the response.

        Parameters
        ----------
        question_id : str
            Unique question identifier (UUID or Pinecone vector ID).
        answer_index : int
            0-based index of the correct answer in the choices list.
        session_id : str | None
            Optional session to associate with this question for history tracking.
        """
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO quizzes (question_id, answer_index, session_id, created_at) VALUES (?,?,?,?)",
                (question_id, int(answer_index), session_id, now),
            )

    def get_answer_index(self, question_id: str) -> Optional[int]:
        """
        Retrieve the correct answer index for a previously stored question.

        Parameters
        ----------
        question_id : str
            The question identifier passed to ``store_question``.

        Returns
        -------
        int | None
            0-based correct answer index, or ``None`` if not found.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT answer_index FROM quizzes WHERE question_id=?", (question_id,)
            ).fetchone()
        return int(row[0]) if row else None

    def award_coins(self, session_id: str, amount: int) -> int:
        """
        Add *amount* coins to a session's balance and return the new total.

        Creates a new coins row for the session if one does not yet exist.

        Parameters
        ----------
        session_id : str
            The session to credit.
        amount : int
            Number of coins to add (typically 10 for a correct answer).

        Returns
        -------
        int
            Updated coin balance after adding *amount*.
        """
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
        """
        Return the current coin balance for *session_id* (0 if never awarded).

        Parameters
        ----------
        session_id : str
            The session whose balance is requested.

        Returns
        -------
        int
            Current coin balance, or 0 if the session has no record.
        """
        with self._connect() as conn:
            row = conn.execute("SELECT coins FROM coins WHERE session_id=?", (session_id,)).fetchone()
        return int(row[0]) if row else 0

    def store_answer(self, question_id: str, session_id: str, selected_index: int, correct: bool, awarded: int) -> None:
        """
        Record a user's quiz answer in the answers audit table.

        Parameters
        ----------
        question_id : str
            The question that was answered.
        session_id : str
            The session that submitted the answer.
        selected_index : int
            The 0-based index the user chose.
        correct : bool
            Whether the chosen answer was correct.
        awarded : int
            Number of coins awarded for this answer (0 if incorrect).
        """
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO answers (question_id, session_id, selected_index, correct, awarded, timestamp) VALUES (?,?,?,?,?,?)",
                (question_id, session_id, int(selected_index), int(bool(correct)), int(awarded), now),
            )

    def get_history(self, session_id: Optional[str] = None, last_n: int = 50) -> list[dict]:
        """
        Return quiz answer history, optionally filtered by session.

        Parameters
        ----------
        session_id : str | None
            Filter to a specific session.  Pass ``None`` to get all sessions.
        last_n : int
            Maximum number of rows to return (default 50), sorted newest-first.

        Returns
        -------
        list[dict]
            Each dict contains: question_id, session_id, selected_index,
            correct, awarded, timestamp.
        """
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
