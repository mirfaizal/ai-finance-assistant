# Plan: Make AI Finance Assistant Truly Agentic

## Gap Analysis (You vs. Reference Projects)

| Feature | Reference Projects | Your Project |
|---|---|---|
| Persistent memory (SQLite) | ✅ FinBrief | ❌ Stateless |
| LLM-based routing | Implied | ❌ Keyword ROUTING_TABLE |
| Memory summarizer agent | ✅ Project 2 | ❌ News synthesis only |
| Real tool calling (OpenAI tools API) | Implied by LangGraph | ❌ Prompt stuffing |
| LangGraph actually used in production | ✅ | ❌ Built but bypassed |
| Multi-agent handoff | ✅ LangGraph edges | ❌ `next_agent` never set |
| FAISS / vector search | ✅ FinBrief | ✅ Pinecone (equivalent) |
| Conversation context carry-over | ✅ "Does it apply to ETFs?" | ❌ Each request is isolated |
| Stock Agent (yfinance + ReAct loop) | ✅ `finance_agent-main` | ❌ No stock-specific agent |
| `@tool` decorated yfinance wrappers | ✅ `financial_data.py` | ❌ Tavily prompt-stuffing only |
| `MemorySaver` LangGraph checkpointer | ✅ `finance_agent-main` | ❌ No checkpointer wired up |
| Supervisor pattern (multi-agent graph) | ✅ `finance_agent-main` | ❌ Single-agent dispatch only |

---

## Step 1 — Persistent Conversation Memory (SQLite)

- Add a `src/memory/` module with a `ConversationStore` class backed by SQLite
- Schema: `sessions(session_id, created_at)` + `messages(id, session_id, role, content, agent, timestamp)`
- `save_turn(session_id, user_msg, assistant_msg, agent_name)` and `get_history(session_id, last_n=10)` methods
- This directly enables the "Does it apply to ETFs?" multi-turn example from FinBrief

## Step 2 — Memory Synthesizer Agent (like Project 2's Synthesizer)

- Add `src/agents/memory_synthesizer_agent/` analogous to your existing `news_synthesizer_agent/`
- `synthesize_memory(history: list[dict]) -> str` — calls GPT to compress prior turns into a concise paragraph of "what the user cares about and what we've discussed"
- Called by the orchestrator whenever history length > 5 turns, replacing older raw messages with the summary
- This is the key differentiator Project 2 had — summarized memory used as context in every new turn

## Step 3 — Wire Up LangGraph in Production

- `src/workflow/orchestrator.py` already builds a `StateGraph` — `AgentOrchestrator.run()` is never called by the server
- Update `src/web_app/server.py` `POST /ask` to call `orchestrator.run()` instead of `process_query()`
- Extend `WorkflowState` in `src/core/protocol.py` to carry `session_id` and `history`
- Pass history into the `router` node so it becomes part of routing context

## Step 4 — LLM-Based Routing (replace ROUTING_TABLE)

- Update `src/core/router.py` `route_query()` to make a lightweight GPT call (use `gpt-4.1-mini` for cost) with a structured output schema: `{"agent": "<agent_name>", "confidence": 0.0–1.0}`
- System prompt lists the 6 agents + their descriptions; user message is the query + last 2 turns of history
- Fall back to keyword matching if LLM call fails (keep existing ROUTING_TABLE as fallback)
- This is the biggest single thing that makes routing "agentic"

## Step 5 — Real Tool Calling via `@tool` + `create_react_agent` (reference: `finance_agent-main`)

The reference project (`finance_agent-main`) proves the pattern: each specialist agent is created with `create_react_agent(model, tools=STOCK_TOOLS, prompt=SYSTEM_PROMPT)` from `langgraph.prebuilt` — a built-in ReAct loop where the LLM decides when to call each tool, inspects results, and loops until it has enough data to answer. Replace your current prompt-stuffing approach across all agents.

