"""Unit tests for src/tools/stock_tools.py"""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_ticker_mock(price=150.25, prev=148.0, info=None, hist=None):
    """Return a MagicMock that looks like a yfinance Ticker."""
    mock_tk = MagicMock()
    mock_tk.fast_info.last_price = price
    mock_tk.fast_info.previous_close = prev
    mock_tk.fast_info.market_cap = 2_500_000_000_000
    mock_tk.fast_info.fifty_two_week_high = 200.0
    mock_tk.fast_info.fifty_two_week_low = 100.0
    mock_tk.info = info or {
        "longName": "Apple Inc.",
        "regularMarketPrice": price,
        "regularMarketPreviousClose": prev,
        "currentPrice": price,
        "previousClose": prev,
        "marketCap": 2_500_000_000_000,
        "trailingPE": 28.5,
        "forwardPE": 25.0,
        "dividendYield": 0.005,
        "fiftyTwoWeekHigh": 200.0,
        "fiftyTwoWeekLow": 100.0,
        "regularMarketVolume": 50_000_000,
        "averageVolume": 60_000_000,
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "totalRevenue": 394_000_000_000,
        "grossMargins": 0.44,
        "operatingMargins": 0.30,
        "profitMargins": 0.25,
        "trailingEps": 6.16,
        "forwardEps": 6.80,
        "debtToEquity": 1.5,
        "currentRatio": 1.1,
        "returnOnEquity": 1.6,
        "returnOnAssets": 0.3,
        "freeCashflow": 90_000_000_000,
        "beta": 1.2,
        "targetMeanPrice": 190.0,
        "recommendationMean": 2.1,
    }
    if hist is None:
        import pandas as pd
        import numpy as np
        dates = pd.date_range("2024-01-01", periods=20, freq="B")
        prices = 140 + np.arange(20, dtype=float)
        df = pd.DataFrame({
            "Close": prices,
            "High": prices + 2,
            "Low": prices - 2,
            "Volume": [1_000_000] * 20,
        }, index=dates)
        mock_tk.history.return_value = df
    else:
        mock_tk.history.return_value = hist

    mock_tk.recommendations = None
    return mock_tk


# ── get_stock_quote ───────────────────────────────────────────────────────────

class TestGetStockQuote:

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_returns_json_string(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock()
        from src.tools.stock_tools import get_stock_quote
        result = get_stock_quote.invoke({"ticker": "AAPL"})
        data = json.loads(result)
        assert "ticker" in data
        assert data["ticker"] == "AAPL"

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_ticker_uppercased(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock()
        from src.tools.stock_tools import get_stock_quote
        result = get_stock_quote.invoke({"ticker": "aapl"})
        data = json.loads(result)
        assert data["ticker"] == "AAPL"

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_price_included(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(price=150.25)
        from src.tools.stock_tools import get_stock_quote
        result = get_stock_quote.invoke({"ticker": "AAPL"})
        data = json.loads(result)
        assert data["price"] == 150.25

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_daily_change_computed(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(price=154.0, prev=148.0)
        from src.tools.stock_tools import get_stock_quote
        result = get_stock_quote.invoke({"ticker": "AAPL"})
        data = json.loads(result)
        # change_pct = (154 - 148) / 148 * 100 ≈ 4.05
        assert "change_pct" in data
        assert abs(data["change_pct"] - 4.05) < 0.1

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_error_handled_gracefully(self, mock_ticker):
        mock_ticker.side_effect = Exception("network error")
        from src.tools.stock_tools import get_stock_quote
        result = get_stock_quote.invoke({"ticker": "BADTICKER"})
        data = json.loads(result)
        assert "error" in data

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_market_cap_included(self, mock_ticker):
        mock = _make_ticker_mock()
        mock.fast_info.market_cap = 3_000_000_000_000
        mock_ticker.return_value = mock
        from src.tools.stock_tools import get_stock_quote
        result = json.loads(get_stock_quote.invoke({"ticker": "AAPL"}))
        assert "market_cap" in result


# ── get_stock_history ─────────────────────────────────────────────────────────

class TestGetStockHistory:

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_returns_json_with_period(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock()
        from src.tools.stock_tools import get_stock_history
        result = get_stock_history.invoke({"ticker": "AAPL", "period": "1mo"})
        data = json.loads(result)
        assert "period" in data
        assert data["period"] == "1mo"

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_total_return_computed(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock()
        from src.tools.stock_tools import get_stock_history
        result = json.loads(get_stock_history.invoke({"ticker": "AAPL", "period": "1y"}))
        assert "total_return_pct" in result

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_empty_history_returns_error(self, mock_ticker):
        import pandas as pd
        mock = _make_ticker_mock()
        mock.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock
        from src.tools.stock_tools import get_stock_history
        result = json.loads(get_stock_history.invoke({"ticker": "EMPTY", "period": "1y"}))
        assert "error" in result

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_error_handled(self, mock_ticker):
        mock_ticker.side_effect = Exception("fail")
        from src.tools.stock_tools import get_stock_history
        result = json.loads(get_stock_history.invoke({"ticker": "X", "period": "1y"}))
        assert "error" in result

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_volatility_included(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock()
        from src.tools.stock_tools import get_stock_history
        result = json.loads(get_stock_history.invoke({"ticker": "AAPL", "period": "1y"}))
        assert "annualized_volatility_pct" in result


# ── get_stock_financials ──────────────────────────────────────────────────────

class TestGetStockFinancials:

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_returns_json(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock()
        from src.tools.stock_tools import get_stock_financials
        result = get_stock_financials.invoke({"ticker": "AAPL"})
        data = json.loads(result)
        assert "ticker" in data
        assert data["ticker"] == "AAPL"

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_revenue_included(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock()
        from src.tools.stock_tools import get_stock_financials
        result = json.loads(get_stock_financials.invoke({"ticker": "AAPL"}))
        assert "revenue" in result

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_error_handled(self, mock_ticker):
        mock_ticker.side_effect = Exception("API down")
        from src.tools.stock_tools import get_stock_financials
        result = json.loads(get_stock_financials.invoke({"ticker": "X"}))
        assert "error" in result

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_with_recommendations(self, mock_ticker):
        import pandas as pd
        mock = _make_ticker_mock()
        recs_df = pd.DataFrame({"period": ["0m"], "strongBuy": [5], "buy": [10], "hold": [3]})
        mock.recommendations = recs_df
        mock_ticker.return_value = mock
        from src.tools.stock_tools import get_stock_financials
        result = json.loads(get_stock_financials.invoke({"ticker": "AAPL"}))
        assert result is not None

    @patch("src.tools.stock_tools.yf.Ticker")
    def test_beta_included(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock()
        from src.tools.stock_tools import get_stock_financials
        result = json.loads(get_stock_financials.invoke({"ticker": "AAPL"}))
        assert "beta" in result


# ── STOCK_TOOLS export ────────────────────────────────────────────────────────

def test_stock_tools_export():
    from src.tools.stock_tools import STOCK_TOOLS
    assert len(STOCK_TOOLS) == 3
    names = {t.name for t in STOCK_TOOLS}
    assert "get_stock_quote" in names
    assert "get_stock_history" in names
    assert "get_stock_financials" in names
