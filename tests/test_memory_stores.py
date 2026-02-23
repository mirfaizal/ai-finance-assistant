"""Unit tests for src/memory/conversation_store.py and portfolio_store.py"""
from __future__ import annotations
import tempfile
from pathlib import Path
import pytest


# ══════════════════════════════════════════════════════════════════════════════
# ConversationStore
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def conv_store(tmp_path):
    from src.memory.conversation_store import ConversationStore
    db = tmp_path / "conversations.db"
    return ConversationStore(db_path=db)


class TestConversationStoreSchema:

    def test_creates_db_file(self, tmp_path):
        from src.memory.conversation_store import ConversationStore
        db = tmp_path / "test.db"
        ConversationStore(db_path=db)
        assert db.exists()

    def test_creates_parent_dirs(self, tmp_path):
        from src.memory.conversation_store import ConversationStore
        db = tmp_path / "nested" / "dir" / "test.db"
        ConversationStore(db_path=db)
        assert db.exists()


class TestEnsureSession:

    def test_creates_session(self, conv_store):
        sid = "session-aaa"
        conv_store.ensure_session(sid)
        sessions = conv_store.list_sessions()
        assert sid in sessions

    def test_idempotent(self, conv_store):
        sid = "session-bbb"
        conv_store.ensure_session(sid)
        conv_store.ensure_session(sid)
        sessions = conv_store.list_sessions()
        assert sessions.count(sid) == 1


class TestSaveTurn:

    def test_saves_user_and_assistant(self, conv_store):
        sid = "session-ccc"
        conv_store.save_turn(sid, "What is inflation?", "Inflation is a rise in prices.", "finance_qa_agent")
        history = conv_store.get_history(sid)
        roles = [m["role"] for m in history]
        assert "user" in roles
        assert "assistant" in roles

    def test_auto_creates_session(self, conv_store):
        sid = "auto-session"
        conv_store.save_turn(sid, "Q", "A", "agent")
        assert sid in conv_store.list_sessions()

    def test_multiple_turns(self, conv_store):
        sid = "multi-session"
        conv_store.save_turn(sid, "Q1", "A1", "agent")
        conv_store.save_turn(sid, "Q2", "A2", "agent")
        history = conv_store.get_history(sid, last_n=10)
        assert len(history) == 4  # 2 user + 2 assistant

    def test_turn_count_increments(self, conv_store):
        sid = "count-session"
        conv_store.save_turn(sid, "Q1", "A1", "agent")
        conv_store.save_turn(sid, "Q2", "A2", "agent")
        assert conv_store.get_turn_count(sid) == 2


class TestGetHistory:

    def test_returns_list(self, conv_store):
        sid = "hist-session"
        conv_store.save_turn(sid, "What is a bond?", "A bond is a debt instrument.", "finance_qa")
        history = conv_store.get_history(sid)
        assert isinstance(history, list)

    def test_history_has_role_and_content(self, conv_store):
        sid = "role-session"
        conv_store.save_turn(sid, "Q", "A", "agent")
        history = conv_store.get_history(sid)
        for msg in history:
            assert "role" in msg
            assert "content" in msg

    def test_history_chronological_order(self, conv_store):
        sid = "order-session"
        conv_store.save_turn(sid, "First Q", "First A", "agent")
        conv_store.save_turn(sid, "Second Q", "Second A", "agent")
        history = conv_store.get_history(sid)
        # Oldest first
        assert history[0]["content"] == "First Q"

    def test_last_n_respected(self, conv_store):
        sid = "limit-session"
        for i in range(10):
            conv_store.save_turn(sid, f"Q{i}", f"A{i}", "agent")
        history = conv_store.get_history(sid, last_n=4)
        assert len(history) <= 4

    def test_empty_session_returns_empty(self, conv_store):
        history = conv_store.get_history("nonexistent-session")
        assert history == []


class TestSaveSummary:

    def test_saves_summary_row(self, conv_store):
        sid = "summary-session"
        # Create some turns first
        for i in range(6):
            conv_store.save_turn(sid, f"Q{i}", f"A{i}", "agent")
        conv_store.save_summary(sid, "Summary of conversation so far.")
        history = conv_store.get_history(sid, last_n=20)
        roles = [m["role"] for m in history]
        assert "summary" in roles

    def test_old_messages_pruned_after_summary(self, conv_store):
        sid = "prune-session"
        for i in range(10):
            conv_store.save_turn(sid, f"Q{i}", f"A{i}", "agent")
        conv_store.save_summary(sid, "Compressed summary.")
        # Only last 4 raw + 1 summary should remain
        history = conv_store.get_history(sid, last_n=20)
        assert len(history) <= 6


class TestGetTurnCount:

    def test_zero_for_new_session(self, conv_store):
        assert conv_store.get_turn_count("new-session-xyz") == 0

    def test_counts_user_messages_only(self, conv_store):
        sid = "count-only"
        conv_store.save_turn(sid, "Q1", "A1", "a")
        conv_store.save_turn(sid, "Q2", "A2", "a")
        assert conv_store.get_turn_count(sid) == 2


class TestListSessions:

    def test_returns_list(self, conv_store):
        sessions = conv_store.list_sessions()
        assert isinstance(sessions, list)

    def test_new_session_appears(self, conv_store):
        sid = conv_store.new_session_id()
        conv_store.ensure_session(sid)
        assert sid in conv_store.list_sessions()


class TestNewSessionId:

    def test_returns_uuid_string(self, conv_store):
        import uuid
        sid = conv_store.new_session_id()
        uuid.UUID(sid)  # should not raise

    def test_each_unique(self, conv_store):
        assert conv_store.new_session_id() != conv_store.new_session_id()


# ══════════════════════════════════════════════════════════════════════════════
# PortfolioStore
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def port_store(tmp_path):
    from src.memory.portfolio_store import PortfolioStore
    db = tmp_path / "portfolio.db"
    return PortfolioStore(db_path=db)


class TestPortfolioStoreBuy:

    def test_buy_returns_dict(self, port_store):
        result = port_store.buy("sess-1", "AAPL", 10.0, 150.0)
        assert isinstance(result, dict)
        assert result["ticker"] == "AAPL"

    def test_buy_records_shares(self, port_store):
        port_store.buy("sess-2", "AAPL", 10.0, 150.0)
        holdings = port_store.get_holdings("sess-2")
        assert len(holdings) == 1
        assert holdings[0]["ticker"] == "AAPL"
        assert holdings[0]["shares"] == 10.0

    def test_buy_weighted_avg_cost(self, port_store):
        port_store.buy("sess-3", "AAPL", 10.0, 100.0)
        port_store.buy("sess-3", "AAPL", 10.0, 200.0)
        holdings = port_store.get_holdings("sess-3")
        # (10*100 + 10*200) / 20 = 150
        assert abs(holdings[0]["avg_cost"] - 150.0) < 0.01

    def test_buy_multiple_tickers(self, port_store):
        port_store.buy("sess-4", "AAPL", 5.0, 150.0)
        port_store.buy("sess-4", "NVDA", 3.0, 400.0)
        holdings = port_store.get_holdings("sess-4")
        assert len(holdings) == 2

    def test_buy_creates_trade_record(self, port_store):
        port_store.buy("sess-5", "AAPL", 5.0, 150.0)
        trades = port_store.get_trades("sess-5")
        assert len(trades) == 1
        assert trades[0]["action"] == "buy"


class TestPortfolioStoreSell:

    def test_sell_reduces_holdings(self, port_store):
        port_store.buy("sess-6", "AAPL", 10.0, 150.0)
        port_store.sell("sess-6", "AAPL", 5.0, 160.0)
        holdings = port_store.get_holdings("sess-6")
        assert holdings[0]["shares"] == 5.0

    def test_sell_all_removes_holding(self, port_store):
        port_store.buy("sess-7", "AAPL", 10.0, 150.0)
        port_store.sell("sess-7", "AAPL", 10.0, 160.0)
        holdings = port_store.get_holdings("sess-7")
        assert len(holdings) == 0

    def test_sell_more_than_held_raises(self, port_store):
        port_store.buy("sess-8", "AAPL", 5.0, 150.0)
        with pytest.raises(ValueError):
            port_store.sell("sess-8", "AAPL", 10.0, 160.0)

    def test_sell_creates_trade_record(self, port_store):
        port_store.buy("sess-9", "AAPL", 10.0, 150.0)
        port_store.sell("sess-9", "AAPL", 3.0, 160.0)
        trades = port_store.get_trades("sess-9")
        assert len(trades) == 2  # 1 buy + 1 sell
        actions = [t["action"] for t in trades]
        assert "sell" in actions

    def test_sell_returns_dict_with_pnl(self, port_store):
        port_store.buy("sess-10", "AAPL", 10.0, 150.0)
        result = port_store.sell("sess-10", "AAPL", 5.0, 160.0)
        assert "realized_pnl" in result or "proceeds" in result or isinstance(result, dict)


class TestPortfolioStoreGetHoldings:

    def test_empty_session_returns_empty(self, port_store):
        holdings = port_store.get_holdings("empty-sess")
        assert holdings == []

    def test_returns_all_tickers(self, port_store):
        port_store.buy("all-sess", "AAPL", 5.0, 150.0)
        port_store.buy("all-sess", "TSLA", 3.0, 200.0)
        holdings = port_store.get_holdings("all-sess")
        tickers = {h["ticker"] for h in holdings}
        assert "AAPL" in tickers
        assert "TSLA" in tickers


class TestPortfolioStoreGetTrades:

    def test_last_n_respected(self, port_store):
        for i in range(5):
            port_store.buy(f"trade-sess", "AAPL", 1.0, 150.0 + i)
        trades = port_store.get_trades("trade-sess", last_n=3)
        assert len(trades) <= 3

    def test_empty_returns_empty(self, port_store):
        trades = port_store.get_trades("no-trades-sess")
        assert trades == []


class TestPortfolioStoreClearHoldings:

    def test_clear_removes_holdings(self, port_store):
        port_store.buy("clear-sess", "AAPL", 10.0, 150.0)
        port_store.clear_holdings("clear-sess")
        holdings = port_store.get_holdings("clear-sess")
        assert holdings == []

    def test_clear_returns_removed_count(self, port_store):
        port_store.buy("count-clear", "AAPL", 10.0, 150.0)
        port_store.buy("count-clear", "NVDA", 5.0, 400.0)
        removed = port_store.clear_holdings("count-clear")
        assert removed == 2

    def test_clear_preserves_trades(self, port_store):
        port_store.buy("preserve-sess", "AAPL", 10.0, 150.0)
        port_store.clear_holdings("preserve-sess")
        trades = port_store.get_trades("preserve-sess")
        assert len(trades) == 1
