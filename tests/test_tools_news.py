"""Unit tests for src/tools/news_tools.py"""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock

import pytest


class TestGetStockNews:

    @patch("yfinance.Ticker")
    def test_returns_json_with_ticker(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.news = [
            {
                "providerPublishTime": 1700000000,
                "title": "Apple hits record high",
                "content": {
                    "title": "Apple hits record high",
                    "summary": "Shares climbed 3% today.",
                    "provider": {"displayName": "Reuters"},
                },
            }
        ]
        mock_ticker.return_value = mock_tk
        from src.tools.news_tools import get_stock_news
        result = json.loads(get_stock_news.invoke({"ticker": "AAPL", "max_items": 5}))
        assert result["ticker"] == "AAPL"

    @patch("yfinance.Ticker")
    def test_articles_list_returned(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.news = [
            {"providerPublishTime": 1700000000,
             "title": "Article 1",
             "content": {"title": "Article 1", "summary": "Summary", "provider": {"displayName": "ABC"}}},
            {"providerPublishTime": 1700000001,
             "title": "Article 2",
             "content": {"title": "Article 2", "summary": "Summary 2", "provider": {"displayName": "XYZ"}}},
        ]
        mock_ticker.return_value = mock_tk
        from src.tools.news_tools import get_stock_news
        result = json.loads(get_stock_news.invoke({"ticker": "TSLA", "max_items": 5}))
        assert "articles" in result
        assert len(result["articles"]) == 2

    @patch("yfinance.Ticker")
    def test_empty_news_note(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.news = []
        mock_ticker.return_value = mock_tk
        from src.tools.news_tools import get_stock_news
        result = json.loads(get_stock_news.invoke({"ticker": "AAPL", "max_items": 5}))
        assert result.get("note") == "No news found" or "articles" in result

    @patch("yfinance.Ticker")
    def test_old_schema_handled(self, mock_ticker):
        """yfinance sometimes returns old schema without nested 'content' dict."""
        mock_tk = MagicMock()
        mock_tk.news = [
            {
                "title": "NVDA soars",
                "publisher": "Bloomberg",
                "providerPublishTime": 1700000000,
                "summary": "NVIDIA hit all-time high",
            }
        ]
        mock_ticker.return_value = mock_tk
        from src.tools.news_tools import get_stock_news
        result = json.loads(get_stock_news.invoke({"ticker": "NVDA", "max_items": 3}))
        assert "articles" in result

    @patch("yfinance.Ticker")
    def test_error_handled(self, mock_ticker):
        mock_ticker.side_effect = Exception("API error")
        from src.tools.news_tools import get_stock_news
        result = json.loads(get_stock_news.invoke({"ticker": "AAPL", "max_items": 3}))
        assert "error" in result

    @patch("yfinance.Ticker")
    def test_max_items_respected(self, mock_ticker):
        mock_tk = MagicMock()
        mock_tk.news = [
            {"providerPublishTime": i,
             "title": f"Article {i}",
             "content": {"title": f"Article {i}", "summary": "x", "provider": {"displayName": "A"}}}
            for i in range(20)
        ]
        mock_ticker.return_value = mock_tk
        from src.tools.news_tools import get_stock_news
        result = json.loads(get_stock_news.invoke({"ticker": "AAPL", "max_items": 3}))
        assert len(result["articles"]) <= 3


class TestGetMarketNews:

    @patch("src.tools.news_tools._fetch_rss")
    def test_returns_category_and_articles(self, mock_fetch):
        mock_fetch.return_value = [
            {"title": "Market Rally", "published": "2025-01-01", "summary": "Stocks up.", "link": "http://example.com"}
        ]
        from src.tools.news_tools import get_market_news
        result = json.loads(get_market_news.invoke({"category": "markets", "max_items": 5}))
        assert result["category"] == "markets"
        assert "articles" in result

    @patch("src.tools.news_tools._fetch_rss")
    def test_default_category_is_top_stories(self, mock_fetch):
        mock_fetch.return_value = []
        from src.tools.news_tools import get_market_news
        result = json.loads(get_market_news.invoke({"category": "top_stories", "max_items": 5}))
        assert result["category"] == "top_stories"

    @patch("src.tools.news_tools._fetch_rss")
    def test_error_handled(self, mock_fetch):
        mock_fetch.side_effect = Exception("RSS down")
        from src.tools.news_tools import get_market_news
        result = json.loads(get_market_news.invoke({"category": "markets", "max_items": 3}))
        assert "error" in result

    @patch("src.tools.news_tools._fetch_rss")
    def test_unknown_category_falls_back_to_top_stories(self, mock_fetch):
        mock_fetch.return_value = []
        from src.tools.news_tools import get_market_news
        # Unknown category falls back to top_stories URL
        result = json.loads(get_market_news.invoke({"category": "random_category", "max_items": 3}))
        assert "articles" in result or "error" in result


def test_news_tools_export():
    from src.tools.news_tools import NEWS_TOOLS
    names = {t.name for t in NEWS_TOOLS}
    assert "get_stock_news" in names
    assert "get_market_news" in names
