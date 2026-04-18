# System Architecture and Cost Rationale

## Overview

BriefCast converts long-form text or PDF content into a short multimedia briefing. The output is a concise narrated slide-deck video with a clear narrative structure, visual support, and audio narration.

The architecture emphasizes:

- open-source tooling
- low marginal cost per run
- practical engineering tradeoffs
- clear separation of pipeline stages

## Pipeline

```text
Document Input
  -> Text Extraction
  -> Cleaning and Chunking
  -> Chunk Summarization
  -> Briefing Assembly
  -> Script + Slide Generation
  -> TTS Narration
  -> Video Composition
```

## Components

### 1. Input Ingestion
The system accepts PDF and plain-text sources.

- **PDF extraction** uses `PyMuPDF` for reliable parsing.
- **Text files** are read directly.

This stage is intentionally lightweight and deterministic.

### 2. Chunking and Content Processing
Long documents are split into paragraph-aware chunks. This reduces memory pressure and keeps summarization tractable on commodity hardware.

The default summarization model is `facebook/bart-large-cnn`, which handles up to 1024 tokens per input and produces coherent extractive summaries without instruction-style prompting. The model is loaded directly via `AutoModelForSeq2SeqLM` and `AutoTokenizer` rather than through the HuggingFace `pipeline()` API, which ensures compatibility across `transformers` versions (including v5.x where the `summarization` task was removed).

Chunk summaries are then assembled into a briefing plan with:

- title
- introduction
- 3–5 main sections
- closing summary

### 3. Briefing Structure Generation
The system transforms chunk summaries into a structured JSON artifact. This intermediate representation decouples content planning from rendering.

The JSON includes:

- section titles
- concise bullet points
- narration text
- summary statement

### 4. Visual Generation
Slides are created using deterministic templates.

Why:

- lower compute cost
- faster iteration
- more predictable output
- easier debugging

Each slide is rendered as a PNG image with:

- section heading
- 3–5 bullets
- footer progress indicator

### 5. Audio Narration
Narration is generated using an open-source or offline-friendly TTS backend. Long scripts are split into ~500-character chunks at sentence boundaries, and each chunk is synthesized in a separate subprocess to avoid engine hang issues (particularly with pyttsx3 on macOS). The resulting audio chunks are concatenated using FFmpeg. After synthesis, the pipeline validates that the output file exists and exceeds a minimum size threshold to catch silent failures.

Supported options:

- **Piper**: preferred for open-source, local inference, and good speed-quality tradeoff
- **pyttsx3**: fallback for environments where local system speech synthesis is easier to run

### 6. Composition
The final video is composed using `ffmpeg` in three steps: each slide image is looped into a short video clip for its assigned duration, all clips are concatenated, and the narration audio is merged in.

Slide durations are calculated by measuring the actual audio length with `ffprobe`, then distributing time proportionally based on each section's narration word count.

Intermediate files (per-slide clips, concat manifest) are cleaned up automatically after composition.

### 7. Web Frontend
A React frontend (Vite + Tailwind CSS) provides a browser-based interface for the pipeline. Users can paste text or upload a file, watch pipeline progress, and view the generated video, slides, and narration script. The frontend communicates with a FastAPI server that wraps the pipeline.

## Cost Considerations

The design avoids using proprietary paid APIs for core logic. The only runtime costs are local compute and a one-time model download (~1.6GB for BART).

### Cost-saving choices

1. **Modular summarization instead of end-to-end multimodal generation**
   - reduces GPU dependence
   - lowers experimentation cost

2. **Template-based slides instead of generated video scenes**
   - avoids expensive image/video generation
   - improves consistency

3. **Offline/open-source TTS**
   - avoids per-minute narration costs

4. **FFmpeg composition**
   - no external rendering service needed

### Robustness choices

1. **Audio output validation** — TTS backends (especially pyttsx3 on headless systems) can silently produce empty files; the pipeline checks file size post-synthesis and raises early.
2. **Structured logging** — all modules use Python's `logging` library with a `--verbose` flag for debug-level output.
3. **Graceful fallback in summarization** — if model inference fails on a chunk, the pipeline falls back to extractive sentence selection rather than crashing.

## Tradeoffs

### Chosen
- determinism over maximal visual richness
- low operational cost over flashy generative media
- simple architecture over model-heavy orchestration

### Not chosen
- agentic planning frameworks
- paid voice APIs
- proprietary video generation pipelines
- complex frontend application layers

## Practical Engineering Decision

The core engineering decision was to optimize for **clarity and cost-efficiency**, not for the most advanced possible generated media. For a briefing task, the primary value is whether the user can quickly understand the source content. A clean narrated slide deck achieves this reliably.

## Future Extensions

- retrieval-based importance ranking for very long inputs
- chart generation from extracted numeric data
- optional avatar presenter
- multilingual narration
- AI-generated video clips via open-source models (e.g. LTX-Video) when GPU budget allows
- higher quality open-source voice cloning
