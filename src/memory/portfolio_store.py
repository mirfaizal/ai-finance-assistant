"""
SQLite-backed portfolio store for persistent paper-trading holdings and trade history.

Uses the same conversations.db file as ConversationStore (separate tables).

Schema
------
holdings : id, session_id, ticker, shares REAL, avg_cost REAL, updated_at TEXT
           UNIQUE(session_id, ticker)  — upserted on every buy
trades   : id, session_id, ticker, action TEXT, shares REAL,
           price REAL, total_value REAL, timestamp TEXT

Usage
-----
    store = PortfolioStore()
    store.buy(session_id, "AAPL", 10, 175.50)
    store.sell(session_id, "AAPL", 5, 180.00)
    holdings = store.get_holdings(session_id)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "conversations.db"


class PortfolioStore:
    """Thread-safe SQLite paper-trading portfolio store."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or _DEFAULT_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ── Internal ───────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS holdings (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT    NOT NULL,
                    ticker      TEXT    NOT NULL,
                    shares      REAL    NOT NULL DEFAULT 0,
                    avg_cost    REAL    NOT NULL DEFAULT 0,
                    updated_at  TEXT    NOT NULL,
                    UNIQUE(session_id, ticker)
                );

                CREATE INDEX IF NOT EXISTS idx_holdings_session
                    ON holdings(session_id);

                CREATE TABLE IF NOT EXISTS trades (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT    NOT NULL,
                    ticker      TEXT    NOT NULL,
                    action      TEXT    NOT NULL CHECK(action IN ('buy', 'sell')),
                    shares      REAL    NOT NULL,
                    price       REAL    NOT NULL,
                    total_value REAL    NOT NULL,
                    timestamp   TEXT    NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_trades_session
                    ON trades(session_id);
            """)

    # ── Public API ─────────────────────────────────────────────────────────────

    def buy(
        self, session_id: str, ticker: str, shares: float, price: float
    ) -> Dict:
        """
        Record a paper buy: upsert holdings (weighted avg cost) and append trade row.

        Returns
        -------
        dict
            ``{ticker, action, shares_bought, price, total_cost, new_position}``
        """
        now = datetime.utcnow().isoformat()
        ticker = ticker.upper().strip()
        total_value = shares * price

        with self._connect() as conn:
            row = conn.execute(
                "SELECT shares, avg_cost FROM holdings WHERE session_id=? AND ticker=?",
                (session_id, ticker),
            ).fetchone()

            if row:
                old_shares: float = row["shares"]
                old_avg: float = row["avg_cost"]
                new_shares = old_shares + shares
                new_avg = (old_avg * old_shares + price * shares) / new_shares
                conn.execute(
                    "UPDATE holdings SET shares=?, avg_cost=?, updated_at=? "
                    "WHERE session_id=? AND ticker=?",
                    (new_shares, new_avg, now, session_id, ticker),
                )
            else:
                new_shares = shares
                new_avg = price
                conn.execute(
                    "INSERT INTO holdings (session_id, ticker, shares, avg_cost, updated_at) "
                    "VALUES (?,?,?,?,?)",
                    (session_id, ticker, shares, price, now),
                )

            conn.execute(
                "INSERT INTO trades "
                "(session_id, ticker, action, shares, price, total_value, timestamp) "
                "VALUES (?,?,?,?,?,?,?)",
                (session_id, ticker, "buy", shares, price, total_value, now),
            )

        return {
            "ticker": ticker,
            "action": "buy",
            "shares_bought": shares,
            "price": round(price, 4),
            "total_cost": round(total_value, 2),
            "new_position": {
                "shares": round(new_shares, 6),
                "avg_cost": round(new_avg, 4),
            },
        }

    def sell(
        self, session_id: str, ticker: str, shares: float, price: float
    ) -> Dict:
        """
        Record a paper sell: reduce holdings and append trade row.

        Raises
        ------
        ValueError
            If the session holds fewer shares than requested.
        """
        now = datetime.utcnow().isoformat()
        ticker = ticker.upper().strip()
        total_value = shares * price

        with self._connect() as conn:
            row = conn.execute(
                "SELECT shares, avg_cost FROM holdings WHERE session_id=? AND ticker=?",
                (session_id, ticker),
            ).fetchone()

            owned = row["shares"] if row else 0.0
            if not row or owned < shares - 1e-9:
                raise ValueError(
                    f"Insufficient shares: you own {owned:.4f} {ticker}, "
                    f"but tried to sell {shares:.4f}."
                )

            old_avg = row["avg_cost"]
            new_shares = owned - shares

            if new_shares < 1e-9:
                conn.execute(
                    "DELETE FROM holdings WHERE session_id=? AND ticker=?",
                    (session_id, ticker),
                )
                new_shares = 0.0
            else:
                conn.execute(
                    "UPDATE holdings SET shares=?, updated_at=? "
                    "WHERE session_id=? AND ticker=?",
                    (new_shares, now, session_id, ticker),
                )

            conn.execute(
                "INSERT INTO trades "
                "(session_id, ticker, action, shares, price, total_value, timestamp) "
                "VALUES (?,?,?,?,?,?,?)",
                (session_id, ticker, "sell", shares, price, total_value, now),
            )

        realized_pnl = (price - old_avg) * shares
        return {
            "ticker": ticker,
            "action": "sell",
            "shares_sold": shares,
            "price": round(price, 4),
            "proceeds": round(total_value, 2),
            "realized_pnl": round(realized_pnl, 2),
            "remaining_shares": round(new_shares, 6),
        }

    def get_holdings(self, session_id: str) -> List[Dict]:
        """Return all current holdings for a session (empty list if none)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ticker, shares, avg_cost, updated_at "
                "FROM holdings WHERE session_id=? "
                "ORDER BY updated_at DESC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_trades(self, session_id: str, last_n: int = 50) -> List[Dict]:
        """Return the most recent *last_n* trades for a session."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ticker, action, shares, price, total_value, timestamp "
                "FROM trades WHERE session_id=? "
                "ORDER BY timestamp DESC LIMIT ?",
                (session_id, last_n),
            ).fetchall()
        return [dict(r) for r in rows]

    def clear_holdings(self, session_id: str) -> int:
        """Delete all holdings for a session. Returns number of rows removed."""
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM holdings WHERE session_id=?", (session_id,)
            )
        return cur.rowcount
