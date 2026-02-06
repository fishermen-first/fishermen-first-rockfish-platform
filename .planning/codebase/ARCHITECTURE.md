# Architecture

Multi-tenant SaaS: Streamlit frontend + Supabase backend (PostgreSQL + Auth + RLS).

## Layers

| Layer | Location | Purpose |
|-------|----------|---------|
| Presentation | `app/views/*.py` | Role-based pages, each has `show()` |
| Components | `app/components/*.py` | Reusable forms (haul_form, coordinate_input) |
| Auth/Session | `app/auth.py` | Login, JWT refresh, role checks, session state |
| Config | `app/config.py` | Supabase client, constants (CURRENT_YEAR, LBS_PER_MT) |
| Utilities | `app/utils/*.py` | Styles, formatting, coordinates, parsers, storage |
| Data Access | In each view | `@st.cache_data(ttl=X)` fetchers (private `_fetch_*`) |
| Database | Supabase PostgreSQL | Tables, views, RLS policies |

## Data Flows

- **Auth**: email/password → Supabase Auth → JWT in session_state → user_profiles for role/org
- **Quota**: view calls `_fetch_quota_remaining()` → `quota_remaining` SQL view → cached 60s
- **Transfers**: form validation → Supabase insert → cache cleared → view refreshes
- **Bycatch**: report form → `bycatch_alerts` + `bycatch_hauls` tables → manager review → share
- **Upload**: CSV/Excel → parse/validate → `account_balances_raw` / `account_detail_raw` (reconciliation only)

## Session State Keys

`authenticated`, `user`, `access_token`, `refresh_token`, `user_role`, `org_id`, `current_page`, `filter_coop`, `filter_vessel`

## Error Handling

Try-catch at data access layer → `st.error()` for user-facing → return safe defaults (0, [], None).
