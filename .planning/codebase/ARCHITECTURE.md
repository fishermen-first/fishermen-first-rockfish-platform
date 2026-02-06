# Architecture

**Analysis Date:** 2026-01-28

## Pattern Overview

**Overall:** Multi-tenant SaaS with Streamlit frontend and Supabase backend using role-based access control (RBAC). The application implements a quota-tracking system for Alaska rockfish cooperatives using organization isolation and PostgreSQL row-level security (RLS).

**Key Characteristics:**
- **Frontend-centric:** Streamlit UI handles authentication, authorization, and all data presentation
- **Backend as a service:** Supabase manages PostgreSQL database, authentication, and RLS policies
- **Multi-tenancy:** Enforced via `org_id` in user_profiles and RLS policies on tenant-specific tables
- **Session-based state:** Streamlit session_state carries authentication context and filter selections
- **Cached data patterns:** Extensive use of `@st.cache_data` with TTL for database queries

## Layers

**Presentation Layer (Views):**
- Purpose: Render user-specific pages with role-based content
- Location: `app/views/*.py` (dashboard.py, transfers.py, bycatch_alerts.py, etc.)
- Contains: Page components that call utilities and data fetchers
- Depends on: `app.auth`, `app.config`, `app.utils`, Streamlit
- Used by: `app/main.py` (router)

**Component Layer (Reusable UI):**
- Purpose: Self-contained UI widgets and form sections
- Location: `app/components/*.py` (haul_form.py, coordinate_input.py)
- Contains: Complex input forms, coordinate entry, multi-haul capture
- Depends on: Streamlit, `app.utils.coordinates`
- Used by: Views (bycatch_alerts.py, report_bycatch.py)

**Authentication & Session Layer:**
- Purpose: Manage user identity, roles, and session lifecycle
- Location: `app/auth.py`
- Contains: Login/logout, session refresh, role checking, JWT handling
- Depends on: Supabase Auth, Streamlit session_state
- Used by: `app/main.py`, protected pages via `require_auth()` and `require_role()`

**Configuration & Client Layer:**
- Purpose: Initialize external dependencies and define constants
- Location: `app/config.py`
- Contains: Supabase client (cached), environment variables, application constants (CURRENT_YEAR, LBS_PER_MT)
- Depends on: python-dotenv, supabase-py
- Used by: All layers

**Utilities Layer:**
- Purpose: Shared functions across the application
- Location: `app/utils/*.py`
  - `styles.py`: Branding constants and CSS injection for consistent UI
  - `formatting.py`: Number formatting (lbs→M/K notation), risk level calculation
  - `coordinates.py`: DMS ↔ decimal coordinate conversion
  - `parsers.py`: CSV/Excel parsing and validation
  - `storage.py`: File operations
- Depends on: Streamlit, pandas
- Used by: Views, components, upload handling

**Data Access (Cached Fetchers):**
- Purpose: Abstract database queries with caching
- Location: In each view module (e.g., `_fetch_quota_remaining()`, `_fetch_transfers()`)
- Pattern: Decorated with `@st.cache_data(ttl=X)` for automatic invalidation
- Depends on: Supabase client from `app.config`
- Used by: Views for data retrieval

**Database Layer:**
- Purpose: Store application data and compute derived values
- Location: Supabase PostgreSQL with tables and views
- Contains: Reference tables, transaction tables, raw upload tables, materialized views
- RLS Policies: Enforce org_id isolation on sensitive tables
- Used by: All data access functions via Supabase client

## Data Flow

**Authentication Flow:**

1. User submits email/password in login form (`show_login()`)
2. `login()` calls `supabase.auth.sign_in_with_password()`
3. On success, JWT tokens stored in session_state
4. `get_user_profile()` fetches role, org_id, processor_code from `user_profiles` table
5. Session state populated with authentication context
6. User routed to role-appropriate sidebar/pages

**Quota Calculation Flow:**

1. View requests quota data via cached fetcher (e.g., `_fetch_quota_remaining()`)
2. Database query hits `quota_remaining` view (SQL)
3. View definition calculates: `allocation + transfers_in - transfers_out - harvested = remaining_lbs`
4. View response cached in Streamlit for 60s
5. Pandas manipulates cached data (pivoting, filtering, formatting)
6. Dashboard displays formatted results with risk colors based on `%remaining`

**Transfer Creation Flow:**

1. Manager fills transfer form (from_llp, to_llp, species, pounds, date)
2. Form validation checks against available quota
3. Submit calls Supabase insert on `quota_transfers` table
4. RLS policies verify org_id context
5. Trigger updates `quota_remaining` view (reads from base tables)
6. Cache cleared via `clear_transfer_cache()` to force fresh data
7. Dashboard re-fetches and displays updated quota immediately

**Bycatch Alert Flow:**

