# Automated Content Briefing System

A cost-efficient, modular pipeline that converts long-form text or PDF content into a concise **3–5 minute multimedia briefing** with:

- structured sections (`intro`, `key points`, `summary`)
- slide visuals
- audio narration
- final stitched video output

This project is designed for technical challenges where **open-source tooling, engineering tradeoffs, and practical system design** matter more than cinematic polish.

## High-level pipeline

```text
Input (PDF/text)
   ↓
Text extraction
   ↓
Chunking + summarization
   ↓
Structured briefing JSON
   ↓
Narration script + slide deck
   ↓
Text-to-speech audio
   ↓
FFmpeg composition
   ↓
Final briefing video (.mp4)
```

## Why this design

Instead of using an expensive end-to-end proprietary multimodal workflow, this system breaks the problem into inexpensive, replaceable modules:

1. **Extraction** keeps ingestion simple and robust.
2. **Summarization** produces a structured outline from long content.
3. **Slide generation** uses deterministic templates rather than costly image/video generation.
4. **Narration** uses offline/open-source TTS with chunked synthesis to handle long scripts reliably.
5. **Composition** uses FFmpeg to create per-slide video clips and merge them with narration audio. Slide durations are calculated from actual audio length using `ffprobe`.

This improves:

- **cost-efficiency**
- **debuggability**
- **reproducibility**
- **modularity**

## Repository structure

```text
automated-content-briefing/
├── input/
├── output/
│   ├── audio/
│   └── slides/
├── src/
│   ├── __init__.py
│   ├── extract.py
│   ├── summarize.py
│   ├── script_writer.py
│   ├── slide_gen.py
│   ├── tts.py
│   ├── compose_video.py
│   ├── pipeline.py
│   └── utils.py
├── architecture.md
├── requirements.txt
└── run.py
```

## Supported inputs

- `.pdf`
- `.txt`
- `.md`

## Outputs

The pipeline produces:

- `output/briefing.json` — structured outline
- `output/script.txt` — narration script
- `output/slides/slide_*.png` — rendered slide images
- `output/audio/narration.wav` — generated narration audio
- `output/final_briefing.mp4` — final briefing video

## Quick start

### 1. Create environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install FFmpeg

Mac:
```bash
brew install ffmpeg
```

Ubuntu:
```bash
sudo apt update && sudo apt install ffmpeg
```

### 3. Optional TTS backends

#### Option A: Piper (recommended)
Install Piper and download a voice model.

Example:
```bash
piper --model en_US-lessac-medium.onnx --output_file test.wav --text "hello"
```

Then run the pipeline with:
```bash
python run.py --input input/sample.txt --tts-backend piper --piper-model /path/to/voice.onnx
```

#### Option B: pyttsx3 fallback
Works without external model downloads in some environments:
```bash
python run.py --input input/sample.txt --tts-backend pyttsx3
```

## Run the pipeline

```bash
python run.py --input input/sample.txt
```

With optional arguments:

```bash
python run.py \
  --input input/sample.txt \
  --output-dir output \
  --max-sections 5 \
  --seconds-per-slide 35 \
  --tts-backend pyttsx3 \
  --verbose
```

## Command-line options

- `--input`: path to `.pdf`, `.txt`, or `.md`
- `--output-dir`: output directory
- `--max-sections`: maximum number of main sections
- `--seconds-per-slide`: fallback duration per slide (seconds) when `ffprobe` is unavailable to measure audio length
- `--tts-backend`: `pyttsx3` or `piper`
- `--piper-model`: path to Piper `.onnx` voice model
- `--hf-model`: Hugging Face summarization model name (default: `facebook/bart-large-cnn`)
- `--verbose`, `-v`: enable debug-level logging for troubleshooting

## Engineering tradeoffs

### Why template-based visuals?
Template slides are deterministic, cheap, and fast. They also align well with briefing-style outputs. Generated cinematic visuals would look flashier, but they add complexity, latency, and compute cost.

### Why a modular pipeline?
A modular design makes each stage independently testable and replaceable. For example, the summarizer can be swapped without rewriting slide or TTS logic.

### Why proportional slide timing instead of word-level alignment?
The pipeline measures actual audio duration with `ffprobe` and distributes time across slides proportionally by narration word count. A more precise approach would split audio at silence gaps or use word-level TTS timestamps, but proportional timing is simple, dependency-free, and produces good-enough sync for a briefing format.

### Why BART-large-CNN as the default model?
`facebook/bart-large-cnn` is a strong open-source summarization model with a 1024-token context window. It produces coherent, extractive summaries out of the box without needing instruction-style prompting. The model is loaded directly via `AutoModelForSeq2SeqLM` for maximum compatibility across `transformers` versions. Heavier reasoning or instruction-following models can be swapped in via `--hf-model` if needed, but BART hits the best tradeoff between quality, speed, and zero-cost local inference for this use case.

### Why subprocess-based TTS chunking?
pyttsx3 on macOS uses NSSpeechSynthesizer, which can hang or produce empty output on long text, and fails to reinitialize within the same process. The pipeline splits narration into ~500-character chunks at sentence boundaries, synthesizes each in a separate subprocess, and concatenates the audio with FFmpeg. This is more robust than a single long TTS call.

## Notes

- For very long documents, consider adding retrieval-based chunk ranking before summarization.
- For stronger narration quality, Piper is preferable to pyttsx3.
- If you want generated charts or topic-specific diagrams, you can extend `slide_gen.py`.

