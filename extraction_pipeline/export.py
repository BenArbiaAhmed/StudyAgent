"""Persist the consolidated result.

Writes three artifacts per document:
- ``<name>.md``            consolidated Markdown with per-region traceability
                           HTML comments (invisible when rendered).
- ``<name>.regions.json``  full structured data (regions, coordinates, scores).
- ``<name>.p{n}.overlay.png``  page image with colored bounding boxes (optional,
                           only when page images are provided).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from extraction_pipeline.schema import Region, PageResult, DocumentResult

# RGB colors per region type for the annotated overlay.
_TYPE_COLORS: dict[str, tuple[int, int, int]] = {
    "text": (66, 135, 245),
    "title": (245, 66, 66),
    "table": (66, 245, 156),
    "figure": (245, 167, 66),
    "list": (138, 66, 245),
    "stamp": (245, 66, 200),
    "header": (120, 120, 120),
    "footer": (120, 120, 120),
    "handwriting": (66, 218, 245),
    "equation": (200, 200, 66),
}
_DEFAULT_COLOR = (0, 200, 0)


def _region_comment(region: Region) -> str:
    bbox = ", ".join(f"{v:.0f}" for v in region.bbox)
    return (
        f"<!-- region id={region.id} type={region.type} "
        f"bbox=[{bbox}] conf={region.confidence:.2f} "
        f"engine={region.source_engine} -->"
    )


def traceable_markdown(doc: DocumentResult) -> str:
    """Consolidated Markdown with a traceability comment before each region."""
    chunks: list[str] = []
    multipage = len(doc.pages) > 1
    for page in doc.pages:
        if multipage:
            chunks.append(f"<!-- page {page.page + 1} -->")
        for region in page.regions:
            body = (region.markdown or "").strip()
            if not body:
                continue
            if region.type == "title" and not body.lstrip().startswith("#"):
                body = f"## {body}"
            chunks.append(f"{_region_comment(region)}\n{body}")
    return "\n\n".join(chunks)


def annotated_overlay(image: np.ndarray, page: PageResult) -> np.ndarray:
    """Return a copy of the page image with region bounding boxes drawn on it."""
    from PIL import Image, ImageDraw

    im = Image.fromarray(image.astype(np.uint8)).convert("RGB")
    draw = ImageDraw.Draw(im)
    for region in page.regions:
        color = _TYPE_COLORS.get(region.type, _DEFAULT_COLOR)
        x0, y0, x1, y1 = region.bbox
        draw.rectangle([x0, y0, x1, y1], outline=color, width=3)
        label = f"{region.id} {region.type} {region.confidence:.2f}"
        draw.text((x0 + 2, max(0, y0 - 12)), label, fill=color)
    return np.asarray(im)


def write_outputs(
    doc: DocumentResult,
    out_dir: str | Path,
    images: list[np.ndarray] | None = None,
    stem: str | None = None,
) -> dict[str, Path]:
    """Write Markdown, JSON sidecar and overlay PNGs. Returns artifact paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = stem or Path(doc.source).stem

    written: dict[str, Path] = {}

    md_path = out_dir / f"{stem}.md"
    md_path.write_text(traceable_markdown(doc), encoding="utf-8")
    written["markdown"] = md_path

    json_path = out_dir / f"{stem}.regions.json"
    json_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    written["json"] = json_path

    if images is not None:
        from PIL import Image

        for page in doc.pages:
            if page.page >= len(images):
                continue
            overlay = annotated_overlay(images[page.page], page)
            overlay_path = out_dir / f"{stem}.p{page.page + 1}.overlay.png"
            Image.fromarray(overlay).save(overlay_path)
            written[f"overlay_p{page.page + 1}"] = overlay_path

    return written
