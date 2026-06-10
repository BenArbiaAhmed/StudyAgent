"""Streamlit page: Document Intelligence extraction pipeline demo.

Upload a scanned/image-based document or PDF, run the layout + VLM extraction
pipeline, and inspect the segmented regions, coordinates, confidence scores and
the consolidated Markdown output. Streamlit auto-discovers files in ``pages/``,
so this appears as a second page next to the main Study Agent chat.
"""

import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

from extraction_pipeline.pipeline import run
from extraction_pipeline.layout import engine_name
from extraction_pipeline.export import annotated_overlay, traceable_markdown
from tools.analyzer_tools.semantic_search import setup_rag_from_text

load_dotenv()

st.set_page_config(page_title="Document Extraction", layout="wide")
st.title("Document Intelligence — Extraction & Structuring")
st.caption(
    "Scanned / image documents → layout segmentation → VLM region interpretation "
    "→ reconciled, traceable Markdown."
)

SUPPORTED = ["pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"]

with st.sidebar:
    st.header("Pipeline settings")
    use_vlm = st.checkbox("Use Gemini VLM for non-text / low-confidence regions", True)
    conf_threshold = st.slider(
        "OCR confidence escalation threshold", 0.0, 1.0, 0.80, 0.05
    )
    dpi = st.select_slider("PDF raster DPI", options=[100, 150, 200, 300], value=200)
    use_cache = st.checkbox("Use cache", True)
    try:
        st.info(f"Layout/OCR engine: **{engine_name()}**")
    except Exception as e:  # noqa: BLE001
        st.warning(f"Engine not ready: {e}")

uploaded = st.file_uploader("Upload a document", type=SUPPORTED)

if uploaded and st.button("Run extraction", type="primary"):
    suffix = os.path.splitext(uploaded.name)[1] or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    try:
        with st.spinner("Running extraction pipeline..."):
            doc, images, _ = run(
                tmp_path,
                use_vlm=use_vlm,
                conf_threshold=conf_threshold,
                dpi=dpi,
                use_cache=use_cache,
                write_files=False,
            )
        # Keep results across reruns (e.g. download / send-to-RAG clicks).
        st.session_state["extraction_doc"] = doc
        st.session_state["extraction_images"] = images
        st.session_state["extraction_name"] = uploaded.name
    except Exception as e:  # noqa: BLE001
        st.error(f"Extraction failed: {e}")
    finally:
        os.remove(tmp_path)

doc = st.session_state.get("extraction_doc")
if doc is not None:
    images = st.session_state.get("extraction_images", [])
    name = st.session_state.get("extraction_name", "document")
    stem = os.path.splitext(name)[0]

    regions = doc.all_regions()
    by_engine: dict[str, int] = {}
    for r in regions:
        by_engine[r.source_engine] = by_engine.get(r.source_engine, 0) + 1

    c1, c2, c3 = st.columns(3)
    c1.metric("Pages", len(doc.pages))
    c2.metric("Regions", doc.region_count)
    c3.metric("VLM-interpreted", by_engine.get("gemini", 0))

    tab_overlay, tab_regions, tab_md = st.tabs(
        ["Segmented pages", "Regions (coords + confidence)", "Markdown output"]
    )

    with tab_overlay:
        for page in doc.pages:
            if page.page < len(images):
                st.image(
                    annotated_overlay(images[page.page], page),
                    caption=f"Page {page.page + 1} — {len(page.regions)} regions",
                    use_container_width=True,
                )

    with tab_regions:
        st.dataframe(
            [
                {
                    "id": r.id,
                    "page": r.page + 1,
                    "type": r.type,
                    "engine": r.source_engine,
                    "confidence": round(r.confidence, 3),
                    "bbox [x0,y0,x1,y1]": ", ".join(f"{v:.0f}" for v in r.bbox),
                }
                for r in regions
            ],
            use_container_width=True,
            hide_index=True,
        )

    with tab_md:
        st.markdown(doc.markdown)

    st.divider()
    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Download Markdown (traceable)",
        traceable_markdown(doc),
        file_name=f"{stem}.md",
        mime="text/markdown",
    )
    d2.download_button(
        "Download regions JSON",
        doc.model_dump_json(indent=2),
        file_name=f"{stem}.regions.json",
        mime="application/json",
    )
    if d3.button("Send to Study Agent (RAG)"):
        try:
            vs = setup_rag_from_text(
                document_text=doc.markdown,
                document_source=name,
                collection_name=stem.replace(".", "_"),
            )
            st.session_state["vector_store"] = vs
            st.session_state["pdf_content"] = doc.markdown
            st.session_state["current_file"] = name
            st.success("Sent to Study Agent — switch to the chat page to query it.")
        except Exception as e:  # noqa: BLE001
            st.error(f"Failed to index for RAG: {e}")
