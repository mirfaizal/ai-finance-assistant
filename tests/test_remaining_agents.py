"""Unit tests for ask_stock_agent, ask_trading_agent, and synthesize_memory"""
from __future__ import annotations
from unittest.mock import patch, MagicMock

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Stock Agent
# ══════════════════════════════════════════════════════════════════════════════

def _make_ai_response(content: str, tool_calls=None) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    return msg


class TestAskStockAgent:

    @patch("src.agents.stock_agent.stock_agent._get_llm")
    def test_returns_string(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = _make_ai_response(
            "AAPL is trading at $150 with a P/E of 28.", []
        )
        mock_get_llm.return_value = mock_llm

        from src.agents.stock_agent.stock_agent import ask_stock_agent
        result = ask_stock_agent("What is AAPL stock price?")
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.stock_agent.stock_agent._get_llm")
    def test_raises_on_empty_question(self, mock_get_llm):
        from src.agents.stock_agent.stock_agent import ask_stock_agent
        with pytest.raises(ValueError):
            ask_stock_agent("")
        with pytest.raises(ValueError):
            ask_stock_agent("   ")

    @patch("src.agents.stock_agent.stock_agent._get_llm")
    def test_with_history(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = _make_ai_response(
            "NVDA is up 5% today.", []
        )
        mock_get_llm.return_value = mock_llm

        history = [
            {"role": "user", "content": "Tell me about stocks"},
            {"role": "assistant", "content": "I can help with that."},
        ]
        from src.agents.stock_agent.stock_agent import ask_stock_agent
        result = ask_stock_agent("What about NVDA?", history=history)
        assert isinstance(result, str)

    @patch("src.agents.stock_agent.stock_agent._get_llm")
    def test_with_memory_summary(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = _make_ai_response(
            "Based on our previous chat, TSLA is volatile.", []
        )
        mock_get_llm.return_value = mock_llm

        from src.agents.stock_agent.stock_agent import ask_stock_agent
        result = ask_stock_agent(
            "What about TSLA?",
            memory_summary="User discussed Tesla and market volatility."
        )
        assert isinstance(result, str)

    @patch("src.agents.stock_agent.stock_agent._get_llm")
    def test_tool_call_loop(self, mock_get_llm):
        """Test ReAct loop: first call has tool calls, second call is final."""
        from langchain_core.messages import ToolMessage

        tool_call_response = MagicMock()
        tool_call_response.content = ""
        tool_call_response.tool_calls = [
            {"name": "get_stock_quote", "args": {"ticker": "AAPL"}, "id": "tc-1"}
        ]

        final_response = _make_ai_response("AAPL is at $150.", [])

        mock_llm_bound = MagicMock()
        mock_llm_bound.invoke.side_effect = [tool_call_response, final_response]
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm_bound
        mock_get_llm.return_value = mock_llm

        with patch("src.agents.stock_agent.stock_agent.STOCK_TOOLS") as mock_tools:
            mock_tool = MagicMock()
            mock_tool.name = "get_stock_quote"
            mock_tool.invoke.return_value = '{"ticker": "AAPL", "price": 150.0}'
            mock_tools.__iter__ = MagicMock(return_value=iter([mock_tool]))
            mock_tools.__len__ = MagicMock(return_value=1)

            from src.agents.stock_agent.stock_agent import ask_stock_agent
            result = ask_stock_agent("What is AAPL price?")
            assert isinstance(result, str)


# ══════════════════════════════════════════════════════════════════════════════
# Trading Agent
# ══════════════════════════════════════════════════════════════════════════════

class TestAskTradingAgent:

    @patch("src.agents.trading_agent.trading_agent._get_llm")
    @patch("src.agents.trading_agent.trading_agent.make_trading_tools")
    def test_returns_string(self, mock_make_tools, mock_get_llm):
        mock_tool = MagicMock()
        mock_tool.name = "view_holdings"
        mock_make_tools.return_value = [mock_tool]

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = _make_ai_response(
            "You have 10 AAPL shares.", []
        )
        mock_get_llm.return_value = mock_llm

        from src.agents.trading_agent.trading_agent import ask_trading_agent
        result = ask_trading_agent("show my holdings", session_id="sess-1")
        assert isinstance(result, str)

    @patch("src.agents.trading_agent.trading_agent._get_llm")
    @patch("src.agents.trading_agent.trading_agent.make_trading_tools")
    def test_with_history_and_memory(self, mock_make_tools, mock_get_llm):
        mock_make_tools.return_value = []
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value.invoke.return_value = _make_ai_response("Done.", [])
        mock_get_llm.return_value = mock_llm

        from src.agents.trading_agent.trading_agent import ask_trading_agent
        result = ask_trading_agent(
            "buy 5 AAPL",
            session_id="sess-2",
            history=[{"role": "user", "content": "hi"}],
            memory_summary="User is a beginner investor.",
        )
        assert isinstance(result, str)

    @patch("src.agents.trading_agent.trading_agent._get_llm")
    @patch("src.agents.trading_agent.trading_agent.make_trading_tools")
    def test_handles_llm_exception(self, mock_make_tools, mock_get_llm):
        mock_make_tools.return_value = []
        mock_get_llm.side_effect = Exception("LLM unavailable")

        from src.agents.trading_agent.trading_agent import ask_trading_agent
        result = ask_trading_agent("buy 5 AAPL", session_id="sess-3")
        assert isinstance(result, str)
        # Should return an error message, not raise
        assert "error" in result.lower() or len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Memory Synthesizer Agent
# ══════════════════════════════════════════════════════════════════════════════

def _mock_openai_response(content: str) -> MagicMock:
    m = MagicMock()
    m.choices[0].message.content = content
    return m


class TestSynthesizeMemory:

    @patch("src.agents.memory_synthesizer_agent.memory_agent.get_client")
    def test_returns_string(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = (
            _mock_openai_response("Summary: user asked about stocks and bonds.")
        )
        from src.agents.memory_synthesizer_agent.memory_agent import synthesize_memory
        history = [
            {"role": "user", "content": "What are stocks?"},
            {"role": "assistant", "content": "Stocks are equity instruments."},
            {"role": "user", "content": "What about bonds?"},
            {"role": "assistant", "content": "Bonds are debt instruments."},
        ]
        result = synthesize_memory(history)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.memory_synthesizer_agent.memory_agent.get_client")
    def test_handles_empty_history(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = (
            _mock_openai_response("No prior conversation.")
        )
        from src.agents.memory_synthesizer_agent.memory_agent import synthesize_memory
        result = synthesize_memory([])
        assert isinstance(result, str)

    @patch("src.agents.memory_synthesizer_agent.memory_agent.get_client")
    def test_includes_summary_role_messages(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = (
            _mock_openai_response("Compressed.")
        )
        from src.agents.memory_synthesizer_agent.memory_agent import synthesize_memory
        history = [
            {"role": "summary", "content": "User discussed inflation earlier."},
            {"role": "user", "content": "What about interest rates?"},
            {"role": "assistant", "content": "Rates affect bonds."},
        ]
        result = synthesize_memory(history)
        assert isinstance(result, str)

    @patch("src.agents.memory_synthesizer_agent.memory_agent.get_client")
    def test_system_prompt_sent(self, mock_get_client):
        mock_client = mock_get_client.return_value
        mock_client.chat.completions.create.return_value = (
            _mock_openai_response("Done.")
        )
        from src.agents.memory_synthesizer_agent.memory_agent import synthesize_memory
        # Need >= 2 history items so the LLM call is actually made
        history = [
            {"role": "user", "content": "What are stocks?"},
            {"role": "assistant", "content": "Stocks are equity instruments."},
        ]
        synthesize_memory(history)
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        system_msgs = [m for m in call_kwargs["messages"] if m["role"] == "system"]
        assert len(system_msgs) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# Agent client factories
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentClientFactories:

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "gpt-4.1"})
    def test_memory_agent_get_client(self):
        from src.agents.memory_synthesizer_agent.client import get_client
        client = get_client()
        assert client is not None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_finance_agent_get_client(self):
        from src.agents.finance_qa_agent.client import get_client
        client = get_client()
        assert client is not None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_goal_agent_get_client(self):
        from src.agents.goal_planning_agent.client import get_client
        client = get_client()
        assert client is not None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_market_agent_get_client(self):
        from src.agents.market_analysis_agent.client import get_client
        client = get_client()
        assert client is not None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_news_agent_get_client(self):
        from src.agents.news_synthesizer_agent.client import get_client
        client = get_client()
        assert client is not None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_portfolio_agent_get_client(self):
        from src.agents.portfolio_analysis_agent.client import get_client
        client = get_client()
        assert client is not None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_tax_agent_get_client(self):
        from src.agents.tax_education_agent.client import get_client
        client = get_client()
        assert client is not None
