# AI Finance Assistant — API Documentation

> **Base URL (local):** `http://localhost:8000`  
> **Base URL (Docker):** `http://localhost:8000`  
> **OpenAPI Docs (interactive):** `http://localhost:8000/docs`  
> **ReDoc:** `http://localhost:8000/redoc`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Common Conventions](#common-conventions)
4. [Endpoints](#endpoints)
   - [Core](#1-core)
   - [Conversation History](#2-conversation-history)
   - [Market Data](#3-market-data)
   - [Portfolio Analysis](#4-portfolio-analysis)
   - [Paper Trading](#5-paper-trading)
   - [RAG / Knowledge Base](#6-rag--knowledge-base)
   - [Financial Academy](#7-financial-academy)
   - [Quiz System](#8-quiz-system)
5. [Error Responses](#error-responses)
6. [User Guide](#user-guide)

---

## Overview

The AI Finance Assistant backend is a **FastAPI** application exposing 25 REST endpoints across eight functional groups.  It combines:

| Layer | Technology |
|---|---|
| LLM routing & agents | OpenAI GPT-4.1 via LangGraph StateGraph |
| Live market data | yfinance |
| Vector search / RAG | Pinecone (`finance-docs` + `quiz-pool` namespaces) |
| Conversation memory | SQLite WAL (`data/conversations.db`) |
| Paper-trading ledger | SQLite WAL (`data/portfolio.db`) |

> **Disclaimer:** All responses are for **general financial education only**.  This service never provides personalised investment, tax, or legal advice.

---

## Authentication

| Context | Header | Description |
|---|---|---|
| Quiz endpoints | `X-QUIZ-API-KEY` | Required only when `QUIZ_API_KEY` env var is set |
| Admin / seeding | `X-RAG-ADMIN-KEY` | Required only when `RAG_ADMIN_KEY` env var is set |

All other endpoints are **unauthenticated** by default.

---

## Common Conventions

- All request and response bodies are **JSON** (`Content-Type: application/json`).
- **Session IDs** are arbitrary strings.  A UUID is recommended (e.g. `550e8400-e29b-41d4-a716-446655440000`).  If a session does not exist it is created automatically.
- Monetary values are in **USD** unless stated otherwise.
- Timestamps follow **ISO 8601** (`YYYY-MM-DDTHH:MM:SSZ`).

---

## Endpoints

---

### 1. Core

#### `GET /health`

Liveness probe.  Returns `200 OK` when the service is running.

**Response**
```json
{ "status": "ok" }
```

---

#### `POST /ask`

Main conversational endpoint.  Routes the question to a specialist agent and returns a structured answer.

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | string | ✅ | User's question |
| `session_id` | string | ❌ | Existing session ID; omit to start a new session |

```json
{
  "question": "What is dollar-cost averaging?",
  "session_id": "my-session-123"
}
```

**Response**

| Field | Type | Description |
|---|---|---|
| `question` | string | The original question |
| `answer` | string | Agent's response |
| `agent` | string | Name of the agent that handled the request |
| `session_id` | string | Session ID (new or echoed) |

```json
{
  "question": "What is dollar-cost averaging?",
  "answer": "Dollar-cost averaging (DCA) is an investment strategy...",
  "agent": "finance_qa",
  "session_id": "my-session-123"
}
```

**Routing table** — the router selects from these agents:

| Agent name | Handles |
|---|---|
| `finance_qa` | General finance questions |
| `stock_agent` | Stock quotes, earnings, financials |
| `market_analysis` | Market trends, sectors, indices |
| `portfolio_analysis` | Portfolio P&L and allocation analysis |
| `goal_planning` | Savings goals and retirement planning |
| `news_synthesizer` | Financial news summarisation |
| `tax_education` | Tax education (capital gains, harvesting, IRA/401k) |
| `trading_agent` | Paper buy/sell commands (e.g. "buy 10 AAPL") |

---

### 2. Conversation History

#### `GET /history/{session_id}`

Return the most recent N messages for a session.

**Path Parameters**

| Name | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier |

**Query Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `last_n` | integer | 20 | Maximum number of messages to return |

**Response**

```json
{
  "session_id": "my-session-123",
  "messages": [
    { "role": "user", "content": "What is dollar-cost averaging?" },
    { "role": "assistant", "content": "Dollar-cost averaging is..." }
  ]
}
```

---

#### `GET /sessions`

List all session IDs ordered by creation time (most recent first).

**Response**

```json
{ "sessions": ["session-abc", "session-xyz"] }
```

---

### 3. Market Data

All market data endpoints use **yfinance** and require no API key.

---

#### `GET /market/overview`

Live snapshot of major indices and assets.

**Response** — object keyed by ticker symbol:

```json
{
  "SPY":  { "name": "S&P 500 ETF",       "price": 542.10, "change_pct": 0.43 },
  "QQQ":  { "name": "NASDAQ 100 ETF",    "price": 468.22, "change_pct": 0.71 },
  "DIA":  { "name": "Dow Jones ETF",     "price": 389.55, "change_pct": 0.15 },
  "IWM":  { "name": "Russell 2000 ETF",  "price": 210.80, "change_pct": -0.22 },
  "VIX":  { "name": "Volatility Index",  "price": 14.35,  "change_pct": -3.11 },
  "GLD":  { "name": "Gold ETF",          "price": 225.40, "change_pct": 0.08 },
  "USO":  { "name": "Oil ETF",           "price": 73.90,  "change_pct": 1.24 }
}
```

---

#### `GET /market/chart`

12-month monthly closing prices for SPY, QQQ, and DIA.  Designed for the dashboard chart component.

**Response** — array of monthly data points:

```json
[
  { "date": "Jul 2024", "sp500": 519.34, "nasdaq": 448.60, "dow": 379.12 },
  { "date": "Aug 2024", "sp500": 522.87, "nasdaq": 451.20, "dow": 381.45 }
]
```

---

#### `GET /market/quotes`

Live price and day-change for arbitrary tickers.

**Query Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `symbols` | string | `SPY,AAPL,TSLA,NVDA,BTC-USD` | Comma-separated ticker symbols |

**Example**
```
GET /market/quotes?symbols=AAPL,NVDA,MSFT
```

**Response**

```json
{
  "AAPL": { "price": 212.34, "change_pct": 1.12, "up": true  },
  "NVDA": { "price": 134.56, "change_pct": -0.45, "up": false },
  "MSFT": { "price": 435.78, "change_pct": 0.67, "up": true  }
}
```

Values may be `null` if the ticker is invalid or data is unavailable.

---

#### `GET /market/news`

Latest deduplicated financial news headlines fetched via yfinance.  Results are sorted newest-first.

**Query Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tickers` | string | `SPY,AAPL,MSFT,NVDA,TSLA` | Comma-separated ticker symbols |
| `limit` | integer | 15 | Maximum number of articles to return |

**Example**
```
GET /market/news?tickers=AAPL,TSLA&limit=5
```

**Response**

```json
{
  "articles": [
    {
      "title":        "Apple Beats Q3 Earnings Expectations",
      "publisher":    "Reuters",
      "link":         "https://...",
      "published_at": "2025-07-24T14:30:00Z",
      "ticker":       "AAPL"
    }
  ],
  "count": 1
}
```

---

### 4. Portfolio Analysis

#### `POST /portfolio/analyze`

Analyze a manually-supplied list of holdings using live prices.  No server-side state; holdings are supplied in the request body.

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `holdings` | array | ✅ | List of `{ticker, shares, avg_cost}` objects |

```json
{
  "holdings": [
    { "ticker": "AAPL", "shares": 10, "avg_cost": 150.00 },
    { "ticker": "NVDA", "shares": 5,  "avg_cost": 500.00 }
  ]
}
```

**Response** — includes per-position detail and portfolio-level summary:

```json
{
  "holdings": [
    {
      "ticker":        "AAPL",
      "shares":        10,
      "avg_cost":      150.00,
      "current_price": 212.34,
      "current_value": 2123.40,
      "cost_basis":   1500.00,
      "pnl":           623.40,
      "pnl_pct":         41.56,
      "allocation_pct":  57.80
    }
  ],
  "summary": {
    "total_value":          3672.10,
    "total_cost":           3250.00,
    "total_pnl":             422.10,
    "total_pnl_pct":          12.99,
    "num_positions":              2,
    "largest_position_pct":   57.80,
    "concentration_risk":    "medium"
  }
}
```

---

### 5. Paper Trading

All paper-trading routes persist to **SQLite**.  Holdings survive restarts; trade history is an append-only ledger.

---

#### `GET /portfolio/holdings/{session_id}`

Return all current holdings for a session.

**Path Parameters**

| Name | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier |

**Response**

```json
{
  "session_id": "my-session-123",
  "holdings": [
    {
      "ticker":     "AAPL",
      "shares":     10.0,
      "avg_cost":   212.34,
      "updated_at": "2025-07-24T14:00:00Z"
    }
  ],
  "count": 1
}
```

---

#### `GET /portfolio/trades/{session_id}`

Return the trade history for a session.

**Path Parameters**

| Name | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier |

**Query Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `last_n` | integer | 50 | Maximum number of trades to return |

**Response**

```json
{
  "session_id": "my-session-123",
  "trades": [
    {
      "id":          1,
      "ticker":      "AAPL",
      "action":      "buy",
      "shares":      10.0,
      "price":       212.34,
      "total_value": 2123.40,
      "timestamp":   "2025-07-24T14:00:00Z"
    }
  ],
  "count": 1
}
```

---

#### `POST /portfolio/buy/{session_id}`

Paper-buy shares at the current live market price.  Updates the weighted-average cost in SQLite.

**Path Parameters**

| Name | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier |

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `ticker` | string | ✅ | Ticker symbol (case-insensitive) |
| `shares` | number | ✅ | Number of shares to buy |

```json
{ "ticker": "AAPL", "shares": 10 }
```

**Response**

```json
{
  "status":    "bought",
  "ticker":    "AAPL",
  "shares":    10.0,
  "price":     212.34,
  "total":     2123.40
}
```

**Errors**

| Code | Reason |
|---|---|
| 422 | Could not fetch live price for the ticker |
| 500 | Internal error |

---

#### `POST /portfolio/sell/{session_id}`

Paper-sell shares at the current live market price.  Returns 422 if the session holds fewer shares than requested.

**Path Parameters**

| Name | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier |

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `ticker` | string | ✅ | Ticker symbol |
| `shares` | number | ✅ | Number of shares to sell |

```json
{ "ticker": "AAPL", "shares": 5 }
```

**Response**

```json
{
  "status": "sold",
  "ticker": "AAPL",
  "shares": 5.0,
  "price":  212.34,
  "total":  1061.70
}
```

**Errors**

| Code | Reason |
|---|---|
| 422 | Insufficient shares or price fetch failure |

---

#### `GET /portfolio/summary/{session_id}`

Load holdings from SQLite, fetch live prices, and return full P&L analysis.

**Path Parameters**

| Name | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier |

**Response**  — same structure as `POST /portfolio/analyze` plus `session_id`, or an empty summary when no holdings exist:

```json
{
  "session_id": "my-session-123",
  "holdings": [...],
  "summary": {
    "total_value":          3672.10,
    "total_cost":           3250.00,
    "total_pnl":             422.10,
    "total_pnl_pct":          12.99,
    "concentration_risk":    "medium"
  }
}
```

---

#### `DELETE /portfolio/holdings/{session_id}`

Clear all holdings for a session.  Trade history (audit trail) is preserved.

**Path Parameters**

| Name | Type | Description |
|---|---|---|
| `session_id` | string | Session identifier |

**Response**

```json
{
  "session_id": "my-session-123",
  "removed":    2,
  "status":     "cleared"
}
```

---

### 6. RAG / Knowledge Base

#### `GET /rag/context`

Debug helper: return the raw Pinecone RAG context for a query.

**Query Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `q` | string | — | Query string |
| `top_k` | integer | 3 | Number of chunks to retrieve |

**Example**
```
GET /rag/context?q=what+is+compound+interest&top_k=3
```

**Response**

```json
{
  "query":   "what is compound interest",
  "context": "Compound interest is the addition of interest to the principal..."
}
```

---

#### `POST /rag/seed`

Seed the Pinecone `finance-docs` namespace from the `data/academy/` markdown files.

> **Requires** `PINECONE_API_KEY`, `OPENAI_API_KEY`.  
> **Protected** by `X-RAG-ADMIN-KEY` header when `RAG_ADMIN_KEY` env var is set.

**Response**

```json
{ "seeded": 16 }
```

| Code | Reason |
|---|---|
| 401 | Missing or invalid admin key |
| 500 | Seeding failed |

---

### 7. Financial Academy

#### `GET /academy/courses`

List all available Financial Academy courses.

**Response**

```json
{
  "courses": [
    { "id": "1", "slug": "investing-101",    "title": "Investing 101"    },
    { "id": "2", "slug": "tax-strategies",   "title": "Tax Strategies"   },
    { "id": "3", "slug": "market-mechanics", "title": "Market Mechanics" },
    { "id": "4", "slug": "crypto-basics",    "title": "Crypto Basics"    }
  ]
}
```

---

#### `GET /academy/course/{slug}`

Retrieve Pinecone-backed content blocks for a course.

**Path Parameters**

| Name | Type | Description |
|---|---|---|
| `slug` | string | One of: `investing-101`, `tax-strategies`, `market-mechanics`, `crypto-basics` |

**Query Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `top_k` | integer | 5 | Number of content chunks to retrieve |

**Response**

```json
{
  "slug":     "investing-101",
  "title":    "Investing 101",
  "from_rag": true,
  "blocks": [
    {
      "text":  "An exchange-traded fund (ETF) is a collection of securities...",
      "score": 0.921,
      "doc":   "investing-101"
    }
  ]
}
```

`from_rag` is `false` when Pinecone returned no results.

| Code | Reason |
|---|---|
| 404 | Unknown course slug |

---

### 8. Quiz System

#### `GET /quiz/pool/random`

Fetch a random, unseen multiple-choice question from the pre-seeded Pinecone quiz pool.

If all questions for a session have been seen, the pool resets cyclically.  If the Pinecone pool is empty an LLM-generated fallback question is returned.

**Query Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `topic` | string | random | Filter by topic slug (see table below) |
| `session_id` | string | — | Used to exclude already-answered questions |

**Available topic slugs**

| Slug | Description |
|---|---|
| `compound-interest` | Compound interest calculations |
| `investing-basics`  | Stocks, bonds, ETFs, asset allocation |
| `tax-strategies`    | Tax-loss harvesting, IRA, 401k |
| `market-mechanics`  | Exchanges, order types, IPOs |
| `crypto-basics`     | Blockchain, Bitcoin, DeFi |
| `retirement`        | Retirement planning |
| `risk-management`   | Diversification and risk |

**Response**

```json
{
  "question_id": "abc123",
  "question":    "What is the Rule of 72?",
  "choices":     [
    "A formula to calculate dividends",
    "A shortcut to estimate how long it takes to double money",
    "The maximum tax rate on capital gains",
    "The number of stocks in the Dow Jones"
  ],
  "topic":  "compound-interest",
  "source": "pinecone"
}
```

`source` is either `"pinecone"` or `"llm"` (fallback).

| Code | Reason |
|---|---|
| 503 | Pool empty and LLM fallback also failed |

---

#### `POST /quiz/generate`

Generate a single multiple-choice question **on demand** using RAG context + OpenAI.

**Query Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `topic` | string | ✅ | Free-text topic (e.g. `"compound interest"`) |
| `session_id` | string | ❌ | Associate the question with a session |

**Headers** (when `QUIZ_API_KEY` is set)

| Header | Description |
|---|---|
| `X-QUIZ-API-KEY` | Quiz API key |

**Response**

```json
{
  "question_id":  "uuid-here",
  "question":     "What does compound interest mean?",
  "choices":      ["Interest on interest only", "Interest on principal only", "Interest on both principal and accumulated interest", "Fixed interest rate"],
  "answer_index": 2
}
```

| Code | Reason |
|---|---|
| 401 | Missing or invalid quiz API key |
| 422 | Empty topic |
| 500 | Generation failed |

---

#### `POST /quiz/answer`

Submit an answer, check correctness, and update the coin balance.

**Query Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `question_id` | string | ✅ | ID returned by `/quiz/pool/random` or `/quiz/generate` |
| `selected_index` | integer | ✅ | 0-based index of the chosen answer |
| `session_id` | string | ❌ | Used for coin tracking |

**Headers** (when `QUIZ_API_KEY` is set): `X-QUIZ-API-KEY`

**Response**

```json
{
  "correct": true,
  "awarded": 10,
  "coins":   30
}
```

`awarded` is `10` for a correct answer, `0` for incorrect.

| Code | Reason |
|---|---|
| 401 | Invalid API key |
| 404 | Question ID not found |

---

#### `GET /quiz/coins/{session_id}`

Return the current coin balance for a session.

**Headers** (when `QUIZ_API_KEY` is set): `X-QUIZ-API-KEY`

**Response**

```json
{ "session_id": "my-session-123", "coins": 30 }
```

---

#### `GET /quiz/history`

Return the quiz answer history (for dev/debugging).

**Query Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `session_id` | string | — | Filter by session; omit for all sessions |
| `last_n` | integer | 50 | Maximum rows to return |

**Headers** (when `QUIZ_API_KEY` is set): `X-QUIZ-API-KEY`

**Response**

```json
{
  "session_id": "my-session-123",
  "history": [
    {
      "question_id":  "abc123",
      "session_id":   "my-session-123",
      "selected":     2,
      "correct":      true,
      "awarded":      10,
      "timestamp":    "2025-07-24T14:00:00Z"
    }
  ]
}
```

---

#### `POST /quiz/seed-pool`

Upsert all 34 questions from the built-in quiz bank into the Pinecone `quiz-pool` namespace.

> **Requires** `PINECONE_API_KEY`, `OPENAI_API_KEY`.  
> **Protected** by `X-RAG-ADMIN-KEY` header when `RAG_ADMIN_KEY` env var is set.

**Response**

```json
{ "seeded": 34, "namespace": "quiz-pool" }
```

| Code | Reason |
|---|---|
| 401 | Missing or invalid admin key |
| 500 | Seeding failed |

---

## Error Responses

All errors follow the standard FastAPI shape:

```json
{ "detail": "Human-readable error message" }
```

| HTTP Code | Meaning |
|---|---|
| 400 | Bad request (malformed input) |
| 401 | Authentication failed (quiz or admin key) |
| 404 | Resource not found |
| 422 | Validation error (e.g. insufficient shares, empty topic) |
| 500 | Internal server error |
| 503 | External dependency unavailable (Pinecone, yfinance, OpenAI) |

---

## User Guide

### Getting Started

1. **Start the server**

   ```bash
   # Local Python
   uvicorn src.web_app.server:app --host 0.0.0.0 --port 8000 --reload

   # Docker Compose (recommended)
   docker compose up --build -d
   ```

2. **Confirm it is running**

   ```bash
   curl http://localhost:8000/health
   # → {"status":"ok"}
   ```

3. **Browse the interactive docs**  
   Open `http://localhost:8000/docs` in your browser.

---

### Session Management

All user data (conversation history, paper-trading holdings, quiz coins) is keyed by a **session ID** you choose.

- Use a **UUID** to avoid collisions: `python -c "import uuid; print(uuid.uuid4())"`
- Pass the same `session_id` across calls to accumulate history and holdings.
- To start fresh, generate a new UUID — no deletion needed.

---

### Workflow: Chat with the AI

```bash
# Start a conversation
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain index funds", "session_id": "demo-001"}'

# Ask a follow-up (context is remembered)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I buy one?", "session_id": "demo-001"}'

# Retrieve the full conversation
curl http://localhost:8000/history/demo-001
```

---

### Workflow: Market Dashboard

```bash
# Get live index prices
curl http://localhost:8000/market/overview

# Get 12-month chart data (SPY/QQQ/DIA monthly closes)
curl http://localhost:8000/market/chart

# Get live prices for specific tickers
curl "http://localhost:8000/market/quotes?symbols=AAPL,TSLA,BTC-USD"

# Get latest news
curl "http://localhost:8000/market/news?tickers=AAPL,NVDA&limit=10"
```

---

### Workflow: Portfolio Tracking

```bash
# One-off portfolio analysis (no persistence needed)
curl -X POST http://localhost:8000/portfolio/analyze \
  -H "Content-Type: application/json" \
  -d '{"holdings": [{"ticker":"AAPL","shares":10,"avg_cost":150}]}'

# Paper-buy via REST
curl -X POST http://localhost:8000/portfolio/buy/demo-001 \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","shares":10}'

# Check current holdings
curl http://localhost:8000/portfolio/holdings/demo-001

# Get live P&L
curl http://localhost:8000/portfolio/summary/demo-001

# Paper-sell
curl -X POST http://localhost:8000/portfolio/sell/demo-001 \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","shares":5}'

# View trade history
curl http://localhost:8000/portfolio/trades/demo-001

# Reset (clear holdings, keep trade log)
curl -X DELETE http://localhost:8000/portfolio/holdings/demo-001
```

Alternatively, type natural-language commands in the chat (via `POST /ask`) and the **Trading Agent** handles them automatically:

```
"buy 10 shares of AAPL"
"sell 5 NVDA"
"what is my portfolio worth?"
```

---

### Workflow: Financial Academy

```bash
# List all courses
curl http://localhost:8000/academy/courses

# Fetch course content (RAG-backed from Pinecone)
curl http://localhost:8000/academy/course/investing-101
curl http://localhost:8000/academy/course/tax-strategies
curl http://localhost:8000/academy/course/market-mechanics
curl http://localhost:8000/academy/course/crypto-basics
```

---

### Workflow: Quiz System

```bash
# Get a random quiz question (fresh for this session)
curl "http://localhost:8000/quiz/pool/random?session_id=demo-001"

# Get a question on a specific topic
curl "http://localhost:8000/quiz/pool/random?topic=crypto-basics&session_id=demo-001"

# Submit an answer (question_id from the previous response)
curl -X POST "http://localhost:8000/quiz/answer?question_id=abc123&selected_index=2&session_id=demo-001"

# Check coin balance
curl http://localhost:8000/quiz/coins/demo-001
```

---

### Workflow: Seeding Pinecone (Admin)

Only needed once, or after content changes.

```bash
# Seed course content (data/academy/*.md → finance-docs namespace)
curl -X POST http://localhost:8000/rag/seed \
  -H "X-RAG-ADMIN-KEY: your-admin-key"

# Seed quiz bank (34 questions → quiz-pool namespace)
curl -X POST http://localhost:8000/quiz/seed-pool \
  -H "X-RAG-ADMIN-KEY: your-admin-key"
```

---

### Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key (all LLM + embeddings calls) |
| `OPENAI_MODEL` | ❌ | `gpt-4o-mini` | Overrides the LLM model used |
| `PINECONE_API_KEY` | ❌ | — | Required for RAG and quiz pool |
| `PINECONE_INDEX` | ❌ | `ai-finance-rag` | Pinecone index name |
| `TAVILY_API_KEY` | ❌ | — | Enables real-time web search in agents |
| `QUIZ_API_KEY` | ❌ | — | When set, all `/quiz/*` endpoints require `X-QUIZ-API-KEY` header |
| `RAG_ADMIN_KEY` | ❌ | — | When set, `/rag/seed` and `/quiz/seed-pool` require `X-RAG-ADMIN-KEY` header |
| `LANGCHAIN_API_KEY` | ❌ | — | LangSmith observability |
| `LANGCHAIN_TRACING_V2` | ❌ | — | Set `true` to enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | ❌ | — | LangSmith project name |
