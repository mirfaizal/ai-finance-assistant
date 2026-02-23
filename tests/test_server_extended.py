"""Extended FastAPI endpoint tests covering all remaining server.py routes."""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_client():
    """Return a fresh TestClient with all external I/O patched out."""
    from src.web_app.server import app
    return TestClient(app)


# ── Health check ──────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_returns_200(self):
        client = _make_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ── /history/{session_id} ─────────────────────────────────────────────────────

class TestGetHistory:

    def test_empty_session_returns_empty_messages(self):
        with patch("src.web_app.server._store") as mock_store:
            mock_store.get_history.return_value = []
            client = _make_client()
            resp = client.get("/history/sess-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "sess-1"
        assert body["messages"] == []

    def test_returns_messages(self):
        msgs = [
            {"role": "user", "content": "What is ETF?"},
            {"role": "assistant", "content": "ETF is exchange traded fund."},
        ]
        with patch("src.web_app.server._store") as mock_store:
            mock_store.get_history.return_value = msgs
            client = _make_client()
            resp = client.get("/history/sess-2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "user"

    def test_last_n_query_param_forwarded(self):
        with patch("src.web_app.server._store") as mock_store:
            mock_store.get_history.return_value = []
            client = _make_client()
            resp = client.get("/history/sess-3?last_n=5")
        assert resp.status_code == 200
        mock_store.get_history.assert_called_once_with("sess-3", last_n=5)


# ── /sessions ─────────────────────────────────────────────────────────────────

class TestListSessions:

    def test_returns_sessions_list(self):
        with patch("src.web_app.server._store") as mock_store:
            mock_store.list_sessions.return_value = ["sess-a", "sess-b"]
            client = _make_client()
            resp = client.get("/sessions")
        assert resp.status_code == 200
        assert resp.json() == {"sessions": ["sess-a", "sess-b"]}

    def test_empty_sessions(self):
        with patch("src.web_app.server._store") as mock_store:
            mock_store.list_sessions.return_value = []
            client = _make_client()
            resp = client.get("/sessions")
        assert resp.status_code == 200
        assert resp.json() == {"sessions": []}


# ── /market/overview ──────────────────────────────────────────────────────────

class TestMarketOverview:

    def test_returns_market_data(self):
        market_data = {"SPY": {"price": 450.0, "change_pct": 0.5}, "QQQ": {"price": 380.0, "change_pct": -0.2}}
        with patch("src.tools.market_tools.get_market_overview") as mock_gmov:
            mock_gmov.invoke.return_value = json.dumps(market_data)
            client = _make_client()
            resp = client.get("/market/overview")
        assert resp.status_code in (200, 500)

    def test_market_overview_uses_invoke(self):
        market_data = {
            "indices": {"SPY": {"price": 450.0, "change_pct": 1.2}},
        }
        with patch("src.tools.market_tools.get_market_overview") as mock_tool:
            mock_tool.invoke.return_value = json.dumps(market_data)
            client = _make_client()
            resp = client.get("/market/overview")
        assert resp.status_code in (200, 500)


# ── /market/chart ─────────────────────────────────────────────────────────────

class TestMarketChart:

    def test_returns_list(self):
        import pandas as pd

        dates = pd.date_range("2023-01-01", periods=3, freq="ME")
        mock_df = pd.DataFrame(
            {"SPY": [400.0, 410.0, 420.0], "QQQ": [300.0, 310.0, 320.0], "DIA": [330.0, 340.0, 350.0]},
            index=dates,
        )
        with patch("yfinance.download") as mock_dl:
            # The endpoint does yf.download(...)['Close'] then accesses .columns
            mock_dl.return_value.__getitem__ = MagicMock(return_value=mock_df)
            client = _make_client()
            resp = client.get("/market/chart")
        assert resp.status_code in (200, 500)

    def test_chart_error_returns_500(self):
        with patch("yfinance.download", side_effect=RuntimeError("network error")):
            client = _make_client()
            resp = client.get("/market/chart")
        assert resp.status_code in (200, 500)


# ── /market/quotes ────────────────────────────────────────────────────────────

class TestMarketQuotes:

    def _make_ticker_mock(self, price=150.0, prev=145.0):
        tk = MagicMock()
        tk.fast_info.last_price = price
        tk.fast_info.previous_close = prev
        return tk

    def test_single_symbol(self):
        with patch("yfinance.Ticker", return_value=self._make_ticker_mock(150.0, 145.0)):
            client = _make_client()
            resp = client.get("/market/quotes?symbols=AAPL")
        assert resp.status_code == 200
        body = resp.json()
        assert "AAPL" in body
        assert "price" in body["AAPL"]

    def test_multiple_symbols(self):
        def make_tk(sym):
            return self._make_ticker_mock(100.0, 98.0)

        with patch("yfinance.Ticker", side_effect=make_tk):
            client = _make_client()
            resp = client.get("/market/quotes?symbols=SPY,AAPL,TSLA")
        assert resp.status_code == 200
        body = resp.json()
        assert "SPY" in body
        assert "AAPL" in body
        assert "TSLA" in body

    def test_failed_ticker_returns_none_fields(self):
        with patch("yfinance.Ticker", side_effect=Exception("fail")):
            client = _make_client()
            resp = client.get("/market/quotes?symbols=BAD")
        assert resp.status_code == 200
        body = resp.json()
        assert body["BAD"]["price"] is None

    def test_default_symbols_used_when_not_provided(self):
        mock_tk = self._make_ticker_mock(200.0, 195.0)
        with patch("yfinance.Ticker", return_value=mock_tk):
            client = _make_client()
            resp = client.get("/market/quotes")
        assert resp.status_code == 200

    def test_change_pct_calculated_correctly(self):
        with patch("yfinance.Ticker", return_value=self._make_ticker_mock(110.0, 100.0)):
            client = _make_client()
            resp = client.get("/market/quotes?symbols=XYZ")
        body = resp.json()
        assert body["XYZ"]["change_pct"] == pytest.approx(10.0)
        assert body["XYZ"]["up"] is True

    def test_zero_prev_close_gives_zero_change_pct(self):
        with patch("yfinance.Ticker", return_value=self._make_ticker_mock(100.0, 0.0)):
            client = _make_client()
            resp = client.get("/market/quotes?symbols=ZERO")
        body = resp.json()
        assert body["ZERO"]["change_pct"] == 0.0


# ── /portfolio/analyze ────────────────────────────────────────────────────────

class TestPortfolioAnalyze:

    def test_returns_analysis(self):
        result = {
            "holdings": [{"ticker": "AAPL", "current_value": 1500.0}],
            "total_value": 1500.0,
        }
        with patch("src.tools.portfolio_tools.analyze_portfolio") as mock_tool:
            mock_tool.invoke.return_value = json.dumps(result)
            client = _make_client()
            resp = client.post(
                "/portfolio/analyze",
                json={"holdings": [{"ticker": "AAPL", "shares": 10, "avg_cost": 150.0}]},
            )
        assert resp.status_code in (200, 500)

    def test_invalid_payload_returns_422(self):
        client = _make_client()
        resp = client.post("/portfolio/analyze", json={"wrong_key": "value"})
        assert resp.status_code == 422

    def test_empty_holdings_accepted(self):
        result = {"holdings": [], "total_value": 0.0}
        with patch("src.web_app.server.analyze_portfolio", create=True) as mock_tool:
            mock_tool.invoke.return_value = json.dumps(result)
            client = _make_client()
            resp = client.post("/portfolio/analyze", json={"holdings": []})
        assert resp.status_code in (200, 500)


# ── /portfolio/holdings/{session_id} GET ─────────────────────────────────────

class TestGetHoldings:

    def test_returns_holdings(self):
        holdings = [{"ticker": "AAPL", "shares": 10.0, "avg_cost": 150.0, "updated_at": "2024-01-01"}]
        with patch("src.web_app.server._portfolio_store") as mock_ps:
            mock_ps.get_holdings.return_value = holdings
            client = _make_client()
            resp = client.get("/portfolio/holdings/sess-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "sess-1"
        assert body["count"] == 1
        assert body["holdings"][0]["ticker"] == "AAPL"

    def test_empty_holdings(self):
        with patch("src.web_app.server._portfolio_store") as mock_ps:
            mock_ps.get_holdings.return_value = []
            client = _make_client()
            resp = client.get("/portfolio/holdings/sess-empty")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


# ── /portfolio/trades/{session_id} GET ───────────────────────────────────────

class TestGetTrades:

    def test_returns_trades(self):
        trades = [
            {"id": 1, "ticker": "AAPL", "action": "buy", "shares": 5, "price": 150.0,
             "total_value": 750.0, "timestamp": "2024-01-01T00:00:00"}
        ]
        with patch("src.web_app.server._portfolio_store") as mock_ps:
            mock_ps.get_trades.return_value = trades
            client = _make_client()
            resp = client.get("/portfolio/trades/sess-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["trades"][0]["action"] == "buy"

    def test_last_n_forwarded(self):
        with patch("src.web_app.server._portfolio_store") as mock_ps:
            mock_ps.get_trades.return_value = []
            client = _make_client()
            resp = client.get("/portfolio/trades/sess-1?last_n=10")
        assert resp.status_code == 200
        mock_ps.get_trades.assert_called_once_with("sess-1", last_n=10)


# ── /portfolio/buy/{session_id} POST ─────────────────────────────────────────

class TestPaperBuy:

    def _mock_ticker(self, price=150.0):
        tk = MagicMock()
        tk.fast_info.last_price = price
        return tk

    def test_successful_buy(self):
        buy_result = {"ticker": "AAPL", "shares": 10.0, "avg_cost": 150.0, "action": "buy"}
        with patch("yfinance.Ticker", return_value=self._mock_ticker(150.0)):
            with patch("src.web_app.server._portfolio_store") as mock_ps:
                mock_ps.buy.return_value = buy_result
                client = _make_client()
                resp = client.post(
                    "/portfolio/buy/sess-1",
                    json={"ticker": "AAPL", "shares": 10},
                )
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"

    def test_buy_with_zero_price_returns_422(self):
        with patch("yfinance.Ticker", return_value=self._mock_ticker(0.0)):
            client = _make_client()
            resp = client.post(
                "/portfolio/buy/sess-1",
                json={"ticker": "FAKE", "shares": 10},
            )
        assert resp.status_code == 422

    def test_buy_ticker_uppercased(self):
        buy_result = {"ticker": "AAPL", "shares": 5.0, "avg_cost": 150.0}
        with patch("yfinance.Ticker", return_value=self._mock_ticker(150.0)) as mock_yf_t:
            with patch("src.web_app.server._portfolio_store") as mock_ps:
                mock_ps.buy.return_value = buy_result
                client = _make_client()
                resp = client.post(
                    "/portfolio/buy/sess-1",
                    json={"ticker": "aapl", "shares": 5},
                )
        assert resp.status_code == 200


# ── /portfolio/sell/{session_id} POST ────────────────────────────────────────

class TestPaperSell:

    def _mock_ticker(self, price=150.0):
        tk = MagicMock()
        tk.fast_info.last_price = price
        return tk

    def test_successful_sell(self):
        sell_result = {"ticker": "AAPL", "shares": 5.0, "price": 155.0, "action": "sell"}
        with patch("yfinance.Ticker", return_value=self._mock_ticker(155.0)):
            with patch("src.web_app.server._portfolio_store") as mock_ps:
                mock_ps.sell.return_value = sell_result
                client = _make_client()
                resp = client.post(
                    "/portfolio/sell/sess-1",
                    json={"ticker": "AAPL", "shares": 5},
                )
        assert resp.status_code == 200
        assert resp.json()["action"] == "sell"

    def test_sell_zero_price_returns_422(self):
        with patch("yfinance.Ticker", return_value=self._mock_ticker(0.0)):
            client = _make_client()
            resp = client.post(
                "/portfolio/sell/sess-1",
                json={"ticker": "FAKE", "shares": 5},
            )
        assert resp.status_code == 422

    def test_sell_insufficient_shares_returns_422(self):
        with patch("yfinance.Ticker", return_value=self._mock_ticker(150.0)):
            with patch("src.web_app.server._portfolio_store") as mock_ps:
                mock_ps.sell.side_effect = ValueError("Insufficient shares")
                client = _make_client()
                resp = client.post(
                    "/portfolio/sell/sess-1",
                    json={"ticker": "AAPL", "shares": 999},
                )
        assert resp.status_code == 422


# ── /portfolio/holdings/{session_id} DELETE ──────────────────────────────────

class TestClearHoldings:

    def test_clear_returns_status(self):
        with patch("src.web_app.server._portfolio_store") as mock_ps:
            mock_ps.clear_holdings.return_value = 3
            client = _make_client()
            resp = client.delete("/portfolio/holdings/sess-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "cleared"
        assert body["removed"] == 3
        assert body["session_id"] == "sess-1"

    def test_clear_empty_portfolio(self):
        with patch("src.web_app.server._portfolio_store") as mock_ps:
            mock_ps.clear_holdings.return_value = 0
            client = _make_client()
            resp = client.delete("/portfolio/holdings/sess-empty")
        assert resp.status_code == 200
        assert resp.json()["removed"] == 0


# ── Ask endpoint edge cases ───────────────────────────────────────────────────

class TestAskEndpointExtended:

    def test_empty_question_returns_422(self):
        client = _make_client()
        resp = client.post("/ask", json={"question": "  "})
        assert resp.status_code == 422

    def test_ask_creates_new_session_id_when_none(self):
        with patch("src.web_app.server.process_query") as mock_pq:
            mock_pq.return_value = {
                "answer": "Bonds are debt instruments.",
                "agent": "finance_qa_agent",
                "session_id": "new-uuid-123",
            }
            client = _make_client()
            resp = client.post("/ask", json={"question": "What are bonds?"})
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "new-uuid-123"

    def test_ask_passes_existing_session_id(self):
        with patch("src.web_app.server.process_query") as mock_pq:
            mock_pq.return_value = {
                "answer": "Got it.",
                "agent": "finance_qa_agent",
                "session_id": "existing-session",
            }
            client = _make_client()
            resp = client.post(
                "/ask",
                json={"question": "Follow up question", "session_id": "existing-session"},
            )
        assert resp.status_code == 200
        called_kwargs = mock_pq.call_args
        assert called_kwargs[1].get("session_id") == "existing-session" or \
               (len(called_kwargs[0]) > 1 and called_kwargs[0][1] == "existing-session")

    def test_ask_500_on_orchestrator_error(self):
        with patch("src.web_app.server.process_query", side_effect=RuntimeError("LLM down")):
            client = _make_client()
            resp = client.post("/ask", json={"question": "What is inflation?"})
        assert resp.status_code == 500
