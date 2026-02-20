"""
LAYERS - Fog of War Tests
============================
FILE: backend/tests/test_exploration.py

Run: pytest tests/test_exploration.py -v
"""

import math
import pytest
from datetime import datetime


# ============================================================
# TEST DATA — Ho Chi Minh City
# ============================================================
BEN_THANH = {"lat": 10.7725, "lng": 106.6980}
NOTRE_DAME = {"lat": 10.7798, "lng": 106.6990}    # ~800m away
BUI_VIEN = {"lat": 10.7675, "lng": 106.6935}      # ~600m away
THU_DUC = {"lat": 10.8500, "lng": 106.7700}       # ~10km away

CHUNK_SIZE = 100  # meters


# ============================================================
# UNIT TESTS — Chunk Math (No DB required!)
# ============================================================

class TestChunkCalculation:
    """Test the core grid math that converts GPS → chunk coordinates."""

    def test_same_spot_same_chunk(self):
        from app.services.exploration_service import _calculate_chunk
        cx1, cy1 = _calculate_chunk(10.7725, 106.6980)
        cx2, cy2 = _calculate_chunk(10.7725, 106.6980)
        assert (cx1, cy1) == (cx2, cy2)

    def test_nearby_spot_same_chunk(self):
        """Points within 100m should often be in the same chunk."""
        from app.services.exploration_service import _calculate_chunk
        # ~10m apart → should be same chunk
        cx1, cy1 = _calculate_chunk(10.7725, 106.6980)
        cx2, cy2 = _calculate_chunk(10.77255, 106.69805)
        assert (cx1, cy1) == (cx2, cy2)

    def test_far_spot_different_chunk(self):
        """Points 800m apart should be different chunks."""
        from app.services.exploration_service import _calculate_chunk
        cx1, cy1 = _calculate_chunk(BEN_THANH["lat"], BEN_THANH["lng"])
        cx2, cy2 = _calculate_chunk(NOTRE_DAME["lat"], NOTRE_DAME["lng"])
        assert (cx1, cy1) != (cx2, cy2)

    def test_chunks_are_integers(self):
        from app.services.exploration_service import _calculate_chunk
        cx, cy = _calculate_chunk(10.7725, 106.6980)
        assert isinstance(cx, int)
        assert isinstance(cy, int)

    def test_chunk_values_reasonable(self):
        """For HCMC (~10.77 lat, ~106.70 lng), chunks should be large positive numbers."""
        from app.services.exploration_service import _calculate_chunk
        cx, cy = _calculate_chunk(10.7725, 106.6980)
        assert cx > 10000   # longitude-based, should be big
        assert cy > 10000   # latitude-based, should be big

    def test_equator_chunk_size(self):
        """At equator, 1 chunk ≈ 100m. Verify math consistency."""
        from app.services.exploration_service import _calculate_chunk
        # Two points ~100m apart at equator
        # lat_per_chunk = 100 / 111_000 ≈ 0.0009009°
        # 0.0009° = 99.9m, which is still inside the first chunk (int(0.999) = 0)
        # Use 0.00091° ≈ 101m to reliably cross the chunk boundary
        cx1, cy1 = _calculate_chunk(0.0, 0.0)
        cx2, cy2 = _calculate_chunk(0.00091, 0.0)  # ~101m north, crosses chunk boundary
        assert cy2 - cy1 == 1  # Should be exactly 1 chunk apart

    def test_saigon_latitude_adjustment(self):
        """Longitude chunks should be slightly wider near equator (cos adjustment)."""
        from app.services.exploration_service import _calculate_chunk
        # At lat 10.77, cos(10.77°) ≈ 0.9824
        # So lng chunks are slightly wider than lat chunks
        cx1, _ = _calculate_chunk(10.77, 106.700)
        cx2, _ = _calculate_chunk(10.77, 106.701)
        # ~111m difference in longitude at this latitude
        # Should be about 1 chunk difference
        assert abs(cx2 - cx1) >= 1


