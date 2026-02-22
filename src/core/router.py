"""
Router Agent

Intelligent router that determines which agent should handle a query.
Uses agent metadata and scoring to make routing decisions.
"""

from typing import Dict, List, Optional, Any
from .base_agent import BaseAgent
from .protocol import AgentInput, AgentMetadata, AgentCapability


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
ROUTING_TABLE: Dict[str, List[str]] = {
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


def route_query(question: str) -> str:
    """
    Return the name of the agent that should handle *question*.

    Checks the question text against keyword triggers in ROUTING_TABLE **in
    insertion order** (most-specific agent first).  Falls back to the default
    agent if no specific match is found.

    Parameters
    ----------
    question : str

    Returns
    -------
    str
        Agent name (key in ROUTING_TABLE).
    """
    q = question.lower()
    for agent_name, keywords in ROUTING_TABLE.items():
        if any(kw in q for kw in keywords):
            return agent_name
    # Default: send everything to the finance Q&A agent
    return _DEFAULT_AGENT
