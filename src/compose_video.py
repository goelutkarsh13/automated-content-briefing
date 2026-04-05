from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import List

from .utils import ensure_dir

logger = logging.getLogger(__name__)


def compose_video(
    slide_paths: List[str | Path],
    audio_path: str | Path,
    output_path: str | Path,
    seconds_per_slide: int | List[int] = 35,
) -> Path:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required but was not found on PATH.")

    slide_paths = [str(Path(p).resolve()) for p in slide_paths]
    audio_path = str(Path(audio_path).resolve())
    output_path = Path(output_path).resolve()
    ensure_dir(output_path.parent)

    num_slides = len(slide_paths)
    if num_slides == 0:
        raise ValueError("No slides provided.")

    # Build per-slide duration list
    if isinstance(seconds_per_slide, list):
        durations = list(seconds_per_slide)
        while len(durations) < num_slides:
            durations.append(durations[-1] if durations else 35)
        durations = durations[:num_slides]
    else:
        durations = [seconds_per_slide] * num_slides

    # Step 1: Create a short video clip from each slide image
    temp_dir = output_path.parent / "_temp_clips"
    temp_dir.mkdir(parents=True, exist_ok=True)
    clip_paths: List[str] = []

    for i, (slide, dur) in enumerate(zip(slide_paths, durations)):
        clip = str(temp_dir / f"clip_{i:03d}.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loop", "1",
                "-i", slide,
                "-t", str(dur),
                "-vf", "scale=1280:720,format=yuv420p",
                "-r", "24",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                clip,
            ],
            check=True,
            capture_output=True,
        )
        clip_paths.append(clip)

    # Step 2: Write concat list for the clips
    concat_file = str(temp_dir / "clips.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for clip in clip_paths:
            f.write(f"file '{clip}'\n")

    # Step 3: Concatenate all clips into one silent video
    temp_video = str(temp_dir / "all_slides.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            temp_video,
        ],
        check=True,
        capture_output=True,
    )

    # Step 4: Merge with audio
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", temp_video,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )

    # Clean up temp directory
    try:
        shutil.rmtree(temp_dir)
    except OSError as exc:
        logger.warning("Could not clean up temp dir %s: %s", temp_dir, exc)

    return output_path
