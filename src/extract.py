from __future__ import annotations

from pathlib import Path

import fitz

from .utils import clean_text


def extract_text(input_path: str | Path) -> str:
    path = Path(input_path)
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8")
        return clean_text(text)

    if suffix == ".pdf":
        return extract_pdf_text(path)

    raise ValueError(f"Unsupported input type: {suffix}")


def extract_pdf_text(path: str | Path) -> str:
    doc = fitz.open(str(path))
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return clean_text("\n\n".join(pages))
