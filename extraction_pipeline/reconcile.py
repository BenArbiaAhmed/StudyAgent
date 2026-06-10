"""Reconciliation: order, deduplicate and merge regions into coherent Markdown.

Takes the per-page regions produced by layout + VLM stages and:
- sorts them into human reading order (column-aware),
- drops regions that are duplicated/contained within another (keeping the
  higher-confidence or VLM-refined one),
- renders each region to Markdown and concatenates pages into one document.
"""

from __future__ import annotations

from extraction_pipeline.schema import Region, PageResult, DocumentResult

_CONTAINMENT_THRESHOLD = 0.7


# --------------------------------------------------------------------------- #
# Geometry
# --------------------------------------------------------------------------- #
def _intersection_area(a: list[float], b: list[float]) -> float:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def _containment(inner: Region, outer: Region) -> float:
    """Fraction of ``inner`` covered by ``outer`` (0..1)."""
    if inner.area <= 0:
        return 0.0
    return _intersection_area(inner.bbox, outer.bbox) / inner.area


# --------------------------------------------------------------------------- #
# Dedup
# --------------------------------------------------------------------------- #
def _engine_rank(region: Region) -> int:
    return 1 if region.source_engine == "gemini" else 0


def dedup(regions: list[Region]) -> list[Region]:
    """Drop regions largely contained within another region.

    When two regions overlap heavily, keep the one preferred by
    ``(VLM-refined, higher confidence, larger area)``.
    """
    kept: list[Region] = []
    discarded: set[int] = set()
    for i, ri in enumerate(regions):
        if i in discarded:
            continue
        for j, rj in enumerate(regions):
            if i == j or j in discarded:
                continue
            if _containment(rj, ri) >= _CONTAINMENT_THRESHOLD:
                # rj sits inside ri; decide which to drop.
                key_i = (_engine_rank(ri), ri.confidence, ri.area)
                key_j = (_engine_rank(rj), rj.confidence, rj.area)
                if key_i >= key_j:
                    discarded.add(j)
                else:
                    discarded.add(i)
                    break
        if i not in discarded:
            kept.append(ri)
    return kept


# --------------------------------------------------------------------------- #
# Reading order
# --------------------------------------------------------------------------- #
def _is_two_column(regions: list[Region], page_width: int) -> bool:
    if len(regions) < 4 or page_width <= 0:
        return False
    mid = page_width / 2.0
    left = sum(1 for r in regions if (r.bbox[0] + r.bbox[2]) / 2 < mid)
    right = len(regions) - left
    # Both sides reasonably populated and few regions straddle the centre.
    straddle = sum(1 for r in regions if r.bbox[0] < mid < r.bbox[2])
    return left >= 2 and right >= 2 and straddle <= len(regions) * 0.25


def reading_order(regions: list[Region], page_width: int) -> list[Region]:
    """Sort regions into reading order, handling simple two-column layouts."""
    if not regions:
        return []

    if _is_two_column(regions, page_width):
        mid = page_width / 2.0
        left = [r for r in regions if (r.bbox[0] + r.bbox[2]) / 2 < mid]
        right = [r for r in regions if (r.bbox[0] + r.bbox[2]) / 2 >= mid]
        left.sort(key=lambda r: (r.bbox[1], r.bbox[0]))
        right.sort(key=lambda r: (r.bbox[1], r.bbox[0]))
        return left + right

    return sorted(regions, key=lambda r: (r.bbox[1], r.bbox[0]))


# --------------------------------------------------------------------------- #
# Markdown rendering
# --------------------------------------------------------------------------- #
def render_region(region: Region) -> str:
    md = (region.markdown or "").strip()
    if not md:
        return ""
    if region.type == "title" and not md.lstrip().startswith("#"):
        return f"## {md}"
    return md


def render_page(page: PageResult) -> str:
    parts = [render_region(r) for r in page.regions]
    return "\n\n".join(p for p in parts if p)


def reconcile_page(page: PageResult, page_width: int) -> PageResult:
    """Dedup + order a single page's regions in place and return it."""
    regions = dedup(page.regions)
    regions = reading_order(regions, page_width)
    # Re-id in final reading order for stable, sequential ids.
    for idx, r in enumerate(regions):
        r.id = f"p{page.page + 1}-r{idx:02d}"
    page.regions = regions
    return page


def build_document(source: str, pages: list[PageResult]) -> DocumentResult:
    """Reconcile every page and assemble the consolidated document Markdown."""
    reconciled: list[PageResult] = []
    for page in pages:
        reconciled.append(reconcile_page(page, page.width))

    chunks: list[str] = []
    multipage = len(reconciled) > 1
    for page in reconciled:
        body = render_page(page)
        if multipage:
            chunks.append(f"<!-- page {page.page + 1} -->\n\n{body}")
        else:
            chunks.append(body)
    markdown = "\n\n---\n\n".join(c for c in chunks if c.strip())

    return DocumentResult(source=source, pages=reconciled, markdown=markdown)
