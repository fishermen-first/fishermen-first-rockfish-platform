---
phase: 01-derived-metrics
plan: 01
subsystem: database
tags: [postgresql, sql, views, metrics, rls]

# Dependency graph
requires:
  - phase: initial-schema
    provides: quota_remaining view with base calculation
provides:
  - quota_metrics view with remaining_pct and risk_level columns
  - SQL documentation via COMMENT ON VIEW statements
  - Safe division-by-zero handling with NULLIF
  - RLS-compatible view using security_invoker=true
affects: [02-materialized-views, 03-api-endpoints, 04-dashboard-components, 05-alerting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Derived metrics in SQL views (not Python)"
    - "NULLIF for safe division"
    - "security_invoker=true for RLS through view layers"
    - "COMMENT ON VIEW for formula documentation"

key-files:
  created:
    - sql/migrations/013_add_quota_metrics.sql
  modified: []

key-decisions:
  - "Use 'ok' not 'healthy' for risk_level to match existing Python RISK_COLORS"
  - "Check allocation_lbs = 0 FIRST in CASE to prevent division errors"
  - "Return NULL for remaining_pct when allocation is zero (not 0 or error)"

patterns-established:
  - "Risk level thresholds: critical <10%, warning <50%, ok >=50%, na for zero allocation"
  - "View-based derived metrics for consistent cross-application calculations"
  - "SQL comments document formulas and business logic"

# Metrics
duration: 2min
completed: 2026-01-28
---

# Phase 01 Plan 01: Derived Metrics Summary

**quota_metrics view with safe percentage and risk level calculations using NULLIF and security_invoker for RLS**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-29T05:16:35Z
- **Completed:** 2026-01-29T05:18:14Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Created quota_metrics view extending quota_remaining with remaining_pct and risk_level columns
- Implemented safe division-by-zero handling using NULLIF (returns NULL not error)
- Added SQL COMMENT documentation for both quota_remaining and quota_metrics views
- Ensured risk_level values match Python RISK_COLORS keys exactly ('ok' not 'healthy')
- Applied security_invoker=true for RLS policy inheritance through view layers

## Task Commits

Each task was committed atomically:

1. **Task 1: Create quota_metrics migration** - `dcbb93a` (feat)
2. **Task 2: Validate migration SQL syntax** - (validation only, no files changed)

## Files Created/Modified
- `sql/migrations/013_add_quota_metrics.sql` - Migration creating quota_metrics view with derived percentage and risk level columns, plus COMMENT documentation for both quota_remaining and quota_metrics views

## Decisions Made

**1. Use 'ok' not 'healthy' for risk_level**
- Rationale: Must match existing Python code in app/utils/formatting.py RISK_COLORS keys exactly
- Impact: Ensures consistency when queries mix SQL and Python risk level calculations

**2. Check allocation_lbs = 0 FIRST in CASE expression**
- Rationale: Prevents division by zero errors before attempting percentage calculation
- Impact: Returns 'na' for zero-allocation rows without database errors

**3. Return NULL for remaining_pct when allocation is zero**
- Rationale: NULL represents "not applicable" more accurately than 0 or error
- Impact: Client code can distinguish between "0% remaining" (quota exhausted) and "N/A" (no quota allocated)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

This migration must be applied to the database via Supabase dashboard or CLI before the view can be queried.

## Next Phase Readiness

**Ready for Phase 02 (Materialized Views):**
- quota_metrics view provides the derived columns needed for materialization
- Formula documentation in SQL ensures future maintainers understand calculations
- RLS compatibility (security_invoker) enables secure multi-tenant access patterns

**No blockers.**

**Next steps:**
- Apply migration 013 to database
- Verify queries against quota_metrics return expected remaining_pct and risk_level
- Consider adding indexes on allocation_lbs or remaining_pct if performance issues arise (unlikely with view-only queries)

---
*Phase: 01-derived-metrics*
*Completed: 2026-01-28*
