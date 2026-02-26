"""
AI Finance Assistant — MCP Server
==================================
Exposes core finance assistant capabilities as Model Context Protocol (MCP)
tools, enabling Claude Desktop and other MCP clients to call them natively.

Requires: fastmcp  (pip install fastmcp)

─────────────────────────────────────────
LOCAL DEV (stdio — MCP Inspector in browser):
    fastmcp dev src/mcp_server/server.py

LOCAL DEV (direct run — stdio):
    python src/mcp_server/server.py

─────────────────────────────────────────
DOCKER / SSE MODE (HTTP transport):
    MCP_TRANSPORT=sse MCP_PORT=8001 python src/mcp_server/server.py
    # Server listens at: http://localhost:8001/sse

─────────────────────────────────────────
CLAUDE DESKTOP CONFIG — local Python process (stdio):
{
  "mcpServers": {
    "ai-finance-assistant": {
      "command": "python",
      "args": ["src/mcp_server/server.py"],
      "cwd": "/absolute/path/to/ai_finance_assistant",
      "env": { "OPENAI_API_KEY": "sk-..." }
    }
  }
}

─────────────────────────────────────────
CLAUDE DESKTOP CONFIG — Docker SSE (after docker-compose up):
{
  "mcpServers": {
    "ai-finance-assistant": {
      "url": "http://localhost:8001/sse"
    }
  }
}
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so src.* imports resolve correctly
# when the MCP server is launched directly (e.g. `fastmcp dev ...`).
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env early (before any src.* imports that read env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env")
except ImportError:
    pass  # dotenv optional — env vars may be set externally

from fastmcp import FastMCP

mcp = FastMCP(
    name="AI Finance Assistant",
    instructions=(
        "A multi-agent AI system specialising in financial education. "
        "Use these tools to get stock quotes, market overviews, portfolio analysis, "
        "financial news, and conversational finance Q&A. "
        "All information is for educational purposes only — not financial advice."
    ),
)


# ── Tool 1: Full conversational finance Q&A ────────────────────────────────

@mcp.tool()
def ask_finance_assistant(question: str, session_id: str = "") -> str:
    """
    Ask any finance question and get a detailed, expert answer.

    Routes your question to the most appropriate specialist agent:
    - stock_agent          -> stock prices, PE ratios, earnings
    - market_analysis_agent -> market trends, indices, sectors
    - portfolio_analysis_agent -> diversification, allocation, risk
    - tax_education_agent  -> capital gains, IRS rules, deductions
    - goal_planning_agent  -> retirement, savings, budgeting
    - news_synthesizer_agent -> latest market news
    - finance_qa_agent     -> general concepts (ETFs, bonds, etc.)

    Supports multi-turn conversations: pass the same session_id across calls
    to maintain context.

    Args:
        question:   The finance question to ask.
        session_id: Optional session UUID from a prior call (for multi-turn).

    Returns:
        A detailed answer with the agent name that handled it.
    """
    from src.workflow.orchestrator import process_query

    result = process_query(
        question=question,
        session_id=session_id if session_id.strip() else None,
    )
    agent = result.get("agent", "finance_qa_agent")
    answer = result.get("answer", "")
    sid = result.get("session_id", "")

    return (
        f"**Agent:** {agent}\n"
        f"**Session:** {sid}\n\n"
        f"{answer}"
    )


# ── Tool 2: Live stock quote ───────────────────────────────────────────────

@mcp.tool()
def get_stock_quote(ticker: str) -> str:
    """
    Get a real-time stock quote with key financial metrics.

    Returns current price, daily change %, market cap, P/E ratio,
    52-week range, volume, and analyst price target.
    Data is sourced from yfinance (no API key required).

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL", "NVDA", "TSLA", "BTC-USD"

    Returns:
        JSON string with price, change_pct, market_cap, pe_ratio,
        week_52_range, volume, and analyst_target.
    """
    from src.tools.stock_tools import get_stock_quote as _get_quote

    raw = _get_quote.invoke({"ticker": ticker.upper().strip()})
    return raw


# ── Tool 3: Market overview ────────────────────────────────────────────────

@mcp.tool()
def get_market_overview() -> str:
    """
    Get a real-time snapshot of major market indices and asset classes.

    Returns live price and daily % change for SPY, QQQ, DIA, IWM,
    VIX, 10-year Treasury yield, GLD, and USO.
    Data is sourced from yfinance (no API key required).

    Returns:
        JSON string mapping each symbol to {price, change_pct, name}.
    """
    from src.tools.market_tools import get_market_overview as _get_overview

    return _get_overview.invoke({})


# ── Tool 4: Portfolio analysis ─────────────────────────────────────────────

@mcp.tool()
def analyze_portfolio(holdings_json: str) -> str:
    """
    Analyze a stock portfolio with live prices to get P&L and allocation.

    Args:
        holdings_json: JSON array of holdings, each with:
                       {"ticker": "AAPL", "shares": 10, "avg_cost": 150.0}
                       Example:
                       '[{"ticker":"AAPL","shares":10,"avg_cost":150},
                         {"ticker":"NVDA","shares":5,"avg_cost":500}]'

    Returns:
        JSON string with per-holding details and a portfolio summary.
    """
    from src.tools.portfolio_tools import analyze_portfolio as _analyze

    try:
        json.loads(holdings_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid JSON: {exc}"})

    return _analyze.invoke({"holdings_json": holdings_json})


# ── Tool 5: Financial news ─────────────────────────────────────────────────

@mcp.tool()
def get_financial_news(tickers: str = "SPY,AAPL,MSFT,NVDA,TSLA") -> str:
    """
    Get the latest financial news headlines for given tickers.

    Args:
        tickers: Comma-separated ticker symbols (default: SPY,AAPL,MSFT,NVDA,TSLA)

    Returns:
        JSON string with an "articles" array.
    """
    from src.tools.news_tools import get_market_news as _get_news

    raw = _get_news.invoke({})
    requested = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if requested != ["SPY", "AAPL", "MSFT", "NVDA", "TSLA"]:
        from src.tools.news_tools import get_stock_news as _get_stock_news
        articles = []
        seen: set = set()
        for ticker in requested:
            try:
                ticker_raw = _get_stock_news.invoke({"ticker": ticker})
                ticker_data = json.loads(ticker_raw)
                for headline in ticker_data.get("headlines", []):
                    if headline not in seen:
                        seen.add(headline)
                        articles.append({"title": headline, "ticker": ticker})
            except Exception:
                continue
        return json.dumps({"articles": articles, "count": len(articles)})

    return raw


# ── Tool 6: Sector performance ─────────────────────────────────────────────

@mcp.tool()
def get_sector_performance(period: str = "1mo") -> str:
    """
    Get performance of all 11 S&P 500 market sectors over a time period.

    Args:
        period: "1d", "5d", "1mo", "3mo", "6mo", or "1y" (default: "1mo")

    Returns:
        JSON string with sectors sorted by return %, each with sector, etf, return_pct.
    """
    from src.tools.market_tools import get_sector_performance as _get_sectors

    valid_periods = {"1d", "5d", "1mo", "3mo", "6mo", "1y"}
    if period not in valid_periods:
        period = "1mo"

    return _get_sectors.invoke({"period": period})


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8001"))

    if transport == "sse":
        # HTTP/SSE mode — used when running in Docker or any networked setup.
        # Claude Desktop connects via: { "url": "http://localhost:8001/sse" }
        print(f"[MCP] Starting SSE server on http://{host}:{port}/sse", flush=True)
        mcp.run(transport="sse", host=host, port=port)
    else:
        # stdio mode — used for local process-based Claude Desktop config.
        mcp.run(transport="stdio")
