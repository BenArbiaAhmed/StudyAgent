"""VLM (Gemini) interpretation of individual layout regions.

Non-textual regions (figures, tables, stamps, diagrams) and low-confidence text
regions (likely handwriting or poor scans) are cropped from the page image and
sent to Gemini for interpretation. Gemini returns Markdown plus a
model-estimated confidence (clearly distinct from real OCR confidence).

Reuses the project's existing Gemini client and ``types.Part.from_bytes``
pattern from ``tools/analyzer_tools/pdf_loader.py``.
"""

from __future__ import annotations

import io

import numpy as np
from google.genai import types

from tools.analyzer_tools.pdf_loader import genai_client
from extraction_pipeline.schema import Region, RegionType, VLMRegionOutput
from extraction_pipeline.layout import TEXTUAL_TYPES

VLM_MODEL = "gemini-2.5-flash"

# Region types that always require VLM interpretation (not plain OCR text).
NON_TEXTUAL_TYPES: set[RegionType] = {"table", "figure", "stamp", "equation"}

# Text regions with OCR confidence below this are re-read by the VLM.
DEFAULT_CONF_THRESHOLD = 0.80

_TYPE_INSTRUCTIONS: dict[RegionType, str] = {
    "table": (
        "This region is a TABLE. Reconstruct it as a GitHub-flavored Markdown "
        "table, preserving every row, column and header. Output only the table."
    ),
    "figure": (
        "This region is a FIGURE, chart or diagram. Produce a concise Markdown "
        "image reference with descriptive alt text capturing what it shows, e.g. "
        "`![<description>](figure)`. If it contains readable labels or data, add "
        "them as a short bullet list beneath."
    ),
    "stamp": (
        "This region is a STAMP, seal or signature block. Transcribe any visible "
        "text and briefly describe the stamp in italics, e.g. "
        "`*[stamp: <description>]* <transcribed text>`."
    ),
    "equation": (
        "This region is a mathematical EQUATION. Transcribe it as LaTeX wrapped in "
        "`$$ ... $$`."
    ),
    "handwriting": (
        "This region contains HANDWRITING. Transcribe it as faithfully as "
        "possible into plain Markdown text. Do not invent content."
    ),
}

_DEFAULT_INSTRUCTION = (
    "Transcribe the content of this document region into clean Markdown, "
    "preserving structure (headings, lists, emphasis). Add nothing that is not "
    "visible."
)


def needs_vlm(region: Region, conf_threshold: float = DEFAULT_CONF_THRESHOLD) -> bool:
    """Decide whether a region should be (re)interpreted by the VLM."""
    if region.type in NON_TEXTUAL_TYPES or region.type == "handwriting":
        return True
    if region.type in TEXTUAL_TYPES and region.confidence < conf_threshold:
        return True
    return False


def _crop(image: np.ndarray, bbox: list[float], pad: int = 4) -> np.ndarray:
    h, w = image.shape[:2]
    x0, y0, x1, y1 = bbox
    x0 = max(0, int(x0) - pad)
    y0 = max(0, int(y0) - pad)
    x1 = min(w, int(x1) + pad)
    y1 = min(h, int(y1) + pad)
    if x1 <= x0 or y1 <= y0:
        return image
    return image[y0:y1, x0:x1]


def _to_png_bytes(image: np.ndarray) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.fromarray(image.astype(np.uint8)).save(buf, format="PNG")
    return buf.getvalue()


def _build_prompt(region: Region) -> str:
    instruction = _TYPE_INSTRUCTIONS.get(region.type, _DEFAULT_INSTRUCTION)
    hint = ""
    if region.ocr_text:
        hint = (
            "\n\nAn OCR engine produced this low-confidence text for the region; "
            "use it only as a hint and correct it against the image:\n"
            f'"""\n{region.ocr_text}\n"""'
        )
    return (
        f"{instruction}{hint}\n\n"
        "Return JSON with: 'markdown' (the rendering), 'confidence' (your "
        "estimated transcription accuracy in 0..1), and optionally 'refined_type'."
    )


def interpret_region(image: np.ndarray, region: Region) -> Region:
    """Return a new Region with VLM-produced Markdown and estimated confidence."""
    crop = _crop(image, region.bbox)
    png = _to_png_bytes(crop)
    prompt = _build_prompt(region)

    try:
        response = genai_client.models.generate_content(
            model=VLM_MODEL,
            contents=[
                types.Part.from_bytes(data=png, mime_type="image/png"),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VLMRegionOutput,
            ),
        )
        parsed: VLMRegionOutput | None = getattr(response, "parsed", None)
    except Exception as e:  # noqa: BLE001 - keep pipeline alive on per-region failure
        return region.model_copy(
            update={
                "markdown": region.markdown or region.ocr_text or "",
                "confidence": region.confidence,
            }
        )

    if parsed is None:
        return region

    new_type = parsed.refined_type or region.type
    return region.model_copy(
        update={
            "type": new_type,
            "markdown": parsed.markdown.strip(),
            "confidence": round(float(parsed.confidence), 4),
            "source_engine": "gemini",
        }
    )
