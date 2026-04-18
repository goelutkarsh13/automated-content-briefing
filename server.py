from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BriefCast Content Briefing")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve output files
os.makedirs("output", exist_ok=True)
app.mount("/output", StaticFiles(directory="output"), name="output")

# Serve frontend
if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")


@app.get("/", response_class=HTMLResponse)
async def root():
    if os.path.exists("frontend/dist/index.html"):
        return FileResponse("frontend/dist/index.html")
    return HTMLResponse("<h1>BriefCast API</h1><p>Frontend not built. Use /docs for API.</p>")


@app.post("/api/briefing")
async def create_briefing(
    text: str = Form(None),
    file: UploadFile = File(None),
    tts_backend: str = Form("pyttsx3"),
):
    """Run the full briefing pipeline on uploaded text or file."""
    from src.extract import extract_text
    from src.pipeline import run_pipeline

    if not text and not file:
        raise HTTPException(status_code=400, detail="Provide either text or a file")

    # Handle file upload
    input_path = "input/_upload.txt"
    os.makedirs("input", exist_ok=True)

    if file:
        content = await file.read()
        with open(input_path, "wb") as f:
            f.write(content)
    else:
        with open(input_path, "w") as f:
            f.write(text)

    try:
        results = run_pipeline(
            input_path=input_path,
            output_dir="output",
            tts_backend=tts_backend,
        )

        # Read briefing JSON
        with open(results["briefing_json"]) as f:
            briefing = json.load(f)

        # Read script
        with open(results["script"]) as f:
            script = f.read()

        # Get slide filenames
        slides = [os.path.basename(s) for s in results["visuals"]]

        return {
            "status": "success",
            "briefing": briefing,
            "script": script,
            "slides": slides,
            "audio": "/output/audio/narration.wav",
            "video": "/output/final_briefing.mp4",
        }
    except Exception as e:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    return {"status": "ok"}
