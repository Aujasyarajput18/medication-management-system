"""
Aujasya — LLaVA Microservice
FastAPI app on port 8001 for handwritten prescription OCR.
Runs in a separate Docker container with GPU access.
LLAVA_MOCK=true returns fixture JSON without loading the model.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

logger = structlog.get_logger()

MOCK_MODE = os.getenv("LLAVA_MOCK", "true").lower() == "true"
model_instance = None


class OcrResult(BaseModel):
    raw_text: str
    confidence: float
    entities: dict


MOCK_RESPONSE = OcrResult(
    raw_text="Tab Metformin 500mg | 1-0-1 | After food | Dr. Sharma",
    confidence=0.82,
    entities={
        "drug_name": "Metformin 500mg",
        "dosage": "500mg",
        "frequency": "1-0-1",
        "instructions": "After food",
        "prescribed_by": "Dr. Sharma",
    },
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_instance
    if not MOCK_MODE:
        from model_loader import load_model
        logger.info("loading_llava_model")
        model_instance = load_model()
        logger.info("llava_model_loaded")
    else:
        logger.info("llava_running_in_mock_mode")
    yield
    model_instance = None


app = FastAPI(
    title="Aujasya LLaVA OCR Service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "mock": MOCK_MODE, "model_loaded": model_instance is not None}


@app.post("/ocr", response_model=OcrResult)
async def ocr_prescription(image: UploadFile = File(...)):
    """Process a prescription image through LLaVA for OCR."""
    if MOCK_MODE:
        return MOCK_RESPONSE

    if model_instance is None:
        raise HTTPException(503, "Model not loaded")

    contents = await image.read()
    max_size = int(os.getenv("LLAVA_MAX_IMAGE_SIZE_MB", "10")) * 1024 * 1024
    if len(contents) > max_size:
        raise HTTPException(413, f"Image exceeds {max_size // (1024*1024)}MB limit")

    try:
        from inference import run_inference
        result = run_inference(model_instance, contents)
        return result
    except Exception as e:
        logger.error("llava_inference_failed", error=str(e))
        raise HTTPException(500, "OCR inference failed")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
