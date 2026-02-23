# GitHub Copilot Instructions — AI Finance Assistant

> These instructions give GitHub Copilot context about the project structure, conventions, and patterns so that generated code fits naturally into the existing codebase.

---

## Project Overview

This is a **production-ready, multi-agent AI finance assistant** built with:

- **FastAPI** — REST backend (`src/web_app/server.py`)
- **LangGraph** `StateGraph` + `MemorySaver` — agent orchestration with in-session state persistence
- **OpenAI GPT-4.1** — all LLM calls (routing + agent responses)
- **LangChain `@tool`** — all yfinance data tools; used in ReAct loops
- **SQLite WAL** — persistent conversation memory (`src/memory/conversation_store.py`)
- **Pinecone** — optional RAG context retrieval (`src/rag/`)
- **Tavily** — optional real-time web search (`src/tools/web_search.py`)
- **LangSmith** — observability via `@traceable` (`src/utils/tracing.py`)
- **React 19 + TypeScript + Vite** — frontend dashboard (`src/web_app/frontend/`)

**Disclaimer enforced everywhere:** general financial *education* only — never personalised advice.

---

## Directory Layout

```
src/
├── agents/                        # All domain-specific agents
│   ├── __init__.py                # Single public re-export of every agent function
│   ├── finance_qa_agent/          # General finance Q&A  (Tavily + RAG)
│   ├── portfolio_analysis_agent/  # Portfolio analysis   (PORTFOLIO_TOOLS ReAct)
│   ├── market_analysis_agent/     # Market trends        (MARKET_TOOLS ReAct + Tavily)
│   ├── goal_planning_agent/       # Goal planning        (RAG)
│   ├── news_synthesizer_agent/    # News synthesis       (Tavily auto-fetch)
│   ├── tax_education_agent/       # Tax education        (TAX_TOOLS ReAct + RAG)
│   ├── stock_agent/               # Stock analysis       (STOCK_TOOLS ReAct)
│   ├── trading_agent/             # Paper trading        (buy/sell tools + SQLite)
│   └── memory_synthesizer_agent/  # History compressor   (GPT — triggered >5 turns)
├── core/
│   ├── base_agent.py              # Abstract BaseAgent class all agents inherit
│   ├── protocol.py                # WorkflowState Pydantic model (LangGraph state)
│   ├── router.py                  # RouterAgent — GPT-4.1-mini routing + keyword fallback
│   └── guards.py                  # Safety / content guardrails
├── memory/
│   ├── conversation_store.py      # SQLite WAL — sessions, messages, summaries
│   └── portfolio_store.py         # SQLite — portfolio holdings CRUD
├── tools/
│   ├── stock_tools.py             # @tool yfinance: quote, history, financials → STOCK_TOOLS
│   ├── portfolio_tools.py         # @tool portfolio P&L + performance → PORTFOLIO_TOOLS
│   ├── market_tools.py            # @tool market overview + sectors → MARKET_TOOLS
│   ├── tax_tools.py               # @tool capital gains + tax-loss harvest → TAX_TOOLS
│   ├── news_tools.py              # @tool yfinance news feed
│   ├── trading_tools.py           # @tool paper buy/sell/positions → TRADING_TOOLS
│   └── web_search.py              # Tavily real-time search; is_realtime_query()
├── rag/
│   ├── pinecone_store.py          # Pinecone upsert + query helpers
│   └── retriever.py               # get_rag_context(q, top_k, agent_filter) -> str
├── workflow/
│   └── orchestrator.py            # AgentOrchestrator (LangGraph StateGraph) + process_query()
├── web_app/
│   ├── server.py                  # FastAPI app — 9 REST endpoints
│   └── frontend/                  # React + TypeScript + Vite
└── utils/
    ├── logging.py                 # get_logger(name) — structured JSON logger
    └── tracing.py                 # @traceable decorator + log_run(); LangSmith wiring
```

---

## Agent Architecture

### Standard Agent Structure

Every agent lives in its own directory and follows this exact layout:

```
src/agents/<agent_name>/
├── __init__.py     # Re-exports the main public function(s)
├── client.py       # OpenAI client factory — MODEL, TEMPERATURE, get_client()
├── prompts.py      # SYSTEM_PROMPT constant (string)
└── <agent>.py      # ask_<agent>(question, history=None, memory_summary=None) -> str
                    # Decorated with @traceable from src/utils/tracing.py
```

### How Agents Are Called

All agent entry-point functions share the same signature:

```python
def ask_finance_agent(
    question: str,
    history: list[dict[str, str]] | None = None,
    memory_summary: str | None = None,
) -> str: ...
```

- `history` — last N `{"role": "user"|"assistant", "content": "..."}` dicts (from SQLite)
- `memory_summary` — GPT-compressed summary of older turns (from `synthesize_memory`)

### ReAct Agents (Tool-Calling Loop)

