"""LLaVA inference for prescription OCR with structured prompt."""

from __future__ import annotations

import io
import json
import re

import structlog
from PIL import Image

logger = structlog.get_logger()

PRESCRIPTION_PROMPT = """<image>
You are reading an Indian medical prescription. Extract the following fields as JSON:
- drug_name: the medicine name with dosage (e.g., "Metformin 500mg")
- dosage: the dosage amount (e.g., "500mg")
- frequency: how often to take it (e.g., "1-0-1" means morning-afternoon-night)
- instructions: meal timing or special instructions (e.g., "After food")
- prescribed_by: doctor name if visible
- duration: treatment duration if mentioned (e.g., "15 days")

Return ONLY valid JSON. If a field is not visible, set it to null.
Handle both printed text and handwritten prescriptions.
Common Indian prescription abbreviations: OD=once daily, BD=twice daily, TDS=thrice daily, SOS=as needed.
"""


def run_inference(model_ctx: dict, image_bytes: bytes) -> dict:
    """Run LLaVA inference on a prescription image."""
    import torch

    model = model_ctx["model"]
    processor = model_ctx["processor"]

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if max(image.size) > 1024:
        image.thumbnail((1024, 1024), Image.LANCZOS)

    inputs = processor(text=PRESCRIPTION_PROMPT, images=image, return_tensors="pt")
    if model_ctx["device"] == "cuda":
        inputs = {k: v.to("cuda") if hasattr(v, "to") else v for k, v in inputs.items()}

    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=512, temperature=0.1, do_sample=False)

    raw_output = processor.decode(output_ids[0], skip_special_tokens=True)
    raw_text = raw_output.split("ASSISTANT:")[-1].strip() if "ASSISTANT:" in raw_output else raw_output

    entities = _parse_json_output(raw_text)
    confidence = 0.75 if entities.get("drug_name") else 0.3

    return {"raw_text": raw_text, "confidence": confidence, "entities": entities}


def _parse_json_output(text: str) -> dict:
    """Best-effort JSON extraction from LLaVA output."""
    try:
        json_match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, AttributeError):
        pass

    return {
        "drug_name": None, "dosage": None, "frequency": None,
        "instructions": None, "prescribed_by": None, "duration": None,
    }
