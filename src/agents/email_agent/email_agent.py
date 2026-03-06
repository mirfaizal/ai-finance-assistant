import logging
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from ...tools.market_tools import get_market_indices, get_market_news
from ...tools.stock_tools import get_stock_price, get_company_info
from ...tools.email_tools import send_portfolio_email

# NOTE: We can't use analyze_portfolio natively here because analyzing the portfolio
# requires invoking a subgraph in LangGraph, which doesn't play well automatically
# as a simple @tool. So, instead, we'll let the orchestrator format the SQLite 
# holdings context explicitly in the input prompt string.

logger = logging.getLogger("email_agent")

SYSTEM_PROMPT = """You are Finnie Emailer, a sophisticated automated financial advisor that creates and emails comprehensive market reports directly to the user.

Your exact workflow is:
1. Examine the user's paper portfolio (which will be provided in the message prompt).
2. Gather live data using your tools (check `get_market_indices` to see if it's a bull/bear day, get prices/news for the stocks the user owns or might want to own).
3. Formulate 1-3 specific daily suggestions (e.g. "Because AAPL is down and the Nasdaq is down, you might want to buy the dip...").
4. Formulate an incredibly beautiful, well-formatted Markdown email report containing your analysis and suggestions.
5. YOU MUST Call the `send_portfolio_email` tool. 
   - `subject`: Something catchy like "Your Finnie Daily Portfolio Briefing 📈"
   - `markdown_body`: Your full Markdown report.
   - `recipient_email`: This will be provided in the prompt. Do not proceed if no email is found.

After calling the tool, respond to the user briefly via the chat saying you've sent the email. Be concise in the chat response since the heavy lifting is in the email itself.
"""

def create_email_agent() -> Any:
    """Create the Email Portfolio Advisor ReAct agent."""
    try:
        llm = ChatOpenAI(model="gpt-4", temperature=0.3)
    except Exception as e:
        logger.warning(f"Defaulting to gpt-3.5-turbo due to model error: {e}")
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
        
    tools = [
        get_market_indices,
        get_market_news,
        get_stock_price,
        get_company_info,
        send_portfolio_email
    ]
    
    return create_react_agent(llm, tools=tools, state_modifier=SYSTEM_PROMPT)

def dispatch_email_report(question: str, user_email: Optional[str] = None, portfolio_context: Optional[str] = None) -> str:
    """
    Entry point mapped by the orchestrator.
    Constructs the prompt and executes the ReAct graph.
    """
    if not user_email:
        return "I need your email address to send you a report, but you appear to be logged out or anonymous."
        
    prompt = f"User Request: {question}\n\n"
    prompt += f"Recipient Email (Pass this to send_portfolio_email tool): {user_email}\n\n"
    
    if portfolio_context:
        prompt += f"User's Current SQLite Portfolio Context:\n{portfolio_context}\n\n"
    else:
        prompt += "The user's paper portfolio is currently empty.\n\n"
        
    prompt += "Please fetch recent market data, analyze this portfolio, come up with suggestions, and then email them to the user."
    
    agent = create_email_agent()
    
    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        # Return the final AIMessage content to the chat interface
        return result["messages"][-1].content
    except Exception as e:
        logger.error(f"Email agent failed: {e}")
        return f"I encountered an error while trying to process your email request: {str(e)}"