**`src/tools/stock_tools.py`** — new file, `@tool` decorated `yfinance` wrappers (no API key needed):
- `get_stock_quote(ticker)` → price, change %, market cap, P/E, 52-week range, volume
- `get_stock_history(ticker, period)` → OHLCV summary, total return %, annualised volatility
- `get_stock_financials(ticker)` → revenue, margins, EPS, debt/equity, ROE, analyst target/recommendation

**`src/tools/portfolio_tools.py`** — new file:
- `analyze_portfolio(holdings_json)` → current value, allocation %, cost basis, P&L per position
- `get_portfolio_performance(holdings_json, period)` → portfolio return % vs SPY (alpha)

**`src/tools/market_tools.py`** — new file:
- `get_market_overview()` → SPY, QQQ, DIA, IWM, VIX, 10-yr yield, GLD, USO
- `get_sector_performance(period)` → all 11 SPDR sector ETFs sorted by return

**`src/tools/tax_tools.py`** — new file:
- `calculate_capital_gains(ticker, shares, avg_cost, holding_period_days)` → short/long-term tax estimate using live price
- `find_tax_loss_opportunities(holdings_json)` → positions with unrealised losses, total harvestable, wash-sale note

**Export collections** at the bottom of each file (mirrors reference project pattern):
```python
STOCK_TOOLS     = [get_stock_quote, get_stock_history, get_stock_financials]
PORTFOLIO_TOOLS = [analyze_portfolio, get_portfolio_performance, get_stock_quote]
MARKET_TOOLS    = [get_market_overview, get_sector_performance, get_stock_history]
TAX_TOOLS       = [calculate_capital_gains, find_tax_loss_opportunities]
```

## Step 5a — Stock Agent (new agent, `create_react_agent` pattern)

- Add `src/agents/stock_agent/` — new specialist for individual stock lookups, fundamentals, and technicals
- `stock_agent.py`:
  ```python
  from langgraph.prebuilt import create_react_agent
  from src.tools.stock_tools import STOCK_TOOLS

  def create_stock_agent(llm):
      return create_react_agent(
          model=llm,
          tools=STOCK_TOOLS,
          prompt=SYSTEM_PROMPT,   # expert equity analyst persona
          name="stock_agent",
      )
  ```
- This is a true ReAct loop: LLM calls `get_stock_quote`, reads the JSON result, may then call `get_stock_financials` for deeper analysis, then writes a final answer — all within a single agent invocation
- Add LLM-based routing trigger: `"stock_agent"` for queries like "What is AAPL trading at?", "Compare NVDA vs AMD", "Is TSLA overvalued?"
- Rewrite all other specialist agents (`portfolio_agent`, `market_agent`, `tax_education_agent`) to use the same `create_react_agent` pattern with their respective tool collections from Step 5

## Step 5b — `MemorySaver` Checkpointer (LangGraph-level persistence)

- The reference project uses `MemorySaver` from `langgraph.checkpoint.memory` as a checkpointer on the `StateGraph` — this gives free in-process turn-by-turn memory without SQLite for the LangGraph state machine
- Add to `AgentOrchestrator` in `src/workflow/orchestrator.py`:
  ```python
  from langgraph.checkpoint.memory import MemorySaver
  checkpointer = MemorySaver()
  self.app = self.graph.compile(checkpointer=checkpointer)
  ```
- Pass `config={"configurable": {"thread_id": session_id}}` on every `.invoke()` call — LangGraph automatically replays the conversation from the checkpoint
- `MemorySaver` handles in-session memory; SQLite from Step 1 handles cross-session persistence (they complement each other)
- Supervisor node reads `state["conversation_history"]` and injects the last 6 turns into every downstream agent prompt using `_format_history()` helper (reference: `finance_agent-main/graph/orchestrator.py`)

## Step 6 — Multi-Agent Handoff via LangGraph Edges

