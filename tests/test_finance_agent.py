"""Unit tests for the Finance Q&A Agent."""

import pytest
from unittest.mock import patch, MagicMock


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_mock_response(content: str) -> MagicMock:
    """Build a minimal mock that looks like an OpenAI ChatCompletion response."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = content
    return mock_response


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestAskFinanceAgent:
    """Tests for ask_finance_agent()."""

    @patch("src.agents.finance_qa_agent.finance_agent.get_client")
    def test_returns_non_empty_string(self, mock_get_client):
        """Agent must return a non-empty string for a valid question."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response(
            "Compound interest is interest earned on both the principal and previously accumulated interest."
        )
        mock_get_client.return_value = mock_client

        from src.agents.finance_qa_agent.finance_agent import ask_finance_agent

        answer = ask_finance_agent("What is compound interest?")
        assert isinstance(answer, str)
        assert len(answer.strip()) > 0

    @patch("src.agents.finance_qa_agent.finance_agent.get_client")
    def test_passes_question_to_api(self, mock_get_client):
        """The user's question must appear in the messages sent to the API."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response("Answer.")
        mock_get_client.return_value = mock_client

        from src.agents.finance_qa_agent.finance_agent import ask_finance_agent

        ask_finance_agent("What is an ETF?")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        user_messages = [m for m in messages if m["role"] == "user"]
        assert any("ETF" in m["content"] for m in user_messages)

    @patch("src.agents.finance_qa_agent.finance_agent.get_client")
    def test_system_prompt_included(self, mock_get_client):
        """A system prompt must be included in the API call messages."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response("Answer.")
        mock_get_client.return_value = mock_client

        from src.agents.finance_qa_agent.finance_agent import ask_finance_agent

        ask_finance_agent("What is diversification?")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        system_messages = [m for m in messages if m["role"] == "system"]
        assert len(system_messages) >= 1

    def test_raises_on_empty_question(self):
        """Empty or whitespace-only questions must raise ValueError."""
        from src.agents.finance_qa_agent.finance_agent import ask_finance_agent

        with pytest.raises(ValueError):
            ask_finance_agent("")

        with pytest.raises(ValueError):
            ask_finance_agent("   ")
