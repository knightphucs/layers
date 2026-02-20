"""
LAYERS - Exploration Service (Fog of War)
==========================================
The Fog of War system that makes the real world a mystery to uncover.

HOW IT WORKS:
  The map is divided into a grid of ~100m × 100m "chunks".
  When a user walks somewhere, their GPS triggers chunk exploration.
  Unexplored chunks are covered in fog on the client map.
  Walking there clears the fog permanently.

GRID MATH:
  1° latitude  ≈ 111,000 meters (constant everywhere)
  1° longitude ≈ 111,000 × cos(latitude) meters (varies by latitude)
  
  For Ho Chi Minh City (lat ~10.77):
    1° lng ≈ 111,000 × cos(10.77°) ≈ 109,050m
    100m chunk ≈ 0.0009° lat × 0.000917° lng

WHY THIS IS ADDICTIVE:
  - Exploration instinct: humans NEED to fill in blank maps
  - Daily motivation: "I'll walk a new route to clear more fog"
  - Competitive: compare explored % with friends
  - Reveals artifacts: cleared fog shows nearby artifact icons
"""

import math
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.location import ExploredChunk
from app.schemas.location import ExploredChunkResponse, ExplorationStats


# ============================================================
# CONSTANTS
# ============================================================
CHUNK_SIZE_METERS = 100             # Each chunk is ~100m × 100m
METERS_PER_LAT_DEGREE = 111_000    # Universal constant
MAX_CHUNKS_PER_REQUEST = 50        # Prevent abuse
SAIGON_ESTIMATED_CHUNKS = 50_000   # Rough estimate for % calculation

# Ho Chi Minh City approximate bounds (for % calculation)
SAIGON_BOUNDS = {
    "lat_min": 10.68, "lat_max": 10.90,
    "lng_min": 106.60, "lng_max": 106.83,
}


def _calculate_chunk(latitude: float, longitude: float) -> Tuple[int, int]:
    """
    Convert GPS coordinates to chunk grid coordinates.

    This is the SAME algorithm as ExploredChunk.calculate_chunk()
    but as a standalone function for flexibility.

    Returns (chunk_x, chunk_y) where:
      chunk_x = integer grid column (based on longitude)
      chunk_y = integer grid row (based on latitude)
    """
    lat_per_chunk = CHUNK_SIZE_METERS / METERS_PER_LAT_DEGREE
    lng_per_chunk = CHUNK_SIZE_METERS / (METERS_PER_LAT_DEGREE * math.cos(math.radians(latitude)))

    chunk_x = int(longitude / lng_per_chunk)
    chunk_y = int(latitude / lat_per_chunk)

    return chunk_x, chunk_y


def _chunk_to_bounds(chunk_x: int, chunk_y: int, ref_lat: float = 10.77) -> dict:
    """
    Convert chunk coordinates back to GPS bounds (for client rendering).

    Returns { lat_min, lat_max, lng_min, lng_max } of the chunk rectangle.
    """
    lat_per_chunk = CHUNK_SIZE_METERS / METERS_PER_LAT_DEGREE
    lng_per_chunk = CHUNK_SIZE_METERS / (METERS_PER_LAT_DEGREE * math.cos(math.radians(ref_lat)))

    return {
        "lat_min": round(chunk_y * lat_per_chunk, 6),
        "lat_max": round((chunk_y + 1) * lat_per_chunk, 6),
        "lng_min": round(chunk_x * lng_per_chunk, 6),
        "lng_max": round((chunk_x + 1) * lng_per_chunk, 6),
    }


def _get_chunks_in_radius(
    center_lat: float, center_lng: float, radius_meters: float
) -> List[Tuple[int, int]]:
    """
    Get all chunk coordinates that overlap with a circle.
    Used by client to know which chunks to query.
    """
    lat_per_chunk = CHUNK_SIZE_METERS / METERS_PER_LAT_DEGREE
    lng_per_chunk = CHUNK_SIZE_METERS / (METERS_PER_LAT_DEGREE * math.cos(math.radians(center_lat)))

    # How many chunks the radius spans
    lat_range = int(math.ceil(radius_meters / CHUNK_SIZE_METERS)) + 1
    lng_range = int(math.ceil(radius_meters / CHUNK_SIZE_METERS)) + 1

    center_cx, center_cy = _calculate_chunk(center_lat, center_lng)

    chunks = []
    for dy in range(-lat_range, lat_range + 1):
        for dx in range(-lng_range, lng_range + 1):
            chunks.append((center_cx + dx, center_cy + dy))

    return chunks


