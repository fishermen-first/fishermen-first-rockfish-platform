-- Migration: 012_bycatch_hauls.sql
-- Description: Add multi-haul support for bycatch alerts + RPCA areas + new transfer species
-- Date: 2026-01-28
-- Issue: Bycatch Hauls Enhancement (Chelsea/Danielle client meeting)

-- =============================================================================
-- PART 1: RPCA AREAS LOOKUP TABLE
-- =============================================================================
-- Rockfish Program Chinook Areas - for reporting linkage
-- When an area has too many hotspots, it gets closed to all fishing

CREATE TABLE rpca_areas (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Seed with placeholder values (real values TBD from inter-co-op agreement)
INSERT INTO rpca_areas (code, name, description) VALUES
    ('RPCA-1', 'Rockfish Program Chinook Area 1', 'Placeholder - update with NMFS boundaries'),
    ('RPCA-2', 'Rockfish Program Chinook Area 2', 'Placeholder - update with NMFS boundaries'),
    ('RPCA-3', 'Rockfish Program Chinook Area 3', 'Placeholder - update with NMFS boundaries'),
    ('RPCA-4', 'Rockfish Program Chinook Area 4', 'Placeholder - update with NMFS boundaries'),
    ('RPCA-5', 'Rockfish Program Chinook Area 5', 'Placeholder - update with NMFS boundaries');

-- RLS: Read-only for all authenticated users (reference data)
ALTER TABLE rpca_areas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS authenticated_read_rpca ON rpca_areas;
CREATE POLICY authenticated_read_rpca ON rpca_areas
    FOR SELECT USING (auth.uid() IS NOT NULL);

-- Only admins can modify
DROP POLICY IF EXISTS admin_manage_rpca ON rpca_areas;
CREATE POLICY admin_manage_rpca ON rpca_areas
    FOR ALL USING (
        (SELECT role FROM user_profiles WHERE user_id = auth.uid()) = 'admin'
    );

-- =============================================================================
-- PART 2: BYCATCH HAULS TABLE
-- =============================================================================
-- One-to-many with bycatch_alerts - each alert can have multiple hauls

CREATE TABLE bycatch_hauls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES bycatch_alerts(id) ON DELETE CASCADE,
    haul_number INTEGER NOT NULL,

    -- Location identifier (free text for spot names like "Tater", "Shit Hole", etc.)
    location_name TEXT,

    -- Salmon encounter flag (checkbox to flag hauls with high salmon bycatch)
    high_salmon_encounter BOOLEAN DEFAULT false,

    -- SET information (gear deployment) - required
    set_date DATE NOT NULL,
    set_time TIME,
    set_latitude NUMERIC(9,6) NOT NULL,
    set_longitude NUMERIC(10,6) NOT NULL,

    -- RETRIEVAL information (gear retrieval) - optional
    retrieval_date DATE,
    retrieval_time TIME,
    retrieval_latitude NUMERIC(9,6),
    retrieval_longitude NUMERIC(10,6),

    -- Depth information (in fathoms)
    bottom_depth INTEGER,  -- Ocean floor depth
    sea_depth INTEGER,     -- Depth gear was fishing

    -- RPCA area for reporting linkage
    rpca_area_id INTEGER REFERENCES rpca_areas(id),

    -- Amount (moved from alert level to haul level)
    amount NUMERIC NOT NULL CHECK (amount > 0),

    -- Audit
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Constraints
    UNIQUE (alert_id, haul_number),

    -- Alaska coordinate validation (same as bycatch_alerts)
    CONSTRAINT bh_valid_set_lat CHECK (set_latitude BETWEEN 50.0 AND 72.0),
    CONSTRAINT bh_valid_set_lon CHECK (set_longitude BETWEEN -180.0 AND -130.0),
    CONSTRAINT bh_valid_ret_lat CHECK (
        retrieval_latitude IS NULL OR retrieval_latitude BETWEEN 50.0 AND 72.0
    ),
    CONSTRAINT bh_valid_ret_lon CHECK (
        retrieval_longitude IS NULL OR retrieval_longitude BETWEEN -180.0 AND -130.0
    ),
    CONSTRAINT bh_valid_bottom_depth CHECK (bottom_depth IS NULL OR bottom_depth > 0),
    CONSTRAINT bh_valid_sea_depth CHECK (sea_depth IS NULL OR sea_depth > 0)
);

-- Indexes for common queries
CREATE INDEX idx_bycatch_hauls_alert ON bycatch_hauls(alert_id);
CREATE INDEX idx_bycatch_hauls_salmon ON bycatch_hauls(alert_id)
    WHERE high_salmon_encounter = true;
CREATE INDEX idx_bycatch_hauls_rpca ON bycatch_hauls(rpca_area_id)
    WHERE rpca_area_id IS NOT NULL;

-- =============================================================================
-- PART 3: RLS FOR BYCATCH_HAULS
-- =============================================================================
-- Hauls inherit access from parent alert via join

ALTER TABLE bycatch_hauls ENABLE ROW LEVEL SECURITY;

