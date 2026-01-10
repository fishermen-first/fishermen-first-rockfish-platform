-- =============================================================================
-- Fishermen First - Multi-Tenant Schema v2
-- =============================================================================
-- This schema supports multiple organizations (tenants), each with their own
-- co-ops, LLPs, quotas, and data isolation via Row-Level Security.
--
-- Current state: Single org (Rockfish Cooperative) with 4 co-ops
-- Future state: Multi-tenant SaaS with full org isolation
-- =============================================================================

-- =============================================================================
-- 1. ORGANIZATIONS (Top-level tenant)
-- =============================================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,                -- 'Rockfish Cooperative', 'New Client'
    slug TEXT UNIQUE NOT NULL,         -- 'rockfish', 'newclient' (URLs, API keys)
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_orgs_slug ON organizations(slug);
CREATE INDEX idx_orgs_active ON organizations(is_active) WHERE is_active = true;

-- =============================================================================
-- 2. REFERENCE TABLES
-- =============================================================================

-- Species (shared across all orgs - same fish everywhere)
CREATE TABLE species (
    code INTEGER PRIMARY KEY,          -- 141, 136, 172
    name TEXT NOT NULL,                -- 'Pacific Ocean Perch'
    short_name TEXT NOT NULL,          -- 'POP'
    is_target BOOLEAN DEFAULT true,    -- target vs PSC
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Cooperatives (belongs to an org)
CREATE TABLE cooperatives (
    coop_code TEXT PRIMARY KEY,        -- 'SB', 'NP', etc.
    org_id UUID NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_coops_org ON cooperatives(org_id);

-- Processors (can be shared or org-specific)
CREATE TABLE processors (
    processor_code TEXT PRIMARY KEY,   -- 'SB', 'NP', 'OBSI', 'WF'
    org_id UUID REFERENCES organizations(id),  -- NULL = shared across orgs
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_processors_org ON processors(org_id);

-- LLPs (the central entity for quota tracking)
CREATE TABLE llps (
    llp TEXT PRIMARY KEY,              -- 'LLN111111111'
    org_id UUID NOT NULL REFERENCES organizations(id),  -- denormalized for query speed
    coop_code TEXT NOT NULL REFERENCES cooperatives(coop_code),
    vessel_name TEXT,
    adfg_number TEXT,                  -- vessel registration
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_llps_org ON llps(org_id);
CREATE INDEX idx_llps_coop ON llps(coop_code);
CREATE INDEX idx_llps_org_active ON llps(org_id, is_active) WHERE is_active = true;

-- =============================================================================
-- 3. ALLOCATION TABLES
-- =============================================================================

-- Annual TAC (Total Allowable Catch per org/species/year)
CREATE TABLE annual_tac (
    org_id UUID NOT NULL REFERENCES organizations(id),
    species_code INTEGER NOT NULL REFERENCES species(code),
    year INTEGER NOT NULL,
    tac_lbs NUMERIC NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (org_id, species_code, year)
);

CREATE INDEX idx_tac_org_year ON annual_tac(org_id, year);

-- Allocations (starting quota per LLP/species/year)
CREATE TABLE allocations (
    org_id UUID NOT NULL REFERENCES organizations(id),  -- denormalized
    llp TEXT NOT NULL REFERENCES llps(llp),
    species_code INTEGER NOT NULL REFERENCES species(code),
    year INTEGER NOT NULL,
    allocation_lbs NUMERIC NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (llp, species_code, year)
);

CREATE INDEX idx_allocations_org_year ON allocations(org_id, year);
CREATE INDEX idx_allocations_lookup ON allocations(org_id, year, llp);

-- =============================================================================
-- 4. TRANSACTION TABLES (Affect Quota)
-- =============================================================================

-- Transfers (quota movements between LLPs)
CREATE TABLE transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),  -- denormalized
    from_llp TEXT NOT NULL REFERENCES llps(llp),
    to_llp TEXT NOT NULL REFERENCES llps(llp),
    species_code INTEGER NOT NULL REFERENCES species(code),
    year INTEGER NOT NULL,
    pounds NUMERIC NOT NULL CHECK (pounds > 0),
    transfer_date DATE NOT NULL DEFAULT CURRENT_DATE,
    notes TEXT,

    -- Audit
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false,
    deleted_by UUID REFERENCES auth.users(id),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT no_self_transfer CHECK (from_llp != to_llp)
);

CREATE INDEX idx_transfers_org_year ON transfers(org_id, year) WHERE NOT is_deleted;
CREATE INDEX idx_transfers_from ON transfers(org_id, year, from_llp) WHERE NOT is_deleted;
CREATE INDEX idx_transfers_to ON transfers(org_id, year, to_llp) WHERE NOT is_deleted;

-- Harvests (from eLandings API only - deducts from quota)
CREATE TABLE harvests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),  -- denormalized
    llp TEXT NOT NULL REFERENCES llps(llp),
    species_code INTEGER NOT NULL REFERENCES species(code),
    year INTEGER NOT NULL,
    pounds NUMERIC NOT NULL,
    landing_date DATE,
    processor_code TEXT REFERENCES processors(processor_code),

    -- eLandings reference
    elandings_id TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false,

    -- Unique per org (different orgs might have overlapping eLandings IDs)
    CONSTRAINT unique_elandings_per_org UNIQUE (org_id, elandings_id)
);