class ExplorationService:

    # ========================================================
    # EXPLORE — Mark chunk(s) as visited
    # ========================================================

    @staticmethod
    async def explore_at(
        db: AsyncSession,
        user_id: UUID,
        latitude: float,
        longitude: float,
    ) -> dict:
        """
        Mark the chunk at this GPS position as explored.
        Uses PostgreSQL ON CONFLICT DO NOTHING (upsert) for idempotency.

        Returns:
          - is_new: True if this chunk was newly explored
          - chunk: (chunk_x, chunk_y)
          - total_explored: Updated total count
        """
        chunk_x, chunk_y = _calculate_chunk(latitude, longitude)

        # Upsert: insert if not exists, ignore if already explored
        stmt = pg_insert(ExploredChunk).values(
            user_id=user_id,
            chunk_x=chunk_x,
            chunk_y=chunk_y,
            explored_at=datetime.utcnow(),
        ).on_conflict_do_nothing(
            constraint="uq_explored_chunk_user_coords"
        )
        result = await db.execute(stmt)
        await db.commit()

        is_new = result.rowcount > 0

        # Get total count
        total = (await db.execute(
            select(func.count(ExploredChunk.id))
            .where(ExploredChunk.user_id == user_id)
        )).scalar() or 0

        return {
            "is_new": is_new,
            "chunk_x": chunk_x,
            "chunk_y": chunk_y,
            "bounds": _chunk_to_bounds(chunk_x, chunk_y, latitude),
            "total_explored": total,
            "message": "New area discovered! 🗺️" if is_new else "Already explored",
        }

    # ========================================================
    # BATCH EXPLORE — Process GPS trail at once
    # ========================================================

    @staticmethod
    async def batch_explore(
        db: AsyncSession,
        user_id: UUID,
        coordinates: List[dict],  # [{"lat": ..., "lng": ...}, ...]
    ) -> dict:
        """
        Process multiple GPS points at once.
        Useful when client sends buffered location updates.

        Deduplicates chunks before inserting.
        Max 50 points per request (anti-abuse).
        """
        if len(coordinates) > MAX_CHUNKS_PER_REQUEST:
            raise ValueError(f"Max {MAX_CHUNKS_PER_REQUEST} coordinates per request")

        # Convert to unique chunks
        seen = set()
        values = []
        for coord in coordinates:
            cx, cy = _calculate_chunk(coord["lat"], coord["lng"])
            key = (cx, cy)
            if key not in seen:
                seen.add(key)
                values.append({
                    "user_id": user_id,
                    "chunk_x": cx,
                    "chunk_y": cy,
                    "explored_at": datetime.utcnow(),
                })

        if not values:
            return {"new_chunks": 0, "total_explored": 0}

        # Batch upsert
        stmt = pg_insert(ExploredChunk).values(values).on_conflict_do_nothing(
            constraint="uq_explored_chunk_user_coords"
        )
        result = await db.execute(stmt)
        await db.commit()

        new_count = result.rowcount

        total = (await db.execute(
            select(func.count(ExploredChunk.id))
            .where(ExploredChunk.user_id == user_id)
        )).scalar() or 0

        return {
            "new_chunks": new_count,
            "points_processed": len(coordinates),
            "unique_chunks": len(values),
            "total_explored": total,
            "area_sqm": total * (CHUNK_SIZE_METERS ** 2),
        }

    # ========================================================
    # GET EXPLORED — Chunks in a viewport region
    # ========================================================

    @staticmethod
    async def get_explored_chunks(
        db: AsyncSession,
        user_id: UUID,
        lat: float,
        lng: float,
        radius: float = 1000,
    ) -> dict:
        """
        Get explored chunks within a viewport radius.
        Client uses this to render fog (explored = clear, unexplored = fog).

        Returns chunk coordinates + bounds for map overlay rendering.
        """
        # Calculate which chunks fall in the viewport
        viewport_chunks = _get_chunks_in_radius(lat, lng, radius)
        chunk_coords = [(cx, cy) for cx, cy in viewport_chunks]

        if not chunk_coords:
            return {"explored": [], "total_in_viewport": 0, "explored_in_viewport": 0}

        # Query which of these the user has explored
        # Build filter: (chunk_x = cx1 AND chunk_y = cy1) OR (chunk_x = cx2 AND chunk_y = cy2) ...
        # For efficiency, use ranges instead of individual OR clauses
        min_cx = min(c[0] for c in chunk_coords)
        max_cx = max(c[0] for c in chunk_coords)
        min_cy = min(c[1] for c in chunk_coords)
        max_cy = max(c[1] for c in chunk_coords)

        result = await db.execute(
            select(ExploredChunk)
            .where(and_(
                ExploredChunk.user_id == user_id,
                ExploredChunk.chunk_x >= min_cx,
                ExploredChunk.chunk_x <= max_cx,
                ExploredChunk.chunk_y >= min_cy,
                ExploredChunk.chunk_y <= max_cy,
            ))
        )
        explored = result.scalars().all()

        # Convert to response with bounds
        explored_set = {(c.chunk_x, c.chunk_y) for c in explored}
        explored_list = [
            {
                "chunk_x": c.chunk_x,
                "chunk_y": c.chunk_y,
                "explored_at": c.explored_at,
                "bounds": _chunk_to_bounds(c.chunk_x, c.chunk_y, lat),
            }
            for c in explored
        ]

        return {
            "explored": explored_list,
            "total_in_viewport": len(chunk_coords),
            "explored_in_viewport": len(explored_list),
            "fog_percentage": round(
                (1 - len(explored_list) / max(len(chunk_coords), 1)) * 100, 1
            ),
        }

    # ========================================================
    # EXPLORATION STATS — Gamification data
    # ========================================================

    @staticmethod
    async def get_stats(
        db: AsyncSession,
        user_id: UUID,
    ) -> ExplorationStats:
        """
        Get user's exploration statistics for profile/gamification.

        Includes: total chunks, area in sq meters, city percentage,
        recent explorations.
        """
        # Total chunks
        total = (await db.execute(
            select(func.count(ExploredChunk.id))
            .where(ExploredChunk.user_id == user_id)
        )).scalar() or 0

        # Area in square meters
        area_sqm = total * (CHUNK_SIZE_METERS ** 2)

        # Percentage of city (rough estimate)
        percentage = round((total / SAIGON_ESTIMATED_CHUNKS) * 100, 2)
        percentage = min(percentage, 100.0)

        # Recent 20 chunks
        recent_result = await db.execute(
            select(ExploredChunk)
            .where(ExploredChunk.user_id == user_id)
            .order_by(ExploredChunk.explored_at.desc())
            .limit(20)
        )
        recent = [
            ExploredChunkResponse(
                chunk_x=c.chunk_x,
                chunk_y=c.chunk_y,
                explored_at=c.explored_at,
            )
            for c in recent_result.scalars().all()
        ]

        return ExplorationStats(
            total_chunks_explored=total,
            total_area_sqm=area_sqm,
            percentage_of_city=percentage,
            recent_chunks=recent,
        )

    # ========================================================
    # HEATMAP — Community exploration data
    # ========================================================

    @staticmethod
    async def get_community_heatmap(
        db: AsyncSession,
        lat: float,
        lng: float,
        radius: float = 2000,
    ) -> dict:
        """
        Get aggregated exploration data for all users in a region.
        Shows which areas are popular (many explorers) vs untouched.

        Returns chunks with explorer_count for heatmap rendering.
        """
        viewport_chunks = _get_chunks_in_radius(lat, lng, radius)
        if not viewport_chunks:
            return {"heatmap": [], "total_chunks": 0}

        min_cx = min(c[0] for c in viewport_chunks)
        max_cx = max(c[0] for c in viewport_chunks)
        min_cy = min(c[1] for c in viewport_chunks)
        max_cy = max(c[1] for c in viewport_chunks)

        result = await db.execute(
            select(
                ExploredChunk.chunk_x,
                ExploredChunk.chunk_y,
                func.count(func.distinct(ExploredChunk.user_id)).label("explorer_count"),
            )
            .where(and_(
                ExploredChunk.chunk_x >= min_cx,
                ExploredChunk.chunk_x <= max_cx,
                ExploredChunk.chunk_y >= min_cy,
                ExploredChunk.chunk_y <= max_cy,
            ))
            .group_by(ExploredChunk.chunk_x, ExploredChunk.chunk_y)
        )

        heatmap = [
            {
                "chunk_x": row.chunk_x,
                "chunk_y": row.chunk_y,
                "explorer_count": row.explorer_count,
                "bounds": _chunk_to_bounds(row.chunk_x, row.chunk_y, lat),
                "heat_level": (
                    "hot" if row.explorer_count >= 50
                    else "warm" if row.explorer_count >= 10
                    else "cool" if row.explorer_count >= 3
                    else "cold"
                ),
            }
            for row in result.all()
        ]

        return {
            "heatmap": heatmap,
            "total_chunks": len(viewport_chunks),
            "explored_chunks": len(heatmap),
        }

    # ========================================================
    # LEADERBOARD — Top explorers
    # ========================================================

    @staticmethod
    async def get_leaderboard(
        db: AsyncSession,
        limit: int = 10,
    ) -> dict:
        """
        Top explorers by chunks explored.
        Gamification: motivates users to walk more!
        """
        from app.models.user import User

        result = await db.execute(
            select(
                ExploredChunk.user_id,
                func.count(ExploredChunk.id).label("chunks_explored"),
                User.username,
                User.avatar_url,
            )
            .join(User, ExploredChunk.user_id == User.id)
            .group_by(ExploredChunk.user_id, User.username, User.avatar_url)
            .order_by(func.count(ExploredChunk.id).desc())
            .limit(limit)
        )

        leaderboard = [
            {
                "rank": idx + 1,
                "user_id": str(row.user_id),
                "username": row.username,
                "avatar_url": row.avatar_url,
                "chunks_explored": row.chunks_explored,
                "area_sqm": row.chunks_explored * (CHUNK_SIZE_METERS ** 2),
            }
            for idx, row in enumerate(result.all())
        ]

        return {"leaderboard": leaderboard, "total_explorers": len(leaderboard)}
