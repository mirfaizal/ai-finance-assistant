"""
Main Entry Point for AI Finance Assistant

Demonstrates how to set up and use the multi-agent system.
This file shows the complete integration of all components.
"""

import logging
from typing import Dict, Any, Optional

from .core.router import RouterAgent
from .core.base_agent import BaseAgent
from .workflow.orchestrator import AgentOrchestrator
from .agents.example_agents import (
    FinancialAnalystAgent,
    PortfolioManagerAgent,
    MarketResearchAgent
)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


class FinanceAssistant:
    """
    Main interface for the AI Finance Assistant.
    Simplifies interaction with the multi-agent system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Finance Assistant.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        setup_logging(level=logging.INFO)
        self.logger = logging.getLogger("finance_assistant")
        
        # Initialize router
        self.router = RouterAgent()
        
        # Initialize specialized agents
        self.agents = self._initialize_agents()
        
        # Initialize orchestrator
        self.orchestrator = AgentOrchestrator(
            router=self.router,
            agents=self.agents,
            config=self.config
        )
        
        self.logger.info("AI Finance Assistant initialized successfully")
    
    def _initialize_agents(self) -> list[BaseAgent]:
        """
        Initialize all specialized agents.
        
        Returns:
            List of agent instances
        """
        agents = [
            FinancialAnalystAgent(config=self.config.get("financial_analyst", {})),
            PortfolioManagerAgent(config=self.config.get("portfolio_manager", {})),
            MarketResearchAgent(config=self.config.get("market_researcher", {}))
        ]
        
        self.logger.info(f"Initialized {len(agents)} agents")
        return agents
    
    def query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user query through the multi-agent system.
        
        Args:
            query: The user's question or request
            context: Optional context dictionary
            session_id: Optional session identifier for tracking
            
        Returns:
            Dictionary with the response and metadata
        """
        self.logger.info(f"Processing query: {query[:100]}...")
        
        result = self.orchestrator.run(
            query=query,
            context=context,
            session_id=session_id
        )
        
        return result
    
    def list_agents(self) -> Dict[str, Any]:
        """
        Get information about all available agents.
        
        Returns:
            Dictionary with agent information
        """
        agents_info = self.router.list_agents()
        return {
            "total_agents": len(agents_info),
            "agents": agents_info
        }
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Get a specific agent by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent instance or None if not found
        """
        return self.orchestrator.agents.get(agent_name)


def main():
    """
    Example usage of the AI Finance Assistant.
    Demonstrates various queries and capabilities.
    """
    print("=" * 60)
    print("AI Finance Assistant - Multi-Agent System Demo")
    print("=" * 60)
    print()
    
    # Initialize the assistant
    assistant = FinanceAssistant()
    
    # List available agents
    print("Available Agents:")
    agents_info = assistant.list_agents()
    for agent in agents_info["agents"]:
        print(f"  • {agent['name']}: {agent['description']}")
    print()
    
    # Example queries
    example_queries = [
        "Analyze AAPL stock performance",
        "Show me my portfolio",
        "What are the current market trends in technology?",
        "What is the P/E ratio of Tesla?",
        "Should I rebalance my portfolio?"
    ]
    
    print("Running Example Queries:")
    print("-" * 60)
    
    for i, query in enumerate(example_queries, 1):
        print(f"\nQuery {i}: {query}")
        print("-" * 60)
        
        # Process the query
        result = assistant.query(query)
        
        # Display results
        print(f"Status: {result['status']}")
        if result.get('result'):
            print(f"Agents Used: {result['metadata']['agents_used']}")
            print(f"Iterations: {result['metadata']['iterations']}")
            
            # Show agent results
            if 'results' in result['result']:
                for agent_name, agent_result in result['result']['results'].items():
                    print(f"\n  {agent_name}:")
                    print(f"    Status: {agent_result['status']}")
                    print(f"    Confidence: {agent_result['confidence']}")
                    if agent_result.get('result'):
                        # Pretty print some key info
                        res = agent_result['result']
                        if isinstance(res, dict):
                            for key in ['recommendation', 'message', 'sentiment']:
                                if key in res:
                                    print(f"    {key.title()}: {res[key]}")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        
        print()
    
    print("=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
