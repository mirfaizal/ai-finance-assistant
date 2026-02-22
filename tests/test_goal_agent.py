"""Unit tests for the Goal Planning Agent."""

import pytest
from unittest.mock import patch, MagicMock


def _mock_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


_SAMPLE_GOALS = {
    "question": "How should I prioritise saving for retirement and an emergency fund?",
    "goals": [
        {"name": "Emergency fund", "timeline": "1 year", "amount": 15000},
        {"name": "Retirement", "timeline": "30 years"},
        {"name": "Home down payment", "timeline": "5 years", "amount": 60000},
    ],
    "income": "$90,000/year",
    "current_savings": "$5,000",
    "time_horizon": "30 years",
}


class TestPlanGoals:

    @patch("src.agents.goal_planning_agent.goal_agent.get_client")
    def test_returns_non_empty_string(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "Start with an emergency fund of 3–6 months of expenses..."
        )
        from src.agents.goal_planning_agent.goal_agent import plan_goals

        result = plan_goals(_SAMPLE_GOALS)
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.goal_planning_agent.goal_agent.get_client")
    def test_handles_empty_dict(self, mock_get_client):
        """An empty goals dict should return a general educational overview."""
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "Here is a general guide to financial goal setting..."
        )
        from src.agents.goal_planning_agent.goal_agent import plan_goals

        result = plan_goals({})
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.goal_planning_agent.goal_agent.get_client")
    def test_handles_question_only(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response(
            "The 50/30/20 rule is a popular budgeting framework..."
        )
        from src.agents.goal_planning_agent.goal_agent import plan_goals

        result = plan_goals({"question": "What is the 50/30/20 budgeting rule?"})
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @patch("src.agents.goal_planning_agent.goal_agent.get_client")
    def test_system_prompt_included(self, mock_get_client):
        mock_get_client.return_value.chat.completions.create.return_value = _mock_response("Answer.")
        from src.agents.goal_planning_agent.goal_agent import plan_goals

        plan_goals(_SAMPLE_GOALS)
        call_kwargs = mock_get_client.return_value.chat.completions.create.call_args.kwargs
        system_msgs = [m for m in call_kwargs["messages"] if m["role"] == "system"]
        assert len(system_msgs) >= 1

    def test_raises_on_non_dict_input(self):
        from src.agents.goal_planning_agent.goal_agent import plan_goals

        with pytest.raises(TypeError):
            plan_goals("save more money")  # type: ignore[arg-type]

        with pytest.raises(TypeError):
            plan_goals(None)  # type: ignore[arg-type]
