"""PDF merge screen (feature #1).

Upload several PDFs, arrange them in the order you want to merge, then download
one merged PDF.

Order is a SessionState list (so it survives Streamlit's reruns) initialised from
the uploaded PDF files on first load. The user reorganises it with per-row
"Move up" / "Move down" controls and can exclude a file with "Remove". "Merge &
download" writes the merged result into WORK_DIR and offers a download button.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import streamlit as st

import shared as sh
from PyPDF2 import PdfReader, PdfWriter


def _sorted_pdf_names() -> list[str]:
    """PDF file names in uploads, sorted, excluding hidden/temp files.

    ``sh.list_upload_files()`` returns a list of ``{name, size, modified}``
    dicts, not filenames, so destructure each row to its ``name`` before the
    ``.lower()`` filter. Applying ``.lower()`` directly to a dict raised
    ``AttributeError`` (see https://github.com/xwenx672/file_manager/issues/5).
    """
    if not os.path.isdir(sh.UPLOAD_DIR):
        return []
    return sorted(
        row["name"]
        for row in sh.list_upload_files()
        if row["name"].lower().endswith(".pdf") and not row["name"].startswith(".")
    )


def _ensure_order() -> list[str]:
    key = "pdf_merge_order"
    order = st.session_state.get(key)
    if not isinstance(order, list):
        st.session_state[key] = _sorted_pdf_names()
        return list(st.session_state[key])
    existing = set(_sorted_pdf_names())
    # Add any PDFs that were uploaded since last render...
    for fn in existing:
        if fn not in order:
            st.session_state[key].append(fn)
    # ...and drop any that were removed from uploads.
    st.session_state[key] = [fn for fn in order if fn in existing]
    return st.session_state[key]


def _merge_pdfs(order: list[str], out_path: str) -> Optional[str]:
    """Merge each file's pages into ``out_path``.

    Returns the path that was written, or ``None`` if nothing could be added
    (every file was unreadable or empty). Callers writing to the output file
    must check for ``None`` first — the writer only outputs an on-disk file
    when a merge actually happens; otherwise ``out_path`` does not exist.
    """
    writer: "PdfWriter" = PdfWriter()
    added = 0
    for fn in order:
        try:
            reader = PdfReader(os.path.join(sh.UPLOAD_DIR, fn))
            added += len(reader.pages)
        except Exception as exc:
            st.warning(f"Skipped '{fn}': {exc}")
            continue
        if not reader.pages:
            st.warning(f"Skipped '{fn}': no readable pages.")
            continue
        for page in reader.pages:
            writer.add_page(page)
    if added == 0:
        st.warning("Nothing to merge — every file was empty or unreadable.")
        return None
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def _pdf_list_ui(order: list[str]) -> list[str]:
    ordered = order[:]
    n = len(ordered)

    if n == 0:
        st.info("No PDFs uploaded yet. Upload PDFs (sidebar), they will appear here.")
        st.rerun()
        return ordered

    st.caption("Step 1 — arrange the order below, then Merge & download (Step 2).")
    for i, fn in enumerate(ordered):
        cols = st.columns([44, 8, 8, 8, 18])
        with cols[0]:
            st.markdown(f"**{i + 1}.** {fn}")
        with cols[1]:
            move_up = st.button("▲", key=f"up_{i}", disabled=i == 0)
        with cols[2]:
            move_down = st.button("▼", key=f"dn_{i}", disabled=i == n - 1)
        with cols[3]:
            from_merge = st.button("✕", key=f"rm_{i}")
        if move_up and i < n - 1:
            ordered[i], ordered[i - 1] = ordered[i - 1], ordered[i]
            st.session_state["pdf_merge_order"] = ordered
            st.rerun()
        if move_down and i > 0:
            ordered[i], ordered[i + 1] = ordered[i + 1], ordered[i]
            st.session_state["pdf_merge_order"] = ordered
            st.rerun()
        if from_merge:
            st.session_state["pdf_merge_order"] = [x for x in ordered if x != fn]
            st.rerun()
    return ordered


def _merge_button(order: list[str]) -> list[str]:
    if not order:
        return order
    if st.button("📎 Merge & download", type="primary"):
        ts = time.strftime("%Y%m%d-%H%M%S")
        out_path = os.path.join(sh.WORK_DIR, f"merged-{ts}.pdf")
        with st.spinner("Merging PDFs…"):
            try:
                result = _merge_pdfs(order, out_path)
            except Exception as exc:
                st.error(f"Merge failed: {exc}")
                return order

        if not result:
            # Nothing was written — every file was unreadable or empty.
            # Returning early avoids os.path.getsize() on a file that does
            # not exist (FileNotFoundError) and stops the UI claiming a
            # success the download button can never deliver.
            return order

        size = os.path.getsize(result)
        st.success(
            f"Merged {len(order)} PDF in one file. (|{size}B|)"
        )
        st.download_button(
            "⬇️ Download merged.pdf",
            data=result,
            file_name="merged.pdf",
            mime="application/pdf",
        )
    return order


def render() -> None:
    st.subheader("📄 PDF Merge")

    existing = _sorted_pdf_names()
    if not existing:
        st.info(
            "No PDFs in uploads yet. Use the sidebar uploader; this list will "
            "auto-refresh (or press **Refresh**)."
        )
        st.rerun()
        return

    order = _ensure_order()
    new_order = _pdf_list_ui(order)
    _merge_button(new_order)
    if new_order != order and new_order:
        st.caption(f"Final merge order: {' → '.join(new_order)}")
