-- Migration: Add 'resolved' status for shared alerts that are no longer active
-- Run this in Supabase SQL Editor

-- =============================================================================
-- UPDATE STATUS CONSTRAINT
-- =============================================================================
-- Add 'resolved' as valid status for alerts that were shared but are no longer active hotspots

ALTER TABLE bycatch_alerts
DROP CONSTRAINT IF EXISTS bycatch_alerts_status_check;

ALTER TABLE bycatch_alerts
ADD CONSTRAINT bycatch_alerts_status_check
CHECK (status IN ('pending', 'shared', 'dismissed', 'resolved'));

-- Add columns to track resolution
ALTER TABLE bycatch_alerts
ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS resolved_by UUID REFERENCES auth.users(id);
