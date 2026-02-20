"""
LAYERS - Anti-Cheat API Router
================================
FILE: backend/app/api/v1/anti_cheat.py

Endpoints for managing the Anti-Cheat system.

Public (Authenticated):
  POST  /validate   — Test detection logic (useful for client dev)
  GET   /my-status  — Check own ban status and strikes

Admin Only:
  GET   /admin/log/{id}    — View cheat log & location history
  POST  /admin/ban/{id}    — Manually ban a user
  POST  /admin/unban/{id}  — Manually unban a user
  GET   /admin/stats       — System-wide statistics

HOW TO REGISTER:
  In app/api/v1/router.py:
  
  from app.api.v1.anti_cheat import router as anti_cheat_router
  api_router.include_router(anti_cheat_router)
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.anti_cheat_service import (
    LocationMetadata,
    CheatDetectionResult,
    AntiCheatService,
    get_user_history,
)

# Prefix is defined here or in the main router include
router = APIRouter(prefix="/anti-cheat", tags=["Anti-Cheat"])


# ============================================================
# HELPER: Require Admin Role
# ============================================================
async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to ensure the user has ADMIN role.
    Handles both string 'ADMIN' and Enum cases.
    """
    role = str(current_user.role).upper()
    # Adjust logic based on whether you use Enum or String for roles
    if "ADMIN" not in role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================================
# 1. PUBLIC ENDPOINTS (Authenticated)
# ============================================================

@router.post(
    "/validate",
    response_model=CheatDetectionResult,
    summary="Test anti-cheat detection on a location update",
    description="""
    Submit a location update and see what the anti-cheat system detects.
    
    Useful for:
    - Testing your app's location data format
    - Seeing what violations are caught
    - Development debugging
    
    **Note:** This DOES update your location history and CAN trigger strikes.
    """,
)
async def validate_location(
    metadata: LocationMetadata,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if user is banned first
    is_banned = await AntiCheatService.check_user_banned(current_user.id, db)
    if is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ACCOUNT_BANNED",
                "message": "Your account has been suspended for violating location integrity rules.",
            }
        )

    # Run analysis
    result = await AntiCheatService.analyze_location(current_user.id, metadata)

    # Apply penalties if critical
    if result.severity == "critical":
        await AntiCheatService.add_strike(current_user.id, db)

    return result


@router.get(
    "/my-status",
    summary="Check your own anti-cheat status",
    description="See if you're banned, your strike count, and location history size.",
)
async def get_my_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = get_user_history(current_user.id)
    # Check banned status (handles auto-unban logic)
    is_banned = await AntiCheatService.check_user_banned(current_user.id, db)

    return {
        "user_id": str(current_user.id),
        "is_banned": is_banned,
        "is_active": current_user.is_active,
        "cheat_strikes": getattr(current_user, "cheat_strikes", 0),
        "reputation_score": current_user.reputation_score,
        "banned_until": current_user.banned_until,
        "ban_reason": current_user.ban_reason,
        "location_history_count": len(history),
        "last_known_position": {
            "latitude": history[-1].latitude,
            "longitude": history[-1].longitude,
            "timestamp": history[-1].timestamp.isoformat(),
            "accuracy": history[-1].accuracy,
        } if history else None,
    }


# ============================================================
# 2. ADMIN ENDPOINTS
# ============================================================

@router.get(
    "/admin/log/{user_id}",
    summary="[ADMIN] View cheat detection log for a user",
    dependencies=[Depends(require_admin)],
)
async def admin_get_cheat_log(
    user_id: UUID,
):
    """
    Get a specific user's location history and cheat logs.
    """
    log = await AntiCheatService.get_cheat_log(user_id)
    history = get_user_history(user_id)

    return {
        **log,
        "recent_positions": [
            {
                "latitude": h.latitude,
                "longitude": h.longitude,
                "timestamp": h.timestamp.isoformat(),
                "accuracy": h.accuracy,
            }
            for h in history[-20:]  # Return last 20 for quick review
        ],
    }


@router.post(
    "/admin/ban/{user_id}",
    summary="[ADMIN] Ban a user for cheating",
)
async def admin_ban_user(
    user_id: UUID,
    permanent: bool = False,
    reason: str = "Manual admin ban for cheating",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually ban a user.
    - permanent=False: 24 hour ban
    - permanent=True: Indefinite ban
    """
    # Safety: Prevent admin from banning themselves
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot ban yourself"
        )

    await AntiCheatService.ban_user(user_id, db, permanent=permanent, reason=reason)

    return {
        "message": f"User {'permanently' if permanent else 'temporarily'} banned",
        "user_id": str(user_id),
        "ban_type": "permanent" if permanent else "24h_temp",
        "reason": reason,
    }


@router.post(
    "/admin/unban/{user_id}",
    summary="[ADMIN] Unban a user",
    dependencies=[Depends(require_admin)],
)
async def admin_unban_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually unban a user and reset their strike count.
    """
    await AntiCheatService.unban_user(user_id, db)

    return {
        "message": "User unbanned successfully",
        "user_id": str(user_id),
    }


@router.get(
    "/admin/stats",
    summary="[ADMIN] Anti-cheat system statistics",
    dependencies=[Depends(require_admin)],
)
async def admin_get_stats():
    """
    View global stats about the anti-cheat system (users tracked, data points).
    """
    # Accessing the internal storage variable from service
    from app.services.anti_cheat_service import _location_history

    total_users = len(_location_history)
    total_points = sum(len(h) for h in _location_history.values())

    return {
        "tracked_users": total_users,
        "total_location_points": total_points,
        "avg_points_per_user": round(total_points / max(total_users, 1), 1),
        "detection_methods": [
            "isMocked flag check",
            "Teleport/jump detection (>5km/1s)",
            "Sensor mismatch (accelerometer vs GPS)",
            "Pattern analysis (static coords, perfect accuracy)",
        ],
        "penalty_system": {
            "strike_1": "Warning + -50 reputation",
            "strike_2": "24h temporary ban",
            "strike_3": "Permanent ban",
        },
    }