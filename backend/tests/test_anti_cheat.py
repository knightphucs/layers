"""
LAYERS - Anti-Cheat System Tests
==================================
FILE: backend/tests/test_anti_cheat.py
(Same folder as test_auth.py, test_locations.py, test_artifacts.py, test_exploration.py)

Run: pytest tests/test_anti_cheat.py -v
Run specific: pytest tests/test_anti_cheat.py -v -k "TestTeleport"
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.anti_cheat_service import (
    LocationMetadata,
    LocationHistoryEntry,
    CheatDetectionResult,
    AntiCheatService,
    check_is_mocked,
    check_teleport,
    check_sensor_mismatch,
    check_suspicious_patterns,
    haversine_meters,
    get_user_history,
    add_to_history,
    clear_user_history,
    TELEPORT_THRESHOLD_KM,
    MAX_SPEED_KMH,
)


# ============================================================
# TEST DATA — Ho Chi Minh City (same locations as other tests)
# ============================================================
BEN_THANH = {"latitude": 10.7725, "longitude": 106.6980}
NOTRE_DAME = {"latitude": 10.7798, "longitude": 106.6990}


# ============================================================
# FIXTURES
# ============================================================
@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def hcmc_location():
    """Normal GPS reading in HCMC District 1."""
    return LocationMetadata(
        latitude=10.7769,
        longitude=106.7009,
        accuracy=10.0,
        is_mocked=False,
        accelerometer_magnitude=10.5,  # Walking
        provider="gps",
    )


@pytest.fixture
def hcmc_history():
    """Recent location history at HCMC."""
    return [LocationHistoryEntry(
        latitude=10.7769,
        longitude=106.7009,
        timestamp=datetime.utcnow() - timedelta(seconds=10),
        accuracy=10.0,
    )]


@pytest.fixture(autouse=True)
def clean_history(user_id):
    """Clear location history before/after each test."""
    clear_user_history(user_id)
    yield
    clear_user_history(user_id)


# ============================================================
# TEST: Haversine Distance Calculation
# ============================================================
class TestHaversine:
    def test_same_point(self):
        """Same point = 0 distance."""
        d = haversine_meters(10.7769, 106.7009, 10.7769, 106.7009)
        assert d == 0.0

    def test_short_distance(self):
        """~100m distance (within a block in District 1)."""
        d = haversine_meters(10.7769, 106.7009, 10.7778, 106.7009)
        assert 90 < d < 110

    def test_medium_distance(self):
        """~1km distance (District 1 to District 3)."""
        d = haversine_meters(10.7769, 106.7009, 10.7850, 106.7009)
        assert 800 < d < 1200

    def test_ben_thanh_to_notre_dame(self):
        """Ben Thanh Market to Notre Dame ≈ 800m."""
        d = haversine_meters(
            BEN_THANH["latitude"], BEN_THANH["longitude"],
            NOTRE_DAME["latitude"], NOTRE_DAME["longitude"],
        )
        assert 500 < d < 1200


# ============================================================
# TEST: isMocked Flag Detection
# ============================================================
class TestIsMocked:
    def test_clean_location(self, hcmc_location):
        """Normal location should pass."""
        result = check_is_mocked(hcmc_location)
        assert result is None

    def test_mocked_location(self):
        """isMocked=True should be detected."""
        metadata = LocationMetadata(
            latitude=10.7769, longitude=106.7009,
            is_mocked=True,
        )
        result = check_is_mocked(metadata)
        assert result is not None
        assert "MOCK_LOCATION_DETECTED" in result

    def test_mock_provider(self):
        """Provider='mock' should be detected."""
        metadata = LocationMetadata(
            latitude=10.7769, longitude=106.7009,
            provider="mock",
        )
        result = check_is_mocked(metadata)
        assert result is not None
        assert "MOCK_PROVIDER_DETECTED" in result

    def test_fake_provider(self):
        """Provider='fake' should be detected."""
        metadata = LocationMetadata(
            latitude=10.7769, longitude=106.7009,
            provider="fake",
        )
        result = check_is_mocked(metadata)
        assert result is not None

    def test_gps_provider_clean(self):
        """Provider='gps' should pass."""
        metadata = LocationMetadata(
            latitude=10.7769, longitude=106.7009,
            provider="gps",
        )
        assert check_is_mocked(metadata) is None

    def test_fused_provider_clean(self):
        """Provider='fused' (Google Fused Location) should pass."""
        metadata = LocationMetadata(
            latitude=10.7769, longitude=106.7009,
            provider="fused",
        )
        assert check_is_mocked(metadata) is None


# ============================================================
# TEST: Teleport/Jump Detection
# ============================================================
class TestTeleportDetection:
    def test_no_history(self):
        """First location (no history) should pass."""
        metadata = LocationMetadata(latitude=10.7769, longitude=106.7009)
        result = check_teleport(metadata, [])
        assert result is None

    def test_normal_walking(self, hcmc_history):
        """Walking 50m in 10 seconds = ~18 km/h. Normal."""
        metadata = LocationMetadata(
            latitude=10.7774,  # ~50m north
            longitude=106.7009,
            timestamp=datetime.utcnow(),
        )
        assert check_teleport(metadata, hcmc_history) is None

    def test_normal_driving(self, hcmc_history):
        """Driving 500m in 10 seconds = ~180 km/h. Fast but possible."""
        metadata = LocationMetadata(
            latitude=10.7814,  # ~500m north
            longitude=106.7009,
            timestamp=datetime.utcnow(),
        )
        assert check_teleport(metadata, hcmc_history) is None

    def test_teleport_instant(self):
        """Moving 10km in 1 second = TELEPORT. Must be caught!"""
        history = [LocationHistoryEntry(
            latitude=10.7769, longitude=106.7009,
            timestamp=datetime.utcnow() - timedelta(seconds=1),
        )]
        metadata = LocationMetadata(
            latitude=10.8669,  # ~10km north
            longitude=106.7009,
            timestamp=datetime.utcnow(),
        )
        result = check_teleport(metadata, history)
        assert result is not None
        assert "TELEPORT_DETECTED" in result

    def test_impossible_speed(self):
        """Moving 50km in 10 seconds = 18,000 km/h. Impossible."""
        history = [LocationHistoryEntry(
            latitude=10.7769, longitude=106.7009,
            timestamp=datetime.utcnow() - timedelta(seconds=10),
        )]
        metadata = LocationMetadata(
            latitude=10.3500, longitude=107.0800,
            timestamp=datetime.utcnow(),
        )
        result = check_teleport(metadata, history)
        assert result is not None
        assert "IMPOSSIBLE_SPEED" in result or "TELEPORT" in result

    def test_rapid_updates(self):
        """Updates faster than 0.5 seconds should be flagged."""
        history = [LocationHistoryEntry(
            latitude=10.7769, longitude=106.7009,
            timestamp=datetime.utcnow() - timedelta(milliseconds=100),
        )]
        metadata = LocationMetadata(
            latitude=10.7770, longitude=106.7009,
            timestamp=datetime.utcnow(),
        )
        result = check_teleport(metadata, history)
        assert result is not None
        assert "RAPID_UPDATES" in result

    def test_time_travel(self):
        """Timestamp going backwards should be caught."""
        history = [LocationHistoryEntry(
            latitude=10.7769, longitude=106.7009,
            timestamp=datetime.utcnow(),
        )]
        metadata = LocationMetadata(
            latitude=10.7770, longitude=106.7009,
            timestamp=datetime.utcnow() - timedelta(seconds=5),
        )
        result = check_teleport(metadata, history)
        assert result is not None
        assert "TIME_ANOMALY" in result


# ============================================================
# TEST: Sensor Mismatch Detection
# ============================================================
class TestSensorMismatch:
    def test_walking_with_movement(self, hcmc_history):
        """Walking: GPS moves + accelerometer shows movement. Clean."""
        metadata = LocationMetadata(
            latitude=10.7774,
            longitude=106.7009,
            accelerometer_magnitude=11.5,  # Walking
            timestamp=datetime.utcnow(),
        )
        assert check_sensor_mismatch(metadata, hcmc_history) is None

    def test_phone_on_desk_gps_moves(self):
        """Phone still (accel≈9.81) but GPS says moved 200m. FAKE!"""
        history = [LocationHistoryEntry(
            latitude=10.7769, longitude=106.7009,
            timestamp=datetime.utcnow() - timedelta(seconds=30),
        )]
        metadata = LocationMetadata(
            latitude=10.7789,  # ~200m moved
            longitude=106.7009,
            accelerometer_magnitude=9.81,  # Exactly gravity = phone is still
            timestamp=datetime.utcnow(),
        )
        result = check_sensor_mismatch(metadata, history)
        assert result is not None
        assert "SENSOR_MISMATCH" in result

    def test_phone_on_desk_gps_small_drift(self, hcmc_history):
        """Phone still + GPS drifts 10m. Normal GPS drift, should pass."""
        metadata = LocationMetadata(
            latitude=10.77699,  # ~10m drift
            longitude=106.7009,
            accelerometer_magnitude=9.81,
            timestamp=datetime.utcnow(),
        )
        assert check_sensor_mismatch(metadata, hcmc_history) is None

    def test_no_sensor_data(self, hcmc_history):
        """No accelerometer data → can't check, should pass."""
        metadata = LocationMetadata(
            latitude=10.7789, longitude=106.7009,
            accelerometer_magnitude=None,
            timestamp=datetime.utcnow(),
        )
        assert check_sensor_mismatch(metadata, hcmc_history) is None


