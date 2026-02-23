"""Unit tests for src/workflow/orchestrator.py – process_query()"""
from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest


def _make_mock_response(content: str) -> MagicMock:
    m = MagicMock()
    m.choices[0].message.content = content
    return m


# ═══════════════════════════════════════════════════════════════════════════════
# process_query
# ═══════════════════════════════════════════════════════════════════════════════

class TestProcessQuery:

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.finance_qa_agent.finance_agent.ask_finance_agent")
    def test_returns_dict_with_answer(
        self, mock_agent, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_route.return_value = "finance_qa_agent"
        mock_agent.return_value = "Inflation is a rise in prices."

        from src.workflow.orchestrator import process_query
        result = process_query("What is inflation?")
        assert "answer" in result
        assert "agent" in result
        assert "session_id" in result

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.stock_agent.stock_agent.ask_stock_agent")
    def test_routes_to_stock_agent(
        self, mock_agent, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_route.return_value = "stock_agent"
        mock_agent.return_value = "AAPL is trading at $150."

        from src.workflow.orchestrator import process_query
        result = process_query("What is AAPL stock price?")
        assert result["agent"] == "stock_agent"
        assert "AAPL" in result["answer"]

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.market_analysis_agent.market_agent.analyze_market")
    def test_routes_to_market_agent(
        self, mock_agent, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_route.return_value = "market_analysis_agent"
        mock_agent.return_value = "Markets are down today."

        from src.workflow.orchestrator import process_query
        result = process_query("How is the market doing?")
        assert result["agent"] == "market_analysis_agent"

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.tax_education_agent.tax_agent.explain_tax_concepts")
    def test_routes_to_tax_agent(
        self, mock_agent, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_route.return_value = "tax_education_agent"
        mock_agent.return_value = "Capital gains are taxed based on holding period."

        from src.workflow.orchestrator import process_query
        result = process_query("What is capital gains tax?")
        assert result["agent"] == "tax_education_agent"

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.goal_planning_agent.goal_agent.plan_goals")
    def test_routes_to_goal_agent(
        self, mock_agent, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_route.return_value = "goal_planning_agent"
        mock_agent.return_value = "You should save 20% of your income."

        from src.workflow.orchestrator import process_query
        result = process_query("Help me plan for retirement")
        assert result["agent"] == "goal_planning_agent"

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.news_synthesizer_agent.news_agent.synthesize_news")
    def test_routes_to_news_agent(
        self, mock_agent, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_route.return_value = "news_synthesizer_agent"
        mock_agent.return_value = "Market news: Fed raises rates."

        from src.workflow.orchestrator import process_query
        result = process_query("What's the latest financial news?")
        assert result["agent"] == "news_synthesizer_agent"

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.trading_agent.trading_agent.ask_trading_agent")
    def test_routes_to_trading_agent(
        self, mock_agent, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_route.return_value = "trading_agent"
        mock_agent.return_value = "Bought 10 AAPL at $150."

        from src.workflow.orchestrator import process_query
        result = process_query("buy 10 AAPL", session_id="test-session")
        assert result["agent"] == "trading_agent"

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.portfolio_analysis_agent.portfolio_agent.analyze_portfolio")
    def test_routes_to_portfolio_agent(
        self, mock_agent, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_port_store = MagicMock()
        mock_port_store.get_holdings.return_value = []
        mock_ps_cls.return_value = mock_port_store
        mock_route.return_value = "portfolio_analysis_agent"
        mock_agent.return_value = "Your portfolio is well diversified."

        from src.workflow.orchestrator import process_query
        result = process_query("analyze my portfolio")
        assert result["agent"] == "portfolio_analysis_agent"

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.core.guards.check_ambiguous_yes_no_guard")
    @patch("src.agents.finance_qa_agent.finance_agent.ask_finance_agent")
    def test_guard_short_circuits(
        self, mock_agent, mock_guard, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_guard.return_value = "Please clarify your question."

        from src.workflow.orchestrator import process_query
        result = process_query("yes")
        assert result["agent"] == "guard"
        assert result["answer"] == "Please clarify your question."
        mock_route.assert_not_called()

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.memory_synthesizer_agent.memory_agent.synthesize_memory")
    @patch("src.agents.finance_qa_agent.finance_agent.ask_finance_agent")
    def test_memory_synthesis_triggered(
        self, mock_agent, mock_synth, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = [{"role": "user", "content": f"Q{i}"} for i in range(6)]
        mock_store.get_turn_count.return_value = 6  # >= _MEMORY_TRIGGER_TURNS
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_route.return_value = "finance_qa_agent"
        mock_synth.return_value = "Compressed summary."
        mock_agent.return_value = "Answer."

        from src.workflow.orchestrator import process_query
        result = process_query("new question", session_id="long-session")
        mock_synth.assert_called_once()

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.finance_qa_agent.finance_agent.ask_finance_agent")
    def test_session_id_generated_when_none(
        self, mock_agent, mock_route, mock_ps_cls, mock_cs_cls
    ):
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_route.return_value = "finance_qa_agent"
        mock_agent.return_value = "Answer."

        from src.workflow.orchestrator import process_query
        result = process_query("test question", session_id=None)
        assert result["session_id"] is not None

    @patch("src.memory.conversation_store.ConversationStore")
    @patch("src.memory.portfolio_store.PortfolioStore")
    @patch("src.core.router.route_query")
    @patch("src.agents.finance_qa_agent.finance_agent.ask_finance_agent")
    def test_fallback_on_agent_failure(
        self, mock_agent, mock_route, mock_ps_cls, mock_cs_cls
    ):
        """When primary agent raises, fallback to finance_qa_agent."""
        mock_store = MagicMock()
        mock_store.get_history.return_value = []
        mock_store.get_turn_count.return_value = 0
        mock_cs_cls.return_value = mock_store
        mock_ps_cls.return_value = MagicMock()
        mock_route.return_value = "tax_education_agent"
        # Primary agent fails, fallback finance_qa returns answer
        mock_agent.return_value = "Fallback answer."

        with patch("src.agents.tax_education_agent.tax_agent.explain_tax_concepts") as mock_tax:
            mock_tax.side_effect = Exception("tax agent failed")
            from src.workflow.orchestrator import process_query
            result = process_query("tax question")
            assert "answer" in result
