from pydantic import BaseModel, Field
class PDFContentResponseFormat(BaseModel):
    """PDF content extraction response schema"""
    content: str = Field(description="The content extracted from the pdf document.")
    format: str | None = Field(description="The format in which the content is extracted.") 