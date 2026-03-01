# Product Requirements Document
## AI Finance Assistant

| Field | Value |
|---|---|
| **Document Version** | 1.0 |
| **Date** | March 1, 2026 |
| **Status** | Released (v2.0.0) |
| **Owner** | AI Finance Assistant Team |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Success Metrics](#3-goals--success-metrics)
4. [Users & Personas](#4-users--personas)
5. [Scope](#5-scope)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [System Architecture](#8-system-architecture)
9. [Agent Specifications](#9-agent-specifications)
10. [API Reference](#10-api-reference)
11. [Data & Storage](#11-data--storage)
12. [Integrations & External Dependencies](#12-integrations--external-dependencies)
13. [Frontend Requirements](#13-frontend-requirements)
14. [Security & Compliance](#14-security--compliance)
15. [Deployment & Infrastructure](#15-deployment--infrastructure)
16. [Testing Requirements](#16-testing-requirements)
17. [Known Limitations & Future Work](#17-known-limitations--future-work)

---

## 1. Executive Summary

The **AI Finance Assistant** is a production-ready, multi-agent AI system that delivers financial *education* to retail users through a conversational interface. It combines nine specialised AI agents, live market data, persistent memory, and a React dashboard into a single coherent product.

Users ask natural-language questions — "What is the wash sale rule?", "How is my portfolio allocated?", "What is NVDA trading at?" — and the system routes each query to the most appropriate specialist agent, maintains conversation context across turns, and responds with grounded, factual answers.

> **Safety boundary:** The system provides **general financial education only**. It does not provide personalised investment advice, tax guidance, legal opinions, or stock-pick recommendations. Every agent enforces this boundary via its system prompt.

---

## 2. Problem Statement

### 2.1 User Pain

Retail investors lack affordable, immediate access to financial expertise. Options today are:

- **Static content** (articles, YouTube) — no interactivity, no personalisation to portfolio context
- **Human advisors** — expensive, appointment-gated, inaccessible to small investors
- **Generic chatbots** — no real-time data, no memory across sessions, no domain specialisation

### 2.2 Product Gap

A single agentic assistant that can simultaneously:
- Answer conceptual finance questions with RAG-backed knowledge
- Analyse a live portfolio by calling real market data tools
- Track multi-turn conversations ("Does the rule apply to ETFs?" should recall prior context)
- Execute paper trades and demonstrate trade lifecycle
- Synthesise breaking news into plain-language summaries

…did not exist as an integrated, open system.

---

## 3. Goals & Success Metrics

### 3.1 Goals

| # | Goal |
|---|---|
| G1 | Deliver accurate, domain-grounded financial education via natural language |
| G2 | Route queries intelligently to the best specialist agent, not a monolith |
| G3 | Maintain multi-turn conversation context across a session |
| G4 | Provide live market data without requiring users to own API keys |
| G5 | Enable paper trading to demonstrate trade lifecycle safely |
| G6 | Ensure all responses stay within the educational-only safety boundary |

### 3.2 Success Metrics

| Metric | Target |
|---|---|
| LLM routing accuracy (GPT-4.1-mini) | ≥ 90 % correct agent selection |
| API p95 response latency ( `/ask` ) | ≤ 8 seconds |
| Memory synthesis trigger at turn > 5 | 100 % reliable |
| Test suite pass rate | 100 % (388 tests) |
| Test coverage | ≥ 80 % of source lines |
| Uptime (Docker / EC2 deployment) | ≥ 99 % |

---

## 4. Users & Personas

### 4.1 Primary Persona — Retail Investor (Self-Directed Learner)

- **Age:** 25–45
- **Technical level:** Low-to-medium (comfortable with web apps)
- **Context:** Has brokerage account, invests occasionally, wants to understand concepts before acting
- **Jobs to be done:**
  - Understand terminology (ETF, P/E ratio, capital gains tax)
  - Evaluate own portfolio performance and risk
  - Monitor market trends daily
  - Learn tax optimisation strategies without paying an advisor

### 4.2 Secondary Persona — Developer / Integration Engineer

- Wants to extend the assistant with new agents or tools
- Uses MCP server to integrate finance capabilities into Claude Desktop or other clients
- Reads API documentation to build downstream services

---

## 5. Scope

### 5.1 In Scope (v2.0.0)

- Nine AI agents with distinct domains (see §9)
- LLM-based routing with keyword fallback
- Persistent multi-turn conversation memory (SQLite WAL)
- Memory synthesis for long sessions (>5 turns)
- Live market data via yfinance (no API key required)
- Paper trading with real prices, SQLite positions store
- Tavily real-time web search (optional, graceful fallback)
- Pinecone RAG knowledge base (optional, graceful fallback)
- LangSmith observability tracing
- FastAPI REST backend (17+ endpoints)
- React + TypeScript frontend dashboard
- MCP server for Claude Desktop integration
- Docker + docker-compose one-command deployment
- AWS ECS / EC2 deployment scripts

### 5.2 Out of Scope

- Real brokerage integration or live order execution
- Personalised investment advice or recommendations
- Tax filing or tax preparation
- Legal or insurance advice
- User authentication / multi-user accounts (v1 scope)
- Mobile native application

---

## 6. Functional Requirements

### 6.1 Conversational Interface

| ID | Requirement |
|---|---|
| F-01 | The system SHALL accept a natural-language `question` and an optional `session_id` via `POST /ask` |
| F-02 | When `session_id` is omitted, the system SHALL generate a new UUID and return it in the response |
| F-03 | When `session_id` is provided, the system SHALL inject the last N turns of history into the agent prompt |
| F-04 | The response SHALL include `answer`, `agent` (which agent handled it), `session_id`, and optional `run_id` |
| F-05 | The system SHALL compress conversation history using the Memory Synthesizer when turn count exceeds 5 |

### 6.2 Routing

| ID | Requirement |
|---|---|
| F-06 | The system SHALL use GPT-4.1-mini to classify each question and select the appropriate agent |
| F-07 | The routing response SHALL include a `confidence` score |
| F-08 | If the LLM routing call fails, the system SHALL fall back to keyword-based scoring via `ROUTING_TABLE` |
| F-09 | The router SHALL consider conversation history when determining context (e.g., follow-up questions) |

### 6.3 Agents

| ID | Requirement |
|---|---|
| F-10 | Each agent SHALL enforce the educational-only disclaimer in its system prompt |
| F-11 | ReAct agents (Stock, Portfolio, Market, Tax, Trading) SHALL iterate tool calls until sufficient data is collected, up to 8 iterations |
| F-12 | All agent entry points SHALL accept `question`, `history`, and `memory_summary` |
| F-13 | All agent calls SHALL be decorated with `@traceable` for LangSmith visibility |

### 6.4 Market Data

| ID | Requirement |
|---|---|
| F-14 | The system SHALL provide live prices for major indices (SPY, QQQ, DIA, IWM, VIX) via `GET /market/overview` |
| F-15 | The system SHALL provide 12-month OHLCV data for SPY/QQQ/DIA via `GET /market/chart` |
| F-16 | The system SHALL provide live prices for arbitrary tickers via `GET /market/quotes` |
| F-17 | Market data SHALL be sourced from yfinance without requiring any user-provided API key |

### 6.5 Portfolio Analysis

| ID | Requirement |
|---|---|
| F-18 | The system SHALL accept a holdings JSON (ticker, shares, avg_cost) and return P&L, allocation %, and concentration risk |
| F-19 | The system SHALL compute portfolio return vs SPY (alpha) for a given period |
| F-20 | The system SHALL identify unrealised tax-loss harvesting opportunities and flag wash-sale risk |

### 6.6 Paper Trading

| ID | Requirement |
|---|---|
| F-21 | The Trading Agent SHALL support `buy` and `sell` actions with live prices from yfinance |
| F-22 | Positions and trade history SHALL be persisted in SQLite across restarts |
| F-23 | The system SHALL reject trades that would create invalid positions (e.g., selling more than held) |

### 6.7 History & Sessions

| ID | Requirement |
|---|---|
| F-24 | `GET /history/{session_id}` SHALL return paginated conversation history (default last 20 messages) |
| F-25 | `GET /sessions` SHALL return all known session IDs ordered by recency |

### 6.8 Feedback

| ID | Requirement |
|---|---|
| F-26 | `POST /feedback` SHALL accept `run_id` and a thumbs-up/down `score` and forward it to LangSmith |
| F-27 | If LangSmith tracing is disabled, feedback SHALL return a `skipped` status gracefully |

### 6.9 MCP Server

| ID | Requirement |
|---|---|
| F-28 | The MCP server SHALL expose 6 tools: `ask_finance_assistant`, `get_stock_quote`, `get_market_overview`, `analyze_portfolio`, `get_financial_news`, `get_sector_performance` |
| F-29 | The MCP server SHALL support both stdio (local) and SSE/HTTP (Docker) transports |

---

## 7. Non-Functional Requirements

### 7.1 Performance

| ID | Requirement |
|---|---|
| NF-01 | `POST /ask` p95 response time ≤ 8 seconds under normal load |
| NF-02 | `GET /market/overview` SHALL respond within 3 seconds |
| NF-03 | SQLite WAL mode ensures non-blocking concurrent reads |

### 7.2 Reliability

| ID | Requirement |
|---|---|
| NF-04 | All external integrations (Tavily, Pinecone, LangSmith) SHALL degrade gracefully when unavailable |
| NF-05 | LLM routing failure SHALL fall back to keyword scoring without surfacing an error to the user |
| NF-06 | The system SHALL return structured errors (HTTP 4xx/5xx) with detail messages |

### 7.3 Scalability

| ID | Requirement |
|---|---|
| NF-07 | The FastAPI server SHALL handle concurrent requests via async endpoints |
| NF-08 | SQLite WAL is sufficient for single-instance deployments; PostgreSQL migration path documented |

### 7.4 Observability

| ID | Requirement |
|---|---|
| NF-09 | Every agent invocation, tool call, and routing decision SHALL produce a LangSmith trace when `LANGCHAIN_TRACING_V2=true` |
| NF-10 | Structured JSON logs SHALL be emitted at INFO/ERROR level via `get_logger()` |
| NF-11 | `GET /health` SHALL serve as the liveness probe for container orchestration |

### 7.5 Maintainability

| ID | Requirement |
|---|---|
| NF-12 | New agents SHALL follow the standard 4-file structure (`__init__.py`, `client.py`, `prompts.py`, `<agent>.py`) |
| NF-13 | New tools SHALL be `@tool`-decorated, placed in `src/tools/`, and added to the relevant `*_TOOLS` list |
| NF-14 | Test coverage SHALL be maintained at ≥ 80 % when adding new code |

---

## 8. System Architecture

```
Client (React Dashboard / curl / Claude Desktop MCP)
        │
        ▼  HTTP
┌───────────────────────────────────┐
│         FastAPI  (server.py)      │
│  /ask  /history  /sessions        │
│  /market/*  /portfolio/analyze    │
│  /feedback  /quiz/*  /rag/*       │
└─────────────┬─────────────────────┘
              │ process_query(question, session_id)
              ▼
┌─────────────────────────────────────────────────┐
│              AgentOrchestrator                  │
│  LangGraph StateGraph + MemorySaver             │
│  (workflow/orchestrator.py)                     │
│                                                 │
│  1. ConversationStore.get_history()  ─► SQLite  │
│  2. synthesize_memory() if turns > 5            │
│  3. RouterAgent (GPT-4.1-mini + keyword)        │
│  4. StateGraph node → agent.run()               │
│  5. ConversationStore.save_turn()   ─► SQLite   │
└────────────────┬────────────────────────────────┘
                 │ dispatch to one of 9 agents
    ┌────────────┼──────────────────────────┐
    ▼            ▼                          ▼
finance_qa   stock_agent           trading_agent
portfolio    market_analysis       tax_education
goal_plan    news_synthesizer      memory_synth
    │            │
    │  ReAct loop (create_react_agent)
    │            │
    ▼            ▼
  @tool       @tool                  External
  Pinecone    yfinance ─────────────► yfinance API
  RAG         Tavily  ─────────────► Tavily API
              LangSmith ──────────► LangSmith
```

### 8.1 Key Design Decisions

| Decision | Rationale |
|---|---|
| LangGraph `StateGraph` + `MemorySaver` | Enables in-session state persistence with checkpointing per `thread_id=session_id` |
| `create_react_agent` for ReAct agents | Handles the tool-call loop, error recovery, and iteration limit automatically |
| SQLite WAL over Redis | Zero-dependency persistence; sufficient for single-instance; WAL ensures concurrent reads |
| GPT-4.1-mini for routing | Lower cost and latency than GPT-4.1 for classification-only tasks |
| Graceful optional dependencies | Tavily, Pinecone, LangSmith are all optional; system degrades gracefully without any of them |
| yfinance (no API key) | Removes a significant onboarding friction for developers running locally |

---

## 9. Agent Specifications

### 9.1 Agent Inventory

| Agent | Entry Function | Routing Keywords | Tools | ReAct |
|---|---|---|---|---|
| Finance Q&A | `ask_finance_agent` | "what is", "explain", "ETF", "Fed" | Tavily, Pinecone | — |
| Portfolio Analysis | `analyze_portfolio` | "portfolio", "allocation", "holdings" | `PORTFOLIO_TOOLS`, Pinecone | ✅ |
| Market Analysis | `analyze_market` | "market", "index", "S&P", "sector" | `MARKET_TOOLS`, Tavily | ✅ |
| Goal Planning | `plan_goals` | "goal", "retire", "save", "FIRE" | Pinecone | — |
| News Synthesizer | `synthesize_news` | "news", "headline", "earnings" | Tavily | — |
| Tax Education | `explain_tax_concepts` | "tax", "capital gains", "IRS" | `TAX_TOOLS`, Pinecone | ✅ |
| Stock Analyst | `ask_stock_agent` | "price", ticker symbols, "PE ratio" | `STOCK_TOOLS` | ✅ |
| Trading Agent | `ask_trading_agent` | "buy", "sell", "paper trading" | `TRADING_TOOLS` | ✅ |
| Memory Synthesizer | `synthesize_memory` | Internal (turn count > 5) | GPT-4.1 | — |

### 9.2 Standard Agent Contract

Every agent MUST implement:
```python
def ask_<agent>(
    question: str,
    history: list[dict[str, str]] | None = None,
    memory_summary: str | None = None,
) -> str
```
- Decorated with `@traceable(name="<agent>_run")`
- System prompt includes the educational-only disclaimer
- Error handling returns a graceful string — never raises to the orchestrator

### 9.3 ReAct Tool Lists

| Agent | Tools |
|---|---|
| Stock | `get_stock_quote`, `get_stock_history`, `get_stock_financials` |
| Portfolio | `analyze_portfolio`, `get_portfolio_performance` |
| Market | `get_market_overview`, `get_sector_performance` |
| Tax | `calculate_capital_gains`, `find_tax_loss_opportunities` |
| Trading | `buy_stock`, `sell_stock`, `get_positions`, `get_trade_history` |

---

## 10. API Reference

### Core Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | Liveness probe |
| POST | `/ask` | None | Route question through multi-agent orchestrator |
| GET | `/history/{session_id}` | None | Retrieve conversation history |
| GET | `/sessions` | None | List all session IDs |
| POST | `/feedback` | None | Submit thumbs up/down to LangSmith |

### Market Data Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/market/overview` | None | Live prices: SPY, QQQ, DIA, IWM, VIX, GLD, USO |
| GET | `/market/chart` | None | 12-month monthly OHLCV (SPY/QQQ/DIA) |
| GET | `/market/quotes` | None | Live prices for arbitrary tickers |

### Portfolio Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/portfolio/analyze` | None | P&L, allocation %, alpha vs SPY |

### Quiz & RAG Admin Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/quiz/question` | `X-QUIZ-API-KEY` (optional) | Random quiz question |
| POST | `/quiz/answer` | `X-QUIZ-API-KEY` (optional) | Submit answer |
| POST | `/rag/seed` | `X-RAG-ADMIN-KEY` (optional) | Seed Pinecone index |

### Request / Response Schemas

**`POST /ask`**
```json
// Request
{ "question": "What is compound interest?", "session_id": "uuid-optional" }

// Response
{
  "question": "What is compound interest?",
  "answer": "Compound interest is...",
  "agent": "finance_qa_agent",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_id": "langsmith-run-id-optional"
}
```

---

## 11. Data & Storage

### 11.1 SQLite WAL — Conversation Store

- **File:** `data/conversations.db`
- **Tables:** `sessions`, `messages`, `summaries`
- **Mode:** WAL (Write-Ahead Logging) — allows concurrent reads during writes
- **Access pattern:** Sequential append on every turn; paginated reads for history

### 11.2 SQLite WAL — Portfolio Store

- **File:** `data/portfolio.db`
- **Tables:** `positions`, `trades`
- **Access pattern:** CRUD per trading action

### 11.3 SQLite — Quiz Store

- **File:** `data/quiz.db`
- **Tables:** `questions`, `answers`

### 11.4 Pinecone Vector Store (Optional)

- **Dimension:** 1536 (OpenAI `text-embedding-ada-002`)
- **Metric:** Cosine similarity
- **Namespace/metadata filter:** `agent_filter` field per document
- **Seeded from:** `data/academy/` markdown files

### 11.5 Data Retention

- Conversation history: indefinite (no TTL in v2.0.0)
- Paper trading positions: indefinite
- LangSmith traces: governed by LangSmith plan limits

---

## 12. Integrations & External Dependencies

### 12.1 Required

| Service | Purpose | Env Var |
|---|---|---|
| OpenAI GPT-4.1 | Agent LLM responses | `OPENAI_API_KEY` |
| OpenAI GPT-4.1-mini | Routing, memory synthesis | `OPENAI_API_KEY` |
| yfinance | Live market data (no key needed) | — |

### 12.2 Optional (graceful fallback)

| Service | Purpose | Env Var | Fallback |
|---|---|---|---|
| Tavily | Real-time web search for news/Q&A | `TAVILY_API_KEY` | LLM training data only |
| Pinecone | RAG knowledge retrieval | `PINECONE_API_KEY`, `PINECONE_INDEX` | No RAG context injected |
| LangSmith | Observability & tracing | `LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2` | Silent no-op |

### 12.3 OpenAI Model Configuration

| Variable | Default |
|---|---|
| `OPENAI_MODEL` | `gpt-4.1` |
| Temperature | `0.3` (most agents) |

---

## 13. Frontend Requirements

### 13.1 Technology Stack

- **Framework:** React 19 + TypeScript
- **Build tool:** Vite
- **Styling:** CSS modules / Tailwind
- **Served by:** nginx (production container)

### 13.2 UI Components

| Component | Data Source | Description |
|---|---|---|
| Ticker Strip | `GET /market/quotes` | Live scrolling price ribbon |
| Market Insights Cards | `GET /market/overview` | SPY, QQQ, VIX, Gold with % change |
| Market Chart | `GET /market/chart` | 12-month line chart (recharts) |
| Portfolio Pie Chart | `POST /portfolio/analyze` | Holdings allocation visualiser |
| Agent Chat | `POST /ask` | Multi-turn conversation UI with session persistence |
| Session History | `GET /history/{session_id}` | Restore prior chat on reload |

### 13.3 Frontend Non-Functional Requirements

- Chat UI SHALL preserve `session_id` in local state for multi-turn continuity
- Thumbs up/down buttons SHALL submit feedback via `POST /feedback` with the `run_id`
- Frontend SHALL handle API errors gracefully with user-facing messages
- Build output SHALL be served as static assets by nginx on port 80

---

## 14. Security & Compliance

### 14.1 Safety Guardrails

- Every agent system prompt includes: *"You provide general financial education only. You NEVER provide personalised investment advice, stock picks, tax advice, or legal guidance."*
- `src/core/guards.py` provides content guardrail checks that can be applied before routing
- Routing to an unsupported intent returns a polite refusal, not a crash

### 14.2 API Security

- CORS is configured to `allow_origins=["*"]` in development; **MUST** be restricted to known origins in production
- Quiz and RAG admin endpoints support optional `X-QUIZ-API-KEY` / `X-RAG-ADMIN-KEY` headers when env vars are set
- OpenAI and other credentials are loaded from `.env` / environment — never hardcoded

### 14.3 Data Privacy

- Conversation history stored locally in SQLite; no user PII collected
- LangSmith traces contain question text — operators must ensure LangSmith data residency meets requirements
- No authentication layer in v2.0.0 — deployment behind a reverse proxy/VPN is recommended for production

---

## 15. Deployment & Infrastructure

### 15.1 Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set env vars
cp .env.example .env  # add OPENAI_API_KEY at minimum

# Run backend
uvicorn src.web_app.server:app --reload --port 8000

# Run frontend
cd src/web_app/frontend && npm install && npm run dev
```

### 15.2 Docker (Recommended)

```bash
docker-compose up --build -d
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# MCP SSE:  http://localhost:8001/sse
```

### 15.3 AWS Deployment

| Component | AWS Service |
|---|---|
| Backend container | ECS Fargate / EC2 |
| Frontend | S3 + CloudFront or same container |
| Load balancer | Application Load Balancer |
| Secrets | AWS Secrets Manager or `.env` on instance |

Deployment scripts in `aws/deploy.sh`; ECS task definition in `aws/task-definition.json`.

### 15.4 HuggingFace Spaces

The system is configured for HuggingFace Spaces deployment via `sdk: docker` in the README front-matter, exposing port `7860`.

### 15.5 Container Architecture

| Container | Image | Port | Purpose |
|---|---|---|---|
| `backend` | `Dockerfile.backend` | 8000 | FastAPI + all agents |
| `frontend` | `Dockerfile.frontend` | 3000 | React dashboard (nginx) |
| `mcp` | (same as backend) | 8001 | MCP SSE server |

---

## 16. Testing Requirements

### 16.1 Test Suite

| Module | Location | Coverage Area |
|---|---|---|
| Agent tests | `tests/test_*_agent.py` | All 9 agents (8 files) |
| Tool tests | `tests/test_tools_*.py` | All 6 tool modules |
| API tests | `tests/test_api.py`, `tests/test_server_extended.py` | FastAPI endpoints |
| Orchestrator | `tests/test_orchestrator.py` | LangGraph routing flow |
| Memory stores | `tests/test_memory_stores.py` | SQLite CRUD |
| Core | `tests/test_core_*.py` | Router, guards, protocol |
| MCP server | `tests/test_mcp_server.py` | MCP tool interfaces |
| Coverage boost | `tests/test_coverage_boost.py` | Edge cases |

**Total: 388 tests across 24 modules**

### 16.2 Running Tests

```bash
# Full suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing

# Single module
pytest tests/test_stock_agent.py -v
```

### 16.3 CI Requirements

- All 388 tests MUST pass before merge to main
- Coverage MUST NOT drop below 80 %
- LLM-dependent tests MUST be mocked (`unittest.mock.patch`) to avoid API cost in CI

---

## 17. Known Limitations & Future Work

### 17.1 Current Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| SQLite single-writer | Cannot horizontally scale writes | Migrate to PostgreSQL for multi-instance |
| No user authentication | All sessions are anonymous | Planned for v3.0 |
| yfinance rate limits | Occasional timeouts under high concurrency | Retry logic + caching layer |
| LLM routing misclassification | ~10 % of edge-case queries routed to wrong agent | Keyword fallback + continuous prompt tuning |
| Paper trading only | No real brokerage execution | By design — safety boundary |

### 17.2 Roadmap Candidates (v3.0+)

| Feature | Description |
|---|---|
| User authentication | JWT-based accounts; per-user conversation history |
| PostgreSQL migration | Replace SQLite for production multi-instance deployments |
| Streaming responses | SSE streaming for `POST /ask` to reduce perceived latency |
| Persistent portfolio | Tie paper trading portfolio to user account |
| Agent evaluation pipeline | Automated LLM-as-judge scoring of agent responses via LangSmith Datasets |
| More RAG sources | Ingest SEC filings, earnings transcripts, FOMC minutes |
| Multi-language support | i18n for frontend; multilingual agent prompts |
| Real broker integration (read-only) | OAuth with Alpaca/IBKR to import real holdings (no trade execution) |

---

*This document reflects the state of the AI Finance Assistant as of v2.0.0 (March 1, 2026). All requirements marked as "SHALL" are implemented and verified by the test suite.*
