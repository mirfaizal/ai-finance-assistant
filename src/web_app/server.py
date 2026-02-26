"""FastAPI server for the AI Finance Assistant."""

# Load .env FIRST — must happen before any other imports so that env vars
# (especially LANGCHAIN_TRACING_V2 / LANGCHAIN_API_KEY) are available when
# @traceable decorators are evaluated at module-import time.
from dotenv import load_dotenv
load_dotenv()

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.workflow.orchestrator import process_query
from src.memory.conversation_store import ConversationStore
from src.memory.portfolio_store import PortfolioStore
from src.utils.logging import get_logger
from src.utils.logging import get_logger
from src.rag.retriever import get_rag_context
from src.memory.quiz_store import QuizStore
from uuid import uuid4
import json
import os

# Quiz store (SQLite-backed)
_quiz_store = QuizStore()
logger = get_logger(__name__)

# Protect quiz and seed endpoints with optional API keys when set in env
QUIZ_API_KEY = os.getenv("QUIZ_API_KEY")  # required header X-QUIZ-API-KEY for quiz endpoints when set
RAG_ADMIN_KEY = os.getenv("RAG_ADMIN_KEY")  # required header X-RAG-ADMIN-KEY for /rag/seed when set

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
_portfolio_store = PortfolioStore()


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


# ── Paper-trading portfolio endpoints (SQLite-backed) ──────────────────────────

