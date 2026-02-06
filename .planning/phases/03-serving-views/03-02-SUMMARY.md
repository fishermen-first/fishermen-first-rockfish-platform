---
phase: 03-serving-views
plan: 02
subsystem: database
tags: [postgresql, views, aggregation, kpi, risk-metrics, cooperatives]

# Dependency graph
requires:
  - phase: 03-01
    provides: kpi_daily_by_species view for time-series charts
  - phase: 01-derived-metrics
    provides: quota_metrics view with risk_level column
provides:
  - kpi_coop_summary view aggregating quota_metrics by cooperative/species/year
  - Risk level counts (critical, warning, ok, na) per cooperative
  - Vessel counts per cooperative/species/year
  - Cooperative-level quota totals (allocation, transfers, harvested, remaining)
affects: [04-dashboards, 05-reports]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "COUNT FILTER aggregation for conditional counts in PostgreSQL"
    - "Multi-table JOIN with org_id for multi-tenant safety"
    - "NULLIF for safe division in percentage calculations"

key-files:
  created: []
  modified:
    - sql/migrations/014_add_serving_views.sql

key-decisions:
  - "Use COUNT(*) FILTER (WHERE ...) for conditional aggregation (PostgreSQL 9.4+ syntax)"
  - "Join to coop_members table - aligns with current production schema"
  - "Include org_id in JOIN condition for multi-tenant safety"

patterns-established:
  - "Conditional aggregation: COUNT(*) FILTER (WHERE condition) for risk level counts"
  - "Safe division: ROUND((SUM(x) / NULLIF(SUM(y), 0) * 100)::NUMERIC, 2)"
  - "security_invoker = true on all views for RLS compatibility"

# Metrics
duration: 2min
completed: 2026-01-29
---

# Phase 3 Plan 2: Serving Views - KPI Coop Summary

**Cooperative-level quota aggregation view with risk level counts using COUNT FILTER for dashboard KPI cards**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-29T06:16:56Z
- **Completed:** 2026-01-29T06:18:40Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created kpi_coop_summary view aggregating quota_metrics by coop_code, species, year
- Implemented risk level counts (critical, warning, ok, na) using COUNT FILTER syntax
- Added comprehensive documentation with column descriptions and use cases
- Ensured multi-tenant safety with org_id in JOIN condition

## Task Commits

Each task was committed atomically:

1. **Task 1: Add kpi_coop_summary view to migration file** - `d3bedb0` (feat)

## Files Created/Modified
- `sql/migrations/014_add_serving_views.sql` - Added kpi_coop_summary view with 15 columns including risk level counts

## Decisions Made

**1. Use COUNT FILTER for conditional aggregation**
- Rationale: PostgreSQL 9.4+ native syntax, more efficient than CASE-based aggregation
- Pattern: `COUNT(*) FILTER (WHERE qm.risk_level = 'critical')`
- Cleaner than: `SUM(CASE WHEN qm.risk_level = 'critical' THEN 1 ELSE 0 END)`

**2. Join to coop_members table**
- Rationale: Aligns with current production schema (coop_members is v1, llps is v2 not yet deployed)
- JOIN condition: `qm.llp = cm.llp AND qm.org_id = cm.org_id`
- Multi-tenant safe with org_id in JOIN

**3. Include org_id in JOIN condition**
- Rationale: Defensive multi-tenant safety even though llp is globally unique
- Pattern follows best practice for all multi-tenant JOINs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 4 (Dashboards):**
- kpi_coop_summary provides risk level counts for dashboard KPI cards
- View returns critical_count, warning_count, ok_count, na_count per coop/species/year
- Example use case: "Show '3 vessels critical, 2 warning, 5 ok' for POP in Coop A"

**Ready for Phase 5 (Reports):**
- Cooperative-level aggregations ready for manager reports
- Includes vessel_count for "X vessels in this coop/species"
- Percentage calculations handled at database layer (remaining_pct)

**No blockers or concerns.**

---
*Phase: 03-serving-views*
*Completed: 2026-01-29*
