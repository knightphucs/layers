"""
LAYERS - Shadow Layer tests
Pure logic — no DB. Run: pytest tests/test_shadow.py -v

The headline: prove the timezone fix. The OLD code compared "23:00" against
UTC hour and locked Shadow content at the wrong time for HCMC users. These
tests pin the CORRECT behaviour using fixed UTC instants.
"""

from datetime import datetime, timezone

import pytest

from app.utils.shadow_time import (
    in_window,
    night_lock_status,
    is_midnight_window_open,
    check_time_lock_tz_aware,
    midnight_unlock_conditions,
    HCMC_TZ_OFFSET_HOURS,
)
from app.services.shadow_service import ShadowService, GlitchType


def utc(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


class TestMidnightLockTimezone:
    """23:00–03:00 is HCMC LOCAL time (UTC+7). These instants pin it down."""

    def test_2330_local_is_open(self):
        # 16:30 UTC == 23:30 ICT → inside the window → OPEN
        assert is_midnight_window_open(utc(2026, 6, 27, 16, 30)) is True

    def test_0200_local_is_open(self):
        # 19:00 UTC == 02:00 ICT → inside (overnight) → OPEN
        assert is_midnight_window_open(utc(2026, 6, 27, 19, 0)) is True

    def test_1700_local_is_closed(self):
        # 10:00 UTC == 17:00 ICT → outside → CLOSED
        assert is_midnight_window_open(utc(2026, 6, 27, 10, 0)) is False

    def test_0300_local_boundary_is_closed(self):
        # 20:00 UTC == 03:00 ICT → end is exclusive → CLOSED
        assert is_midnight_window_open(utc(2026, 6, 27, 20, 0)) is False

    def test_2300_local_boundary_is_open(self):
        # 16:00 UTC == 23:00 ICT → start is inclusive → OPEN
        assert is_midnight_window_open(utc(2026, 6, 27, 16, 0)) is True

    def test_old_utc_bug_would_have_failed(self):
        # Regression guard: at 16:30 UTC the OLD code (UTC hour 16 vs 23–03)
        # returned LOCKED. The fix must return OPEN.
        locked, _ = check_time_lock_tz_aware(
            midnight_unlock_conditions(), now_utc=utc(2026, 6, 27, 16, 30)
        )
        assert locked is False


class TestNightLockStatus:
    def test_locked_when_closed_has_reason(self):
        s = night_lock_status("23:00", "03:00", now_utc=utc(2026, 6, 27, 10, 0))
        assert s["locked"] is True
        assert s["open"] is False
        assert "23:00" in s["reason"]
        assert s["seconds_until_change"] > 0

    def test_open_has_no_reason(self):
        s = night_lock_status("23:00", "03:00", now_utc=utc(2026, 6, 27, 16, 30))
        assert s["open"] is True
        assert s["reason"] is None

    def test_seconds_until_open_is_sane(self):
        # 12:00 ICT (05:00 UTC). Opens at 23:00 ICT → 11 hours away.
        s = night_lock_status("23:00", "03:00", now_utc=utc(2026, 6, 27, 5, 0))
        assert 10 * 3600 < s["seconds_until_change"] <= 11 * 3600


class TestInWindow:
    def test_daytime_window_non_overnight(self):
        # 09:00–17:00 window, at 12:00 ICT (05:00 UTC) → open
        assert in_window("09:00", "17:00", utc(2026, 6, 27, 5, 0)) is True

    def test_daytime_window_closed(self):
        # 09:00–17:00, at 20:00 ICT (13:00 UTC) → closed
        assert in_window("09:00", "17:00", utc(2026, 6, 27, 13, 0)) is False

    def test_zero_length_window_never_open(self):
        assert in_window("12:00", "12:00", utc(2026, 6, 27, 5, 0)) is False


class TestTimeCapsuleStillWorks:
    def test_future_date_locked(self):
        cond = {"unlock_date": "2099-01-01T00:00:00Z"}
        locked, reason = check_time_lock_tz_aware(cond, now_utc=utc(2026, 6, 27, 12))
        assert locked is True
        assert "Opens in" in reason

    def test_past_date_unlocked(self):
        cond = {"unlock_date": "2020-01-01T00:00:00Z"}
        locked, _ = check_time_lock_tz_aware(cond, now_utc=utc(2026, 6, 27, 12))
        assert locked is False

    def test_no_conditions_unlocked(self):
        assert check_time_lock_tz_aware(None) == (False, None)
        assert check_time_lock_tz_aware({}) == (False, None)


# ---- Glitch Zone membership ----

class FakeZone:
    def __init__(self, lat, lng, radius=150, gtype="XP_SURGE", intensity=2.0,
                 start="23:00", end="03:00", active=True):
        self.center_lat = lat
        self.center_lng = lng
        self.radius_m = radius
        self.glitch_type = gtype
        self.intensity = intensity
        self.active_start = start
        self.active_end = end
        self.is_active = active


BEN_THANH = (10.7725, 106.6980)
NEAR_50M = (10.7727, 106.6981)   # ~30m away
FAR_1KM = (10.7800, 106.7050)    # ~1km away


class TestGlitchZoneSpace:
    def test_user_inside_radius(self):
        z = FakeZone(*BEN_THANH, radius=150)
        assert ShadowService.is_inside(z, *NEAR_50M) is True

    def test_user_outside_radius(self):
        z = FakeZone(*BEN_THANH, radius=150)
        assert ShadowService.is_inside(z, *FAR_1KM) is False


class TestGlitchZoneTime:
    def test_open_when_window_open(self):
        z = FakeZone(*BEN_THANH)
        assert ShadowService.zone_is_open(z, utc(2026, 6, 27, 16, 30)) is True

    def test_closed_when_window_closed(self):
        z = FakeZone(*BEN_THANH)
        assert ShadowService.zone_is_open(z, utc(2026, 6, 27, 10, 0)) is False

    def test_no_window_always_open(self):
        z = FakeZone(*BEN_THANH, start=None, end=None)
        assert ShadowService.zone_is_open(z, utc(2026, 6, 27, 10, 0)) is True

    def test_inactive_zone_never_open(self):
        z = FakeZone(*BEN_THANH, active=False)
        assert ShadowService.zone_is_open(z, utc(2026, 6, 27, 16, 30)) is False


class TestGlitchZoneCombined:
    def test_affects_only_when_inside_and_open(self):
        z = FakeZone(*BEN_THANH)
        # inside + open
        assert ShadowService.affects_user(z, *NEAR_50M, utc(2026, 6, 27, 16, 30)) is True
        # inside + closed (noon)
        assert ShadowService.affects_user(z, *NEAR_50M, utc(2026, 6, 27, 10, 0)) is False
        # far + open
        assert ShadowService.affects_user(z, *FAR_1KM, utc(2026, 6, 27, 16, 30)) is False


class TestXPMultiplier:
    def test_no_zones_is_1x(self):
        assert ShadowService.xp_multiplier([]) == 1.0

    def test_takes_highest_surge(self):
        zones = [FakeZone(*BEN_THANH, intensity=1.5),
                 FakeZone(*BEN_THANH, intensity=2.5)]
        assert ShadowService.xp_multiplier(zones) == 2.5

    def test_capped_at_max(self):
        zones = [FakeZone(*BEN_THANH, intensity=9.0)]
        assert ShadowService.xp_multiplier(zones) == 3.0

    def test_non_surge_zones_ignored(self):
        zones = [FakeZone(*BEN_THANH, gtype="SHADOW_REVEAL", intensity=2.0)]
        assert ShadowService.xp_multiplier(zones) == 1.0
