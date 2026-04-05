from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

from .utils import ensure_dir

WIDTH = 1280
HEIGHT = 720
MARGIN_X = 80
MARGIN_Y = 60


def _load_font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_slides(slides: List[Dict], output_dir: str | Path) -> List[Path]:
    out_dir = ensure_dir(output_dir)
    files: List[Path] = []

    title_font = _load_font(42, bold=True)
    body_font = _load_font(28, bold=False)
    footer_font = _load_font(22, bold=False)

    total = len(slides)
    for i, slide in enumerate(slides, start=1):
        img = Image.new("RGB", (WIDTH, HEIGHT), "white")
        draw = ImageDraw.Draw(img)

        draw.rectangle([(0, 0), (WIDTH, 12)], fill=(30, 30, 30))
        draw.rectangle([(0, HEIGHT - 12), (WIDTH, HEIGHT)], fill=(30, 30, 30))

        title_text = slide["title"][:65] if len(slide["title"]) > 65 else slide["title"]
        draw.text((MARGIN_X, MARGIN_Y), title_text, font=title_font, fill=(20, 20, 20))

        y = MARGIN_Y + 100
        bullets = slide.get("bullets", [])
        max_y = HEIGHT - 70  # leave room for footer
        for bullet in bullets[:5]:
            wrapped = _wrap_text(bullet, 80)
            for line_idx, line in enumerate(wrapped):
                if y + 42 > max_y:
                    break
                prefix = "• " if line_idx == 0 else "  "
                draw.text((MARGIN_X, y), prefix + line, font=body_font, fill=(40, 40, 40))
                y += 42
            y += 18
            if y > max_y:
                break

        progress = f"Slide {i}/{total}"
        draw.text((MARGIN_X, HEIGHT - 50), progress, font=footer_font, fill=(90, 90, 90))

        file_path = out_dir / f"slide_{i:02d}.png"
        img.save(file_path)
        files.append(file_path)

    return files


def _wrap_text(text: str, width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = []
    current_len = 0
    for word in words:
        new_len = current_len + len(word) + (1 if current else 0)
        if current and new_len > width:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len = new_len
    if current:
        lines.append(" ".join(current))
    return lines
