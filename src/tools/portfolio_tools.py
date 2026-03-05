"""
LangChain @tool wrappers for portfolio analysis via yfinance.

No API key required.

Exported collections
--------------------
PORTFOLIO_TOOLS = [analyze_portfolio, get_portfolio_performance, get_stock_quote]
"""
from __future__ import annotations

import json
import time
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


import os
import requests
from src.utils.config import FINNHUB_BASE_URL

# Global in-memory cache for company names to prevent redundant yfinance API calls
_COMPANY_NAME_CACHE: dict[str, str] = {}

def _fetch_company_name(ticker: str, retries: int = 3, backoff: float = 2.0) -> str:
    """Fetch longName for *ticker* with exponential-backoff retry on rate-limit errors."""
    ticker_upper = ticker.upper()

    # 1. Return from cache if we already fetched it this server session
    if ticker_upper in _COMPANY_NAME_CACHE:
        return _COMPANY_NAME_CACHE[ticker_upper]

    # 1.5 Finnhub API
    api_key = os.environ.get("FINNHUB_API_KEY")
    if api_key:
        try:
            url = f"{FINNHUB_BASE_URL}/stock/profile2?symbol={ticker_upper}&token={api_key}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("name"):
                    name = data["name"]
                    _COMPANY_NAME_CACHE[ticker_upper] = name
                    return name
        except Exception:
            pass

    # 2. Otherwise fetch from yfinance
    for attempt in range(retries):
        try:
            info = yf.Ticker(ticker_upper).info
            name = info.get("longName", ticker_upper)
            _COMPANY_NAME_CACHE[ticker_upper] = name
            return name
        except Exception as exc:
            msg = str(exc).lower()
            if "too many requests" in msg or "rate limit" in msg or "429" in msg:
                if attempt < retries - 1:
                    time.sleep(backoff * (2 ** attempt))
                    continue
            return ticker_upper  # non-rate-limit error or retries exhausted
    return ticker_upper


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

        tickers = [h["ticker"].upper() for h in holdings]
        prices: dict[str, float] = {}
        api_key = os.environ.get("FINNHUB_API_KEY")

        # ── Method 1: Finnhub REST API ──────────────
        if api_key:
            for tk_sym in tickers:
                try:
                    url = f"{FINNHUB_BASE_URL}/quote?symbol={tk_sym}&token={api_key}"
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        if "c" in data and data["c"] > 0:
                            prices[tk_sym] = float(data["c"])
                except Exception:
                    pass
                time.sleep(0.05)  # Throttle Finnhub calls

        # ── Method 2: yfinance fallback for missing ──────────────
        missing_tickers = [t for t in tickers if t not in prices]
        if missing_tickers:
            try:
                raw = yf.download(
                    missing_tickers,
                    period="5d",
                    auto_adjust=True,
                    progress=False,
                    threads=True,
                )
                close = raw["Close"] if "Close" in raw.columns else raw.xs("Close", axis=1, level=0)
                last_row = close.ffill().iloc[-1]
                for tk_sym in missing_tickers:
                    val = _safe_float(last_row.get(tk_sym))
                    prices[tk_sym] = val if val else 0.0
            except Exception:
                # Fallback: individual fast_info calls (slower, but resilient)
                for tk_sym in missing_tickers:
                    try:
                        prices[tk_sym] = _safe_float(yf.Ticker(tk_sym).fast_info.last_price) or 0.0
                    except Exception:
                        prices[tk_sym] = 0.0
                    time.sleep(0.3)  # throttle individual calls

        # ── Per-holding metadata (company names) ─────────────────────────────
        # Spread requests with a small delay to avoid rate-limiting.
        rows = []
        total_cost = 0.0
        total_value = 0.0

        for h in holdings:
            ticker    = h["ticker"].upper()
            shares    = float(h["shares"])
            avg_cost  = float(h.get("avg_cost", 0))
            price     = prices.get(ticker, 0.0)

            # Only hit tk.info (expensive) when we have a valid price
            if price:
                is_cached = ticker.upper() in _COMPANY_NAME_CACHE
                company = _fetch_company_name(ticker)
                
                # Only throttle if we actually made a network request
                if not is_cached:
                    time.sleep(0.25)
            else:
                company = ticker

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
