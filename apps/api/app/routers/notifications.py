"""
Aujasya — Notifications Router
4 endpoints: push subscribe, get preferences, update preferences, test push.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, DbSession
from app.models.push_subscription import PushSubscription
from app.schemas.notification import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    PushSubscribeRequest,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post(
    "/push-subscribe",
    status_code=status.HTTP_201_CREATED,
    summary="Register FCM push token",
)
async def push_subscribe(
    body: PushSubscribeRequest,
    user: CurrentUser,
    db: DbSession,
) -> dict:
    """Register or update FCM push notification token for the current device."""
    # Check if token already exists
    stmt = select(PushSubscription).where(
        PushSubscription.user_id == user.id,
        PushSubscription.fcm_token == body.fcm_token,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.is_active = True
        existing.platform = body.platform
    else:
        sub = PushSubscription(
            user_id=user.id,
            fcm_token=body.fcm_token,
            platform=body.platform,
        )
        db.add(sub)

    await db.flush()
    return {"success": True, "message": "Push subscription registered"}


@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Get notification preferences",
)
async def get_preferences(user: CurrentUser) -> NotificationPreferencesResponse:
    """Get notification preferences for the current user."""
    # Phase 1: return defaults. Phase 2: stored per-user preferences.
    return NotificationPreferencesResponse()


@router.patch(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Update notification preferences",
)
async def update_preferences(
    body: NotificationPreferencesUpdate,
    user: CurrentUser,
) -> NotificationPreferencesResponse:
    """Update notification preferences. Phase 1: stored in Redis/DB."""
    # Phase 1: acknowledge update, return defaults
    return NotificationPreferencesResponse(
        enable_whatsapp=body.enable_whatsapp or False,
        enable_sms=body.enable_sms or False,
        enable_ivr=body.enable_ivr or False,
        escalation_delay_minutes=body.escalation_delay_minutes or 30,
    )


@router.post("/test-push", summary="Send test push notification")
async def test_push(
    user: CurrentUser,
    db: DbSession,
) -> dict:
    """Send a test push notification to verify FCM setup."""
    from app.services.notification_service import NotificationService

    service = NotificationService(db)
    success = await service.send_push(
        patient_id=user.id,
        title="Aujasya Test",
        body="Push notifications are working! 🎉",
    )

    if success:
        return {"success": True, "message": "Test notification sent"}
    return {"success": False, "message": "Failed to send test notification. Check FCM configuration."}
