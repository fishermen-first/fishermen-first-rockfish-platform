# Codebase Concerns

**Analysis Date:** 2026-01-28

## Tech Debt

**Race Condition in Quota Transfers:**
- Issue: No database-level locking when checking and inserting transfers. Two concurrent requests can both pass the quota check, but together exceed available quota.
- Files: `app/views/transfers.py` (lines 80-100, 145-193), `tests/test_transfers.py` (line 693 - TestTransferConcurrency)
- Impact: Quota can be oversold in high-concurrency scenarios. Business logic depends on application-level validation which cannot be atomically guaranteed.
- Fix approach: Implement database-level transaction with row-level locking on `vessel_allocations`, or use a stored procedure with `SELECT ... FOR UPDATE` to lock quota during transfer insertion. Alternatively, implement event-sourcing or timestamp-based optimistic locking.
- Current state: Documented as known issue in TESTING.md line 93. Tests exist (`test_concurrent_transfers`) that confirm the limitation but explicitly do not fix it.

**Inactive Vessels Not Filtered in Dropdowns:**
- Issue: `vessels` table has `is_active` column (schema.sql line 31), but transfer and bycatch forms pull all LLPs from `coop_members` without checking vessel active status.
- Files: `app/views/transfers.py` (lines 29-32, 59-77), `app/views/bycatch_alerts.py` (lines 86-92, 777-790)
- Impact: Users can create transfers to/from inactive vessels, violating business rules and potentially creating orphaned quota.
- Fix approach: Join `coop_members.llp` with `vessels.is_active = true` in cached fetch functions. Filter dropdowns to exclude inactive vessels. Add validation in `insert_transfer()` and alert creation functions.
- Tests: `test_inactive_vessel_not_filtered_in_dropdown()` and `test_transfer_to_inactive_vessel_proceeds()` in `tests/test_transfers.py` (lines 911-935) document current behavior without blocking.

**Vessel Table Schema Mismatch:**
- Issue: `vessels.is_active` column is defined as `TEXT` (schema.sql line 31), not `BOOLEAN`. This is inconsistent with other boolean flags in the schema and may cause comparison issues.
- Files: `sql/schema.sql` (line 31), `app/views/rosters.py` (line 68) displays it as-is without conversion
- Impact: Queries checking `is_active = true` or `is_active = false` may fail to match stored values ('1'/'0' or 'true'/'false' strings).
- Fix approach: Migrate `vessels.is_active` to `BOOLEAN DEFAULT true`. Update migration script to convert existing string values.

## Known Bugs

**Stale Cache After Transfer Submission:**
- Symptoms: After submitting a transfer, quota numbers briefly show stale values on the same page, even after cache clear.
- Files: `app/views/transfers.py` (lines 54-56, 341-342)
- Trigger: Submit transfer -> cache cleared -> quota fetched from `quota_remaining` view -> view may take seconds to reflect in Supabase
- Workaround: Page refresh (`st.rerun()` on line 342) forces re-fetch. View calculation in `quota_remaining` may lag behind transaction insert.
- Root cause: `quota_remaining` view (sql/schema.sql lines 180-210) aggregates with SUM, which requires all reads to complete. In high-load scenarios, view materialization may lag.

**Exception Swallowing in Key Functions:**
- Issue: Multiple critical functions catch all exceptions generically without logging context.
- Files: `app/auth.py` (lines 115-117, 149-150 return empty dict), `app/views/transfers.py` (lines 101-103), `app/views/bycatch_alerts.py` (lines 149, 179, 233, 293, 332, 370, 415, 440, 447, 540, 633)
- Impact: Production bugs are silent. Quota calculation errors fail without alerting operators. No audit trail of failures.
- Fix approach: Implement structured logging with context (user, LLP, organization). Log all exceptions to a dedicated table or external service. Set up alerts for critical error patterns.

## Security Considerations