class HoldingRow(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    updated_at: str


class TradeRow(BaseModel):
    id: int
    ticker: str
    action: str
    shares: float
    price: float
    total_value: float
    timestamp: str


class BuyRequest(BaseModel):
    ticker: str
    shares: float

    model_config = {
        "json_schema_extra": {
            "example": {"ticker": "AAPL", "shares": 10}
        }
    }


class SellRequest(BaseModel):
    ticker: str
    shares: float

    model_config = {
        "json_schema_extra": {
            "example": {"ticker": "AAPL", "shares": 5}
        }
    }


@app.get(
    "/portfolio/holdings/{session_id}",
    summary="Get paper-portfolio holdings for a session",
)
def get_holdings(session_id: str) -> dict:
    """
    Return all current paper-trading holdings for *session_id* as stored
    in SQLite.  Includes ticker, shares, average cost, and last-updated time.
    """
    holdings = _portfolio_store.get_holdings(session_id)
    return {"session_id": session_id, "holdings": holdings, "count": len(holdings)}


@app.get(
    "/portfolio/trades/{session_id}",
    summary="Get paper-trade history for a session",
)
def get_trades(session_id: str, last_n: int = 50) -> dict:
    """
    Return the most recent *last_n* paper trades for *session_id* (default 50).
    Each row: id, ticker, action, shares, price, total_value, timestamp.
    """
    trades = _portfolio_store.get_trades(session_id, last_n=last_n)
    return {"session_id": session_id, "trades": trades, "count": len(trades)}


@app.post(
    "/portfolio/buy/{session_id}",
    summary="Paper-buy shares at live market price",
)
def paper_buy(session_id: str, request: BuyRequest) -> dict:
    """
    Paper-buy *shares* of *ticker* at the current live yfinance price.
    Updates the session's holdings in SQLite (weighted avg cost).

    This endpoint is a REST shortcut; the Trading Agent also executes buys
    automatically when the user types "buy 10 AAPL" in the chat.
    """
    import yfinance as yf
    try:
        tk = yf.Ticker(request.ticker.upper())
        price = float(tk.fast_info.last_price or 0)
        if price <= 0:
            raise HTTPException(status_code=422, detail=f"Could not fetch price for {request.ticker}")
        result = _portfolio_store.buy(session_id, request.ticker, request.shares, price)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("paper_buy error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/portfolio/sell/{session_id}",
    summary="Paper-sell shares at live market price",
)
def paper_sell(session_id: str, request: SellRequest) -> dict:
    """
    Paper-sell *shares* of *ticker* at the current live yfinance price.
    Reduces the session's holdings in SQLite.  Returns 422 if insufficient shares.
    """
    import yfinance as yf
    try:
        tk = yf.Ticker(request.ticker.upper())
        price = float(tk.fast_info.last_price or 0)
        if price <= 0:
            raise HTTPException(status_code=422, detail=f"Could not fetch price for {request.ticker}")
        result = _portfolio_store.sell(session_id, request.ticker, request.shares, price)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("paper_sell error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/portfolio/summary/{session_id}",
    summary="Live portfolio summary from SQLite WAL holdings",
)
def portfolio_summary(session_id: str) -> dict:
    """
    Load holdings from the SQLite WAL paper-trading store, fetch live prices
    via yfinance, and return total value, P&L, and per-ticker allocation.

    Returns an empty summary when the session has no holdings yet.
    """
    import json
    from src.tools.portfolio_tools import analyze_portfolio  # type: ignore[attr-defined]

    holdings = _portfolio_store.get_holdings(session_id)
    if not holdings:
        return {
            "session_id": session_id,
            "holdings": [],
            "summary": {
                "total_value": 0.0,
                "total_cost": 0.0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "num_positions": 0,
                "largest_position_pct": 0.0,
                "concentration_risk": "none",
            },
        }

    clean = [
        {"ticker": h["ticker"], "shares": h["shares"], "avg_cost": h["avg_cost"]}
        for h in holdings
    ]
    try:
        raw = analyze_portfolio.invoke({"holdings_json": json.dumps(clean)})
        result = json.loads(raw)
        result["session_id"] = session_id
        return result
    except Exception as exc:
        logger.error("portfolio_summary error: %s", exc)
        return {
            "session_id": session_id,
            "holdings": [],
            "summary": {"total_value": 0.0, "total_pnl": 0.0, "total_pnl_pct": 0.0,
                        "concentration_risk": "none"},
            "error": str(exc),
        }


@app.get("/market/news", summary="Latest financial news headlines via yfinance")
def market_news(tickers: str = "SPY,AAPL,MSFT,NVDA,TSLA", limit: int = 15) -> dict:
    """
    Fetch deduplicated financial news for the given comma-separated tickers.
    Supports both the legacy flat yfinance news format and the newer nested
    ``content`` format.  Results are sorted newest-first.
    """
    import yfinance as yf
    import time as _time

    seen: set = set()
    articles = []

    for sym in tickers.split(","):
        sym = sym.strip().upper()
        if not sym:
            continue
        try:
            tk = yf.Ticker(sym)
            for item in (tk.news or []):
                # New yfinance format wraps everything under "content"
                content = item.get("content") or {}
                title = content.get("title") or item.get("title", "")
                if not title or title in seen:
                    continue
                seen.add(title)

                provider = (
                    (content.get("provider") or {}).get("displayName")
                    or item.get("publisher", "—")
                )
                pub = content.get("pubDate", "") or ""
                if not pub:
                    ts = item.get("providerPublishTime", 0)
                    pub = (_time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime(ts))
                           if ts else "")

                link = (
                    (content.get("canonicalUrl") or {}).get("url", "")
                    or item.get("link", "")
                )
                articles.append({
                    "title":        title,
                    "publisher":    provider,
                    "link":         link,
                    "published_at": pub,
                    "ticker":       sym,
                })
        except Exception:
            continue

    articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)
    deduped = articles[:limit]
    return {"articles": deduped, "count": len(deduped)}


# ── RAG / Quiz endpoints (dev demo helpers) ─────────────────────────────────


@app.get("/rag/context", summary="Return RAG context for a query")
def rag_context(q: str, top_k: int = 3):
    """Return formatted RAG context for debugging or generation."""
    ctx = get_rag_context(q, top_k=top_k, agent_filter="finance_qa")
    return {"query": q, "context": ctx}


# ── Financial Academy course content (RAG-backed) ──────────────────────────────

