from langchain.tools import tool, ToolRuntime
from langchain_community.tools import BraveSearch
from dotenv import load_dotenv


load_dotenv()
brave_search = BraveSearch()

@tool
def web_search(query: str, runtime: ToolRuntime) -> str:
    """
    Search for information about unclear or incomplete concepts.
    
    Use this when:
    - A concept needs a better definition
    - Examples are missing
    - Technical terms need clarification
    - Prerequisites are unclear
    
    Args:
        query: The concept or term to search for (e.g., "gradient descent definition")
    
    Returns:
        Search results with relevant information
    """
    writer = runtime.stream_writer
    writer(f"Looking up information to answer the query: {query}")
    return brave_search.run(query)