**Streamlit HTML Injection Risk:**
- Risk: 24 instances of `st.markdown(..., unsafe_allow_html=True)` across views without input validation.
- Files: `app/views/bycatch_alerts.py` (line 53), `app/views/dashboard.py` (styling), `app/views/report_bycatch.py` (styling)
- Current mitigation: HTML is hard-coded styling only, no user input is passed directly. Variable substitution uses formatted strings (e.g., `f"color: {NAVY}"`).
- Recommendations: (1) Use Streamlit's native styled components instead of HTML where possible. (2) If HTML is required, sanitize all variables with `markupsafe.escape()` or use f-string expressions only for literal values. (3) Document that this pattern is read-only styling, never user-generated content.

**RLS Enforcement Depends on Supabase:**
- Risk: Row-level security (RLS) policies protect data in database, but application catches all exceptions (see above) without alerting if RLS fails.
- Files: `sql/migrations/011_add_rls_security_fixes.sql`, `app/views/*` (all query functions)
- Current mitigation: RLS is enabled on all tables (migration 011). Each table has policies restricting by `org_id` or role.
- Recommendations: (1) Add RLS policy tests in CI/CD that verify isolation by role. (2) Log RLS violation attempts. (3) Add unit tests that explicitly test RLS by querying across org boundaries (will fail if RLS not working).

**Authentication Token Handling:**
- Risk: Access and refresh tokens stored in Streamlit session state, which persists in browser memory/session. No secure httpOnly cookies used.
- Files: `app/auth.py` (lines 40-41, 93-94), `app/main.py` (context)
- Current mitigation: Supabase SDK handles token refresh. Session expires on browser close.
- Recommendations: (1) Add session timeout enforcement (e.g., 30 min inactivity). (2) Add re-authentication requirement for sensitive operations (transfers, alerts). (3) Document token refresh behavior in auth module.

**User Profile Fetching Without Null Checks:**
- Risk: `get_user_profile()` in `app/auth.py` (lines 134-150) returns empty dict on failure. Calling code assumes keys exist.
- Files: `app/auth.py` (login function, lines 44-48)
- Trigger: User exists in Auth but not in user_profiles table (e.g., account creation before profile setup).
- Impact: Login succeeds but user_role, org_id, processor_code remain None. User may see broken pages instead of "account not configured" error.
- Fix approach: Raise exception or return specific error code if profile missing. Catch in login and show user-friendly message.

## Performance Bottlenecks

**Bycatch Alerts Page Load Time:**
- Problem: `bycatch_alerts.py` is 1368 lines with multiple data fetches and transformations. Largest single Python file in app.
- Files: `app/views/bycatch_alerts.py`
- Cause: (1) Multiple cached functions with varying TTLs (60s to 300s) create stale-data windows. (2) Alert list fetch + join with hauls happens on every page load even if tab not viewed. (3) Complex coordinate formatting and haul validation done upfront.
- Improvement path: (1) Use lazy loading for alert details (fetch only when expanded). (2) Move haul validation to backend stored procedure. (3) Cache haul list separately with longer TTL since hauls are immutable once saved.

**Quota Remaining View Performance:**
- Problem: `quota_remaining` view (sql/schema.sql lines 180-210) performs three LEFT JOINs with aggregations on every read.
- Files: `sql/schema.sql`, queried by `app/views/transfers.py` (line 94-96) multiple times per page load
- Cause: No materialized view or caching. Each quota check re-scans quota_transfers and harvests tables.
- Improvement path: (1) Materialize the view with periodic refresh (every 60s). (2) Add indexes on (llp, species_code, year, is_deleted). (3) Pre-calculate quota for current year on page load, cache in session.

**Dashboard Table Join Without Limits:**
- Problem: `get_quota_data()` in `dashboard.py` (lines 18-38) joins vessel_allocations with quota_remaining without pagination or limit.
- Files: `app/views/dashboard.py` (lines 18-38)
- Cause: Assumes all species x vessels x years fit in memory. No LIMIT clause.
- Impact: At scale (100+ vessels, 5+ species, 10+ years) could fetch 5000+ rows and perform cross-product operations.
- Improvement path: (1) Add LIMIT 1000 or paginate by coop_code. (2) Filter to current year by default. (3) Add user-selectable coop/species filter to reduce data.