- Currently `_after_execution_decision()` in `src/workflow/orchestrator.py` always returns `"end"` — `{"next_agent": "..."}` is never set
- Have portfolio agent emit `{"next_agent": "market_analysis_agent"}` to pull fresh prices when no real-time data is found
- Have tax agent emit `{"next_agent": "finance_qa_agent"}` for follow-up conceptual questions
- This creates true multi-agent collaboration visible in LangSmith traces

## Step 7 — Carry History into Agent Prompts

- Update each agent's system prompt (in `prompts.py` files across all agents) to accept an optional `memory_summary: str` parameter
- When the synthesizer summary exists, prepend it: `"Previous context: {memory_summary}\n\nUser now asks: {question}"`
- This is what enables the FinBrief "Does it apply to ETFs?" behavior — the wash sale rule answer is in the summary

## Step 8 — Expose Session Management in the API

- Add `session_id` field to the `/ask` request body (optional, auto-generated UUID if absent)
- Return `session_id` in every response so the frontend can maintain continuity
- Add `GET /history/{session_id}` endpoint to retrieve past turns
- Update `src/web_app/frontend/src/lib/storage.ts` and `api.ts` to persist and send `session_id`

---

## Verification Checklist

- [ ] Multi-turn test: ask "What is the wash sale rule?" then "Does it apply to ETFs?" — second answer must reference first without repeating
- [ ] LangSmith trace shows: `router (LLM)` → `execute_agent` → optional `next_agent` edge → `finalize`
- [ ] Run `tests/test_finance_agent.py` and new `tests/test_memory.py` to confirm session persistence
- [ ] Routing decisions change when keyword is absent but context implies the right agent
- [ ] Stock Agent ReAct trace shows at least one `tool_call` → `tool_result` → `final_answer` cycle (visible in LangSmith)
- [ ] `get_stock_quote('AAPL')` returns live price + P/E without Tavily or any API key
- [ ] Portfolio analysis calls `analyze_portfolio` tool with JSON holdings and returns current values + SPY alpha
- [ ] Tax agent calls `calculate_capital_gains` with live price fetched via `yfinance` (not hard-coded 2025 rates)

---

## Decisions

- Use SQLite (not Redis) for cross-session memory — matches FinBrief, no extra infra dependency
- `MemorySaver` for in-session LangGraph checkpointing — free, zero config, matches `finance_agent-main`
- LLM routing uses `gpt-4.1-mini` not full `gpt-4.1` to keep latency/cost low
- Pinecone stays for RAG (equivalent to FAISS, already working — no change needed)
- Wire LangGraph into the actual HTTP path rather than maintaining the parallel `process_query()` function
- Use `yfinance` (no API key) for all stock/market/portfolio/tax data — matches `finance_agent-main`; replace Tavily for real-time price lookups (Tavily stays for news/web search only)
- Convert all agents to `create_react_agent` from `langgraph.prebuilt` — eliminates bespoke `_execute()` overrides and gives a proper multi-step tool loop for free
- Add `stock_agent` as a 7th specialist agent — completes the coverage gap vs. reference projects that had explicit stock price/history/financials capability

## Reference Projects Map

| What to copy | Source file | Target file in your project |
|---|---|---|
| `@tool` yfinance wrappers | `finance_agent-main/tools/financial_data.py` | `src/tools/stock_tools.py`, `portfolio_tools.py`, `market_tools.py`, `tax_tools.py` |
| `create_react_agent` agent factory | `finance_agent-main/agents/stock_agent.py` | `src/agents/stock_agent/stock_agent.py` (and refactor all others) |
| `MemorySaver` + `conversation_history` | `finance_agent-main/graph/orchestrator.py` | `src/workflow/orchestrator.py` |
| `_format_history()` helper | `finance_agent-main/graph/orchestrator.py` L57–73 | `src/workflow/orchestrator.py` |
| Supervisor `StateGraph` with 7 agents | `finance_agent-main/graph/orchestrator.py` | `src/workflow/orchestrator.py` |
| `@tool` news tools (RSS + yfinance news) | `finance_agent-main/tools/news_tools.py` | `src/tools/news_tools.py` |
