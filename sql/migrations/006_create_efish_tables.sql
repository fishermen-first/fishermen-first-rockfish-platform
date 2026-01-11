-- Migration: 006_create_efish_tables.sql
-- Description: Create eFish reconciliation tables (Account Balance and Account Detail)
-- Date: 2026-01-10
-- Note: These tables are for reconciliation/reporting only - they do NOT affect quota_remaining

-- =============================================================================
-- 1. eFish Account Balance (reconciliation data from CSV uploads)
-- =============================================================================

CREATE TABLE IF NOT EXISTS efish_account_balance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    llp TEXT REFERENCES coop_members(llp),
    species_code INTEGER REFERENCES species(code),
    year INTEGER NOT NULL,

    -- eFish balance fields
    allocation_lbs NUMERIC,
    transfers_in_lbs NUMERIC,
    transfers_out_lbs NUMERIC,
    harvested_lbs NUMERIC,
    remaining_lbs NUMERIC,

    -- Import metadata
    source_file TEXT,
    imported_by UUID REFERENCES auth.users(id),
    imported_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_efish_balance_org_year ON efish_account_balance(org_id, year);
CREATE INDEX IF NOT EXISTS idx_efish_balance_llp ON efish_account_balance(org_id, year, llp);

-- Unique constraint to prevent duplicate imports
CREATE UNIQUE INDEX IF NOT EXISTS idx_efish_balance_unique
    ON efish_account_balance(org_id, llp, species_code, year, source_file);

-- =============================================================================
-- 2. eFish Account Detail (line-item harvest data from CSV uploads)
-- =============================================================================

CREATE TABLE IF NOT EXISTS efish_account_detail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    llp TEXT REFERENCES coop_members(llp),
    species_code INTEGER REFERENCES species(code),
    year INTEGER NOT NULL,

    -- eFish detail fields
    report_number TEXT,
    landing_date DATE,
    processor_code TEXT REFERENCES processors(processor_code),
    pounds NUMERIC,

    -- Import metadata
    source_file TEXT,
    imported_by UUID REFERENCES auth.users(id),
    imported_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_efish_detail_org_year ON efish_account_detail(org_id, year);
CREATE INDEX IF NOT EXISTS idx_efish_detail_llp ON efish_account_detail(org_id, year, llp);
CREATE INDEX IF NOT EXISTS idx_efish_detail_report ON efish_account_detail(report_number);

-- Unique constraint on report_number per org (allow NULLs)
CREATE UNIQUE INDEX IF NOT EXISTS idx_efish_detail_unique_report
    ON efish_account_detail(org_id, report_number)
    WHERE report_number IS NOT NULL;

-- =============================================================================
-- 3. Enable Row-Level Security
-- =============================================================================

ALTER TABLE efish_account_balance ENABLE ROW LEVEL SECURITY;
ALTER TABLE efish_account_detail ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- 4. RLS Policies (org isolation)
-- =============================================================================

DROP POLICY IF EXISTS org_isolation_efish_balance ON efish_account_balance;
CREATE POLICY org_isolation_efish_balance ON efish_account_balance
    FOR ALL USING (org_id = get_user_org_id());

DROP POLICY IF EXISTS org_isolation_efish_detail ON efish_account_detail;
CREATE POLICY org_isolation_efish_detail ON efish_account_detail
    FOR ALL USING (org_id = get_user_org_id());

-- =============================================================================
-- 5. Verification
-- =============================================================================

/*
-- Check tables exist:
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('efish_account_balance', 'efish_account_detail');

-- Check RLS is enabled:
SELECT tablename, rowsecurity FROM pg_tables
WHERE tablename IN ('efish_account_balance', 'efish_account_detail');

-- Check policies:
SELECT policyname, tablename FROM pg_policies
WHERE tablename IN ('efish_account_balance', 'efish_account_detail');
*/