-- Vessel owners can see/insert hauls for their own alerts
DROP POLICY IF EXISTS vessel_owner_hauls ON bycatch_hauls;
CREATE POLICY vessel_owner_hauls ON bycatch_hauls
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM bycatch_alerts ba
            WHERE ba.id = bycatch_hauls.alert_id
            AND ba.org_id = get_user_org_id()
            AND ba.reported_by_llp = (
                SELECT llp FROM user_profiles WHERE user_id = auth.uid()
            )
        )
    );

-- Managers/admins can access all hauls in their org
DROP POLICY IF EXISTS manager_hauls ON bycatch_hauls;
CREATE POLICY manager_hauls ON bycatch_hauls
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM bycatch_alerts ba
            WHERE ba.id = bycatch_hauls.alert_id
            AND ba.org_id = get_user_org_id()
            AND (SELECT role FROM user_profiles WHERE user_id = auth.uid())
                IN ('admin', 'manager')
        )
    );

-- =============================================================================
-- PART 4: MIGRATE EXISTING ALERTS TO HAUL FORMAT
-- =============================================================================
-- Create "haul 1" for each existing alert, preserving existing data

INSERT INTO bycatch_hauls (
    alert_id,
    haul_number,
    set_date,
    set_latitude,
    set_longitude,
    amount,
    created_at
)
SELECT
    id,
    1,  -- First haul
    COALESCE(created_at::date, CURRENT_DATE),
    latitude,
    longitude,
    amount,
    created_at
FROM bycatch_alerts
WHERE NOT is_deleted;

-- =============================================================================
-- PART 5: ADD COORDINATE FORMAT PREFERENCE TO ALERTS (optional)
-- =============================================================================
-- Tracks user preference for DMS vs decimal display

ALTER TABLE bycatch_alerts ADD COLUMN IF NOT EXISTS coordinate_format TEXT
    DEFAULT 'dms' CHECK (coordinate_format IN ('dms', 'decimal'));

-- =============================================================================
-- PART 6: DEPRECATE OLD COLUMNS ON BYCATCH_ALERTS
-- =============================================================================
-- Note: Do NOT drop columns yet - keep for backwards compatibility during transition
-- These will be removed in a future migration (013_remove_legacy_alert_columns.sql)
-- after confirming all data is migrated and code is updated

COMMENT ON COLUMN bycatch_alerts.latitude IS
    'DEPRECATED: Use bycatch_hauls.set_latitude instead. Will be removed in v2.0';
COMMENT ON COLUMN bycatch_alerts.longitude IS
    'DEPRECATED: Use bycatch_hauls.set_longitude instead. Will be removed in v2.0';
COMMENT ON COLUMN bycatch_alerts.amount IS
    'DEPRECATED: Use bycatch_hauls.amount (sum for total). Will be removed in v2.0';

-- =============================================================================
-- PART 7: ADD NEW SPECIES FOR TRANSFERS
-- =============================================================================
-- Add Shortraker and Rougheye rockfish (not currently in species table)
-- Thornyhead (143) and Halibut (200) already exist
-- Note: species table has columns (code, species_name, is_psc, unit) - no short_name
-- Use WHERE NOT EXISTS since species.code has no unique constraint

INSERT INTO species (code, species_name, is_psc, unit)
SELECT 137, 'Shortraker Rockfish', false, 'lbs'
WHERE NOT EXISTS (SELECT 1 FROM species WHERE code = 137);

INSERT INTO species (code, species_name, is_psc, unit)
SELECT 138, 'Rougheye Rockfish', false, 'lbs'
WHERE NOT EXISTS (SELECT 1 FROM species WHERE code = 138);

-- Ensure Halibut is transferable (update is_psc if needed)
-- Halibut (200) should be PSC but still transferable in certain cases
-- No change needed - leave as is, app logic handles it

-- =============================================================================
-- PART 8: HELPER FUNCTION FOR TOTAL AMOUNT
-- =============================================================================
-- Function to compute total amount from hauls (for display)

CREATE OR REPLACE FUNCTION get_alert_total_amount(alert_uuid UUID)
RETURNS NUMERIC AS $$
    SELECT COALESCE(SUM(amount), 0)
    FROM bycatch_hauls
    WHERE alert_id = alert_uuid;
$$ LANGUAGE SQL STABLE;

-- =============================================================================
-- VERIFICATION QUERIES (run manually to confirm migration)
-- =============================================================================

/*
-- Check RPCA areas seeded:
SELECT * FROM rpca_areas ORDER BY code;

-- Check hauls created from existing alerts:
SELECT
    ba.id as alert_id,
    ba.status,
    ba.latitude as old_lat,
    bh.set_latitude as new_lat,
    ba.amount as old_amount,
    bh.amount as new_amount
FROM bycatch_alerts ba
LEFT JOIN bycatch_hauls bh ON ba.id = bh.alert_id
WHERE NOT ba.is_deleted
ORDER BY ba.created_at DESC
LIMIT 10;

-- Check RLS works for hauls:
SELECT COUNT(*) FROM bycatch_hauls;

-- Check new species added:
SELECT * FROM species WHERE code IN (137, 138);

-- Test helper function:
SELECT
    ba.id,
    get_alert_total_amount(ba.id) as total_amount
FROM bycatch_alerts ba
WHERE NOT ba.is_deleted
LIMIT 5;
*/
