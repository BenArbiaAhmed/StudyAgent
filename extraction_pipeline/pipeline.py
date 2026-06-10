"""End-to-end orchestrator.

ingest -> layout + OCR -> VLM region interpretation -> reconcile -> export.

Run as a module:
    python -m extraction_pipeline.pipeline path/to/document.pdf
    python -m extraction_pipeline.pipeline scan.png --out results --no-vlm
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from extraction_pipeline.ingest import ingest, DEFAULT_DPI
from extraction_pipeline.layout import analyze_page, engine_name
from extraction_pipeline.vlm_regions import (
    interpret_region,
    needs_vlm,
    DEFAULT_CONF_THRESHOLD,
)
from extraction_pipeline.reconcile import build_document
from extraction_pipeline.export import write_outputs
from extraction_pipeline.schema import PageResult, DocumentResult

_CACHE_DIR = Path("./cache/extraction")


def _cache_key(path: Path, use_vlm: bool, conf_threshold: float, dpi: int) -> Path:
    digest = hashlib.md5(path.read_bytes()).hexdigest()
    tag = f"{digest}_vlm{int(use_vlm)}_c{conf_threshold}_d{dpi}"
    return _CACHE_DIR / f"{path.stem}_{tag}.json"


def run(
    file_path: str | Path,
    out_dir: str | Path = "extraction_output",
    use_vlm: bool = True,
    conf_threshold: float = DEFAULT_CONF_THRESHOLD,
    dpi: int = DEFAULT_DPI,
    use_cache: bool = True,
    write_files: bool = True,
) -> tuple[DocumentResult, list[np.ndarray], dict[str, Path]]:
    """Process a document end-to-end.

    Returns ``(document_result, page_images, artifact_paths)``. ``page_images``
    is always returned (re-ingested on cache hits) so callers can render overlays.
    """
    path = Path(file_path)
    pages = ingest(path, dpi=dpi)
    images = [img for _, img in pages]

    doc: DocumentResult | None = None
    cache_file = None
    if use_cache:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = _cache_key(path, use_vlm, conf_threshold, dpi)
        if cache_file.exists():
            doc = DocumentResult.model_validate_json(
                cache_file.read_text(encoding="utf-8")
            )

    if doc is None:
        page_results: list[PageResult] = []
        for idx, img in pages:
            regions = analyze_page(img, idx)
            if use_vlm:
                regions = [
                    interpret_region(img, r) if needs_vlm(r, conf_threshold) else r
                    for r in regions
                ]
            h, w = img.shape[:2]
            page_results.append(
                PageResult(page=idx, width=int(w), height=int(h), regions=regions)
            )

        doc = build_document(path.name, page_results)
        if use_cache and cache_file is not None:
            cache_file.write_text(doc.model_dump_json(indent=2), encoding="utf-8")

    artifacts: dict[str, Path] = {}
    if write_files:
        artifacts = write_outputs(doc, out_dir, images=images)

    return doc, images, artifacts


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Document Intelligence extraction & structuring pipeline."
    )
    parser.add_argument("file", help="PDF or image file to process.")
    parser.add_argument("--out", default="extraction_output", help="Output directory.")
    parser.add_argument(
        "--no-vlm",
        action="store_true",
        help="Disable Gemini region interpretation (OCR only).",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=DEFAULT_CONF_THRESHOLD,
        help="OCR confidence below which text regions are escalated to the VLM.",
    )
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="PDF raster DPI.")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cache.")
    args = parser.parse_args()

    print(f"Layout/OCR engine: {engine_name()}")
    doc, _images, artifacts = run(
        args.file,
        out_dir=args.out,
        use_vlm=not args.no_vlm,
        conf_threshold=args.conf,
        dpi=args.dpi,
        use_cache=not args.no_cache,
    )

    print(f"Pages: {len(doc.pages)}  Regions: {doc.region_count}")
    by_engine: dict[str, int] = {}
    for r in doc.all_regions():
        by_engine[r.source_engine] = by_engine.get(r.source_engine, 0) + 1
    print(f"Regions by engine: {by_engine}")
    print("Artifacts:")
    for name, p in artifacts.items():
        print(f"  {name}: {p}")


if __name__ == "__main__":
    _main()
