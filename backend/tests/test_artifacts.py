"""
LAYERS - Artifact & Feature Tests
====================================
FILE: backend/tests/test_artifacts.py

Run: pytest tests/test_artifacts.py -v
"""

import pytest
import hashlib
from datetime import datetime, timedelta
from uuid import uuid4


# ============================================================
# TEST DATA — Ho Chi Minh City
# ============================================================
BEN_THANH = {"latitude": 10.7725, "longitude": 106.6980}
NOTRE_DAME = {"latitude": 10.7798, "longitude": 106.6990}
NEARBY_30M = {"latitude": 10.7728, "longitude": 106.6980}  # ~30m from Ben Thanh


# ============================================================
# UNIT TESTS (No DB required!)
# ============================================================

class TestPasscodeHashing:
    """Test passcode hashing logic."""

    def test_same_code_same_hash(self):
        from app.services.artifact_service import _hash_passcode
        hash1 = _hash_passcode("anniversary2025")
        hash2 = _hash_passcode("anniversary2025")
        assert hash1 == hash2

    def test_different_codes_different_hash(self):
        from app.services.artifact_service import _hash_passcode
        hash1 = _hash_passcode("code123")
        hash2 = _hash_passcode("code456")
        assert hash1 != hash2

    def test_case_insensitive(self):
        from app.services.artifact_service import _hash_passcode
        hash1 = _hash_passcode("MySecret")
        hash2 = _hash_passcode("mysecret")
        assert hash1 == hash2

    def test_strips_whitespace(self):
        from app.services.artifact_service import _hash_passcode
        hash1 = _hash_passcode("hello")
        hash2 = _hash_passcode("  hello  ")
        assert hash1 == hash2

    def test_hash_is_sha256(self):
        from app.services.artifact_service import _hash_passcode
        result = _hash_passcode("test")
        assert len(result) == 64  # SHA-256 hex = 64 chars


class TestTimeLockLogic:
    """Test time-based unlock conditions."""

    def test_no_conditions_not_locked(self):
        from app.services.artifact_service import _check_time_lock
        locked, reason = _check_time_lock(None)
        assert locked is False
        assert reason is None

    def test_empty_conditions_not_locked(self):
        from app.services.artifact_service import _check_time_lock
        locked, reason = _check_time_lock({})
        assert locked is False

    def test_future_date_locked(self):
        from app.services.artifact_service import _check_time_lock
        future = (datetime.utcnow() + timedelta(days=365)).isoformat()
        locked, reason = _check_time_lock({"unlock_date": future})
        assert locked is True
        assert "days" in reason

    def test_past_date_unlocked(self):
        from app.services.artifact_service import _check_time_lock
        past = (datetime.utcnow() - timedelta(days=1)).isoformat()
        locked, reason = _check_time_lock({"unlock_date": past})
        assert locked is False

    def test_time_window_formatting(self):
        from app.services.artifact_service import _check_time_lock
        # Test with a time window — result depends on current time
        locked, reason = _check_time_lock({
            "time_start": "23:00",
            "time_end": "03:00"
        })
        # Should return a bool regardless
        assert isinstance(locked, bool)
        if locked:
            assert "23:00" in reason


class TestPayloadValidation:
    """Test payload validation per content type."""

    def test_letter_requires_text(self):
        from app.services.artifact_service import ArtifactService
        from app.models.artifact import ContentType

        with pytest.raises(ValueError, match="text"):
            ArtifactService._validate_payload(ContentType.LETTER, {})

    def test_letter_requires_nonempty_text(self):
        from app.services.artifact_service import ArtifactService
        from app.models.artifact import ContentType

        with pytest.raises(ValueError, match="text"):
            ArtifactService._validate_payload(ContentType.LETTER, {"text": "   "})

    def test_letter_valid(self):
        from app.services.artifact_service import ArtifactService
        from app.models.artifact import ContentType

        # Should not raise
        ArtifactService._validate_payload(ContentType.LETTER, {"text": "Hello world"})

    def test_voice_requires_url(self):
        from app.services.artifact_service import ArtifactService
        from app.models.artifact import ContentType

        with pytest.raises(ValueError, match="url"):
            ArtifactService._validate_payload(ContentType.VOICE, {"duration_sec": 30})

    def test_photo_requires_url(self):
        from app.services.artifact_service import ArtifactService
        from app.models.artifact import ContentType

        with pytest.raises(ValueError, match="url"):
            ArtifactService._validate_payload(ContentType.PHOTO, {"caption": "test"})

    def test_voucher_requires_code(self):
        from app.services.artifact_service import ArtifactService
        from app.models.artifact import ContentType

        with pytest.raises(ValueError, match="code"):
            ArtifactService._validate_payload(ContentType.VOUCHER, {"discount": 50})

    def test_paper_plane_requires_text(self):
        from app.services.artifact_service import ArtifactService
        from app.models.artifact import ContentType

        with pytest.raises(ValueError, match="text"):
            ArtifactService._validate_payload(ContentType.PAPER_PLANE, {})

    def test_time_capsule_requires_text(self):
        from app.services.artifact_service import ArtifactService
        from app.models.artifact import ContentType

        with pytest.raises(ValueError, match="text"):
            ArtifactService._validate_payload(ContentType.TIME_CAPSULE, {})

    def test_notebook_initializes_pages(self):
        from app.services.artifact_service import ArtifactService
        from app.models.artifact import ContentType

        payload = {}
        ArtifactService._validate_payload(ContentType.NOTEBOOK, payload)
        assert payload["pages"] == []


