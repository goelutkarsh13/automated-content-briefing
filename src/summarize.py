from __future__ import annotations

import logging
from typing import List

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from .utils import chunk_text, sentence_split, shorten

logger = logging.getLogger(__name__)


class BriefingSummarizer:
    def __init__(
        self,
        model_name: str = "facebook/bart-large-cnn",
        max_sections: int = 5,
    ):
        self.model_name = model_name
        self.max_sections = max_sections
        self._model = None
        self._tokenizer = None

    def _load_model(self) -> None:
        if self._model is None:
            logger.debug("Loading model: %s", self.model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)

    def _generate(self, text: str, max_new_tokens: int = 140) -> str:
        self._load_model()
        try:
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                max_length=1024,
                truncation=True,
            )
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                num_beams=4,
                early_stopping=True,
            )
            return self._tokenizer.decode(
                output_ids[0], skip_special_tokens=True
            ).strip()
        except Exception as exc:
            logger.warning("Model inference failed: %s", exc)
            return ""

    def summarize_chunk(self, text: str) -> str:
        result = self._generate(text, max_new_tokens=140)
        if result:
            return result

        logger.warning("Chunk summarization failed, using sentence fallback.")
        sentences = sentence_split(text)
        fallback = sentences[:5]
        return "\n".join(f"- {s}" for s in fallback)

    def build_briefing(self, full_text: str) -> dict:
        chunks = chunk_text(full_text)
        chunk_summaries = [self.summarize_chunk(c) for c in chunks]
        return self._build_briefing(full_text, chunk_summaries)

    def _build_briefing(
        self, full_text: str, chunk_summaries: List[str]
    ) -> dict:
        """Build a structured briefing from chunk summaries."""
        sentences = sentence_split(full_text)
        intro = (
            " ".join(sentences[:3])
            if sentences
            else "This briefing summarizes the source content."
        )
        closing = (
            " ".join(sentences[-3:]) if len(sentences) >= 3 else intro
        )

        sections = []
        for idx, summary in enumerate(
            chunk_summaries[: self.max_sections], start=1
        ):
            summary_sentences = [
                s.lstrip("- ") for s in summary.splitlines() if s.strip()
            ]
            # BART outputs a single block of text so split into sentences
            if len(summary_sentences) == 1:
                summary_sentences = sentence_split(summary_sentences[0])
            bullets = [s for s in summary_sentences[:4]]
            narration = " ".join(summary_sentences[:4])
            sections.append(
                {
                    "title": f"Key Point {idx}",
                    "bullets": bullets
                    or ["Main point extracted from source content."],
                    "narration": narration
                    or "This section covers one of the core ideas in the source material.",
                }
            )

        while len(sections) < 3:
            sections.append(
                {
                    "title": f"Key Point {len(sections) + 1}",
                    "bullets": ["Additional context from the source content."],
                    "narration": "This section adds supporting context to the overall briefing.",
                }
            )

        return {
            "title": shorten(
                sentences[0] if sentences else "Automated Content Briefing",
                80,
            ),
            "intro": intro,
            "sections": sections,
            "summary": closing,
        }
