"""
Aujasya — Bhashini STT/TTS Service
India's national language AI platform for speech-to-text and text-to-speech.
Circuit breaker protected.
"""

from __future__ import annotations

import structlog
import httpx
from redis.asyncio import Redis

from app.config import settings
from app.utils.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()


class BhashiniService:
    """Bhashini API client for STT and TTS."""

    def __init__(self, redis: Redis) -> None:
        self.breaker = CircuitBreaker(redis, "bhashini", failure_threshold=5, recovery_timeout_s=60)

    async def speech_to_text(self, audio_bytes: bytes, language: str = "hi") -> dict:
        """
        Convert speech to text via Bhashini STT.
        Audio is NOT persisted (DPDPA compliance) — processed in memory only.
        """
        if await self.breaker.is_open():
            return {"transcript": "", "error": "service_unavailable"}

        if not settings.BHASHINI_API_KEY:
            logger.warning("bhashini_not_configured")
            return {"transcript": "", "error": "not_configured"}

        try:
            import base64
            audio_b64 = base64.b64encode(audio_bytes).decode()

            payload = {
                "pipelineTasks": [{
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": language},
                        "serviceId": settings.BHASHINI_STT_SERVICE_ID,
                        "audioFormat": "wav",
                        "samplingRate": 16000,
                    },
                }],
                "inputData": {
                    "audio": [{"audioContent": audio_b64}],
                },
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.BHASHINI_API_URL}/services/inference/pipeline",
                    json=payload,
                    headers={
                        "Authorization": settings.BHASHINI_API_KEY,
                        "userID": settings.BHASHINI_USER_ID,
                        "Content-Type": "application/json",
                    },
                )

            if resp.status_code == 200:
                await self.breaker.record_success()
                data = resp.json()
                outputs = data.get("pipelineResponse", [{}])
                transcript = ""
                if outputs:
                    output_data = outputs[0].get("output", [{}])
                    if output_data:
                        transcript = output_data[0].get("source", "")
                return {"transcript": transcript, "language": language}
            else:
                await self.breaker.record_failure()
                logger.error("bhashini_stt_failed", status=resp.status_code)
                return {"transcript": "", "error": "api_error"}

        except Exception as e:
            await self.breaker.record_failure()
            logger.error("bhashini_stt_error", error=str(e))
            return {"transcript": "", "error": str(e)}

    async def text_to_speech(self, text: str, language: str = "hi") -> bytes | None:
        """Convert text to speech via Bhashini TTS. Returns WAV audio bytes."""
        if await self.breaker.is_open() or not settings.BHASHINI_API_KEY:
            return None

        try:
            payload = {
                "pipelineTasks": [{
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": language},
                        "serviceId": settings.BHASHINI_TTS_SERVICE_ID,
                        "gender": "female",
                    },
                }],
                "inputData": {
                    "input": [{"source": text}],
                },
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.BHASHINI_API_URL}/services/inference/pipeline",
                    json=payload,
                    headers={
                        "Authorization": settings.BHASHINI_API_KEY,
                        "userID": settings.BHASHINI_USER_ID,
                    },
                )

            if resp.status_code == 200:
                await self.breaker.record_success()
                import base64
                data = resp.json()
                outputs = data.get("pipelineResponse", [{}])
                if outputs:
                    audio_data = outputs[0].get("audio", [{}])
                    if audio_data:
                        audio_b64 = audio_data[0].get("audioContent", "")
                        return base64.b64decode(audio_b64)
            await self.breaker.record_failure()
            return None

        except Exception as e:
            await self.breaker.record_failure()
            logger.error("bhashini_tts_error", error=str(e))
            return None
