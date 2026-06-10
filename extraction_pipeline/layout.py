"""Layout detection + OCR.

Detects layout regions (text/title/table/figure/list/...) with bounding boxes
and confidence scores. The engine is resolved at runtime so the pipeline keeps
working across environments:

1. PaddleOCR PP-Structure   -> richest output (real region types + OCR conf)
2. RapidOCR (onnxruntime)   -> stable, already installed; OCR lines grouped into
                               text blocks (no figure/table typing)

Both engines emit a uniform list of ``schema.Region`` objects with pixel bboxes
``[x0, y0, x1, y1]`` and a confidence in [0, 1]. Non-text regions are left with
empty ``markdown`` for the VLM stage to fill in.
"""

from __future__ import annotations

import numpy as np

from extraction_pipeline.schema import Region, RegionType

# PP-Structure label -> our RegionType. Unknown labels fall back to "text".
_PPSTRUCTURE_LABEL_MAP: dict[str, RegionType] = {
    "text": "text",
    "title": "title",
    "table": "table",
    "figure": "figure",
    "image": "figure",
    "list": "list",
    "header": "header",
    "footer": "footer",
    "reference": "text",
    "equation": "equation",
}

TEXTUAL_TYPES: set[RegionType] = {"text", "title", "list", "header", "footer"}

_engine_cache: dict[str, object] = {}


# --------------------------------------------------------------------------- #
# Geometry helpers
# --------------------------------------------------------------------------- #
def _poly_to_bbox(poly) -> list[float]:
    pts = np.asarray(poly, dtype=float).reshape(-1, 2)
    return [
        float(pts[:, 0].min()),
        float(pts[:, 1].min()),
        float(pts[:, 0].max()),
        float(pts[:, 1].max()),
    ]


def _region_id(page: int, index: int) -> str:
    return f"p{page + 1}-r{index:02d}"


# --------------------------------------------------------------------------- #
# Engine resolution
# --------------------------------------------------------------------------- #
def _resolve_engine(lang: str = "en") -> tuple[str, object]:
    """Return ``(engine_name, engine_object)``, trying the richest first."""
    if "engine" in _engine_cache:
        return _engine_cache["name"], _engine_cache["engine"]  # type: ignore[return-value]

    name, engine = None, None

    # 1) PaddleOCR PP-Structure (best region typing).
    try:
        from paddleocr import PPStructure  # type: ignore

        engine = PPStructure(show_log=False, lang=lang)
        name = "paddleocr"
    except Exception:  # noqa: BLE001 - any import/runtime failure -> fall back
        engine = None

    # 2) RapidOCR (stable, already installed).
    if engine is None:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore

        engine = RapidOCR()
        name = "rapidocr"

    _engine_cache["name"] = name
    _engine_cache["engine"] = engine
    return name, engine  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# Per-engine analysis
# --------------------------------------------------------------------------- #
def _analyze_ppstructure(engine, image: np.ndarray, page: int) -> list[Region]:
    # PP-Structure expects BGR.
    bgr = image[:, :, ::-1]
    raw = engine(bgr)
    regions: list[Region] = []
    for i, item in enumerate(raw):
        label = str(item.get("type", "text")).lower()
        rtype: RegionType = _PPSTRUCTURE_LABEL_MAP.get(label, "text")
        bbox = [float(v) for v in item["bbox"]]

        markdown, ocr_text, conf = "", None, 1.0
        res = item.get("res")
        if rtype in TEXTUAL_TYPES and isinstance(res, list):
            lines, confs = [], []
            for line in res:
                if isinstance(line, dict) and "text" in line:
                    lines.append(line["text"])
                    confs.append(float(line.get("confidence", 1.0)))
            ocr_text = "\n".join(lines)
            markdown = ocr_text
            conf = float(np.mean(confs)) if confs else 1.0
        elif rtype == "table" and isinstance(res, dict) and res.get("html"):
            # Keep the HTML table; reconcile/VLM may refine it to Markdown.
            markdown = res["html"]
            conf = 0.9

        regions.append(
            Region(
                id=_region_id(page, i),
                page=page,
                type=rtype,
                bbox=bbox,
                confidence=round(conf, 4),
                source_engine="paddleocr",
                markdown=markdown,
                ocr_text=ocr_text,
            )
        )
    return regions


def _analyze_rapidocr(engine, image: np.ndarray, page: int) -> list[Region]:
    result, _ = engine(image)
    lines = []
    if result:
        for poly, text, conf in result:
            lines.append((_poly_to_bbox(poly), str(text), float(conf)))
    blocks = _group_lines_into_blocks(lines)
    regions: list[Region] = []
    for i, (bbox, text, conf) in enumerate(blocks):
        regions.append(
            Region(
                id=_region_id(page, i),
                page=page,
                type="text",
                bbox=bbox,
                confidence=round(conf, 4),
                source_engine="rapidocr",
                markdown=text,
                ocr_text=text,
            )
        )
    return regions


def _group_lines_into_blocks(
    lines: list[tuple[list[float], str, float]],
    y_gap_ratio: float = 0.8,
) -> list[tuple[list[float], str, float]]:
    """Merge OCR text lines into paragraph blocks by vertical proximity.

    Lines are sorted top-to-bottom; a new block starts when the vertical gap to
    the previous line exceeds ``y_gap_ratio`` times the previous line height.
    """
    if not lines:
        return []

    lines = sorted(lines, key=lambda l: (l[0][1], l[0][0]))
    blocks: list[dict] = []
    for bbox, text, conf in lines:
        x0, y0, x1, y1 = bbox
        height = y1 - y0
        if blocks:
            prev = blocks[-1]
            gap = y0 - prev["bbox"][3]
            if gap <= y_gap_ratio * max(height, 1.0):
                prev["bbox"][0] = min(prev["bbox"][0], x0)
                prev["bbox"][1] = min(prev["bbox"][1], y0)
                prev["bbox"][2] = max(prev["bbox"][2], x1)
                prev["bbox"][3] = max(prev["bbox"][3], y1)
                prev["texts"].append(text)
                prev["confs"].append(conf)
                continue
        blocks.append({"bbox": [x0, y0, x1, y1], "texts": [text], "confs": [conf]})

    return [
        (b["bbox"], " ".join(b["texts"]), float(np.mean(b["confs"])))
        for b in blocks
    ]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def analyze_page(image: np.ndarray, page: int, lang: str = "en") -> list[Region]:
    """Detect and OCR all regions on a single page image (RGB ndarray)."""
    name, engine = _resolve_engine(lang)
    if name == "paddleocr":
        return _analyze_ppstructure(engine, image, page)
    return _analyze_rapidocr(engine, image, page)


def engine_name(lang: str = "en") -> str:
    return _resolve_engine(lang)[0]
