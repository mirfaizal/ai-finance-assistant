import logging
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

from ...tools.market_tools import get_market_overview
from ...tools.news_tools import get_market_news
from ...tools.stock_tools import get_stock_quote, get_stock_financials
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

def run_email_agent(prompt: str) -> str:
    """Run the Email Portfolio Advisor logic manually."""
    try:
        llm = ChatOpenAI(model="gpt-4", temperature=0.3)
    except Exception as e:
        logger.warning(f"Defaulting to gpt-3.5-turbo due to model error: {e}")
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
        
    tools = [
        get_market_overview,
        get_market_news,
        get_stock_quote,
        get_stock_financials,
        send_portfolio_email
    ]
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]
    
    # Run manual ReAct loop
    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)
    msgs = list(messages)

    for _ in range(8):
        response = llm_with_tools.invoke(msgs)
        msgs.append(response)

        if not getattr(response, "tool_calls", None):
            return str(response.content)

        for tc in response.tool_calls:
            name = tc["name"]
            args = tc["args"]
            call_id = tc["id"]
            try:
                result = tool_map[name].invoke(args) if name in tool_map else f"Unknown tool: {name}"
            except Exception as exc:
                result = f"Tool error ({name}): {exc}"
            msgs.append(ToolMessage(content=str(result), tool_call_id=call_id))

    # Fallback to last distinct message
    for msg in reversed(msgs):
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
            return str(msg.content)
            
    return "I successfully processed your request."

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
    
    try:
        content = run_email_agent(prompt)
        return content
    except Exception as e:
        logger.error(f"Email agent failed: {e}")
        return f"I encountered an error while trying to process your email request: {str(e)}"
