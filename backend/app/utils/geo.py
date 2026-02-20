"""
LAYERS - Geo Utilities
=======================
Shared geographic utility functions.

FILE: backend/app/utils/geo.py
(Same folder as your existing anti_cheat.py, notifications.py)
"""

import math
import random
from typing import Tuple

EARTH_RADIUS_M = 6_371_000  # meters


def haversine_distance(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
) -> float:
    """
    Distance between two GPS points in METERS.
    
    Example:
        >>> haversine_distance(10.7725, 106.6980, 10.7798, 106.6990)
        ~823m (Ben Thanh to Notre-Dame)
    """
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    )
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def format_distance(meters: float) -> str:
    """
    Format for human display:
      47.3  → "47m"
      1234  → "1.2km"
    """
    if meters < 1000:
        return f"{int(round(meters))}m"
    return f"{meters / 1000:.1f}km"


def is_within_radius(
    user_lat: float, user_lng: float,
    target_lat: float, target_lng: float,
    radius_meters: float,
) -> bool:
    """Check if user is within radius of target."""
    return haversine_distance(user_lat, user_lng, target_lat, target_lng) <= radius_meters


def random_point_in_ring(
    center_lat: float, center_lng: float,
    min_radius_m: float = 200,
    max_radius_m: float = 1000,
) -> Tuple[float, float]:
    """
    Paper Planes random drop algorithm.
    From Masterplan Section 5B:
    1. Random angle θ ∈ [0, 360]
    2. Random distance d ∈ [200, 1000] meters
    3. Calculate target via Haversine inverse
    """
    theta = random.uniform(0, 2 * math.pi)
    distance = random.uniform(min_radius_m, max_radius_m)
    
    lat_r = math.radians(center_lat)
    lng_r = math.radians(center_lng)
    angular_dist = distance / EARTH_RADIUS_M
    
    new_lat = math.asin(
        math.sin(lat_r) * math.cos(angular_dist) +
        math.cos(lat_r) * math.sin(angular_dist) * math.cos(theta)
    )
    new_lng = lng_r + math.atan2(
        math.sin(theta) * math.sin(angular_dist) * math.cos(lat_r),
        math.cos(angular_dist) - math.sin(lat_r) * math.sin(new_lat)
    )
    return (math.degrees(new_lat), math.degrees(new_lng))


def validate_coordinates(lat: float, lng: float) -> bool:
    return -90 <= lat <= 90 and -180 <= lng <= 180


def is_likely_fake_gps(
    prev_lat: float, prev_lng: float,
    curr_lat: float, curr_lng: float,
    time_diff_seconds: float,
) -> bool:
    """
    Anti-cheat: From Masterplan Section 6
    "If coordinates change > 5km in 1 second → Ban"
    """
    if time_diff_seconds <= 0:
        return True
    distance = haversine_distance(prev_lat, prev_lng, curr_lat, curr_lng)
    return (distance / time_diff_seconds) > 5000  # 5km/s threshold
