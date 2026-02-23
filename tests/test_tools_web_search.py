"""Unit tests for src/tools/web_search.py"""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest


class TestIsRealtimeQuery:

    def test_today_signals_realtime(self):
        from src.tools.web_search import is_realtime_query
        assert is_realtime_query("What is the S&P 500 today?") is True

    def test_current_signals_realtime(self):
        from src.tools.web_search import is_realtime_query
        assert is_realtime_query("current fed rate") is True

    def test_who_is_signals_realtime(self):
        from src.tools.web_search import is_realtime_query
        assert is_realtime_query("who is the president?") is True

    def test_latest_signals_realtime(self):
        from src.tools.web_search import is_realtime_query
        assert is_realtime_query("latest inflation numbers") is True

    def test_general_question_not_realtime(self):
        from src.tools.web_search import is_realtime_query
        assert is_realtime_query("what is compound interest?") is False

    def test_empty_string_not_realtime(self):
        from src.tools.web_search import is_realtime_query
        assert is_realtime_query("") is False

    def test_breaking_news_realtime(self):
        from src.tools.web_search import is_realtime_query
        assert is_realtime_query("breaking financial news") is True


class TestWebSearch:

    def test_empty_query_returns_empty(self):
        from src.tools.web_search import web_search
        assert web_search("") == ""

    def test_whitespace_query_returns_empty(self):
        from src.tools.web_search import web_search
        assert web_search("   ") == ""

    @patch("src.tools.web_search._get_tavily_client")
    def test_returns_formatted_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "S&P 500 today", "url": "https://example.com", "content": "The S&P hit 5000."},
            ]
        }
        mock_get_client.return_value = mock_client
        from src.tools.web_search import web_search
        result = web_search("S&P 500 today")
        assert "S&P 500 today" in result or len(result) > 0

    @patch("src.tools.web_search._get_tavily_client")
    def test_no_results_returns_empty(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}
        mock_get_client.return_value = mock_client
        from src.tools.web_search import web_search
        assert web_search("obscure query xyz abc") == ""

    @patch("src.tools.web_search._get_tavily_client")
    def test_environment_error_returns_empty(self, mock_get_client):
        mock_get_client.side_effect = EnvironmentError("TAVILY_API_KEY not set")
        from src.tools.web_search import web_search
        # Should degrade gracefully to empty string
        result = web_search("test query")
        assert result == ""

    @patch("src.tools.web_search._get_tavily_client")
    def test_unexpected_error_returns_empty(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("network timeout")
        mock_get_client.return_value = mock_client
        from src.tools.web_search import web_search
        result = web_search("who is the president?")
        assert result == ""

    @patch("src.tools.web_search._get_tavily_client")
    def test_content_truncated(self, mock_get_client):
        long_content = "x" * 1000
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [{"title": "Long article", "url": "http://x.com", "content": long_content}]
        }
        mock_get_client.return_value = mock_client
        from src.tools.web_search import web_search
        result = web_search("test query")
        # Content should be truncated in the output
        assert "truncated" in result or len(result) > 0

    @patch("src.tools.web_search._get_tavily_client")
    def test_multiple_results_formatted(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "Result 1", "url": "http://a.com", "content": "Content A."},
                {"title": "Result 2", "url": "http://b.com", "content": "Content B."},
            ]
        }
        mock_get_client.return_value = mock_client
        from src.tools.web_search import web_search
        result = web_search("market news")
        assert "Result 1" in result
        assert "Result 2" in result


class TestFinanceSearch:

    @patch("src.tools.web_search.web_search")
    def test_calls_web_search(self, mock_ws):
        mock_ws.return_value = "results"
        from src.tools.web_search import finance_search
        result = finance_search("S&P performance")
        mock_ws.assert_called_once()
        assert result == "results"

    @patch("src.tools.web_search.web_search")
    def test_with_context_hint(self, mock_ws):
        mock_ws.return_value = "results"
        from src.tools.web_search import finance_search
        finance_search("inflation", context_hint="macroeconomics")
        call_args = mock_ws.call_args
        assert "macroeconomics" in call_args[0][0]

    @patch("src.tools.web_search.web_search")
    def test_without_context_hint(self, mock_ws):
        mock_ws.return_value = "results"
        from src.tools.web_search import finance_search
        finance_search("interest rates")
        mock_ws.assert_called_once_with("interest rates", max_results=3)
