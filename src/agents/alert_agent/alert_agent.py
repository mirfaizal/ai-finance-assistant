import logging
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from ...tools.market_tools import get_market_indices, get_market_news
from ...tools.stock_tools import get_stock_price, get_company_info
from ...memory.notification_store import NotificationStore

logger = logging.getLogger("alert_agent")

SYSTEM_PROMPT = """You are Finnie Alert, an automated daily insights generator.

You are being invoked silently in the background because the user just logged in. 
Your exact workflow:
1. Review the user's paper portfolio (injected into your prompt).
2. Look at live market conditions and news for their held stocks or the broader market.
3. Formulate exactly 1-2 QUICK, punchy insights. 
4. Include actionable links in your markdown. Use relative links to the `/assistant` tab with a pre-filled query.
   - Example format: `To rebalance safely: [Ask Finnie about ETFs](/assistant?q=Find+good+ETFs)`
   - Example format 2: `[Take profits on AAPL](/assistant?q=Sell+all+my+AAPL+shares)`
5. Keep the total output to 2-3 short sentences. Markdown is fully supported. This will appear as a small banner on their dashboard.
"""

def create_alert_agent() -> Any:
    """Create the Login Alert ReAct agent."""
    try:
        # We can use gpt-4.1-mini as it's faster for simple banner text
        llm = ChatOpenAI(model="gpt-4", temperature=0.5) 
    except Exception as e:
        logger.warning(f"Defaulting to gpt-3.5-turbo due to model error: {e}")
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.5)
        
    tools = [
        get_market_indices,
        get_market_news,
        get_stock_price,
        get_company_info
    ]
    
    return create_react_agent(llm, tools=tools, state_modifier=SYSTEM_PROMPT)

def generate_login_alert(user_email: str, portfolio_context: Optional[str] = None) -> None:
    """
    Entry point for generating a login alert. 
    It is executed in a background FastAPI thread.
    On completion, it pushes the alert to the NotificationStore.
    """
    if not user_email:
        return
        
    prompt = "The user just logged in. Here is their portfolio.\n\n"
    
    if portfolio_context:
        prompt += f"Portfolio Context:\n{portfolio_context}\n\n"
    else:
        prompt += "The user currently has no holdings. Suggest a good beginner stock or index to look at.\n\n"
        
    prompt += "Analyze the market and generate a concise banner notification for their dashboard with an actionable link."
    
    agent = create_alert_agent()
    
    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        insight_markdown = result["messages"][-1].content
        
        # Determine a title
        title = "Daily Portfolio Insights" if portfolio_context else "Welcome to Finnie!"
        
        # Save to store
        NotificationStore.add_notification(user_email, insight_markdown, title)
        logger.info(f"Generated alert for {user_email}")
        
    except Exception as e:
        logger.error(f"Alert agent failed: {e}")
