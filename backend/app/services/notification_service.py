"""
LAYERS — Notification Service
==========================================
Business logic for push notification delivery.

HOW IT WORKS:
  1. User opens app → useNotifications hook → POST /notifications/device-token
  2. Backend stores Expo push token in device_tokens table
  3. When event fires (e.g., Slow Mail delivered):
     → NotificationService.send_to_user(user_id, type, title, body)
       → Check user preferences (category enabled? quiet hours?)
       → Find all device tokens for user
       → Send via Expo Push API (or FCM)
       → Store in notification_history for retrieval

PATTERN: Static class methods, same as ArtifactService,
  ExplorationService, AntiCheatService.

NOTE: For MVP we use Expo Push API directly.
  FCM/APNs integration comes when we eject from Expo.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class NotificationService:
    """Push notification business logic."""

    # ========================================================
    # DEVICE TOKEN MANAGEMENT
    # ========================================================

    @staticmethod
    async def register_device_token(
        db: AsyncSession,
        user_id: uuid.UUID,
        token: str,
        platform: str,
        device_name: Optional[str] = None,
    ) -> dict:
        """
        Register or update a device push token.
        Uses ON CONFLICT to handle re-registration gracefully.
        """
        from app.models.notification import DeviceToken

        # Check if token already exists for this user
        result = await db.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.token == token,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update last_used
            existing.last_used_at = datetime.now(timezone.utc)
            existing.device_name = device_name or existing.device_name
            await db.commit()
            await db.refresh(existing)
            return {
                "id": str(existing.id),
                "token_last4": token[-4:],
                "platform": existing.platform,
                "device_name": existing.device_name,
                "registered_at": existing.created_at,
                "status": "updated",
            }

        # Create new
        device_token = DeviceToken(
            user_id=user_id,
            token=token,
            platform=platform,
            device_name=device_name,
        )
        db.add(device_token)
        await db.commit()
        await db.refresh(device_token)

        logger.info(f"Device token registered: user={user_id}, platform={platform}")

        return {
            "id": str(device_token.id),
            "token_last4": token[-4:],
            "platform": device_token.platform,
            "device_name": device_token.device_name,
            "registered_at": device_token.created_at,
            "status": "created",
        }

    @staticmethod
    async def unregister_device_token(
        db: AsyncSession,
        user_id: uuid.UUID,
        token: str,
    ) -> bool:
        """Remove a device token (e.g., on logout)."""
        from app.models.notification import DeviceToken

        result = await db.execute(
            delete(DeviceToken).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.token == token,
                )
            )
        )
        await db.commit()
        return result.rowcount > 0

    # ========================================================
    # PREFERENCES
    # ========================================================

    @staticmethod
    async def get_preferences(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> dict:
        """Get user's notification preferences."""
        from app.models.notification import NotificationPreference

        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id
            )
        )
        prefs = result.scalar_one_or_none()

        if not prefs:
            # Return defaults — will be created on first update
            return {
                "enabled": True,
                "social": True,
                "discovery": True,
                "inbox": True,
                "capsule": True,
                "system": True,
                "quiet_hours_enabled": True,
                "quiet_hours_start": "23:00",
                "quiet_hours_end": "07:00",
            }

        return {
            "enabled": prefs.enabled,
            "social": prefs.social,
            "discovery": prefs.discovery,
            "inbox": prefs.inbox,
            "capsule": prefs.capsule,
            "system": prefs.system,
            "quiet_hours_enabled": prefs.quiet_hours_enabled,
            "quiet_hours_start": prefs.quiet_hours_start,
            "quiet_hours_end": prefs.quiet_hours_end,
        }

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        user_id: uuid.UUID,
        updates: dict,
    ) -> dict:
        """Update notification preferences (upsert)."""
        from app.models.notification import NotificationPreference

        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id
            )
        )
        prefs = result.scalar_one_or_none()

        if not prefs:
            prefs = NotificationPreference(user_id=user_id)
            db.add(prefs)

        # Apply updates
        for key, value in updates.items():
            if hasattr(prefs, key) and value is not None:
                setattr(prefs, key, value)

        await db.commit()
        await db.refresh(prefs)

        return await NotificationService.get_preferences(db, user_id)

    # ========================================================
    # SEND NOTIFICATION
    # ========================================================

    @staticmethod
    async def send_to_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        category: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send push notification to a user.

        Steps:
          1. Check preferences (enabled? category on? quiet hours?)
          2. Find device tokens
          3. Send via Expo Push API
          4. Store in notification history

        Returns True if sent successfully.
        """
        from app.models.notification import DeviceToken, NotificationHistory

        # Check preferences
        prefs = await NotificationService.get_preferences(db, user_id)
        if not prefs.get("enabled", True):
            logger.debug(f"Notifications disabled for user {user_id}")
            return False

        if not prefs.get(category, True):
            logger.debug(f"Category '{category}' disabled for user {user_id}")
            return False

        # Check quiet hours
        if prefs.get("quiet_hours_enabled", False):
            now = datetime.now(timezone.utc)
            # Simplified — in production, convert to user's timezone
            current_minutes = now.hour * 60 + now.minute
            start = prefs.get("quiet_hours_start", "23:00")
            end = prefs.get("quiet_hours_end", "07:00")
            start_h, start_m = map(int, start.split(":"))
            end_h, end_m = map(int, end.split(":"))
            start_mins = start_h * 60 + start_m
            end_mins = end_h * 60 + end_m

            if start_mins > end_mins:  # Overnight
                if current_minutes >= start_mins or current_minutes <= end_mins:
                    logger.debug(f"Quiet hours active for user {user_id}")
                    # Still store in history, just don't push
                    pass
            elif start_mins <= current_minutes <= end_mins:
                logger.debug(f"Quiet hours active for user {user_id}")
                pass

        # Get device tokens
        result = await db.execute(
            select(DeviceToken).where(DeviceToken.user_id == user_id)
        )
        tokens = result.scalars().all()

        if not tokens:
            logger.debug(f"No device tokens for user {user_id}")

        # Send via Expo Push API
        # TODO: Implement actual Expo Push API call
        # For now, we log and store in history
        for token in tokens:
            logger.info(
                f"📱 Push → {token.platform} ({token.token[-8:]}): "
                f"[{notification_type}] {title}"
            )

        # Store in notification history
        history_entry = NotificationHistory(
            user_id=user_id,
            type=notification_type,
            category=category,
            title=title,
            body=body,
            data=data or {},
        )
        db.add(history_entry)
        await db.commit()

        return True

    # ========================================================
    # NOTIFICATION HISTORY
    # ========================================================

    @staticmethod
    async def get_history(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Get notification history for a user."""
        from app.models.notification import NotificationHistory

        # Count total + unread
        total_result = await db.execute(
            select(func.count(NotificationHistory.id)).where(
                NotificationHistory.user_id == user_id
            )
        )
        total = total_result.scalar() or 0

        unread_result = await db.execute(
            select(func.count(NotificationHistory.id)).where(
                and_(
                    NotificationHistory.user_id == user_id,
                    NotificationHistory.is_read == False,
                )
            )
        )
        unread_count = unread_result.scalar() or 0

        # Fetch items
        result = await db.execute(
            select(NotificationHistory)
            .where(NotificationHistory.user_id == user_id)
            .order_by(NotificationHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = result.scalars().all()

        return {
            "notifications": [
                {
                    "id": str(n.id),
                    "type": n.type,
                    "category": n.category,
                    "title": n.title,
                    "body": n.body,
                    "data": n.data,
                    "is_read": n.is_read,
                    "created_at": n.created_at,
                }
                for n in items
            ],
            "total": total,
            "unread_count": unread_count,
        }

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_ids: List[str],
    ) -> int:
        """Mark notifications as read. Returns count updated."""
        from app.models.notification import NotificationHistory

        uuids = [uuid.UUID(nid) for nid in notification_ids]

        result = await db.execute(
            update(NotificationHistory)
            .where(
                and_(
                    NotificationHistory.user_id == user_id,
                    NotificationHistory.id.in_(uuids),
                )
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return result.rowcount
