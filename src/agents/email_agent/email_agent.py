import logging
from typing import Optional

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
2. Gather live data using your tools (check `get_market_overview` to see if it's a bull/bear day, get prices/news for the stocks the user owns or might want to own).
3. Formulate 1-3 specific daily suggestions (e.g. "Because AAPL is down and the Nasdaq is down, you might want to buy the dip...").
4. Compose a well-formatted Markdown report containing your full analysis and suggestions.
5. YOU MUST call the `send_portfolio_email` tool with:
   - `subject`: Something catchy like "Your Finnie Daily Portfolio Briefing 📈"
   - `markdown_body`: Your full Markdown report.
   - `recipient_email`: This will be provided in the prompt. Do not proceed if no email is found.

After calling the tool and receiving a SUCCESS response, reply briefly in chat confirming the email was sent.

CRITICAL FALLBACK — READ CAREFULLY:
If `send_portfolio_email` returns ANY message starting with "Failed:", email delivery failed completely.
You MUST immediately write your COMPLETE portfolio analysis directly in your chat reply.
Do NOT say "I was unable to send" and stop. Do NOT use a colon and then produce nothing.
Instead, output the full Markdown report right here — beginning with a # header — so the user
can still read all market data, holdings analysis, and actionable suggestions."""

# Minimum character count and required marker to consider a response a real analysis.
_MIN_ANALYSIS_LEN = 300
_ANALYSIS_MARKER = "#"


def run_email_agent(prompt: str) -> str:
    """Run the Email Portfolio Advisor logic manually."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    tools = [
        get_market_overview,
        get_market_news,
        get_stock_quote,
        get_stock_financials,
        send_portfolio_email,
    ]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)
    msgs = list(messages)

    email_failed = False
    final_text: Optional[str] = None

    for _ in range(8):
        response = llm_with_tools.invoke(msgs)
        msgs.append(response)

        if not getattr(response, "tool_calls", None):
            # LLM produced a text response — capture it and exit the loop so we
            # can still apply the email-failure fallback check below.
            final_text = str(response.content)
            break

        for tc in response.tool_calls:
            name = tc["name"]
            args = tc["args"]
            call_id = tc["id"]
            try:
                result = (
                    tool_map[name].invoke(args)
                    if name in tool_map
                    else f"Unknown tool: {name}"
                )
                if name == "send_portfolio_email" and str(result).startswith("Failed:"):
                    email_failed = True
            except Exception as exc:
                result = f"Tool error ({name}): {exc}"
                if name == "send_portfolio_email":
                    email_failed = True
            msgs.append(ToolMessage(content=str(result), tool_call_id=call_id))

    # -----------------------------------------------------------------------
    # Fallback: if email delivery failed AND the LLM's reply doesn't actually
    # contain the analysis (e.g. it only produced the apologetic intro line),
    # force a second LLM call that writes the full analysis into the chat.
    # -----------------------------------------------------------------------
    response_is_thin = final_text is None or (
        len(final_text) < _MIN_ANALYSIS_LEN or _ANALYSIS_MARKER not in final_text
    )
    if email_failed and response_is_thin:
        followup_instruction = (
            "The email could not be delivered due to a server configuration issue. "
            "You MUST now output the COMPLETE portfolio analysis as a well-formatted "
            "Markdown document directly in this chat message. "
            "Start immediately with a top-level Markdown header "
            "(e.g. '# Your Daily Portfolio Briefing'). "
            "Include: (1) a market overview summary, (2) a per-holding analysis with "
            "current prices and P&L, and (3) at least two specific, actionable "
            "suggestions with clear reasoning. "
            "Do NOT open with an apology or explanation — go straight into the analysis."
        )
        msgs.append(HumanMessage(content=followup_instruction))
        try:
            followup_response = llm_with_tools.invoke(msgs)
            return str(followup_response.content)
        except Exception as exc:
            logger.error(f"Follow-up analysis call failed: {exc}")

    if final_text is not None:
        return final_text

    # Last-resort: return the most recent substantive AI message
    for msg in reversed(msgs):
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
            return str(msg.content)

    return "I was unable to complete the portfolio analysis. Please try again."

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