class TestConstants:
    """Test that masterplan constants are correctly set."""

    def test_proof_of_presence_radius(self):
        from app.services.artifact_service import PROOF_OF_PRESENCE_RADIUS
        assert PROOF_OF_PRESENCE_RADIUS == 50  # 50 meters

    def test_slow_mail_delay(self):
        from app.services.artifact_service import (
            SLOW_MAIL_MIN_DELAY_HOURS,
            SLOW_MAIL_MAX_DELAY_HOURS,
        )
        assert SLOW_MAIL_MIN_DELAY_HOURS == 6
        assert SLOW_MAIL_MAX_DELAY_HOURS == 12
        assert SLOW_MAIL_MIN_DELAY_HOURS < SLOW_MAIL_MAX_DELAY_HOURS

    def test_paper_plane_range(self):
        from app.services.artifact_service import (
            PAPER_PLANE_MIN_DISTANCE,
            PAPER_PLANE_MAX_DISTANCE,
        )
        assert PAPER_PLANE_MIN_DISTANCE == 200
        assert PAPER_PLANE_MAX_DISTANCE == 1000

    def test_auto_hide_threshold(self):
        from app.services.artifact_service import AUTO_HIDE_REPORT_THRESHOLD
        assert AUTO_HIDE_REPORT_THRESHOLD == 5


class TestPaperPlaneAlgorithm:
    """Test Paper Plane random landing using geo utils."""

    def test_landing_within_ring(self):
        from app.utils.geo import random_point_in_ring, haversine_distance

        for _ in range(30):
            lat, lng = random_point_in_ring(
                BEN_THANH["latitude"], BEN_THANH["longitude"],
                min_radius_m=200, max_radius_m=1000,
            )
            dist = haversine_distance(
                BEN_THANH["latitude"], BEN_THANH["longitude"],
                lat, lng,
            )
            assert 180 < dist < 1050, f"Distance {dist} out of 200-1000m ring"

    def test_landing_produces_valid_coordinates(self):
        from app.utils.geo import random_point_in_ring

        for _ in range(20):
            lat, lng = random_point_in_ring(10.77, 106.70)
            assert -90 <= lat <= 90
            assert -180 <= lng <= 180


# ============================================================
# API ENDPOINT TEST PATTERNS
# ============================================================
# Uncomment and use with your test fixtures (client + auth_token)