# ============================================================
# TEST: Pattern Analysis
# ============================================================
class TestPatternAnalysis:
    def test_normal_movement(self):
        """Varied coordinates with varying accuracy. Normal."""
        history = [
            LocationHistoryEntry(
                latitude=10.7769 + i * 0.0001,
                longitude=106.7009 + i * 0.00005,
                timestamp=datetime.utcnow() - timedelta(seconds=(10 - i) * 5),
                accuracy=8.0 + i * 0.5,
            )
            for i in range(10)
        ]
        assert check_suspicious_patterns(history) is None

    def test_static_coordinates(self):
        """Same exact coordinates 10 times. Suspicious!"""
        history = [
            LocationHistoryEntry(
                latitude=10.7769, longitude=106.7009,
                timestamp=datetime.utcnow() - timedelta(seconds=(10 - i) * 5),
                accuracy=10.0,
            )
            for i in range(10)
        ]
        result = check_suspicious_patterns(history)
        assert result is not None
        assert "STATIC_LOCATION" in result

    def test_perfect_accuracy(self):
        """All readings have identical accuracy. Real GPS varies."""
        history = [
            LocationHistoryEntry(
                latitude=10.7769 + i * 0.0001,
                longitude=106.7009,
                timestamp=datetime.utcnow() - timedelta(seconds=(10 - i) * 5),
                accuracy=5.0,  # Always exactly 5.0m
            )
            for i in range(10)
        ]
        result = check_suspicious_patterns(history)
        assert result is not None
        assert "PERFECT_ACCURACY" in result

    def test_too_few_points(self):
        """Less than 5 points — not enough to detect patterns."""
        history = [LocationHistoryEntry(
            latitude=10.7769, longitude=106.7009,
            timestamp=datetime.utcnow(), accuracy=5.0,
        )]
        assert check_suspicious_patterns(history) is None


