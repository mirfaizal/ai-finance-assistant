"""Unit tests for the Portfolio Analysis Agent."""

import pytest
from unittest.mock import patch, MagicMock


# ── Helpers ────────────────────────────────────────────────────────────────────

_SAMPLE_PORTFOLIO = {
    "assets": [
        {"symbol": "AAPL", "allocation": 0.25},
        {"symbol": "VTI",  "allocation": 0.40},
        {"symbol": "BND",  "allocation": 0.35},
    ]
}

_PARTIAL_PORTFOLIO = {
    "assets": [
        {"symbol": "AAPL"},                          # missing allocation
        {"symbol": "VTI", "allocation": "invalid"},  # bad allocation value
        {"allocation": 0.20},                        # missing symbol
    ]
}

_EMPTY_PORTFOLIO: dict = {"assets": []}
_NO_ASSETS_KEY: dict = {}


def _make_mock_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestAnalyzePortfolio:
    """Tests for analyze_portfolio()."""

    @patch("src.agents.portfolio_analysis_agent.portfolio_agent.get_client")
    def test_returns_non_empty_string(self, mock_get_client):
        """analyze_portfolio must return a non-empty string for a valid portfolio."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response(
            "This portfolio is well-diversified across equities and fixed income."
        )
        mock_get_client.return_value = mock_client

        from src.agents.portfolio_analysis_agent.portfolio_agent import analyze_portfolio

        result = analyze_portfolio(_SAMPLE_PORTFOLIO)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.portfolio_analysis_agent.portfolio_agent.get_client")
    def test_passes_symbols_to_prompt(self, mock_get_client):
        """Asset symbols must appear in the user message sent to the API."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response("Analysis.")
        mock_get_client.return_value = mock_client

        from src.agents.portfolio_analysis_agent.portfolio_agent import analyze_portfolio

        analyze_portfolio(_SAMPLE_PORTFOLIO)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        user_content = next(
            m["content"] for m in call_kwargs["messages"] if m["role"] == "user"
        )
        assert "AAPL" in user_content
        assert "VTI" in user_content
        assert "BND" in user_content

    @patch("src.agents.portfolio_analysis_agent.portfolio_agent.get_client")
    def test_system_prompt_included(self, mock_get_client):
        """A system prompt must be included in the API call."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response("Analysis.")
        mock_get_client.return_value = mock_client

        from src.agents.portfolio_analysis_agent.portfolio_agent import analyze_portfolio

        analyze_portfolio(_SAMPLE_PORTFOLIO)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        system_msgs = [m for m in call_kwargs["messages"] if m["role"] == "system"]
        assert len(system_msgs) >= 1

    @patch("src.agents.portfolio_analysis_agent.portfolio_agent.get_client")
    def test_handles_empty_assets_list(self, mock_get_client):
        """An empty assets list should not raise — agent should respond gracefully."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response(
            "No assets found. Here is general guidance on building a portfolio..."
        )
        mock_get_client.return_value = mock_client

        from src.agents.portfolio_analysis_agent.portfolio_agent import analyze_portfolio

        result = analyze_portfolio(_EMPTY_PORTFOLIO)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.portfolio_analysis_agent.portfolio_agent.get_client")
    def test_handles_missing_assets_key(self, mock_get_client):
        """A portfolio dict with no 'assets' key must not raise."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response(
            "No assets found."
        )
        mock_get_client.return_value = mock_client

        from src.agents.portfolio_analysis_agent.portfolio_agent import analyze_portfolio

        result = analyze_portfolio(_NO_ASSETS_KEY)
        assert isinstance(result, str)

    @patch("src.agents.portfolio_analysis_agent.portfolio_agent.get_client")
    def test_handles_partial_data(self, mock_get_client):
        """Partial / malformed asset entries must not raise an exception."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_response(
            "Partial portfolio analysis..."
        )
        mock_get_client.return_value = mock_client

        from src.agents.portfolio_analysis_agent.portfolio_agent import analyze_portfolio

        result = analyze_portfolio(_PARTIAL_PORTFOLIO)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_raises_on_non_dict_input(self):
        """Passing a non-dict must raise TypeError."""
        from src.agents.portfolio_analysis_agent.portfolio_agent import analyze_portfolio

        with pytest.raises(TypeError):
            analyze_portfolio("AAPL 50%, VTI 50%")  # type: ignore[arg-type]

        with pytest.raises(TypeError):
            analyze_portfolio(None)  # type: ignore[arg-type]
