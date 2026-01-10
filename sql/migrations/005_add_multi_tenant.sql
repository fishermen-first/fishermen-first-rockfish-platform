-- Migration: 005_add_multi_tenant.sql
-- Description: Add multi-tenant support with org_id across all tables
-- Date: 2026-01-10
-- Rockfish Org ID: 06da23e7-4cce-446a-a9f7-67fc86094b98

-- =============================================================================
-- STEP 1: Create organizations table (if not exists)
-- =============================================================================

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orgs_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_orgs_active ON organizations(is_active) WHERE is_active = true;

-- Insert Rockfish org if not exists (idempotent)
INSERT INTO organizations (id, name, slug)
VALUES ('06da23e7-4cce-446a-a9f7-67fc86094b98', 'Rockfish Cooperative', 'rockfish')
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- STEP 2: Add org_id column to all tables
-- =============================================================================

-- Cooperatives
ALTER TABLE cooperatives ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- Coop Members (LLPs)
ALTER TABLE coop_members ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- Processors
ALTER TABLE processors ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- Annual TAC
ALTER TABLE annual_tac ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- Vessel Allocations
ALTER TABLE vessel_allocations ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- Quota Transfers
ALTER TABLE quota_transfers ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- Harvests
ALTER TABLE harvests ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- eFish tables (uncomment when created)
-- ALTER TABLE efish_account_balance ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
-- ALTER TABLE efish_account_detail ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- User Profiles
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- =============================================================================
-- STEP 3: Backfill org_id with Rockfish org
-- =============================================================================

UPDATE cooperatives
SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98'
WHERE org_id IS NULL;

UPDATE coop_members
SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98'
WHERE org_id IS NULL;

UPDATE processors
SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98'
WHERE org_id IS NULL;

UPDATE annual_tac
SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98'
WHERE org_id IS NULL;

UPDATE vessel_allocations
SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98'
WHERE org_id IS NULL;

UPDATE quota_transfers
SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98'
WHERE org_id IS NULL;

UPDATE harvests
SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98'
WHERE org_id IS NULL;

-- eFish tables (uncomment when created)
-- UPDATE efish_account_balance SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;
-- UPDATE efish_account_detail SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;

UPDATE user_profiles
SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98'
WHERE org_id IS NULL;

-- =============================================================================
-- STEP 4: Add NOT NULL constraints
-- =============================================================================

ALTER TABLE cooperatives ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE coop_members ALTER COLUMN org_id SET NOT NULL;
-- processors.org_id stays nullable (shared processors have NULL org_id)
ALTER TABLE annual_tac ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE vessel_allocations ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE quota_transfers ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE harvests ALTER COLUMN org_id SET NOT NULL;
-- eFish tables (uncomment when created)
-- ALTER TABLE efish_account_balance ALTER COLUMN org_id SET NOT NULL;
-- ALTER TABLE efish_account_detail ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE user_profiles ALTER COLUMN org_id SET NOT NULL;

-- =============================================================================
-- STEP 5: Add indexes for org_id queries
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_cooperatives_org ON cooperatives(org_id);
CREATE INDEX IF NOT EXISTS idx_coop_members_org ON coop_members(org_id);
CREATE INDEX IF NOT EXISTS idx_processors_org ON processors(org_id);
CREATE INDEX IF NOT EXISTS idx_annual_tac_org_year ON annual_tac(org_id, year);
CREATE INDEX IF NOT EXISTS idx_vessel_allocations_org_year ON vessel_allocations(org_id, year);
CREATE INDEX IF NOT EXISTS idx_quota_transfers_org_year ON quota_transfers(org_id, year) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_harvests_org_date ON harvests(org_id, harvest_date) WHERE NOT is_deleted;
-- eFish tables (uncomment when created)
-- CREATE INDEX IF NOT EXISTS idx_efish_balance_org_year ON efish_account_balance(org_id, year);
-- CREATE INDEX IF NOT EXISTS idx_efish_detail_org_year ON efish_account_detail(org_id, year);
CREATE INDEX IF NOT EXISTS idx_user_profiles_org ON user_profiles(org_id);

-- =============================================================================
-- STEP 6: Enable Row-Level Security
-- =============================================================================

ALTER TABLE cooperatives ENABLE ROW LEVEL SECURITY;
ALTER TABLE coop_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE processors ENABLE ROW LEVEL SECURITY;
ALTER TABLE annual_tac ENABLE ROW LEVEL SECURITY;
ALTER TABLE vessel_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE quota_transfers ENABLE ROW LEVEL SECURITY;
ALTER TABLE harvests ENABLE ROW LEVEL SECURITY;
-- eFish tables (uncomment when created)
-- ALTER TABLE efish_account_balance ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE efish_account_detail ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- STEP 7: Helper function for RLS policies
-- =============================================================================

CREATE OR REPLACE FUNCTION get_user_org_id()
RETURNS UUID AS $$
    SELECT org_id FROM user_profiles WHERE user_id = auth.uid()
$$ LANGUAGE SQL SECURITY DEFINER STABLE;

-- =============================================================================
-- STEP 8: RLS Policies (drop existing first for idempotency)
-- =============================================================================

-- Cooperatives
DROP POLICY IF EXISTS org_isolation_cooperatives ON cooperatives;
CREATE POLICY org_isolation_cooperatives ON cooperatives
    FOR ALL USING (org_id = get_user_org_id());

