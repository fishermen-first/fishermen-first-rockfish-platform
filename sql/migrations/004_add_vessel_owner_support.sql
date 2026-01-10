-- Migration: 004_add_vessel_owner_support.sql
-- Description: Add LLP column to user_profiles and RLS policies for vessel owner role
-- Date: 2026-01-08

-- =============================================================================
-- 1. Add LLP column to user_profiles
-- =============================================================================

ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS llp TEXT;

-- Index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_llp ON user_profiles(llp);

-- =============================================================================
-- 2. Enable Row-Level Security on transaction tables
-- =============================================================================

ALTER TABLE quota_transfers ENABLE ROW LEVEL SECURITY;
ALTER TABLE harvests ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- 3. RLS Policies for quota_transfers
-- =============================================================================

-- Drop existing policies if any (for idempotency)
DROP POLICY IF EXISTS vessel_owner_select_transfers ON quota_transfers;
DROP POLICY IF EXISTS admin_manager_all_transfers ON quota_transfers;

-- Admin/Manager can see all transfers
CREATE POLICY admin_manager_all_transfers ON quota_transfers
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM user_profiles
            WHERE user_id = auth.uid()
            AND role IN ('admin', 'manager')
        )
    );

-- Vessel owner can only SELECT transfers involving their LLP
CREATE POLICY vessel_owner_select_transfers ON quota_transfers
    FOR SELECT
    USING (
        from_llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
        OR
        to_llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
    );

-- =============================================================================
-- 4. RLS Policies for harvests
-- =============================================================================

-- Drop existing policies if any (for idempotency)
DROP POLICY IF EXISTS vessel_owner_select_harvests ON harvests;
DROP POLICY IF EXISTS admin_manager_all_harvests ON harvests;

-- Admin/Manager can see all harvests
CREATE POLICY admin_manager_all_harvests ON harvests
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM user_profiles
            WHERE user_id = auth.uid()
            AND role IN ('admin', 'manager')
        )
    );

-- Vessel owner can only SELECT their own harvests
CREATE POLICY vessel_owner_select_harvests ON harvests
    FOR SELECT
    USING (
        llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
    );

-- =============================================================================
-- 5. Verification queries (run manually to test)
-- =============================================================================

-- Check column was added:
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'user_profiles' AND column_name = 'llp';

-- Check RLS is enabled:
-- SELECT tablename, rowsecurity FROM pg_tables
-- WHERE tablename IN ('quota_transfers', 'harvests');

-- Check policies exist:
-- SELECT policyname, tablename FROM pg_policies
-- WHERE tablename IN ('quota_transfers', 'harvests');