The following agents run a manual ReAct loop via `_run_react_loop()`:

| Agent | Tools list | Max iterations |
|---|---|---|
| `stock_agent` | `STOCK_TOOLS` | 8 |
| `market_analysis_agent` | `MARKET_TOOLS` | 8 |
| `portfolio_analysis_agent` | `PORTFOLIO_TOOLS` | 8 |
| `tax_education_agent` | `TAX_TOOLS` | 8 |
| `trading_agent` | `TRADING_TOOLS` | 8 |

The loop is implemented as:

```python
llm_with_tools = llm.bind_tools(tools)
# Iterates: LLM → tool_call → ToolMessage → LLM → ... → final text answer
```

---

## Orchestration Flow

```
POST /ask
  └─► process_query(question, session_id)           # workflow/orchestrator.py
        ├─► ConversationStore.get_history()          # inject prior turns
        ├─► (if turns > 5) synthesize_memory()       # compress history
        ├─► RouterAgent._execute()                   # LLM routing → agent name
        │     └─► GPT-4.1-mini JSON → {"agent": ..., "confidence": ...}
        │          └─► keyword fallback if LLM fails
        ├─► LangGraph StateGraph node "execute_agent"
        │     └─► agents[name].run(AgentInput)
        └─► ConversationStore.save_turn()            # persist Q&A to SQLite
```

---

## Key Conventions

### Imports

Always import agents through the package `__init__.py`:

```python
# ✅ Correct
from src.agents import ask_stock_agent, synthesize_memory

# ❌ Avoid direct module imports in outside code
from src.agents.stock_agent.stock_agent import ask_stock_agent
```

### Adding a New Tool

```python
# src/tools/my_tools.py
from langchain_core.tools import tool

@tool
def my_tool(ticker: str) -> dict:
    """One-line docstring — shown to the LLM as the tool description."""
    ...

MY_TOOLS = [my_tool]
```

### Adding a New Agent

1. Create `src/agents/my_agent/` with `__init__.py`, `client.py`, `prompts.py`, `my_agent.py`
2. Implement `ask_my_agent(question, history=None, memory_summary=None) -> str` decorated with `@traceable`
3. Export from `src/agents/my_agent/__init__.py`
4. Add to `src/agents/__init__.py` (import + `__all__`)
5. Register in `src/core/router.py` — add to `AGENT_DESCRIPTIONS` (LLM routing) and `ROUTING_TABLE` (keyword fallback)
6. Wire dispatch branch in `src/workflow/orchestrator.py` → `process_query()`
7. Write tests in `tests/test_my_agent.py`

### Logging

```python
from src.utils.logging import get_logger
logger = get_logger(__name__)
```

### Tracing

```python
from src.utils.tracing import traceable

@traceable(name="my_agent_run")
def ask_my_agent(question: str, ...) -> str:
    ...
```

### Environment Variables

| Variable | Required | Used by |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | All agents, router |
| `OPENAI_MODEL` | optional | Defaults to `gpt-4.1` |
| `TAVILY_API_KEY` | optional | `web_search.py` |
| `PINECONE_API_KEY` | optional | `rag/pinecone_store.py` |
| `PINECONE_INDEX` | optional | `rag/pinecone_store.py` |
| `LANGCHAIN_API_KEY` | optional | LangSmith tracing |
| `LANGCHAIN_TRACING_V2` | optional | Set `true` to enable tracing |
| `LANGCHAIN_PROJECT` | optional | LangSmith project name |

---

## FastAPI Endpoints

| Method | Path | Handler | Description |
|---|---|---|---|
| GET | `/health` | `health_check` | Liveness probe |
| POST | `/ask` | `ask` | Main chat endpoint |
| GET | `/history/{session_id}` | `get_history` | Conversation history |
| GET | `/sessions` | `list_sessions` | All sessions |
| GET | `/market/overview` | `market_overview` | Live index prices |
| GET | `/market/chart` | `market_chart` | 12-month OHLCV |
| GET | `/market/quotes` | `market_quotes` | Arbitrary ticker prices |
| POST | `/portfolio/analyze` | `portfolio_analyze` | P&L + allocation |

---

## Pydantic Models (server.py)

```python
class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None  # None → new session

class AskResponse(BaseModel):
    question: str
    answer: str
    agent: str
    session_id: str
```

---

## Testing

```bash
# All tests
pytest tests/ -v

# Individual
pytest tests/test_finance_agent.py -v
pytest tests/test_api.py -v          # requires running server

# System smoke test
python test_system.py
```

Test files live in `tests/` (project root) and `src/tests/` (unit tests for internals).

---

## Safety Rules (enforced in all agent system prompts)

- Agents are restricted to **general financial education**
- No personalised investment/tax advice, stock picks, or legal guidance
- Every `SYSTEM_PROMPT` includes the disclaimer; Copilot should preserve it when editing prompts
