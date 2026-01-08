-- ============================================
-- REFERENCE TABLES
-- ============================================

CREATE TABLE cooperatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coop_name TEXT,
    coop_code TEXT,
    coop_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE coop_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coop_code TEXT,
    coop_id INTEGER,
    llp TEXT,
    company_name TEXT,
    vessel_name TEXT,
    representative TEXT,
    representative_title TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE vessels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coop_code TEXT,
    vessel_name TEXT,
    adfg_number TEXT,
    is_active TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE processors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    processor_name TEXT,
    processor_code TEXT,
    associated_coop TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE species (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code INTEGER,
    species_name TEXT,
    is_psc BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE annual_tac (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species_code INTEGER,
    year INTEGER,
    tac_mt NUMERIC,
    qs_pool NUMERIC,
    tac_lbs NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE vessel_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    llp TEXT,
    species_code INTEGER,
    year INTEGER,
    allocation_lbs NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE psc_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    species_code INTEGER,
    year INTEGER,
    cv_sector_lbs NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TRANSACTION TABLES
-- ============================================

CREATE TABLE quota_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_llp TEXT,
    to_llp TEXT,
    species_code INTEGER,
    year INTEGER,
    pounds NUMERIC,
    transfer_date DATE,
    notes TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT,
    updated_at TIMESTAMPTZ,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_by TEXT,
    deleted_at TIMESTAMPTZ
);

CREATE TABLE harvests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    llp TEXT,
    species_code INTEGER,
    processor_code TEXT,
    harvest_date DATE,
    pounds NUMERIC,
    source_file TEXT,
    notes TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT,
    updated_at TIMESTAMPTZ,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_by TEXT,
    deleted_at TIMESTAMPTZ
);

-- ============================================
-- USER MANAGEMENT
-- ============================================

CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    processor_code TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- RAW UPLOAD TABLES
-- ============================================

CREATE TABLE account_balances_raw (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    balance_date DATE,
    account_id TEXT,
    account_name TEXT,
    species_group TEXT,
    species_group_id INTEGER,
    initial_quota NUMERIC,
    transfers_in NUMERIC,
    transfers_out NUMERIC,
    total_quota NUMERIC,
    total_catch NUMERIC,
    remaining_quota NUMERIC,
    percent_taken NUMERIC,
    quota_pool_type_code TEXT,
    source_file TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE account_detail_raw (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catch_activity_date DATE,
    processor_permit TEXT,
    vessel_name TEXT,
    adfg TEXT,
    catch_report_type TEXT,
    haul_number TEXT,
    report_number TEXT,
    landing_date DATE,
    gear_code TEXT,
    reporting_area TEXT,
    special_area TEXT,
    species_name TEXT,
    weight_posted NUMERIC,
    count_posted NUMERIC,
    precedence INTEGER,
    source_file TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- VIEWS
-- ============================================

CREATE OR REPLACE VIEW quota_remaining AS
SELECT
    va.llp,
    va.species_code,
    va.year,
    va.allocation_lbs,
    COALESCE(ti.transfers_in, 0) as transfers_in,
    COALESCE(tout.transfers_out, 0) as transfers_out,
    COALESCE(h.harvested, 0) as harvested,
    va.allocation_lbs + COALESCE(ti.transfers_in, 0) - COALESCE(tout.transfers_out, 0) - COALESCE(h.harvested, 0) as remaining_lbs
FROM vessel_allocations va
LEFT JOIN (
    SELECT to_llp as llp, species_code, year, SUM(pounds) as transfers_in
    FROM quota_transfers WHERE is_deleted = FALSE
    GROUP BY to_llp, species_code, year
) ti ON va.llp = ti.llp AND va.species_code = ti.species_code AND va.year = ti.year
LEFT JOIN (
    SELECT from_llp as llp, species_code, year, SUM(pounds) as transfers_out
    FROM quota_transfers WHERE is_deleted = FALSE
    GROUP BY from_llp, species_code, year
) tout ON va.llp = tout.llp AND va.species_code = tout.species_code AND va.year = tout.year
LEFT JOIN (
    SELECT llp, species_code, EXTRACT(YEAR FROM harvest_date)::INTEGER as year, SUM(pounds) as harvested
    FROM harvests WHERE is_deleted = FALSE
    GROUP BY llp, species_code, EXTRACT(YEAR FROM harvest_date)
) h ON va.llp = h.llp AND va.species_code = h.species_code AND va.year = h.year;


CREATE OR REPLACE VIEW account_balances AS
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


CREATE OR REPLACE VIEW account_detail AS
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
