from langchain.tools import tool
from langchain_community.tools import BraveSearch
from dotenv import load_dotenv


load_dotenv()
brave_search = BraveSearch()

@tool
def web_search(query: str) -> str:
    """Search for information."""
    return brave_search.run(query)