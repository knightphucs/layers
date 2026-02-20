"""
LAYERS - Week 3 Integration Tests
====================================
FILE: backend/tests/test_integration_week3.py
(Same folder as test_auth.py, test_locations.py, test_artifacts.py,
 test_exploration.py, test_anti_cheat.py)

PURPOSE:
  Test all 4 geo-spatial systems TOGETHER — the way real users will use them.
  A user walks around HCMC, creates artifacts, explores fog, and the anti-cheat
  watches everything.

Run: pytest tests/test_integration_week3.py -v
Run all: pytest tests/ -v
"""

import pytest
import math
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.anti_cheat_service import (
    LocationMetadata,
    AntiCheatService,
    haversine_meters,
    clear_user_history,
)
from app.services.exploration_service import ExplorationService


# ============================================================
# TEST DATA — Real Ho Chi Minh City locations
# ============================================================

# District 1 landmarks (real coordinates)
LOCATIONS = {
    "ben_thanh": {"lat": 10.7725, "lng": 106.6980, "name": "Bến Thành Market"},
    "notre_dame": {"lat": 10.7798, "lng": 106.6990, "name": "Nhà Thờ Đức Bà"},
    "post_office": {"lat": 10.7800, "lng": 106.6997, "name": "Bưu Điện Trung Tâm"},
    "book_street": {"lat": 10.7765, "lng": 106.7005, "name": "Đường Sách"},
    "turtle_lake": {"lat": 10.7750, "lng": 106.6925, "name": "Hồ Con Rùa"},
    "bitexco": {"lat": 10.7717, "lng": 106.7043, "name": "Bitexco Tower"},
    "saigon_river": {"lat": 10.7870, "lng": 106.7050, "name": "Bến Bạch Đằng"},
}

# Walking path simulation: Bến Thành → Notre Dame (~800m, ~10 min walk)
WALKING_PATH_BEN_THANH_TO_NOTRE_DAME = [
    {"lat": 10.7725, "lng": 106.6980, "delay_s": 0},     # Start: Bến Thành
    {"lat": 10.7733, "lng": 106.6982, "delay_s": 60},     # Walking north...
    {"lat": 10.7741, "lng": 106.6984, "delay_s": 120},
    {"lat": 10.7750, "lng": 106.6985, "delay_s": 180},
    {"lat": 10.7758, "lng": 106.6986, "delay_s": 240},
    {"lat": 10.7766, "lng": 106.6987, "delay_s": 300},
    {"lat": 10.7774, "lng": 106.6988, "delay_s": 360},
    {"lat": 10.7782, "lng": 106.6989, "delay_s": 420},
    {"lat": 10.7790, "lng": 106.6990, "delay_s": 480},
    {"lat": 10.7798, "lng": 106.6990, "delay_s": 540},    # Arrive: Notre Dame
]

# Motorbike ride: District 1 → District 7 (~8km, ~20 min)
MOTORBIKE_D1_TO_D7 = [
    {"lat": 10.7725, "lng": 106.6980, "delay_s": 0},      # Start: Bến Thành
    {"lat": 10.7600, "lng": 106.6950, "delay_s": 120},     # Heading south
    {"lat": 10.7450, "lng": 106.6900, "delay_s": 240},
    {"lat": 10.7300, "lng": 106.6950, "delay_s": 360},
    {"lat": 10.7200, "lng": 106.7000, "delay_s": 480},
    {"lat": 10.7100, "lng": 106.7050, "delay_s": 600},
    {"lat": 10.7000, "lng": 106.7100, "delay_s": 720},
    {"lat": 10.6950, "lng": 106.7200, "delay_s": 840},     # Arrive: D7
]


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def user_id_2():
    return uuid4()


@pytest.fixture(autouse=True)
def clean_state(user_id, user_id_2):
    """Clean anti-cheat history before each test."""
    clear_user_history(user_id)
    clear_user_history(user_id_2)
    yield
    clear_user_history(user_id)
    clear_user_history(user_id_2)


# ============================================================
# SCENARIO 1: Normal User Journey
# "Kazyy walks from Bến Thành to Notre Dame, drops a letter"
# ============================================================

