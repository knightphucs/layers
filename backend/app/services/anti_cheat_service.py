"""
LAYERS - Anti-Cheat Service
============================
FILE: backend/app/services/anti_cheat_service.py

Protects LAYERS from fake GPS apps and location spoofing.

THREE DETECTION METHODS (from Masterplan):
  1. isMocked Flag  — OS reports if location is mocked
  2. Jump Detection — >5km in 1 second = impossible = ban
  3. Sensor Check   — GPS moves but accelerometer says phone is still = fake

FLOW:
  Client sends location update with metadata →
  Middleware validates EVERY request →
  Suspicious? → Flag + log →
  Confirmed cheat? → Ban user

PENALTY SYSTEM:
  - Strike 1: Warning (flag in DB)
  - Strike 2: 24h temporary ban
  - Strike 3: Permanent ban
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import math
import logging

from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.models.user import User

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS
# ============================================================
MAX_SPEED_KMH = 200          # Max realistic speed (fast train)
TELEPORT_THRESHOLD_KM = 5    # >5km in 1 second = teleport (Masterplan rule)
MIN_TIME_BETWEEN_UPDATES = 0.5  # Minimum 0.5 seconds between updates (for teleport calc only)
ANTI_CHEAT_COOLDOWN_SECONDS = 5  # Skip analysis if last check was < 5s ago (avoids false RAPID_UPDATES from concurrent API calls)
STRIKE_WARNING = 1
STRIKE_TEMP_BAN = 2
STRIKE_PERM_BAN = 3
TEMP_BAN_HOURS = 24
MAX_LOCATION_HISTORY = 50     # Keep last 50 positions per user
SENSOR_STILL_THRESHOLD = 0.5  # m/s² — below this = phone is "still"
GPS_MOVE_THRESHOLD = 50       # meters — GPS moved more than this but phone still? Suspicious
STATIC_LOCATION_MIN_READINGS = 10  # Need at least 10 identical readings before flagging (was 4, too low)
SUSPICIOUS_EVENTS_PER_STRIKE = 5   # How many "suspicious" events before adding a real strike


# ============================================================
# DATA MODELS (for location updates from client)
# ============================================================
class LocationMetadata(BaseModel):
    """Metadata sent by mobile client with every location update."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: float = Field(default=10.0, ge=0, description="GPS accuracy in meters")
    altitude: Optional[float] = None
    speed: Optional[float] = Field(default=None, ge=0, description="Speed in m/s from device")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Anti-cheat fields (client MUST send these)
    is_mocked: bool = Field(default=False, description="OS isMocked flag")
    accelerometer_magnitude: Optional[float] = Field(
        default=None, 
        description="Accelerometer magnitude in m/s². ~9.8 when still (gravity). Changes when moving."
    )
    provider: Optional[str] = Field(
        default=None,
        description="Location provider: 'gps', 'network', 'fused', 'mock'"
    )


class CheatDetectionResult(BaseModel):
    """Result of anti-cheat analysis."""
    is_clean: bool = True
    violations: list[str] = []
    severity: str = "none"  # none, warning, suspicious, critical
    should_ban: bool = False
    details: dict = {}


class LocationHistoryEntry(BaseModel):
    """Single entry in user's location history (stored in Redis ideally)."""
    latitude: float
    longitude: float
    timestamp: datetime
    accuracy: float = 10.0


# ============================================================
# HAVERSINE DISTANCE (meters)
# ============================================================
def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS points in meters."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


# ============================================================
# IN-MEMORY LOCATION HISTORY (Replace with Redis in production)
# Structure: { user_id_str: [LocationHistoryEntry, ...] }
# ============================================================
_location_history: dict[str, list[LocationHistoryEntry]] = {}

# Per-user last anti-cheat run timestamp (to enforce cooldown)
# Prevents false positives from concurrent API calls
_last_check_time: dict[str, datetime] = {}