-- Coop Members
DROP POLICY IF EXISTS org_isolation_coop_members ON coop_members;
CREATE POLICY org_isolation_coop_members ON coop_members
    FOR ALL USING (org_id = get_user_org_id());

-- Processors (NULL org_id = shared, otherwise org-specific)
DROP POLICY IF EXISTS org_isolation_processors ON processors;
CREATE POLICY org_isolation_processors ON processors
    FOR ALL USING (org_id IS NULL OR org_id = get_user_org_id());

-- Annual TAC
DROP POLICY IF EXISTS org_isolation_annual_tac ON annual_tac;
CREATE POLICY org_isolation_annual_tac ON annual_tac
    FOR ALL USING (org_id = get_user_org_id());

-- Vessel Allocations
DROP POLICY IF EXISTS org_isolation_vessel_allocations ON vessel_allocations;
CREATE POLICY org_isolation_vessel_allocations ON vessel_allocations
    FOR ALL USING (org_id = get_user_org_id());

-- Quota Transfers
DROP POLICY IF EXISTS org_isolation_quota_transfers ON quota_transfers;
CREATE POLICY org_isolation_quota_transfers ON quota_transfers
    FOR ALL USING (org_id = get_user_org_id());

-- Harvests
DROP POLICY IF EXISTS org_isolation_harvests ON harvests;
CREATE POLICY org_isolation_harvests ON harvests
    FOR ALL USING (org_id = get_user_org_id());

-- eFish tables (uncomment when created)
-- DROP POLICY IF EXISTS org_isolation_efish_balance ON efish_account_balance;
-- CREATE POLICY org_isolation_efish_balance ON efish_account_balance
--     FOR ALL USING (org_id = get_user_org_id());

-- DROP POLICY IF EXISTS org_isolation_efish_detail ON efish_account_detail;
-- CREATE POLICY org_isolation_efish_detail ON efish_account_detail
--     FOR ALL USING (org_id = get_user_org_id());

-- User Profiles
DROP POLICY IF EXISTS org_isolation_user_profiles ON user_profiles;
CREATE POLICY org_isolation_user_profiles ON user_profiles
    FOR ALL USING (org_id = get_user_org_id());

-- =============================================================================
-- STEP 9: Update quota_remaining view to include org_id
-- =============================================================================

-- Must drop first because column order is changing
DROP VIEW IF EXISTS quota_remaining;

CREATE VIEW quota_remaining AS
SELECT
    a.org_id,
    a.llp,
    a.species_code,
    a.year,
    a.allocation_lbs,
    COALESCE(t_in.total, 0) AS transfers_in,
    COALESCE(t_out.total, 0) AS transfers_out,
    COALESCE(h.total, 0) AS harvested,
    a.allocation_lbs
        + COALESCE(t_in.total, 0)
        - COALESCE(t_out.total, 0)
        - COALESCE(h.total, 0) AS remaining_lbs
FROM vessel_allocations a
LEFT JOIN (
    SELECT org_id, to_llp AS llp, species_code, year, SUM(pounds) AS total
    FROM quota_transfers
    WHERE NOT is_deleted
    GROUP BY org_id, to_llp, species_code, year
) t_in USING (org_id, llp, species_code, year)
LEFT JOIN (
    SELECT org_id, from_llp AS llp, species_code, year, SUM(pounds) AS total
    FROM quota_transfers
    WHERE NOT is_deleted
    GROUP BY org_id, from_llp, species_code, year
) t_out USING (org_id, llp, species_code, year)
LEFT JOIN (
    SELECT org_id, llp, species_code, EXTRACT(YEAR FROM harvest_date)::INTEGER AS year, SUM(pounds) AS total
    FROM harvests
    WHERE NOT is_deleted
    GROUP BY org_id, llp, species_code, EXTRACT(YEAR FROM harvest_date)
) h USING (org_id, llp, species_code, year);

-- =============================================================================
-- VERIFICATION QUERIES (run manually to confirm migration)
-- =============================================================================

/*
-- Check org_id is populated in all tables:
SELECT 'cooperatives' as tbl, COUNT(*) as total, COUNT(org_id) as with_org FROM cooperatives
UNION ALL SELECT 'coop_members', COUNT(*), COUNT(org_id) FROM coop_members
UNION ALL SELECT 'processors', COUNT(*), COUNT(org_id) FROM processors
UNION ALL SELECT 'annual_tac', COUNT(*), COUNT(org_id) FROM annual_tac
UNION ALL SELECT 'vessel_allocations', COUNT(*), COUNT(org_id) FROM vessel_allocations
UNION ALL SELECT 'quota_transfers', COUNT(*), COUNT(org_id) FROM quota_transfers
UNION ALL SELECT 'harvests', COUNT(*), COUNT(org_id) FROM harvests
UNION ALL SELECT 'user_profiles', COUNT(*), COUNT(org_id) FROM user_profiles;
-- Add these when efish tables exist:
-- UNION ALL SELECT 'efish_account_balance', COUNT(*), COUNT(org_id) FROM efish_account_balance
-- UNION ALL SELECT 'efish_account_detail', COUNT(*), COUNT(org_id) FROM efish_account_detail

-- Check RLS is enabled:
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('cooperatives', 'coop_members', 'vessel_allocations', 'quota_transfers', 'harvests', 'user_profiles');

-- Check policies exist:
SELECT policyname, tablename
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename;

-- Test quota_remaining view includes org_id:
SELECT * FROM quota_remaining LIMIT 5;
*/