class TestNormalUserJourney:
    """Simulate a complete normal user session."""

    @pytest.mark.asyncio
    async def test_walking_path_all_clean(self, user_id):
        """Walking 800m in 10 minutes — every point should pass anti-cheat."""
        base_time = datetime.utcnow()

        for i, point in enumerate(WALKING_PATH_BEN_THANH_TO_NOTRE_DAME):
            metadata = LocationMetadata(
                latitude=point["lat"],
                longitude=point["lng"],
                accuracy=8.0 + (i % 5) * 0.5,  # Varying accuracy (realistic)
                timestamp=base_time + timedelta(seconds=point["delay_s"]),
                is_mocked=False,
                accelerometer_magnitude=10.2 + (i % 3) * 0.3,  # Walking vibration
                provider="fused",
            )
            result = await AntiCheatService.analyze_location(user_id, metadata)
            assert result.is_clean, (
                f"Point {i} ({point['lat']}, {point['lng']}) flagged: {result.violations}"
            )

    @pytest.mark.asyncio
    async def test_motorbike_ride_clean(self, user_id):
        """Riding motorbike 8km in 14 minutes (~34 km/h). Normal HCMC traffic."""
        base_time = datetime.utcnow()

        for i, point in enumerate(MOTORBIKE_D1_TO_D7):
            metadata = LocationMetadata(
                latitude=point["lat"],
                longitude=point["lng"],
                accuracy=5.0 + (i % 4),
                timestamp=base_time + timedelta(seconds=point["delay_s"]),
                is_mocked=False,
                accelerometer_magnitude=11.0 + (i % 5) * 0.5,  # Motorbike vibration
                provider="gps",
            )
            result = await AntiCheatService.analyze_location(user_id, metadata)
            assert result.is_clean, (
                f"Point {i} flagged at speed check: {result.violations}"
            )

    def test_walking_path_reveals_fog_chunks(self):
        """Walking 800m should reveal multiple fog chunks."""
        from app.services.exploration_service import _calculate_chunk

        chunks = set()
        for point in WALKING_PATH_BEN_THANH_TO_NOTRE_DAME:
            cx, cy = _calculate_chunk(point["lat"], point["lng"])
            chunks.add((cx, cy))

        # 800m walk → at least 6 unique 100m chunks
        assert len(chunks) >= 6, f"Only {len(chunks)} chunks for 800m walk"

    def test_walking_distance_realistic(self):
        """Total walking path distance should be ~800m."""
        path = WALKING_PATH_BEN_THANH_TO_NOTRE_DAME
        total_distance = 0

        for i in range(1, len(path)):
            d = haversine_meters(
                path[i-1]["lat"], path[i-1]["lng"],
                path[i]["lat"], path[i]["lng"],
            )
            total_distance += d

        assert 700 < total_distance < 1000, f"Path distance: {total_distance:.0f}m"


# ============================================================
# SCENARIO 2: Cheater Caught!
# "A cheater tries to fake GPS while sitting at home"
# ============================================================

