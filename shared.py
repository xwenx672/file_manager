"""Shared helpers for the file-manager ScreenFlow application.

This module is imported by every screen (files, PDF merge, MP3 transcription)
so behaviour stays consistent: where files live, how they are named, and the
small collection of file-management helpers.
"""

from __future__ import annotations

import os
import shutil
import uuid


# All generated/processed files are written next to user uploads so the
# docker-compose volume mount persists them and they show up in the Files tab.
UPLOAD_DIR = "/uploads"

# Where temporary work products (converted audio, PDFs mid-merge) are staged.
# Keeps the uploads root clean; these are always cleaned up by the owner.
WORK_DIR = "/tmp/filemanager"


def ensure_dir(path: str) -> str:
    """Create ``path`` if it does not exist and return it."""
    os.makedirs(path, exist_ok=True)
    return path


def safe_name(name: str) -> str:
    """Return a filesystem-safe basename for a filename."""
    base = os.path.basename(name or "") or "unnamed"
    base = os.path.normpath(base)
    if os.sep in base or os.altsep in base:
        base = base.split(os.sep)[-1]
    return base or "unnamed"


def unique_name(name: str) -> str:
    """Return ``name`` rewritten so it will not collide if it already exists.

    A 6-char suffix is inserted before the extension so a repeated upload of the
    same filename still lands in its own file rather than overwriting.
    """
    name = safe_name(name)
    if not os.path.exists(os.path.join(UPLOAD_DIR, name)):
        return name
    base, ext = os.path.splitext(name)
    suffix = uuid.uuid4().hex[:6]
    return f"{base}.{suffix}{ext}"


def fmt_size(n: float) -> str:
    """Format a byte count as a human string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def list_upload_files() -> list[dict]:
    """Return a list of ``{name, size, modified}`` dicts for uploads/.

    No hidden files, no directories. Sorting is purely cosmetic; the
    production order of PDFs comes from the user in the PDF screen.
    """
    if not os.path.isdir(UPLOAD_DIR):
        return []
    rows = []
    for fn in os.listdir(UPLOAD_DIR):
        if fn.startswith("."):
            continue
        p = os.path.join(UPLOAD_DIR, fn)
        if os.path.isfile(p):
            rows.append(
                {
                    "name": fn,
                    "size": os.path.getsize(p),
                    "modified": _modified(p),
                }
            )
    return rows


def _modified(path: str) -> str:
    import datetime

    return datetime.datetime.fromtimestamp(
        os.path.getmtime(path)
    ).strftime("%Y-%m-%d %H:%M:%S")


def delete_file(name: str) -> bool:
    """Delete a single file from uploads/. Returns True successfully."""
    p = os.path.join(UPLOAD_DIR, name)
    if not os.path.isfile(p):
        return False
    try:
        os.remove(p)
    except OSError:
        return False
    return True


def delete_dir(name: str) -> bool:
    """Delete a directory tree from uploads/."""
    p = os.path.join(UPLOAD_DIR, name)
    if not os.path.isdir(p):
        return False
    try:
        shutil.rmtree(p)
    except OSError:
        return False
    return True


def cleanup_dir(name: str) -> None:
    """Best-effort removal of a workspace directory. Never raises."""
    try:
        shutil.rmtree(name)
    except OSError:
        pass