**Cache TTL Mismatch:**
- Problem: Related data has different cache lifetimes, creating stale-data windows.
- Files: `app/views/transfers.py` (LLPs cached 300s, history 30s), `app/views/bycatch_alerts.py` (alerts 60s, species 300s)
- Cause: No coordination between cache invalidation. After a transfer, quota_remaining cache is cleared (line 56) but LLP dropdown cache (300s TTL) is not cleared.
- Impact: User sees updated quota but LLP list may still show deleted/inactive vessels for 300s.
- Fix approach: Implement cache invalidation keys or use a single cache-clear function that clears all related caches.

## Fragile Areas

**Auth State Initialization:**
- Files: `app/auth.py` (lines 17-21, 129-131)
- Why fragile: `init_session_state()` called in multiple functions (`is_authenticated()`, `get_current_user()`, `get_current_role()`, `get_user_llp()`). If called in wrong order or missing in a code path, auth state is undefined.
- Safe modification: (1) Call `init_session_state()` once in `app/main.py` before any auth checks. (2) Add assertions in critical auth functions to verify session state is initialized. (3) Make session state a class/dataclass to prevent direct access.
- Test coverage: 20 auth edge case tests exist (`test_auth.py`, lines 59-90), but they don't verify initialization order.

**Transfer Validation Logic:**
- Files: `app/views/transfers.py` (lines 296-312)
- Why fragile: Validation checks are in UI code, not enforced by database. Adding a new species or changing business rules requires updating both validation logic and RLS policies.
- Safe modification: (1) Move validation rules to database CHECK constraints. (2) Add stored procedure for transfer insertion that validates atomically. (3) Return detailed error from stored procedure so UI can display it.
- Test coverage: 83 transfer tests exist, but none validate that invalid transfers are rejected at the DB level.

**Bycatch Alert Status Transitions:**
- Files: `app/views/bycatch_alerts.py` (lines 308-370, status updates scattered)
- Why fragile: Status values ('pending', 'shared', 'resolved') are strings hardcoded in multiple places. No state machine enforces valid transitions.
- Safe modification: (1) Create enum type in database. (2) Add CHECK constraint to enforce transitions (e.g., pending->shared OR pending->resolved, not pending->resolved directly if shared). (3) Update functions to use enum in queries.

**Soft Delete with Active Flag:**
- Files: All transaction tables use `is_deleted` flag. `vessels` table uses `is_active`. Mismatch in semantics.
- Why fragile: Queries must remember to add `.eq("is_deleted", False)` or risk showing deleted data. `is_active` filtering is inconsistent.
- Safe modification: (1) Standardize on `is_deleted` flag everywhere. (2) Migrate `vessels.is_active` to `is_deleted`. (3) Create a database view that filters by is_deleted for each table. (4) Add helper function to apply soft-delete filter to all queries.

## Scaling Limits

**Database Connections:**
- Current capacity: Streamlit app creates one Supabase client per session (cached with `@st.cache_resource`). Supabase allows ~100 concurrent connections on free tier, ~1000 on pro.
- Limit: At 50+ concurrent users, connection pool exhaustion may occur.
- Scaling path: (1) Use connection pooling (Supabase PgBouncer). (2) Implement read-only replica for dashboard queries. (3) Cache frequently accessed data (LLPs, species) in Redis instead of querying DB every 30-300s.

**View Materialization:**
- Current capacity: `quota_remaining` view scans entire quota_transfers and harvests tables on every read.
- Limit: With 10,000+ transfers/harvests, view query times out (typically >30s at scale).
- Scaling path: (1) Materialize view with triggers to update on insert/delete. (2) Create daily snapshot table of quota_remaining and query snapshots + deltas. (3) Pre-aggregate by (year, org_id, species_code) and compute LLP-level details on demand.

