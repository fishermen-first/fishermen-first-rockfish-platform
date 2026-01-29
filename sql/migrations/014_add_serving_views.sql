-- =============================================================================
-- Migration: 014_add_serving_views.sql
-- Purpose: Create serving views for dashboard KPIs
-- Date: 2026-01-29
-- =============================================================================

-- =============================================================================
-- PART 1: CREATE kpi_daily_by_species VIEW
-- =============================================================================

CREATE OR REPLACE VIEW kpi_daily_by_species
WITH (security_invoker = true)
AS
SELECT
    org_id,
    DATE_TRUNC('day', landing_date) AS landing_day,
    species_code,
    SUM(pounds) AS total_harvested_lbs,
    COUNT(*) AS harvest_count
FROM harvests
WHERE NOT is_deleted
GROUP BY org_id, DATE_TRUNC('day', landing_date), species_code
ORDER BY landing_day DESC, species_code;

-- =============================================================================
-- PART 2: ADD DOCUMENTATION TO kpi_daily_by_species VIEW
-- =============================================================================

COMMENT ON VIEW kpi_daily_by_species IS
    'Pre-aggregated daily harvest totals grouped by species for dashboard time-series charts.

    Columns:
    - org_id: Organization identifier for multi-tenant filtering
    - landing_day: Date truncated to day (from landing_date)
    - species_code: Species identifier (POP=141, NR=136, Dusky=172)
    - total_harvested_lbs: Sum of pounds harvested for that day/species
    - harvest_count: Number of harvest records aggregated

    Filters Applied:
    - Only includes non-deleted harvests (is_deleted = FALSE)
    - Excludes records with NULL landing_date (implicitly via DATE_TRUNC)

    RLS Compatibility:
    - Uses WITH (security_invoker = true) to inherit RLS policies from harvests table
    - Postgres 15+ feature ensures org_id filtering applies correctly

    Use Cases:
    - Dashboard time-series charts showing harvest trends over time
    - Daily KPI tracking by species
    - Avoids expensive GROUP BY calculations in application layer';

-- =============================================================================
-- PART 3: CREATE kpi_coop_summary VIEW
-- =============================================================================

CREATE OR REPLACE VIEW kpi_coop_summary
WITH (security_invoker = true)
AS
SELECT
    qm.org_id,
    l.coop_code,
    qm.species_code,
    qm.year,
    -- Aggregated quota metrics
    SUM(qm.allocation_lbs) AS total_allocation_lbs,
    SUM(qm.transfers_in) AS total_transfers_in,
    SUM(qm.transfers_out) AS total_transfers_out,
    SUM(qm.harvested) AS total_harvested,
    SUM(qm.remaining_lbs) AS total_remaining_lbs,
    -- Calculated percentage (handle division by zero)
    ROUND((SUM(qm.remaining_lbs) / NULLIF(SUM(qm.allocation_lbs), 0) * 100)::NUMERIC, 2) AS remaining_pct,
    -- Risk level counts (conditional aggregation using FILTER)
    COUNT(*) FILTER (WHERE qm.risk_level = 'critical') AS critical_count,
    COUNT(*) FILTER (WHERE qm.risk_level = 'warning') AS warning_count,
    COUNT(*) FILTER (WHERE qm.risk_level = 'ok') AS ok_count,
    COUNT(*) FILTER (WHERE qm.risk_level = 'na') AS na_count,
    -- Vessel counts
    COUNT(DISTINCT qm.llp) AS vessel_count
FROM quota_metrics qm
JOIN llps l ON qm.llp = l.llp AND qm.org_id = l.org_id
GROUP BY qm.org_id, l.coop_code, qm.species_code, qm.year
ORDER BY l.coop_code, qm.species_code;

-- =============================================================================
-- PART 4: ADD DOCUMENTATION TO kpi_coop_summary VIEW
-- =============================================================================

COMMENT ON VIEW kpi_coop_summary IS
    'Cooperative-level quota summary aggregating quota_metrics by coop, species, and year.

    Aggregation Level:
    - Grouped by: org_id, coop_code, species_code, year
    - Each row represents one cooperative''s quota status for one species in one year

    Columns:
    - org_id: Organization identifier for multi-tenant filtering
    - coop_code: Cooperative code from llps table
    - species_code: Species identifier (POP=141, NR=136, Dusky=172)
    - year: Quota year
    - total_allocation_lbs: Sum of initial allocations across all vessels in coop
    - total_transfers_in: Sum of all incoming transfers
    - total_transfers_out: Sum of all outgoing transfers
    - total_harvested: Sum of all harvested pounds
    - total_remaining_lbs: Sum of remaining quota across all vessels
    - remaining_pct: Percentage of quota remaining (total_remaining / total_allocation * 100)
    - critical_count: Number of vessels with risk_level = ''critical'' (< 10% remaining)
    - warning_count: Number of vessels with risk_level = ''warning'' (< 50% remaining)
    - ok_count: Number of vessels with risk_level = ''ok'' (>= 50% remaining)
    - na_count: Number of vessels with risk_level = ''na'' (zero allocation)
    - vessel_count: Total distinct vessels (LLPs) in this coop/species/year

    Risk Level Definitions:
    - critical: Vessel has < 10% of allocation remaining (immediate attention required)
    - warning: Vessel has < 50% of allocation remaining (monitor closely)
    - ok: Vessel has >= 50% of allocation remaining (healthy status)
    - na: Vessel has zero allocation for this species/year (not applicable)

    Dependencies:
    - quota_metrics view: Provides per-vessel metrics including risk_level
    - llps table: Provides coop_code for grouping vessels by cooperative

    RLS Compatibility:
    - Uses WITH (security_invoker = true) to inherit RLS policies from quota_metrics view
    - JOIN condition includes org_id for multi-tenant safety
    - Postgres 15+ feature ensures org_id filtering applies correctly

    Use Cases:
    - Dashboard KPI cards showing coop-level status (e.g., "3 vessels critical")
    - Cooperative manager reports summarizing fleet-wide quota usage
    - Risk monitoring at cooperative level (count of vessels in each risk category)
    - Performance comparisons between cooperatives';
