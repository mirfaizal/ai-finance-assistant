# AI Finance Assistant

A **production-ready, multi-agent AI system** for financial education, built with OpenAI (GPT-4.1), FastAPI, LangGraph, and a React/TypeScript frontend.

> **Disclaimer:** This system provides **general financial education only**. It does NOT provide personalised financial advice, investment recommendations, tax guidance, or legal advice. Always consult qualified professionals for decisions about your own finances.

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Agents](#agents)
4. [API Reference](#api-reference)
5. [Frontend](#frontend)
6. [Configuration](#configuration)
7. [Running Tests](#running-tests)
8. [Project Structure](#project-structure)
9. [Adding a New Agent](#adding-a-new-agent)
10. [Safety Disclaimers](#safety-disclaimers)

---

## Features

- **6 Specialized AI Agents** — each expert in a specific financial domain
- **Intelligent Routing** — keyword-based router dispatches each query to the correct agent automatically
- **Tavily Real-Time Web Search** — agents automatically fetch live data (current news, stock prices, today's date, current affairs) when the query needs it
- **Pinecone RAG** — relevant document chunks from your knowledge base are retrieved and injected into the LLM prompt before each answer
- **LangSmith Observability** — every agent call and orchestrator run is traced and visible in the LangSmith UI (enable with one env var)
- **LangGraph Orchestration** — `StateGraph`-based workflow with routing, execution, and state management
- **FastAPI Backend** — async REST API with automatic OpenAPI/Swagger docs
- **React + TypeScript Frontend** — interactive dashboard with charts and conversation interface
- **Type-Safe Communication** — Pydantic models validate every request/response
- **Extensible** — add new agents by inheriting from `BaseAgent`
- **Configurable** — `config.yaml` controls model, temperature, Tavily, Pinecone, LangSmith, and agent settings

---

## Architecture

```
Client (React / curl)
        │
        ▼  HTTP POST /ask
┌─────────────────────────┐
│   FastAPI  server.py    │  ← GET /health  |  POST /ask  |  GET /docs
└──────────┬──────────────┘
           │ process_query(question)          ← logged to LangSmith
           ▼
┌─────────────────────────┐
│  Orchestrator           │  ← LangGraph StateGraph
│  (orchestrator.py)      │     router → execute_agent → finalize
└──────────┬──────────────┘
           │ route_query(question)
           ▼
┌─────────────────────────┐
│  Router Agent           │  ← Keyword scoring → picks best agent
│  (router.py)            │
└──────────┬──────────────┘
           │
    ┌──────┴──────────────────────────────────┐
    ▼        ▼         ▼        ▼       ▼     ▼
finance_qa  portfolio  market  goals  news  tax
  _agent    _analysis  _analysis _planning _synth _educ
    │           │          │        │       │      │
    └───────────┴──────────┴────────┴───────┴──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        Tavily API    Pinecone RAG   LangSmith
       (live search) (doc context)  (tracing)
```

**Enriched request flow:**
```
POST /ask  {"question": "Who is the current Fed chair?"}
  → server.py: validates request
  → orchestrator.process_query(question)
      → router: routes to finance_qa_agent (matches "current")
      → finance_qa_agent:
          ① is_realtime_query? YES → Tavily search → live web context injected
          ② should_use_rag?  YES → Pinecone query → doc chunks injected
          ③ OpenAI GPT-4.1  → answer with grounded, up-to-date context
      → LangSmith: run logged (if LANGCHAIN_TRACING_V2=true)
  ← {"question": "...", "answer": "Jerome Powell is...", "agent": "finance_qa_agent"}
```

### Core Components

| Component | File | Responsibility |
|---|---|---|
| FastAPI App | `src/web_app/server.py` | REST endpoints, CORS, error handling |
| Orchestrator | `src/workflow/orchestrator.py` | LangGraph workflow, LangSmith `log_run` |
| Router | `src/core/router.py` | Keyword scoring, agent selection |
| Base Agent | `src/core/base_agent.py` | Abstract class all agents inherit from |
| Protocol | `src/core/protocol.py` | Pydantic models for all messages/state |
| **Web Search Tool** | `src/tools/web_search.py` | **Tavily API — real-time search for agents** |
| **RAG Retriever** | `src/rag/retriever.py` | **Pinecone query → context string for prompts** |
| **Pinecone Store** | `src/rag/pinecone_store.py` | **Embed + upsert + query Pinecone index** |
| **LangSmith Tracing** | `src/utils/tracing.py` | **`@traceable` decorator + `log_run` helper** |
| Logging | `src/utils/logging.py` | Shared structured logging |

---

## Agents

Six specialized agents are registered with the router. The router dispatches based on keyword scoring of the incoming question. **All agents now support real-time Tavily search, Pinecone RAG context, and LangSmith tracing.**

| Agent | Module | Triggered by keywords like… | Tavily | RAG |
|---|---|---|---|---|
| **Finance Q&A** | `finance_qa_agent` | "what is", "explain", "ETF", "interest", "current", "today", "who is" | ✅ | ✅ |
| **Portfolio Analysis** | `portfolio_analysis_agent` | "portfolio", "allocation", "diversif", "holdings" | — | ✅ |
| **Market Analysis** | `market_analysis_agent` | "market", "index", "sector", "S&P", "stock price", "today" | ✅ | — |
| **Goal Planning** | `goal_planning_agent` | "goal", "retire", "save", "budget", "emergency fund" | — | ✅ |
| **News Synthesizer** | `news_synthesizer_agent` | "news", "article", "headline", "recent", "current events" | ✅ (auto) | — |
| **Tax Education** | `tax_education_agent` | "tax", "deduction", "credit", "capital gains", "IRS" | — | ✅ |

Each agent follows the same pattern:
```
src/agents/<agent_name>/
├── __init__.py       — public exports
├── client.py         — OpenAI client factory (MODEL, TEMPERATURE)
├── prompts.py        — SYSTEM_PROMPT constant
└── <agent>.py        — core function decorated with @traceable
```

---

## Tools & Services

### Tavily Web Search (`src/tools/web_search.py`)

Gives agents access to **live internet data** — current news, today's prices, who currently holds a role, etc.

```python
from src.tools.web_search import web_search, is_realtime_query

# Automatic check — triggered inside agents
if is_realtime_query("Who is the current Fed chair?"):
    context = web_search("Who is the current Federal Reserve chair 2025")
    # → injects live results into LLM system prompt
```

| Function | Description |
|---|---|
| `web_search(query, max_results)` | Call Tavily, return formatted results string |
| `is_realtime_query(question)` | Heuristic: should this question fetch live data? |
| `finance_search(topic, context_hint)` | Convenience wrapper for finance-focused searches |

Requires: `TAVILY_API_KEY` in `.env`. Without it, agents silently fall back to LLM training data.

---

### Pinecone RAG (`src/rag/`)

Allows agents to answer from **your own knowledge base** — financial regulations, fund prospectuses, internal reports, etc.

```python
from src.rag.retriever import get_rag_context, should_use_rag
from src.rag.pinecone_store import upsert_documents

# One-time: load your documents into Pinecone
upsert_documents([
    {"id": "etf-101", "text": "An ETF is a basket of securities...",
     "metadata": {"source": "finance-basics", "agent": "finance_qa"}},
])

# At query time (happens automatically inside agents)
if should_use_rag(question):
    context = get_rag_context(question, top_k=3, agent_filter="finance_qa")
    # → injects retrieved chunks into LLM system prompt
```

| Function | Description |
|---|---|
| `upsert_documents(docs)` | Embed + store document chunks in Pinecone |
| `query_similar(query, top_k)` | Search Pinecone for nearest neighbours |
| `get_rag_context(question, top_k, agent_filter)` | Returns formatted context string for prompt injection |
| `should_use_rag(question)` | Heuristic: would this question benefit from RAG? |

**Setup:**
1. Create a Pinecone Serverless index with `dimension=1536` (ada-002) at [app.pinecone.io](https://app.pinecone.io)
2. Set `PINECONE_API_KEY` and `PINECONE_INDEX` in `.env`
3. Run `upsert_documents()` to populate it with your domain content

---

### LangSmith Tracing (`src/utils/tracing.py`)

Every agent call and orchestrator run is traced and inspectable in the [LangSmith UI](https://smith.langchain.com).

```python
from src.utils.tracing import traceable, log_run

# Applied to every agent function:
@traceable(name="finance_qa_agent", run_type="chain", tags=["finance", "qa"])
def ask_finance_agent(question: str) -> str:
    ...

# Manual span logging (used in orchestrator):
log_run(
    name="process_query",
    inputs={"question": question, "routed_to": agent_name},
    outputs={"answer": answer[:200]},
    tags=["orchestrator"],
)
```

**Enable tracing in `.env`:**
```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=ai-finance-assistant
```

All traces appear under the `ai-finance-assistant` project in your LangSmith workspace. When `LANGCHAIN_TRACING_V2` is `false` or unset, `@traceable` is a transparent no-op — zero overhead, no crashes.

---

## API Reference

### `GET /health`

Returns 200 OK when the service is running.

```json
{"status": "ok"}
```

### `POST /ask`

Route a finance question through the multi-agent system.

**Request body:**

```json
{
  "question": "What is an ETF?"
}
```

For structured portfolio analysis, the orchestrator can accept richer payloads via the frontend (the backend `AskRequest` currently takes `question: str`; portfolio data is embedded in the question text or handled via the frontend layer).

**Response body:**

```json
{
  "question": "What is an ETF?",
  "answer": "An ETF (Exchange-Traded Fund) is a type of investment fund...",
  "agent": "finance_qa_agent"
}
```

**Error responses:**

| Status | Meaning |
|---|---|
| 422 | Empty or invalid `question` field |
| 500 | OpenAI API error or internal failure |

### Interactive Docs

Available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

### Example curl commands

```bash
# Health check
curl http://localhost:8000/health

# Finance Q&A
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is compound interest?"}'

# Tax education
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the difference between a Roth IRA and a Traditional IRA?"}'

# Market analysis
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do rising interest rates affect the stock market?"}'

# Goal planning
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How should I plan for retirement in my 30s?"}'
```

---

## Frontend

A React 19 + TypeScript dashboard located at `src/web_app/frontend/`.

**Key libraries:** React, Vite, Recharts (charts), Framer Motion (animation), react-markdown, lucide-react (icons).

**Components:**

| Component | Description |
|---|---|
| `Dashboard.tsx` | Main layout container |
| `ChatInterface.tsx` | Sends questions to `POST /ask`, renders agent responses |
| `Sidebar.tsx` | Navigation and agent selector |
| `RightSidebar.tsx` | Supplementary info panel |
| `PortfolioChart.tsx` | Recharts pie/bar chart for portfolio data |
| `MarketChart.tsx` | Recharts line chart for market data |
| `AgentBadge.tsx` | Displays which agent answered |
| `MessageBubble.tsx` | Chat message component with Markdown rendering |

**Run the frontend (development):**
```bash
cd src/web_app/frontend
npm install
npm run dev          # starts Vite dev server on http://localhost:5173
```

**Build for production:**
```bash
npm run build        # outputs to dist/
```

The frontend connects to the FastAPI backend at `http://localhost:8000` by default (configured in `src/web_app/frontend/src/lib/api.ts`).

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
│   │   ├── finance_qa_agent/        ← Q&A on financial concepts  [Tavily + RAG + LangSmith]
│   │   ├── portfolio_analysis_agent/← Portfolio diversification  [RAG + LangSmith]
│   │   ├── market_analysis_agent/   ← Market trends & macro      [Tavily + LangSmith]
│   │   ├── goal_planning_agent/     ← Goal setting & budgeting   [RAG + LangSmith]
│   │   ├── news_synthesizer_agent/  ← Financial news synthesis   [Tavily auto-fetch + LangSmith]
│   │   ├── tax_education_agent/     ← Tax concepts education     [RAG + LangSmith]
│   │   └── example_agents.py        ← Legacy example agents
│   ├── core/
│   │   ├── base_agent.py            ← Abstract base class for all agents
│   │   ├── protocol.py              ← Pydantic models (AgentInput/Output/etc.)
│   │   └── router.py                ← Keyword-scoring router
│   ├── tools/                       ← NEW: Shared agent tools
│   │   ├── __init__.py
│   │   └── web_search.py            ← NEW: Tavily real-time web search tool
│   ├── workflow/
│   │   └── orchestrator.py          ← LangGraph StateGraph + process_query() [LangSmith log_run]
│   ├── rag/                         ← NEW: Retrieval-Augmented Generation
│   │   ├── __init__.py
│   │   ├── pinecone_store.py        ← NEW: Pinecone upsert + query
│   │   └── retriever.py             ← NEW: get_rag_context() for agents
│   ├── web_app/
│   │   ├── server.py                ← FastAPI app (POST /ask, GET /health)
│   │   └── frontend/                ← React + TypeScript + Vite UI
│   ├── data/                        ← (placeholder) financial datasets
│   └── utils/
│       ├── logging.py               ← Shared structured logger
│       └── tracing.py               ← NEW: LangSmith @traceable + log_run
├── tests/
│   ├── test_api.py
│   ├── test_finance_agent.py
│   ├── test_portfolio_agent.py
│   ├── test_market_agent.py
│   ├── test_goal_agent.py
│   ├── test_news_agent.py
│   └── test_tax_agent.py
├── .env                             ← API keys: OpenAI, Tavily, Pinecone, LangSmith
├── config.yaml                      ← All service configuration
├── requirements.txt                 ← Python dependencies
└── test_system.py                   ← Quick smoke tests
```

---

## Adding a New Agent

1. **Create the agent directory:**
   ```
   src/agents/my_new_agent/
   ├── __init__.py
   ├── client.py      ← get_client(), MODEL, TEMPERATURE
   ├── prompts.py     ← SYSTEM_PROMPT
   └── my_agent.py    ← core function: def my_function(query: str) -> str
   ```

2. **Register routing keywords** in `src/core/router.py` — add keywords to the `ROUTING_TABLE` dict so the router can score your agent.

3. **Wire into the orchestrator** in `src/workflow/orchestrator.py` — import your function and add a branch that calls it when your agent is selected.

4. **Write tests** in `tests/test_my_agent.py`.

---

## Safety Disclaimers

- All agent system prompts are explicitly restricted to **general financial education**.
- The system will **not** provide stock picks, personalised tax advice, or investment recommendations.
- Portfolio and market analysis outputs are educational illustrations only.
- Users requiring actionable advice should consult a licensed financial advisor, CPA, or attorney.
