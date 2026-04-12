import os
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from langchain.tools import ToolRuntime, tool


load_dotenv()


def _extract_markdown(result: object) -> str:
    """Normalize Firecrawl responses across SDK versions."""
    if result is None:
        return ""

    if isinstance(result, dict):
        if isinstance(result.get("markdown"), str):
            return result["markdown"]
        data = result.get("data")
        if isinstance(data, dict) and isinstance(data.get("markdown"), str):
            return data["markdown"]

    markdown = getattr(result, "markdown", None)
    if isinstance(markdown, str):
        return markdown

    data = getattr(result, "data", None)
    if isinstance(data, dict) and isinstance(data.get("markdown"), str):
        return data["markdown"]

    return ""


@tool
def web_scrape_for_concepts(url: str, runtime: ToolRuntime) -> str:
    """Scrape full webpage content as markdown for concept enrichment.

    Use this tool when a user provides a URL and full-page context is needed.
    """
    writer = runtime.stream_writer
    writer(f"Scraping webpage for concept details: {url}")

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return "FIRECRAWL_API_KEY is not configured. Use web_search instead."

    try:
        app = FirecrawlApp(api_key=api_key)
        result = app.scrape_url(url, params={"formats": ["markdown"]})
        markdown = _extract_markdown(result).strip()

        if markdown:
            return markdown

        return f"Scrape completed but no markdown content was extracted from {url}."
    except Exception as e:
        return f"Scrape failed for {url}: {e}. Use web_search as fallback."