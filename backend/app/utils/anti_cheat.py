"""
LAYERS - Anti-Cheat Validation & Middleware
===========================================
FILE: backend/app/utils/anti_cheat.py (hoặc backend/app/middleware/anti_cheat.py)

Intercepts location-related API requests and validates them
against the anti-cheat detection pipeline.

HOW TO USE (As Dependency):
  @router.post("/explore", dependencies=[Depends(validate_location)])
  async def explore(...)
  
  OR (As Direct Call in Router):
  from app.utils.anti_cheat import validate_location_update
  
  @router.post("/explore")
  async def explore(data: ExploreRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
      await validate_location_update(current_user.id, data.latitude, data.longitude, db)
      ...

WHAT IT DOES:
  1. Checks if the user is already banned (handles expired temp bans).
  2. Extracts location metadata (from request body, query params, or direct args).
  3. Runs all detection checks via AntiCheatService.
  4. If critical → Adds strike + Returns 403 Forbidden
  5. If suspicious → Logs + Adds strike (allows request to pass)
  6. If clean → Passes through normally
"""

from typing import Optional
from uuid import UUID

from fastapi import Request, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.anti_cheat_service import (
    LocationMetadata,
    AntiCheatService,
)

# Shared helper: handle result from analyze_location consistently across all validators
async def _handle_result(result, user_id, db) -> None:
    """
    Apply strike logic based on detection result severity:
    - critical  → immediate strike + (optionally) raise 403
    - suspicious → increment sliding-window counter; strike after N events
    - warning   → log only (no action)

    Raises HTTPException if the violation is critical and should_ban is True.
    Returns normally otherwise.
    """
    if result.is_clean:
        return

    if result.severity == "critical":
        strikes = await AntiCheatService.add_strike(user_id, db)
        if result.should_ban:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "CHEAT_DETECTED",
                    "message": "Location spoofing detected. Your account has been flagged.",
                    "violations": result.violations,
                    "strikes": strikes,
                },
            )
    elif result.severity == "suspicious":
        # Accumulate; only strike after SUSPICIOUS_EVENTS_PER_STRIKE occurrences
        for violation in result.violations:
            await AntiCheatService.add_suspicious_event(user_id, db, violation)
    # warning = already logged by analyze_location, no further action


# ============================================================
# 1. FASTAPI DEPENDENCY (FOR REQUEST BODY)
# ============================================================
async def validate_location(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that validates location data in request body.
    
    Add to any endpoint that receives location data:
    
        @router.post("/explore")
        async def explore(
            data: ExploreRequest,
            user: User = Depends(validate_location),
            db: AsyncSession = Depends(get_db),
        ):
            # user is guaranteed to be clean here
            ...
    
    Raises HTTPException if:
    - User is banned
    - Critical cheat detected (isMocked, teleport)
    """
    # Step 1: Check ban status first (includes auto-unban for expired temp bans)
    is_banned = await AntiCheatService.check_user_banned(current_user.id, db)
    if is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ACCOUNT_BANNED",
                "message": "Your account has been suspended for violating location integrity rules.",
                "action": "Contact support to appeal.",
            }
        )
    
    # Step 2: Try to extract location metadata from request body
    try:
        body = await request.json()
    except Exception:
        # Not a JSON request or no body — skip validation
        return current_user
    
    # Look for location fields in request body
    latitude = body.get("latitude")
    longitude = body.get("longitude")
    
    if latitude is None or longitude is None:
        # No location data in this request — skip validation
        return current_user
    
    # Build LocationMetadata from request body
    metadata = LocationMetadata(
        latitude=latitude,
        longitude=longitude,
        accuracy=body.get("accuracy", 10.0),
        altitude=body.get("altitude"),
        speed=body.get("speed"),
        is_mocked=body.get("is_mocked", False),
        accelerometer_magnitude=body.get("accelerometer_magnitude"),
        provider=body.get("provider"),
    )
    
    # Step 3: Run anti-cheat analysis + apply strike logic
    result = await AntiCheatService.analyze_location(current_user.id, metadata)
    await _handle_result(result, current_user.id, db)
    return current_user


# ============================================================
# 2. FASTAPI DEPENDENCY (FOR QUERY PARAMETERS)
# ============================================================
async def require_clean_location(
    latitude: float,
    longitude: float,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    is_mocked: bool = False,
    accelerometer_magnitude: Optional[float] = None,
    provider: Optional[str] = None,
) -> User:
    """
    Simpler dependency for Query Parameter based endpoints.
    
    Use when location is passed as query params instead of body:
    
        @router.get("/nearby")
        async def get_nearby(
            lat: float, lon: float,
            user: User = Depends(require_clean_location),
        ):
            ...
    """
    is_banned = await AntiCheatService.check_user_banned(current_user.id, db)
    if is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ACCOUNT_BANNED",
                "message": "Your account has been suspended for violating location integrity rules."
            }
        )
    
    metadata = LocationMetadata(
        latitude=latitude,
        longitude=longitude,
        is_mocked=is_mocked,
        accelerometer_magnitude=accelerometer_magnitude,
        provider=provider,
    )
    
    result = await AntiCheatService.analyze_location(current_user.id, metadata)
    await _handle_result(result, current_user.id, db)
    return current_user


# ============================================================
# 3. DIRECT FUNCTION CALL (FOR ROUTER LOGIC)
# ============================================================
async def validate_location_update(
    user_id: UUID,
    latitude: float,
    longitude: float,
    db: AsyncSession,
    is_mocked: bool = False,
    accelerometer_magnitude: Optional[float] = None,
    provider: Optional[str] = None,
) -> None:
    """
    Quick validation function for use directly inside endpoint handlers.
    
    Raises HTTPException 403 if cheat detected.
    Returns None if clean (no return value needed).
    
    Can be called from explore, map, artifacts — any location endpoint.
    """
    # Check ban status first (includes auto-unban for expired temp bans)
    is_banned = await AntiCheatService.check_user_banned(user_id, db)
    if is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ACCOUNT_BANNED",
                "message": "Your account has been suspended for violating location integrity rules.",
                "action": "Contact support to appeal.",
            }
        )

    # Run detection pipeline
    metadata = LocationMetadata(
        latitude=latitude,
        longitude=longitude,
        is_mocked=is_mocked,
        accelerometer_magnitude=accelerometer_magnitude,
        provider=provider,
    )

    result = await AntiCheatService.analyze_location(user_id, metadata)
    await _handle_result(result, user_id, db)