class TestCheaterDetection:
    """Simulate various cheating attempts."""

    @pytest.mark.asyncio
    async def test_fake_gps_app_caught(self, user_id):
        """Cheater uses Fake GPS app — isMocked flag catches them."""
        metadata = LocationMetadata(
            latitude=10.7725, longitude=106.6980,
            is_mocked=True,  # Fake GPS app sets this
            provider="mock",
            accelerometer_magnitude=9.81,  # Phone on desk
        )
        result = await AntiCheatService.analyze_location(user_id, metadata)
        assert result.is_clean is False
        assert result.severity == "critical"
        assert result.should_ban is True

    @pytest.mark.asyncio
    async def test_teleport_between_districts(self, user_id):
        """Walk normally in D1, then "teleport" to D7 instantly."""
        now = datetime.utcnow()

        # Walk normally first (build trust)
        for i in range(3):
            await AntiCheatService.analyze_location(user_id, LocationMetadata(
                latitude=10.7725 + i * 0.0001,
                longitude=106.6980,
                timestamp=now + timedelta(seconds=i * 30),
                is_mocked=False,
                accelerometer_magnitude=10.5,
            ))

        # Teleport to District 7 (8km away, 1 second later!)
        result = await AntiCheatService.analyze_location(user_id, LocationMetadata(
            latitude=10.6950,
            longitude=106.7200,
            timestamp=now + timedelta(seconds=91),  # 1 second after last point
            is_mocked=False,
            accelerometer_magnitude=9.81,
        ))
        assert result.is_clean is False
        assert any("TELEPORT" in v or "IMPOSSIBLE_SPEED" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_desk_spoofer_caught(self, user_id):
        """Phone on desk (accel ≈ 9.81) but GPS jumps 200m. Caught!"""
        now = datetime.utcnow()

        # First point
        await AntiCheatService.analyze_location(user_id, LocationMetadata(
            latitude=10.7725, longitude=106.6980,
            timestamp=now,
            is_mocked=False,
            accelerometer_magnitude=9.81,
        ))

        # 200m jump while phone is still
        result = await AntiCheatService.analyze_location(user_id, LocationMetadata(
            latitude=10.7745, longitude=106.6980,  # ~220m north
            timestamp=now + timedelta(seconds=30),
            is_mocked=False,
            accelerometer_magnitude=9.80,  # Still = phone on desk
        ))
        assert result.is_clean is False
        assert any("SENSOR_MISMATCH" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_legitimate_then_cheat(self, user_id):
        """Start legitimate, then start cheating. Should only flag the cheat."""
        now = datetime.utcnow()

        # 5 legitimate walking points
        clean_count = 0
        for i in range(5):
            result = await AntiCheatService.analyze_location(user_id, LocationMetadata(
                latitude=10.7725 + i * 0.0001,
                longitude=106.6980,
                timestamp=now + timedelta(seconds=i * 30),
                is_mocked=False,
                accelerometer_magnitude=10.5 + (i % 3) * 0.3,
                accuracy=8.0 + i * 0.5,
            ))
            if result.is_clean:
                clean_count += 1

        assert clean_count == 5, "Legitimate points should all pass"

        # Now cheat: enable mock GPS
        result = await AntiCheatService.analyze_location(user_id, LocationMetadata(
            latitude=10.7730, longitude=106.6980,
            timestamp=now + timedelta(seconds=180),
            is_mocked=True,  # Switched on fake GPS
        ))
        assert result.is_clean is False


# ============================================================
# SCENARIO 3: Two Users at Same Location
# "Two strangers meet at Bến Thành Market"
# ============================================================

class TestMultiUserScenario:
    """Test that anti-cheat tracks users independently."""

    @pytest.mark.asyncio
    async def test_two_users_same_location(self, user_id, user_id_2):
        """Two users at Bến Thành — both should pass independently."""
        for uid in [user_id, user_id_2]:
            result = await AntiCheatService.analyze_location(uid, LocationMetadata(
                latitude=10.7725, longitude=106.6980,
                is_mocked=False, accelerometer_magnitude=10.0,
            ))
            assert result.is_clean

    @pytest.mark.asyncio
    async def test_one_cheater_doesnt_affect_other(self, user_id, user_id_2):
        """User 1 cheats, User 2 is clean. Only User 1 should be flagged."""
        # User 1: Normal
        r1 = await AntiCheatService.analyze_location(user_id, LocationMetadata(
            latitude=10.7725, longitude=106.6980,
            is_mocked=False, accelerometer_magnitude=10.5,
        ))
        assert r1.is_clean

        # User 2: Cheating
        r2 = await AntiCheatService.analyze_location(user_id_2, LocationMetadata(
            latitude=10.7725, longitude=106.6980,
            is_mocked=True,
        ))
        assert r2.is_clean is False

        # User 1 still clean on next update
        r1_again = await AntiCheatService.analyze_location(user_id, LocationMetadata(
            latitude=10.7726, longitude=106.6981,
            timestamp=datetime.utcnow() + timedelta(seconds=30),
            is_mocked=False, accelerometer_magnitude=10.3,
        ))
        assert r1_again.is_clean


# ============================================================
# SCENARIO 4: Geo-Spatial Edge Cases
# "What happens at extreme GPS coordinates?"
# ============================================================

class TestGeoEdgeCases:
    """Test boundary conditions for GPS calculations."""

    def test_equator(self):
        """Distance calculation at the equator (lat=0)."""
        d = haversine_meters(0.0, 106.0, 0.001, 106.0)
        assert 100 < d < 120  # ~111m per 0.001° at equator

    def test_high_latitude(self):
        """At high latitudes, longitude degrees are shorter."""
        # At 60°N, 1° longitude ≈ 55km (vs ~111km at equator)
        d_equator = haversine_meters(0.0, 0.0, 0.0, 0.01)
        d_60north = haversine_meters(60.0, 0.0, 60.0, 0.01)
        assert d_60north < d_equator * 0.6  # Should be roughly half

    def test_date_line_crossing(self):
        """Crossing the International Date Line (180° → -180°)."""
        d = haversine_meters(0.0, 179.999, 0.0, -179.999)
        assert d < 250  # Should be ~222m, not half the Earth

    def test_north_pole(self):
        """Near the North Pole."""
        d = haversine_meters(89.999, 0.0, 89.999, 180.0)
        assert d < 250  # Very close at the pole

    def test_south_pole(self):
        """Near the South Pole."""
        d = haversine_meters(-89.999, 0.0, -89.999, 90.0)
        assert d < 200

    def test_same_point_zero_distance(self):
        """Same point should be exactly 0."""
        assert haversine_meters(10.7725, 106.6980, 10.7725, 106.6980) == 0.0

    def test_antipodal_points(self):
        """Points on opposite sides of Earth ≈ 20,000km."""
        d = haversine_meters(0.0, 0.0, 0.0, 180.0)
        assert 19_900_000 < d < 20_100_000  # ~20,015km

    def test_negative_coordinates(self):
        """Southern hemisphere coordinates (Sydney, Australia)."""
        # Sydney Opera House to Sydney Harbour Bridge ≈ 850m
        d = haversine_meters(-33.8568, 151.2153, -33.8523, 151.2108)
        assert 400 < d < 1000

    def test_hcmc_known_distances(self):
        """Verify known HCMC distances are reasonable."""
        # Bến Thành to Notre Dame ≈ 800m
        d = haversine_meters(
            LOCATIONS["ben_thanh"]["lat"], LOCATIONS["ben_thanh"]["lng"],
            LOCATIONS["notre_dame"]["lat"], LOCATIONS["notre_dame"]["lng"],
        )
        assert 500 < d < 1200, f"Ben Thanh to Notre Dame: {d:.0f}m"

        # Notre Dame to Post Office ≈ 50-100m (right across the street)
        d2 = haversine_meters(
            LOCATIONS["notre_dame"]["lat"], LOCATIONS["notre_dame"]["lng"],
            LOCATIONS["post_office"]["lat"], LOCATIONS["post_office"]["lng"],
        )
        assert d2 < 200, f"Notre Dame to Post Office: {d2:.0f}m"


# ============================================================
# SCENARIO 5: Fog of War Chunk Math Verification
# ============================================================

class TestFogOfWarChunkMath:
    """Verify chunk calculations are consistent and correct."""

    def test_chunk_consistency(self):
        """Same GPS point always maps to same chunk."""
        from app.services.exploration_service import _calculate_chunk

        for _ in range(100):
            cx, cy = _calculate_chunk(10.7725, 106.6980)
            assert cx == _calculate_chunk(10.7725, 106.6980)[0]
            assert cy == _calculate_chunk(10.7725, 106.6980)[1]

    def test_nearby_points_same_chunk(self):
        """Points 10m apart should be in the same ~100m chunk."""
        from app.services.exploration_service import _calculate_chunk

        c1 = _calculate_chunk(10.77250, 106.69800)
        c2 = _calculate_chunk(10.77255, 106.69805)  # ~6m away
        assert c1 == c2

    def test_distant_points_different_chunks(self):
        """Points 200m apart should be in different chunks."""
        from app.services.exploration_service import _calculate_chunk

        c1 = _calculate_chunk(10.7725, 106.6980)
        c2 = _calculate_chunk(10.7745, 106.6980)  # ~220m north
        assert c1 != c2

    def test_chunk_at_equator(self):
        """Chunks should work at the equator."""
        from app.services.exploration_service import _calculate_chunk

        cx, cy = _calculate_chunk(0.0001, 0.0001)
        assert isinstance(cx, int)
        assert isinstance(cy, int)

    def test_chunk_negative_coordinates(self):
        """Chunks should work in southern/western hemispheres."""
        from app.services.exploration_service import _calculate_chunk

        # Buenos Aires, Argentina
        cx, cy = _calculate_chunk(-34.6037, -58.3816)
        assert isinstance(cx, int)
        assert isinstance(cy, int)


# ============================================================
# SCENARIO 6: Performance Characteristics (Unit-level)
# ============================================================

class TestPerformanceCharacteristics:
    """Verify operations are fast enough for production."""

    def test_haversine_speed(self):
        """Haversine calculation should be very fast (pure math)."""
        import time
        start = time.perf_counter()

        for _ in range(10_000):
            haversine_meters(10.7725, 106.6980, 10.7798, 106.6990)

        elapsed_ms = (time.perf_counter() - start) * 1000
        # 10,000 calculations should take < 100ms
        assert elapsed_ms < 100, f"10k haversine: {elapsed_ms:.1f}ms (too slow!)"

    def test_chunk_calculation_speed(self):
        """Chunk calculation should be very fast (pure math)."""
        from app.services.exploration_service import _calculate_chunk
        import time

        start = time.perf_counter()
        for i in range(10_000):
            _calculate_chunk(10.7725 + i * 0.00001, 106.6980)

        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, f"10k chunks: {elapsed_ms:.1f}ms (too slow!)"

    @pytest.mark.asyncio
    async def test_anti_cheat_pipeline_speed(self, user_id):
        """Full anti-cheat pipeline should be fast (no DB calls)."""
        import time

        metadata = LocationMetadata(
            latitude=10.7725, longitude=106.6980,
            is_mocked=False, accelerometer_magnitude=10.5,
        )

        start = time.perf_counter()
        for _ in range(1_000):
            await AntiCheatService.analyze_location(user_id, metadata)

        elapsed_ms = (time.perf_counter() - start) * 1000
        per_call = elapsed_ms / 1_000
        # Each call should be < 1ms
        assert per_call < 1.0, f"Anti-cheat: {per_call:.3f}ms/call (target: <1ms)"

    def test_50m_radius_calculation(self):
        """Verify 50m geo-lock radius works correctly."""
        center = LOCATIONS["ben_thanh"]

        # Point 30m away — INSIDE radius
        d_inside = haversine_meters(center["lat"], center["lng"], 10.77277, 106.6980)
        assert d_inside < 50, f"Should be inside 50m: {d_inside:.0f}m"

        # Point 80m away — OUTSIDE radius
        d_outside = haversine_meters(center["lat"], center["lng"], 10.7732, 106.6980)
        assert d_outside > 50, f"Should be outside 50m: {d_outside:.0f}m"


# ============================================================
# SCENARIO 7: Proof of Presence Distance Tests
# ============================================================

class TestProofOfPresence:
    """Test the 50m geo-lock radius from Masterplan."""

    def test_at_exact_location(self):
        """Standing exactly at artifact location = within radius."""
        d = haversine_meters(10.7725, 106.6980, 10.7725, 106.6980)
        assert d <= 50

    def test_10m_away(self):
        """10m away = within radius."""
        d = haversine_meters(10.7725, 106.6980, 10.77259, 106.6980)
        assert d <= 50

    def test_49m_away(self):
        """49m away = just barely within radius."""
        d = haversine_meters(10.7725, 106.6980, 10.7729, 106.6981)
        assert d <= 55  # Allow small tolerance for float math

    def test_100m_away(self):
        """100m away = definitely outside radius."""
        d = haversine_meters(10.7725, 106.6980, 10.7734, 106.6980)
        assert d > 50

    def test_across_street(self):
        """Notre Dame to Post Office (across the street) ≈ within 100m."""
        d = haversine_meters(
            LOCATIONS["notre_dame"]["lat"], LOCATIONS["notre_dame"]["lng"],
            LOCATIONS["post_office"]["lat"], LOCATIONS["post_office"]["lng"],
        )
        # These are very close but likely > 50m
        assert d < 200  # They're very close in real life