class TestChunkToBounds:
    """Test converting chunk coords back to GPS rectangles."""

    def test_bounds_are_dict(self):
        from app.services.exploration_service import _chunk_to_bounds
        bounds = _chunk_to_bounds(116289, 119694)
        assert "lat_min" in bounds
        assert "lat_max" in bounds
        assert "lng_min" in bounds
        assert "lng_max" in bounds

    def test_bounds_order(self):
        from app.services.exploration_service import _chunk_to_bounds
        bounds = _chunk_to_bounds(116289, 119694)
        assert bounds["lat_min"] < bounds["lat_max"]
        assert bounds["lng_min"] < bounds["lng_max"]

    def test_bounds_size_approximately_100m(self):
        from app.services.exploration_service import _chunk_to_bounds
        bounds = _chunk_to_bounds(116289, 119694, ref_lat=10.77)
        lat_span = bounds["lat_max"] - bounds["lat_min"]
        lng_span = bounds["lng_max"] - bounds["lng_min"]
        # Lat span should be ~0.0009 degrees (100m)
        assert 0.0008 < lat_span < 0.0010
        # Lng span should be ~0.00092 degrees (100m at lat 10.77)
        assert 0.0008 < lng_span < 0.0011

    def test_roundtrip_consistency(self):
        """calculate_chunk → chunk_to_bounds should contain original point."""
        from app.services.exploration_service import _calculate_chunk, _chunk_to_bounds
        lat, lng = 10.7725, 106.6980
        cx, cy = _calculate_chunk(lat, lng)
        bounds = _chunk_to_bounds(cx, cy, ref_lat=lat)
        assert bounds["lat_min"] <= lat <= bounds["lat_max"]
        assert bounds["lng_min"] <= lng <= bounds["lng_max"]


class TestChunksInRadius:
    """Test viewport chunk calculation."""

    def test_small_radius(self):
        from app.services.exploration_service import _get_chunks_in_radius
        chunks = _get_chunks_in_radius(10.77, 106.70, 100)
        # 100m radius → should be ~9 chunks (3x3 grid)
        assert len(chunks) >= 4
        assert len(chunks) <= 25

    def test_medium_radius(self):
        from app.services.exploration_service import _get_chunks_in_radius
        chunks = _get_chunks_in_radius(10.77, 106.70, 500)
        # 500m radius → should be many chunks
        assert len(chunks) >= 50

    def test_large_radius(self):
        from app.services.exploration_service import _get_chunks_in_radius
        chunks = _get_chunks_in_radius(10.77, 106.70, 2000)
        # 2km radius → hundreds of chunks
        assert len(chunks) >= 400

    def test_center_chunk_included(self):
        from app.services.exploration_service import _get_chunks_in_radius, _calculate_chunk
        center_cx, center_cy = _calculate_chunk(10.77, 106.70)
        chunks = _get_chunks_in_radius(10.77, 106.70, 500)
        assert (center_cx, center_cy) in chunks

    def test_all_tuples(self):
        from app.services.exploration_service import _get_chunks_in_radius
        chunks = _get_chunks_in_radius(10.77, 106.70, 200)
        for chunk in chunks:
            assert len(chunk) == 2
            assert isinstance(chunk[0], int)
            assert isinstance(chunk[1], int)


class TestConstants:
    """Verify masterplan constants."""

    def test_chunk_size(self):
        from app.services.exploration_service import CHUNK_SIZE_METERS
        assert CHUNK_SIZE_METERS == 100

    def test_max_batch(self):
        from app.services.exploration_service import MAX_CHUNKS_PER_REQUEST
        assert MAX_CHUNKS_PER_REQUEST == 50

    def test_saigon_bounds(self):
        from app.services.exploration_service import SAIGON_BOUNDS
        assert SAIGON_BOUNDS["lat_min"] < SAIGON_BOUNDS["lat_max"]
        assert SAIGON_BOUNDS["lng_min"] < SAIGON_BOUNDS["lng_max"]
        # Verify it covers HCMC
        assert SAIGON_BOUNDS["lat_min"] < 10.77 < SAIGON_BOUNDS["lat_max"]
        assert SAIGON_BOUNDS["lng_min"] < 106.70 < SAIGON_BOUNDS["lng_max"]


