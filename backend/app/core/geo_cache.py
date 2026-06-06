"""
LAYERS - Geo Query Cache Helpers
================================
Cache keys + invalidation for expensive PostGIS reads (fog-of-war viewport,
nearby artifacts). Built on app.core.cache (which fails open when Redis is
down), so wiring these in never risks a crash — worst case you just hit the
database like before.

KEY IDEA — quantize coordinates:
Map panning produces thousands of slightly-different viewports. Rounding the
bounding box / center to ~3 decimals (~110m buckets at HCMC latitude) means
nearby pans share a cache key, so a short TTL absorbs bursts of identical-ish
queries without serving stale data for long.

USAGE:

    from app.core.cache import cache_get_or_set
    from app.core.geo_cache import nearby_key, NEARBY_TTL

    key = nearby_key(lat, lng, radius, layer)
    artifacts = await cache_get_or_set(
        key, NEARBY_TTL,
        lambda: ArtifactService.get_nearby(db, lat, lng, radius, layer),
    )

    # after creating an artifact:
    from app.core.geo_cache import invalidate_on_artifact_create
    await invalidate_on_artifact_create()
"""

from app.core.cache import cache_delete_pattern

# Short TTLs keep cached geo data fresh even with coarse invalidation.
FOG_TTL = 20      # seconds
NEARBY_TTL = 15   # seconds

PRECISION = 3     # decimal places ≈ 110m buckets


def _q(value: float, precision: int = PRECISION) -> float:
    return round(float(value), precision)


def nearby_key(lat: float, lng: float, radius: int, layer: str = "LIGHT") -> str:
    """Cache key for a nearby-artifacts query."""
    return f"nearby:{layer}:{_q(lat)}_{_q(lng)}_{int(radius)}"


def viewport_key(
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    layer: str = "LIGHT",
) -> str:
    """Cache key for a fog-of-war / viewport query (bounding box)."""
    return (
        f"fog:{layer}:{_q(min_lat)}_{_q(min_lng)}_{_q(max_lat)}_{_q(max_lng)}"
    )


async def invalidate_on_artifact_create() -> int:
    """
    Clear the nearby-artifact cache after a new artifact is dropped.

    We clear `nearby:*` (a new artifact can appear in many nearby lists).
    We deliberately do NOT clear `fog:*` — fog is driven by which chunks a
    user has *explored*, not by artifact creation, so it's unaffected.

    Artifact creation is rate-limited (a few per user per day), so clearing
    the whole nearby namespace is cheap and keeps logic simple/correct.
    Returns number of keys removed.
    """
    return await cache_delete_pattern("nearby:*")


async def invalidate_fog_for_layer(layer: str = "*") -> int:
    """Clear fog cache (optionally for one layer). Useful in admin/debug."""
    return await cache_delete_pattern(f"fog:{layer}:*" if layer != "*" else "fog:*")
