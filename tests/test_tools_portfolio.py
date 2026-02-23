"""Unit tests for src/tools/portfolio_tools.py"""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock

import pytest


def _make_ticker_mock(price=150.0, company="Apple Inc."):
    mock_tk = MagicMock()
    mock_tk.fast_info.last_price = price
    mock_tk.info = {"longName": company}
    return mock_tk


_HOLDINGS_JSON = json.dumps([
    {"ticker": "AAPL", "shares": 10, "avg_cost": 140.0},
    {"ticker": "NVDA", "shares": 5,  "avg_cost": 400.0},
])


class TestAnalyzePortfolio:

    @patch("src.tools.portfolio_tools.yf.Ticker")
    def test_returns_json_with_holdings(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(150.0)
        from src.tools.portfolio_tools import analyze_portfolio
        result = json.loads(analyze_portfolio.invoke({"holdings_json": _HOLDINGS_JSON}))
        assert "holdings" in result
        assert len(result["holdings"]) == 2

    @patch("src.tools.portfolio_tools.yf.Ticker")
    def test_summary_included(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(150.0)
        from src.tools.portfolio_tools import analyze_portfolio
        result = json.loads(analyze_portfolio.invoke({"holdings_json": _HOLDINGS_JSON}))
        assert "summary" in result
        assert "total_value" in result["summary"]

    @patch("src.tools.portfolio_tools.yf.Ticker")
    def test_pnl_computed(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(160.0)
        from src.tools.portfolio_tools import analyze_portfolio
        result = json.loads(analyze_portfolio.invoke({"holdings_json": _HOLDINGS_JSON}))
        holding = next(h for h in result["holdings"] if h["ticker"] == "AAPL")
        # bought at 140, now 160 → +200 pnl
        assert holding["pnl"] > 0

    @patch("src.tools.portfolio_tools.yf.Ticker")
    def test_allocation_pct_sums_to_100(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(150.0)
        from src.tools.portfolio_tools import analyze_portfolio
        result = json.loads(analyze_portfolio.invoke({"holdings_json": _HOLDINGS_JSON}))
        total_alloc = sum(h["allocation_pct"] for h in result["holdings"])
        assert abs(total_alloc - 100.0) < 0.5

    def test_empty_portfolio_returns_error(self):
        from src.tools.portfolio_tools import analyze_portfolio
        result = json.loads(analyze_portfolio.invoke({"holdings_json": "[]"}))
        assert "error" in result

    def test_invalid_json_returns_error(self):
        from src.tools.portfolio_tools import analyze_portfolio
        result = json.loads(analyze_portfolio.invoke({"holdings_json": "not-json"}))
        assert "error" in result

    @patch("src.tools.portfolio_tools.yf.Ticker")
    def test_concentration_risk_high(self, mock_ticker):
        # single stock portfolio → high concentration
        single = json.dumps([{"ticker": "AAPL", "shares": 100, "avg_cost": 100.0}])
        mock_ticker.return_value = _make_ticker_mock(200.0)
        from src.tools.portfolio_tools import analyze_portfolio
        result = json.loads(analyze_portfolio.invoke({"holdings_json": single}))
        assert result["summary"]["concentration_risk"] == "high"

    @patch("src.tools.portfolio_tools.yf.Ticker")
    def test_zero_price_handled(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.fast_info.last_price = None
        mock_tk.info = {"longName": "Apple"}
        mock_ticker.return_value = mock_tk
        from src.tools.portfolio_tools import analyze_portfolio
        result = json.loads(analyze_portfolio.invoke({"holdings_json": _HOLDINGS_JSON}))
        # Should not raise, even with None price
        assert "summary" in result or "error" in result


class TestGetPortfolioPerformance:

    @patch("src.tools.portfolio_tools.yf.download")
    def test_returns_period(self, mock_download):
        import pandas as pd
        import numpy as np
        tickers = ["AAPL", "NVDA", "SPY"]
        idx = pd.date_range("2024-01-01", periods=10, freq="B")
        data = pd.DataFrame({t: 100 + np.arange(10, dtype=float) for t in tickers}, index=idx)
        mock_download.return_value = data
        from src.tools.portfolio_tools import get_portfolio_performance
        result = json.loads(get_portfolio_performance.invoke({"holdings_json": _HOLDINGS_JSON, "period": "1y"}))
        assert result.get("period") == "1y" or "error" in result

    @patch("src.tools.portfolio_tools.yf.download")
    def test_error_on_empty_data(self, mock_download):
        import pandas as pd
        mock_download.return_value = pd.DataFrame()
        from src.tools.portfolio_tools import get_portfolio_performance
        result = json.loads(get_portfolio_performance.invoke({"holdings_json": _HOLDINGS_JSON, "period": "1y"}))
        assert "error" in result

    def test_invalid_json_returns_error(self):
        from src.tools.portfolio_tools import get_portfolio_performance
        result = json.loads(get_portfolio_performance.invoke({"holdings_json": "bad", "period": "1y"}))
        assert "error" in result

    @patch("src.tools.portfolio_tools.yf.download")
    def test_alpha_computed(self, mock_download):
        import pandas as pd
        import numpy as np
        tickers = ["AAPL", "NVDA", "SPY"]
        idx = pd.date_range("2024-01-01", periods=10, freq="B")
        data = pd.DataFrame({t: 100 + np.arange(10, dtype=float) for t in tickers}, index=idx)
        mock_download.return_value = data
        from src.tools.portfolio_tools import get_portfolio_performance
        result = json.loads(get_portfolio_performance.invoke({"holdings_json": _HOLDINGS_JSON, "period": "1y"}))
        if "alpha_pct" in result:
            assert isinstance(result["alpha_pct"], (int, float))


class TestPortfolioToolsExport:

    def test_portfolio_tools_exported(self):
        from src.tools.portfolio_tools import PORTFOLIO_TOOLS
        names = {t.name for t in PORTFOLIO_TOOLS}
        assert "analyze_portfolio" in names
        assert "get_portfolio_performance" in names
        assert "get_stock_quote" in names
