"""
LAYERS - Shadow Time utilities
=============================================
The canonical, TIMEZONE-AWARE implementation of night-window logic. Both the
Midnight Lock and Glitch Zone activation windows go through here.

WHY THIS EXISTS (a real bug we're fixing):
The old _check_time_lock in artifact_service compared "23:00" against
datetime.now(timezone.utc).hour. But for a user standing in Ho Chi Minh City
(UTC+7), 23:00 means 23:00 LOCAL. 23:30 ICT is 16:30 UTC — the old code saw
hour=16, decided the 23:00–03:00 window was closed, and locked content that
should have been OPEN. Every Shadow artifact was unlockable at the wrong time.

Fix: shift "now" by the city's offset before comparing, and compare with
minute precision (not just the hour). HCMC has no DST, so a fixed +7 offset is
correct and dependency-free (no pytz/zoneinfo needed).

All functions accept now_utc for deterministic testing.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

# Asia/Ho_Chi_Minh — fixed UTC+7, no daylight saving.
HCMC_TZ_OFFSET_HOURS = 7

# Masterplan default Shadow window.
MIDNIGHT_LOCK_START = "23:00"
MIDNIGHT_LOCK_END = "03:00"


def _parse_hhmm(value: str) -> int:
    """'23:00' -> 1380 (minutes since local midnight)."""
    h, _, m = value.partition(":")
    return int(h) * 60 + (int(m) if m else 0)


def local_now(now_utc: Optional[datetime] = None,
              tz_offset_hours: int = HCMC_TZ_OFFSET_HOURS) -> datetime:
    """UTC instant shifted into the city's local wall-clock time."""
    now_utc = now_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    return now_utc.astimezone(timezone.utc) + timedelta(hours=tz_offset_hours)


def in_window(time_start: str, time_end: str,
              now_utc: Optional[datetime] = None,
              tz_offset_hours: int = HCMC_TZ_OFFSET_HOURS) -> bool:
    """True if the local time is inside [start, end). Handles overnight
    ranges where start > end (e.g. 23:00–03:00)."""
    local = local_now(now_utc, tz_offset_hours)
    cur = local.hour * 60 + local.minute
    start, end = _parse_hhmm(time_start), _parse_hhmm(time_end)
    if start == end:
        return False  # zero-length window
    if start < end:
        return start <= cur < end
    return cur >= start or cur < end  # overnight wrap


def night_lock_status(time_start: str, time_end: str,
                      now_utc: Optional[datetime] = None,
                      tz_offset_hours: int = HCMC_TZ_OFFSET_HOURS) -> dict:
    """Rich status for UX: is it locked, why, and how long until it flips.

    Returns:
      {
        "locked": bool,                 # True when OUTSIDE the window
        "open": bool,                   # convenience inverse
        "reason": str | None,           # human string when locked
        "seconds_until_change": int,    # until it opens (if locked) / closes (if open)
      }
    """
    local = local_now(now_utc, tz_offset_hours)
    cur = local.hour * 60 + local.minute
    start, end = _parse_hhmm(time_start), _parse_hhmm(time_end)
    open_now = in_window(time_start, time_end, now_utc, tz_offset_hours)

    # Minutes until the next boundary we care about.
    target = end if open_now else start
    delta_min = (target - cur) % (24 * 60)
    if delta_min == 0:
        delta_min = 24 * 60
    seconds = delta_min * 60 - local.second

    return {
        "locked": not open_now,
        "open": open_now,
        "reason": None if open_now else f"Only available {time_start}–{time_end}",
        "seconds_until_change": max(0, seconds),
    }


def is_midnight_window_open(now_utc: Optional[datetime] = None,
                            tz_offset_hours: int = HCMC_TZ_OFFSET_HOURS) -> bool:
    """Is the default Shadow window (23:00–03:00 local) open right now?"""
    return in_window(MIDNIGHT_LOCK_START, MIDNIGHT_LOCK_END,
                     now_utc, tz_offset_hours)


def midnight_unlock_conditions() -> dict:
    """The unlock_conditions dict to stamp onto a Midnight-Locked artifact."""
    return {"time_start": MIDNIGHT_LOCK_START, "time_end": MIDNIGHT_LOCK_END}


def check_time_lock_tz_aware(
    unlock_conditions: Optional[dict],
    now_utc: Optional[datetime] = None,
    tz_offset_hours: int = HCMC_TZ_OFFSET_HOURS,
) -> Tuple[bool, Optional[str]]:
    """Timezone-correct drop-in replacement for artifact_service._check_time_lock.
    Handles BOTH the night window (tz-aware) and the unlock_date capsule lock.
    Returns (is_locked, reason)."""
    if not unlock_conditions:
        return False, None

    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Night window (Shadow / Midnight Lock) — NOW timezone-aware.
    if "time_start" in unlock_conditions and "time_end" in unlock_conditions:
        status = night_lock_status(
            unlock_conditions["time_start"], unlock_conditions["time_end"],
            now_utc=now, tz_offset_hours=tz_offset_hours,
        )
        if status["locked"]:
            return True, status["reason"]

    # Future date (Time Capsule) — unchanged behaviour.
    if "unlock_date" in unlock_conditions:
        unlock_date = datetime.fromisoformat(
            str(unlock_conditions["unlock_date"]).replace("Z", "+00:00")
        )
        if unlock_date.tzinfo is None:
            unlock_date = unlock_date.replace(tzinfo=timezone.utc)
        if now < unlock_date:
            days_left = (unlock_date - now).days
            return True, f"Opens in {days_left} days"

    return False, None
