"""w9d4 drop 7 duplicate indexes

Revision ID: w9d4_perf_002
Revises: w9d4_perf_001
Create Date: 2026-09-05

LAYERS Week 9 Day 4 — performance pass, second half.

The §1 index inventory turned up seven pairs of indexes that are byte-for-byte
the same index under two names. Postgres maintains both on every write and can
only ever use one, so each pair is pure write tax:

    artifacts        (content_type)               idx_ + ix_
    artifacts        (location_id)                idx_ + ix_
    artifacts        (user_id)                    idx_ + ix_
    chat_rooms       gist (center_geom)           idx_ + ix_
    waves            gist (geom)                  idx_ + ix_
    explored_chunks  (user_id)                    idx_ + ix_
    explored_chunks  (user_id, chunk_x, chunk_y)  idx_ + uq_ constraint

How they got here: w3d5_performance_indexes_001 added idx_artifacts_* and
idx_explored_chunks_* next to the ix_* indexes the models already declare via
index=True, and idx_explored_chunks_user_chunk next to the UniqueConstraint
uq_explored_chunk_user_coords from the initial schema. Separately,
w7d6_fix_schema_gaps added idx_chat_rooms_center_geom / idx_waves_geom without
noticing that w6d3 and w6d4 had already created ix_ versions of both.

WHICH NAME SURVIVES:
  - btree pairs → keep ix_*, which is what the model's index=True generates.
  - GiST pairs  → keep idx_*, which is what GeoAlchemy2 auto-names a Geography
    column's spatial index.
  - explored_chunks composite → keep the uq_ UNIQUE CONSTRAINT; the ON CONFLICT
    in ExplorationService.record_batch depends on the constraint, not the index.
Keeping the model-owned name in every case is what stops autogenerate from
proposing these drops again on the next revision.

MEASURED on a seeded 400k-row explored_chunks table — the busiest write path in
the app, since POST /explore/batch inserts up to 50 chunks every 30s per active
user:

    100k chunk inserts, both duplicates present  →  1624 ms
    100k chunk inserts, duplicates dropped       →  1245 ms   (23% faster)
    disk reclaimed on explored_chunks alone      →  19.4 MB per 300k chunks

DROP INDEX IF EXISTS rather than op.drop_index: layers_db and a freshly migrated
database do not currently hold the same index set (see docs/PRODUCTION_READINESS
"schema drift"), so this has to be a no-op on whichever names are already absent.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "w9d4_perf_002"
down_revision = "w9d4_perf_001"
branch_labels = None
depends_on = None

# (index to drop, index that already covers it)
REDUNDANT = [
    ("idx_artifacts_content_type", "ix_artifacts_content_type"),
    ("idx_artifacts_location_id", "ix_artifacts_location_id"),
    ("idx_artifacts_user_id", "ix_artifacts_user_id"),
    ("ix_chat_rooms_center_geom", "idx_chat_rooms_center_geom"),
    ("ix_waves_geom", "idx_waves_geom"),
    ("idx_explored_chunks_user_id", "ix_explored_chunks_user_id"),
    ("idx_explored_chunks_user_chunk", "uq_explored_chunk_user_coords"),
]


def upgrade() -> None:
    for redundant, _kept in REDUNDANT:
        op.execute(f"DROP INDEX IF EXISTS {redundant}")


def downgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_artifacts_content_type "
        "ON artifacts (content_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_artifacts_location_id "
        "ON artifacts (location_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_artifacts_user_id ON artifacts (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_rooms_center_geom "
        "ON chat_rooms USING gist (center_geom)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_waves_geom ON waves USING gist (geom)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_explored_chunks_user_id "
        "ON explored_chunks (user_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_explored_chunks_user_chunk "
        "ON explored_chunks (user_id, chunk_x, chunk_y)"
    )