1. Vessel owner or manager submits bycatch data via `report_bycatch.py` or `bycatch_alerts.py`
2. Multi-haul form captures set/retrieval times, coordinates (DMS), catch details
3. Coordinates converted to decimal via `dms_to_decimal()` and stored
4. Alert inserted into `bycatch_alerts` table with org_id and status
5. Haul details stored in `bycatch_hauls` junction table (multi-haul support)
6. Alert appears in manager's `bycatch_alerts` view (status=pending)
7. Manager reviews and marks resolved, triggering shared notification

**Upload/Reconciliation Flow:**

1. Manager uploads CSV (Account Balance) or Excel (Account Detail) file
2. `upload.py` validates column names, detects duplicates
3. Parsed data stored in `account_balances_raw` or `account_detail_raw` tables
4. View definitions denormalize and aggregate by coop/species
5. Data used for reconciliation (not quota calculation)
6. Latest records displayed in `account_balances` and `account_detail` views

**State Management:**

- **Authentication state:** `st.session_state["authenticated"]`, `.user`, `.access_token`, `.user_role`, `.org_id`
- **Page navigation:** `st.session_state["current_page"]` (set by sidebar buttons)
- **Filters (dashboard):** `st.session_state["filter_coop"]`, `.filter_vessel` (scoped to dashboard page)
- **Form data:** Inline Streamlit widgets with `key=` parameters maintain state between reruns
- **Transient data:** Cached fetchers store query results with TTL, cleared on data mutations

## Key Abstractions

**Quota Remaining View:**
- Purpose: Single source of truth for quota calculations
- Examples: `sql/schema.sql` lines 180-205
- Pattern: Outer join of vessel_allocations with aggregations from quota_transfers and harvests
- Why: Centralizes quota math, prevents client-side calculation errors

**Account Balances View:**
- Purpose: Reconciliation data aggregation from eFish CSV uploads
- Examples: `sql/schema.sql` lines 208-249
- Pattern: Ranked window function to get latest balance per account/species
- Why: Deduplicates overlapping uploads, provides audit trail with created_at

**Cached Fetchers:**
- Purpose: Hide database queries, enable transparent caching
- Examples: `app/views/dashboard.py` lines 11-23, `app/views/transfers.py` lines 35-40
- Pattern: `@st.cache_data(ttl=X)` decorator on private functions returning raw data
- Why: Reduces Supabase calls, improves responsiveness, clear invalidation points

**Reusable Components:**
- Purpose: Eliminate duplicate UI code and business logic
- Examples: `app/components/coordinate_input.py` (DMS/decimal toggle), `haul_form.py` (multi-haul capture)
- Pattern: Parameterized functions that render Streamlit widgets and return structured data
- Why: Consistent coordinate handling across bycatch forms, reduces maintenance burden

## Entry Points

**Web Application:**
- Location: `app/main.py`
- Triggers: Streamlit CLI (`streamlit run app/main.py`)
- Responsibilities:
  - Initialize session state
  - Show login or sidebar+page router based on auth status
  - Manage page navigation and sidebar UI

**Page Views (Dynamic Imports):**
- Location: `app/views/*.py`
- Triggers: User clicks sidebar button (sets `st.session_state["current_page"]`)
- Pattern: `importlib.import_module()` loads view module, calls `module.show()`
- Responsibilities: Render page-specific content, fetch/display data, handle user actions

**Supabase Functions:**
- Location: `supabase/functions/send-bycatch-alert/` (Deno/TypeScript)
- Triggers: Webhook from `bycatch_alerts` table changes or RPC calls
- Responsibilities: Send email notifications for shared bycatch alerts

## Error Handling

**Strategy:** Try-catch at data access layer, user-facing error messages via `st.error()`

**Patterns:**
- **Auth errors:** `login()` returns `(bool, message)` tuple with human-readable error
- **JWT expiration:** `handle_jwt_error()` detects JWT errors, attempts refresh, forces logout if failed
- **Database errors:** Cached fetchers return empty list/dict on exception (fail-safe to empty state)
- **Upload validation:** `detect_balance_duplicates()` and `detect_detail_duplicates()` return validation results before insert
- **Missing data:** Views check for empty response and show `st.info()` message instead of crashing

## Cross-Cutting Concerns

**Logging:** Inline `print()` statements in views for debugging (e.g., filtered species codes in `dashboard.py`). No centralized logger.

**Validation:**
- CSV headers mapped and checked before parsing (`app/views/upload.py`)
- Coordinates validated via min/max bounds in component inputs
- Transfers validated against available quota before insert
- Haul data validated via `validate_haul_data()` in components

**Authentication:**
- All pages call `require_auth()` at top to redirect unauthenticated users
- Role checks via `require_role()` or role-based sidebar filtering
- RLS policies on database enforce org_id isolation (second layer of security)
- JWT refresh attempted on each request via `check_and_refresh_session()`

**Styling:**
- Global CSS injected via `apply_page_styling()` (called in each page)
- Brand colors defined in `app/utils/styles.py` (NAVY=#1e3a5f)
- Page headers and section headers use consistent functions from styles module
- Responsive layout via Streamlit columns and containers

---

*Architecture analysis: 2026-01-28*