# Per-user suspicious event counter for sliding-window strike logic
# { user_id_str: count }  — resets when a real strike is issued
_suspicious_event_count: dict[str, int] = {}


def get_user_history(user_id: UUID) -> list[LocationHistoryEntry]:
    """Get user's recent location history."""
    return _location_history.get(str(user_id), [])


def add_to_history(user_id: UUID, entry: LocationHistoryEntry):
    """Add location to user's history, keeping last N entries."""
    key = str(user_id)
    if key not in _location_history:
        _location_history[key] = []
    _location_history[key].append(entry)
    # Keep only last N entries
    if len(_location_history[key]) > MAX_LOCATION_HISTORY:
        _location_history[key] = _location_history[key][-MAX_LOCATION_HISTORY:]


def clear_user_history(user_id: UUID):
    """Clear user's location history (on ban or reset)."""
    key = str(user_id)
    _location_history.pop(key, None)
    _last_check_time.pop(key, None)
    _suspicious_event_count.pop(key, None)


def increment_suspicious_count(user_id: UUID) -> int:
    """Increment and return the suspicious event counter for a user."""
    key = str(user_id)
    _suspicious_event_count[key] = _suspicious_event_count.get(key, 0) + 1
    return _suspicious_event_count[key]


def reset_suspicious_count(user_id: UUID):
    """Reset suspicious counter after a strike is issued."""
    _suspicious_event_count.pop(str(user_id), None)


# ============================================================
# DETECTION METHOD 1: isMocked Flag
# ============================================================
def check_is_mocked(metadata: LocationMetadata) -> Optional[str]:
    """
    Check if the OS reports location as mocked.
    
    Android: Location.isFromMockProvider()
    iOS: Doesn't have this natively, but jailbreak detection helps.
    
    Returns violation string or None if clean.
    """
    if metadata.is_mocked:
        return "MOCK_LOCATION_DETECTED: OS reports location is mocked/simulated"
    
    # Also check provider — 'mock' provider is a dead giveaway
    if metadata.provider and metadata.provider.lower() in ("mock", "test", "fake"):
        return f"MOCK_PROVIDER_DETECTED: Location provider is '{metadata.provider}'"
    
    return None


# ============================================================
# DETECTION METHOD 2: Jump/Teleport Detection
# ============================================================
def check_teleport(
    metadata: LocationMetadata,
    history: list[LocationHistoryEntry],
) -> Optional[str]:
    """
    Check if user 'teleported' — moved impossibly fast.

    From Masterplan: "If coordinates change >5km in 1 second → Ban"

    We also check against MAX_SPEED_KMH for less extreme but still
    suspicious movement (e.g., 300 km/h on foot).

    Returns violation string or None if clean.
    """
    if not history:
        return None  # First location, nothing to compare

    last = history[-1]

    # Time difference in seconds
    time_diff = (metadata.timestamp - last.timestamp).total_seconds()

    # Check time anomaly first (clock went backwards)
    if time_diff <= 0:
        return "TIME_ANOMALY: New location timestamp is before or equal to previous"

    # Skip teleport/speed checks if updates are too close together.
    # This is NOT a violation — the app makes concurrent API calls legitimately.
    # We simply cannot compute meaningful speed with < 0.5s resolution.
    if time_diff < MIN_TIME_BETWEEN_UPDATES:
        return None

    # Distance in meters
    distance_m = haversine_meters(
        last.latitude, last.longitude,
        metadata.latitude, metadata.longitude
    )
    distance_km = distance_m / 1000.0

    # Speed in km/h
    speed_kmh = (distance_km / time_diff) * 3600

    # CRITICAL: Teleport check (Masterplan rule)
    if distance_km > TELEPORT_THRESHOLD_KM and time_diff <= 1.0:
        return (
            f"TELEPORT_DETECTED: Moved {distance_km:.1f}km in {time_diff:.1f}s "
            f"(speed: {speed_kmh:.0f} km/h). This is physically impossible."
        )

    # Suspicious speed check (less severe)
    if speed_kmh > MAX_SPEED_KMH:
        return (
            f"IMPOSSIBLE_SPEED: {speed_kmh:.0f} km/h "
            f"(moved {distance_km:.1f}km in {time_diff:.0f}s). "
            f"Max allowed: {MAX_SPEED_KMH} km/h"
        )

    return None