# ============================================================
# TEST: Full Detection Pipeline (AntiCheatService)
# ============================================================
class TestAntiCheatPipeline:
    @pytest.mark.asyncio
    async def test_clean_first_location(self, user_id):
        """First location from a new user. Should be clean."""
        metadata = LocationMetadata(
            latitude=10.7769, longitude=106.7009,
            is_mocked=False, provider="gps",
            accelerometer_magnitude=10.5,
        )
        result = await AntiCheatService.analyze_location(user_id, metadata)
        assert result.is_clean is True
        assert len(result.violations) == 0
        assert result.severity == "none"

    @pytest.mark.asyncio
    async def test_mocked_is_critical(self, user_id):
        """isMocked=True should be critical severity."""
        metadata = LocationMetadata(
            latitude=10.7769, longitude=106.7009,
            is_mocked=True,
        )
        result = await AntiCheatService.analyze_location(user_id, metadata)
        assert result.is_clean is False
        assert result.severity == "critical"
        assert result.should_ban is True

    @pytest.mark.asyncio
    async def test_normal_walking_sequence(self, user_id):
        """Simulate normal walking — all clean."""
        base_time = datetime.utcnow()
        for i in range(5):
            metadata = LocationMetadata(
                latitude=10.7769 + i * 0.0001,
                longitude=106.7009,
                timestamp=base_time + timedelta(seconds=i * 10),
                is_mocked=False,
                accelerometer_magnitude=10.0 + (i % 3) * 0.5,
                accuracy=8.0 + i * 0.3,
                provider="gps",
            )
            result = await AntiCheatService.analyze_location(user_id, metadata)
            assert result.is_clean is True, f"Step {i} flagged: {result.violations}"

    @pytest.mark.asyncio
    async def test_teleport_after_walking(self, user_id):
        """Walk normally then teleport. Should be caught."""
        now = datetime.utcnow()

        # Walk normally first
        for i in range(3):
            await AntiCheatService.analyze_location(user_id, LocationMetadata(
                latitude=10.7769 + i * 0.0001,
                longitude=106.7009,
                timestamp=now + timedelta(seconds=i * 10),
                is_mocked=False, accelerometer_magnitude=10.5,
            ))

        # Now teleport 10km!
        result = await AntiCheatService.analyze_location(user_id, LocationMetadata(
            latitude=10.8769,
            longitude=106.7009,
            timestamp=now + timedelta(seconds=31),
            is_mocked=False,
        ))
        assert result.is_clean is False
        assert result.severity == "critical"

    @pytest.mark.asyncio
    async def test_multiple_violations(self, user_id):
        """Mocked + teleport = multiple violations."""
        add_to_history(user_id, LocationHistoryEntry(
            latitude=10.7769, longitude=106.7009,
            timestamp=datetime.utcnow() - timedelta(seconds=1),
        ))
        metadata = LocationMetadata(
            latitude=10.9000,
            longitude=106.7009,
            is_mocked=True,
            timestamp=datetime.utcnow(),
        )
        result = await AntiCheatService.analyze_location(user_id, metadata)
        assert result.is_clean is False
        assert len(result.violations) >= 2
        assert result.severity == "critical"


# ============================================================
# TEST: Location History Management
# ============================================================
class TestLocationHistory:
    def test_add_and_get(self, user_id):
        """Add entries and retrieve them."""
        add_to_history(user_id, LocationHistoryEntry(
            latitude=10.7769, longitude=106.7009,
            timestamp=datetime.utcnow(),
        ))
        history = get_user_history(user_id)
        assert len(history) == 1
        assert history[0].latitude == 10.7769

    def test_history_limit(self, user_id):
        """History should be capped at 50 entries."""
        for i in range(100):
            add_to_history(user_id, LocationHistoryEntry(
                latitude=10.7769 + i * 0.0001,
                longitude=106.7009,
                timestamp=datetime.utcnow() + timedelta(seconds=i),
            ))
        assert len(get_user_history(user_id)) == 50

    def test_clear_history(self, user_id):
        """Clear should remove all entries."""
        add_to_history(user_id, LocationHistoryEntry(
            latitude=10.7769, longitude=106.7009,
            timestamp=datetime.utcnow(),
        ))
        clear_user_history(user_id)
        assert len(get_user_history(user_id)) == 0
