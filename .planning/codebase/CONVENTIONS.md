# Coding Conventions

## Naming

- **Files**: `snake_case.py`, views in `app/views/`, utils in `app/utils/`, tests as `test_*.py`
- **Functions**: `snake_case()`, private with `_` prefix, cached fetchers use `_fetch_*`
- **Variables**: `snake_case`, constants `UPPER_CASE`
- **Types**: Python 3.10+ hints (`str | None`, `list[tuple]`), return types on all public functions

## Patterns

- **Cached fetchers**: `@st.cache_data(ttl=X)` on private `_fetch_*` functions
- **Cache clearing**: Explicit `.clear()` after mutations, autouse fixture in tests
- **Error handling**: try/except → `st.error()` → return safe default
- **Multi-tenancy**: `.eq("org_id", org_id)` on all queries
- **Soft deletes**: `is_deleted`, `deleted_by`, `deleted_at` fields
- **Auth guards**: `require_auth()` at page top, `require_role("manager")` for protected pages

## Style

- PEP 8, 4-space indent, no formatter enforced
- Imports: stdlib → third-party → local
- Docstrings on public functions (Args/Returns format)
- No barrel files — import directly from submodules

## Constants

- `app/config.py`: `CURRENT_YEAR`, `LBS_PER_MT`, Supabase client
- `app/utils/styles.py`: `NAVY = "#1e3a5f"`, `page_header()`, `section_header()`
- `app/utils/formatting.py`: `RISK_COLORS`, `format_lbs()`, `get_risk_level()`
