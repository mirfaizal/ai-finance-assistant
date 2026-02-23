"""Agents package — contains all domain-specific sub-agents.

Nine specialized agents, each an expert in a specific financial domain:

  Core Q&A / Education
  --------------------
  ask_finance_agent       finance_qa_agent         General finance Q&A (Tavily + RAG)
  explain_tax_concepts    tax_education_agent       Tax education (TAX_TOOLS ReAct + RAG)

  Market & Stock Data
  -------------------
  ask_stock_agent         stock_agent               Individual stock analysis (STOCK_TOOLS ReAct)
  analyze_market          market_analysis_agent     Market trends & macro (MARKET_TOOLS + Tavily)
  ask_trading_agent       trading_agent             Paper-trading via buy/sell tools (SQLite)

  Portfolio & Goals
  -----------------
  analyze_portfolio       portfolio_analysis_agent  Portfolio diversification (PORTFOLIO_TOOLS ReAct)
  plan_goals              goal_planning_agent       Goal setting & retirement planning (RAG)

  News & Memory
  -------------
  synthesize_news         news_synthesizer_agent    Financial news synthesis (Tavily auto-fetch)
  synthesize_memory       memory_synthesizer_agent  GPT history compressor (triggered >5 turns)
"""

# ── Core Q&A / Education ──────────────────────────────────────────────────────
from .finance_qa_agent.finance_agent import ask_finance_agent
from .tax_education_agent.tax_agent import explain_tax_concepts

# ── Market & Stock Data ───────────────────────────────────────────────────────
from .stock_agent.stock_agent import ask_stock_agent
from .market_analysis_agent.market_agent import analyze_market
from .trading_agent.trading_agent import ask_trading_agent

# ── Portfolio & Goals ─────────────────────────────────────────────────────────
from .portfolio_analysis_agent.portfolio_agent import analyze_portfolio
from .goal_planning_agent.goal_agent import plan_goals

# ── News & Memory ─────────────────────────────────────────────────────────────
from .news_synthesizer_agent.news_agent import synthesize_news
from .memory_synthesizer_agent.memory_agent import synthesize_memory

__all__ = [
    # Core Q&A / Education
    "ask_finance_agent",
    "explain_tax_concepts",
    # Market & Stock Data
    "ask_stock_agent",
    "analyze_market",
    "ask_trading_agent",
    # Portfolio & Goals
    "analyze_portfolio",
    "plan_goals",
    # News & Memory
    "synthesize_news",
    "synthesize_memory",
]