"""
LangChain @tool wrappers for financial news.

Uses yfinance for ticker-specific news and standard-library urllib + ElementTree
for market-wide Yahoo Finance RSS feeds. No additional API keys required.

Exported collections
--------------------
NEWS_TOOLS = [get_stock_news, get_market_news]
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET

from langchain_core.tools import tool


# ── RSS feed registry ─────────────────────────────────────────────────────────

_RSS_FEEDS = {
    "top_stories": "https://finance.yahoo.com/rss/topfinstories",
    "markets":     "https://finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US",
    "technology":  "https://finance.yahoo.com/rss/2.0/headline?s=%5ENDX&region=US&lang=en-US",
    "crypto":      "https://finance.yahoo.com/rss/2.0/headline?s=BTC-USD&region=US&lang=en-US",
    "economy":     "https://finance.yahoo.com/rss/2.0/headline?s=%5ETNX&region=US&lang=en-US",
}

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; finance-assistant/1.0)"}


def _fetch_rss(url: str, max_items: int) -> list[dict]:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        content = resp.read()

    root = ET.fromstring(content)
    articles: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link")  or "").strip()
        pub   = (item.findtext("pubDate") or "").strip()
        desc  = re.sub(r"<[^>]+>", " ", item.findtext("description") or "").strip()
        if len(desc) > 350:
            desc = desc[:350] + "…"
        if title:
            articles.append({"title": title, "published": pub, "summary": desc, "link": link})
        if len(articles) >= max_items:
            break
    return articles


# ── tools ─────────────────────────────────────────────────────────────────────

@tool
def get_stock_news(ticker: str, max_items: int = 8) -> str:
    """
    Fetch recent news headlines for a specific stock ticker.

    Provide the ticker symbol (e.g. 'AAPL', 'TSLA', 'NVDA').
    Returns up to max_items recent articles with title, publisher, and publish date.
    """
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker.upper().strip())
        raw_news = tk.news or []

        articles: list[dict] = []
        for item in raw_news[:max_items]:
            pub_ts   = item.get("providerPublishTime", 0)
            pub_date = (
                time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(pub_ts)) if pub_ts else "Unknown"
            )
            # Handle both old and new yfinance news schema
            content  = item.get("content", item)
            title    = content.get("title", item.get("title", "No title"))
            summary  = content.get("summary", item.get("summary", ""))
            provider = content.get("provider", {})
            publisher = (
                provider.get("displayName", "") if isinstance(provider, dict)
                else item.get("publisher", "Unknown")
            )
            articles.append({
                "title":     title,
                "publisher": publisher,
                "published": pub_date,
                "summary":   summary[:300] if summary else "",
            })

        if not articles:
            return json.dumps({"ticker": ticker.upper(), "articles": [], "note": "No news found"})

        return json.dumps({"ticker": ticker.upper(), "articles": articles})
    except Exception as e:
        return json.dumps({"error": str(e), "ticker": ticker})


@tool
def get_market_news(category: str = "top_stories", max_items: int = 8) -> str:
    """
    Fetch market-wide financial news headlines from Yahoo Finance RSS feeds.

    category options: top_stories, markets, technology, crypto, economy
    Returns up to max_items articles with title, summary, published date, and link.
    """
    url = _RSS_FEEDS.get(category, _RSS_FEEDS["top_stories"])
    try:
        articles = _fetch_rss(url, max_items)
        return json.dumps({"category": category, "articles": articles})
    except Exception as e:
        return json.dumps({"error": str(e), "category": category})


# ── exported collection ───────────────────────────────────────────────────────

NEWS_TOOLS = [get_stock_news, get_market_news]
