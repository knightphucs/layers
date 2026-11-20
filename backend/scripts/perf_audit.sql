-- ============================================================
-- LAYERS — Performance Audit
-- ============================================================
-- Run inside the Postgres container:
--   docker compose cp backend/scripts/perf_audit.sql postgres:/perf_audit.sql
--   docker compose exec postgres psql -U layers_admin -d layers_db -f /perf_audit.sql
-- (or paste sections into psql interactively)
--
-- WORKFLOW:
--   §1 shows what indexes ALREADY exist  (don't create duplicates!)
--   §2 shows table sizes + sequential-scan counts (seq scans on big
--      tables = missing index smell)
--   §3 EXPLAIN ANALYZE templates for the hot queries
--   §4 candidate indexes — create ONLY the ones §1 shows are missing
--      AND §3 proves are needed. Verdicts from the W9D4 run are recorded
--      inline; §4b re-checks for duplicate indexes and §4c for schema drift.
--
-- ⚠️ EXPLAIN on the dev database proves nothing. With a few dozen rows per
-- table Postgres picks a Seq Scan every time no matter what indexes exist.
-- Seed representative volume first, or you will "prove" you need indexes you
-- don't and miss the ones you do.
-- ============================================================

-- ============================================================
-- §1 EXISTING INDEXES — the ground truth
-- ============================================================
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- ============================================================
-- §2 SEQ SCAN SMELL TEST
-- seq_scan high + n_live_tup high = probable missing index
-- ============================================================
SELECT
    relname                       AS table,
    n_live_tup                    AS rows,
    seq_scan,
    idx_scan,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;

-- ============================================================
-- §3 EXPLAIN ANALYZE — the hot paths
-- Replace the :params with real values from your dev data.
-- WHAT TO LOOK FOR:
--   "Index Scan" / "Index Cond"  = good
--   "Seq Scan" on a big table    = bad
--   "Rows Removed by Filter" huge = index not selective enough
-- ============================================================

-- 3a. Nearby artifacts (THE hottest query — every map pan)
EXPLAIN ANALYZE
SELECT * FROM artifacts a
JOIN locations l ON l.id = a.location_id
WHERE ST_DWithin(
    l.geom,
    ST_SetSRID(ST_MakePoint(106.7009, 10.7769), 4326)::geography,
    1000
)
AND a.status = 'ACTIVE'
LIMIT 50;
-- Expect: "Bitmap Index Scan on idx_locations_geom" (GIST). The column is
-- geom, and the index has existed since Week 3 — verified W9D4.
-- If you see Seq Scan on locations → the PostGIS GIST index is missing (§4a).

-- 3b. Badge evaluation — counts xp_events per user per type
EXPLAIN ANALYZE
SELECT event_type, count(*)
FROM xp_events
WHERE user_id = (SELECT id FROM users LIMIT 1)
GROUP BY event_type;
-- Expect: "Index Only Scan using idx_xp_events_user_type", Heap Fetches: 0
-- (migration w9d4_perf_001). Anything else means the index is gone.

-- 3c. Inbox replies — undelivered mail sweep
EXPLAIN ANALYZE
SELECT * FROM artifact_replies
WHERE is_delivered = false
AND deliver_at <= now()
LIMIT 100;
-- Currently returns nothing and is never called by the app: ArtifactReply is
-- INSERT-only, there is no delivery sweep yet. See §4c verdict.

-- 3d. Explored chunks lookup (Fog of War load)
EXPLAIN ANALYZE
SELECT * FROM explored_chunks
WHERE user_id = (SELECT id FROM users LIMIT 1);
-- (adjust table name if yours differs — check §1 output)

-- ============================================================
-- §4 CANDIDATE INDEXES — RESOLVED 2026-09-05 (W9D4)
-- ⚠️ Create ONLY if §1 shows missing AND §3 shows Seq Scan.
-- CONCURRENTLY = no table lock (safe once you have real users;
-- note: CONCURRENTLY can't run inside a transaction block).
--
-- All four were measured against a seeded database (5k users, 50k locations,
-- 50k artifacts, 400k xp_events, 400k explored_chunks) rather than against the
-- near-empty dev database, where every plan is a Seq Scan regardless and
-- nothing can be proven. Verdicts below; only 4b was created.
-- ============================================================

-- 4a. PostGIS spatial index — ALREADY EXISTS, no action.
--     idx_locations_geom ON locations USING gist (geom), created in Week 3.
--     §3a confirms the plan: Bitmap Index Scan on idx_locations_geom, 44 ms
--     for a 1 km radius over 50k locations. Note the column is `geom`, not
--     `coordinates` as this file originally guessed.

-- 4b. Badge evaluation composite (user_id, event_type) — CREATED.
--     Migration w9d4_perf_001. Before: Bitmap Heap Scan, 17.3 ms, 5588
--     buffers. After: Index Only Scan, 5.0 ms, 24 buffers, Heap Fetches: 0.
--     Write cost measured at ~7 µs per XP event, index ~5 MB per 440k rows.
-- CREATE INDEX CONCURRENTLY idx_xp_events_user_type
--     ON xp_events (user_id, event_type);

-- 4c. Slow Mail delivery sweep — NOT CREATED, nothing reads it yet.
--     grep says ArtifactReply is INSERT-only across the whole codebase
--     (artifact_service.py:619). deliver_at and is_delivered are written and
--     never queried — there is no delivery sweep. An index here would be pure
--     write tax. Create it in the same commit that builds the sweep.
-- CREATE INDEX CONCURRENTLY idx_replies_pending_delivery
--     ON artifact_replies (deliver_at)
--     WHERE is_delivered = false;

-- 4d. Artifacts by owner — NOT CREATED, existing index is enough.
--     ix_artifacts_user_id already lands get_user_artifacts in 26 buffers /
--     2.7 ms. Anti-cheat caps drops at 3/day so no owner accumulates enough
--     artifacts to matter, and `status <> DELETED` is a non-equality filter a
--     btree cannot narrow anyway.
-- CREATE INDEX CONCURRENTLY idx_artifacts_user_status
--     ON artifacts (user_id, status);

-- ============================================================
-- §4b DUPLICATE INDEXES — the actual finding of this audit
-- Seven pairs of byte-for-byte identical indexes under two names. Postgres
-- maintains both on every write and can only ever use one. Dropped in
-- migration w9d4_perf_002; run this query to make sure none come back.
-- ============================================================
SELECT tablename,
       regexp_replace(indexdef, '^.*USING ', '') AS definition,
       string_agg(indexname, '  +  ' ORDER BY indexname) AS duplicates
FROM pg_indexes
WHERE schemaname = 'public'
GROUP BY tablename, regexp_replace(indexdef, '^.*USING ', '')
HAVING count(*) > 1
ORDER BY tablename;
-- Expected: 0 rows.
-- Measured impact of the seven before removal: 100k explored_chunks inserts
-- went 1624 ms -> 1245 ms (23% faster) and 19.4 MB per 300k chunks came back.
-- explored_chunks is the busiest write path in the app — POST /explore/batch
-- inserts up to 50 rows every 30 s per active user.

-- ============================================================
-- §4c SCHEMA DRIFT — run this against dev AND a fresh migrate
-- A database built by init_db()'s create_all (DEBUG=True) does NOT hold the
-- same indexes as one built by `alembic upgrade head`. layers_db was short 24
-- indexes that a fresh production deploy creates, which means an EXPLAIN run
-- locally is not testing the schema production will have. Compare the two:
--   createdb layers_shape_check && alembic upgrade head against it,
--   then diff this query's output between the two databases.
-- ============================================================
SELECT tablename, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- ============================================================
-- §5 AFTERCARE — refresh planner stats after creating indexes
-- ============================================================
-- ANALYZE artifacts; ANALYZE xp_events; ANALYZE artifact_replies;
