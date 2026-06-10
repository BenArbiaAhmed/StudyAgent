"""Input ingestion: normalize PDFs and image files into a list of page images.

PDFs (digital or scanned) are rasterized with PyMuPDF (already a project
dependency). Image files (PNG/JPG/TIFF/BMP/WEBP) are loaded directly. Output is
always a list of ``(page_index, rgb_ndarray)`` so the rest of the pipeline is
input-agnostic.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
PDF_SUFFIXES = {".pdf"}

# Rasterization DPI for PDF pages. 200 is a good accuracy/speed trade-off for OCR.
DEFAULT_DPI = 200


def _pdf_to_images(file_path: Path, dpi: int) -> list[np.ndarray]:
    import fitz  # PyMuPDF

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pages: list[np.ndarray] = []
    with fitz.open(file_path) as doc:
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            # Normalize to 3-channel RGB.
            if pix.n == 1:
                img = np.repeat(img, 3, axis=2)
            elif pix.n == 4:
                img = img[:, :, :3]
            pages.append(np.ascontiguousarray(img))
    return pages


def _image_to_array(file_path: Path) -> np.ndarray:
    from PIL import Image

    with Image.open(file_path) as im:
        return np.asarray(im.convert("RGB"))


def ingest(file_path: str | Path, dpi: int = DEFAULT_DPI) -> list[tuple[int, np.ndarray]]:
    """Load a document into ``[(page_index, rgb_image), ...]``.

    Raises ``ValueError`` for unsupported file types and ``FileNotFoundError``
    if the path does not exist.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix in PDF_SUFFIXES:
        images = _pdf_to_images(path, dpi)
    elif suffix in IMAGE_SUFFIXES:
        images = [_image_to_array(path)]
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            f"Supported: {sorted(PDF_SUFFIXES | IMAGE_SUFFIXES)}"
        )

    return list(enumerate(images))
