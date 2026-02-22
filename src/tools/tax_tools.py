"""
LangChain @tool wrappers for tax calculations via yfinance (live prices).

No API key required.

Exported collections
--------------------
TAX_TOOLS = [calculate_capital_gains, find_tax_loss_opportunities]
"""
from __future__ import annotations

import json
from typing import Optional

import yfinance as yf
from langchain_core.tools import tool


def _safe_float(val) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@tool
def calculate_capital_gains(
    ticker: str,
    shares: float,
    avg_cost_per_share: float,
    holding_period_days: int,
) -> str:
    """
    Calculate estimated capital gains tax for selling a stock position.

    Fetches the current live market price via yfinance, then computes:
    - Cost basis, current value, and gain/loss
    - Whether the holding is short-term (<365 days) or long-term (>=365 days)
    - Estimated US federal tax at simplified rates (37% ST, 15% LT typical)
    - After-tax proceeds

    Parameters: ticker (e.g. 'AAPL'), shares, avg_cost_per_share, holding_period_days.
    Note: this is a simplified estimate — consult a tax professional for accuracy.
    """
    try:
        tk = yf.Ticker(ticker.upper().strip())
        price = _safe_float(tk.fast_info.last_price)
        if price is None:
            return json.dumps({"error": f"Could not get live price for {ticker}"})

        cost_basis    = shares * avg_cost_per_share
        current_value = shares * price
        gain          = current_value - cost_basis
        is_long_term  = holding_period_days >= 365

        # Simplified US federal rates
        st_rate = 0.37   # top short-term (ordinary income) rate
        lt_rate = 0.15   # most common long-term rate

        applied_rate = lt_rate if is_long_term else st_rate
        tax_estimate = gain * applied_rate if gain > 0 else 0.0

        return json.dumps({
            "ticker":             ticker.upper(),
            "shares":             shares,
            "avg_cost":           avg_cost_per_share,
            "current_price":      price,
            "cost_basis":         round(cost_basis, 2),
            "current_value":      round(current_value, 2),
            "gain_loss":          round(gain, 2),
            "is_long_term":       is_long_term,
            "holding_period_days": holding_period_days,
            "applicable_rate":    applied_rate,
            "estimated_tax":      round(tax_estimate, 2),
            "after_tax_proceeds": round(current_value - tax_estimate, 2),
            "note": (
                "Simplified estimate using top federal rates only. "
                "State taxes, NIIT (3.8%), and deductions are excluded. "
                "Consult a qualified tax advisor."
            ),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def find_tax_loss_opportunities(holdings_json: str) -> str:
    """
    Scan a portfolio for tax-loss harvesting opportunities.

    Input: JSON string list of objects with 'ticker', 'shares', and 'avg_cost'.
    Example: '[{"ticker": "AAPL", "shares": 10, "avg_cost": 200}]'

    Returns positions with unrealised losses that could offset capital gains,
    sorted by largest loss first. Includes a reminder about the 30-day wash-sale rule.
    """
    try:
        holdings = json.loads(holdings_json)
        losers: list = []

        for h in holdings:
            ticker   = h["ticker"].upper()
            shares   = float(h["shares"])
            avg_cost = float(h.get("avg_cost", 0))

            try:
                price = _safe_float(yf.Ticker(ticker).fast_info.last_price) or 0.0
            except Exception:
                price = 0.0

            current_value = price * shares
            cost_basis    = avg_cost * shares
            pnl           = current_value - cost_basis

            if pnl < 0:
                losers.append({
                    "ticker":         ticker,
                    "shares":         shares,
                    "current_price":  price,
                    "avg_cost":       avg_cost,
                    "unrealized_loss": round(pnl, 2),
                    "loss_pct":       round(pnl / cost_basis * 100, 2) if cost_basis else 0,
                })

        losers.sort(key=lambda x: x["unrealized_loss"])
        total_harvestable = sum(p["unrealized_loss"] for p in losers)

        return json.dumps({
            "tax_loss_candidates":    losers,
            "total_harvestable_loss": round(total_harvestable, 2),
            "num_candidates":         len(losers),
            "wash_sale_warning": (
                "Selling these positions realises losses that can offset capital gains. "
                "Do NOT repurchase substantially identical securities within 30 days "
                "before or after the sale — the wash-sale rule will disallow the loss."
            ),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── exported collection ───────────────────────────────────────────────────────

TAX_TOOLS = [calculate_capital_gains, find_tax_loss_opportunities]
