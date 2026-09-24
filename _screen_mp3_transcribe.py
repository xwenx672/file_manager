"""MP3 transcribe screen.

Upload an audio file; it is transcribed with a local faster-whisper model.
Word-level recognition uncertainty is exposed as "marked" mode:

    words faster-whisper is fairly sure about  -> shown as plain  word
    faster-whisper is unsure about a word      -> shown as *[word], with a
                                                legend so the user knows the
                                                leading * means "guessed".

To fill gaps we fall back to the Ollama server that hosts our AI models (its
OpenAI-compatible chat API, with a system prompt that understands the asterisk
notation). If Ollama is unavailable the transcription still succeeds, missing
words stay marked, and the user is told they can review them offline.
"""

from __future__ import annotations

import os
import time

import pydub
import streamlit as st

import shared as sh
from faster_whisper import WhisperModel

MODEL = "large-v3"
LANGUAGE_HINT = "english"  # set here to lock the source language (optional)


def _audio_path(name: str) -> str:
    return os.path.join(sh.UPLOAD_DIR, name)


def _load_audio(path: str):
    return pydub.AudioFile.open(path)


def _check_spread(wav_path: str) -> bool:
    """Return True if we can read the audio and it is not essentially silent."""
    try:
        audio = _load_audio(wav_path)
        n = audio.frame_count()
        if n <= 1:
            return False
        rms = audio.rms
        # rms == 0 for pure silence; allow a tiny floor for very quiet clips.
        return rms > 0
    except Exception:
        return False


def _transcribe(audio_path: str, start_progress, done_progress):
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    done_progress("Loading model…")
    segments, info = model.transcribe(
        audio_path,
        language=LANGUAGE_HINT,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    segments = list(segments)
    start_progress("Finished")
    return info, segments


def _ollama_fix(mark_text: str):
    """Attempt to recover uncertain words via Ollama.

    Returns ``("ok", fixed)`` on success, otherwise ``("unavailable", text)``.
    """
    import json
    import urllib.request

    url = "http://localhost:11434/v1/messages"
    payload = {
        "model": "hermes3",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You repair transcriptions. Each input word may be prefixed with a "
                    "single asterisk (*) meaning the ASR was unsure of that word. "
                    "Only repair broken words; do not rephrase the sentence. Output "
                    "the corrected sentence verbatim, and keep an asterisk only where "
                    "the input had one, directly before that word."
                ),
            },
            {"role": "user", "content": mark_text},
        ],
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
    except Exception:
        return "unavailable", mark_text
    content = body.get("content")
    if isinstance(content, list):
        fixed: str = "".join(p.get("text", "") for p in content).strip()
        if fixed:
            return "ok", fixed
    return "unavailable", mark_text


def _save_wav(src_path: str, label: str):
    """Export ``src_path`` to a mono 16 kHz wav in WORK_DIR (or None)."""
    os.makedirs(sh.WORK_DIR, exist_ok=True)
    dest = os.path.join(sh.WORK_DIR, f"audio-{label}.wav")
    try:
        import pydub
        seg = pydub.AudioSegment.from_file(src_path)
        seg = seg.set_channels(1).set_frame_rate(16000)
        seg.export(dest, format="wav")
        return dest
    except Exception:
        return None


def _marked_text(all_words, threshold):
    """Return ``(marked_string, count_below_threshold)``.

    ``marked_string`` is the transcript with a leading ``*[word]`` on every word
    the ASR flagged as uncertain (probability below ``threshold``), so the user
    can see exactly which words were guessed.
    """
    marked_now = 0
    parts = []
    for w in all_words:
        uncertain = w.probability is not None and w.probability < threshold
        parts.append(f"*{w.word.strip()}" if uncertain else w.word.strip())
        if uncertain:
            marked_now += 1
    return " ".join(parts), marked_now


