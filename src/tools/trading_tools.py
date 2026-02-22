"""
Session-bound trading tools for the Trading Agent.

Tools are created as closures that capture ``session_id`` so the
ReAct LLM never needs to ask for or pass a session identifier — it
just calls ``buy_stock("AAPL", 10)`` and the right portfolio row is updated.

Usage
-----
    from src.tools.trading_tools import make_trading_tools

    # Build tools scoped to a session
    tools = make_trading_tools(session_id)

    # Combine with stock-quote tool for pre-trade price check
    from src.tools.stock_tools import get_stock_quote
    all_tools = tools + [get_stock_quote]

    agent = create_react_agent(llm, tools=all_tools, ...)
"""
from __future__ import annotations

import json
from typing import Optional

import yfinance as yf
from langchain_core.tools import tool

from src.memory.portfolio_store import PortfolioStore


# ── Low-level yfinance price fetch ────────────────────────────────────────────

def _live_price(ticker: str) -> float:
    """Fetch the latest market price for *ticker* via yfinance.  No API key required."""
    tk = yf.Ticker(ticker.upper())
    price = tk.fast_info.last_price
    if not price:
        raise ValueError(f"Could not fetch live price for '{ticker}'. Verify the ticker symbol.")
    return float(price)


# ── Session-bound tool factory ────────────────────────────────────────────────

def make_trading_tools(session_id: str) -> list:
    """
    Build and return a list of four LangChain ``@tool`` functions, all
    scoped to *session_id* via closure.

    Tools returned
    --------------
    buy_stock        — purchase shares at live market price
    sell_stock       — sell shares at live market price
    view_holdings    — list current portfolio positions
    view_trade_history — show recent trade log
    """
    store = PortfolioStore()

    # ── buy ───────────────────────────────────────────────────────────────────

    @tool
    def buy_stock(ticker: str, shares: float) -> str:
        """
        Buy shares of a stock at the current live market price (paper trading only).

        Fetches the real-time price via yfinance, records the purchase in the
        portfolio database, and updates the weighted-average cost basis.

        Args:
            ticker: Stock ticker symbol, e.g. 'AAPL', 'TSLA', 'NVDA'.
            shares: Number of shares to buy.  May be fractional (e.g. 0.5).

        Returns:
            JSON string confirming the trade: ticker, shares_bought, price,
            total_cost, and new_position (shares + avg_cost).
        """
        try:
            ticker = ticker.upper().strip()
            shares = float(shares)
            if shares <= 0:
                return json.dumps({"error": "shares must be a positive number."})

            price = _live_price(ticker)
            result = store.buy(session_id, ticker, shares, price)
            result["status"] = "confirmed"
            result["note"] = "This is a paper trade. No real money was used."
            return json.dumps(result, indent=2)

        except Exception as exc:
            return json.dumps({"error": str(exc)})

    # ── sell ──────────────────────────────────────────────────────────────────

    @tool
    def sell_stock(ticker: str, shares: float) -> str:
        """
        Sell shares of a stock at the current live market price (paper trading only).

        Fetches the real-time price via yfinance and reduces the holdings.
        Returns an error if you do not hold enough shares.

        Args:
            ticker: Stock ticker symbol, e.g. 'AAPL', 'TSLA', 'NVDA'.
            shares: Number of shares to sell.  Use the keyword 'all' by converting
                    to 0 to trigger view_holdings first, then pass the exact count.

        Returns:
            JSON string confirming the trade: ticker, shares_sold, price,
            proceeds, realized_pnl, and remaining_shares.
        """
        try:
            ticker = ticker.upper().strip()
            shares = float(shares)
            if shares <= 0:
                return json.dumps({"error": "shares must be a positive number."})

            price = _live_price(ticker)
            result = store.sell(session_id, ticker, shares, price)
            result["status"] = "confirmed"
            result["note"] = "This is a paper trade. No real money was used."
            return json.dumps(result, indent=2)

        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    # ── view holdings ─────────────────────────────────────────────────────────

    @tool
    def view_holdings() -> str:
        """
        View all current paper-portfolio holdings for this session.

        Each holding includes: ticker, shares owned, average cost basis,
        and the date/time it was last updated.

        Returns:
            JSON string with a 'holdings' list and total count.
            Returns a helpful message if the portfolio is empty.
        """
        try:
            holdings = store.get_holdings(session_id)
            if not holdings:
                return json.dumps({
                    "holdings": [],
                    "count": 0,
                    "message": (
                        "Your paper portfolio is empty. "
                        "Use buy_stock to add your first position."
                    ),
                })
            return json.dumps({"holdings": holdings, "count": len(holdings)}, indent=2)

        except Exception as exc:
            return json.dumps({"error": str(exc)})

    # ── view trade history ────────────────────────────────────────────────────

    @tool
    def view_trade_history() -> str:
        """
        View recent paper-trade history (last 20 trades) for this session.

        Each record shows: id, ticker, action (buy/sell), shares, execution
        price, total_value, and timestamp (UTC).

        Returns:
            JSON string with a 'trades' list and total count.
        """
        try:
            trades = store.get_trades(session_id, last_n=20)
            return json.dumps({"trades": trades, "count": len(trades)}, indent=2)
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    return [buy_stock, sell_stock, view_holdings, view_trade_history]
