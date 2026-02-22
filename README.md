# AI Finance Assistant

A **production-ready, truly agentic AI system** for financial education, built with OpenAI (GPT-4.1), LangGraph `create_react_agent`, FastAPI, SQLite conversation memory, and a React/TypeScript live-data dashboard.

> **Disclaimer:** This system provides **general financial education only**. It does NOT provide personalised financial advice, investment recommendations, tax guidance, or legal advice. Always consult qualified professionals for decisions about your own finances.

---

## Table of Contents

1. [What Makes It Truly Agentic](#what-makes-it-truly-agentic)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Agents](#agents)
5. [Tools & Services](#tools--services)
6. [API Reference](#api-reference)
7. [Frontend](#frontend)
8. [Configuration](#configuration)
9. [Running Tests](#running-tests)
10. [Project Structure](#project-structure)
11. [Adding a New Agent](#adding-a-new-agent)
12. [Safety Disclaimers](#safety-disclaimers)

---

## What Makes It Truly Agentic

| Capability | Before | After |
|---|---|---|
| **Persistent memory** | ❌ Stateless | ✅ SQLite WAL (`ConversationStore`) |
| **LLM-based routing** | ❌ Keyword ROUTING_TABLE | ✅ GPT-4.1-mini with keyword fallback |
| **Memory synthesizer** | ❌ None | ✅ GPT compressor agent (>5 turns) |
| **Real tool calling** | ❌ Prompt stuffing | ✅ `@tool` + `create_react_agent` ReAct loop |
| **LangGraph in production** | ❌ Built but bypassed | ✅ Full `StateGraph` + `MemorySaver` |
| **`MemorySaver` checkpointer** | ❌ None | ✅ Wired with `thread_id=session_id` |
| **Multi-turn context** | ❌ Each query isolated | ✅ "Does it apply to ETFs?" works |
| **Stock agent** | ❌ Missing | ✅ ReAct loop with yfinance tools |
| **Live market data** | ❌ Mock data | ✅ yfinance — no API key needed |
| **Session management** | ❌ None | ✅ UUID session_id end-to-end |

---

## Features

- **7 Specialized AI Agents** — each an expert in a specific financial domain
- **LLM-Based Routing** — GPT-4.1-mini classifies every question and routes to the best agent; falls back to keyword scoring if the LLM call fails
- **Persistent Conversation Memory** — SQLite WAL database stores every session; history injected into agent prompts for multi-turn awareness
- **Memory Synthesizer Agent** — GPT-compresses conversation history into a concise summary when turns exceed 5
- **`create_react_agent` ReAct Loop** — Stock, Portfolio, Market, and Tax agents call `@tool`-decorated yfinance functions iteratively until they have enough data to answer
- **`MemorySaver` LangGraph Checkpointer** — in-session state persisted automatically per `thread_id=session_id`
- **Live yfinance Data** — real stock prices, market overview, 12-month chart, portfolio P&L — no API key
- **Tavily Real-Time Web Search** — news and web context for Finance Q&A and News agents
- **Pinecone RAG** — domain knowledge retrieved and injected for conceptual questions
- **LangSmith Observability** — every ReAct tool call, routing decision, and agent run traced
- **FastAPI Backend** — 9 async REST endpoints with Pydantic validation
- **React + TypeScript Frontend** — live dashboard: market chart, portfolio pie, ticker strip, agent chat

---

## Architecture

```
Client (React / curl)
        │
        ▼  HTTP POST /ask  {question, session_id?}
┌─────────────────────────┐
│   FastAPI  server.py    │  ← /ask  /history/{sid}  /sessions
│                         │    /market/overview  /market/chart
│                         │    /market/quotes    /portfolio/analyze
└──────────┬──────────────┘
           │ process_query(question, session_id)
           ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│  ConversationStore      │────▶│  Memory Synthesizer     │
│  (SQLite WAL)           │     │  (GPT-4.1-mini compressor│
│  sessions + messages    │     │   triggered @ turn > 5)  │
└──────────┬──────────────┘     └─────────────────────────┘
           │ history + summary
           ▼
┌─────────────────────────┐
│  AgentOrchestrator      │  ← LangGraph StateGraph
│  (orchestrator.py)      │     + MemorySaver(thread_id=session_id)
└──────────┬──────────────┘
           │ route_query_llm(question, history)
           ▼
┌─────────────────────────┐
│  LLM Router             │  ← GPT-4.1-mini → {"agent": ..., "confidence": ...}
│  (router.py)            │     keyword fallback if LLM fails
└──────────┬──────────────┘
           │
    ┌──────┴──────────────────────────────────────────┐
    ▼        ▼         ▼        ▼       ▼     ▼       ▼
finance_qa  portfolio  market  goals  news  tax    stock
  _agent    _analysis  _agent  _agent _agent _agent _agent
    │           │          │                        │
    │     create_react_agent  (ReAct loop)           │
    │           │          │                        │
    └───────────┴──────────┴────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          yfinance     Pinecone RAG   LangSmith
       (live prices)  (doc context)  (tracing)
            + Tavily Search (news/web)
```

**Multi-turn request flow:**
```
Session 1, Turn 1:
  POST /ask  {"question": "What is the wash sale rule?", "session_id": null}
    → ConversationStore.new_session_id() → "abc-123"
    → LLM Router → tax_education_agent
    → answer saved to SQLite
  ← {"answer": "...", "agent": "tax_education_agent", "session_id": "abc-123"}

Session 1, Turn 2:
  POST /ask  {"question": "Does it apply to ETFs?", "session_id": "abc-123"}
    → ConversationStore.get_history("abc-123") → [prior turn]
    → LLM Router sees history → still tax_education_agent
    → agent receives: "Previous context: wash sale rule discussed\nUser asks: Does it apply to ETFs?"
    → GPT-4.1 references prior answer without repeating it
  ← {"answer": "Yes, the wash sale rule applies to ETFs because...", ...}
```

### Core Components

| Component | File | Responsibility |
|---|---|---|
| FastAPI App | `src/web_app/server.py` | 9 REST endpoints, CORS, Pydantic validation |
| Orchestrator | `src/workflow/orchestrator.py` | LangGraph StateGraph + MemorySaver + process_query |
| LLM Router | `src/core/router.py` | GPT-4.1-mini routing + keyword fallback |
| Conversation Store | `src/memory/conversation_store.py` | SQLite WAL — sessions, messages, summaries |
| Memory Synthesizer | `src/agents/memory_synthesizer_agent/` | GPT compressor for long histories |
| Stock Agent | `src/agents/stock_agent/` | `create_react_agent` with STOCK_TOOLS |
| Protocol | `src/core/protocol.py` | WorkflowState with conversation_history, memory_summary |
| yfinance Tools | `src/tools/stock_tools.py` etc. | `@tool` decorated — no API key needed |
| Web Search Tool | `src/tools/web_search.py` | Tavily API — real-time search |
| RAG Retriever | `src/rag/retriever.py` | Pinecone query → context string |
| LangSmith Tracing | `src/utils/tracing.py` | `@traceable` decorator + `log_run` |

---

## Agents

Seven specialized agents — the LLM router dispatches based on GPT-4.1-mini classification of the question plus conversation history. Keyword scoring acts as fallback.

| Agent | Module | Triggered by | Tools | ReAct Loop |
|---|---|---|---|---|
| **Finance Q&A** | `finance_qa_agent` | "what is", "explain", "ETF", "current", "Fed" | Tavily, Pinecone | — |
| **Portfolio Analysis** | `portfolio_analysis_agent` | "portfolio", "allocation", "diversif", "holdings" | `PORTFOLIO_TOOLS`, Pinecone | ✅ |
| **Market Analysis** | `market_analysis_agent` | "market", "index", "sector", "S&P", "today" | `MARKET_TOOLS`, Tavily | ✅ |
| **Goal Planning** | `goal_planning_agent` | "goal", "retire", "save", "budget", "FIRE" | Pinecone | — |
| **News Synthesizer** | `news_synthesizer_agent` | "news", "headline", "recent", "earnings" | Tavily (auto) | — |
| **Tax Education** | `tax_education_agent` | "tax", "capital gains", "IRS", "deduction" | `TAX_TOOLS`, Pinecone | ✅ |
| **Stock Analyst** | `stock_agent` | "price", "AAPL", "PE ratio", ticker symbols | `STOCK_TOOLS` | ✅ |

### Stock Agent — `create_react_agent` ReAct Loop

```python
from langgraph.prebuilt import create_react_agent
from src.tools.stock_tools import STOCK_TOOLS

agent = create_react_agent(
    model=llm,
    tools=STOCK_TOOLS,   # get_stock_quote, get_stock_history, get_stock_financials
    prompt=SYSTEM_PROMPT,
    name="stock_agent",
)
# LLM calls tools iteratively:
# tool_call: get_stock_quote("NVDA")
# tool_result: {"price": 875.50, "pe_ratio": 42.1, ...}
# tool_call: get_stock_financials("NVDA")  ← decides it needs more
# tool_result: {"revenue": "...", "eps": "...", ...}
# final_answer: "NVDA is trading at $875.50 with a P/E of 42.1..."
```

Each agent follows the same directory pattern:
```
src/agents/<agent_name>/
├── __init__.py       — public exports
├── client.py         — OpenAI client factory (MODEL, TEMPERATURE)
├── prompts.py        — SYSTEM_PROMPT constant
└── <agent>.py        — ask_<agent>() decorated with @traceable
```

---

## Tools & Services

### yfinance Tools (`src/tools/`) — No API Key Required

All financial data tools are `@tool`-decorated wrappers around `yfinance`. They are used by ReAct agents in iterative tool-calling loops.

**`stock_tools.py`**

| Tool | Description |
|---|---|
| `get_stock_quote(ticker)` | Price, change %, market cap, P/E, 52-week range, volume |
| `get_stock_history(ticker, period)` | OHLCV summary, total return %, annualised volatility |
| `get_stock_financials(ticker)` | Revenue, margins, EPS, debt/equity, ROE, analyst target |

**`portfolio_tools.py`**

| Tool | Description |
|---|---|
| `analyze_portfolio(holdings_json)` | Current value, allocation %, cost basis, P&L per position |
| `get_portfolio_performance(holdings_json, period)` | Portfolio return % vs SPY (alpha) |

**`market_tools.py`**

| Tool | Description |
|---|---|
| `get_market_overview()` | SPY, QQQ, DIA, IWM, VIX, 10-yr yield, GLD, USO |
| `get_sector_performance(period)` | All 11 SPDR sector ETFs sorted by return |

**`tax_tools.py`**

| Tool | Description |
|---|---|
| `calculate_capital_gains(ticker, shares, avg_cost, holding_period_days)` | Short/long-term tax estimate using live price |
| `find_tax_loss_opportunities(holdings_json)` | Positions with unrealised losses, wash-sale note |

**`news_tools.py`**

| Tool | Description |
|---|---|
| `get_stock_news(ticker)` | Recent yfinance news headlines for a ticker |
| `get_market_news()` | Broad market news feed |

---

### Persistent Conversation Memory (`src/memory/conversation_store.py`)

SQLite WAL-mode database at `data/conversations.db` — cross-session persistence without Redis.

```python
from src.memory.conversation_store import ConversationStore

store = ConversationStore()

# Save a turn
store.save_turn(session_id, user_msg, assistant_msg, agent_name)

# Retrieve last 10 messages (injected into agent prompts)
history = store.get_history(session_id, last_n=10)

# Compress long histories with the memory synthesizer
if store.get_turn_count(session_id) >= 5:
    from src.agents.memory_synthesizer_agent import synthesize_memory
    summary = synthesize_memory(history)
    store.save_summary(session_id, summary)
```

---

### Tavily Web Search (`src/tools/web_search.py`)

Gives Finance Q&A, Market Analysis, and News agents access to live internet data.

```python
from src.tools.web_search import web_search, is_realtime_query

if is_realtime_query("Who is the current Fed chair?"):
    context = web_search("Federal Reserve chair 2026")
    # → injected into system prompt
```

Requires `TAVILY_API_KEY` in `.env`. Agents fall back gracefully to LLM training data without it.

---

### Pinecone RAG (`src/rag/`)

```python
from src.rag.retriever import get_rag_context, should_use_rag

if should_use_rag(question):
    context = get_rag_context(question, top_k=3, agent_filter="finance_qa")
```

**Setup:** Create a Pinecone Serverless index (`dimension=1536`), set `PINECONE_API_KEY` and `PINECONE_INDEX` in `.env`, then call `upsert_documents()` to populate.

---

### LangSmith Tracing (`src/utils/tracing.py`)

Every agent call, tool invocation in the ReAct loop, routing decision, and memory synthesis operation is visible in LangSmith.

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=ai-finance-assistant
```

The ReAct tool loop produces especially rich traces — each `tool_call → tool_result → final_answer` cycle is a separate child span.

---

## API Reference

### `GET /health`

```json
{"status": "ok"}
```

### `POST /ask`

```json
{
  "question": "What is NVDA trading at today?",
  "session_id": "abc-123"   // optional — auto-generated if absent
}
```

```json
{
  "question": "What is NVDA trading at today?",
  "answer": "NVIDIA (NVDA) is currently trading at $875.50...",
  "agent": "stock_agent",
  "session_id": "abc-123"
}
```

Pass the returned `session_id` in subsequent requests to maintain conversation continuity.

---

### `GET /history/{session_id}`

Returns the last N conversation turns for a session.

```json
[
  {"role": "user", "content": "What is the wash sale rule?", "agent": null},
  {"role": "assistant", "content": "The wash sale rule...", "agent": "tax_education_agent"}
]
```

---

### `GET /sessions`

Lists all session IDs with turn counts.

---

### `GET /market/overview`

Live prices and change % for SPY, QQQ, DIA, IWM, VIX, ^TNX, GLD, USO via yfinance.

```json
{
  "SPY": {"price": 689.43, "change_pct": 0.68, "name": "SPDR S&P 500 ETF"},
  "QQQ": {"price": 523.10, "change_pct": 1.12, "name": "Invesco QQQ"},
  ...
}
```

---

### `GET /market/chart`

12-month monthly OHLCV for SPY, QQQ, DIA — used to render the live market chart.

```json
[
  {"date": "Mar 2025", "sp500": 580.12, "nasdaq": 489.34, "dow": 440.10},
  ...
]
```

---

### `GET /market/quotes?symbols=SPY,AAPL,TSLA,NVDA,BTC-USD`

Live prices for an arbitrary comma-separated ticker list.

---

### `POST /portfolio/analyze`

```json
{
  "holdings": [
    {"ticker": "AAPL", "shares": 10, "avg_cost": 150},
    {"ticker": "TSLA", "shares": 5,  "avg_cost": 200}
  ]
}
```

```json
{
  "holdings": [
    {"ticker": "AAPL", "current_price": 264.58, "pnl": 1145.80, "allocation_pct": 56.23, ...},
    ...
  ],
  "summary": {"total_value": 4704.90, "total_pnl": 2204.90, "concentration_risk": "high"}
}
```

### Interactive Docs

Swagger UI: `http://localhost:8000/docs` &nbsp;|&nbsp; ReDoc: `http://localhost:8000/redoc`

### Example curl commands

```bash
# Health
curl http://localhost:8000/health

# Multi-turn conversation
SID=$(curl -s -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is the wash sale rule?"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d "{\"question\":\"Does it apply to ETFs?\",\"session_id\":\"$SID\"}"

# Stock agent ReAct loop
curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Compare NVDA and AMD — which has better fundamentals?"}'

# Live market data
curl http://localhost:8000/market/overview
curl "http://localhost:8000/market/quotes?symbols=SPY,AAPL,TSLA"

# Portfolio analysis
curl -X POST http://localhost:8000/portfolio/analyze \
  -H 'Content-Type: application/json' \
  -d '{"holdings":[{"ticker":"AAPL","shares":10,"avg_cost":150}]}'
```

---

## Frontend

A React 19 + TypeScript live-data dashboard at `src/web_app/frontend/`.

**Key libraries:** React, Vite, Recharts, Framer Motion, react-markdown, lucide-react.

### Components

| Component | Description |
|---|---|
| `Dashboard.tsx` | Fetches `/market/overview` — live SPY/QQQ/VIX insight cards |
| `ChatInterface.tsx` | Session-aware chat; sends `session_id`; shows agent badge |
| `MarketChart.tsx` | Fetches `/market/chart` — 12-month live line chart |
| `PortfolioChart.tsx` | POSTs to `/portfolio/analyze` — live pie chart + P&L summary |
| `PortfolioInput.tsx` | Add/remove holdings (ticker, shares, avg cost) |
| `RightSidebar.tsx` | Fetches `/market/quotes` — live ticker strip with change % |
| `AgentBadge.tsx` | Colour-coded badge for each of the 7 agents |
| `MessageBubble.tsx` | Markdown-rendered message with agent identification |

### Frontend Storage

| Key | Storage | Content |
|---|---|---|
| `finnie_holdings` | localStorage | Portfolio positions (`Holding[]`) |
| `finnie_backend_session_map` | localStorage | Frontend UUID → backend session UUID map |
| `finnie_sessions` | localStorage | Chat session list |
| `finnie_active_session` | localStorage | Currently active session ID |

**Run (development):**
```bash
cd src/web_app/frontend
npm install
npm run dev          # http://localhost:5173
```

**Build for production:**
```bash
npm run build        # outputs to dist/
```

---

## Configuration (`config.yaml`)

```yaml
openai:
  model: gpt-4.1          # model used by all agents
  temperature: 0.3        # lower = more factual responses

server:
  host: "0.0.0.0"
  port: 8000

agents:
  max_iterations: 10      # max LangGraph iterations per query
  timeout: 300            # seconds before a query times out

workflow:
  max_concurrent_tasks: 5
  retry_attempts: 3
```

| Key | Default | Description |
|---|---|---|
| `openai.model` | `gpt-4.1` | OpenAI model (try `gpt-4o-mini` for lower cost) |
| `openai.temperature` | `0.3` | Sampling temperature |
| `server.host` | `0.0.0.0` | Bind address |
| `server.port` | `8000` | Listen port |
| `agents.max_iterations` | `10` | LangGraph workflow cap |
| `agents.timeout` | `300` | Request timeout in seconds |

---

## Running Tests

```bash
# Unit + integration tests
pytest tests/ -v

# Individual agent tests
pytest tests/test_finance_agent.py -v
pytest tests/test_portfolio_agent.py -v
pytest tests/test_market_agent.py -v
pytest tests/test_goal_agent.py -v
pytest tests/test_news_agent.py -v
pytest tests/test_tax_agent.py -v

# API tests (requires running server)
pytest tests/test_api.py -v
```

---

## Project Structure

```
ai_finance_assistant/
├── src/
│   ├── agents/
│   │   ├── finance_qa_agent/          ← Q&A: concepts, current events  [Tavily + RAG]
│   │   ├── portfolio_analysis_agent/  ← Portfolio diversification      [PORTFOLIO_TOOLS ReAct]
│   │   ├── market_analysis_agent/     ← Market trends & macro          [MARKET_TOOLS ReAct + Tavily]
│   │   ├── goal_planning_agent/       ← Goal setting & budgeting       [RAG]
│   │   ├── news_synthesizer_agent/    ← Financial news synthesis       [Tavily auto-fetch]
│   │   ├── tax_education_agent/       ← Tax concepts education         [TAX_TOOLS ReAct + RAG]
│   │   ├── stock_agent/               ← NEW: Stock lookups & analysis  [STOCK_TOOLS ReAct]
│   │   └── memory_synthesizer_agent/  ← NEW: GPT history compressor
│   ├── core/
│   │   ├── base_agent.py              ← Abstract base class
│   │   ├── protocol.py                ← WorkflowState with history + summary
│   │   └── router.py                  ← LLM routing (GPT-4.1-mini) + keyword fallback
│   ├── memory/                        ← NEW: Persistent conversation memory
│   │   └── conversation_store.py      ← SQLite WAL — sessions + messages + summaries
│   ├── tools/
│   │   ├── stock_tools.py             ← NEW: @tool yfinance stock wrappers
│   │   ├── portfolio_tools.py         ← NEW: @tool portfolio analysis
│   │   ├── market_tools.py            ← NEW: @tool market overview/sectors
│   │   ├── tax_tools.py               ← NEW: @tool capital gains + tax loss
│   │   ├── news_tools.py              ← NEW: @tool yfinance news feed
│   │   └── web_search.py              ← Tavily real-time search
│   ├── workflow/
│   │   └── orchestrator.py            ← StateGraph + MemorySaver(thread_id=session_id)
│   ├── rag/
│   │   ├── pinecone_store.py          ← Pinecone upsert + query
│   │   └── retriever.py               ← get_rag_context() for agents
│   ├── web_app/
│   │   ├── server.py                  ← FastAPI (9 endpoints)
│   │   └── frontend/                  ← React + TypeScript + Vite
│   │       └── src/
│   │           ├── components/
│   │           │   ├── PortfolioInput.tsx  ← NEW: add/remove holdings
│   │           │   ├── PortfolioChart.tsx  ← UPDATED: live /portfolio/analyze
│   │           │   ├── MarketChart.tsx     ← UPDATED: live /market/chart
│   │           │   ├── RightSidebar.tsx    ← UPDATED: live /market/quotes
│   │           │   └── Dashboard.tsx       ← UPDATED: live /market/overview
│   │           └── lib/
│   │               ├── holdingsStore.ts   ← NEW: localStorage CRUD for holdings
│   │               ├── storage.ts         ← UPDATED: session_id persistence
│   │               └── api.ts             ← UPDATED: session_id in ask()
│   └── utils/
│       ├── logging.py                 ← Shared structured logger
│       └── tracing.py                 ← LangSmith @traceable + log_run
├── data/
│   └── conversations.db               ← SQLite WAL conversation store (auto-created)
├── tests/
│   ├── test_api.py
│   ├── test_finance_agent.py
│   ├── test_portfolio_agent.py
│   ├── test_market_agent.py
│   ├── test_goal_agent.py
│   ├── test_news_agent.py
│   └── test_tax_agent.py
├── .env                               ← API keys: OpenAI, Tavily, Pinecone, LangSmith
├── config.yaml
├── requirements.txt
└── test_system.py
```

---

## Adding a New Agent

1. **Create the agent directory:**
   ```
   src/agents/my_new_agent/
   ├── __init__.py
   ├── client.py      ← get_client(), MODEL, TEMPERATURE
   ├── prompts.py     ← SYSTEM_PROMPT
   └── my_agent.py    ← ask_my_agent(question, history=None, memory_summary=None) -> str
   ```

2. **Add tools** (optional) in `src/tools/my_tools.py`:
   ```python
   from langchain_core.tools import tool

   @tool
   def my_data_tool(ticker: str) -> dict:
       """Fetch data for a given ticker."""
       ...

   MY_TOOLS = [my_data_tool]
   ```

3. **Use `create_react_agent`** (preferred) in `my_agent.py`:
   ```python
   from langgraph.prebuilt import create_react_agent
   from src.tools.my_tools import MY_TOOLS

   def create_my_agent(llm):
       return create_react_agent(llm, tools=MY_TOOLS, prompt=SYSTEM_PROMPT)
   ```

4. **Register** in `src/core/router.py` — add an entry to `AGENT_DESCRIPTIONS` for LLM routing and `ROUTING_TABLE` for keyword fallback.

5. **Wire** in `src/workflow/orchestrator.py` — add a dispatch branch in `process_query()`.

6. **Write tests** in `tests/test_my_agent.py`.

---

## Safety Disclaimers

- All agent system prompts are explicitly restricted to **general financial education**.
- The system will **not** provide stock picks, personalised tax advice, or investment recommendations.
- Portfolio and market analysis outputs are educational illustrations only.
- Users requiring actionable advice should consult a licensed financial advisor, CPA, or attorney.
