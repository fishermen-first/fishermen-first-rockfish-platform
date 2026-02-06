# Archived Work

## v1.0 Metrics Layer (Shipped: 2026-01-29)

**Goal:** Move derived calculations into SQL views, add data quality checks, enable reconciliation.
**Result:** 18/18 requirements satisfied, 5 phases passed audit.
**Git range:** `dcbb93a` → `2a52751` (2 days)

### Phases

| # | Phase | Deliverable | Plans |
|---|-------|-------------|-------|
| 1 | Derived Metrics | `sql/migrations/013_add_quota_metrics.sql` | 1 |
| 2 | Sanity Checks | `sql/checks.sql` | 1 |
| 3 | Serving Views | `sql/migrations/014_add_serving_views.sql` | 2 |
| 4 | Reconciliation | `sql/migrations/015_add_reconciliation_view.sql` | 1 |
| 5 | Dashboard Integration | `app/views/dashboard.py` refactored | 2 |

### Key Decisions (v1.0)

- `risk_level` uses 'ok' not 'healthy' (matches Python RISK_COLORS)
- FULL OUTER JOIN for reconciliation (bi-directional discrepancies)
- 100 lbs investigation threshold (noise vs material)
- COUNT(*) FILTER for conditional aggregation (PostgreSQL 9.4+)
- Renamed remaining_pct → pct_remaining for downstream compatibility

### Tech Debt Carried Forward

- `kpi_daily_by_species`, `kpi_coop_summary` not yet consumed by UI
- `reconciliation_variance` not yet consumed by UI
- Views are non-materialized (materialize if perf degrades)

### Phase Files (archived in place)

All files in `.planning/phases/01-05/` are v1.0 artifacts:
- `*-RESEARCH.md` — pre-implementation research
- `*-PLAN.md` — execution plans
- `*-SUMMARY.md` — post-execution summaries
- `*-VERIFICATION.md` — phase verification reports

Milestone files in `.planning/milestones/`:
- `v1.0-ROADMAP.md` — phase breakdown and success criteria
- `v1.0-REQUIREMENTS.md` — 18 requirements with traceability
- `v1.0-MILESTONE-AUDIT.md` — final audit (PASSED)

---

## Bycatch Alert System (Shipped: 2026-02-05)

**Scope:** Full bycatch alerting — report form, manager review, multi-haul support, folium map.
**Feature plan:** `.planning/bycatch-hotspot-alerts.md` (archived reference)

### What shipped

- Vessel owners report bycatch via form (GPS, species, amount, haul details)
- Managers review/share/dismiss alerts
- Multi-haul support (junction table `bycatch_hauls`)
- Folium map with red pins for shared alerts on alerts page
- 61 bycatch tests + 10 E2E tests passing

### What didn't ship

- Email broadcasting — Edge Function stub exists, needs Resend API key
- Contacts management UI — vessel_contacts seeded from user_profiles only
- Plan: `.planning/email-broadcasting.md` (still pending)

### Migrations

- `007_add_bycatch_alerts.sql` — core tables + RLS
- `008_add_species_unit.sql`
- `009_add_manager_insert_alerts_policy.sql`
- `010_add_resolved_status.sql`
- `011_add_rls_security_fixes.sql`
- `012_bycatch_hauls.sql`

---

## Testing Baseline (as of 2026-02-05)

| Type | Count | Location | Run Time |
|------|-------|----------|----------|
| Unit | 362 | `tests/test_*.py` | ~29s |
| Integration | 26 | `tests/test_quota_tracking.py` | ~20s |
| E2E | 10 | `tests/e2e/` | ~80s |
| **Total** | **398** | | |

All 398 tests passing. 43 previously-skipped bycatch tests activated.

---

*Archived: 2026-02-05*
