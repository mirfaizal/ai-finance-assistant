"""
Tools package — reusable capabilities available to all agents.

    web_search   Real-time web search via the Tavily API
"""

from .web_search import web_search, is_realtime_query

__all__ = ["web_search", "is_realtime_query"]
