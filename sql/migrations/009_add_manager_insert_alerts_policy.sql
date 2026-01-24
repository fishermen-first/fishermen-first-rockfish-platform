-- Migration: Add INSERT policy for managers on bycatch_alerts
-- Run this in Supabase SQL Editor
--
-- Issue: Managers could not create alerts on behalf of vessels because
-- the only INSERT policy required reported_by_llp to match the user's own LLP.

-- =============================================================================
-- ADD MANAGER INSERT POLICY
-- =============================================================================

CREATE POLICY manager_insert_alerts ON bycatch_alerts
    FOR INSERT WITH CHECK (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );
