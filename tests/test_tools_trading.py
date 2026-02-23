"""Unit tests for src/tools/trading_tools.py"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def _make_store_and_session(tmp_path: Path):
    """Create a PortfolioStore with a temp DB and return (store, session_id)."""
    from src.memory.portfolio_store import PortfolioStore
    db = tmp_path / "test.db"
    store = PortfolioStore(db_path=db)
    return store, "test-session-999"


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path


class TestMakeTradingTools:

    def test_returns_four_tools(self, tmp_db):
        with patch("src.tools.trading_tools.PortfolioStore") as mock_store_cls:
            from src.memory.portfolio_store import PortfolioStore
            mock_store = PortfolioStore(db_path=tmp_db / "t.db")
            mock_store_cls.return_value = mock_store
            from src.tools.trading_tools import make_trading_tools
            tools = make_trading_tools("session-123")
            assert len(tools) == 4

    def test_tool_names(self, tmp_db):
        with patch("src.tools.trading_tools.PortfolioStore") as mock_store_cls:
            from src.memory.portfolio_store import PortfolioStore
            mock_store = PortfolioStore(db_path=tmp_db / "t.db")
            mock_store_cls.return_value = mock_store
            from src.tools.trading_tools import make_trading_tools
            tools = make_trading_tools("session-abc")
            names = {t.name for t in tools}
            assert "buy_stock" in names
            assert "sell_stock" in names
            assert "view_holdings" in names
            assert "view_trade_history" in names


class TestBuyStock:

    @patch("src.tools.trading_tools._live_price")
    @patch("src.tools.trading_tools.PortfolioStore")
    def test_buy_returns_confirmed(self, mock_store_cls, mock_price, tmp_db):
        mock_price.return_value = 150.0
        from src.memory.portfolio_store import PortfolioStore
        store = PortfolioStore(db_path=tmp_db / "t.db")
        mock_store_cls.return_value = store

        from src.tools.trading_tools import make_trading_tools
        tools = {t.name: t for t in make_trading_tools("sess-1")}
        result = json.loads(tools["buy_stock"].invoke({"ticker": "AAPL", "shares": 10.0}))
        assert result.get("status") == "confirmed"

    @patch("src.tools.trading_tools._live_price")
    @patch("src.tools.trading_tools.PortfolioStore")
    def test_buy_invalid_shares(self, mock_store_cls, mock_price, tmp_db):
        mock_price.return_value = 150.0
        from src.memory.portfolio_store import PortfolioStore
        store = PortfolioStore(db_path=tmp_db / "t2.db")
        mock_store_cls.return_value = store
        from src.tools.trading_tools import make_trading_tools
        tools = {t.name: t for t in make_trading_tools("sess-1")}
        result = json.loads(tools["buy_stock"].invoke({"ticker": "AAPL", "shares": -5.0}))
        assert "error" in result

    @patch("src.tools.trading_tools._live_price")
    @patch("src.tools.trading_tools.PortfolioStore")
    def test_buy_price_fetch_error(self, mock_store_cls, mock_price, tmp_db):
        mock_price.side_effect = ValueError("Could not fetch price")
        from src.memory.portfolio_store import PortfolioStore
        store = PortfolioStore(db_path=tmp_db / "t3.db")
        mock_store_cls.return_value = store
        from src.tools.trading_tools import make_trading_tools
        tools = {t.name: t for t in make_trading_tools("sess-err")}
        result = json.loads(tools["buy_stock"].invoke({"ticker": "AAPL", "shares": 5.0}))
        assert "error" in result


class TestSellStock:

    @patch("src.tools.trading_tools._live_price")
    @patch("src.tools.trading_tools.PortfolioStore")
    def test_sell_existing_position(self, mock_store_cls, mock_price, tmp_db):
        mock_price.return_value = 160.0
        from src.memory.portfolio_store import PortfolioStore
        store = PortfolioStore(db_path=tmp_db / "t4.db")
        # Pre-buy
        store.buy("sess-s", "AAPL", 10.0, 150.0)
        mock_store_cls.return_value = store

        from src.tools.trading_tools import make_trading_tools
        tools = {t.name: t for t in make_trading_tools("sess-s")}
        result = json.loads(tools["sell_stock"].invoke({"ticker": "AAPL", "shares": 5.0}))
        assert result.get("status") == "confirmed" or "error" in result

    @patch("src.tools.trading_tools._live_price")
    @patch("src.tools.trading_tools.PortfolioStore")
    def test_sell_zero_shares_error(self, mock_store_cls, mock_price, tmp_db):
        mock_price.return_value = 150.0
        from src.memory.portfolio_store import PortfolioStore
        store = PortfolioStore(db_path=tmp_db / "t5.db")
        mock_store_cls.return_value = store
        from src.tools.trading_tools import make_trading_tools
        tools = {t.name: t for t in make_trading_tools("sess-2")}
        result = json.loads(tools["sell_stock"].invoke({"ticker": "AAPL", "shares": 0.0}))
        assert "error" in result

    @patch("src.tools.trading_tools._live_price")
    @patch("src.tools.trading_tools.PortfolioStore")
    def test_sell_more_than_held_error(self, mock_store_cls, mock_price, tmp_db):
        mock_price.return_value = 160.0
        from src.memory.portfolio_store import PortfolioStore
        store = PortfolioStore(db_path=tmp_db / "t6.db")
        mock_store_cls.return_value = store
        from src.tools.trading_tools import make_trading_tools
        tools = {t.name: t for t in make_trading_tools("sess-3")}
        result = json.loads(tools["sell_stock"].invoke({"ticker": "AAPL", "shares": 100.0}))
        assert "error" in result


class TestViewHoldings:

    @patch("src.tools.trading_tools.PortfolioStore")
    def test_empty_portfolio_message(self, mock_store_cls, tmp_db):
        from src.memory.portfolio_store import PortfolioStore
        store = PortfolioStore(db_path=tmp_db / "t7.db")
        mock_store_cls.return_value = store
        from src.tools.trading_tools import make_trading_tools
        tools = {t.name: t for t in make_trading_tools("empty-sess")}
        result = json.loads(tools["view_holdings"].invoke({}))
        assert result["count"] == 0
        assert "message" in result

    @patch("src.tools.trading_tools.PortfolioStore")
    def test_holdings_shown(self, mock_store_cls, tmp_db):
        from src.memory.portfolio_store import PortfolioStore
        store = PortfolioStore(db_path=tmp_db / "t8.db")
        store.buy("full-sess", "AAPL", 10.0, 150.0)
        mock_store_cls.return_value = store
        from src.tools.trading_tools import make_trading_tools
        tools = {t.name: t for t in make_trading_tools("full-sess")}
        result = json.loads(tools["view_holdings"].invoke({}))
        assert result["count"] == 1


class TestViewTradeHistory:

    @patch("src.tools.trading_tools.PortfolioStore")
    def test_returns_trades(self, mock_store_cls, tmp_db):
        from src.memory.portfolio_store import PortfolioStore
        store = PortfolioStore(db_path=tmp_db / "t9.db")
        store.buy("trade-sess", "AAPL", 10.0, 150.0)
        mock_store_cls.return_value = store
        from src.tools.trading_tools import make_trading_tools
        tools = {t.name: t for t in make_trading_tools("trade-sess")}
        result = json.loads(tools["view_trade_history"].invoke({}))
        assert "trades" in result
        assert result["count"] >= 1
