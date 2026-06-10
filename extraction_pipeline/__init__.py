"""Document Intelligence extraction & structuring pipeline.

Turns scanned / image-based / heterogeneous documents into clean, structured
Markdown with traceable regions, coordinates and confidence scores.

Public entry point: ``extraction_pipeline.pipeline.run``.
"""

from extraction_pipeline.schema import Region, PageResult, DocumentResult

__all__ = ["Region", "PageResult", "DocumentResult"]
