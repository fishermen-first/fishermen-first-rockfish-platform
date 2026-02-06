# Fishermen First - Rockfish Platform

## What This Is

Multi-tenant SaaS for Alaska fishing cooperatives to track quota allocations and harvests under the Central GOA Rockfish Program. Vessel owners, managers, and admins can monitor quota remaining, execute transfers, and reconcile against external eFish data.

## Core Value

**Accurate quota tracking** — the `quota_remaining` calculation must be correct and consistent everywhere. If this breaks, cooperatives can't manage their fishing operations.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Multi-tenant organization support — v0
- ✓ Quota allocation management by LLP/species/year — v0
- ✓ Transfer tracking (in/out between vessels) — v0
- ✓ Harvest recording from eLandings API — v0
- ✓ `quota_remaining` view as single source of truth — v0
- ✓ Role-based access (admin, manager, processor, vessel_owner) — v0
- ✓ eFish reconciliation tables (account_balance, account_detail) — v0
- ✓ Bycatch alert system with multi-haul support — v0
- ✓ Soft delete pattern for transactions — v0
- ✓ Derived metrics in SQL (remaining %, risk level) — v1.0
- ✓ Sanity check queries for data quality — v1.0
- ✓ Aggregated serving views for dashboards — v1.0
- ✓ SQL-level metric documentation — v1.0
- ✓ Reconciliation view (internal vs eFish variance) — v1.0
- ✓ Dashboard consumes SQL views — v1.0

### Active

<!-- Current scope. Building toward these. -->

(None defined yet — run `/gsd:new-milestone` to plan next milestone)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- DuckDB integration — PostgreSQL handles this workload fine
- Materialized views — Premature optimization; add if performance degrades
- BI tool changes — Views are the contract; Streamlit remains a "viewer"
- New features (notifications, reporting) — Metrics layer hardening only

## Context

**Tech Stack:**
- Frontend: Streamlit
- Backend: Supabase (PostgreSQL + Auth)
- Multi-tenancy: org_id + RLS policies

**Key Business Logic:**
- LLP is the primary identifier for quota holders
- Quota Remaining = Allocation + Transfers In - Transfers Out - Harvested
- Species codes: POP=141, NR=136, Dusky=172
- Soft deletes: `is_deleted` flag on transaction tables

**Current Architecture:**
- 15 migrations shipped (013-015 added in v1.0)
- Core formula in `quota_remaining` view, extended by `quota_metrics` view
- 40+ tests covering quota edge cases
- Dashboard consumes SQL views for all derived metrics

## Constraints

- **Tech stack**: PostgreSQL only (Supabase) — no new databases
- **Backward compatibility**: Existing `quota_remaining` view must continue to work
- **Testing**: All changes must pass existing 40+ quota tests

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single `quota_remaining` view | Prevents KPI drift | ✓ Good |
| Soft deletes over hard deletes | Audit trail, recovery | ✓ Good |
| eFish as reconciliation only | Separate external data from operational | ✓ Good |
| Derived metrics in SQL views | Eliminates Python/SQL calculation drift | ✓ Good (v1.0) |
| FULL OUTER JOIN for reconciliation | Captures bi-directional discrepancies | ✓ Good (v1.0) |
| 100 lbs investigation threshold | Balances noise vs material discrepancies | ✓ Good (v1.0) |
| Use 'ok' not 'healthy' for risk_level | Matches existing Python RISK_COLORS | ✓ Good (v1.0) |

---
*Last updated: 2026-01-29 after v1.0 milestone shipped*
