"""Pydantic data models for the extraction pipeline.

Every extracted region carries the metadata the internship deliverable asks for:
a stable id, its page, a bounding box (coordinates), a confidence score, and the
engine that produced it (so results are fully traceable).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

RegionType = Literal[
    "text",
    "title",
    "table",
    "figure",
    "list",
    "stamp",
    "header",
    "footer",
    "handwriting",
    "equation",
]

SourceEngine = Literal["paddleocr", "rapidocr", "gemini"]


class Region(BaseModel):
    """A single layout region on a page."""

    id: str = Field(description="Stable region id, e.g. 'p1-r03'.")
    page: int = Field(description="0-based page index this region belongs to.")
    type: RegionType = Field(description="Detected layout/region category.")
    bbox: list[float] = Field(
        description="Bounding box in page pixels as [x0, y0, x1, y1]."
    )
    confidence: float = Field(
        description=(
            "Confidence in [0, 1]. Real OCR confidence for paddleocr/rapidocr "
            "engines; model-estimated for gemini regions."
        )
    )
    source_engine: SourceEngine = Field(
        description="Which engine produced the final content for this region."
    )
    markdown: str = Field(
        default="", description="Final Markdown rendering of this region."
    )
    ocr_text: Optional[str] = Field(
        default=None, description="Raw OCR text before any VLM re-reading, if any."
    )

    @property
    def area(self) -> float:
        x0, y0, x1, y1 = self.bbox
        return max(0.0, x1 - x0) * max(0.0, y1 - y0)


class PageResult(BaseModel):
    """All regions extracted from a single page, in reading order."""

    page: int
    width: int
    height: int
    regions: list[Region] = Field(default_factory=list)


class DocumentResult(BaseModel):
    """Consolidated result for a whole document."""

    source: str = Field(description="Original file name / path.")
    pages: list[PageResult] = Field(default_factory=list)
    markdown: str = Field(
        default="", description="Consolidated, reconciled Markdown for the document."
    )

    @property
    def region_count(self) -> int:
        return sum(len(p.regions) for p in self.pages)

    def all_regions(self) -> list[Region]:
        return [r for p in self.pages for r in p.regions]


class VLMRegionOutput(BaseModel):
    """Structured output requested from Gemini for a single cropped region."""

    markdown: str = Field(description="Markdown rendering of the region content.")
    confidence: float = Field(
        description="Model-estimated confidence in [0, 1] for this transcription."
    )
    refined_type: Optional[RegionType] = Field(
        default=None,
        description="Region type the model believes is correct, if different.",
    )
