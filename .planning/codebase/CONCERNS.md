# Codebase Concerns

## Tech Debt

1. **Transfer race condition** — No DB-level locking. Two concurrent transfers can both pass quota check. Fix: `SELECT ... FOR UPDATE` or stored procedure. (`transfers.py:80-100`)

2. **Inactive vessels in dropdowns** — `coop_members` query doesn't filter by `vessels.is_active`. Fix: Join with `is_active = true`. (`transfers.py:29-32`, `bycatch_alerts.py:86-92`)

3. **vessels.is_active is TEXT not BOOLEAN** — Schema mismatch. Fix: Migration to convert. (`schema.sql:31`)

4. **Exception swallowing** — Multiple functions catch all exceptions without logging context. No structured logging. (`auth.py:115-117`, `bycatch_alerts.py` multiple locations)

5. **bycatch_alerts.py is 1368 lines** — Largest file. Consider splitting or lazy-loading haul details.

## Security Notes

- 24 instances of `unsafe_allow_html=True` — all hard-coded styling, no user input. OK for now.
- RLS enabled on all tables (migration 011) but no automated RLS isolation tests.
- JWT tokens in session_state (browser memory), no httpOnly cookies.

## Test Coverage Gaps

- RLS policy enforcement (unit tests mock Supabase, don't verify isolation)
- Concurrent transfer rejection
- Session expiry/token refresh (mocked, not tested end-to-end)
- Inactive vessel filtering
- Soft delete audit trail (deleted_by, deleted_at populated)

## Scaling Limits

- ~100 concurrent connections on free Supabase tier
- `quota_remaining` view scans full tables (materialize if >10K transactions)
- No pagination on dashboard queries
