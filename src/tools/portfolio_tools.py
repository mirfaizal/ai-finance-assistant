"""
LangChain @tool wrappers for portfolio analysis via yfinance.

No API key required.

Exported collections
--------------------
PORTFOLIO_TOOLS = [analyze_portfolio, get_portfolio_performance, get_stock_quote]
"""
from __future__ import annotations

import json
from typing import Optional

import yfinance as yf
from langchain_core.tools import tool

from src.tools.stock_tools import get_stock_quote


def _safe_float(val) -> Optional[float]:
    """Coerce *val* to float, returning ``None`` for any non-numeric input."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@tool
def analyze_portfolio(holdings_json: str) -> str:
    """
    Analyze a portfolio of stock holdings.

    Input: JSON string of a list with objects containing 'ticker', 'shares', and 'avg_cost'.
    Example: '[{"ticker": "AAPL", "shares": 10, "avg_cost": 150.0}]'

    Returns current values, allocation %, cost basis, P&L per position, and a portfolio summary.
    """
    try:
        holdings = json.loads(holdings_json)
        if not holdings:
            return json.dumps({"error": "Empty portfolio"})

        rows = []
        total_cost = 0.0
        total_value = 0.0

        for h in holdings:
            ticker    = h["ticker"].upper()
            shares    = float(h["shares"])
            avg_cost  = float(h.get("avg_cost", 0))

            tk = yf.Ticker(ticker)
            price   = _safe_float(tk.fast_info.last_price) or 0.0
            company = tk.info.get("longName", ticker) if price else ticker

            current_value = price * shares
            cost_basis    = avg_cost * shares
            pnl           = current_value - cost_basis
            pnl_pct       = (pnl / cost_basis * 100) if cost_basis else 0

            total_cost  += cost_basis
            total_value += current_value

            rows.append({
                "ticker":        ticker,
                "company":       company,
                "shares":        shares,
                "current_price": price,
                "avg_cost":      avg_cost,
                "current_value": round(current_value, 2),
                "cost_basis":    round(cost_basis, 2),
                "pnl":           round(pnl, 2),
                "pnl_pct":       round(pnl_pct, 2),
            })

        for r in rows:
            r["allocation_pct"] = round(r["current_value"] / total_value * 100, 2) if total_value else 0

        total_pnl     = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

        # Concentration score: highest single allocation %
        max_alloc = max((r["allocation_pct"] for r in rows), default=0)
        concentration_risk = "high" if max_alloc > 40 else "medium" if max_alloc > 25 else "low"

        return json.dumps({
            "holdings": rows,
            "summary": {
                "total_cost":              round(total_cost, 2),
                "total_value":             round(total_value, 2),
                "total_pnl":               round(total_pnl, 2),
                "total_pnl_pct":           round(total_pnl_pct, 2),
                "num_positions":           len(rows),
                "largest_position_pct":    round(max_alloc, 2),
                "concentration_risk":      concentration_risk,
            },
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_portfolio_performance(holdings_json: str, period: str = "1y") -> str:
    """
    Compare portfolio performance against the S&P 500 benchmark (SPY).

    Input: JSON string of a list with objects containing 'ticker', 'shares', and 'avg_cost'.
    period options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y

    Returns portfolio return %, SPY benchmark return %, and alpha.
    """
    try:
        holdings = json.loads(holdings_json)
        tickers   = [h["ticker"].upper() for h in holdings]
        shares_map = {h["ticker"].upper(): float(h["shares"]) for h in holdings}

        all_tickers = tickers + ["SPY"]
        data = yf.download(all_tickers, period=period, auto_adjust=True, progress=False)["Close"]
        if data.empty:
            return json.dumps({"error": "Could not fetch price history"})

        data = data.dropna(how="all")
        individual_returns: dict = {}
        portfolio_start = portfolio_end = 0.0

        for ticker in tickers:
            if ticker in data.columns:
                col = data[ticker].dropna()
                if len(col) >= 2:
                    r = (float(col.iloc[-1]) - float(col.iloc[0])) / float(col.iloc[0]) * 100
                    individual_returns[ticker] = round(r, 2)
                    s = shares_map.get(ticker, 0)
                    portfolio_start += float(col.iloc[0]) * s
                    portfolio_end   += float(col.iloc[-1]) * s

        portfolio_return = (
            (portfolio_end - portfolio_start) / portfolio_start * 100 if portfolio_start else 0
        )

        spy_return = None
        if "SPY" in data.columns:
            spy = data["SPY"].dropna()
            if len(spy) >= 2:
                spy_return = round(
                    (float(spy.iloc[-1]) - float(spy.iloc[0])) / float(spy.iloc[0]) * 100, 2
                )

        return json.dumps({
            "period":                   period,
            "portfolio_return_pct":     round(portfolio_return, 2),
            "benchmark_spy_return_pct": spy_return,
            "alpha_pct":                round(portfolio_return - (spy_return or 0), 2),
            "individual_returns":       individual_returns,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── exported collection ───────────────────────────────────────────────────────

PORTFOLIO_TOOLS = [analyze_portfolio, get_portfolio_performance, get_stock_quote]
