"""
LAYERS - Location Service
==========================
This is the GEO ENGINE — the brain behind all location operations.

KEY PostGIS FUNCTIONS USED:
- ST_SetSRID(ST_MakePoint(lng, lat), 4326)  → Create a geography point
- ST_DWithin(a, b, meters)                    → Is a within X meters of b?
- ST_Distance(a, b)                           → Distance in meters between a and b
- ST_AsText(geom)                             → Convert to readable text

IMPORTANT: In PostGIS, it's MakePoint(LONGITUDE, LATITUDE) not (lat, lng)!
This trips up EVERYONE. GPS gives lat/lng but PostGIS wants lng/lat.

From Masterplan Section 5A:
  SELECT * FROM artifacts
  JOIN locations ON artifacts.location_id = locations.id
  WHERE ST_DWithin(
      locations.geom,
      ST_SetSRID(ST_MakePoint(:user_lon, :user_lat), 4326),
      1000 -- meters
  );
"""

from uuid import UUID
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_SetSRID, ST_MakePoint

from app.models.location import Location, LayerType
from app.schemas.location import (
    LocationCreate, LocationUpdate, NearbyQuery,
    LocationResponse, LocationListResponse, LocationDetailResponse,
    NearbyCountResponse,
)


# ============================================================
# PROOF OF PRESENCE RADIUS (meters)
# From Masterplan: "User must be within < 50m to interact"
# ============================================================
PROOF_OF_PRESENCE_RADIUS = 50  # meters

# Anti-spam: No new location within 20m of existing one
MIN_DISTANCE_BETWEEN_LOCATIONS = 20  # meters

# Rate limit: Max new locations per day per user
MAX_LOCATIONS_PER_DAY = 3