# Map URL slug → human title and representative search query
_COURSE_META: dict[str, dict] = {
    "investing-101":     {"title": "Investing 101",     "query": "investing basics stocks bonds ETF asset allocation"},
    "tax-strategies":    {"title": "Tax Strategies",    "query": "tax strategies tax-loss harvesting Roth IRA 401k capital gains"},
    "market-mechanics":  {"title": "Market Mechanics",  "query": "stock exchange market mechanics bid ask limit order IPO"},
    "crypto-basics":     {"title": "Crypto Basics",     "query": "blockchain cryptocurrency Bitcoin smart contracts DeFi"},
}


@app.get("/academy/courses", summary="List all Financial Academy courses with metadata")
def list_academy_courses() -> dict:
    """Return the list of available courses with their slugs and titles."""
    courses = [
        {"id": str(i + 1), "slug": slug, "title": meta["title"]}
        for i, (slug, meta) in enumerate(_COURSE_META.items())
    ]
    return {"courses": courses}


@app.get("/academy/course/{slug}", summary="Get RAG-retrieved content for a Financial Academy course")
def get_academy_course(slug: str, top_k: int = 5) -> dict:
    """
    Query Pinecone for content relevant to the named course and return it as
    a list of content blocks for display in the Financial Academy UI.

    Slug must be one of: investing-101 | tax-strategies | market-mechanics | crypto-basics
    """
    meta = _COURSE_META.get(slug)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown course slug '{slug}'. Valid values: {list(_COURSE_META.keys())}",
        )

    from src.rag.pinecone_store import query_similar

    # First try: filter by doc slug (exact match for seeded content)
    matches = query_similar(
        query_text=meta["query"],
        top_k=top_k,
        filter_metadata={"doc": slug},
    )

    # Fallback: semantic search without metadata filter
    if not matches:
        matches = query_similar(query_text=meta["query"], top_k=top_k)

    blocks = []
    seen_texts: set[str] = set()
    for m in matches:
        text = (m.get("text") or "").strip()
        if not text or text in seen_texts:
            continue
        seen_texts.add(text)
        blocks.append({
            "text":  text,
            "score": round(m.get("score", 0.0), 3),
            "doc":   m.get("metadata", {}).get("doc", slug),
        })

    return {
        "slug":    slug,
        "title":   meta["title"],
        "blocks":  blocks,
        "from_rag": len(blocks) > 0,
    }


@app.post("/rag/seed", summary="Seed Pinecone from data/academy (dev only)")
def rag_seed(request: Request) -> dict:
    """Seed the Pinecone index from bundled data/academy markdown files.

    Note: this endpoint is meant for dev convenience and requires that
    PINECONE_API_KEY and OPENAI_API_KEY are configured in the environment.
    """
    from src.rag.seed_pinecone import seed_from_directory
    # Require admin key if configured
    if RAG_ADMIN_KEY:
        provided = request.headers.get("x-rag-admin-key") or request.headers.get("X-RAG-ADMIN-KEY")
        if not provided or provided != RAG_ADMIN_KEY:
            raise HTTPException(status_code=401, detail="Missing or invalid admin key")
    try:
        n = seed_from_directory("data/academy")
        return {"seeded": n}
    except Exception as exc:
        logger.error("RAG seed failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/quiz/seed-pool", summary="Seed pre-written quiz bank into Pinecone quiz-pool namespace")
def quiz_seed_pool(request: Request) -> dict:
    """Upsert all questions from the quiz bank into the Pinecone quiz-pool namespace.

    Requires PINECONE_API_KEY and OPENAI_API_KEY.  Protected by RAG_ADMIN_KEY if set.
    """
    if RAG_ADMIN_KEY:
        provided = request.headers.get("x-rag-admin-key") or request.headers.get("X-RAG-ADMIN-KEY")
        if not provided or provided != RAG_ADMIN_KEY:
            raise HTTPException(status_code=401, detail="Missing or invalid admin key")
    try:
        from src.rag.seed_pinecone import seed_quiz_pool
        n = seed_quiz_pool()
        return {"seeded": n, "namespace": "quiz-pool"}
    except Exception as exc:
        logger.error("Quiz pool seed failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/quiz/pool/random", summary="Fetch a random unseen quiz question from the Pinecone quiz pool")
