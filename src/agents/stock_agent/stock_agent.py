"""
Stock Analysis Agent — uses a ReAct tool-calling loop backed by yfinance tools.

LangGraph 1.x compatible: uses ChatOpenAI.bind_tools() + a manual ReAct
tool loop.  langgraph.prebuilt.create_react_agent is NOT available in
LangGraph 1.0.5, so we drive the tool-calling loop manually.

The LLM decides when to call each yfinance tool, inspects the JSON result,
may call additional tools (e.g. get_stock_financials after get_stock_quote),
and only produces a final answer when it has enough data.

Usage (in orchestrator / process_query)
----------------------------------------
    answer = ask_stock_agent(question, history=history)

Usage (standalone / testing)
------------------------------
    from src.agents.stock_agent import ask_stock_agent
    print(ask_stock_agent("Is NVDA overvalued?"))
"""
from __future__ import annotations

import os
from typing import List, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.tools.stock_tools import STOCK_TOOLS
from src.utils.logging import get_logger
from src.utils.tracing import traceable
from .prompts import SYSTEM_PROMPT

logger = get_logger(__name__)

_MAX_TOOL_ITERATIONS = 8


# ── LLM factory ───────────────────────────────────────────────────────────────

def _get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI instance configured from environment."""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


# ── History formatter ─────────────────────────────────────────────────────────

def _format_history(history: List[Dict[str, str]]) -> str:
    """Format prior turns for injection into the user message."""
    if not history:
        return ""
    lines = ["\n\n### Conversation history:"]
    for entry in history[-6:]:  # last 3 turns (6 messages)
        role  = "User" if entry.get("role") == "user" else "Assistant"
        text  = entry.get("content", "")
        if entry.get("role") == "assistant" and len(text) > 400:
            text = text[:400] + "... [truncated]"
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


# ── Tool-calling ReAct loop ───────────────────────────────────────────────────

def _run_react_loop(llm: ChatOpenAI, tools: list, messages: list) -> str:
    """
    Drive a tool-calling loop until the LLM returns a final text answer.

    LangGraph 1.x removed create_react_agent from langgraph.prebuilt.
    This function replicates the same Thought -> Action -> Observation cycle
    using ChatOpenAI.bind_tools() directly.
    """
    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)
    msgs = list(messages)

    for _ in range(_MAX_TOOL_ITERATIONS):
        response: AIMessage = llm_with_tools.invoke(msgs)
        msgs.append(response)

        if not getattr(response, "tool_calls", None):
            return str(response.content)

        for tc in response.tool_calls:
            name = tc["name"]
            args = tc["args"]
            call_id = tc["id"]
            try:
                result = tool_map[name].invoke(args) if name in tool_map else f"Unknown tool: {name}"
            except Exception as exc:  # noqa: BLE001
                result = f"Tool error ({name}): {exc}"
            msgs.append(ToolMessage(content=str(result), tool_call_id=call_id))

    # Fallback: return last non-tool-call AI message
    for msg in reversed(msgs):
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
            return str(msg.content)
    return "I was unable to retrieve stock data at this time. Please try again."


@traceable(name="stock_agent", run_type="chain", tags=["stock", "react"])
def ask_stock_agent(
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
    memory_summary: Optional[str] = None,
) -> str:
    """
    Answer a stock-related question using a ReAct loop with live yfinance tools.

    The agent will call get_stock_quote, get_stock_history, and/or get_stock_financials
    as needed, inspect the JSON results, and produce a final answer.

    Parameters
    ----------
    question : str
        The user's question about a stock or stocks.
    history : list of {"role": str, "content": str}, optional
        Prior conversation turns for context.
    memory_summary : str, optional
        Compressed memory from the memory synthesizer agent.

    Returns
    -------
    str
        Plain-text answer from the agent.
    """
    if not question or not question.strip():
        raise ValueError("Question must be a non-empty string.")

    logger.info("Stock agent received question: %s", question[:80])

    # Build the enriched user message with prior context
    user_content = question.strip()
    if memory_summary:
        user_content = f"Previous context: {memory_summary}\n\nQuestion: {user_content}"
    if history:
        user_content += _format_history(history)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    return _run_react_loop(_get_llm(), STOCK_TOOLS, messages)
