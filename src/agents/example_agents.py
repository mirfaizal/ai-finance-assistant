"""
Example Agents

Demonstrates how to implement concrete agents using the BaseAgent class.
These examples show the architecture in action.
"""

from typing import Any, Dict, List
from ..core.base_agent import BaseAgent
from ..core.protocol import AgentInput, AgentMetadata, AgentCapability


class FinancialAnalystAgent(BaseAgent):
    """
    Example agent that performs financial analysis.
    Demonstrates basic agent implementation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            name="financial_analyst",
            description="Analyzes stocks, provides financial metrics, and investment insights",
            config=config
        )
    
    def get_metadata(self) -> AgentMetadata:
        """Return agent metadata and capabilities"""
        return AgentMetadata(
            name=self.name,
            description=self.description,
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="stock_analysis",
                    description="Analyze stock performance and metrics",
                    input_requirements=["ticker_symbol"],
                    output_format="Dictionary with analysis results",
                    examples=[
                        "Analyze AAPL stock",
                        "What is the P/E ratio of TSLA?",
                        "Show me MSFT performance"
                    ]
                ),
                AgentCapability(
                    name="fundamental_analysis",
                    description="Perform fundamental analysis on companies",
                    input_requirements=["company_name or ticker"],
                    output_format="Dictionary with fundamental metrics",
                    examples=[
                        "Fundamental analysis of Apple",
                        "Evaluate Tesla fundamentals"
                    ]
                )
            ],
            tags=["finance", "stocks", "analysis"]
        )
    
    def _execute(self, agent_input: AgentInput) -> Dict[str, Any]:
        """
        Execute financial analysis.
        
        In a real implementation, this would:
        - Call financial data APIs (Alpha Vantage, etc.)
        - Calculate metrics
        - Generate insights
        """
        query = agent_input.query.lower()
        context = agent_input.context
        
        # Extract ticker if possible (simple pattern matching)
        ticker = context.get("ticker")
        if not ticker:
            # Try to extract from query (very simple approach)
            common_tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
            for t in common_tickers:
                if t.lower() in query:
                    ticker = t
                    break
        
        # Mock analysis result
        result = {
            "query": agent_input.query,
            "ticker": ticker or "UNKNOWN",
            "analysis_type": "stock_analysis",
            "metrics": {
                "pe_ratio": 28.5,
                "market_cap": "2.8T",
                "52_week_high": 198.23,
                "52_week_low": 164.08
            },
            "recommendation": "This is a mock analysis. Integrate real financial APIs for actual data.",
            "confidence": 0.8,
            "sources": ["Mock Data - Replace with Alpha Vantage API"]
        }
        
        self.logger.info(f"Analyzed ticker: {ticker}")
        return result
    
    def can_handle(self, query: str, context: Dict[str, Any] = None) -> float:
        """Determine if this agent can handle the query"""
        query_lower = query.lower()
        
        # High confidence keywords
        high_confidence_keywords = ["stock", "analyze", "analysis", "ticker", "pe ratio", "metrics"]
        if any(keyword in query_lower for keyword in high_confidence_keywords):
            return 0.9
        
        # Medium confidence keywords
        medium_confidence_keywords = ["company", "performance", "financial", "valuation"]
        if any(keyword in query_lower for keyword in medium_confidence_keywords):
            return 0.6
        
        # Check for ticker symbols
        common_tickers = ["aapl", "msft", "googl", "tsla", "amzn"]
        if any(ticker in query_lower for ticker in common_tickers):
            return 0.85
        
        return 0.0


class PortfolioManagerAgent(BaseAgent):
    """
    Example agent that manages investment portfolios.
    Demonstrates agent with state and user preferences.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            name="portfolio_manager",
            description="Manages investment portfolios, tracks performance, and rebalancing",
            config=config
        )
    
    def get_metadata(self) -> AgentMetadata:
        """Return agent metadata and capabilities"""
        return AgentMetadata(
            name=self.name,
            description=self.description,
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="portfolio_tracking",
                    description="Track portfolio holdings and performance",
                    input_requirements=["portfolio_id or holdings"],
                    output_format="Dictionary with portfolio metrics",
                    examples=[
                        "Show my portfolio",
                        "Portfolio performance",
                        "What's in my portfolio?"
                    ]
                ),
                AgentCapability(
                    name="rebalancing",
                    description="Suggest portfolio rebalancing strategies",
                    input_requirements=["portfolio_data", "target_allocation"],
                    output_format="Rebalancing recommendations",
                    examples=[
                        "Should I rebalance my portfolio?",
                        "Rebalance to 60/40 stocks/bonds"
                    ]
                )
            ],
            tags=["portfolio", "investment", "management"]
        )
    
    def _execute(self, agent_input: AgentInput) -> Dict[str, Any]:
        """
        Execute portfolio management tasks.
        
        In a real implementation, this would:
        - Access user portfolio data
        - Calculate performance metrics
        - Suggest rebalancing strategies
        """
        query = agent_input.query.lower()
        
        # Mock portfolio data
        result = {
            "query": agent_input.query,
            "portfolio_id": "user_portfolio_001",
            "holdings": [
                {"ticker": "AAPL", "shares": 10, "value": 1950.00},
                {"ticker": "MSFT", "shares": 15, "value": 5250.00},
                {"ticker": "GOOGL", "shares": 5, "value": 750.00}
            ],
            "total_value": 7950.00,
            "performance": {
                "day_change": "+1.2%",
                "month_change": "+5.4%",
                "year_change": "+18.7%"
            },
            "recommendation": "Portfolio is well-balanced. Consider adding bonds for diversification.",
            "message": "This is mock data. Integrate with real portfolio tracking system."
        }
        
        self.logger.info("Retrieved portfolio data")
        return result
    
    def can_handle(self, query: str, context: Dict[str, Any] = None) -> float:
        """Determine if this agent can handle the query"""
        query_lower = query.lower()
        
        # High confidence keywords
        high_confidence_keywords = ["portfolio", "holdings", "my investments", "rebalance"]
        if any(keyword in query_lower for keyword in high_confidence_keywords):
            return 0.95
        
        # Medium confidence keywords
        medium_confidence_keywords = ["diversification", "allocation", "performance"]
        if any(keyword in query_lower for keyword in medium_confidence_keywords):
            return 0.5
        
        return 0.0


