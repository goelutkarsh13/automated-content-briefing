from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import List

from .utils import ensure_dir

logger = logging.getLogger(__name__)

_MIN_AUDIO_BYTES = 256
_MAX_CHUNK_CHARS = 500  # pyttsx3 hangs on very long text; split into chunks


def _validate_audio(path: Path) -> None:
    """Raise if the output file is missing or suspiciously small."""
    if not path.exists():
        raise RuntimeError(f"TTS produced no output file at {path}")
    size = path.stat().st_size
    if size < _MIN_AUDIO_BYTES:
        raise RuntimeError(
            f"TTS output is too small ({size} bytes) — audio generation likely failed. "
            f"File: {path}"
        )


def _split_text_for_tts(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> List[str]:
    """Split text into chunks at sentence boundaries."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = current + " " + sentence if current else sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text]


def _concat_audio_files(audio_paths: List[Path], output_path: Path) -> None:
    """Concatenate multiple audio files into one WAV using ffmpeg."""
    if not audio_paths:
        raise ValueError("No audio files to concatenate.")

    temp_list = output_path.parent / "_concat_list.txt"
    with open(temp_list, "w", encoding="utf-8") as f:
        for p in audio_paths:
            f.write(f"file '{p.resolve()}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(temp_list),
            "-c:a", "pcm_s16le",
            "-ar", "22050",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )

    try:
        temp_list.unlink()
    except OSError:
        pass


def synthesize_speech(
    text: str,
    output_path: str | Path,
    backend: str = "pyttsx3",
    piper_model: str | None = None,
) -> Path:
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    backend = backend.lower()
    if backend == "piper":
        return _synthesize_with_piper(text, output_path, piper_model)
    if backend == "pyttsx3":
        return _synthesize_with_pyttsx3(text, output_path)

    raise ValueError(f"Unsupported TTS backend: {backend}")


def _synthesize_with_piper(
    text: str, output_path: Path, model_path: str | None
) -> Path:
    if not model_path:
        raise ValueError("Piper backend selected but --piper-model was not provided.")
    if shutil.which("piper") is None:
        raise RuntimeError("Piper is not installed or not available on PATH.")

    cmd = [
        "piper",
        "--model",
        model_path,
        "--output_file",
        str(output_path),
        "--text",
        text,
    ]
    subprocess.run(cmd, check=True)
    _validate_audio(output_path)
    return output_path


def _synthesize_with_pyttsx3(text: str, output_path: Path) -> Path:
    chunks = _split_text_for_tts(text)
    logger.debug("Splitting narration into %d chunks for TTS.", len(chunks))

    if len(chunks) == 1:
        _pyttsx3_subprocess(chunks[0], output_path)
        return output_path

    # Multiple chunks — synthesize each in a separate process, then concatenate
    temp_dir = output_path.parent / "_tts_chunks"
    temp_dir.mkdir(parents=True, exist_ok=True)
    chunk_paths: List[Path] = []

    try:
        for i, chunk in enumerate(chunks):
            chunk_path = temp_dir / f"chunk_{i:03d}.wav"
            logger.debug("TTS chunk %d/%d (%d chars)", i + 1, len(chunks), len(chunk))
            _pyttsx3_subprocess(chunk, chunk_path)
            chunk_paths.append(chunk_path)

        _concat_audio_files(chunk_paths, output_path)
        _validate_audio(output_path)
    finally:
        try:
            shutil.rmtree(temp_dir)
        except OSError as exc:
            logger.warning("Could not clean up TTS temp dir: %s", exc)

    return output_path


def _pyttsx3_subprocess(text: str, output_path: Path) -> None:
    """Run pyttsx3 in a separate process to avoid Mac NSSpeechSynthesizer hangs."""
    import sys
    import json as _json

    script = (
        "import pyttsx3, sys, json; "
        "args = json.loads(sys.argv[1]); "
        "e = pyttsx3.init(); "
        "e.setProperty('rate', 165); "
        "e.save_to_file(args['text'], args['path']); "
        "e.runAndWait()"
    )
    payload = _json.dumps({"text": text, "path": str(output_path)})
    result = subprocess.run(
        [sys.executable, "-c", script, payload],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        logger.warning("pyttsx3 subprocess stderr: %s", result.stderr)
        raise RuntimeError(f"pyttsx3 subprocess failed: {result.stderr}")
    _validate_audio(output_path)
