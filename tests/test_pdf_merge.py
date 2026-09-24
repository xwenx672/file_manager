"""Regression tests for ``_screen_pdf_merge._sorted_pdf_names``.

Contract captured by these tests: ``sh.list_upload_files()`` returns a list of
``{name, size, modified}`` dicts; ``_sorted_pdf_names`` must turn that dict-form
input into a sorted list of *strings*, filtering to ``.pdf`` files and hiding
dot-files. Applying ``.lower()`` directly to the dicts raised
``AttributeError: 'dict' object has no attribute 'lower'`` (see
https://github.com/xwenx672/file_manager/issues/5).

Runnable with plain Python (``python -m tests.test_pdf_merge``) or pytest.
No pytest requirement and no heavy streamlit/PyPDF2 deps.
"""

import conftest


def _sorted_names():
    from _screen_pdf_merge import _delete_pdf, _sorted_pdf_names
    return sorted(_sorted_pdf_names() or [])


def test_no_pdf_files_returns_empty_list():
    conftest.setup_isolated_uploads([])
    assert _sorted_names() == []


def test_returns_list_of_strings_from_dict_input():
    """Regression guard: dict input must not raise, and names come back as str."""
    conftest.setup_isolated_uploads(["a.pdf", "b.pdf", "notes.txt", "photo.jpg"])
    names = _sorted_names()
    assert names == ["a.pdf", "b.pdf"]
    assert all(isinstance(n, str) for n in names)


def test_non_pdf_files_filtered_out():
    conftest.setup_isolated_uploads(["c.pdf", "z.txt", "x.png"])
    assert _sorted_names() == ["c.pdf"]


def test_hidden_and_backup_files_excluded():
    conftest.setup_isolated_uploads(["visible.pdf", ".hidden.pdf", "temp.pdf.bak"])
    assert _sorted_names() == ["visible.pdf"]


def test_pdf_prefix_case_insensitive():
    conftest.setup_isolated_uploads(["A.PDF", "b.Pdf"])
    assert _sorted_names() == ["A.PDF", "b.Pdf"]


def test_delete_pdf_removes_file_from_disk():
    """Regression guard for issue #6: "_delete_pdf" must actually remove the
    PDF from uploads/, not just drop it from the in-memory order list.
    """
    from _screen_pdf_merge import _delete_pdf

    conftest.setup_isolated_uploads(["keep.pdf", "gone.pdf"])
    missing = _delete_pdf("gone.pdf")
    assert missing is True
    # The file must no longer exist on disk.
    assert "gone.pdf" not in _sorted_names()
    # The sibling file must still be present.
    assert "keep.pdf" in _sorted_names()


def test_delete_pdf_missing_returns_false():
    """Deleting a filename that is not present must return False (no crash)."""
    from _screen_pdf_merge import _delete_pdf

    conftest.setup_isolated_uploads(["keep.pdf"])
    assert _delete_pdf("nope.pdf") is False
    assert _sorted_names() == ["keep.pdf"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print("PASS:", fn.__name__)
        passed += 1
    print(f"\nAll {passed} tests passed.")
