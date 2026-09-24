"""Pytest + standalone configuration for the file-manager tests.

The suite intentionally needs neither pytest nor the streamlit/PyPDF2 heavy
dependencies, so it can run the same way in CI and with a plain
``python -m tests.test_pdf_merge`` invocation.

It configures two things before any module under test is imported:

1. ``sh.UPLOAD_DIR`` points at an empty temporary directory, so the file
   helpers operate on throwaway files instead of the real ``/uploads``.
2. A minimal ``streamlit`` stub provides ``st.session_state`` (a dict-like
   object) and ``st.rerun`` (a no-op), because ``_screen_pdf_merge`` imports
   streamlit at module load but only touches session state during rendering.
"""

import os
import sys
import tempfile

# Ensure the project root (one level up from tests/) is importable.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FILES_ROOT = os.path.dirname(os.path.abspath(__file__))


def setup_isolated_uploads(file_names):
    """Populate ``sh.UPLOAD_DIR`` with ``file_names`` and return the filenames.

    The uploads dir is wiped first so repeated runs do not accumulate files
    left over from an earlier test.
    """
    import shutil
    if os.path.isdir(sh.UPLOAD_DIR):
        shutil.rmtree(sh.UPLOAD_DIR)
    os.makedirs(sh.UPLOAD_DIR, exist_ok=True)
    for name in file_names or []:
        with open(os.path.join(sh.UPLOAD_DIR, name), "w") as f:
            f.write("content")
    return list(file_names or [])


# --- Minimal streamlit stub: enough for the module to import and expose its
# --- pure helpers without pulling in the (heavy, unavailable) library.
if "streamlit" not in sys.modules:
    import types

    class SessionState(dict):
        pass

    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = SessionState()
    streamlit_stub.rerun = lambda *args, **kwargs: None
    sys.modules["streamlit"] = streamlit_stub


# --- Point the shared helpers at a throwaway uploads dir.
import shared as sh  # noqa: E402  (after sys.path / streamlit stub setup)

_temp_uploads = tempfile.mkdtemp(prefix="filemanager-test-")
os.makedirs(_temp_uploads, exist_ok=True)
sh.UPLOAD_DIR = _temp_uploads