class MarketResearchAgent(BaseAgent):
    """
    Example agent that performs market research and trend analysis.
    Demonstrates RAG (Retrieval-Augmented Generation) integration.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            name="market_researcher",
            description="Researches market trends, news, and economic indicators",
            config=config
        )
    
    def get_metadata(self) -> AgentMetadata:
        """Return agent metadata and capabilities"""
        return AgentMetadata(
            name=self.name,
            description=self.description,
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="trend_analysis",
                    description="Analyze market trends and patterns",
                    input_requirements=["market or sector"],
                    output_format="Trend analysis report",
                    examples=[
                        "What are the tech market trends?",
                        "Analyze energy sector trends",
                        "Market outlook for 2026"
                    ]
                ),
                AgentCapability(
                    name="news_analysis",
                    description="Analyze financial news and sentiment",
                    input_requirements=["topic or company"],
                    output_format="News summary and sentiment",
                    examples=[
                        "Latest news on tech stocks",
                        "What's happening with the Fed?"
                    ]
                )
            ],
            tags=["research", "market", "trends", "news"],
            dependencies=["rag_system"]
        )
    
    def _execute(self, agent_input: AgentInput) -> Dict[str, Any]:
        """
        Execute market research.
        
        In a real implementation, this would:
        - Query news APIs
        - Use RAG to fetch relevant market data
        - Analyze trends using ML models
        """
        query = agent_input.query
        
        # Mock research result
        result = {
            "query": query,
            "research_type": "market_trends",
            "findings": [
                "AI and technology sectors showing strong growth",
                "Federal Reserve maintaining cautious stance on rates",
                "Emerging markets seeing increased investment flows"
            ],
            "sentiment": "Moderately Bullish",
            "key_indicators": {
                "sp500_trend": "Upward",
                "vix_level": "Low",
                "market_sentiment": "Positive"
            },
            "sources": [
                "Mock News Source - Replace with real news APIs",
                "Mock Market Data - Integrate Alpha Vantage"
            ],
            "message": "This is mock research. Integrate RAG system and news APIs for real data."
        }
        
        self.logger.info(f"Conducted market research on: {query}")
        return result
    
    def can_handle(self, query: str, context: Dict[str, Any] = None) -> float:
        """Determine if this agent can handle the query"""
        query_lower = query.lower()
        
        # High confidence keywords
        high_confidence_keywords = [
            "trend", "market", "research", "news", "outlook", 
            "sentiment", "forecast"
        ]
        if any(keyword in query_lower for keyword in high_confidence_keywords):
            return 0.85
        
        # Medium confidence keywords
        medium_confidence_keywords = ["economy", "sector", "industry"]
        if any(keyword in query_lower for keyword in medium_confidence_keywords):
            return 0.6
        
        return 0.0