**Session State Memory:**
- Current capacity: Each user session stores full list of LLPs, species, coops, processors in cache.
- Limit: 500+ vessels × 7 species × org members = 3500+ rows per user session.
- Scaling path: (1) Paginate roster lists in UI. (2) Move reference data to client-side IndexedDB. (3) Implement global cache (Redis) for reference data shared across users.

## Dependencies at Risk

**Streamlit Version Pinning:**
- Risk: No version constraints in requirements.txt. `streamlit run` fetches latest major version, which may introduce breaking UI changes.
- Impact: `st.cache_data` TTL parameter added in 1.18.0. If Streamlit downgrades, code breaks.
- Migration plan: Pin `streamlit>=1.25.0` in requirements.txt to ensure cache_data availability. Lock to latest stable (1.32.0) for production.

**Supabase Client Library:**
- Risk: No version pinned. Python Supabase client updates may change method signatures.
- Impact: `.select().execute()` chain signature has changed between versions. `.table()` method behavior differs.
- Migration plan: Pin `supabase>=2.0.0,<3.0.0` to lock to stable v2 API.

**PostgreSQL Window Functions:**
- Risk: `quota_remaining` view and account_balances view use ROW_NUMBER and PARTITION (lines 132-135 in migration 011). These require PostgreSQL 8.4+.
- Impact: Low risk since Supabase uses modern PostgreSQL (14+).
- Migration plan: Document minimum PostgreSQL version in README.

## Test Coverage Gaps

**RLS Policy Enforcement:**
- What's not tested: Unit tests mock Supabase and don't verify RLS actually blocks cross-org access.
- Files: `app/views/*` (all views), `tests/test_auth.py`, `tests/test_transfers.py`
- Risk: RLS policies could be misconfigured and tests still pass.
- Priority: High - Multi-tenant isolation is critical. Add integration tests that query another org and verify RLS error returned.

**Concurrent Access Patterns:**
- What's not tested: Only documented (TESTING.md line 93), not prevented. No integration test that simulates two users transferring same quota simultaneously.
- Files: `tests/test_transfers.py` (line 693)
- Risk: Data corruption in production if race condition hit.
- Priority: High - Add integration test with parallel transfers that verifies rejection on second attempt.

**Session Expiry and Token Refresh:**
- What's not tested: `refresh_session()` and `check_and_refresh_session()` are mocked in unit tests.
- Files: `tests/test_auth.py` (lines 126-140)
- Risk: Token expiry handling could fail silently, leaving users with stale tokens.
- Priority: Medium - Add e2e test that lets token expire and verifies automatic refresh or re-login prompt.

**Inactive Vessel Filtering:**
- What's not tested: No validation that inactive vessels are excluded from dropdowns.
- Files: `app/views/transfers.py`, `app/views/bycatch_alerts.py`
- Risk: Users accidentally transfer to inactive vessels, creating orphaned quota.
- Priority: Medium - Add unit test that verifies `_fetch_coop_members_for_dropdown()` returns only active vessels (or add `is_active` check to dropdown generation).

**Soft Delete Audit Trail:**
- What's not tested: No verification that `deleted_by` and `deleted_at` fields are populated on soft delete.
- Files: `app/views/bycatch_alerts.py` (lines 322, 626), transfer deletion (if implemented)
- Risk: Orphaned soft-deleted records without context, preventing audit compliance.
- Priority: Low - Add unit test for all soft-delete operations that verifies metadata fields.

**SQL Injection Prevention:**
- What's not tested: No input fuzzing or SQL injection tests, relying on Supabase SDK parameterization.
- Files: All query functions, especially with user input (notes, coordinates, etc.)
- Risk: Low if Supabase SDK is used correctly, but no automated verification.
- Priority: Low - Add test with malicious input (SQL keywords, quotes, unicode) and verify escaping.

---

*Concerns audit: 2026-01-28*