def quiz_pool_random(
    request: Request,
    topic: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict:
    """
    Return a random unasked multiple-choice question from the pre-seeded quiz pool.

    The question is retrieved from Pinecone's quiz-pool namespace.  If session_id
    is provided, questions already answered in that session are excluded so the
    user is always served fresh content.

    topic (optional): filter by topic slug, e.g. 'crypto-basics', 'tax-strategies'.
    """
    import random
    from src.rag.pinecone_store import query_similar

    # Build a varied query so we get a broad set of candidates
    topics_rotation = [
        "compound interest investing basics",
        "tax strategies retirement IRA",
        "stock market trading mechanics",
        "cryptocurrency blockchain DeFi",
        "risk management portfolio diversification",
    ]
    search_query = topic if topic else random.choice(topics_rotation)

    filter_meta: dict = {"type": "quiz"}
    if topic:
        filter_meta["topic"] = topic

    try:
        matches = query_similar(
            query_text=search_query,
            top_k=20,              # fetch many so we can pick a fresh one
            namespace="quiz-pool",
            filter_metadata=filter_meta,
        )
    except Exception as exc:
        logger.error("quiz_pool_random: Pinecone query failed: %s", exc)
        matches = []

    if not matches:
        # Fallback: use the LLM-generated quiz if Pinecone quiz pool is empty
        fallback_topic = topic or "compound interest"
        ctx = get_rag_context(fallback_topic, top_k=3, agent_filter="finance_qa")
        prompt = (
            "You are a finance teacher. Using the context below (or your own knowledge if "
            "context is empty), generate ONE multiple-choice question (4 options) with a single "
            "correct answer. Output JSON only: {\"question\": \"...\", \"choices\": [...], "
            "\"answer_index\": 0-3}.\n\nContext:\n" + ctx
        )
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7,
            )
            text = resp.choices[0].message.content
            import re
            m = re.search(r"\{.*\}", text, re.S)
            payload = json.loads(m.group(0) if m else text)
            qid = str(uuid4())
            _quiz_store.store_question(qid, int(payload["answer_index"]), session_id)
            return {"question_id": qid, "question": payload["question"],
                    "choices": payload["choices"], "source": "llm"}
        except Exception as llm_exc:
            logger.error("Fallback LLM quiz generation failed: %s", llm_exc)
            raise HTTPException(status_code=503, detail="Quiz pool empty and LLM fallback failed") from llm_exc

    # Exclude already-answered question IDs for this session
    answered_ids: set[str] = set()
    if session_id:
        answered_ids = set(_quiz_store.get_answered_pool_ids(session_id))

    fresh = [m for m in matches if m["id"] not in answered_ids]
    if not fresh:
        # All seen — reset and serve any question (cyclic)
        fresh = matches

    chosen = random.choice(fresh)
    meta = chosen.get("metadata", {})

    try:
        choices = json.loads(meta.get("choices_json", "[]"))
    except Exception:
        choices = []

    answer_index = int(meta.get("answer_index", 0))
    qid = chosen["id"]

    # Store so /quiz/answer can look up the correct index
    _quiz_store.store_question(qid, answer_index, session_id)

    return {
        "question_id": qid,
        "question":    meta.get("question", chosen.get("text", "")),
        "choices":     choices,
        "topic":       meta.get("topic", ""),
        "source":      "pinecone",
    }


