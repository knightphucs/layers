"""
LAYERS — Notification Endpoints
==========================================
API routes for push notification management.

Endpoints:
  POST   /notifications/device-token    — Register push token
  DELETE /notifications/device-token    — Unregister push token
  GET    /notifications/preferences     — Get preferences
  PUT    /notifications/preferences     — Update preferences
  GET    /notifications/history         — Notification history
  POST   /notifications/read           — Mark as read
  POST   /notifications/clear-badge    — Clear badge count
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService
from app.schemas.notification import (
    DeviceTokenCreate,
    NotificationPreferencesUpdate,
    MarkReadRequest,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============================================================
# POST /notifications/device-token — Register push token
# ============================================================

@router.post(
    "/device-token",
    status_code=status.HTTP_201_CREATED,
    summary="Register device for push notifications",
    description="Store Expo push token. Called automatically when app opens.",
)
async def register_device_token(
    data: DeviceTokenCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await NotificationService.register_device_token(
        db=db,
        user_id=current_user.id,
        token=data.token,
        platform=data.platform,
        device_name=data.device_name,
    )


# ============================================================
# DELETE /notifications/device-token — Unregister
# ============================================================

@router.delete(
    "/device-token",
    summary="Unregister device (e.g., on logout)",
)
async def unregister_device_token(
    token: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await NotificationService.unregister_device_token(
        db=db, user_id=current_user.id, token=token,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"status": "deleted"}


# ============================================================
# GET /notifications/preferences — Get preferences
# ============================================================

@router.get(
    "/preferences",
    summary="Get notification preferences",
)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await NotificationService.get_preferences(
        db=db, user_id=current_user.id,
    )


# ============================================================
# PUT /notifications/preferences — Update preferences
# ============================================================

@router.put(
    "/preferences",
    summary="Update notification preferences",
    description="Partial update — only send fields you want to change.",
)
async def update_preferences(
    data: NotificationPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    return await NotificationService.update_preferences(
        db=db, user_id=current_user.id, updates=updates,
    )


# ============================================================
# GET /notifications/history — Recent notifications
# ============================================================

@router.get(
    "/history",
    summary="Get notification history",
    description="Last 50 notifications with read/unread status.",
)
async def get_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await NotificationService.get_history(
        db=db, user_id=current_user.id, limit=limit, offset=offset,
    )


# ============================================================
# POST /notifications/read — Mark as read
# ============================================================

@router.post(
    "/read",
    summary="Mark notifications as read",
)
async def mark_as_read(
    data: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await NotificationService.mark_as_read(
        db=db,
        user_id=current_user.id,
        notification_ids=data.notification_ids,
    )
    return {"marked_read": count}


# ============================================================
# POST /notifications/clear-badge — Clear app badge
# ============================================================

@router.post(
    "/clear-badge",
    summary="Clear notification badge count",
)
async def clear_badge(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Badge is client-side. This endpoint is for future
    # server-side badge tracking (e.g., Apple badge push).
    return {"status": "cleared"}
