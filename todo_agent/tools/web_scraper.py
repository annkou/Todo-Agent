from langchain_tavily import TavilyExtract

from todo_agent.config import settings


def web_scraper():
    """Tavily extract tool. This tool allows you to extract content from URLs."""
    tavily_extract = TavilyExtract(
        extract_depth="basic",
        include_images=False,
        tavily_api_key=settings.tavily_api_key,
    )
    return tavily_extract