class LocationService:
    """
    All location-related business logic.
    Each method takes a db session and returns data or raises exceptions.
    """

    # ========================================================
    # CREATE
    # ========================================================

    @staticmethod
    async def create_location(
        db: AsyncSession,
        data: LocationCreate,
        user_id: UUID,
    ) -> Location:
        """
        Create a new location with PostGIS geography point.

        ANTI-SPAM CHECKS:
        1. No duplicate within 20m of existing location
        2. Max 3 new locations per day per user
        """

        # --- Anti-Spam Check 1: Too close to existing location ---
        too_close = await db.execute(
            select(Location.id).where(
                and_(
                    Location.is_active == True,
                    ST_DWithin(
                        Location.geom,
                        ST_SetSRID(
                            ST_MakePoint(data.longitude, data.latitude),
                            4326
                        ),
                        MIN_DISTANCE_BETWEEN_LOCATIONS  # 20 meters
                    )
                )
            ).limit(1)
        )
        if too_close.scalar():
            raise ValueError(
                f"A location already exists within {MIN_DISTANCE_BETWEEN_LOCATIONS}m. "
                "Try a slightly different spot!"
            )

        # --- Anti-Spam Check 2: Daily limit ---
        from datetime import datetime
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        daily_count_result = await db.execute(
            select(func.count(Location.id)).where(
                and_(
                    Location.created_by == user_id,
                    Location.created_at >= today_start
                )
            )
        )
        daily_count = daily_count_result.scalar() or 0

        if daily_count >= MAX_LOCATIONS_PER_DAY:
            raise ValueError(
                f"You can create max {MAX_LOCATIONS_PER_DAY} locations per day. "
                "Come back tomorrow! 🌅"
            )

        # --- Create the location ---
        # CRITICAL: PostGIS wants (longitude, latitude) not (latitude, longitude)!
        geom_wkt = f"SRID=4326;POINT({data.longitude} {data.latitude})"

        location = Location(
            geom=geom_wkt,
            latitude=data.latitude,
            longitude=data.longitude,
            layer=data.layer,
            category=data.category,
            name=data.name,
            description=data.description,
            address=data.address,
            location_meta=data.metadata or {},
            created_by=user_id,
        )
        db.add(location)
        await db.commit()
        await db.refresh(location)

        return location

    # ========================================================
    # READ - NEARBY (The Core Geo-Query!)
    # ========================================================

    @staticmethod
    async def get_nearby(
        db: AsyncSession,
        query: NearbyQuery,
    ) -> LocationListResponse:
        """
        Find locations within radius of user's position.

        This is THE most important query in LAYERS.
        It powers the map view — showing what's around you.

        SQL equivalent:
            SELECT *, ST_Distance(geom, user_point) as distance
            FROM locations
            WHERE ST_DWithin(geom, user_point, :radius)
              AND is_active = true
            ORDER BY distance ASC
            LIMIT :limit OFFSET :offset
        """

        # Create user's position as PostGIS point
        user_point = ST_SetSRID(
            ST_MakePoint(query.lng, query.lat),
            4326
        )

        # Calculate distance for each location
        distance_col = ST_Distance(
            Location.geom,
            user_point
        ).label("distance_meters")

        # Base query: find within radius + active
        base_filter = and_(
            Location.is_active == True,
            ST_DWithin(Location.geom, user_point, query.radius)
        )

        # Optional filters
        filters = [base_filter]
        if query.layer is not None:
            filters.append(Location.layer == query.layer)
        if query.category is not None:
            filters.append(Location.category == query.category)

        combined_filter = and_(*filters)

        # Count total matching (for pagination)
        count_q = select(func.count(Location.id)).where(combined_filter)
        total_result = await db.execute(count_q)
        total = total_result.scalar() or 0

        # Sort order
        if query.sort_by == "distance":
            order = distance_col.asc()
        elif query.sort_by == "newest":
            order = Location.created_at.desc()
        elif query.sort_by == "most_visited":
            order = Location.visit_count.desc()
        elif query.sort_by == "most_artifacts":
            order = Location.artifact_count.desc()
        else:
            order = distance_col.asc()

        # Main query with distance calculation
        stmt = (
            select(Location, distance_col)
            .where(combined_filter)
            .order_by(order)
            .limit(query.limit)
            .offset(query.offset)
        )

        result = await db.execute(stmt)
        rows = result.all()

        # Build response
        items = []
        for location, distance in rows:
            loc_dict = {
                "id": location.id,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "layer": location.layer,
                "category": location.category,
                "name": location.name,
                "description": location.description,
                "address": location.address,
                "metadata": location.location_meta,
                "is_verified": location.is_verified,
                "visit_count": location.visit_count,
                "artifact_count": location.artifact_count,
                "created_by": location.created_by,
                "created_at": location.created_at,
                "distance_meters": round(distance, 1) if distance else None,
            }
            items.append(LocationResponse(**loc_dict))

        return LocationListResponse(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
            has_more=(query.offset + query.limit) < total,
        )

    # ========================================================
    # READ - SINGLE LOCATION
    # ========================================================

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        location_id: UUID,
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
    ) -> Optional[LocationDetailResponse]:
        """
        Get single location with optional distance from user.
        Also calculates if user is_within_reach (< 50m).
        """
        stmt = select(Location).where(
            and_(Location.id == location_id, Location.is_active == True)
        )
        result = await db.execute(stmt)
        location = result.scalar_one_or_none()

        if not location:
            return None

        # Calculate distance if user position provided
        user_distance = None
        is_within_reach = None

        if user_lat is not None and user_lng is not None:
            user_point = ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326)
            dist_result = await db.execute(
                select(ST_Distance(Location.geom, user_point)).where(
                    Location.id == location_id
                )
            )
            user_distance = dist_result.scalar()
            if user_distance is not None:
                user_distance = round(user_distance, 1)
                is_within_reach = user_distance <= PROOF_OF_PRESENCE_RADIUS

        return LocationDetailResponse(
            id=location.id,
            latitude=location.latitude,
            longitude=location.longitude,
            layer=location.layer,
            category=location.category,
            name=location.name,
            description=location.description,
            address=location.address,
            metadata=location.location_meta,
            is_verified=location.is_verified,
            visit_count=location.visit_count,
            artifact_count=location.artifact_count,
            created_by=location.created_by,
            created_at=location.created_at,
            user_distance_meters=user_distance,
            is_within_reach=is_within_reach,
        )

    # ========================================================
    # READ - MY LOCATIONS
    # ========================================================

    @staticmethod
    async def get_user_locations(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> LocationListResponse:
        """Get all locations created by a specific user."""
        base_filter = and_(
            Location.created_by == user_id,
            Location.is_active == True,
        )

        count_result = await db.execute(
            select(func.count(Location.id)).where(base_filter)
        )
        total = count_result.scalar() or 0

        stmt = (
            select(Location)
            .where(base_filter)
            .order_by(Location.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        locations = result.scalars().all()

        items = [
            LocationResponse(
                id=loc.id,
                latitude=loc.latitude,
                longitude=loc.longitude,
                layer=loc.layer,
                category=loc.category,
                name=loc.name,
                description=loc.description,
                address=loc.address,
                metadata=loc.location_meta,
                is_verified=loc.is_verified,
                visit_count=loc.visit_count,
                artifact_count=loc.artifact_count,
                created_by=loc.created_by,
                created_at=loc.created_at,
            )
            for loc in locations
        ]

        return LocationListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )

    # ========================================================
    # READ - NEARBY COUNT (Quick stat for map UI)
    # ========================================================

    @staticmethod
    async def get_nearby_count(
        db: AsyncSession,
        lat: float,
        lng: float,
        radius: float = 1000,
    ) -> NearbyCountResponse:
        """
        Quick count of locations nearby — used for map badge.
        Shows "12 locations nearby" without loading all details.
        """
        user_point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)

        base_filter = and_(
            Location.is_active == True,
            ST_DWithin(Location.geom, user_point, radius)
        )

        # Count total
        total_result = await db.execute(
            select(func.count(Location.id)).where(base_filter)
        )
        total = total_result.scalar() or 0

        # Count per layer
        light_result = await db.execute(
            select(func.count(Location.id)).where(
                and_(base_filter, Location.layer == LayerType.LIGHT)
            )
        )
        light_count = light_result.scalar() or 0

        shadow_count = total - light_count

        # Nearest distance
        nearest_result = await db.execute(
            select(func.min(ST_Distance(Location.geom, user_point))).where(base_filter)
        )
        nearest_dist = nearest_result.scalar()

        return NearbyCountResponse(
            total=total,
            light_count=light_count,
            shadow_count=shadow_count,
            nearest_distance_meters=round(nearest_dist, 1) if nearest_dist else None,
        )

    # ========================================================
    # UPDATE
    # ========================================================

    @staticmethod
    async def update_location(
        db: AsyncSession,
        location_id: UUID,
        data: LocationUpdate,
        user_id: UUID,
    ) -> Optional[Location]:
        """Update a location. Only the creator can update."""
        stmt = select(Location).where(
            and_(
                Location.id == location_id,
                Location.created_by == user_id,
                Location.is_active == True,
            )
        )
        result = await db.execute(stmt)
        location = result.scalar_one_or_none()

        if not location:
            return None

        # Update only provided fields
        # Map schema field names to model attribute names
        field_map = {"metadata": "location_meta"}
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            attr = field_map.get(field, field)
            setattr(location, attr, value)

        await db.commit()
        await db.refresh(location)
        return location

    # ========================================================
    # DELETE (Soft delete)
    # ========================================================

    @staticmethod
    async def delete_location(
        db: AsyncSession,
        location_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Soft delete a location. Only creator can delete."""
        stmt = select(Location).where(
            and_(
                Location.id == location_id,
                Location.created_by == user_id,
                Location.is_active == True,
            )
        )
        result = await db.execute(stmt)
        location = result.scalar_one_or_none()

        if not location:
            return False

        location.is_active = False
        await db.commit()
        return True

    # ========================================================
    # UTILITY - Increment visit count
    # ========================================================

    @staticmethod
    async def increment_visit(
        db: AsyncSession,
        location_id: UUID,
    ) -> None:
        """Increment visit count when user enters 50m radius."""
        stmt = select(Location).where(Location.id == location_id)
        result = await db.execute(stmt)
        location = result.scalar_one_or_none()
        if location:
            location.visit_count += 1
            await db.commit()
