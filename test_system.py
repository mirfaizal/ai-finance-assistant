"""
Quick Start Guide and Testing

Run this file to verify the multi-agent system is working correctly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core import BaseAgent, RouterAgent, AgentInput, AgentMetadata, AgentCapability
from src.agents import FinancialAnalystAgent, PortfolioManagerAgent, MarketResearchAgent
from src.workflow import AgentOrchestrator


def test_base_agent():
    """Test that BaseAgent works correctly"""
    print("=" * 60)
    print("Test 1: BaseAgent Functionality")
    print("=" * 60)
    
    agent = FinancialAnalystAgent()
    
    # Test call method
    output = agent.call(query="Analyze AAPL stock")
    
    print(f"✓ Agent Name: {output.agent_name}")
    print(f"✓ Status: {output.status}")
    print(f"✓ Confidence: {output.confidence}")
    print(f"✓ Result Keys: {list(output.result.keys()) if isinstance(output.result, dict) else 'N/A'}")
    print()


def test_router():
    """Test router functionality"""
    print("=" * 60)
    print("Test 2: Router Agent")
    print("=" * 60)
    
    router = RouterAgent()
    
    # Register agents
    agents = [
        FinancialAnalystAgent(),
        PortfolioManagerAgent(),
        MarketResearchAgent()
    ]
    router.register_agents(agents)
    
    # Test routing
    test_queries = [
        "Analyze AAPL stock",
        "Show my portfolio",
        "What are the market trends?"
    ]
    
    for query in test_queries:
        output = router.call(query=query)
        result = output.result
        print(f"Query: '{query}'")
        print(f"  → Routed to: {result.get('agent_name')}")
        print(f"  → Score: {result.get('score'):.2f}")
        print()


def test_orchestrator():
    """Test full orchestrator workflow"""
    print("=" * 60)
    print("Test 3: Full Orchestrator Workflow")
    print("=" * 60)
    
    # Setup
    router = RouterAgent()
    agents = [
        FinancialAnalystAgent(),
        PortfolioManagerAgent(),
        MarketResearchAgent()
    ]
    
    orchestrator = AgentOrchestrator(
        router=router,
        agents=agents
    )
    
    # Run workflow
    query = "What is the P/E ratio of AAPL?"
    print(f"Query: {query}")
    print()
    
    result = orchestrator.run(query=query)
    
    print(f"✓ Status: {result['status']}")
    print(f"✓ Agents Used: {result['metadata']['agents_used']}")
    print(f"✓ Iterations: {result['metadata']['iterations']}")
    
    if result.get('result') and 'results' in result['result']:
        for agent_name, agent_result in result['result']['results'].items():
            print(f"\n{agent_name}:")
            print(f"  Status: {agent_result['status']}")
            print(f"  Confidence: {agent_result['confidence']}")
    print()


def test_agent_metadata():
    """Test agent metadata and capabilities"""
    print("=" * 60)
    print("Test 4: Agent Metadata")
    print("=" * 60)
    
    agent = FinancialAnalystAgent()
    metadata = agent.get_metadata()
    
    print(f"Agent: {metadata.name}")
    print(f"Description: {metadata.description}")
    print(f"Version: {metadata.version}")
    print(f"\nCapabilities:")
    for cap in metadata.capabilities:
        print(f"  • {cap.name}: {cap.description}")
        print(f"    Examples: {', '.join(cap.examples[:2])}")
    print()


def test_can_handle():
    """Test agent routing scores"""
    print("=" * 60)
    print("Test 5: Agent Routing Scores")
    print("=" * 60)
    
    agents = [
        FinancialAnalystAgent(),
        PortfolioManagerAgent(),
        MarketResearchAgent()
    ]
    
    test_queries = [
        "Analyze Microsoft stock",
        "Show my investment portfolio",
        "Market trends in AI sector",
        "What's the weather like?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        scores = {}
        for agent in agents:
            score = agent.can_handle(query)
            scores[agent.name] = score
            if score > 0:
                print(f"  {agent.name}: {score:.2f}")
        
        if max(scores.values()) == 0:
            print("  → No agent can handle this query")
    print()


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "AI Finance Assistant - System Tests" + " " * 12 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        test_base_agent()
        test_router()
        test_agent_metadata()
        test_can_handle()
        test_orchestrator()
        
        print("=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Run: python -m src.main (for full demo)")
        print("  2. Review: ARCHITECTURE.md (for detailed documentation)")
        print("  3. Extend: Create your own agents by inheriting from BaseAgent")
        print()
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
