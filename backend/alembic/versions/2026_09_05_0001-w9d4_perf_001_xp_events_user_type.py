"""w9d4 add composite index xp_events(user_id, event_type)

Revision ID: w9d4_perf_001
Revises: w9d3_user_blocks_001
Create Date: 2026-09-05

LAYERS Week 9 Day 4 — performance pass.

WHY this index and no others:

BadgeService._event_counts (app/services/badge_service.py:139-145) runs
    SELECT event_type, count(*) FROM xp_events WHERE user_id = :u GROUP BY event_type
on every badge evaluation. The two separate single-column indexes that already
exist (ix_xp_events_user_id, ix_xp_events_event_type) let Postgres find the
user's rows but not the event_type, so it had to visit the heap for every row.

Measured on a seeded 440k-row xp_events table (power user = 23k events):

    before  Bitmap Heap Scan  →  17.3 ms, 5588 shared buffers
    after   Index Only Scan   →   5.0 ms,   24 shared buffers (Heap Fetches: 0)

Cost side: index is ~5 MB against an 88 MB heap, and 20k inserts went from
188 ms to 334 ms — about 7 µs of extra write per XP event, which are written
one at a time. Worth it for a 233x drop in buffer reads on the read path.

The other candidates in scripts/perf_audit.sql were measured and rejected:
  - locations GIST index already exists (idx_locations_geom) and is used.
  - artifacts (user_id, status): existing ix_artifacts_user_id already lands
    the query in 26 buffers; anti-cheat caps drops at 3/day so no user grows a
    large enough artifact set to matter, and `status <> DELETED` is a
    non-equality filter a btree can't narrow anyway.
  - artifact_replies partial index: ArtifactReply is INSERT-only in the whole
    codebase — no query reads deliver_at/is_delivered yet, so the index would
    be pure write tax. Revisit when the Slow Mail delivery sweep is built.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "w9d4_perf_001"
down_revision = "w9d3_user_blocks_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_xp_events_user_type",
        "xp_events",
        ["user_id", "event_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_xp_events_user_type", table_name="xp_events")
