"""
LAYERS - Location & Geo Tests
================================
FILE: backend/tests/test_locations.py

Run: pytest tests/test_locations.py -v
"""

import pytest
from uuid import uuid4

# Test data — Ho Chi Minh City
BEN_THANH = {"latitude": 10.7725, "longitude": 106.6980}
NOTRE_DAME = {"latitude": 10.7798, "longitude": 106.6990}
BUI_VIEN  = {"latitude": 10.7672, "longitude": 106.6934}
THU_DUC   = {"latitude": 10.8494, "longitude": 106.7529}


# ============================================================
# GEO UTILITY TESTS (No DB required!)
# ============================================================

class TestGeoUtils:
    """Test app/utils/geo.py functions."""

    def test_haversine_ben_thanh_to_notre_dame(self):
        from app.utils.geo import haversine_distance
        dist = haversine_distance(
            BEN_THANH["latitude"], BEN_THANH["longitude"],
            NOTRE_DAME["latitude"], NOTRE_DAME["longitude"],
        )
        # Should be roughly 800m
        assert 500 < dist < 1500

    def test_haversine_same_point(self):
        from app.utils.geo import haversine_distance
        dist = haversine_distance(10.77, 106.70, 10.77, 106.70)
        assert dist == 0.0

    def test_format_distance_meters(self):
        from app.utils.geo import format_distance
        assert format_distance(47.3) == "47m"
        assert format_distance(523.8) == "524m"
        assert format_distance(0) == "0m"

    def test_format_distance_kilometers(self):
        from app.utils.geo import format_distance
        assert format_distance(1234) == "1.2km"
        assert format_distance(15000) == "15.0km"

    def test_is_within_radius_true(self):
        from app.utils.geo import is_within_radius
        # Ben Thanh to point 30m away — should be within 50m
        assert is_within_radius(
            BEN_THANH["latitude"], BEN_THANH["longitude"],
            BEN_THANH["latitude"] + 0.0003, BEN_THANH["longitude"],
            50  # 50m radius
        )

    def test_is_within_radius_false(self):
        from app.utils.geo import is_within_radius
        # Ben Thanh to Notre Dame — should NOT be within 50m
        assert not is_within_radius(
            BEN_THANH["latitude"], BEN_THANH["longitude"],
            NOTRE_DAME["latitude"], NOTRE_DAME["longitude"],
            50
        )

    def test_fake_gps_normal_walking(self):
        from app.utils.geo import is_likely_fake_gps
        # 100m in 60 seconds = walking speed → NOT fake
        assert is_likely_fake_gps(
            10.77, 106.70, 10.771, 106.70, 60
        ) is False

    def test_fake_gps_teleportation(self):
        from app.utils.geo import is_likely_fake_gps
        # 10km in 1 second → FAKE GPS
        assert is_likely_fake_gps(
            10.77, 106.70, 10.87, 106.70, 1
        ) is True

    def test_fake_gps_zero_time(self):
        from app.utils.geo import is_likely_fake_gps
        # 0 seconds time diff → suspicious
        assert is_likely_fake_gps(10.77, 106.70, 10.78, 106.70, 0) is True

    def test_random_point_in_ring(self):
        from app.utils.geo import random_point_in_ring, haversine_distance
        for _ in range(50):
            lat, lng = random_point_in_ring(
                BEN_THANH["latitude"], BEN_THANH["longitude"],
                min_radius_m=200, max_radius_m=1000,
            )
            dist = haversine_distance(
                BEN_THANH["latitude"], BEN_THANH["longitude"], lat, lng
            )
            assert 180 < dist < 1050  # Allow small margin

    def test_validate_coordinates(self):
        from app.utils.geo import validate_coordinates
        assert validate_coordinates(10.77, 106.70) is True
        assert validate_coordinates(999, 106.70) is False
        assert validate_coordinates(10.77, -999) is False
        assert validate_coordinates(-90, -180) is True
        assert validate_coordinates(90, 180) is True


# ============================================================
# API ENDPOINT TESTS (Require running backend + DB)
# ============================================================
# Uncomment and adapt these when you have test fixtures set up.

"""
class TestLocationCreate:
    async def test_create_success(self, client, auth_token):
        response = await client.post(
            "/api/v1/map/locations",
            json={
                "latitude": BEN_THANH["latitude"],
                "longitude": BEN_THANH["longitude"],
                "layer": "LIGHT",
                "category": "MARKET",
                "name": "Ben Thanh Market",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Ben Thanh Market"
        assert data["layer"] == "LIGHT"

    async def test_create_invalid_coords(self, client, auth_token):
        response = await client.post(
            "/api/v1/map/locations",
            json={"latitude": 999, "longitude": 106.7, "layer": "LIGHT"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 422

    async def test_create_too_close(self, client, auth_token):
        # Create first
        await client.post(
            "/api/v1/map/locations",
            json={"latitude": 10.77, "longitude": 106.70, "layer": "LIGHT", "category": "CAFE"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        # Create ~5m away → should fail
        response = await client.post(
            "/api/v1/map/locations",
            json={"latitude": 10.77001, "longitude": 106.70, "layer": "LIGHT", "category": "CAFE"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 400

    async def test_requires_auth(self, client):
        response = await client.post(
            "/api/v1/map/locations",
            json={"latitude": 10.77, "longitude": 106.70, "layer": "LIGHT"},
        )
        assert response.status_code in [401, 403]


class TestNearbyQuery:
    async def test_finds_within_radius(self, client, auth_token):
        response = await client.get(
            "/api/v1/map/nearby",
            params={"lat": BEN_THANH["latitude"], "lng": BEN_THANH["longitude"], "radius": 1000},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "has_more" in data

    async def test_returns_distance(self, client, auth_token):
        response = await client.get(
            "/api/v1/map/nearby",
            params={"lat": BEN_THANH["latitude"], "lng": BEN_THANH["longitude"], "radius": 2000},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        data = response.json()
        for item in data["items"]:
            assert "distance_meters" in item

    async def test_filter_by_layer(self, client, auth_token):
        response = await client.get(
            "/api/v1/map/nearby",
            params={"lat": 10.77, "lng": 106.70, "radius": 1000, "layer": "LIGHT"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        data = response.json()
        for item in data["items"]:
            assert item["layer"] == "LIGHT"


class TestLocationDetail:
    async def test_proof_of_presence(self, client, auth_token, created_location_id):
        # From 30m away → is_within_reach = True
        response = await client.get(
            f"/api/v1/map/locations/{created_location_id}",
            params={"lat": BEN_THANH["latitude"] + 0.0003, "lng": BEN_THANH["longitude"]},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        data = response.json()
        assert data["is_within_reach"] is True

    async def test_not_within_reach(self, client, auth_token, created_location_id):
        # From 800m away → is_within_reach = False
        response = await client.get(
            f"/api/v1/map/locations/{created_location_id}",
            params={"lat": NOTRE_DAME["latitude"], "lng": NOTRE_DAME["longitude"]},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        data = response.json()
        assert data["is_within_reach"] is False
"""
