from langchain.tools import tool, ToolRuntime
from data_classes.context import Context
from langchain_community.utilities import OpenWeatherMapAPIWrapper
from dotenv import load_dotenv

load_dotenv()

weather_api = OpenWeatherMapAPIWrapper()

@tool
def get_weather_for_location(city: str) -> str:
    """Get weather for a given city."""
    try:
        return weather_api.run(city)
    except Exception as e:
        return f"Error fetching weather for {city}: {str(e)}"



@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """Retrieve user information based on user ID."""
    user_id = runtime.context.user_id
    return "Florida" if user_id == "1" else "SF"