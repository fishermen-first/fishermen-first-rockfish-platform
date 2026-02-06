---
phase: 03-serving-views
plan: 01
subsystem: database
tags: [postgres, views, aggregation, dashboard-kpis, multi-tenant, rls]

# Dependency graph
requires:
  - phase: 01-derived-metrics
    provides: "quota_metrics view pattern with security_invoker for RLS"
  - phase: 02-sanity-checks
    provides: "NOT is_deleted filter pattern for harvest queries"
provides:
  - "kpi_daily_by_species view for pre-aggregated daily harvest totals"
  - "Pattern for serving views with security_invoker RLS inheritance"
affects: [04-dashboard-ui, 05-alerting, future-kpi-views]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Serving views with security_invoker = true for dashboard performance"
    - "DATE_TRUNC for daily aggregation in time-series views"

key-files:
  created:
    - "sql/migrations/014_add_serving_views.sql"
  modified: []

key-decisions:
  - "Use DATE_TRUNC('day', landing_date) for daily aggregation vs application-layer grouping"
  - "Include harvest_count in view for observability (number of records aggregated)"
  - "Filter NULL landing_date implicitly via DATE_TRUNC (no explicit IS NOT NULL needed)"

patterns-established:
  - "Serving views: Pre-aggregate expensive GROUP BY calculations at database layer"
  - "RLS inheritance: Use security_invoker = true to inherit policies from base tables"
  - "Multi-tenant grouping: Always include org_id in GROUP BY for tenant-specific aggregations"

# Metrics
duration: 1min
completed: 2026-01-29
---

# Phase 03 Plan 01: Serving Views Summary

**Pre-aggregated daily harvest KPIs view with RLS inheritance for dashboard time-series charts**

## Performance

- **Duration:** 1 min
- **Started:** 2026-01-29T06:12:23Z
- **Completed:** 2026-01-29T06:13:53Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created kpi_daily_by_species view aggregating harvests by day and species
- Established serving view pattern with security_invoker for RLS compatibility
- Pre-computation moves expensive GROUP BY from application layer to database

## Task Commits

Each task was committed atomically:

1. **Task 1: Create kpi_daily_by_species view in migration file** - `f7ecd0a` (feat)

## Files Created/Modified
- `sql/migrations/014_add_serving_views.sql` - Migration creating kpi_daily_by_species view with daily harvest aggregation by species

## Decisions Made

**1. Use DATE_TRUNC('day', landing_date) for daily aggregation**
- Rationale: Database-native date truncation more efficient than application-layer grouping
- Alternative: GROUP BY landing_date would fail if landing_date included time component (future-proofing)

**2. Include harvest_count column in view**
- Rationale: Provides observability - can distinguish "10 lbs from 1 record" vs "10 lbs from 10 records"
- Use case: Data quality monitoring and anomaly detection

**3. Filter NULL landing_date implicitly via DATE_TRUNC**
- Rationale: DATE_TRUNC returns NULL for NULL input, which is excluded by GROUP BY
- Alternative: Explicit `WHERE landing_date IS NOT NULL` would be redundant

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 04 (Dashboard UI):**
- kpi_daily_by_species view provides pre-aggregated data for time-series charts
- View includes org_id for multi-tenant filtering via RLS
- View tested structurally (columns, filters, grouping verified)

**Database deployment required:**
- Migration 014_add_serving_views.sql must be applied to Supabase before dashboard can query view
- No breaking changes - pure additive migration

**No blockers or concerns.**

---
*Phase: 03-serving-views*
*Completed: 2026-01-29*
