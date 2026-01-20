-- Migration: Add unit column to species and bycatch_alerts tables
-- Run this in Supabase SQL Editor

-- =============================================================================
-- 1. ADD UNIT COLUMN TO SPECIES TABLE
-- =============================================================================
-- Tracks whether species is measured in 'lbs' (pounds) or 'count' (number of fish)

ALTER TABLE species ADD COLUMN IF NOT EXISTS unit TEXT DEFAULT 'lbs';

-- Set Salmon to use count (PSC salmon is tracked by number of fish)
UPDATE species SET unit = 'count' WHERE LOWER(species_name) LIKE '%salmon%';

-- Ensure Halibut uses lbs (PSC halibut is tracked by pounds)
UPDATE species SET unit = 'lbs' WHERE LOWER(species_name) LIKE '%halibut%';

-- =============================================================================
-- 2. ADD UNIT COLUMN TO BYCATCH_ALERTS TABLE
-- =============================================================================
-- Stores the unit at time of alert creation for display consistency

ALTER TABLE bycatch_alerts ADD COLUMN IF NOT EXISTS unit TEXT DEFAULT 'lbs';

-- Backfill existing alerts based on species (if any exist)
UPDATE bycatch_alerts ba
SET unit = s.unit
FROM species s
WHERE ba.species_code = s.code
  AND ba.unit IS NULL;
