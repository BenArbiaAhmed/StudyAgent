from pydantic import BaseModel, Field

class WebSearchResponseFormat(BaseModel):
    """Response schema for web search"""
    information: str = Field(description="The information answering the question.")
    sources: list[str] | None = Field(description="The sources used to get the information.") 