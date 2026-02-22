"""
Stock Analysis Agent — uses a true ReAct loop via LangGraph's create_react_agent.

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
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage

from src.tools.stock_tools import STOCK_TOOLS
from src.utils.logging import get_logger
from src.utils.tracing import traceable
from .prompts import SYSTEM_PROMPT

logger = get_logger(__name__)

# ── LLM factory ───────────────────────────────────────────────────────────────

def _get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI instance configured from environment."""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def create_stock_agent(llm=None):
    """
    Build and return a LangGraph ReAct agent for stock analysis.

    The returned object is a compiled LangGraph app with a .invoke() method.
    You usually don't need to call this directly — use ask_stock_agent() instead.
    """
    model = llm or _get_llm()
    return create_react_agent(
        model=model,
        tools=STOCK_TOOLS,
        prompt=SYSTEM_PROMPT,
        name="stock_agent",
    )


# Module-level singleton (created lazily on first call)
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = create_stock_agent()
    return _agent


def _format_history(history: List[Dict[str, str]]) -> str:
    """Format prior turns for injection into the user message."""
    if not history:
        return ""
    lines = ["\n\n### Conversation history:"]
    for entry in history[-6:]:  # last 3 turns (6 messages)
        role  = "User" if entry.get("role") == "user" else "Assistant"
        text  = entry.get("content", "")
        if entry.get("role") == "assistant" and len(text) > 400:
            text = text[:400] + "… [truncated]"
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


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

    agent = _get_agent()
    result = agent.invoke(
        {"messages": [HumanMessage(content=user_content)]},
        config={"recursion_limit": 10},
    )

    # Extract the final text response
    messages = result.get("messages", [])
    for msg in reversed(messages):
        content = getattr(msg, "content", None)
        if content and isinstance(content, str) and not getattr(msg, "tool_calls", None):
            return content.strip()

    return "I was unable to retrieve stock data at this time. Please try again."
