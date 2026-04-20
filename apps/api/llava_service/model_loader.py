"""LLaVA 1.6 model loader with 4-bit quantization for GPU-constrained environments."""

from __future__ import annotations
import structlog

logger = structlog.get_logger()


def load_model():
    """
    Load LLaVA 1.6 7B model with 4-bit quantization.
    Requires ~5GB VRAM. Falls back to CPU with warning.
    """
    try:
        import torch
        from transformers import AutoProcessor, LlavaForConditionalGeneration, BitsAndBytesConfig

        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

        model_id = "llava-hf/llava-v1.6-mistral-7b-hf"
        device = "cuda" if torch.cuda.is_available() else "cpu"

        if device == "cpu":
            logger.warning("llava_loading_on_cpu", note="Inference will be slow (15-30s per image)")
            processor = AutoProcessor.from_pretrained(model_id)
            model = LlavaForConditionalGeneration.from_pretrained(model_id, torch_dtype=torch.float32)
        else:
            processor = AutoProcessor.from_pretrained(model_id)
            model = LlavaForConditionalGeneration.from_pretrained(
                model_id, quantization_config=quantization_config, device_map="auto",
            )

        logger.info("llava_model_loaded", device=device, model=model_id)
        return {"model": model, "processor": processor, "device": device}

    except Exception as e:
        logger.error("llava_model_load_failed", error=str(e))
        raise
