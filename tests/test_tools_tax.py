"""Unit tests for src/tools/tax_tools.py"""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock

import pytest


def _make_ticker_mock(price=200.0):
    mock_tk = MagicMock()
    mock_tk.fast_info.last_price = price
    return mock_tk


class TestCalculateCapitalGains:

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_returns_json(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(200.0)
        from src.tools.tax_tools import calculate_capital_gains
        result = json.loads(calculate_capital_gains.invoke({
            "ticker": "AAPL",
            "shares": 10,
            "avg_cost_per_share": 150.0,
            "holding_period_days": 400,
        }))
        assert "ticker" in result
        assert result["ticker"] == "AAPL"

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_long_term_classification(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(200.0)
        from src.tools.tax_tools import calculate_capital_gains
        result = json.loads(calculate_capital_gains.invoke({
            "ticker": "AAPL",
            "shares": 10,
            "avg_cost_per_share": 150.0,
            "holding_period_days": 400,
        }))
        assert result["is_long_term"] is True

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_short_term_classification(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(200.0)
        from src.tools.tax_tools import calculate_capital_gains
        result = json.loads(calculate_capital_gains.invoke({
            "ticker": "AAPL",
            "shares": 10,
            "avg_cost_per_share": 150.0,
            "holding_period_days": 200,
        }))
        assert result["is_long_term"] is False

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_gain_loss_computed(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(200.0)
        from src.tools.tax_tools import calculate_capital_gains
        result = json.loads(calculate_capital_gains.invoke({
            "ticker": "AAPL",
            "shares": 10,
            "avg_cost_per_share": 150.0,
            "holding_period_days": 400,
        }))
        # (200-150)*10 = 500 gain
        assert result["gain_loss"] == 500.0

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_zero_tax_on_loss(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(100.0)  # below cost
        from src.tools.tax_tools import calculate_capital_gains
        result = json.loads(calculate_capital_gains.invoke({
            "ticker": "AAPL",
            "shares": 10,
            "avg_cost_per_share": 150.0,
            "holding_period_days": 400,
        }))
        assert result["estimated_tax"] == 0.0

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_none_price_returns_error(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.fast_info.last_price = None
        mock_ticker.return_value = mock_tk
        from src.tools.tax_tools import calculate_capital_gains
        result = json.loads(calculate_capital_gains.invoke({
            "ticker": "AAPL",
            "shares": 10,
            "avg_cost_per_share": 150.0,
            "holding_period_days": 400,
        }))
        assert "error" in result

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_error_handled(self, mock_ticker):
        mock_ticker.side_effect = Exception("network fail")
        from src.tools.tax_tools import calculate_capital_gains
        result = json.loads(calculate_capital_gains.invoke({
            "ticker": "X",
            "shares": 10,
            "avg_cost_per_share": 150.0,
            "holding_period_days": 200,
        }))
        assert "error" in result

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_note_included(self, mock_ticker):
        mock_ticker.return_value = _make_ticker_mock(200.0)
        from src.tools.tax_tools import calculate_capital_gains
        result = json.loads(calculate_capital_gains.invoke({
            "ticker": "AAPL",
            "shares": 10,
            "avg_cost_per_share": 150.0,
            "holding_period_days": 400,
        }))
        assert "note" in result


class TestFindTaxLossOpportunities:

    _HOLDINGS = json.dumps([
        {"ticker": "AAPL", "shares": 10, "avg_cost": 200.0},  # loss: now 150
        {"ticker": "NVDA", "shares": 5, "avg_cost": 100.0},   # gain: now 400
    ])

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_returns_candidates(self, mock_ticker):
        mock_tk = MagicMock()
        # AAPL at 150 (below 200 cost) → loser; NVDA at 400 (above 100) → winner
        call_count = [0]
        def side_effect(sym):
            m = MagicMock()
            if sym == "AAPL":
                m.fast_info.last_price = 150.0
            else:
                m.fast_info.last_price = 400.0
            return m
        mock_ticker.side_effect = side_effect
        from src.tools.tax_tools import find_tax_loss_opportunities
        result = json.loads(find_tax_loss_opportunities.invoke({"holdings_json": self._HOLDINGS}))
        assert "tax_loss_candidates" in result
        assert result["num_candidates"] == 1

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_no_losers(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.fast_info.last_price = 500.0  # everything up
        mock_ticker.return_value = mock_tk
        from src.tools.tax_tools import find_tax_loss_opportunities
        holdings = json.dumps([{"ticker": "AAPL", "shares": 10, "avg_cost": 100.0}])
        result = json.loads(find_tax_loss_opportunities.invoke({"holdings_json": holdings}))
        assert result["num_candidates"] == 0

    def test_invalid_json_returns_error(self):
        from src.tools.tax_tools import find_tax_loss_opportunities
        result = json.loads(find_tax_loss_opportunities.invoke({"holdings_json": "bad-json"}))
        assert "error" in result

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_wash_sale_warning_included(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.fast_info.last_price = 50.0
        mock_ticker.return_value = mock_tk
        from src.tools.tax_tools import find_tax_loss_opportunities
        holdings = json.dumps([{"ticker": "AAPL", "shares": 10, "avg_cost": 200.0}])
        result = json.loads(find_tax_loss_opportunities.invoke({"holdings_json": holdings}))
        assert "wash_sale_warning" in result

    @patch("src.tools.tax_tools.yf.Ticker")
    def test_total_harvestable_negative(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.fast_info.last_price = 50.0
        mock_ticker.return_value = mock_tk
        from src.tools.tax_tools import find_tax_loss_opportunities
        holdings = json.dumps([{"ticker": "AAPL", "shares": 10, "avg_cost": 200.0}])
        result = json.loads(find_tax_loss_opportunities.invoke({"holdings_json": holdings}))
        assert result["total_harvestable_loss"] < 0


def test_tax_tools_export():
    from src.tools.tax_tools import TAX_TOOLS
    names = {t.name for t in TAX_TOOLS}
    assert "calculate_capital_gains" in names
    assert "find_tax_loss_opportunities" in names
