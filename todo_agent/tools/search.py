from langchain_tavily import TavilySearch

from todo_agent.config import settings


def create_search_tool():
    """Create Tavily search tool"""
    tavily_search = TavilySearch(
        max_results=3, topic="general", tavily_api_key=settings.tavily_api_key
    )
    return tavily_search