"""
class TestCreateArtifact:

    async def test_create_letter(self, client, auth_token):
        response = await client.post(
            "/api/v1/artifacts",
            json={
                "latitude": BEN_THANH["latitude"],
                "longitude": BEN_THANH["longitude"],
                "content_type": "LETTER",
                "payload": {"text": "I was here. The sunset was beautiful."},
                "visibility": "PUBLIC",
                "layer": "LIGHT",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content_type"] == "LETTER"
        assert "id" in data

    async def test_create_targeted_letter(self, client, auth_token):
        response = await client.post(
            "/api/v1/artifacts",
            json={
                "latitude": BEN_THANH["latitude"],
                "longitude": BEN_THANH["longitude"],
                "content_type": "LETTER",
                "payload": {"text": "This is only for you 💌"},
                "visibility": "TARGETED",
                "target_username": "testuser2",
                "layer": "LIGHT",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 201

    async def test_create_passcode_letter(self, client, auth_token):
        response = await client.post(
            "/api/v1/artifacts",
            json={
                "latitude": BEN_THANH["latitude"],
                "longitude": BEN_THANH["longitude"],
                "content_type": "LETTER",
                "payload": {"text": "Secret message for our anniversary"},
                "visibility": "PASSCODE",
                "passcode": "20250214",
                "layer": "LIGHT",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 201

    async def test_requires_auth(self, client):
        response = await client.post(
            "/api/v1/artifacts",
            json={
                "latitude": 10.77,
                "longitude": 106.70,
                "content_type": "LETTER",
                "payload": {"text": "hello"},
            },
        )
        assert response.status_code in [401, 403]


class TestNearbyArtifacts:

    async def test_find_nearby(self, client, auth_token):
        response = await client.get(
            "/api/v1/artifacts/nearby",
            params={"lat": BEN_THANH["latitude"], "lng": BEN_THANH["longitude"], "radius": 1000},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_filter_by_layer(self, client, auth_token):
        response = await client.get(
            "/api/v1/artifacts/nearby",
            params={"lat": 10.77, "lng": 106.70, "radius": 1000, "layer": "SHADOW"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200


class TestArtifactDetail:

    async def test_locked_when_far(self, client, auth_token, artifact_id):
        # Query from 800m away → should be geo-locked
        response = await client.get(
            f"/api/v1/artifacts/{artifact_id}",
            params={"lat": NOTRE_DAME["latitude"], "lng": NOTRE_DAME["longitude"]},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        data = response.json()
        assert data["is_locked"] is True
        assert data["lock_reason"] == "distance"
        assert "payload" not in data  # Content hidden!

    async def test_unlocked_when_close(self, client, auth_token, artifact_id):
        # Query from 30m away → should be unlocked (Proof of Presence)
        response = await client.get(
            f"/api/v1/artifacts/{artifact_id}",
            params={"lat": NEARBY_30M["latitude"], "lng": NEARBY_30M["longitude"]},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        data = response.json()
        assert data["is_locked"] is False
        assert "payload" in data  # Content revealed!


class TestPasscodeUnlock:

    async def test_wrong_passcode(self, client, auth_token, passcode_artifact_id):
        response = await client.post(
            f"/api/v1/artifacts/{passcode_artifact_id}/unlock",
            params={
                "passcode": "wrongcode",
                "lat": NEARBY_30M["latitude"],
                "lng": NEARBY_30M["longitude"],
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 400
        assert "Wrong passcode" in response.json()["detail"]

    async def test_correct_passcode(self, client, auth_token, passcode_artifact_id):
        response = await client.post(
            f"/api/v1/artifacts/{passcode_artifact_id}/unlock",
            params={
                "passcode": "20250214",
                "lat": NEARBY_30M["latitude"],
                "lng": NEARBY_30M["longitude"],
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_locked"] is False
        assert "payload" in data


class TestSlowMailReply:

    async def test_reply_success(self, client, auth_token_user2, artifact_id):
        response = await client.post(
            f"/api/v1/artifacts/{artifact_id}/reply",
            json={"content": "Your letter touched my heart 💌"},
            params={"lat": NEARBY_30M["latitude"], "lng": NEARBY_30M["longitude"]},
            headers={"Authorization": f"Bearer {auth_token_user2}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_delivered"] is False  # Slow Mail!
        assert "deliver_at" in data

    async def test_reply_too_far(self, client, auth_token_user2, artifact_id):
        response = await client.post(
            f"/api/v1/artifacts/{artifact_id}/reply",
            json={"content": "test"},
            params={"lat": NOTRE_DAME["latitude"], "lng": NOTRE_DAME["longitude"]},
            headers={"Authorization": f"Bearer {auth_token_user2}"},
        )
        assert response.status_code == 400
        assert "away" in response.json()["detail"]


class TestPaperPlane:

    async def test_throw_paper_plane(self, client, auth_token):
        response = await client.post(
            "/api/v1/artifacts/paper-plane",
            json={
                "text": "Hello stranger! Find me 🛩️",
                "latitude": BEN_THANH["latitude"],
                "longitude": BEN_THANH["longitude"],
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "landed_at" in data
        assert "flight_distance_meters" in data
        assert 200 <= data["flight_distance_meters"] <= 1000


class TestReport:

    async def test_report_artifact(self, client, auth_token, artifact_id):
        response = await client.post(
            f"/api/v1/artifacts/{artifact_id}/report",
            params={"reason": "Inappropriate content - spam message"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Report submitted" in data["message"]
"""
