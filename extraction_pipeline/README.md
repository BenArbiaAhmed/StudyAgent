# Document Intelligence — Extraction & Structuring Pipeline

An end-to-end pipeline that turns heterogeneous, scanned/image-based and
partially-handwritten documents into **clean, structured Markdown** with
**traceable regions, coordinates and confidence scores**.

This module is self-contained and can run as a CLI or via its Streamlit page
(`pages/1_Document_Extraction.py`). Its Markdown output can optionally be fed
into the wider Study Agent's RAG flow.

## Approach

```
ingest → layout + OCR → VLM region interpretation → reconcile → export
```

| Stage | File | What it does |
|-------|------|--------------|
| Ingest | `ingest.py` | PDFs (digital or scanned) rasterized with PyMuPDF; PNG/JPG/TIFF/BMP/WEBP loaded directly. Output: list of `(page_index, RGB image)`. |
| Layout + OCR | `layout.py` | Detects layout regions (text/title/table/figure/list/...) with pixel bounding boxes and OCR confidence. |
| VLM interpretation | `vlm_regions.py` | Crops non-textual regions (tables, figures, stamps, equations) and low-confidence text (handwriting / poor scans) and sends them to **Gemini** for Markdown transcription + a model-estimated confidence. |
| Reconcile | `reconcile.py` | Orders regions into reading order (column-aware), drops duplicate/contained regions, and concatenates everything into one coherent document. |
| Export | `export.py` | Writes `<name>.md` (with per-region traceability comments), `<name>.regions.json` (full structured data), and annotated overlay PNGs. |
| Orchestrate | `pipeline.py` | Wires the stages together with MD5-based caching. CLI entry point. |

## Design choices

- **Hybrid engine (PaddleOCR + Gemini), per the offer's constraints.** Traditional
  OCR/layout (PaddleOCR PP-Structure) gives real bounding boxes and genuine OCR
  confidence; Gemini (a hard project constraint) interprets the regions OCR
  cannot — figures, tables, stamps, diagrams, handwriting.
- **Confidence-gated VLM escalation.** Text regions whose OCR confidence falls
  below a threshold (default `0.80`) are re-read by Gemini. This targets exactly
  the handwriting / low-quality-scan cases while keeping cost down on clean text.
- **Graceful degradation.** `layout.py` resolves the best available engine at
  runtime: PaddleOCR PP-Structure first, falling back to the already-installed,
  dependency-light **RapidOCR** (onnxruntime). The pipeline always produces
  coordinates and confidence regardless of which engine is available.
- **Two kinds of confidence, never conflated.** Regions carry `source_engine`.
  `paddleocr`/`rapidocr` confidence is real OCR probability; `gemini` confidence
  is *model-estimated* and labelled as such.
- **Traceability by construction.** Every `Region` has `id`, `page`, `bbox`,
  `confidence`, `source_engine`. These are embedded as invisible HTML comments
  before each block in the Markdown and duplicated in full in the JSON sidecar,
  so any line of output can be traced back to a pixel region on a page.

## Setup

Use **Python 3.11 or 3.12** — several binary dependencies (`pydantic-core`,
`paddlepaddle`, `onnxruntime`, `pymupdf`) do not yet ship wheels for 3.14.

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`GOOGLE_API_KEY` must be set (in `.env`) for the Gemini VLM stage.

## Usage

### CLI
```bash
python -m extraction_pipeline.pipeline path/to/document.pdf
python -m extraction_pipeline.pipeline scan.png --out results --no-vlm
python -m extraction_pipeline.pipeline form.tiff --conf 0.85 --dpi 300
```
Outputs land in `extraction_output/` (or `--out`): `*.md`, `*.regions.json`,
`*.pN.overlay.png`.

### Streamlit
```bash
streamlit run main.py
```
Open the **Document Extraction** page in the sidebar, upload a document, and
inspect segmented pages, the region table (coordinates + confidence), the
rendered Markdown, and download the artifacts.

### Programmatic
```python
from extraction_pipeline.pipeline import run

doc, images, artifacts = run("scan.png", use_vlm=True)
print(doc.markdown)          # consolidated Markdown
print(doc.region_count)      # number of traced regions
```

## Output schema (`schema.py`)

`DocumentResult` → `PageResult[]` → `Region[]`, where each `Region` is:

```json
{
  "id": "p1-r03",
  "page": 0,
  "type": "table",
  "bbox": [120.0, 340.0, 980.0, 610.0],
  "confidence": 0.92,
  "source_engine": "gemini",
  "markdown": "| ... | ... |",
  "ocr_text": null
}
```

## Requirements coverage (internship offer)

| Requirement | Status |
|-------------|--------|
| Read text from scanned / image documents | ✅ ingest + OCR |
| Interpret non-text regions via VLM | ✅ `vlm_regions.py` (Gemini) |
| Detect & segment layout regions | ✅ `layout.py` (PP-Structure) |
| Process / merge / reconcile regions | ✅ `reconcile.py` |
| Persist clean structured Markdown | ✅ `export.py` |
| Traceable regions / coordinates / confidence | ✅ ids + bbox + scores in MD & JSON |
| PaddleOCR (or equivalent) | ✅ PaddleOCR, RapidOCR fallback |
| Gemini models (constraint) | ✅ region interpretation |

## Notes / limitations

- PaddleOCR/PaddlePaddle can be awkward to install on Windows; the RapidOCR
  fallback keeps the pipeline functional (text regions only, no figure/table
  typing). Install PaddleOCR for full layout typing.
- Two-column reading-order detection is a simple heuristic; complex multi-column
  or rotated layouts may need refinement.
- Gemini-estimated confidence is not a calibrated probability.
