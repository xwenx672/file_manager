"""Original file uploader screen.

Lists every file in the shared uploads directory, shows size/modified, and lets
the user delete individual files or clear everything. The sidebar ``file_uploader``
is what actually persists new uploads; this screen is then a live view.
"""

from __future__ import annotations

import os

import streamlit as st

import shared as sh


def render() -> None:
    st.subheader("📁 Files in uploads")

    files = sh.list_upload_files()
    if files:
        df = [
            (f["name"], sh.fmt_size(f["size"]), f["modified"]) for f in files
        ]
        st.dataframe(df, use_container_width=True, hide_index=True)
        total = sum(f["size"] for f in files)
        st.caption(f"{len(files)} files, {sh.fmt_size(total)} total")
    else:
        st.info("No files yet. Browse above (sidebar) and a file will appear here.")

    if st.button("🗑️ Delete all files"):
        for fn in _delete_all():
            st.warning(f"Deleted {fn}")
        # Re-render so the Files list clears to reflect the deletions.
        # We do NOT write to the "uploader" key in session_state: it is the
        # key of the sidebar file_uploader widget, and Streamlit forbids
        # mutating a widget's state after that widget has been instantiated.
        st.rerun()


def _delete_all() -> list[str]:
    removed = []
    try:
        for fn in os.listdir(sh.UPLOAD_DIR):
            p = os.path.join(sh.UPLOAD_DIR, fn)
            if os.path.isfile(p):
                try:
                    os.remove(p)
                    removed.append(fn)
                except OSError:
                    pass
    except OSError:
        pass
    return removed


if __name__ == "__main__":
    render()
