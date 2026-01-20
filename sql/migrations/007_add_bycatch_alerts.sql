-- Migration: Add bycatch alerts, vessel contacts, and email log tables
-- Run this in Supabase SQL Editor

-- =============================================================================
-- 1. BYCATCH ALERTS TABLE
-- =============================================================================
-- Vessel owners report bycatch hotspots, managers review and share to fleet

CREATE TABLE bycatch_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    reported_by_llp TEXT NOT NULL,  -- No FK; LLP validated via RLS policies
    species_code INTEGER NOT NULL,  -- No FK; species validated via dropdown
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(10,6) NOT NULL,
    amount NUMERIC NOT NULL CHECK (amount > 0),
    details TEXT,

    -- Status workflow: pending -> shared/dismissed (one-way for broadcast safety)
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'shared', 'dismissed')),
    shared_at TIMESTAMPTZ,
    shared_by UUID REFERENCES auth.users(id),
    shared_recipient_count INTEGER,

    -- Audit
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false,
    deleted_by UUID REFERENCES auth.users(id),
    deleted_at TIMESTAMPTZ,

    -- GPS coordinate validation (Alaska fishing areas)
    CONSTRAINT valid_latitude CHECK (latitude BETWEEN 50.0 AND 72.0),
    CONSTRAINT valid_longitude CHECK (longitude BETWEEN -180.0 AND -130.0)
);

-- Indexes for common queries
CREATE INDEX idx_bycatch_alerts_org_status ON bycatch_alerts(org_id, status) WHERE NOT is_deleted;
CREATE INDEX idx_bycatch_alerts_pending ON bycatch_alerts(org_id) WHERE status = 'pending' AND NOT is_deleted;
CREATE INDEX idx_bycatch_alerts_created ON bycatch_alerts(org_id, created_at DESC) WHERE NOT is_deleted;

-- =============================================================================
-- 2. VESSEL CONTACTS TABLE
-- =============================================================================
-- Multiple contacts per LLP for email alerts

CREATE TABLE vessel_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    llp TEXT NOT NULL,  -- No FK; LLP validated via application logic
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT false,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false
);

-- Indexes
CREATE INDEX idx_vessel_contacts_org ON vessel_contacts(org_id) WHERE NOT is_deleted;
CREATE INDEX idx_vessel_contacts_llp ON vessel_contacts(org_id, llp) WHERE NOT is_deleted;
CREATE INDEX idx_vessel_contacts_email ON vessel_contacts(org_id) WHERE NOT is_deleted;

-- =============================================================================
-- 3. ALERT EMAIL LOG TABLE (for debugging)
-- =============================================================================
-- Captures email delivery attempts for troubleshooting

CREATE TABLE alert_email_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES bycatch_alerts(id),
    org_id UUID NOT NULL REFERENCES organizations(id),
    recipient_count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'partial', 'failed')),
    error_message TEXT,
    resend_response JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_alert_email_log_alert ON alert_email_log(alert_id);
CREATE INDEX idx_alert_email_log_org ON alert_email_log(org_id, created_at DESC);

-- =============================================================================
-- 4. ROW-LEVEL SECURITY - BYCATCH ALERTS
-- =============================================================================

ALTER TABLE bycatch_alerts ENABLE ROW LEVEL SECURITY;

-- Vessel owners can insert alerts for their own LLP only
CREATE POLICY vessel_owner_insert_alerts ON bycatch_alerts
    FOR INSERT WITH CHECK (
        org_id = get_user_org_id()
        AND reported_by_llp = (
            SELECT llp FROM user_profiles WHERE user_id = auth.uid()
        )
    );

-- Vessel owners can view their own alerts
CREATE POLICY vessel_owner_select_alerts ON bycatch_alerts
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND reported_by_llp = (
            SELECT llp FROM user_profiles WHERE user_id = auth.uid()
        )
    );

-- Managers and admins can view all org alerts
CREATE POLICY manager_select_alerts ON bycatch_alerts
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

-- Managers and admins can update org alerts (share/dismiss)
CREATE POLICY manager_update_alerts ON bycatch_alerts
    FOR UPDATE USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

-- =============================================================================
-- 5. ROW-LEVEL SECURITY - VESSEL CONTACTS
-- =============================================================================

ALTER TABLE vessel_contacts ENABLE ROW LEVEL SECURITY;

-- Org isolation for vessel contacts
CREATE POLICY org_isolation_vessel_contacts ON vessel_contacts
    FOR ALL USING (org_id = get_user_org_id());

-- =============================================================================
-- 6. ROW-LEVEL SECURITY - ALERT EMAIL LOG
-- =============================================================================

ALTER TABLE alert_email_log ENABLE ROW LEVEL SECURITY;

-- Only managers/admins can view email logs
CREATE POLICY manager_select_email_log ON alert_email_log
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

-- =============================================================================
-- 7. BOOTSTRAP: SEED CONTACTS FROM EXISTING VESSEL OWNERS
-- =============================================================================
-- Creates one contact per vessel owner account so feature works on day one

INSERT INTO vessel_contacts (org_id, llp, name, email, is_primary)
SELECT
    up.org_id,
    up.llp,
    COALESCE(SPLIT_PART(up.email, '@', 1), 'Vessel Owner'),
    up.email,
    true
FROM user_profiles up
WHERE up.role = 'vessel_owner'
  AND up.llp IS NOT NULL
ON CONFLICT DO NOTHING;

-- =============================================================================
-- 8. HELPER VIEW FOR PENDING ALERT COUNT
-- =============================================================================

CREATE OR REPLACE VIEW pending_bycatch_alert_count AS
SELECT
    org_id,
    COUNT(*) as pending_count
FROM bycatch_alerts
WHERE status = 'pending' AND NOT is_deleted
GROUP BY org_id;
