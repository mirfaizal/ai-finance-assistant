"""FastAPI server for the AI Finance Assistant."""

from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.workflow.orchestrator import process_query
from src.memory.conversation_store import ConversationStore
from src.utils.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="AI Finance Assistant",
    description=(
        "A modular AI-powered finance education assistant. "
        "Provides general financial education only — not personalised advice."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared conversation store (singleton per server process)
_store = ConversationStore()


# ── Request / Response models ──────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None  # omit to start a new session

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "What is compound interest?",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    }


class AskResponse(BaseModel):
    question: str
    answer: str
    agent: str
    session_id: str   # always returned so the client can continue the session


class HistoryMessage(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[HistoryMessage]


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health", summary="Health check")
def health_check() -> dict:
    """Returns 200 OK when the service is running."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse, summary="Ask a finance question")
def ask(request: AskRequest) -> AskResponse:
    """
    Route a finance question through the orchestrator and return the answer.

    Pass an optional ``session_id`` to continue a prior conversation —
    the assistant will use previous turns as context.  If omitted, a new
    session UUID is generated and returned so you can track future turns.

    Routing is LLM-based (gpt-4.1-mini) with keyword fallback.
    7 specialist agents are available:
      stock_agent | finance_qa_agent | portfolio_analysis_agent |
      market_analysis_agent | goal_planning_agent |
      news_synthesizer_agent | tax_education_agent
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question must not be empty.")

    logger.info("POST /ask  question=%s  session=%s", question[:80], request.session_id)
    try:
        result = process_query(question, session_id=request.session_id)
        return AskResponse(
            question=question,
            answer=result["answer"],
            agent=result["agent"],
            session_id=result["session_id"],
        )
    except Exception as exc:
        logger.error("Error processing question: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/history/{session_id}",
    response_model=HistoryResponse,
    summary="Retrieve conversation history for a session",
)
def get_history(session_id: str, last_n: int = 20) -> HistoryResponse:
    """
    Return up to *last_n* prior messages for the given *session_id*.

    Useful for the frontend to restore the chat UI after a page reload.
    """
    messages = _store.get_history(session_id, last_n=last_n)
    return HistoryResponse(
        session_id=session_id,
        messages=[HistoryMessage(**m) for m in messages],
    )


@app.get("/sessions", summary="List all session IDs")
def list_sessions() -> dict:
    """Return all known session IDs ordered by creation time (most recent first)."""
    return {"sessions": _store.list_sessions()}


# ── Market data endpoints (live via yfinance, no API key required) ─────────────

@app.get("/market/overview", summary="Live market snapshot")
def market_overview() -> dict:
    """
    Return current price and daily % change for major indices and assets:
    SPY, QQQ, DIA, IWM, VIX, 10-year yield, GLD, USO.
    Powers the dashboard insights cards and the ticker strip.
    """
    import json
    from src.tools.market_tools import get_market_overview  # type: ignore[attr-defined]
    try:
        raw = get_market_overview.invoke({})  # @tool returns a JSON string
        return json.loads(raw)
    except Exception as exc:
        logger.error("market_overview error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/market/chart", summary="12-month monthly closing prices for SPY/QQQ/DIA")
def market_chart() -> list:
    """
    Return the last 12 months of monthly closing prices for SPY, QQQ, and DIA
    in [{date, sp500, nasdaq, dow}] format — drops directly into MarketChart.tsx.
    """
    import yfinance as yf
    import pandas as pd

    try:
        data = yf.download(
            ["SPY", "QQQ", "DIA"],
            period="1y",
            interval="1mo",
            auto_adjust=True,
            progress=False,
        )["Close"]

        # Normalise column access (single vs multi-ticker)
        if hasattr(data, "columns"):
            spy = data["SPY"] if "SPY" in data.columns else pd.Series(dtype=float)
            qqq = data["QQQ"] if "QQQ" in data.columns else pd.Series(dtype=float)
            dia = data["DIA"] if "DIA" in data.columns else pd.Series(dtype=float)
        else:
            spy = qqq = dia = pd.Series(dtype=float)

        rows = []
        for ts in spy.index:
            label = ts.strftime("%b %Y") if hasattr(ts, "strftime") else str(ts)[:7]
            rows.append({
                "date":   label,
                "sp500":  round(float(spy.get(ts, 0)), 2),
                "nasdaq": round(float(qqq.get(ts, 0)), 2),
                "dow":    round(float(dia.get(ts, 0)), 2),
            })
        return rows
    except Exception as exc:
        logger.error("market_chart error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/market/quotes", summary="Live quotes for a comma-separated list of tickers")
def market_quotes(symbols: str = "SPY,AAPL,TSLA,NVDA,BTC-USD") -> dict:
    """
    Return price and day-change for each requested ticker symbol.
    symbols: comma-separated, e.g. ?symbols=AAPL,NVDA,TSLA
    """
    import yfinance as yf

    result = {}
    for sym in symbols.split(","):
        sym = sym.strip().upper()
        if not sym:
            continue
        try:
            tk = yf.Ticker(sym)
            fast = tk.fast_info
            price = float(fast.last_price or 0)
            prev  = float(fast.previous_close or 0)
            chg_pct = round((price - prev) / prev * 100, 2) if prev else 0.0
            result[sym] = {
                "price":      round(price, 2),
                "change_pct": chg_pct,
                "up":         chg_pct >= 0,
            }
        except Exception:
            result[sym] = {"price": None, "change_pct": None, "up": None}
    return result


# ── Portfolio endpoints ────────────────────────────────────────────────────────

class HoldingItem(BaseModel):
    ticker: str
    shares: float
    avg_cost: float


class PortfolioRequest(BaseModel):
    holdings: List[HoldingItem]

    model_config = {
        "json_schema_extra": {
            "example": {
                "holdings": [
                    {"ticker": "AAPL", "shares": 10, "avg_cost": 150.0},
                    {"ticker": "NVDA", "shares": 5,  "avg_cost": 500.0},
                ]
            }
        }
    }


@app.post("/portfolio/analyze", summary="Analyze a portfolio with live prices")
def portfolio_analyze(request: PortfolioRequest) -> dict:
    """
    Fetch live prices via yfinance and return P&L, allocation %, and a summary
    for each holding.  Holdings are supplied by the caller (stored in the
    browser's localStorage — no server-side persistence needed).
    """
    import json
    from src.tools.portfolio_tools import analyze_portfolio  # type: ignore[attr-defined]

    holdings_list = [h.model_dump() for h in request.holdings]
    try:
        raw = analyze_portfolio.invoke({"holdings_json": json.dumps(holdings_list)})
        return json.loads(raw)
    except Exception as exc:
        logger.error("portfolio_analyze error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Entry point (local dev) ────────────────────────────────────────────────────

if __name__ == "__main__":
    import yaml
    from pathlib import Path
    import uvicorn

    _cfg_path = Path(__file__).resolve().parents[2] / "config.yaml"
    _server_cfg: dict = {}
    if _cfg_path.exists():
        with open(_cfg_path) as f:
            _server_cfg = yaml.safe_load(f).get("server", {})

    uvicorn.run(
        "src.web_app.server:app",
        host=_server_cfg.get("host", "0.0.0.0"),
        port=int(_server_cfg.get("port", 8000)),
        reload=True,
    )
