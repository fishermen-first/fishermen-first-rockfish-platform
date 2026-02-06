# Coding Conventions

**Analysis Date:** 2026-01-28

## Naming Patterns

**Files:**
- Lowercase with underscores: `main.py`, `formatting.py`, `bycatch_alerts.py`
- View files in `app/views/`: descriptive names like `vessel_owner_view.py`, `account_detail.py`
- Utility files in `app/utils/`: `styles.py`, `formatting.py`, `parsers.py`, `coordinates.py`, `storage.py`
- Component files in `app/components/`: `coordinate_input.py`, `haul_form.py`
- Test files use `test_` prefix: `test_auth.py`, `test_transfers.py`, `test_quota_tracking.py`

**Functions:**
- Snake_case for all functions: `get_quota_remaining()`, `_fetch_quota_remaining()`, `format_lbs()`, `get_risk_level()`
- Private/internal functions prefixed with underscore: `_fetch_transfer_history()`, `_apply_create_alert_styles()`, `_get_risk_level_for_df()`
- Cache-decorated functions commonly use `_fetch_` prefix: `_fetch_coop_members()`, `_fetch_transfer_history()`, `_fetch_llp_to_vessel_map()`

**Variables:**
- Snake_case for all variables: `llp`, `species_code`, `remaining_lbs`, `transfer_date`, `org_id`
- Constants in UPPERCASE: `NAVY = "#1e3a5f"`, `SPECIES_MAP`, `CURRENT_YEAR`, `LBS_PER_MT`, `RISK_COLORS`
- Dict-like constants map codes to values: `SPECIES_OPTIONS = {141: "POP", 136: "NR", 172: "Dusky"}`

**Types:**
- Use Python type hints in function signatures: `def get_quota_remaining(llp: str, species_code: int, year: int = CURRENT_YEAR) -> float:`
- Use type hints for return values and parameters
- Union types using `|` syntax: `def _fetch_alerts(org_id: str, status: str | None = None)` (Python 3.10+)
- List/dict types: `list[tuple[str, str]]`, `dict[str, str]`

## Code Style

**Formatting:**
- No explicit formatter (ESLint/Prettier) configured; follows PEP 8 Python conventions
- Indentation: 4 spaces
- Max line length: Not explicitly enforced but generally under 100 characters
- Imports are organized but not sorted with isort

**Linting:**
- No explicit linter configured in repository (no `.eslintrc`, `.flake8`, `pyproject.toml` linting config)
- Follows PEP 8 implicitly through team discipline

## Import Organization

**Order:**
1. Standard library imports: `import os`, `import sys`, `from pathlib import Path`, `from datetime import date, time, datetime`, `from typing import BinaryIO`
2. Third-party imports: `import streamlit as st`, `import pandas as pd`, `from dotenv import load_dotenv`, `from supabase import create_client, Client`, `from unittest.mock import MagicMock, patch`
3. Local imports: `from app.config import supabase`, `from app.auth import require_role`, `from app.utils.formatting import format_lbs`

**Path Aliases:**
- No path aliases configured (no `jsconfig.json` or `tsconfig.json` equivalent)
- Explicit relative imports: `from app.views.transfers import ...`
- Module path management via `sys.path.insert(0, str(Path(__file__).parent.parent))` in entry points like `main.py`

## Error Handling

**Patterns:**
- Try-catch blocks around database operations with user-friendly error messages:
  ```python
  try:
      response = supabase.table("quota_remaining").select(...).execute()
      if response.data and len(response.data) > 0:
          return float(response.data[0]["remaining_lbs"] or 0)
      return 0.0
  except Exception as e:
      st.error(f"Error checking quota: {e}")
      return 0.0
  ```
- Silent failures (try-except with pass) used sparingly, e.g., in logout when signout might fail:
  ```python
  try:
      supabase.auth.sign_out()
  except Exception:
      pass  # Sign out locally even if remote fails
  ```
- Streamlit error display: `st.error(f"Error message: {e}")` for user-facing errors
- Return safe defaults on error (0, empty list, False, None)

**Error Message Style:**
- User-friendly for auth: "Invalid email or password" (not raw exception)
- Descriptive for operations: "Error loading LLPs: {e}", "Error checking quota: {e}"
- Machine-friendly for debugging via print/logging

## Logging

**Framework:** `print()` statements for debugging, no structured logger (no logging module usage)

**Patterns:**
- Print statements for internal debugging (commented as such): `print(f"Filtered {unknown_count} rows with unknown species codes: {unknown_codes}")`
- No production logging framework; Streamlit displays errors via `st.error()`, `st.warning()`
- Session state used to track authentication state rather than audit logs

## Comments