CREATE INDEX idx_harvests_org_year ON harvests(org_id, year) WHERE NOT is_deleted;
CREATE INDEX idx_harvests_llp ON harvests(org_id, year, llp) WHERE NOT is_deleted;
CREATE INDEX idx_harvests_processor ON harvests(org_id, year, processor_code) WHERE NOT is_deleted;

-- =============================================================================
-- 5. RECONCILIATION TABLES (Do NOT affect quota)
-- =============================================================================

-- eFish Account Balance (CSV uploads for reconciliation)
CREATE TABLE efish_account_balance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    llp TEXT REFERENCES llps(llp),
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
    imported_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT unique_balance_import UNIQUE (org_id, llp, species_code, year, source_file)
);

CREATE INDEX idx_efish_balance_org_year ON efish_account_balance(org_id, year);
CREATE INDEX idx_efish_balance_llp ON efish_account_balance(org_id, year, llp);

-- eFish Account Detail (CSV uploads for reconciliation)
CREATE TABLE efish_account_detail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    llp TEXT REFERENCES llps(llp),
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

-- Unique report number per org (allow NULLs)
CREATE UNIQUE INDEX idx_efish_detail_unique_report
    ON efish_account_detail(org_id, report_number)
    WHERE report_number IS NOT NULL;

CREATE INDEX idx_efish_detail_org_year ON efish_account_detail(org_id, year);
CREATE INDEX idx_efish_detail_llp ON efish_account_detail(org_id, year, llp);

-- =============================================================================
-- 6. AUTH TABLES
-- =============================================================================

-- User Profiles (extends Supabase auth.users)
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id),
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'processor', 'vessel_owner')),
    llp TEXT REFERENCES llps(llp),              -- for vessel_owner role
    processor_code TEXT REFERENCES processors(processor_code),  -- for processor role
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Role-specific validation
    CONSTRAINT vessel_owner_needs_llp CHECK (
        role != 'vessel_owner' OR llp IS NOT NULL
    ),
    CONSTRAINT processor_needs_code CHECK (
        role != 'processor' OR processor_code IS NOT NULL
    )
);

CREATE INDEX idx_user_profiles_org ON user_profiles(org_id);
CREATE INDEX idx_user_profiles_role ON user_profiles(org_id, role);

-- =============================================================================
-- 7. VIEWS
-- =============================================================================

-- Quota Remaining (the core calculation)
CREATE OR REPLACE VIEW quota_remaining AS
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
FROM allocations a
LEFT JOIN (
    SELECT org_id, to_llp AS llp, species_code, year, SUM(pounds) AS total
    FROM transfers
    WHERE NOT is_deleted
    GROUP BY org_id, to_llp, species_code, year
) t_in USING (org_id, llp, species_code, year)
LEFT JOIN (
    SELECT org_id, from_llp AS llp, species_code, year, SUM(pounds) AS total
    FROM transfers
    WHERE NOT is_deleted
    GROUP BY org_id, from_llp, species_code, year
) t_out USING (org_id, llp, species_code, year)
LEFT JOIN (
    SELECT org_id, llp, species_code, year, SUM(pounds) AS total
    FROM harvests
    WHERE NOT is_deleted
    GROUP BY org_id, llp, species_code, year
) h USING (org_id, llp, species_code, year);

-- =============================================================================
-- 8. ROW-LEVEL SECURITY (Org Isolation)
-- =============================================================================

-- Enable RLS on all org-scoped tables
ALTER TABLE cooperatives ENABLE ROW LEVEL SECURITY;
ALTER TABLE processors ENABLE ROW LEVEL SECURITY;
ALTER TABLE llps ENABLE ROW LEVEL SECURITY;
ALTER TABLE annual_tac ENABLE ROW LEVEL SECURITY;
ALTER TABLE allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE transfers ENABLE ROW LEVEL SECURITY;
ALTER TABLE harvests ENABLE ROW LEVEL SECURITY;
ALTER TABLE efish_account_balance ENABLE ROW LEVEL SECURITY;
ALTER TABLE efish_account_detail ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Helper function to get current user's org_id
CREATE OR REPLACE FUNCTION get_user_org_id()
RETURNS UUID AS $$
    SELECT org_id FROM user_profiles WHERE user_id = auth.uid()
$$ LANGUAGE SQL SECURITY DEFINER STABLE;

-- Cooperatives: users see their org's co-ops
CREATE POLICY org_isolation_cooperatives ON cooperatives
    FOR ALL USING (org_id = get_user_org_id());

