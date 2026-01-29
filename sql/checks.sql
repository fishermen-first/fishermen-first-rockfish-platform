-- =============================================================================
-- Data Quality Sanity Checks for Quota Tracking System
-- =============================================================================
-- Purpose: Detect data integrity issues in quota tracking tables
-- Usage: Run manually via psql or SQL editor to identify data quality issues
-- Expected: All queries should return 0 rows if data is valid
--
-- Requirements Coverage:
--   CHEK-01: Detect negative allocation amounts
--   CHEK-02: Detect over-transferred quota (remaining < 0)
--   CHEK-03: Detect future-year data in allocations, transfers, harvests
--   CHEK-04: Detect invalid species codes (not in species table)
--
-- Notes:
-- - Respects soft-delete pattern (is_deleted flag on transfers and harvests)
-- - Uses quota_metrics view for CHEK-02 (includes derived remaining_lbs)
-- - Each query returns descriptive columns for issue tracking
-- =============================================================================


-- =============================================================================
-- CHEK-01: Negative Allocations
-- =============================================================================
-- Detects allocation records with negative pounds
-- Expected: 0 rows (allocations should always be >= 0)
-- Fix: Review data source, correct allocation_lbs to non-negative value
-- =============================================================================

SELECT
    'CHEK-01' AS check_id,
    'Negative allocation detected' AS issue,
    org_id,
    llp,
    species_code,
    year,
    allocation_lbs
FROM allocations
WHERE allocation_lbs < 0
ORDER BY allocation_lbs ASC, year DESC, llp;


