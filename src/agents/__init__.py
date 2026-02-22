"""Agents package — contains all domain-specific sub-agents."""

from .finance_qa_agent.finance_agent import ask_finance_agent
from .portfolio_analysis_agent.portfolio_agent import analyze_portfolio
from .market_analysis_agent.market_agent import analyze_market
from .goal_planning_agent.goal_agent import plan_goals
from .news_synthesizer_agent.news_agent import synthesize_news
from .tax_education_agent.tax_agent import explain_tax_concepts

__all__ = [
    "ask_finance_agent",
    "analyze_portfolio",
    "analyze_market",
    "plan_goals",
    "synthesize_news",
    "explain_tax_concepts",
]