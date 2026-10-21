# 📁 file-manager

A small Streamlit app for managing files in the browser: upload files,
list/delete them, merge PDFs in a user-chosen order, and transcribe audio
locally with faster-whisper (uncertain words marked, optional Ollama repair
pass).

## Screens

| Screen | What it does |
| --- | --- |
| 📁 **Files** | Live listing of everything in `uploads/` (name, size, modified) plus a **Delete all** button that also clears the sidebar upload box. |
| 📄 **PDF Merge** | Arrange uploaded PDFs with ▲ / ▼ / ✕ row controls, then merge and download one combined PDF. Unreadable files are skipped with a warning. |
| 🎙️ **MP3 Transcribe** | Transcribes audio locally with faster-whisper (`large-v3`, int8/CPU, VAD on). Words the model is unsure of (word probability < 0.6) are flagged `*word` in the "Marked version"; an optional button asks a local Ollama model to repair them. If Ollama is unavailable the transcript still succeeds and the guesses stay marked. |

## Layout

```
app.py                     entry point, sidebar navigation + shared uploader
shared.py                  shared helpers (paths, naming, listing, deletion)
_screen_files.py           Files screen
_screen_pdf_merge.py       PDF Merge screen
_screen_mp3_transcribe.py  MP3 Transcribe screen
conftest.py                test env: streamlit stub + isolated uploads dir
tests/                     test suite (runs without streamlit/whisper)
Dockerfile                 python:3.12-slim + ffmpeg + deps, port 8501
```

Uploaded files land in `uploads/` (or the mounted volume); intermediate
work products are staged in `/tmp/filemanager`.

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

## Running in Docker

```bash
docker build -t file-manager .
docker run --rm -p 8501:8501 -v "$(pwd)/uploads:/uploads" file-manager
```

Notes:

- The volume mount is what makes uploads survive container recreation.
- The whisper model (~3 GB for `large-v3`) downloads on first transcription
  into the container layer. For durability bind-mount the Hugging Face cache
  as well, e.g. `-v hf-cache:/root/.cache/huggingface`.
- The Ollama repair button expects a local Ollama at
  `http://localhost:11434` with the `hermes3` model; without it,
  transcription still works — uncertain words just stay marked.

## Tests

The suite is deliberately light: `conftest.py` stubs Streamlit (a dict-backed
`session_state` + no-op `rerun`) and points `shared.UPLOAD_DIR` at a temp
dir, so only `PyPDF2` is needed:

```bash
pip install PyPDF2
python -m tests.test_shared
python -m tests.test_pdf_merge
python -m tests.test_files
```

or `pip install pytest && pytest`. The same three modules run in CI
(`.github/workflows/tests.yml`).
