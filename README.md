# BriefCast

A cost-efficient, modular pipeline that converts long-form text or PDF content into a concise **multimedia briefing** with structured sections, slide visuals, audio narration, and a final stitched video — all powered by open-source models running locally.

## High-level pipeline

```text
Input (PDF/text)
   ↓
Text extraction
   ↓
Chunking + summarization (BART-large-CNN)
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

## Features

- **React frontend** — paste text or upload a file, watch the pipeline run, view video/slides/script
- **BART-large-CNN summarization** — open-source, runs locally via `AutoModelForSeq2SeqLM`
- **Template-based slides** — deterministic, fast, no GPU required
- **Offline TTS** — subprocess-chunked pyttsx3 or Piper for narration
- **FFmpeg composition** — per-slide video clips with proportional audio timing via `ffprobe`
- **Multi-format export** — JSON, CSV, XML, PDF, Markdown (via CLI)

## Repository structure

```text
briefcast/
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
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
├── server.py
├── run.py
├── architecture.md
├── requirements.txt
└── README.md
```

## Quick start

### 1. Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install uvicorn python-multipart fastapi
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

### 3. Frontend setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run (full-stack)

Terminal 1 — Backend:
```bash
source .venv/bin/activate
uvicorn server:app --reload --port 8000
```

Terminal 2 — Frontend:
```bash
cd frontend
npm run dev
```

Open `http://localhost:3000` in your browser.

### 5. Run (CLI only)

```bash
python run.py --input input/sample.txt --tts-backend pyttsx3 --verbose
```

## Command-line options

- `--input`: path to `.pdf`, `.txt`, or `.md`
- `--output-dir`: output directory
- `--max-sections`: maximum number of main sections
- `--seconds-per-slide`: fallback duration per slide (seconds) when `ffprobe` is unavailable
- `--tts-backend`: `pyttsx3` or `piper`
- `--piper-model`: path to Piper `.onnx` voice model
- `--hf-model`: Hugging Face summarization model name (default: `facebook/bart-large-cnn`)
- `--verbose`, `-v`: enable debug-level logging

## Engineering tradeoffs

### Why template-based visuals as the default?
Template slides are deterministic, cheap, and fast. They align well with briefing-style outputs where clarity matters more than cinematic quality.

### Why a modular pipeline?
Each stage is independently testable and replaceable. The summarizer can be swapped without touching slide or TTS logic.

### Why proportional slide timing instead of word-level alignment?
The pipeline measures actual audio duration with `ffprobe` and distributes time across slides proportionally by narration word count. A more precise approach would split audio at silence gaps or use word-level TTS timestamps, but proportional timing is simple and produces good-enough sync for a briefing format.

### Why BART-large-CNN as the default model?
`facebook/bart-large-cnn` produces coherent extractive summaries out of the box with a 1024-token context window. The model is loaded directly via `AutoModelForSeq2SeqLM` for compatibility across `transformers` versions.

### Why subprocess-based TTS chunking?
pyttsx3 on macOS uses NSSpeechSynthesizer, which hangs on long text and fails to reinitialize within the same process. The pipeline splits narration into ~500-character chunks at sentence boundaries, synthesizes each in a separate subprocess, and concatenates the audio with FFmpeg.

## Tech stack

- **Frontend**: React, Vite, Tailwind CSS
- **Backend**: Python, FastAPI
- **Summarization**: facebook/bart-large-cnn (HuggingFace Transformers)
- **Slides**: Pillow (PIL)
- **TTS**: pyttsx3 / Piper
- **Composition**: FFmpeg
- **No paid APIs** — everything runs locally
