"""file-manager — entry point and navigation.

ScreenFlow app (single Streamlit app). Screens are registered here and each a
module in this package:

    shared.py                      shared helpers (paths, naming, formatting)
    _screen_files.py               original file uploader
    _screen_pdf_merge.py           merge uploaded PDFs in a user-chosen order
    _screen_mp3_transcribe.py      transcribe uploaded mp3s (word-level marking)

Each screen module exposes ``render()`` and ``label`` (shown in the sidebar).
"""

from __future__ import annotations

import os

import streamlit as st

from shared import UPLOAD_DIR, WORK_DIR, ensure_dir, unique_name

# (screen_module, human label)
SCREENS = [
    ("_screen_files", "📁 Files"),
    ("_screen_pdf_merge", "📄 PDF Merge"),
    ("_screen_mp3_transcribe", "🎙️ MP3 Transcribe"),
]


def _activate(label: str) -> bool:
    return st.session_state.get("scr") == label


def main() -> None:
    ensure_dir(UPLOAD_DIR)
    ensure_dir(WORK_DIR)

    st.set_page_config(page_title="file-manager", page_icon="📁", layout="wide")

    st.title("📁 file-manager")

    # Sidebar screen selector. Created exactly once (not once per screen).
    active = st.sidebar.radio(
        "Screen",
        [label for _, label in SCREENS],
        index=0,
        key="scr",
        format_func=lambda x: x,
    )

    screen_name = next(name for name, shown in SCREENS if shown == active)

    # Sidebar file uploader persists files across every screen. Streamlit holds
    # the last selection and re-fires this block on the rerun that a
    # delete-triggered st.rerun() causes, which would otherwise re-write the
    # same files onto a freshly-wiped directory. We only write on a genuine
    # change to the selection, so a re-sent identical upload is ignored.
    last_selected = st.session_state.setdefault("last_upload", ())
    uploaded = st.sidebar.file_uploader(
        "Upload files", accept_multiple_files=True, key="uploader"
    )
    if uploaded:
        names = tuple(up.name for up in uploaded)
        if names != last_selected:
            to_save = []
            for up in uploaded:
                target = unique_name(up.name)
                to_save.append((up, target))
            for up, target in to_save:
                with open(os.path.join(UPLOAD_DIR, target), "wb") as f:
                    f.write(up.getbuffer())
            st.session_state["last_upload"] = names
            st.success(
                f"{len(to_save)} file(s) saved: "
                f"{', '.join(t for _, t in to_save)}"
            )

    import importlib

    mod = importlib.import_module(screen_name)
    with st.container():
        mod.render()

    st.sidebar.markdown("---")
    st.caption("file-manager")


if __name__ == "__main__":
    main()
