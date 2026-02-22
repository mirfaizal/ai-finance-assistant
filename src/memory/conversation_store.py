"""
SQLite-backed conversation store for cross-session persistent memory.

Schema
------
sessions  : session_id TEXT PK, created_at TEXT
messages  : id INTEGER PK, session_id TEXT FK, role TEXT,
            content TEXT, agent TEXT, timestamp TEXT

Usage
-----
    store = ConversationStore()          # opens/creates data/conversations.db
    store.save_turn(sid, "user q", "assistant a", "finance_qa_agent")
    history = store.get_history(sid)     # [{"role": ..., "content": ...}, ...]
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Store the DB alongside the src/ tree in a sibling data/ directory
_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "conversations.db"


class ConversationStore:
    """Thread-safe SQLite conversation store."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or _DEFAULT_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ── schema ────────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # safe for concurrent reads
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id  TEXT PRIMARY KEY,
                    created_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT    NOT NULL REFERENCES sessions(session_id),
                    role        TEXT    NOT NULL CHECK(role IN ('user', 'assistant', 'summary')),
                    content     TEXT    NOT NULL,
                    agent       TEXT,
                    timestamp   TEXT    NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, id);
            """)

    # ── public API ────────────────────────────────────────────────────────────

    def ensure_session(self, session_id: str) -> None:
        """Create the session row if it does not exist."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id, created_at) VALUES (?, ?)",
                (session_id, datetime.utcnow().isoformat()),
            )

    def save_turn(
        self,
        session_id: str,
        user_msg: str,
        assistant_msg: str,
        agent_name: str = "unknown",
    ) -> None:
        """
        Persist a user/assistant exchange as two message rows.
        Creates the session automatically if it doesn't exist.
        """
        self.ensure_session(session_id)
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO messages (session_id, role, content, agent, timestamp) VALUES (?,?,?,?,?)",
                [
                    (session_id, "user",      user_msg,      agent_name, now),
                    (session_id, "assistant", assistant_msg, agent_name, now),
                ],
            )

    def save_summary(self, session_id: str, summary: str) -> None:
        """
        Replace older raw messages with a synthesized summary row.
        Keeps only the most recent 4 raw messages after compressing.
        """
        self.ensure_session(session_id)
        with self._connect() as conn:
            # Delete all but the last 4 messages
            conn.execute(
                """
                DELETE FROM messages
                WHERE session_id = ?
                  AND id NOT IN (
                      SELECT id FROM messages
                      WHERE session_id = ?
                      ORDER BY id DESC
                      LIMIT 4
                  )
                  AND role != 'summary'
                """,
                (session_id, session_id),
            )
            # Insert the summary as the earliest row (id-wise it will sort first)
            conn.execute(
                "INSERT INTO messages (session_id, role, content, agent, timestamp) VALUES (?,?,?,?,?)",
                (session_id, "summary", summary, "memory_synthesizer", datetime.utcnow().isoformat()),
            )

    def get_history(
        self,
        session_id: str,
        last_n: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Return the last *last_n* messages for *session_id* as a list of
        ``{"role": str, "content": str}`` dicts — ready to use as OpenAI
        ``messages`` history.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, last_n),
            ).fetchall()
        # Reverse so oldest first (chronological order for LLM context)
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def get_turn_count(self, session_id: str) -> int:
        """Return number of user messages in the session (= number of turns)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM messages WHERE session_id = ? AND role = 'user'",
                (session_id,),
            ).fetchone()
        return row["cnt"] if row else 0

    def list_sessions(self) -> List[str]:
        """Return all known session IDs ordered by creation time."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT session_id FROM sessions ORDER BY created_at DESC"
            ).fetchall()
        return [r["session_id"] for r in rows]

    @staticmethod
    def new_session_id() -> str:
        """Generate a fresh UUID4 session identifier."""
        return str(uuid.uuid4())