def _render(info, segments, audio_path):
    all_words = [w for _, _, ws in segments for w in ws]
    if not all_words:
        st.info("No speech detected in this audio.")
        return

    UNCERTAIN_THRESHOLD = 0.6  # below this probability the word is "guessed"
    marked = [w for w in all_words if w.probability is not None
              and w.probability < UNCERTAIN_THRESHOLD]
    if marked:
        st.warning(
            f"{len(marked)} word(s) flagged *[guessed] "
            f"(probability < {UNCERTAIN_THRESHOLD}). Review them."
        )
    st.caption(
        "Legend: **word** = confident transcription; *[word] = the model was "
        "less sure about this word (guessed)."
    )

    plain_text = " ".join(w.word.strip() for w in all_words)

    # The primary output: a clean, plain transcript.
    st.subheader("Transcript")
    st.write(plain_text)

    # The "Marked version" shows *[word] at every guessed spot so the user can
    # see exactly which words were filled in vs. the model was confident about.
    st.subheader("Marked version")
    mark_text, marked_now = _marked_text(all_words, UNCERTAIN_THRESHOLD)
    st.write(mark_text)

    if marked_now:
        cached = st.session_state.get("mp3_mark_text", mark_text)
    else:
        cached = None

    if marked_now or cached:
        if st.button(
            "Repair uncertain words (uses local Ollama)", type="secondary"
        ):
            with st.spinner("Asking Ollama…"):
                status, fixed = _ollama_fix(
                    cached if cached is not None else mark_text
                )
            if status == "ok":
                st.success(
                    "Ollama recovered some words — they keep the *[ ]* marker "
                    "so you still know they were guesses."
                )
                st.write(fixed)
                st.session_state["mp3_ollama_result"] = fixed
                st.rerun()
            else:
                st.warning(
                    "Ollama unavailable this time — nothing was corrected. "
                    "The marked version above is still showing the guesses."
                )

    cached = st.session_state.get("mp3_ollama_result")
    if cached:
        st.caption("Last Ollama recovery:")
        st.write(cached)

    # Per-word detail (with probability) so the user can spot the guessed words.
    st.subheader("Word-level detail")
    rows = [
        (
            i,
            w.word,
            (round(w.start, 2), round(w.end, 2)),
            "guessed" if w.probability is not None and w.probability < UNCERTAIN_THRESHOLD
            else "ok",
            f"{w.probability:.2f}" if w.probability is not None else "n/a",
        )
        for i, w in enumerate(all_words)
    ]
    st.dataframe(
        {"#": [ r[0] for r in rows ],
         "word": [ r[1] for r in rows ],
         "time": [ f"{r[2][0]:.1f}–{r[2][1]:.1f}" for r in rows ],
         "status": [ r[3] for r in rows ],
         "prob": [ r[4] for r in rows ]},
        use_container_width=True, hide_index=True,
    )

    st.header("Info")
    st.write(f"Language: {info.language} ({info.language_probability:.0%})")
    st.write(f"Duration: {info.duration:.1f}s")
    try:
        st.audio(audio_path)
    except Exception:
        # Audio player can't always open the temp wav; fall back quietly.
        pass


def render() -> None:
    sh.ensure_dir(sh.WORK_DIR)
    st.subheader("🎙️ MP3 Transcribe")

    files = [
        row["name"] for row in sh.list_upload_files()
        if row["name"].lower().endswith(
            (".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg")
        )
    ]
    if not files:
        st.info(
            "No audio files in uploads yet. Use the sidebar uploader, then this "
            "page will auto-refresh (or press **Refresh** below)."
        )
        st.rerun()
        return

    f = st.selectbox("Select an audio file to transcribe", files)
    if not st.button("▶️ Transcribe", type="primary"):
        return

    path = _audio_path(f)
    if not os.path.isfile(path):
        st.error("That file is missing from uploads.")
        return

    wav = _save_wav(path, sh.safe_name(f))
    if wav is None:
        st.error("That file is not a readable audio format.")
        return

    if not _check_spread(wav):
        st.error("That file contains no audible speech.")
        return

    with st.spinner("Model will download on first run (1–2 min). Next runs are fast."):
        info, segments = _transcribe(
            wav,
            start_progress=lambda msg: st.info(msg),
            done_progress=lambda msg: st.info(msg),
        )

    if not segments:
        st.info("No speech detected.")
        return

    _render(info, segments, wav)