-- Processors: users see shared (NULL org_id) or their org's processors
CREATE POLICY org_isolation_processors ON processors
    FOR ALL USING (org_id IS NULL OR org_id = get_user_org_id());

-- LLPs: users see their org's LLPs
CREATE POLICY org_isolation_llps ON llps
    FOR ALL USING (org_id = get_user_org_id());

-- Annual TAC: users see their org's TAC
CREATE POLICY org_isolation_tac ON annual_tac
    FOR ALL USING (org_id = get_user_org_id());

-- Allocations: users see their org's allocations
CREATE POLICY org_isolation_allocations ON allocations
    FOR ALL USING (org_id = get_user_org_id());

-- Transfers: users see their org's transfers
CREATE POLICY org_isolation_transfers ON transfers
    FOR ALL USING (org_id = get_user_org_id());

-- Harvests: users see their org's harvests
CREATE POLICY org_isolation_harvests ON harvests
    FOR ALL USING (org_id = get_user_org_id());

-- eFish Account Balance: users see their org's data
CREATE POLICY org_isolation_efish_balance ON efish_account_balance
    FOR ALL USING (org_id = get_user_org_id());

-- eFish Account Detail: users see their org's data
CREATE POLICY org_isolation_efish_detail ON efish_account_detail
    FOR ALL USING (org_id = get_user_org_id());

-- User Profiles: users see their org's users (admin/manager only for full list)
CREATE POLICY org_isolation_user_profiles ON user_profiles
    FOR ALL USING (org_id = get_user_org_id());

-- =============================================================================
-- 9. MIGRATION: Create Rockfish Org and Backfill
-- =============================================================================
-- Run this section to migrate existing data to multi-tenant schema

-- Step 1: Create the Rockfish organization (COMPLETED)
-- INSERT INTO organizations (id, name, slug)
-- VALUES (gen_random_uuid(), 'Rockfish Cooperative', 'rockfish')
-- RETURNING id;

-- Rockfish Cooperative org_id: 06da23e7-4cce-446a-a9f7-67fc86094b98

-- Step 2: Backfill org_id to existing tables
-- Backfill cooperatives
UPDATE cooperatives SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;

-- Backfill llps (currently named coop_members)
UPDATE coop_members SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;

-- Backfill annual_tac
UPDATE annual_tac SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;

-- Backfill allocations (currently named vessel_allocations)
UPDATE vessel_allocations SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;

-- Backfill transfers (currently named quota_transfers)
UPDATE quota_transfers SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;

-- Backfill harvests
UPDATE harvests SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;

-- Backfill efish tables
UPDATE efish_account_balance SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;
UPDATE efish_account_detail SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;

-- Backfill user_profiles
UPDATE user_profiles SET org_id = '06da23e7-4cce-446a-a9f7-67fc86094b98' WHERE org_id IS NULL;

-- Step 3: Add NOT NULL constraints after backfill
ALTER TABLE cooperatives ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE coop_members ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE annual_tac ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE vessel_allocations ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE quota_transfers ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE harvests ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE efish_account_balance ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE efish_account_detail ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE user_profiles ALTER COLUMN org_id SET NOT NULL;

-- =============================================================================
-- 10. SUMMARY
-- =============================================================================
/*
TABLE RELATIONSHIPS:

organizations (tenant)
    │
    ├── cooperatives (coop_code)
    │       │
    │       └── llps (llp) ◄── PRIMARY KEY FOR QUOTA
    │               │
    │               ├── allocations (starting quota)
    │               ├── transfers (from_llp / to_llp)
    │               ├── harvests (eLandings - deducts quota)
    │               │
    │               └── quota_remaining (calculated view)
    │
    ├── processors (may be shared across orgs)
    │
    ├── efish_account_balance (reconciliation only)
    ├── efish_account_detail (reconciliation only)
    │
    └── user_profiles (users belong to one org)

species (shared across all orgs)


DATA SOURCES:

┌─────────────────────────────────────────────────────────────────┐
│                    QUOTA CALCULATION                            │
│                                                                 │
│  allocations ──► remaining = allocation                         │
│  transfers ────►           + transfers_in                       │
│  harvests ─────►           - transfers_out                      │
│  (eLandings)               - harvested                          │
│                                                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                     quota_remaining ──► Dashboard

┌─────────────────────────────────────────────────────────────────┐
│               RECONCILIATION / REPORTING                        │
│                                                                 │
│  efish_account_balance ──► Compare against quota_remaining      │
│  efish_account_detail ───► to find discrepancies               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘


CORE FORMULA:

    Quota Remaining = Starting Allocation
                    + Transfers In  (to_llp = this LLP)
                    - Transfers Out (from_llp = this LLP)
                    - Harvested     (from eLandings only)


SPECIES CODES:
    - POP (Pacific Ocean Perch): 141
    - NR (Northern Rockfish): 136
    - Dusky (Dusky Rockfish): 172
*/
