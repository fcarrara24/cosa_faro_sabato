-- Initialize database schema for Bergamo Events
-- This file is automatically executed when the PostgreSQL container starts

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)
-- Create extensions for geospatial queries (optional)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";  -- Uncomment if you need geospatial features

-- Create indexes for better performance
-- These will be created by SQLAlchemy, but we can add additional ones here

-- Example: Full-text search index (PostgreSQL specific)
-- CREATE INDEX IF NOT EXISTS idx_events_fulltext ON events USING gin(to_tsvector('italian', title || ' ' || COALESCE(description, '')));

-- Example: Geospatial index (if using PostGIS)
-- CREATE INDEX IF NOT EXISTS idx_events_location ON events USING GIST (ST_Point(longitude, latitude));

-- Set timezone
SET timezone = 'Europe/Rome';
