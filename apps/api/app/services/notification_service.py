"""
Aujasya — Notification Service
Unified dispatch for push, WhatsApp, SMS, and IVR channels.
All notifications are logged to the notification_logs table.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.notification_log import NotificationLog
from app.utils.timezone import now_ist

logger = structlog.get_logger()


class NotificationService:
    """
    Unified notification dispatcher.
    Dispatches to: FCM Push, Wati WhatsApp, Msg91 SMS.
    All dispatches are logged to notification_logs.
    Gracefully degrades when API keys are not configured.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def send_push(
        self,
        patient_id: uuid.UUID,
        title: str,
        body: str,
        dose_log_id: uuid.UUID | None = None,
        level: int = 1,
    ) -> bool:
        """Send FCM push notification."""
        success = False

        if settings.FIREBASE_PROJECT_ID:
            try:
                import firebase_admin
                from firebase_admin import messaging

                # Get user's FCM token
                from sqlalchemy import select
                from app.models.push_subscription import PushSubscription

                stmt = select(PushSubscription).where(
                    PushSubscription.user_id == patient_id,
                    PushSubscription.is_active == True,  # noqa: E712
                )
                result = await self.db.execute(stmt)
                subscriptions = result.scalars().all()

                for sub in subscriptions:
                    try:
                        message = messaging.Message(
                            notification=messaging.Notification(
                                title=title,
                                body=body,
                            ),
                            token=sub.fcm_token,
                            data={"dose_log_id": str(dose_log_id) if dose_log_id else ""},
                        )
                        messaging.send(message)
                        success = True
                    except Exception as e:
                        logger.error(
                            "fcm_send_failed",
                            error=str(e),
                            token_prefix=sub.fcm_token[:10],
                        )
                        # Mark token as inactive if invalid
                        if "NOT_FOUND" in str(e) or "INVALID" in str(e):
                            sub.is_active = False

            except Exception as e:
                logger.error("push_notification_failed", error=str(e))
        else:
            logger.warning("firebase_not_configured")

        # Log the notification
        await self._log_notification(
            patient_id=patient_id,
            dose_log_id=dose_log_id,
            channel="push",
            level=level,
            status="sent" if success else "failed",
        )

        return success

    async def send_whatsapp(
        self,
        phone: str,
        template_name: str,
        params: list[str],
        patient_id: uuid.UUID,
        dose_log_id: uuid.UUID | None = None,
        level: int = 2,
    ) -> bool:
        """Send WhatsApp message via Wati."""
        success = False

        if settings.WATI_API_TOKEN:
            try:
                import httpx

                # Strip + from phone for Wati API
                wati_phone = phone.lstrip("+")

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{settings.WATI_API_URL}/api/v1/sendTemplateMessage",
                        headers={
                            "Authorization": f"Bearer {settings.WATI_API_TOKEN}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "template_name": template_name,
                            "broadcast_name": "aujasya_reminder",
                            "parameters": [{"name": f"p{i+1}", "value": p} for i, p in enumerate(params)],
                        },
                        params={"whatsappNumber": wati_phone},
                        timeout=15.0,
                    )
                    success = response.status_code == 200

                    if not success:
                        logger.error(
                            "wati_send_failed",
                            status=response.status_code,
                            phone_last4=phone[-4:],
                        )

            except Exception as e:
                logger.error("whatsapp_send_failed", error=str(e))
        else:
            logger.warning("wati_not_configured")

        await self._log_notification(
            patient_id=patient_id,
            dose_log_id=dose_log_id,
            channel="whatsapp",
            level=level,
            status="sent" if success else "failed",
        )

        return success

    async def send_sms(
        self,
        phone: str,
        message: str,
        patient_id: uuid.UUID,
        dose_log_id: uuid.UUID | None = None,
        level: int = 3,
    ) -> bool:
        """Send SMS via Msg91."""
        success = False

        if settings.MSG91_API_KEY:
            try:
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.msg91.com/api/v5/flow/",
                        headers={"authkey": settings.MSG91_API_KEY},
                        json={
                            "template_id": settings.MSG91_TEMPLATE_ID_REMINDER,
                            "recipients": [
                                {"mobiles": phone.replace("+", ""), "message": message}
                            ],
                        },
                        timeout=10.0,
                    )
                    success = response.status_code == 200

            except Exception as e:
                logger.error("sms_send_failed", error=str(e))
        else:
            logger.warning("msg91_not_configured")

        await self._log_notification(
            patient_id=patient_id,
            dose_log_id=dose_log_id,
            channel="sms",
            level=level,
            status="sent" if success else "failed",
        )

        return success

    # ── Phase 2: IVR via Exotel ──────────────────────────────────────────

    async def send_ivr(
        self,
        phone: str,
        patient_id: uuid.UUID,
        dose_log_id: uuid.UUID | None = None,
        tts_message: str = "Aapki dawai ka samay ho gaya hai. Kripya apni dawai lein.",
        level: int = 4,
    ) -> bool:
        """
        Send IVR call via Exotel (Level 4 escalation).
        Circuit breaker: If Exotel is down, skip IVR and escalate via WhatsApp.
        TTS message is in Hindi by default (Aujasya's primary user base).
        """
        success = False

        if settings.EXOTEL_ACCOUNT_SID and settings.EXOTEL_API_KEY:
            try:
                import httpx

                exotel_url = (
                    f"https://api.exotel.com/v1/Accounts/{settings.EXOTEL_ACCOUNT_SID}"
                    f"/Calls/connect.json"
                )

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        exotel_url,
                        auth=(settings.EXOTEL_API_KEY, settings.EXOTEL_API_TOKEN),
                        data={
                            "From": phone,
                            "CallerId": settings.EXOTEL_CALLER_ID,
                            "Url": f"http://my.exotel.com/exoml/start_voice/{settings.EXOTEL_ACCOUNT_SID}",
                            "CustomField": tts_message,
                            "StatusCallback": "",  # TODO: Add callback URL for call status tracking
                        },
                    )
                    success = response.status_code in (200, 201)

                    if not success:
                        logger.error(
                            "exotel_ivr_failed",
                            status=response.status_code,
                            phone_last4=phone[-4:],
                        )

            except Exception as e:
                logger.error("ivr_send_failed", error=str(e))
                # Fallback: escalate via WhatsApp when IVR is unavailable
                logger.info("ivr_fallback_to_whatsapp", phone_last4=phone[-4:])
                return await self.send_whatsapp(
                    phone=phone,
                    template_name="missed_dose_urgent",
                    params=[tts_message],
                    patient_id=patient_id,
                    dose_log_id=dose_log_id,
                    level=level,
                )
        else:
            logger.warning("exotel_not_configured")
            # Fallback to WhatsApp if Exotel not configured
            return await self.send_whatsapp(
                phone=phone,
                template_name="missed_dose_urgent",
                params=[tts_message],
                patient_id=patient_id,
                dose_log_id=dose_log_id,
                level=level,
            )

        await self._log_notification(
            patient_id=patient_id,
            dose_log_id=dose_log_id,
            channel="ivr",
            level=level,
            status="sent" if success else "failed",
        )

        return success

    async def _log_notification(
        self,
        patient_id: uuid.UUID,
        dose_log_id: uuid.UUID | None,
        channel: str,
        level: int,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """[FIX-11] Log notification to the notification_logs table."""
        log_entry = NotificationLog(
            patient_id=patient_id,
            dose_log_id=dose_log_id,
            channel=channel,
            level=level,
            status=status,
            error_message=error_message,
        )
        self.db.add(log_entry)
        await self.db.flush()