@app.post("/quiz/generate", summary="Generate a multiple-choice quiz question from RAG context")
def quiz_generate(request: Request, topic: str, session_id: Optional[str] = None):
    """Generate a multiple-choice question for a given topic using RAG context

    Uses OpenAI to convert retrieved context into a single-question JSON payload:
    { question_id, question, choices: [...], answer_index }
    """
    if not topic or not topic.strip():
        raise HTTPException(status_code=422, detail="topic required")
    # Get RAG context
    ctx = get_rag_context(topic, top_k=3, agent_filter="finance_qa")
    prompt = (
        "You are a finance teacher. Using the context below, generate ONE multiple-choice question (4 options) "
        "with a single correct answer. Output JSON only with keys: question, choices (array), answer_index (0-3).\n\n"
        "Context:\n" + ctx
    )
    # If QUIZ_API_KEY is set, require it in header X-QUIZ-API-KEY
    if QUIZ_API_KEY:
        provided = request.headers.get("x-quiz-api-key") or request.headers.get("X-QUIZ-API-KEY")
        if not provided or provided != QUIZ_API_KEY:
            raise HTTPException(status_code=401, detail="Missing or invalid quiz API key")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.2,
        )
        text = resp.choices[0].message.content
        try:
            payload = json.loads(text)
        except Exception:
            # Try to extract the first JSON object from the model output
            import re
            logger.warning("Quiz generation: model output not pure JSON, attempting extraction. output=%%s", text[:500])
            m = re.search(r"\{.*\}", text, re.S)
            if not m:
                raise
            payload = json.loads(m.group(0))
        qid = str(uuid4())
        # persist the question answer index and optional session association
        _quiz_store.store_question(qid, int(payload["answer_index"]), session_id)
        return {"question_id": qid, **payload}
    except Exception as exc:
        logger.error("Quiz generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/quiz/answer", summary="Submit quiz answer and award coins")
def quiz_answer(request: Request, question_id: str, selected_index: int, session_id: Optional[str] = None) -> dict:
    """Accept an answer, compare to stored correct index, and award coins.

    Rewards: +10 coins for correct, 0 for incorrect. Returns current coin balance.
    """
    # If QUIZ_API_KEY is set, require it in header
    if QUIZ_API_KEY:
        provided = request.headers.get("x-quiz-api-key") or request.headers.get("X-QUIZ-API-KEY")
        if not provided or provided != QUIZ_API_KEY:
            raise HTTPException(status_code=401, detail="Missing or invalid quiz API key")

    correct = _quiz_store.get_answer_index(question_id)
    if correct is None:
        raise HTTPException(status_code=404, detail="question not found")
    awarded = 10 if int(selected_index) == int(correct) else 0
    sid = session_id or "anonymous"
    new_balance = _quiz_store.award_coins(sid, awarded) if awarded else _quiz_store.get_coins(sid)
    # persist answer history for auditing
    try:
        _quiz_store.store_answer(question_id, sid, selected_index, selected_index == correct, awarded)
    except Exception:
        logger.exception("Failed to store quiz answer history")
    return {"correct": selected_index == correct, "awarded": awarded, "coins": new_balance}


@app.get("/quiz/coins/{session_id}", summary="Get coin balance for a session")
def quiz_coins(request: Request, session_id: str) -> dict:
    """Return the current coin balance for a given session_id."""
    if QUIZ_API_KEY:
        provided = request.headers.get("x-quiz-api-key") or request.headers.get("X-QUIZ-API-KEY")
        if not provided or provided != QUIZ_API_KEY:
            raise HTTPException(status_code=401, detail="Missing or invalid quiz API key")
    coins = _quiz_store.get_coins(session_id or "anonymous")
    return {"session_id": session_id, "coins": coins}


@app.get("/quiz/history", summary="Get quiz answer history (dev)")
def quiz_history(request: Request, session_id: Optional[str] = None, last_n: int = 50) -> dict:
    if QUIZ_API_KEY:
        provided = request.headers.get("x-quiz-api-key") or request.headers.get("X-QUIZ-API-KEY")
        if not provided or provided != QUIZ_API_KEY:
            raise HTTPException(status_code=401, detail="Missing or invalid quiz API key")
    history = _quiz_store.get_history(session_id=session_id, last_n=last_n)
    return {"session_id": session_id, "history": history}



@app.delete(
    "/portfolio/holdings/{session_id}",
    summary="Clear all paper-portfolio holdings for a session",
)
def clear_holdings(session_id: str) -> dict:
    """
    Delete all holdings for *session_id*.  Trade history is preserved.
    Useful for resetting a paper portfolio without losing the audit trail.
    """
    removed = _portfolio_store.clear_holdings(session_id)
    return {"session_id": session_id, "removed": removed, "status": "cleared"}


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
