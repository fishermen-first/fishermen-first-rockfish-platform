---
phase: 04-reconciliation
plan: 01
subsystem: database
tags: [postgresql, sql, views, reconciliation, variance-analysis]

# Dependency graph
requires:
  - phase: 01-derived-metrics
    provides: quota_metrics view with security_invoker pattern
  - phase: 06-create-efish-tables
    provides: efish_account_balance table schema
provides:
  - reconciliation_variance view for internal vs external quota comparison
  - Variance calculation with needs_investigation flag
  - FULL OUTER JOIN pattern for bi-directional discrepancy detection
affects: [05-ui-dashboard, reconciliation-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - FULL OUTER JOIN for reconciliation (captures both-direction discrepancies)
    - COALESCE for NULL handling in variance calculations
    - ABS() threshold for investigation flagging

key-files:
  created:
    - sql/migrations/015_add_reconciliation_view.sql
  modified: []

key-decisions:
  - "Use FULL OUTER JOIN (not LEFT JOIN) to capture discrepancies from both internal and external sources"
  - "Set 100 lbs as investigation threshold to ignore rounding while catching material discrepancies"
  - "Sign convention: variance_lbs = internal - external (positive = internal > external)"
  - "Treat NULL values as 0 in variance calculation via COALESCE"

patterns-established:
  - "Variance analysis pattern: FULL OUTER JOIN + COALESCE for NULL handling"
  - "Investigation flagging: ABS(variance) > threshold boolean column"
  - "security_invoker = true for RLS compatibility in reconciliation views"

# Metrics
duration: 2min
completed: 2026-01-29
---

# Phase 04 Plan 01: Reconciliation View Summary

**FULL OUTER JOIN view comparing internal quota_remaining against external efish_account_balance with 100 lbs investigation threshold**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-29T06:42:52Z
- **Completed:** 2026-01-29T06:44:50Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created reconciliation_variance view with FULL OUTER JOIN to capture bi-directional discrepancies
- Implemented variance calculation (internal - external) with documented sign convention
- Added needs_investigation boolean flag for ABS(variance_lbs) > 100
- Proper NULL handling via COALESCE for records existing in only one source
- RLS-compatible via security_invoker = true

## Task Commits

Each task was committed atomically:

1. **Task 1: Create reconciliation_variance view migration** - `e46e889` (feat)

**Plan metadata:** (to be committed with STATE.md update)

## Files Created/Modified
- `sql/migrations/015_add_reconciliation_view.sql` - reconciliation_variance view comparing internal quota_remaining vs external efish_account_balance

## Decisions Made

**1. FULL OUTER JOIN vs LEFT JOIN**
- Rationale: Need to detect discrepancies in both directions (records only in internal OR only in external)
- LEFT JOIN would miss records that exist only in efish_account_balance
- FULL OUTER JOIN ensures complete reconciliation coverage

**2. Investigation threshold: 100 lbs**
- Rationale: Balance between noise reduction and discrepancy detection
- Ignores rounding differences and minor variances
- Catches material discrepancies requiring investigation

**3. Sign convention: variance_lbs = internal - external**
- Positive variance: internal shows more quota than external (potential over-allocation concern)
- Negative variance: external shows more quota than internal (potential under-tracking concern)
- Documented in COMMENT ON VIEW for clarity

**4. NULL handling: COALESCE to 0**
- Records existing in only one source get treated as 0 in the other
- Example: If only in internal, external_remaining_lbs = NULL, variance = internal value
- Allows variance calculation to work for one-sided discrepancies

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 5 (UI Dashboard):**
- reconciliation_variance view available for dashboard queries
- All join keys (org_id, llp, species_code, year) use COALESCE for safe NULL handling
- needs_investigation flag ready for UI filtering/alerts
- RLS compatibility ensures multi-tenant safety

**Integration notes:**
- UI can filter WHERE needs_investigation = TRUE for action items
- Sort by ABS(variance_lbs) DESC to prioritize largest discrepancies
- Verification queries included in migration file for testing

**No blockers or concerns**

---
*Phase: 04-reconciliation*
*Completed: 2026-01-29*
