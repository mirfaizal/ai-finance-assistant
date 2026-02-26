"""
Tests for the MCP Server (src/mcp_server/server.py).

These tests verify that each MCP tool:
1. Can be imported without error
2. Returns the expected data shape when called with mocked backend tools
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


# ── helpers ───────────────────────────────────────────────────────────────────

_MOCK_STOCK_JSON = json.dumps({
    "ticker": "AAPL",
    "price": 225.50,
    "change_pct": 1.23,
    "market_cap": "3.4T",
    "pe_ratio": 35.2,
})

_MOCK_MARKET_JSON = json.dumps({
    "SPY": {"price": 689.0, "change_pct": 0.68, "name": "SPDR S&P 500 ETF"},
    "QQQ": {"price": 523.0, "change_pct": 1.12, "name": "Invesco QQQ"},
})

_MOCK_PORTFOLIO_JSON = json.dumps({
    "holdings": [
        {"ticker": "AAPL", "current_price": 225.50, "pnl": 755.0, "allocation_pct": 100.0}
    ],
    "summary": {
        "total_value": 2255.0,
        "total_pnl": 755.0,
        "total_pnl_pct": 50.3,
        "concentration_risk": "high",
    },
})

_MOCK_NEWS_JSON = json.dumps({
    "articles": [
        {"title": "Markets rise on Fed signals", "ticker": "SPY", "published_at": "2026-02-25T18:00:00Z"},
    ],
    "count": 1,
})

_MOCK_SECTOR_JSON = json.dumps([
    {"sector": "Technology", "etf": "XLK", "return_pct": 5.2},
    {"sector": "Energy", "etf": "XLE", "return_pct": -1.3},
])


# ── import guard ──────────────────────────────────────────────────────────────

class TestMCPServerImport:
    """The MCP server module should import cleanly."""

    def test_server_can_be_imported(self):
        # Heavy imports (langgraph, openai) are only triggered when tools are
        # *called*, not when the module is imported.  fastmcp itself is a
        # lightweight decorator framework.
        import src.mcp_server.server as mcp_server  # noqa: F401
        assert hasattr(mcp_server, "mcp")
        assert hasattr(mcp_server, "ask_finance_assistant")
        assert hasattr(mcp_server, "get_stock_quote")
        assert hasattr(mcp_server, "get_market_overview")
        assert hasattr(mcp_server, "analyze_portfolio")
        assert hasattr(mcp_server, "get_financial_news")
        assert hasattr(mcp_server, "get_sector_performance")


# ── tool tests ────────────────────────────────────────────────────────────────

class TestAskFinanceAssistant:
    """ask_finance_assistant should return a formatted string with agent name."""

    def test_returns_agent_and_answer(self):
        mock_result = {
            "answer": "Diversification spreads risk across asset classes.",
            "agent": "finance_qa_agent",
            "session_id": "test-sid-123",
        }
        with patch("src.workflow.orchestrator.process_query", return_value=mock_result):
            from src.mcp_server.server import ask_finance_assistant
            result = ask_finance_assistant("What is diversification?")

        assert "finance_qa_agent" in result
        assert "Diversification" in result
        assert "test-sid-123" in result

    def test_returns_string(self):
        mock_result = {
            "answer": "Compound interest grows exponentially.",
            "agent": "finance_qa_agent",
            "session_id": "abc",
        }
        with patch("src.workflow.orchestrator.process_query", return_value=mock_result):
            from src.mcp_server.server import ask_finance_assistant
            result = ask_finance_assistant("Explain compound interest")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_passes_session_id(self):
        mock_result = {
            "answer": "The wash sale rule prevents claiming losses...",
            "agent": "tax_education_agent",
            "session_id": "existing-sid",
        }
        captured = {}
        def _capture(**kwargs):
            captured.update(kwargs)
            return mock_result

        with patch("src.workflow.orchestrator.process_query", side_effect=_capture):
            from src.mcp_server.server import ask_finance_assistant
            ask_finance_assistant("Wash sale rule?", session_id="existing-sid")

        assert captured.get("session_id") == "existing-sid"

    def test_empty_session_id_becomes_none(self):
        mock_result = {
            "answer": "ETFs are baskets of securities.",
            "agent": "finance_qa_agent",
            "session_id": "new-sid",
        }
        captured = {}
        def _capture(**kwargs):
            captured.update(kwargs)
            return mock_result

        with patch("src.workflow.orchestrator.process_query", side_effect=_capture):
            from src.mcp_server.server import ask_finance_assistant
            ask_finance_assistant("What is an ETF?", session_id="")

        assert captured.get("session_id") is None


class TestGetStockQuote:
    """get_stock_quote should invoke the stock tool and return a JSON string."""

    def test_returns_json_string(self):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = _MOCK_STOCK_JSON

        with patch("src.tools.stock_tools.get_stock_quote", mock_tool):
            from src.mcp_server.server import get_stock_quote
            result = get_stock_quote("AAPL")

        assert isinstance(result, str)
        data = json.loads(result)
        assert "price" in data

    def test_uppercases_ticker(self):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = _MOCK_STOCK_JSON

        with patch("src.tools.stock_tools.get_stock_quote", mock_tool):
            from src.mcp_server.server import get_stock_quote
            get_stock_quote("aapl")

        call_kwargs = mock_tool.invoke.call_args[0][0]
        assert call_kwargs["ticker"] == "AAPL"


class TestGetMarketOverview:
    """get_market_overview should return JSON with known tickers."""

    def test_returns_json_string(self):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = _MOCK_MARKET_JSON

        with patch("src.tools.market_tools.get_market_overview", mock_tool):
            from src.mcp_server.server import get_market_overview
            result = get_market_overview()

        assert isinstance(result, str)
        data = json.loads(result)
        assert "SPY" in data


class TestAnalyzePortfolio:
    """analyze_portfolio should validate JSON input and return analysis."""

    _valid_holdings = '[{"ticker":"AAPL","shares":10,"avg_cost":150}]'

    def test_valid_holdings_returns_analysis(self):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = _MOCK_PORTFOLIO_JSON

        with patch("src.tools.portfolio_tools.analyze_portfolio", mock_tool):
            from src.mcp_server.server import analyze_portfolio
            result = analyze_portfolio(self._valid_holdings)

        assert isinstance(result, str)
        data = json.loads(result)
        assert "summary" in data

    def test_invalid_json_returns_error(self):
        from src.mcp_server.server import analyze_portfolio
        result = analyze_portfolio("not json at all")
        data = json.loads(result)
        assert "error" in data

    def test_empty_array_is_valid_json(self):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = json.dumps({"holdings": [], "summary": {}})

        with patch("src.tools.portfolio_tools.analyze_portfolio", mock_tool):
            from src.mcp_server.server import analyze_portfolio
            result = analyze_portfolio("[]")

        assert isinstance(result, str)


class TestGetFinancialNews:
    """get_financial_news should return news articles as JSON."""

    def test_default_tickers_returns_json(self):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = _MOCK_NEWS_JSON

        with patch("src.tools.news_tools.get_market_news", mock_tool):
            from src.mcp_server.server import get_financial_news
            result = get_financial_news()

        assert isinstance(result, str)
        data = json.loads(result)
        assert "articles" in data

    def test_result_is_string(self):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = _MOCK_NEWS_JSON

        with patch("src.tools.news_tools.get_market_news", mock_tool):
            from src.mcp_server.server import get_financial_news
            result = get_financial_news("SPY,AAPL,MSFT,NVDA,TSLA")  # default

        assert isinstance(result, str)


class TestGetSectorPerformance:
    """get_sector_performance should return sorted sector data."""

    def test_returns_json_string(self):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = _MOCK_SECTOR_JSON

        with patch("src.tools.market_tools.get_sector_performance", mock_tool):
            from src.mcp_server.server import get_sector_performance
            result = get_sector_performance("1mo")

        assert isinstance(result, str)

    def test_invalid_period_defaults_to_1mo(self):
        mock_tool = MagicMock()
        mock_tool.invoke.return_value = _MOCK_SECTOR_JSON

        with patch("src.tools.market_tools.get_sector_performance", mock_tool):
            from src.mcp_server.server import get_sector_performance
            get_sector_performance("BAD_PERIOD")

        call_kwargs = mock_tool.invoke.call_args[0][0]
        assert call_kwargs["period"] == "1mo"

    def test_valid_periods_are_passed_through(self):
        for period in ("1d", "5d", "1mo", "3mo", "6mo", "1y"):
            mock_tool = MagicMock()
            mock_tool.invoke.return_value = _MOCK_SECTOR_JSON

            with patch("src.tools.market_tools.get_sector_performance", mock_tool):
                from src.mcp_server.server import get_sector_performance
                get_sector_performance(period)

            call_kwargs = mock_tool.invoke.call_args[0][0]
            assert call_kwargs["period"] == period
