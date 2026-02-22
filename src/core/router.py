"""
Router Agent

Intelligent router that determines which agent should handle a query.
Uses agent metadata and scoring to make routing decisions.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
from .base_agent import BaseAgent
from .protocol import AgentInput, AgentMetadata, AgentCapability

_router_logger = logging.getLogger("llm_router")


class RouterAgent(BaseAgent):
    """
    Router agent that analyzes queries and routes them to appropriate agents.
    
    The router maintains a registry of available agents and uses their
    metadata and can_handle() methods to make routing decisions.
    """
    
    def __init__(
        self,
        name: str = "router",
        description: str = "Routes queries to appropriate specialized agents",
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(name, description, config)
        self.agent_registry: Dict[str, BaseAgent] = {}
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the router.
        
        Args:
            agent: The agent instance to register
        """
        self.agent_registry[agent.name] = agent
        self.logger.info(f"Registered agent: {agent.name}")
    
    def register_agents(self, agents: List[BaseAgent]) -> None:
        """
        Register multiple agents with the router.
        
        Args:
            agents: List of agent instances to register
        """
        for agent in agents:
            self.register_agent(agent)
    
    def get_metadata(self) -> AgentMetadata:
        """Return router metadata"""
        return AgentMetadata(
            name=self.name,
            description=self.description,
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="routing",
                    description="Routes queries to appropriate agents",
                    input_requirements=["query"],
                    output_format="Dictionary with 'agent_name' and 'reasoning'",
                    examples=[
                        "Analyze AAPL stock",
                        "What should I invest in?",
                        "Show me portfolio performance"
                    ]
                )
            ],
            tags=["routing", "orchestration"]
        )
    
    def _execute(self, agent_input: AgentInput) -> Dict[str, Any]:
        """
        Execute routing logic to determine which agent should handle the query.
        
        Args:
            agent_input: The input containing the query to route
            
        Returns:
            Dict with 'agent_name', 'score', and 'reasoning'
        """
        query = agent_input.query
        context = agent_input.context
        
        self.logger.info(f"Routing query: {query[:100]}...")
        
        # Score each registered agent
        scores: Dict[str, float] = {}
        for agent_name, agent in self.agent_registry.items():
            try:
                score = agent.can_handle(query, context)
                scores[agent_name] = score
                self.logger.debug(f"Agent '{agent_name}' score: {score}")
            except Exception as e:
                self.logger.warning(f"Error scoring agent '{agent_name}': {e}")
                scores[agent_name] = 0.0
        
        # Select agent with highest score
        if not scores or max(scores.values()) == 0.0:
            # No agent can handle this query
            return {
                "agent_name": None,
                "score": 0.0,
                "reasoning": "No suitable agent found for this query",
                "all_scores": scores
            }
        
        best_agent_name = max(scores, key=scores.get)
        best_score = scores[best_agent_name]
        best_agent = self.agent_registry[best_agent_name]
        
        reasoning = self._generate_reasoning(
            query=query,
            selected_agent=best_agent,
            score=best_score,
            all_scores=scores
        )
        
        return {
            "agent_name": best_agent_name,
            "score": best_score,
            "reasoning": reasoning,
            "all_scores": scores,
            "agent_metadata": best_agent.get_metadata().dict()
        }
    
    def _generate_reasoning(
        self,
        query: str,
        selected_agent: BaseAgent,
        score: float,
        all_scores: Dict[str, float]
    ) -> str:
        """
        Generate human-readable reasoning for the routing decision.
        
        Args:
            query: The original query
            selected_agent: The agent that was selected
            score: The score of the selected agent
            all_scores: Scores of all agents
            
        Returns:
            Reasoning string
        """
        metadata = selected_agent.get_metadata()
        
        reasoning_parts = [
            f"Selected '{selected_agent.name}' (score: {score:.2f})",
            f"Reason: {metadata.description}",
        ]
        
        if metadata.capabilities:
            cap_names = [cap.name for cap in metadata.capabilities]
            reasoning_parts.append(f"Capabilities: {', '.join(cap_names)}")
        
        # Show alternatives if any
        sorted_scores = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_scores) > 1:
            alternatives = [f"{name}({score:.2f})" for name, score in sorted_scores[1:3]]
            if alternatives:
                reasoning_parts.append(f"Alternatives: {', '.join(alternatives)}")
        
        return " | ".join(reasoning_parts)
    
    def _calculate_confidence(self, result: Any) -> float:
        """
        Calculate confidence based on the routing score.
        
        Args:
            result: The routing result dictionary
            
        Returns:
            Confidence score
        """
        if result and isinstance(result, dict):
            return result.get("score", 0.0)
        return 0.0
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all registered agents and their metadata.
        
        Returns:
            List of agent information dictionaries
        """
        agents_info = []
        for agent_name, agent in self.agent_registry.items():
            metadata = agent.get_metadata()
            agents_info.append({
                "name": agent_name,
                "description": agent.description,
                "capabilities": [cap.dict() for cap in metadata.capabilities],
                "tags": metadata.tags
            })
        return agents_info


# ── Simple functional router (used by orchestrator.process_query) ──────────────

# Routing table: order matters — more-specific agents are checked first.
# Maps agent name → list of keyword triggers (lowercase).
# ── LLM routing ─────────────────────────────────────────────────────────────

AGENT_DESCRIPTIONS: Dict[str, str] = {
    "stock_agent": (
        "Individual stock prices, historical performance, P/E ratios, earnings, "
        "analyst ratings, buy/sell/hold recommendations, comparing two stocks."
    ),
    "portfolio_analysis_agent": (
        "User's own portfolio: allocation, holdings, rebalancing, concentration risk, "
        "total value, cost basis, P&L, diversification suggestions."
    ),
    "market_analysis_agent": (
        "Broad market conditions, sector performance, indices (S&P 500, Nasdaq, Dow), "
        "VIX, macro trends, bull/bear markets, market overview."
    ),
    "news_synthesizer_agent": (
        "Summarise or fetch financial news headlines, earnings reports, press releases, "
        "company announcements, and current financial events."
    ),
    "goal_planning_agent": (
        "Financial goal setting, savings plans, retirement calculations, emergency fund, "
        "monthly savings targets, time horizon, inflation-adjusted growth projections."
    ),
    "tax_education_agent": (
        "Tax concepts, capital gains, tax-loss harvesting, wash-sale rule, Roth vs Traditional IRA, "
        "401k, HSA, 529, tax brackets, deductions, W-2, 1099, IRS rules."
    ),
    "finance_qa_agent": (
        "General financial education: compound interest, bonds, dividends, ETFs, liquidity, "
        "inflation, credit, loans, asset classes, investing basics."
    ),
}

_LLM_ROUTING_SYSTEM = (
    "You are a routing assistant for a financial AI system. "
    "Given a user question and conversation context, choose the best agent.\n\n"
    "Available agents and their responsibilities:\n"
    + "\n".join(f"- {name}: {desc}" for name, desc in AGENT_DESCRIPTIONS.items())
    + "\n\nRespond ONLY with valid JSON: "
    '{"agent": "<agent_name>", "confidence": 0.9}'
    " where agent is exactly one of the agent names listed above."
)


def route_query_llm(
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """
    Use gpt-4.1-mini to pick the best agent for *question*.
    Returns the agent name or None on failure (triggers keyword fallback).
    """
    try:
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        context_lines: List[str] = []
        if history:
            for entry in history[-4:]:
                role = "User" if entry.get("role") == "user" else "Assistant"
                text = entry.get("content", "")[:200]
                context_lines.append(f"{role}: {text}")

        user_content = question
        if context_lines:
            user_content = "Context:\n" + "\n".join(context_lines) + "\n\nNew question: " + question

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("ROUTER_MODEL", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": _LLM_ROUTING_SYSTEM},
                {"role": "user",   "content": user_content},
            ],
            temperature=0,
            max_tokens=80,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        agent_name = parsed.get("agent", "").strip()
        confidence = float(parsed.get("confidence", 0.0))

        if agent_name in AGENT_DESCRIPTIONS and confidence >= 0.5:
            _router_logger.info("LLM routed to '%s' (confidence=%.2f)", agent_name, confidence)
            return agent_name

        _router_logger.warning("LLM low confidence (%s %.2f) — keyword fallback", agent_name, confidence)
        return None
    except Exception as exc:
        _router_logger.warning("LLM routing failed (%s) — keyword fallback", exc)
        return None


# ── Keyword routing table (fallback) ─────────────────────────────────────────

ROUTING_TABLE: Dict[str, List[str]] = {
    # Stock agent — single-ticker / specific-stock queries
    "stock_agent": [
        "stock price", "share price", "trading at", "price of",
        "p/e ratio", "pe ratio", "eps", "earnings per share",
        "analyst rating", "buy or sell", "overvalued", "undervalued",
        "52-week", "52 week", "stock history", "stock performance",
        "fundamentals", "market cap of", "aapl stock", "tsla stock",
        "nvda stock", "msft stock", "googl stock",
    ],
    # Portfolio analysis — most specific, checked first
    "portfolio_analysis_agent": [
        "portfolio",
        "allocation",
        "holdings",
        "rebalance",
        "rebalancing",
        "asset mix",
        "weighting",
        "overweight",
        "underweight",
        "concentration",
        "risk profile",
        "my stocks",
        "my investments",
        "my assets",
        "my holdings",
        "analyze my",
        "analyse my",
        "review my portfolio",
        "diversif",
    ],
    # News synthesizer — BEFORE market_analysis so 'market news' routes here
    "news_synthesizer_agent": [
        "news",
        "headline",
        "summarize",
        "summarise",
        "synthesize",
        "market news",
        "financial news",
        "latest news",
        "breaking",
        "press release",
        "article",
        "what happened",
        "recent report",
        "earnings report",
        "announcement",
        "today's news",
        "current events",
        "current news",
    ],
    # Market analysis agent
    "market_analysis_agent": [
        "market trend",
        "market analysis",
        "stock market",
        "sector",
        "index",
        "indices",
        "volatility",
        "macro",
        "macroeconomic",
        "s&p",
        "nasdaq",
        "dow",
        "vix",
        "bull market",
        "bear market",
        "market today",
        "stock price",
        "price of",
        "current price",
        "trading today",
    ],
    # Goal planning agent
    "goal_planning_agent": [
        "goal",
        "goals",
        "planning",
        "budget",
        "budgeting",
        "saving",
        "savings",
        "retirement plan",
        "emergency fund",
        "time horizon",
        "financial plan",
        "50/30/20",
        "down payment",
        "monthly savings",
    ],
    # Tax education agent
    "tax_education_agent": [
        "tax",
        "taxes",
        "deduction",
        "tax credit",
        "capital gains",
        "roth",
        "traditional ira",
        "tax bracket",
        "marginal rate",
        "effective rate",
        "w-2",
        "1099",
        "irs",
        "tax return",
        "tax filing",
        "taxable income",
    ],
    # General finance Q&A — broadest, checked last
    # Also handles real-time / current-affairs questions via Tavily search
    "finance_qa_agent": [
        "finance", "invest", "bond", "fund", "ira", "401k",
        "compound", "interest", "dividend", "insurance",
        "inflation", "compound interest", "asset", "credit", "loan",
        "etf", "stock", "equity", "market",
        # real-time / current-affairs queries (Tavily handles these)
        "today", "current", "right now", "who is", "what is the",
        "latest rate", "rate today", "president", "fed rate",
        "what date", "today's date",
    ],
}

_DEFAULT_AGENT = "finance_qa_agent"


def _route_by_keywords(question: str) -> str:
    """Pure keyword fallback — no LLM call."""
    q = question.lower()
    for agent_name, keywords in ROUTING_TABLE.items():
        if any(kw in q for kw in keywords):
            return agent_name
    return _DEFAULT_AGENT


def route_query(
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
    use_llm: bool = True,
) -> str:
    """
    Return the agent name that should handle *question*.

    Strategy
    --------
    1. Try LLM routing (gpt-4.1-mini with conversation context).
    2. Fall back to keyword matching from ROUTING_TABLE on failure.

    Parameters
    ----------
    question : str
    history : list of {"role": str, "content": str}, optional
        Prior turns — used by LLM routing for pronoun resolution.
    use_llm : bool
        Set False to skip LLM routing (tests / low-latency paths).
    """
    if use_llm:
        llm_choice = route_query_llm(question, history)
        if llm_choice:
            return llm_choice
    return _route_by_keywords(question)
