from langchain.tools import tool, ToolRuntime
from langchain_community.tools import BraveSearch
from dotenv import load_dotenv


load_dotenv()
brave_search = BraveSearch()

@tool
def web_search(query: str, runtime: ToolRuntime) -> str:
    """Search for information.
    
    Args:
        query: The search query to get response for 
    """
    writer = runtime.stream_writer
    writer(f"Looking up information to answer the query: {query}")
    return brave_search.run(query)