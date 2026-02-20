-- LAYERS Database Initialization
-- Runs when PostgreSQL container is first created

-- Ensure PostGIS extensions are enabled in layers_db
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Optional: Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create test database
CREATE DATABASE layers_test_db;

-- Connect to test database and enable extensions
\c layers_test_db
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Switch back to main database
\c layers_db

-- Verify PostGIS is installed
SELECT PostGIS_Version();

-- Log success
DO $$
BEGIN
    RAISE NOTICE '✅ LAYERS Database initialized successfully!';
    RAISE NOTICE '✅ PostGIS version: %', PostGIS_Version();
    RAISE NOTICE '✅ Test database layers_test_db created!';
END $$;