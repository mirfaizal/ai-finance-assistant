"""
Trading Agent -- paper-trading via buy/sell/hold tools backed by SQLite.

LangGraph 1.x compatible: uses ChatOpenAI.bind_tools() + a manual ReAct
tool loop.  langgraph.prebuilt.create_react_agent is NOT available in
LangGraph 1.0.5, so we drive the tool-calling loop manually.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI

from src.tools.stock_tools import get_stock_quote
from src.tools.trading_tools import make_trading_tools
from src.utils.logging import get_logger
from src.utils.tracing import traceable
from .prompts import SYSTEM_PROMPT

logger = get_logger(__name__)

_MAX_TOOL_ITERATIONS = 8


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _format_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return ""
    lines = ["\n\n### Conversation history:"]
    for entry in history[-6:]:
        role = "User" if entry.get("role") == "user" else "Assistant"
        text = entry.get("content", "")
        if entry.get("role") == "assistant" and len(text) > 300:
            text = text[:300] + "... [truncated]"
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


def _run_react_loop(llm: ChatOpenAI, tools: list, messages: list) -> str:
    """Drive a tool-calling loop using ChatOpenAI.bind_tools() directly."""
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
            except Exception as exc:
                result = f"Tool error ({name}): {exc}"
            msgs.append(ToolMessage(content=str(result), tool_call_id=call_id))

    for msg in reversed(msgs):
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
            return str(msg.content)
    return "Trade action completed."


@traceable(name="trading_agent", run_type="chain", tags=["trading"])
def ask_trading_agent(
    question: str,
    session_id: str,
    history: Optional[List[Dict]] = None,
    memory_summary: Optional[str] = None,
) -> str:
    """Execute a paper-trading action (buy / sell / view) via a ReAct tool loop."""
    session_tools = make_trading_tools(session_id) + [get_stock_quote]

    user_text = question
    if memory_summary:
        user_text = f"Previous context: {memory_summary}\n\n{user_text}"
    hist = _format_history(history or [])
    if hist:
        user_text = f"{hist}\n\n{user_text}"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_text),
    ]

    try:
        return _run_react_loop(_get_llm(), session_tools, messages)
    except Exception as exc:
        logger.error("Trading agent error: %s", exc, exc_info=True)
        return f"I encountered an error while processing your trade: {exc}"
