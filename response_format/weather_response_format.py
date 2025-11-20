from pydantic import BaseModel, Field

class WeatherResponseFormat(BaseModel):
    """Weather information schema"""
    punny_response: str = Field(description="The response in punny format.")
    weather_conditions: str | None = Field(description="Any interesting information about the weather if available") 