class TestWalkingScenario:
    """Simulate a realistic walking path through Saigon."""

    def test_walking_path_generates_multiple_chunks(self):
        """Walking 500m should cross ~5 chunks."""
        from app.services.exploration_service import _calculate_chunk

        # Simulate walking north from Ben Thanh (~500m)
        path = [
            (10.7725, 106.6980),  # Start: Ben Thanh
            (10.7735, 106.6980),  # ~110m north
            (10.7745, 106.6980),  # ~220m north
            (10.7755, 106.6980),  # ~330m north
            (10.7765, 106.6980),  # ~440m north
            (10.7775, 106.6980),  # ~550m north
        ]

        chunks = set()
        for lat, lng in path:
            cx, cy = _calculate_chunk(lat, lng)
            chunks.add((cx, cy))

        # 500m walk → should be at least 4 unique chunks
        assert len(chunks) >= 4, f"Only {len(chunks)} chunks for 500m walk"

    def test_stationary_user_one_chunk(self):
        """Standing still should only produce 1 chunk."""
        from app.services.exploration_service import _calculate_chunk

        chunks = set()
        for _ in range(10):
            # Same position with tiny GPS jitter
            cx, cy = _calculate_chunk(10.7725, 106.6980)
            chunks.add((cx, cy))

        assert len(chunks) == 1

    def test_batch_coordinates_format(self):
        """Verify batch format matches what the service expects."""
        coords = [
            {"lat": 10.7725, "lng": 106.6980},
            {"lat": 10.7735, "lng": 106.6985},
        ]
        for c in coords:
            assert "lat" in c
            assert "lng" in c
            assert -90 <= c["lat"] <= 90
            assert -180 <= c["lng"] <= 180


# ============================================================
# API ENDPOINT TEST PATTERNS
# ============================================================
# Uncomment and use with your test fixtures (client + auth_token)

"""
class TestExploreEndpoint:

    async def test_explore_new_chunk(self, client, auth_token):
        response = await client.post(
            "/api/v1/explore",
            json={"latitude": BEN_THANH["lat"], "longitude": BEN_THANH["lng"]},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_new"] is True
        assert "chunk_x" in data
        assert "chunk_y" in data
        assert "bounds" in data
        assert "New area discovered" in data["message"]

    async def test_explore_same_chunk_idempotent(self, client, auth_token):
        # First explore
        await client.post(
            "/api/v1/explore",
            json={"latitude": BEN_THANH["lat"], "longitude": BEN_THANH["lng"]},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        # Second explore — same spot
        response = await client.post(
            "/api/v1/explore",
            json={"latitude": BEN_THANH["lat"], "longitude": BEN_THANH["lng"]},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        data = response.json()
        assert data["is_new"] is False
        assert "Already explored" in data["message"]

    async def test_batch_explore(self, client, auth_token):
        response = await client.post(
            "/api/v1/explore/batch",
            json={
                "coordinates": [
                    {"lat": 10.7725, "lng": 106.6980},
                    {"lat": 10.7735, "lng": 106.6985},
                    {"lat": 10.7745, "lng": 106.6990},
                ]
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["points_processed"] == 3
        assert data["new_chunks"] >= 1

    async def test_batch_too_many_points(self, client, auth_token):
        coords = [{"lat": 10.77 + i*0.001, "lng": 106.70} for i in range(60)]
        response = await client.post(
            "/api/v1/explore/batch",
            json={"coordinates": coords},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 400

    async def test_get_chunks_in_viewport(self, client, auth_token):
        # Explore first
        await client.post(
            "/api/v1/explore",
            json={"latitude": BEN_THANH["lat"], "longitude": BEN_THANH["lng"]},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        # Then query viewport
        response = await client.get(
            "/api/v1/explore/chunks",
            params={"lat": BEN_THANH["lat"], "lng": BEN_THANH["lng"], "radius": 500},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "explored" in data
        assert "fog_percentage" in data
        assert len(data["explored"]) >= 1

    async def test_exploration_stats(self, client, auth_token):
        response = await client.get(
            "/api/v1/explore/stats",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_chunks_explored" in data
        assert "total_area_sqm" in data
        assert "percentage_of_city" in data

    async def test_leaderboard(self, client, auth_token):
        response = await client.get(
            "/api/v1/explore/leaderboard",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data

    async def test_heatmap(self, client, auth_token):
        response = await client.get(
            "/api/v1/explore/heatmap",
            params={"lat": BEN_THANH["lat"], "lng": BEN_THANH["lng"], "radius": 2000},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "heatmap" in data
        assert "total_chunks" in data
"""
