-- Migration: 011_add_rls_security_fixes.sql
-- Description: Enable RLS on remaining tables and fix SECURITY DEFINER views
-- Date: 2026-01-23
-- Issue: GitHub #3 - Fix RLS and Security Definer warnings from Supabase linter

-- =============================================================================
-- PART 1: ENABLE RLS ON ORGANIZATIONS TABLE
-- =============================================================================
-- Users should only see their own organization

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

-- Users can see their own org
DROP POLICY IF EXISTS user_select_own_org ON organizations;
CREATE POLICY user_select_own_org ON organizations
    FOR SELECT USING (id = get_user_org_id());

-- Only admins can modify orgs (future-proofing for multi-org admin panel)
DROP POLICY IF EXISTS admin_all_orgs ON organizations;
CREATE POLICY admin_all_orgs ON organizations
    FOR ALL USING (
        (SELECT role FROM user_profiles WHERE user_id = auth.uid()) = 'admin'
        AND id = get_user_org_id()
    );

-- =============================================================================
-- PART 2: ENABLE RLS ON SPECIES TABLE
-- =============================================================================
-- Read-only reference data - all authenticated users can read

ALTER TABLE species ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS authenticated_read_species ON species;
CREATE POLICY authenticated_read_species ON species
    FOR SELECT USING (auth.uid() IS NOT NULL);

-- Only admins can modify species (reference data)
DROP POLICY IF EXISTS admin_manage_species ON species;
CREATE POLICY admin_manage_species ON species
    FOR ALL USING (
        (SELECT role FROM user_profiles WHERE user_id = auth.uid()) = 'admin'
    );

-- =============================================================================
-- PART 3: ENABLE RLS ON PSC_ALLOCATIONS TABLE (if exists)
-- =============================================================================
-- Read-only reference data - all authenticated users can read

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'psc_allocations') THEN
        ALTER TABLE psc_allocations ENABLE ROW LEVEL SECURITY;

        DROP POLICY IF EXISTS authenticated_read_psc ON psc_allocations;
        CREATE POLICY authenticated_read_psc ON psc_allocations
            FOR SELECT USING (auth.uid() IS NOT NULL);

        DROP POLICY IF EXISTS admin_manage_psc ON psc_allocations;
        CREATE POLICY admin_manage_psc ON psc_allocations
            FOR ALL USING (
                (SELECT role FROM user_profiles WHERE user_id = auth.uid()) = 'admin'
            );
    END IF;
END $$;

-- =============================================================================
-- PART 4: ENABLE RLS ON LEGACY ACCOUNT TABLES
-- =============================================================================
-- account_balances_raw and account_detail_raw are older tables without org_id
-- These need to be deprecated in favor of efish_* tables, but for now enable RLS

-- Option A: If these tables have org_id, use org isolation
-- Option B: If no org_id, restrict to managers/admins only

-- account_balances_raw - restrict to managers/admins (no org_id column)
ALTER TABLE account_balances_raw ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS manager_access_balances_raw ON account_balances_raw;
CREATE POLICY manager_access_balances_raw ON account_balances_raw
    FOR ALL USING (
        (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

-- account_detail_raw - restrict to managers/admins (no org_id column)
ALTER TABLE account_detail_raw ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS manager_access_detail_raw ON account_detail_raw;
CREATE POLICY manager_access_detail_raw ON account_detail_raw
    FOR ALL USING (
        (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

-- =============================================================================
-- PART 5: FIX SECURITY DEFINER VIEWS
-- =============================================================================
-- Views that use SECURITY DEFINER bypass RLS - convert to SECURITY INVOKER
-- where the underlying tables have proper RLS

-- pending_bycatch_alert_count - can use SECURITY INVOKER since bycatch_alerts has RLS
DROP VIEW IF EXISTS pending_bycatch_alert_count;
CREATE VIEW pending_bycatch_alert_count
WITH (security_invoker = true) AS
SELECT
    org_id,
    COUNT(*) as pending_count
FROM bycatch_alerts
WHERE status = 'pending' AND NOT is_deleted
GROUP BY org_id;

-- account_balances view - references account_balances_raw which now has RLS
DROP VIEW IF EXISTS account_balances;
CREATE VIEW account_balances
WITH (security_invoker = true) AS
WITH ranked AS (
    SELECT
        r.*,
        CASE
            WHEN r.account_name LIKE '%Silver Bay%' THEN 'SBS'
            WHEN r.account_name LIKE '%North Pacific%' THEN 'NP'
            WHEN r.account_name LIKE '%OBSI%' THEN 'OBSI'
            WHEN r.account_name LIKE '%Star of Kodiak%' THEN 'SOK'
        END as coop_code,
        CASE r.species_group
            WHEN 'POPA' THEN 141
            WHEN 'NORK' THEN 136
            WHEN 'DUSK' THEN 172
            WHEN 'HLBT' THEN 200
            WHEN 'PCOD' THEN 110
            WHEN 'SABL' THEN 710
            WHEN 'THDS' THEN 143
        END as species_code,
        ROW_NUMBER() OVER (
            PARTITION BY r.account_name, r.species_group
            ORDER BY r.balance_date DESC
        ) as rn
    FROM account_balances_raw r
)
SELECT
    id,
    balance_date,
    account_id,
    account_name,
    coop_code,
    species_group,
    species_code,
    species_group_id,
    initial_quota,
    transfers_in,
    transfers_out,
    total_quota,
    total_catch,
    remaining_quota,
    percent_taken,
    quota_pool_type_code,
    source_file,
    created_by,
    created_at
FROM ranked
WHERE rn = 1;

-- account_detail view - references account_detail_raw which now has RLS
DROP VIEW IF EXISTS account_detail;
CREATE VIEW account_detail
WITH (security_invoker = true) AS
SELECT
    r.*,
    CASE r.species_name
        WHEN 'Pacific Ocean Perch' THEN 141
        WHEN 'Northern Rockfish' THEN 136
        WHEN 'Dusky Rockfish' THEN 172
        WHEN 'Halibut' THEN 200
        WHEN 'Pacific Cod' THEN 110
        WHEN 'Sablefish' THEN 710
        WHEN 'Thornyhead' THEN 143
    END as species_code
FROM account_detail_raw r;

-- =============================================================================
-- VERIFICATION QUERIES (run manually to confirm migration)
-- =============================================================================

/*
-- Check RLS is enabled on all tables:
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('organizations', 'species', 'psc_allocations',
                  'account_balances_raw', 'account_detail_raw')
ORDER BY tablename;

-- Check policies exist:
SELECT policyname, tablename, cmd
FROM pg_policies
WHERE schemaname = 'public'
AND tablename IN ('organizations', 'species', 'psc_allocations',
                  'account_balances_raw', 'account_detail_raw')
ORDER BY tablename, policyname;

-- Check views are SECURITY INVOKER (not DEFINER):
SELECT viewname,
       pg_get_viewdef(viewname::regclass) LIKE '%security_invoker%' as is_invoker
FROM pg_views
WHERE schemaname = 'public'
AND viewname IN ('pending_bycatch_alert_count', 'account_balances', 'account_detail');

-- Test as authenticated user:
-- Should see species (all users)
SELECT COUNT(*) FROM species;

-- Should see own org only
SELECT * FROM organizations;
*/
