-- =============================================================================
-- Migration: 015_add_reconciliation_view.sql
-- Purpose: Create reconciliation_variance view comparing internal quota tracking vs external eFish data
-- Date: 2026-01-29
-- =============================================================================

-- =============================================================================
-- PART 1: CREATE reconciliation_variance VIEW
-- =============================================================================

CREATE OR REPLACE VIEW reconciliation_variance
WITH (security_invoker = true)
AS
SELECT
    -- Use COALESCE to handle NULL org_id from either side of FULL OUTER JOIN
    COALESCE(qr.org_id, ef.org_id) AS org_id,
    COALESCE(qr.llp, ef.llp) AS llp,
    COALESCE(qr.species_code, ef.species_code) AS species_code,
    COALESCE(qr.year, ef.year) AS year,

    -- Source data (may be NULL if record only exists in one source)
    qr.remaining_lbs AS internal_remaining_lbs,
    ef.remaining_lbs AS external_remaining_lbs,

    -- Variance calculation: internal - external (positive = internal > external)
    COALESCE(qr.remaining_lbs, 0) - COALESCE(ef.remaining_lbs, 0) AS variance_lbs,

    -- Investigation flag: TRUE if absolute variance exceeds 100 lbs threshold
    ABS(COALESCE(qr.remaining_lbs, 0) - COALESCE(ef.remaining_lbs, 0)) > 100 AS needs_investigation

FROM quota_remaining qr
FULL OUTER JOIN efish_account_balance ef
    ON qr.org_id = ef.org_id
    AND qr.llp = ef.llp
    AND qr.species_code = ef.species_code
    AND qr.year = ef.year;

-- =============================================================================
-- PART 2: ADD DOCUMENTATION TO reconciliation_variance VIEW
-- =============================================================================

COMMENT ON VIEW reconciliation_variance IS
    'Compares internal quota tracking (quota_remaining) against external eFish account balances.

    Purpose:
    - Identify discrepancies between internal calculations and external eFish data
    - Flag rows requiring investigation when variance exceeds threshold

    Formula:
    - variance_lbs = internal_remaining_lbs - external_remaining_lbs
    - Sign convention: Positive variance = internal shows more quota than external
                       Negative variance = external shows more quota than internal

    Investigation Threshold:
    - needs_investigation = TRUE when ABS(variance_lbs) > 100
    - 100 lbs threshold chosen to ignore rounding differences while catching material discrepancies

    NULL Handling:
    - FULL OUTER JOIN ensures rows from both sources are included
    - NULL values treated as 0 in variance calculation via COALESCE
    - If record exists only in internal source: external_remaining_lbs = NULL, variance = internal value
    - If record exists only in external source: internal_remaining_lbs = NULL, variance = -external value

    RLS Compatibility:
    - Uses WITH (security_invoker = true) to inherit RLS policies from underlying views
    - Postgres 15+ feature ensures org_id filtering applies correctly through view layers';

-- =============================================================================
-- PART 3: VERIFICATION
-- =============================================================================

/*
-- Check view exists:
SELECT table_name, table_type
FROM information_schema.views
WHERE table_name = 'reconciliation_variance';

-- Sample data (rows needing investigation):
SELECT
    org_id,
    llp,
    species_code,
    year,
    internal_remaining_lbs,
    external_remaining_lbs,
    variance_lbs,
    needs_investigation
FROM reconciliation_variance
WHERE needs_investigation = TRUE
ORDER BY ABS(variance_lbs) DESC
LIMIT 10;

-- Summary statistics:
SELECT
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE needs_investigation = TRUE) AS flagged_records,
    ROUND(AVG(ABS(variance_lbs))::NUMERIC, 2) AS avg_abs_variance,
    MAX(ABS(variance_lbs)) AS max_abs_variance
FROM reconciliation_variance;
*/