**When to Comment:**
- Module-level docstrings explain purpose: `"""Quota Transfers page - transfer quota between LLPs."""`
- Comments on complex business logic: `# Species mapping for transferable species (target + secondary)`
- Inline comments for non-obvious calculations or workarounds
- TODOs or design notes in docstrings

**JSDoc/TSDoc:**
- Use Python docstrings with Args/Returns format:
  ```python
  def format_lbs(value, na_text: str = "N/A") -> str:
      """
      Format pounds as M, K, or raw number with sign handling.

      Args:
          value: Numeric value to format, or None
          na_text: Text to display for None values

      Returns:
          Formatted string (e.g., "1.5M", "250K", "500")
      """
  ```
- Brief one-liners for utility functions
- Longer docstrings for functions with business logic

## Function Design

**Size:**
- Most functions are short (10-50 lines), performing single responsibilities
- Data fetching functions cached with `@st.cache_data(ttl=...)` are typically 5-10 lines
- View rendering functions may be longer (50-150 lines) due to Streamlit widget composition

**Parameters:**
- Functions accept explicit parameters (no `**kwargs` overuse)
- Cache-decorated functions use explicit parameters for cache key generation
- Optional parameters use defaults: `year: int = CURRENT_YEAR`, `status: str | None = None`

**Return Values:**
- Single return values preferred: `-> float`, `-> str`, `-> bool`
- Complex data returned as DataFrames or dicts: `-> pd.DataFrame`, `-> list[tuple[str, str]]`
- Safe defaults on error: `return 0.0`, `return []`, `return None`

## Module Design

**Exports:**
- Explicit function exports from modules
- Private/internal functions prefixed with `_`: `_fetch_quota_remaining()`, `_apply_create_alert_styles()`
- Public API functions without prefix: `get_quota_remaining()`, `format_lbs()`, `get_risk_level()`

**Barrel Files:**
- Minimal barrel files; `app/__init__.py` and view/utils `__init__.py` are empty
- Imports are explicit from submodules: `from app.auth import login`, not `from app import login`
- Component `__init__.py` does not re-export; consumers import directly: `from app.components.haul_form import render_multi_haul_section`

## Caching Strategy

**Streamlit Caching:**
- `@st.cache_data()` used for database queries and data transformations (most common):
  - TTL varies by data volatility: `ttl=60` (1 minute) for frequently-changing data like transfer history
  - TTL `ttl=300` (5 minutes) for less volatile data like coop members
  - `ttl=30` for near-realtime data
  - `max_entries=500` used for per-item caches like `get_quota_remaining()` to avoid memory bloat

**Cache Clearing:**
- Explicit cache clearing after mutations: `_fetch_transfer_history.clear()`, `get_quota_remaining.clear()`
- Clear function defined: `clear_transfer_cache()` clears related caches after successful transfer
- `conftest.py` autofixture clears all caches before/after tests to prevent data leakage

## Type System

**Type Hints:**
- Modern Python 3.10+ union syntax: `str | None` instead of `Optional[str]`
- Generic types: `list[tuple[str, str]]`, `dict[str, float]`
- Return type hints on all public functions
- Parameter type hints on all functions

## Constants and Configuration

**Where Defined:**
- Application constants in `app/config.py`: `CURRENT_YEAR = 2026`, `LBS_PER_MT = 2204.62`
- Color constants in `app/utils/styles.py`: `NAVY = "#1e3a5f"`, `GRAY_TEXT = "#64748b"`
- Risk colors in `app/utils/formatting.py`: `RISK_COLORS = {"critical": "#dc2626", ...}`
- Species mappings in view files where used: `SPECIES_MAP = {141: 'POP', 136: 'NR', 172: 'Dusky'}`
- Options dicts in view files: `SPECIES_OPTIONS = {141: "POP (Pacific Ocean Perch)", ...}`

## Business Logic Patterns

**Quota Calculations:**
- "Remaining" always calculated from view `quota_remaining`, not in-app
- Safe null handling for allocation 0: `if row["allocation_lbs"] > 0 else None`
- Risk levels calculated as: `<10%` = critical, `10-50%` = warning, `>=50%` = ok

**Multi-Tenancy:**
- `org_id` used as isolation key in all queries: `.eq("org_id", org_id)`
- RLS policies enforce org_id isolation in Supabase
- User profile includes `org_id` fetched at login

**Date Handling:**
- Year-centric: all operations use `CURRENT_YEAR` (2026)
- Transfer dates tracked with `transfer_date` field
- Created timestamps use `created_at` from Supabase
- Timezone handling with `zoneinfo.ZoneInfo` for bycatch alerts

---

*Convention analysis: 2026-01-28*
