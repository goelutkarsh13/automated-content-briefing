from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .compose_video import compose_video
from .extract import extract_text
from .script_writer import build_script, build_slide_payloads
from .slide_gen import render_slides
from .summarize import BriefingSummarizer
from .tts import synthesize_speech
from .utils import ensure_dir, write_json, write_text

logger = logging.getLogger(__name__)


def _get_audio_duration(audio_path: Path) -> float | None:
    """Get audio duration in seconds using ffprobe."""
    import shutil
    import subprocess

    if shutil.which("ffprobe") is None:
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except Exception as exc:
        logger.warning("Could not get audio duration: %s", exc)
        return None


def _compute_slide_durations(
    briefing: dict,
    audio_path: Path | None = None,
    fallback: int = 35,
) -> list[int]:
    """Compute per-slide duration proportional to narration word count.

    If audio_path is provided, durations are scaled so the total matches
    the actual audio length.  Otherwise falls back to WPM estimate.
    """
    # Collect narration text per slide in the same order build_slide_payloads produces
    narration_parts: list[str] = []

    # Title slide narrates the intro
    narration_parts.append(briefing.get("intro", ""))

    # Section slides
    for section in briefing.get("sections", []):
        narration_parts.append(section.get("narration", ""))

    # Summary slide
    narration_parts.append(briefing.get("summary", ""))

    word_counts = [max(1, len(part.split())) for part in narration_parts]
    total_words = sum(word_counts)

    # Try to get real audio duration
    total_seconds: float | None = None
    if audio_path and audio_path.exists():
        total_seconds = _get_audio_duration(audio_path)

    if total_seconds is None:
        # Fall back to WPM estimate
        total_seconds = total_words / 145.0 * 60.0

    # Distribute proportionally, minimum 3 seconds per slide
    durations = [max(3, int(total_seconds * wc / total_words)) for wc in word_counts]

    # Add any leftover time to the last slide so audio doesn't get cut off
    assigned = sum(durations)
    if total_seconds and assigned < int(total_seconds) + 2:
        durations[-1] += int(total_seconds) + 2 - assigned

    logger.debug(
        "Slide durations: %s (total_audio=%.1fs, total_assigned=%ds)",
        durations,
        total_seconds,
        sum(durations),
    )
    return durations


def run_pipeline(
    input_path: str,
    output_dir: str = "output",
    max_sections: int = 5,
    seconds_per_slide: int = 35,
    tts_backend: str = "pyttsx3",
    piper_model: str | None = None,
    hf_model: str = "facebook/bart-large-cnn",
    verbose: bool = False,
) -> dict:
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    out_dir = ensure_dir(output_dir)
    slides_dir = ensure_dir(Path(out_dir) / "slides")
    audio_dir = ensure_dir(Path(out_dir) / "audio")

    print("[1/6] Extracting text...")
    text = extract_text(input_path)
    logger.debug("Extracted %d characters.", len(text))

    print("[2/6] Summarizing and planning briefing...")
    summarizer = BriefingSummarizer(model_name=hf_model, max_sections=max_sections)
    briefing = summarizer.build_briefing(text)
    write_json(Path(out_dir) / "briefing.json", briefing)
    logger.debug("Briefing has %d sections.", len(briefing.get("sections", [])))

    print("[3/6] Building narration script...")
    script = build_script(briefing)
    write_text(Path(out_dir) / "script.txt", script)

    print("[4/6] Rendering slides...")
    slides = build_slide_payloads(briefing)
    slide_paths = render_slides(slides, slides_dir)

    print("[5/6] Generating narration...")
    audio_path = Path(audio_dir) / "narration.wav"
    synthesize_speech(script, audio_path, backend=tts_backend, piper_model=piper_model)

    print("[6/6] Composing final video...")
    durations = _compute_slide_durations(briefing, audio_path=audio_path, fallback=seconds_per_slide)

    final_video = Path(out_dir) / "final_briefing.mp4"
    compose_video(slide_paths, audio_path, final_video, seconds_per_slide=durations)

    print("\nDone.")
    return {
        "briefing_json": str(Path(out_dir) / "briefing.json"),
        "script": str(Path(out_dir) / "script.txt"),
        "slides": [str(p) for p in slide_paths],
        "audio": str(audio_path),
        "video": str(final_video),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated Content Briefing Pipeline")
    parser.add_argument("--input", required=True, help="Path to input file (.pdf, .txt, .md)")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--max-sections", type=int, default=5, help="Maximum number of sections")
    parser.add_argument(
        "--seconds-per-slide",
        type=int,
        default=35,
        help="Fallback duration per slide (seconds) when narration timing is unavailable",
    )
    parser.add_argument("--tts-backend", default="pyttsx3", choices=["pyttsx3", "piper"], help="TTS backend")
    parser.add_argument("--piper-model", default=None, help="Path to Piper ONNX voice model")
    parser.add_argument(
        "--hf-model",
        default="facebook/bart-large-cnn",
        help="Hugging Face summarization model (default: facebook/bart-large-cnn)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose/debug logging")

    args = parser.parse_args()
    outputs = run_pipeline(
        input_path=args.input,
        output_dir=args.output_dir,
        max_sections=args.max_sections,
        seconds_per_slide=args.seconds_per_slide,
        tts_backend=args.tts_backend,
        piper_model=args.piper_model,
        hf_model=args.hf_model,
        verbose=args.verbose,
    )

    print("Generated files:")
    for key, value in outputs.items():
        print(f"  {key}: {value}")
