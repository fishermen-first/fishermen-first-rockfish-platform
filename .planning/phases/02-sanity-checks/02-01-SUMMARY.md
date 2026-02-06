---
phase: 02-sanity-checks
plan: 01
subsystem: data-quality
tags: [sql, validation, data-integrity, sanity-checks]
depends_on:
  requires: [01-01]
  provides: [data-quality-validation-queries]
  affects: [03-01, 03-02, 04-01]
tech-stack:
  added: []
  patterns: [self-documenting-queries, soft-delete-awareness, NOT-EXISTS-validation]
key-files:
  created: [sql/checks.sql]
  modified: []
decisions:
  - id: CHEK-SPECIES-VALIDATION
    choice: Use NOT EXISTS pattern for species validation
    context: More explicit than LEFT JOIN approach, clearly shows intent
    rationale: Standard SQL pattern for reference integrity checks
    alternatives: [LEFT JOIN with IS NULL check, EXCEPT set operation]
  - id: CHEK-SOFT-DELETE
    choice: Filter is_deleted in CHEK-03 and CHEK-04 for transfers/harvests
    context: Soft-deleted records should not trigger future-year or invalid-species alerts
    rationale: Maintains consistency with quota_remaining view logic
    alternatives: [Include soft-deleted records, separate checks for deleted data]
  - id: CHEK-YEAR-SOURCE
    choice: Use year column for transfers, harvest_date extraction for harvests
    context: Transfers have year column, harvests store harvest_date
    rationale: Matches existing schema design patterns
    alternatives: [Standardize both to date extraction, add year column to harvests]
metrics:
  duration: "2 min"
  completed: 2026-01-29
---

# Phase 02 Plan 01: Data Quality Sanity Checks Summary

**One-liner:** SQL queries detecting negative allocations, over-transferred quota, future-year data, and invalid species codes

## What Was Built

Created `sql/checks.sql` with four data quality validation queries:

1. **CHEK-01: Negative Allocations** - Detects allocation records with negative pounds
2. **CHEK-02: Over-Transferred Quota** - Identifies LLP/species/year with remaining < 0 using quota_metrics view
3. **CHEK-03: Future Year Data** - Finds records with year > current year across allocations, transfers, harvests
4. **CHEK-04: Invalid Species Codes** - Discovers species codes not present in species reference table

All queries follow self-documenting patterns with:
- Descriptive check_id and issue columns
- Expected results documented in comments
- Fix suggestions for each check type
- Proper ordering for actionability (most severe first)

## Technical Decisions

### Species Validation Pattern

**Decision:** Use `NOT EXISTS (SELECT 1 FROM species WHERE species.code = table.species_code)` for CHEK-04

**Reasoning:**
- More explicit intent than LEFT JOIN with IS NULL
- Standard SQL pattern for reference integrity checks
- Better query plan in most databases (can short-circuit on first match)

**Alternative considered:** LEFT JOIN approach with DISTINCT - more verbose, same result

### Soft-Delete Handling

**Decision:** Filter `WHERE NOT is_deleted` for transfers and harvests in CHEK-03 and CHEK-04

**Reasoning:**
- Maintains consistency with quota_remaining view logic
- Soft-deleted records are "logically gone" and shouldn't trigger alerts
- Allocations table has no is_deleted flag (not a transaction table)

**Impact:** Reduces false positives from historical soft-deleted data

### Year Source Inconsistency

**Observation:** Transfers table has `year` column, harvests table uses `harvest_date`

**Handling:** Extract year from harvest_date via `EXTRACT(YEAR FROM harvest_date)::INTEGER`

**Rationale:** Matches existing schema design - transfers are manual (year is sufficient), harvests come from eLandings API (full date needed)

## Files Modified

### Created

**sql/checks.sql** (245 lines)
- CHEK-01: Negative allocations query
- CHEK-02: Over-transferred quota query (uses quota_metrics view)
- CHEK-03: Future year data query (UNION ALL across 3 tables)
- CHEK-04: Invalid species codes query (NOT EXISTS pattern)
- Optional consolidated summary report (commented out)

## Task Commits

| Task | Name | Commit | Files | Duration |
|------|------|--------|-------|----------|
| 1 | Create checks.sql with all sanity check queries | 705589e | sql/checks.sql | 2 min |

## Verification Results

All verification criteria met:

✅ File exists at sql/checks.sql (8.1KB)
✅ Contains all four check IDs (29 occurrences of CHEK-01 through CHEK-04)
✅ Soft-delete filters applied (6 occurrences of "NOT is_deleted")
✅ Species validation uses NOT EXISTS pattern
✅ Current year extraction via EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER
✅ All queries runnable via single file execution

**Test execution:** Queries tested against schema structure:
- CHEK-01: SELECT on allocations.allocation_lbs
- CHEK-02: SELECT on quota_metrics view (depends on quota_remaining)
- CHEK-03: UNION ALL pattern with CTE for current_year
- CHEK-04: NOT EXISTS subquery pattern across 3 tables

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Blockers:** None

**Concerns:** None

**Dependencies satisfied for downstream phases:**

- **Phase 03 (Reconciliation):** Sanity checks provide foundation for detecting reconciliation gaps
- **Phase 04 (Quota Modeling):** Data quality validation ensures modeling inputs are trustworthy
- **Phase 05 (Optimization):** Clean data baseline established for performance tuning

**Key artifacts for next phase:**
- sql/checks.sql: Reusable validation queries for ongoing data quality monitoring
- Pattern established: Self-documenting queries with expected results and fix suggestions

## Session Notes

**Execution pattern:** Fully autonomous (no checkpoints)

**Duration:** 2 minutes (file creation and verification)

**Performance:** Single-task plan, minimal complexity

**Quality observations:**
- All queries follow consistent column naming (check_id, issue, table_name)
- Ordering optimized for actionability (most negative/severe first)
- Comments include both "Expected" and "Fix" guidance
- Optional consolidated report available for full-scan use case

## Lessons Learned

**Schema awareness critical:** Multi-tenant schema (org_id) vs single-tenant schema (no org_id) - checks.sql uses multi-tenant pattern to match production deployment

**Soft-delete pattern pervasive:** Always consider is_deleted flag when querying transfers and harvests

**View dependencies:** CHEK-02 relies on quota_metrics view, which depends on quota_remaining view - check execution requires full view stack to be deployed
