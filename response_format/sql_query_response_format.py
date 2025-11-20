

from pydantic import BaseModel, Field

class SQLQueryResponseFormat(BaseModel):
    """SQL query response schema"""
    result: str = Field(description="The result returned from the query execution.")
    query: str | None = Field(description="The query used to get the final response") 