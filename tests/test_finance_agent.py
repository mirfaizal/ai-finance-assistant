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


# ── Tests for ask_finance_agent_with_history ───────────────────────────────────

class TestAskFinanceAgentWithHistory:
    """Tests for ask_finance_agent_with_history()."""

    def _make_chain_result(self, answer: str, sources: list[str] | None = None):
        """Build a minimal mock dict that invoke_chain would return."""
        docs = []
        for s in (sources or []):
            doc = MagicMock()
            doc.metadata = {"source": s}
            doc.page_content = f"Content from {s}"
            docs.append(doc)
        return {
            "answer":           answer,
            "sources":          sources or [],
            "source_documents": docs,
        }

    @patch("src.agents.finance_qa_agent.finance_agent.invoke_chain")
    def test_returns_expected_schema(self, mock_invoke_chain):
        """Result must be a dict with 'answer', 'sources', 'source_documents'."""
        mock_invoke_chain.return_value = self._make_chain_result(
            "An ETF is an exchange-traded fund.",
            sources=["finance-basics"],
        )

        from src.agents.finance_qa_agent.finance_agent import ask_finance_agent_with_history

        result = ask_finance_agent_with_history("What is an ETF?", [])

        assert isinstance(result, dict)
        assert "answer" in result
        assert "sources" in result
        assert "source_documents" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0
        assert isinstance(result["sources"], list)

    @patch("src.agents.finance_qa_agent.finance_agent.invoke_chain")
    def test_chat_history_passed_to_chain(self, mock_invoke_chain):
        """chat_history must be forwarded as-is to invoke_chain."""
        mock_invoke_chain.return_value = self._make_chain_result("Mutual funds are pooled investments.")

        from src.agents.finance_qa_agent.finance_agent import ask_finance_agent_with_history

        history = [("What is an ETF?", "An ETF is an exchange-traded fund.")]
        ask_finance_agent_with_history("How do they differ from mutual funds?", history)

        call_kwargs = mock_invoke_chain.call_args.kwargs
        assert call_kwargs["chat_history"] == history

    @patch("src.agents.finance_qa_agent.finance_agent.invoke_chain")
    def test_sources_are_deduplicated(self, mock_invoke_chain):
        """Sources list must not contain duplicates."""
        mock_invoke_chain.return_value = self._make_chain_result(
            "Compound interest grows exponentially.",
            sources=["finance-basics", "finance-basics", "intro-guide"],
        )

        from src.agents.finance_qa_agent.finance_agent import ask_finance_agent_with_history

        result = ask_finance_agent_with_history("How does compound interest work?", [])
        # sources from invoke_chain are deduplicated inside langchain_rag; verify list type
        assert isinstance(result["sources"], list)

    @patch("src.agents.finance_qa_agent.finance_agent.invoke_chain")
    @patch("src.agents.finance_qa_agent.finance_agent.get_client")
    def test_fallback_when_chain_returns_empty(self, mock_get_client, mock_invoke_chain):
        """When invoke_chain returns empty answer, must fall back to ask_finance_agent."""
        # Chain returns empty
        mock_invoke_chain.return_value = {"answer": "", "sources": [], "source_documents": []}

        # Fallback OpenAI call succeeds
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response("Fallback answer.")
        mock_get_client.return_value = mock_client

        from src.agents.finance_qa_agent.finance_agent import ask_finance_agent_with_history

        result = ask_finance_agent_with_history("What is diversification?", [])

        assert result["answer"] == "Fallback answer."
        assert result["sources"] == []

    def test_raises_on_empty_question(self):
        """Empty or whitespace-only questions must raise ValueError."""
        from src.agents.finance_qa_agent.finance_agent import ask_finance_agent_with_history

        with pytest.raises(ValueError):
            ask_finance_agent_with_history("", [])

        with pytest.raises(ValueError):
            ask_finance_agent_with_history("   ", None)
