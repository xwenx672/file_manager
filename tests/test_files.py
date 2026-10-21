"""Regression tests for the Files screen "Delete all" behaviour (issue #7).

Contract: clicking "Delete all files" must (a) remove every file from the
uploads directory and (b) clear the sidebar upload box so the stale selection
does not linger. The clear is signalled by a ``clear_uploader`` flag in
session state that ``app._apply_pending_clear`` consumes *before* the
``file_uploader`` widget is instantiated on the rerun.

Runnable with plain Python (``python -m tests.test_files``) or pytest.
No pytest requirement and no heavy streamlit deps (streamlit is stubbed by
``conftest``).
"""

import conftest
import shared as sh
import streamlit as st


def test_delete_all_removes_every_file():
    conftest.setup_isolated_uploads(["a.txt", "b.txt", "c.txt"])
    from _screen_files import _delete_all

    removed = _delete_all()
    assert sorted(removed) == ["a.txt", "b.txt", "c.txt"]
    assert sh.list_upload_files() == []


def test_delete_all_sets_clear_flag():
    """The flag is what lets app.py clear the sidebar upload box (issue #7)."""
    conftest.setup_isolated_uploads(["a.txt"])
    st.session_state.clear()
    from _screen_files import _delete_all

    _delete_all()
    assert st.session_state.get("clear_uploader") is True


def test_apply_pending_clear_resets_uploader():
    """Simulates the rerun right after "Delete all" set the flag: the
    widget's selection is dropped and the dedupe tracker is reset so a
    re-upload of the same names is accepted again.
    """
    import app

    st.session_state.clear()
    st.session_state["clear_uploader"] = True
    st.session_state["uploader"] = ["a.txt", "b.txt"]
    st.session_state["last_upload"] = ("a.txt", "b.txt")

    assert app._apply_pending_clear() is True
    assert "uploader" not in st.session_state
    assert st.session_state["last_upload"] == ()
    assert "clear_uploader" not in st.session_state


def test_apply_pending_clear_noop_without_flag():
    """A normal render must not touch the uploader selection."""
    import app

    st.session_state.clear()
    st.session_state["uploader"] = ["a.txt"]
    st.session_state["last_upload"] = ("a.txt",)

    assert app._apply_pending_clear() is False
    assert st.session_state["uploader"] == ["a.txt"]
    assert st.session_state["last_upload"] == ("a.txt",)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("PASS:", fn.__name__)
    print(f"\nAll {len(fns)} tests passed.")