-- =============================================================================
-- CHEK-02: Over-Transferred Quota
-- =============================================================================
-- Detects LLP/species/year combinations where remaining quota is negative
-- (indicates transfers out + harvests exceed allocation + transfers in)
-- Expected: 0 rows (can't transfer/harvest more than you have)
-- Fix: Review transfers and harvests for this LLP/species/year, reconcile
-- =============================================================================

SELECT
    'CHEK-02' AS check_id,
    'Over-transferred quota (remaining < 0)' AS issue,
    org_id,
    llp,
    species_code,
    year,
    allocation_lbs,
    transfers_in,
    transfers_out,
    harvested,
    remaining_lbs
FROM quota_metrics
WHERE remaining_lbs < 0
ORDER BY remaining_lbs ASC, year DESC, llp;


-- =============================================================================
-- CHEK-03: Future Year Data
-- =============================================================================
-- Detects records with year > current year in allocations, transfers, harvests
-- Expected: 0 rows (can't have data from the future)
-- Fix: Correct year field to current or past year
-- =============================================================================

WITH current_year_cte AS (
    SELECT EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER AS current_year
)
SELECT
    'CHEK-03' AS check_id,
    'Future year data detected' AS issue,
    'allocations' AS table_name,
    org_id,
    llp,
    species_code,
    year,
    (SELECT current_year FROM current_year_cte) AS current_year
FROM allocations, current_year_cte
WHERE year > current_year_cte.current_year

UNION ALL

SELECT
    'CHEK-03' AS check_id,
    'Future year data detected' AS issue,
    'transfers' AS table_name,
    org_id,
    from_llp AS llp,  -- using from_llp for consistency
    species_code,
    year,
    (SELECT current_year FROM current_year_cte) AS current_year
FROM transfers, current_year_cte
WHERE year > current_year_cte.current_year
  AND NOT is_deleted  -- exclude soft-deleted transfers

UNION ALL

SELECT
    'CHEK-03' AS check_id,
    'Future year data detected' AS issue,
    'harvests' AS table_name,
    org_id,
    llp,
    species_code,
    EXTRACT(YEAR FROM harvest_date)::INTEGER AS year,
    (SELECT current_year FROM current_year_cte) AS current_year
FROM harvests, current_year_cte
WHERE EXTRACT(YEAR FROM harvest_date)::INTEGER > current_year_cte.current_year
  AND NOT is_deleted  -- exclude soft-deleted harvests

ORDER BY table_name, year DESC, llp;


-- =============================================================================
-- CHEK-04: Invalid Species Codes
-- =============================================================================
-- Detects species codes in transaction tables that don't exist in species table
-- Expected: 0 rows (all species codes should be valid references)
-- Fix: Either add missing species to species table, or correct invalid codes
-- =============================================================================

SELECT
    'CHEK-04' AS check_id,
    'Invalid species code (not in species table)' AS issue,
    'allocations' AS table_name,
    species_code,
    COUNT(*) AS affected_rows
FROM allocations
WHERE NOT EXISTS (
    SELECT 1 FROM species WHERE species.code = allocations.species_code
)
GROUP BY species_code

UNION ALL

SELECT
    'CHEK-04' AS check_id,
    'Invalid species code (not in species table)' AS issue,
    'transfers' AS table_name,
    species_code,
    COUNT(*) AS affected_rows
FROM transfers
WHERE NOT is_deleted  -- exclude soft-deleted transfers
  AND NOT EXISTS (
    SELECT 1 FROM species WHERE species.code = transfers.species_code
)
GROUP BY species_code

UNION ALL

SELECT
    'CHEK-04' AS check_id,
    'Invalid species code (not in species table)' AS issue,
    'harvests' AS table_name,
    species_code,
    COUNT(*) AS affected_rows
FROM harvests
WHERE NOT is_deleted  -- exclude soft-deleted harvests
  AND NOT EXISTS (
    SELECT 1 FROM species WHERE species.code = harvests.species_code
)
GROUP BY species_code

ORDER BY table_name, species_code;


-- =============================================================================
-- OPTIONAL: Consolidated Summary Report
-- =============================================================================
-- Uncomment to run all checks and get a simplified summary view
-- Useful for quick scans across all data quality dimensions
-- =============================================================================

/*
SELECT
    check_id,
    COUNT(*) AS issues_found,
    ARRAY_AGG(DISTINCT table_name ORDER BY table_name) FILTER (WHERE table_name IS NOT NULL) AS affected_tables
FROM (
    -- CHEK-01: Negative allocations
    SELECT 'CHEK-01' AS check_id, 'allocations' AS table_name
    FROM allocations WHERE allocation_lbs < 0

    UNION ALL

    -- CHEK-02: Over-transferred
    SELECT 'CHEK-02' AS check_id, 'quota_metrics' AS table_name
    FROM quota_metrics WHERE remaining_lbs < 0

    UNION ALL

    -- CHEK-03: Future year (all tables)
    WITH current_year_cte AS (
        SELECT EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER AS current_year
    )
    SELECT 'CHEK-03' AS check_id, 'allocations' AS table_name
    FROM allocations, current_year_cte
    WHERE year > current_year_cte.current_year

    UNION ALL

    SELECT 'CHEK-03' AS check_id, 'transfers' AS table_name
    FROM transfers, (SELECT EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER AS current_year) cy
    WHERE year > cy.current_year AND NOT is_deleted

    UNION ALL

    SELECT 'CHEK-03' AS check_id, 'harvests' AS table_name
    FROM harvests, (SELECT EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER AS current_year) cy
    WHERE EXTRACT(YEAR FROM harvest_date)::INTEGER > cy.current_year AND NOT is_deleted

    UNION ALL

    -- CHEK-04: Invalid species codes
    SELECT 'CHEK-04' AS check_id, 'allocations' AS table_name
    FROM allocations
    WHERE NOT EXISTS (SELECT 1 FROM species WHERE species.code = allocations.species_code)

    UNION ALL

    SELECT 'CHEK-04' AS check_id, 'transfers' AS table_name
    FROM transfers
    WHERE NOT is_deleted
      AND NOT EXISTS (SELECT 1 FROM species WHERE species.code = transfers.species_code)

    UNION ALL

    SELECT 'CHEK-04' AS check_id, 'harvests' AS table_name
    FROM harvests
    WHERE NOT is_deleted
      AND NOT EXISTS (SELECT 1 FROM species WHERE species.code = harvests.species_code)
) all_checks
GROUP BY check_id
ORDER BY check_id;
*/