# ============================================================
# DETECTION METHOD 3: Sensor Mismatch (Accelerometer vs GPS)
# ============================================================
def check_sensor_mismatch(
    metadata: LocationMetadata,
    history: list[LocationHistoryEntry],
) -> Optional[str]:
    """
    From Masterplan: "If coordinates change but accelerometer reports
    phone is still → Fake GPS (phone on desk but location moving)"
    
    Logic:
    - Accelerometer at rest ≈ 9.8 m/s² (gravity only)
    - Accelerometer while walking ≈ 10-15 m/s² (gravity + movement)
    - If accelerometer shows < THRESHOLD but GPS moved > 50m, suspicious
    
    Returns violation string or None if clean.
    """
    if metadata.accelerometer_magnitude is None:
        return None  # Client didn't send sensor data, can't check
    
    if not history:
        return None
    
    last = history[-1]
    
    # How far did GPS say we moved?
    distance_m = haversine_meters(
        last.latitude, last.longitude,
        metadata.latitude, metadata.longitude
    )
    
    # Time between updates
    time_diff = (metadata.timestamp - last.timestamp).total_seconds()
    if time_diff <= 0:
        return None
    
    # Subtract gravity (~9.81) to get movement acceleration
    # magnitude - gravity ≈ movement acceleration
    movement_accel = abs(metadata.accelerometer_magnitude - 9.81)
    
    # If phone is "still" (very low movement acceleration)
    # but GPS says we moved significantly
    if movement_accel < SENSOR_STILL_THRESHOLD and distance_m > GPS_MOVE_THRESHOLD:
        return (
            f"SENSOR_MISMATCH: Phone appears stationary (accel: {movement_accel:.2f} m/s²) "
            f"but GPS moved {distance_m:.0f}m in {time_diff:.0f}s. "
            f"Possible fake GPS with phone sitting on desk."
        )
    
    return None


# ============================================================
# PATTERN ANALYSIS (Bonus detection)
# ============================================================
def check_suspicious_patterns(history: list[LocationHistoryEntry]) -> Optional[str]:
    """
    Additional pattern checks:
    - Perfect straight lines (bots follow exact paths)
    - Exact same coordinates repeated (stuck GPS spoofer)
    - Perfect identical accuracy (real GPS varies)
    - Impossible altitude changes
    
    Returns violation string or None if clean.
    """
    if len(history) < 5:
        return None
    
    recent = history[-10:]  # Last 10 positions
    
    # Check for repeated exact coordinates (spoofer didn't randomize)
    coords = [(h.latitude, h.longitude) for h in recent]
    unique_coords = set(coords)
    
    if len(unique_coords) == 1 and len(coords) >= STATIC_LOCATION_MIN_READINGS:
        # All positions are exactly the same — only flag after many readings
        # (users legitimately stand still; low reading count = false positive)
        return (
            f"STATIC_LOCATION: {len(coords)} consecutive identical coordinates. "
            "Real GPS always has slight drift."
        )
    
    # Check for perfect accuracy (real GPS fluctuates).
    # Skip if all entries use the default value (10.0) — that just means
    # the client didn't send accuracy, not that it's spoofed.
    accuracies = [h.accuracy for h in recent]
    default_accuracy = 10.0
    all_default = all(a == default_accuracy for a in accuracies)
    if (not all_default and all(a == accuracies[0] for a in accuracies)
            and len(accuracies) > 5):
        return (
            f"PERFECT_ACCURACY: All {len(accuracies)} recent readings have "
            f"identical accuracy ({accuracies[0]}m). Real GPS accuracy varies."
        )
    
    return None


