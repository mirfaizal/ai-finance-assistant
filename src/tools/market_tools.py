"""
LangChain @tool wrappers for market overview and sector data via yfinance.

No API key required.

Exported collections
--------------------
MARKET_TOOLS = [get_market_overview, get_sector_performance, get_stock_history]
"""
from __future__ import annotations

import json
from typing import Optional

import yfinance as yf
from langchain_core.tools import tool

from src.tools.stock_tools import get_stock_history


def _safe_float(val) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@tool
def get_market_overview() -> str:
    """
    Get a current snapshot of major US market indices and asset classes.

    Returns live data for SPY (S&P 500), QQQ (Nasdaq 100), DIA (Dow Jones),
    IWM (Russell 2000), VIX (fear index), 10-year Treasury yield, Gold (GLD),
    and Oil (USO) — each with price and daily % change.
    """
    tickers = {
        "SPY":  "S&P 500 ETF",
        "QQQ":  "Nasdaq 100 ETF",
        "DIA":  "Dow Jones ETF",
        "IWM":  "Russell 2000 ETF",
        "^VIX": "VIX Fear Index",
        "^TNX": "10-Year Treasury Yield",
        "GLD":  "Gold ETF",
        "USO":  "Oil ETF",
    }
    result: dict = {}
    for sym, name in tickers.items():
        try:
            tk = yf.Ticker(sym)
            fast   = tk.fast_info
            price  = _safe_float(fast.last_price)
            prev   = _safe_float(fast.previous_close)
            chg    = ((price - prev) / prev * 100) if (price and prev) else None
            result[sym] = {
                "name":       name,
                "price":      price,
                "change_pct": round(chg, 2) if chg is not None else None,
            }
        except Exception:
            result[sym] = {"name": name, "price": None, "change_pct": None}

    return json.dumps(result)


@tool
def get_sector_performance(period: str = "1mo") -> str:
    """
    Get performance of all 11 S&P 500 sectors using SPDR sector ETFs.

    period options: 1d, 5d, 1mo, 3mo, 6mo, 1y
    Returns each sector's total return % for the period, sorted best to worst.
    """
    sector_etfs = {
        "XLK":  "Technology",
        "XLV":  "Healthcare",
        "XLF":  "Financials",
        "XLY":  "Consumer Discretionary",
        "XLP":  "Consumer Staples",
        "XLE":  "Energy",
        "XLI":  "Industrials",
        "XLB":  "Materials",
        "XLRE": "Real Estate",
        "XLU":  "Utilities",
        "XLC":  "Communication Services",
    }
    try:
        data = yf.download(
            list(sector_etfs.keys()), period=period, auto_adjust=True, progress=False
        )["Close"]
        results: dict = {}
        for sym, sector in sector_etfs.items():
            if sym in data.columns:
                col = data[sym].dropna()
                if len(col) >= 2:
                    ret = (float(col.iloc[-1]) - float(col.iloc[0])) / float(col.iloc[0]) * 100
                    results[sector] = round(ret, 2)

        sorted_results = dict(sorted(results.items(), key=lambda x: x[1], reverse=True))
        return json.dumps({"period": period, "sector_returns_pct": sorted_results})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── exported collection ───────────────────────────────────────────────────────

MARKET_TOOLS = [get_market_overview, get_sector_performance, get_stock_history]
