from __future__ import annotations

from typing import Dict, List


def build_script(briefing: dict) -> str:
    lines: List[str] = []
    lines.append(f"Title: {briefing['title']}")
    lines.append("")
    lines.append("Introduction")
    lines.append(briefing["intro"])
    lines.append("")

    for i, section in enumerate(briefing["sections"], start=1):
        lines.append(f"Section {i}: {section['title']}")
        lines.append(section["narration"])
        lines.append("")

    lines.append("Summary")
    lines.append(briefing["summary"])
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_slide_payloads(briefing: dict) -> List[Dict]:
    slides: List[Dict] = []
    slides.append(
        {
            "title": briefing["title"],
            "bullets": [briefing["intro"]],
            "kind": "title",
        }
    )

    for idx, section in enumerate(briefing["sections"], start=1):
        slides.append(
            {
                "title": section["title"],
                "bullets": section["bullets"][:5],
                "kind": "section",
                "index": idx,
            }
        )

    slides.append(
        {
            "title": "Key Takeaways",
            "bullets": [briefing["summary"]],
            "kind": "summary",
        }
    )
    return slides
