"""
LangChain @tool wrappers for individual stock data via yfinance.

No API key required — uses Yahoo Finance directly.

Exported collections
--------------------
STOCK_TOOLS = [get_stock_quote, get_stock_history, get_stock_financials]
"""
from __future__ import annotations

import json
from typing import Optional

import yfinance as yf
from langchain_core.tools import tool


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe_float(val) -> Optional[float]:
    """Coerce *val* to float, returning ``None`` for any non-numeric input."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ── tools ─────────────────────────────────────────────────────────────────────

@tool
def get_stock_quote(ticker: str) -> str:
    """
    Get the current price and key stats for a stock ticker.

    Provide the ticker symbol (e.g. 'AAPL', 'TSLA', 'NVDA').
    Returns price, change %, market cap, P/E ratio, 52-week range, sector, and volume.
    """
    try:
        tk = yf.Ticker(ticker.upper().strip())
        info = tk.info
        if not info or "regularMarketPrice" not in info:
            fast = tk.fast_info
            price = _safe_float(fast.last_price)
            return json.dumps({"ticker": ticker.upper(), "price": price, "note": "Limited data available"})

        price     = info.get("regularMarketPrice") or info.get("currentPrice")
        prev      = info.get("regularMarketPreviousClose") or info.get("previousClose")
        change    = (price - prev) if (price and prev) else None
        change_pct = (change / prev * 100) if (change is not None and prev) else None

        return json.dumps({
            "ticker":         ticker.upper(),
            "company":        info.get("longName", ticker.upper()),
            "price":          price,
            "change":         round(change, 4) if change is not None else None,
            "change_pct":     round(change_pct, 2) if change_pct is not None else None,
            "market_cap":     info.get("marketCap"),
            "pe_ratio":       info.get("trailingPE"),
            "forward_pe":     info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "52wk_high":      info.get("fiftyTwoWeekHigh"),
            "52wk_low":       info.get("fiftyTwoWeekLow"),
            "volume":         info.get("regularMarketVolume"),
            "avg_volume":     info.get("averageVolume"),
            "sector":         info.get("sector"),
            "industry":       info.get("industry"),
        })
    except Exception as e:
        return json.dumps({"error": str(e), "ticker": ticker})


@tool
def get_stock_history(ticker: str, period: str = "1y") -> str:
    """
    Get historical OHLCV data for a ticker.

    period options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    Returns start/end price, total return %, annualised volatility, and trading day count.
    """
    try:
        tk = yf.Ticker(ticker.upper().strip())
        hist = tk.history(period=period)
        if hist.empty:
            return json.dumps({"error": "No historical data found", "ticker": ticker})

        start_price = float(hist["Close"].iloc[0])
        end_price   = float(hist["Close"].iloc[-1])
        total_return = (end_price - start_price) / start_price * 100
        daily_returns = hist["Close"].pct_change().dropna()
        volatility = float(daily_returns.std() * (252 ** 0.5) * 100)

        return json.dumps({
            "ticker":                    ticker.upper(),
            "period":                    period,
            "start_date":               str(hist.index[0].date()),
            "end_date":                 str(hist.index[-1].date()),
            "start_price":              round(start_price, 4),
            "end_price":                round(end_price, 4),
            "total_return_pct":         round(total_return, 2),
            "high":                     round(float(hist["High"].max()), 4),
            "low":                      round(float(hist["Low"].min()), 4),
            "avg_volume":               round(float(hist["Volume"].mean())),
            "annualized_volatility_pct": round(volatility, 2),
            "trading_days":             len(hist),
        })
    except Exception as e:
        return json.dumps({"error": str(e), "ticker": ticker})


@tool
def get_stock_financials(ticker: str) -> str:
    """
    Get key fundamental metrics for a stock: revenue, margins, earnings,
    debt ratios, return on equity, beta, and analyst recommendations.
    """
    try:
        tk = yf.Ticker(ticker.upper().strip())
        info = tk.info

        # Analyst recommendations summary
        analyst_summary: str | list = "N/A"
        try:
            recs = tk.recommendations
            if recs is not None and not recs.empty:
                if "period" in recs.columns:
                    latest = recs[recs["period"] == "0m"]
                else:
                    latest = recs.tail(5)
                if not latest.empty:
                    analyst_summary = latest.to_dict(orient="records")
        except Exception:
            pass

        return json.dumps({
            "ticker":                   ticker.upper(),
            "company":                  info.get("longName"),
            "revenue":                  info.get("totalRevenue"),
            "gross_margin":             info.get("grossMargins"),
            "operating_margin":         info.get("operatingMargins"),
            "profit_margin":            info.get("profitMargins"),
            "eps":                      info.get("trailingEps"),
            "forward_eps":              info.get("forwardEps"),
            "debt_to_equity":           info.get("debtToEquity"),
            "current_ratio":            info.get("currentRatio"),
            "return_on_equity":         info.get("returnOnEquity"),
            "return_on_assets":         info.get("returnOnAssets"),
            "free_cash_flow":           info.get("freeCashflow"),
            "beta":                     info.get("beta"),
            "analyst_target_price":     info.get("targetMeanPrice"),
            "analyst_recommendation":   info.get("recommendationMean"),
            "analyst_summary":          analyst_summary,
        })
    except Exception as e:
        return json.dumps({"error": str(e), "ticker": ticker})


# ── exported collection ───────────────────────────────────────────────────────

STOCK_TOOLS = [get_stock_quote, get_stock_history, get_stock_financials]
