"""Unit tests for the Market Analysis Agent."""

import pytest
from unittest.mock import patch, MagicMock


def _mock_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


_SAMPLE_DATA = {
    "question": "How is the tech sector performing?",
    "indices": [
        {"name": "S&P 500", "value": 5200, "change_pct": -0.5},
        {"name": "NASDAQ", "value": 18200, "change_pct": -1.1},
    ],
    "sectors": [
        {"name": "Technology", "change_pct": -1.3},
        {"name": "Energy", "change_pct": 0.8},
    ],
    "macro": {"inflation": "3.1%", "fed_rate": "5.25%"},
}


class TestAnalyzeMarket:

    @patch("src.agents.market_analysis_agent.market_agent.get_client")
    def test_returns_non_empty_string(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "The tech sector is experiencing downward pressure due to rising rates."
        )
        from src.agents.market_analysis_agent.market_agent import analyze_market

        result = analyze_market(_SAMPLE_DATA)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.market_analysis_agent.market_agent.get_client")
    def test_handles_none_data(self, mock_get_client):
        """Passing None should trigger a general market overview without raising."""
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "General market overview..."
        )
        from src.agents.market_analysis_agent.market_agent import analyze_market

        result = analyze_market(None)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.market_analysis_agent.market_agent.get_client")
    def test_handles_empty_dict(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "No data provided..."
        )
        from src.agents.market_analysis_agent.market_agent import analyze_market

        result = analyze_market({})
        assert isinstance(result, str)

    @patch("src.agents.market_analysis_agent.market_agent.get_client")
    def test_handles_partial_data(self, mock_get_client):
        """Only a question key — no indices/sectors/macro — should still work."""
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "Partial market analysis..."
        )
        from src.agents.market_analysis_agent.market_agent import analyze_market

        result = analyze_market({"question": "What drives market volatility?"})
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.market_analysis_agent.market_agent.get_client")
    def test_system_prompt_included(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response("Answer.")
        from src.agents.market_analysis_agent.market_agent import analyze_market

        analyze_market(_SAMPLE_DATA)
        call_kwargs = mock_get_client.return_value.chat.completions.create.call_args.kwargs
        system_msgs = [m for m in call_kwargs["messages"] if m["role"] == "system"]
        assert len(system_msgs) >= 1

    def test_raises_on_non_dict_non_none_input(self):
        from src.agents.market_analysis_agent.market_agent import analyze_market

        with pytest.raises(TypeError):
            analyze_market("S&P 500 is down")  # type: ignore[arg-type]
