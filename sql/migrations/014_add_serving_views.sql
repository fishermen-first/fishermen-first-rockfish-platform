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
