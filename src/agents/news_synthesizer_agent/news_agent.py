"""Core logic for the News Synthesizer Agent.

Enhancements
------------
- Tavily web search: when the user provides no articles (or asks about
  'latest news'), Tavily fetches live headlines automatically.
- LangSmith tracing via @traceable decorator
"""

from __future__ import annotations

from .client import get_client, MODEL, TEMPERATURE
from .prompts import SYSTEM_PROMPT
from src.utils.logging import get_logger
from src.utils.tracing import traceable
from src.tools.web_search import web_search

logger = get_logger(__name__)

_MAX_ARTICLE_CHARS = 2000  # truncate each article to keep prompt size reasonable


_NEWS_QUERY_SIGNALS = [
    "?", "news", "headline", "latest", "recent", "today", "current",
    "what happened", "tell me", "give me", "show me", "summarize",
]


def _looks_like_user_query(text: str) -> bool:
    """Return True if the text is a user question rather than a news article."""
    t = text.strip()
    if len(t) > 300:          # real articles are longer
        return False
    tl = t.lower()
    return any(sig in tl for sig in _NEWS_QUERY_SIGNALS)


def _build_news_prompt(articles: list[str]) -> str:
    """
    Format a list of article texts into a prompt for the model.
    When articles is empty OR the single entry looks like a user question,
    Tavily is used to fetch live news automatically.
    """
    # Determine the effective search query (if any) and real articles
    search_query = "latest financial news headlines today"
    real_articles: list[str] = []

    if not articles:
        pass  # use default search_query
    elif len(articles) == 1 and _looks_like_user_query(articles[0]):
        # The orchestrator passed the user's question as the single "article"
        search_query = articles[0].strip()
        logger.info("News agent: treating single entry as user query: %s", search_query[:80])
    else:
        real_articles = articles

    if not real_articles:
        # Auto-fetch live news via Tavily
        logger.info("News agent: fetching live news via Tavily — query: %s", search_query[:80])
        live_news = web_search(search_query, max_results=5)
        if live_news:
            return (
                "Please synthesize the following live financial news "
                f"(fetched in response to: \u201c{search_query}\u201d):\n\n"
                + live_news
            )
        return (
            "No live news could be retrieved at this time. "
            "Please explain what a financial news synthesis involves and what "
            "kinds of themes typically appear in financial news."
        )

    lines: list[str] = [
        f"Please synthesize the following {len(articles)} financial news article(s):\n"
    ]

    for i, article in enumerate(articles, start=1):
        trimmed = article.strip()
        if len(trimmed) > _MAX_ARTICLE_CHARS:
            trimmed = trimmed[:_MAX_ARTICLE_CHARS] + " … [truncated]"
        lines.append(f"--- Article {i} ---\n{trimmed}\n")

    lines.append(
        "Provide a clear educational synthesis: identify key themes, explain "
        "relevant financial concepts, note any conflicts between articles, and "
        "summarise the main takeaways. Do not give personalised investment advice."
    )
    return "\n".join(lines)


@traceable(name="news_synthesizer_agent", run_type="chain", tags=["news"])
def synthesize_news(articles: list[str]) -> str:
    """
    Synthesize and contextualize financial news articles.

    If no articles are provided (empty list), Tavily automatically fetches
    the latest financial news headlines to give the LLM real content to work with.

    Parameters
    ----------
    articles : list[str]
        A list of raw article texts (or headlines + snippets).
        Pass an empty list or a single question string to trigger auto-fetch.

    Returns
    -------
    str
        Educational synthesis as plain text.

    Raises
    ------
    TypeError
        If *articles* is not a list.
    ValueError
        If any element of *articles* is not a string.
    """
    if not isinstance(articles, list):
        raise TypeError(f"articles must be a list, got {type(articles).__name__!r}.")

    non_str = [i for i, a in enumerate(articles) if not isinstance(a, str)]
    if non_str:
        raise ValueError(
            f"All articles must be strings. Non-string items at indices: {non_str}"
        )

    user_prompt = _build_news_prompt(articles)
    logger.info("News agent synthesizing %d article(s).", len(articles))

    client = get_client()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=TEMPERATURE,
    )

    answer = response.choices[0].message.content
    logger.info("News agent answer (first 80 chars): %s", answer[:80])
    return answer
