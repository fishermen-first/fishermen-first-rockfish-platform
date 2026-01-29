-- =============================================================================
-- Migration: 013_add_quota_metrics.sql
-- Purpose: Create quota_metrics view with derived percentage and risk level columns
-- Date: 2026-01-28
-- =============================================================================

-- =============================================================================
-- PART 1: ADD DOCUMENTATION TO EXISTING quota_remaining VIEW
-- =============================================================================

COMMENT ON VIEW quota_remaining IS
    'Calculates remaining quota for each LLP/species/year combination.

    Formula: remaining_lbs = allocation_lbs + transfers_in - transfers_out - harvested

    Assumptions:
    - All amounts are in pounds (lbs)
    - Transactions with is_deleted = true are excluded from all calculations
    - Harvests are sourced exclusively from eLandings API
    - Transfers use to_llp for incoming and from_llp for outgoing
    - COALESCE ensures NULL values are treated as 0 in calculations';

-- =============================================================================
-- PART 2: CREATE quota_metrics VIEW
-- =============================================================================

CREATE OR REPLACE VIEW quota_metrics
WITH (security_invoker = true)
AS
SELECT
    qr.*,
    -- Percentage remaining (NULL if allocation is zero to avoid division by zero)
    ROUND((qr.remaining_lbs / NULLIF(qr.allocation_lbs, 0) * 100)::NUMERIC, 2) AS remaining_pct,
    -- Risk level based on percentage thresholds
    CASE
        WHEN qr.allocation_lbs = 0 THEN 'na'
        WHEN qr.remaining_lbs / NULLIF(qr.allocation_lbs, 0) * 100 < 10 THEN 'critical'
        WHEN qr.remaining_lbs / NULLIF(qr.allocation_lbs, 0) * 100 < 50 THEN 'warning'
        ELSE 'ok'
    END AS risk_level
FROM quota_remaining qr;

-- =============================================================================
-- PART 3: ADD DOCUMENTATION TO quota_metrics VIEW
-- =============================================================================

COMMENT ON VIEW quota_metrics IS
    'Extends quota_remaining with derived metrics for quota tracking and alerting.

    Formulas:
    - remaining_pct = ROUND((remaining_lbs / allocation_lbs * 100), 2)
      Returns NULL if allocation_lbs is 0 (avoids division by zero)

    - risk_level = CASE-based categorization:
      * "na" (not applicable): allocation_lbs = 0 (no quota allocated)
      * "critical": remaining_pct < 10% (immediate attention required)
      * "warning": remaining_pct < 50% (monitor closely)
      * "ok": remaining_pct >= 50% (healthy status)

    Risk level values match app/utils/formatting.py RISK_COLORS keys.

    RLS Compatibility:
    - Uses WITH (security_invoker = true) to inherit RLS policies from underlying quota_remaining view
    - Postgres 15+ feature ensures org_id filtering applies correctly through view layers';