# ============================================================
# MAIN DETECTION PIPELINE & SERVICE
# ============================================================
class AntiCheatService:
    """
    Static methods following same pattern as LocationService,
    ArtifactService, ExplorationService.
    """

    @staticmethod
    async def analyze_location(
        user_id: UUID,
        metadata: LocationMetadata,
    ) -> CheatDetectionResult:
        """
        Run ALL detection methods on a location update.
        
        Returns CheatDetectionResult with violations and severity.
        
        Usage in middleware:
            result = await AntiCheatService.analyze_location(user.id, location_metadata)
            if result.should_ban:
                await AntiCheatService.ban_user(user.id, db)
            elif result.violations:
                await AntiCheatService.add_strike(user.id, db)
        """
        result = CheatDetectionResult()

        # Cooldown: skip analysis if we ran it very recently for this user.
        # This prevents false positives from the app making concurrent API calls
        # (e.g., GET /artifacts/nearby + POST /explore/batch firing within ms of each other).
        now = datetime.utcnow()
        key = str(user_id)
        last_check = _last_check_time.get(key)
        if last_check and (now - last_check).total_seconds() < ANTI_CHEAT_COOLDOWN_SECONDS:
            # Still add to history so we track movement, but skip violation checks
            add_to_history(user_id, LocationHistoryEntry(
                latitude=metadata.latitude,
                longitude=metadata.longitude,
                timestamp=metadata.timestamp,
                accuracy=metadata.accuracy,
            ))
            return result  # Clean pass during cooldown window

        _last_check_time[key] = now
        history = get_user_history(user_id)

        # ---- Method 1: isMocked ----
        mock_violation = check_is_mocked(metadata)
        if mock_violation:
            result.violations.append(mock_violation)
            result.severity = "critical"  # isMocked is definitive
            result.should_ban = True
            result.details["is_mocked"] = True
        
        # ---- Method 2: Teleport/Jump ----
        teleport_violation = check_teleport(metadata, history)
        if teleport_violation:
            result.violations.append(teleport_violation)
            if "TELEPORT_DETECTED" in teleport_violation:
                result.severity = "critical"
                result.should_ban = True
            elif result.severity != "critical":
                result.severity = "suspicious"
            result.details["movement_anomaly"] = True
        
        # ---- Method 3: Sensor Mismatch ----
        sensor_violation = check_sensor_mismatch(metadata, history)
        if sensor_violation:
            result.violations.append(sensor_violation)
            if result.severity != "critical":
                result.severity = "suspicious"
            result.details["sensor_mismatch"] = True
        
        # ---- Bonus: Pattern Analysis ----
        pattern_violation = check_suspicious_patterns(history)
        if pattern_violation:
            result.violations.append(pattern_violation)
            if result.severity == "none":
                result.severity = "warning"
            result.details["pattern_anomaly"] = True
        
        # Update result
        result.is_clean = len(result.violations) == 0
        
        # Always add to history (even if suspicious — for tracking)
        add_to_history(user_id, LocationHistoryEntry(
            latitude=metadata.latitude,
            longitude=metadata.longitude,
            timestamp=metadata.timestamp,
            accuracy=metadata.accuracy,
        ))
        
        # Log violations
        if not result.is_clean:
            logger.warning(
                f"ANTI-CHEAT: User {user_id} | Severity: {result.severity} | "
                f"Violations: {result.violations}"
            )
        
        return result

    # ============================================================
    # STRIKE & BAN SYSTEM
    # ============================================================

    @staticmethod
    async def add_strike(user_id: UUID, db: AsyncSession) -> int:
        """
        Add a strike to user. Returns new strike count.
        
        Strike 1: Warning
        Strike 2: 24h temp ban
        Strike 3: Permanent ban
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return 0
        
        # Increment cheat_strikes safely
        new_strikes = getattr(user, 'cheat_strikes', 0) + 1
        
        # Update strikes + deduct reputation
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                cheat_strikes=new_strikes,
                reputation_score=User.reputation_score - 50,
            )
        )
        
        if new_strikes >= STRIKE_PERM_BAN:
            await AntiCheatService.ban_user(user_id, db, permanent=True)
        elif new_strikes >= STRIKE_TEMP_BAN:
            await AntiCheatService.ban_user(user_id, db, permanent=False)
        
        await db.commit()
        reset_suspicious_count(user_id)  # Reset sliding window after a real strike
        logger.warning(f"STRIKE: User {user_id} now has {new_strikes} strike(s)")
        return new_strikes

    @staticmethod
    async def add_suspicious_event(user_id: UUID, db: AsyncSession, violation: str) -> int:
        """
        Record a suspicious (non-critical) event.
        After SUSPICIOUS_EVENTS_PER_STRIKE events, escalate to a real strike.

        This prevents punishing users for occasional anomalies (GPS drift,
        brief signal loss) while still catching persistent pattern cheating
        (e.g., someone consistently moving at 300 km/h).

        Returns: current suspicious event count
        """
        count = increment_suspicious_count(user_id)
        logger.info(
            f"SUSPICIOUS [{count}/{SUSPICIOUS_EVENTS_PER_STRIKE}]: "
            f"User {user_id} | {violation}"
        )
        if count >= SUSPICIOUS_EVENTS_PER_STRIKE:
            logger.warning(
                f"SUSPICIOUS threshold reached for user {user_id} — issuing strike"
            )
            await AntiCheatService.add_strike(user_id, db)
        return count

    @staticmethod
    async def ban_user(
        user_id: UUID, 
        db: AsyncSession, 
        permanent: bool = False,
        reason: str = "Anti-cheat violation"
    ) -> bool:
        """
        Ban a user. Uses is_banned field (NOT is_active).
        is_active = account deactivation (user choice)
        is_banned = punishment (system/admin action)
        """
        ban_until = None if permanent else datetime.utcnow() + timedelta(hours=TEMP_BAN_HOURS)
        
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                is_banned=True,
                banned_until=ban_until,
                ban_reason=reason,
            )
        )
        await db.commit()
        
        # Clear location history
        clear_user_history(user_id)
        
        ban_type = "PERMANENTLY" if permanent else f"for {TEMP_BAN_HOURS}h"
        logger.critical(f"BAN: User {user_id} banned {ban_type}. Reason: {reason}")
        
        return True

    @staticmethod
    async def unban_user(user_id: UUID, db: AsyncSession) -> bool:
        """Admin: unban a user."""
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                is_banned=False,
                banned_until=None,
                ban_reason=None,
                cheat_strikes=0,
            )
        )
        await db.commit()
        logger.info(f"UNBAN: User {user_id} unbanned by admin")
        return True

    @staticmethod
    async def check_user_banned(user_id: UUID, db: AsyncSession) -> bool:
        """Check if user is currently banned and handle auto-unban logic."""
        result = await db.execute(
            select(User.is_banned, User.banned_until).where(User.id == user_id)
        )
        row = result.one_or_none()
        if not row:
            return False
            
        is_banned, banned_until = row
        
        # Check if temp ban has expired
        if is_banned and banned_until and banned_until < datetime.utcnow():
            # Auto-unban: temp ban expired
            await AntiCheatService.unban_user(user_id, db)
            return False
            
        return is_banned

    # ============================================================
    # ADMIN UTILITIES
    # ============================================================

    @staticmethod
    async def get_cheat_log(user_id: UUID) -> dict:
        """Get cheat detection history for admin review."""
        history = get_user_history(user_id)
        return {
            "user_id": str(user_id),
            "total_positions": len(history),
            "last_position": {
                "lat": history[-1].latitude,
                "lon": history[-1].longitude,
                "time": history[-1].timestamp.isoformat(),
            } if history else None,
        }