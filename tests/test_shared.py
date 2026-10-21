"""Unit tests for the ``shared`` helper module.

Covers the pure file-management helpers (naming, formatting, listing,
deletion) every screen relies on. Uses the same minimal environment as the
rest of the suite: no streamlit, no heavy deps — only the stdlib and the
``shared`` module itself.

Runnable with plain Python (``python -m tests.test_shared``) or pytest.
"""

import os

import conftest
import shared as sh


def test_ensure_dir_creates_missing_directory():
    conftest.setup_isolated_uploads([])
    target = os.path.join(sh.UPLOAD_DIR, "nested", "dir")
    result = sh.ensure_dir(target)
    assert os.path.isdir(target)
    assert result == target


def test_safe_name_strips_path_components():
    assert sh.safe_name("a/b/c.txt") == "c.txt"
    assert sh.safe_name("plain.txt") == "plain.txt"


def test_safe_name_falls_back_for_blank():
    assert sh.safe_name("") == "unnamed"
    assert sh.safe_name(None) == "unnamed"
    assert sh.safe_name("   ") == "unnamed"


def test_unique_name_returns_input_when_absent():
    conftest.setup_isolated_uploads([])
    assert sh.unique_name("fresh.txt") == "fresh.txt"


def test_unique_name_suffixes_on_collision():
    conftest.setup_isolated_uploads(["dup.txt"])
    result = sh.unique_name("dup.txt")
    assert result != "dup.txt"
    assert result.startswith("dup.")
    assert result.endswith(".txt")
    # The rewritten name must not already exist on disk.
    assert not os.path.exists(os.path.join(sh.UPLOAD_DIR, result))


def test_unique_name_without_extension():
    conftest.setup_isolated_uploads(["README"])
    result = sh.unique_name("README")
    assert result != "README"
    assert not os.path.exists(os.path.join(sh.UPLOAD_DIR, result))


def test_fmt_size_units():
    assert sh.fmt_size(5) == "5 B"
    assert sh.fmt_size(1023) == "1023 B"
    assert sh.fmt_size(1024) == "1.0 KB"
    assert sh.fmt_size(2 * 1024 * 1024) == "2.0 MB"
    assert sh.fmt_size(3 * 1024 ** 3) == "3.0 GB"


def test_list_upload_files_ignores_hidden_and_dirs():
    conftest.setup_isolated_uploads(["a.txt", "b.txt"])
    # Add a hidden file and a subdirectory — both must be excluded.
    with open(os.path.join(sh.UPLOAD_DIR, ".hidden"), "w") as f:
        f.write("x")
    os.makedirs(os.path.join(sh.UPLOAD_DIR, "subdir"))

    rows = sh.list_upload_files()
    assert {r["name"] for r in rows} == {"a.txt", "b.txt"}
    for r in rows:
        assert set(r.keys()) == {"name", "size", "modified"}
        assert r["size"] == 7  # len("content") written by setup helper


def test_list_upload_files_empty_dir():
    conftest.setup_isolated_uploads([])
    assert sh.list_upload_files() == []


def test_delete_file_existing():
    conftest.setup_isolated_uploads(["gone.txt", "keep.txt"])
    assert sh.delete_file("gone.txt") is True
    assert not os.path.exists(os.path.join(sh.UPLOAD_DIR, "gone.txt"))
    assert os.path.exists(os.path.join(sh.UPLOAD_DIR, "keep.txt"))


def test_delete_file_missing():
    conftest.setup_isolated_uploads(["keep.txt"])
    assert sh.delete_file("nope.txt") is False


def test_delete_dir():
    conftest.setup_isolated_uploads([])
    sub = os.path.join(sh.UPLOAD_DIR, "tree")
    os.makedirs(os.path.join(sub, "inner"))
    with open(os.path.join(sub, "inner", "leaf.txt"), "w") as f:
        f.write("x")
    assert sh.delete_dir("tree") is True
    assert not os.path.exists(sub)


def test_delete_dir_missing():
    conftest.setup_isolated_uploads([])
    assert sh.delete_dir("no-such-dir") is False


def test_cleanup_dir_never_raises():
    conftest.setup_isolated_uploads([])
    sub = os.path.join(sh.UPLOAD_DIR, "temp")
    os.makedirs(sub)
    sh.cleanup_dir(sub)  # should not raise
    assert not os.path.exists(sub)
    sh.cleanup_dir(os.path.join(sh.UPLOAD_DIR, "already-gone"))  # should not raise


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("PASS:", fn.__name__)
    print(f"\nAll {len(fns)} tests passed.")
