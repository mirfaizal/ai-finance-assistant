"""Unit tests for the Tax Education Agent."""

import pytest
from unittest.mock import patch, MagicMock


def _mock_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


class TestExplainTaxConcepts:

    @patch("src.agents.tax_education_agent.tax_agent.get_client")
    def test_returns_non_empty_string(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "A tax deduction reduces your taxable income, while a tax credit "
            "reduces your tax bill directly..."
        )
        from src.agents.tax_education_agent.tax_agent import explain_tax_concepts

        result = explain_tax_concepts("What is the difference between a deduction and a credit?")
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.tax_education_agent.tax_agent.get_client")
    def test_query_appears_in_user_message(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response("Answer.")
        from src.agents.tax_education_agent.tax_agent import explain_tax_concepts

        explain_tax_concepts("Explain capital gains tax.")
        call_kwargs = mock_get_client.return_value.chat.completions.create.call_args.kwargs
        user_msgs = [m for m in call_kwargs["messages"] if m["role"] == "user"]
        assert any("capital gains" in m["content"].lower() for m in user_msgs)

    @patch("src.agents.tax_education_agent.tax_agent.get_client")
    def test_system_prompt_included(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response("Answer.")
        from src.agents.tax_education_agent.tax_agent import explain_tax_concepts

        explain_tax_concepts("What are tax brackets?")
        call_kwargs = mock_get_client.return_value.chat.completions.create.call_args.kwargs
        system_msgs = [m for m in call_kwargs["messages"] if m["role"] == "system"]
        assert len(system_msgs) >= 1

    @patch("src.agents.tax_education_agent.tax_agent.get_client")
    def test_handles_roth_vs_traditional_query(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "Roth IRA contributions are made with after-tax dollars..."
        )
        from src.agents.tax_education_agent.tax_agent import explain_tax_concepts

        result = explain_tax_concepts(
            "What is the tax treatment difference between a Roth IRA and a Traditional IRA?"
        )
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_raises_on_empty_query(self):
        from src.agents.tax_education_agent.tax_agent import explain_tax_concepts

        with pytest.raises(ValueError):
            explain_tax_concepts("")

        with pytest.raises(ValueError):
            explain_tax_concepts("   ")

    def test_raises_on_non_string_input(self):
        from src.agents.tax_education_agent.tax_agent import explain_tax_concepts

        with pytest.raises(TypeError):
            explain_tax_concepts(None)  # type: ignore[arg-type]

        with pytest.raises(TypeError):
            explain_tax_concepts(42)  # type: ignore[arg-type]
