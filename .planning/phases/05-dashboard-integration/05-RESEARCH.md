# Phase 5: Dashboard Integration - Research

**Researched:** 2026-01-28
**Domain:** Streamlit + PostgreSQL view integration and visual regression testing
**Confidence:** HIGH

## Summary

This phase migrates the dashboard from Python-based quota calculations to consuming the `quota_metrics` SQL view created in Phase 1. The current dashboard implementation (app/views/dashboard.py) calculates `pct_remaining` in Pandas and applies risk level logic in Python. Phase 5 replaces these calculations by directly consuming the view's `remaining_pct` and `risk_level` columns.

The technical challenge is ensuring **zero user-visible changes** while refactoring the data source. This requires careful testing of the calculation equivalence and visual regression validation.

**Primary recommendation:** Use pandas.testing.assert_frame_equal() for calculation equivalence verification and existing pytest unit tests for regression coverage. Avoid heavyweight visual regression tools (SeleniumBase) in favor of dataframe comparison and functional tests.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.x | DataFrame operations | De facto standard for tabular data in Python, already in use |
| pytest | 7.x+ | Test framework | Project standard, existing 270 tests use it |
| pandas.testing | (pandas) | DataFrame comparison | Built-in module specifically for testing DataFrame equality |
| streamlit | 1.28+ | App framework | Already in use, provides st.cache_data for database queries |
| psycopg2-binary | 2.9+ | PostgreSQL adapter | Standard Postgres driver for Python |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unittest.mock | (stdlib) | Mock Supabase calls | Unit tests - already used in test_dashboard.py |
| pytest-mock | 3.x+ | Mock fixtures | Optional convenience wrapper over unittest.mock |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pandas.testing | DeepDiff, pytest-compare | More complex APIs, unnecessary for simple DataFrame comparison |
| Unit tests | SeleniumBase visual tests | Playwright already used for E2E, SeleniumBase adds dependency bloat |
| pytest | unittest | pytest already project standard with 270 existing tests |

**Installation:**
```bash
# All dependencies already installed
# No new packages required for Phase 5
```

## Architecture Patterns

### Recommended Refactoring Structure

The dashboard migration follows a **progressive enhancement** pattern:

```
Before (Python calculation):
  fetch quota_remaining → join coop_members → calculate pct_remaining → apply get_risk_level()

After (View consumption):
  fetch quota_metrics → join coop_members → use remaining_pct/risk_level directly
```

### Pattern 1: View-First Data Fetching
**What:** Replace quota_remaining table query with quota_metrics view query
**When to use:** When transitioning from app-layer calculations to database-layer computations

**Example:**
```python
# OLD: app/views/dashboard.py lines 12-15
@st.cache_data(ttl=60)
def _fetch_quota_remaining(year: int):
    """Cached: Fetch raw quota_remaining data from database."""
    response = supabase.table("quota_remaining").select("*").eq("year", year).execute()
    return response.data if response.data else []

# NEW: Replace table name, add remaining_pct and risk_level
@st.cache_data(ttl=60)
def _fetch_quota_metrics(year: int):
    """Cached: Fetch quota_metrics (with derived % and risk level) from database."""
    response = supabase.table("quota_metrics").select("*").eq("year", year).execute()
    return response.data if response.data else []
```

### Pattern 2: Eliminate Redundant Calculations
**What:** Remove Python code that duplicates SQL view logic
**When to use:** After migrating to quota_metrics, remove pct_remaining calculation

**Example:**
```python
# DELETE: Lines 54-58 of dashboard.py
# This calculation now happens in SQL
df["pct_remaining"] = df.apply(
    lambda row: (row["remaining_lbs"] / row["allocation_lbs"] * 100)
    if row["allocation_lbs"] > 0 else None,
    axis=1
)

# REPLACE WITH: Rename column from view
df = df.rename(columns={"remaining_pct": "pct_remaining"})
```

### Pattern 3: Risk Level from View
**What:** Use risk_level from view instead of calling get_risk_level()
**When to use:** For add_risk_flags() function

**Example:**
```python
# OLD: app/views/dashboard.py lines 88-105
def add_risk_flags(df):
    """Add risk flags for each species and overall vessel risk"""
    for species in ["POP", "NR", "Dusky"]:
        col = f"{species}_pct_remaining"
        if col in df.columns:
            df[f"{species}_risk"] = df[col].apply(_get_risk_level_for_df)

# NEW: Use risk_level from quota_metrics view
def add_risk_flags(df):
    """Add risk flags for each species and overall vessel risk"""
    for species in ["POP", "NR", "Dusky"]:
        risk_col_from_view = f"{species}_risk_level"  # Assuming pivot creates this
        if risk_col_from_view in df.columns:
            df[f"{species}_risk"] = df[risk_col_from_view]
```

**CRITICAL:** The exact implementation depends on how pivot_quota_data() handles the risk_level column. Planner must verify column naming after pivot.

### Pattern 4: Cache TTL Best Practices
**What:** Maintain appropriate TTL for database view queries
**When to use:** Always for database/API queries in Streamlit

**Existing implementation is CORRECT:**
```python
@st.cache_data(ttl=60)  # 60 seconds = 1 minute
```

**Rationale:**
- Dashboard shows real-time quota usage
- 1-minute TTL balances freshness vs database load
- Longer TTL (e.g., 300s for coop_members) appropriate for reference data that changes rarely

**Source:** [Streamlit Caching Docs](https://docs.streamlit.io/develop/concepts/architecture/caching) - "For database queries, always set a ttl to prevent stale data"

### Anti-Patterns to Avoid

- **Anti-pattern:** Fetching quota_remaining and recalculating pct in Python
  - **Why bad:** Defeats purpose of metrics layer, wastes compute
  - **Do instead:** Fetch quota_metrics and use remaining_pct directly

- **Anti-pattern:** Changing RISK_COLORS dictionary values
  - **Why bad:** SQL view risk_level keys ('critical', 'warning', 'ok', 'na') are contractually matched to RISK_COLORS
  - **Do instead:** Keep RISK_COLORS unchanged, verify SQL view uses identical keys

- **Anti-pattern:** Modifying calculation thresholds (10%, 50%)
  - **Why bad:** Creates divergence between SQL and Python logic
  - **Do instead:** Ensure SQL view thresholds match Python exactly (already done in Phase 1)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DataFrame equality testing | Custom comparison loops | pandas.testing.assert_frame_equal() | Handles float precision, NaN comparisons, column order, dtypes |
| Visual regression testing | Screenshot comparison tools | Unit tests with dataframe assertions | Dashboard output is data-driven; test data, not pixels |
| Mocking Supabase calls | Custom mock objects | unittest.mock.patch() | Already used in 234 existing unit tests |
| Cache invalidation | Manual cache clearing | st.cache_data(ttl=N) | Built-in TTL handling, no manual management needed |

**Key insight:** This phase is a **refactoring**, not a feature addition. The best validation is proving output equivalence, not testing new functionality. DataFrame comparison is more reliable than visual diffing for tabular data.

## Common Pitfalls

### Pitfall 1: Column Name Mismatch After Pivot
**What goes wrong:** View uses `remaining_pct`, dashboard expects `pct_remaining`
**Why it happens:** Inconsistent naming between SQL convention (col_name) and Python convention (name_col)
**How to avoid:**
- Add explicit column rename after fetching from view
- OR update all downstream code to use remaining_pct
**Warning signs:** KeyError: 'pct_remaining' in pivot_quota_data() or add_risk_flags()

### Pitfall 2: Risk Level String Mismatch
**What goes wrong:** SQL returns 'ok' but Python expects 'healthy'
**Why it happens:** Prior decision (01-01) standardized on 'ok' to match RISK_COLORS, but code might have old 'healthy' references
**How to avoid:**
- Grep codebase for 'healthy' and replace with 'ok'
- Verify RISK_COLORS keys match SQL view CASE values exactly
**Warning signs:** Color rendering breaks, risk flags show 'na' for healthy vessels

### Pitfall 3: Float Precision Differences
**What goes wrong:** Python calculates 25.0%, SQL returns 25.00 (NUMERIC with ROUND)
**Why it happens:** SQL ROUND() returns NUMERIC type, Pandas uses float64
**How to avoid:**
- Use check_exact=False in assert_frame_equal()
- Set rtol=0.01 (1% relative tolerance) for percentage comparisons
**Warning signs:** Test failures like "25.0 != 25.00" despite functionally identical values

### Pitfall 4: NULL vs None Handling
**What goes wrong:** SQL returns NULL for zero allocation, Python represents as None or NaN
**Why it happens:** Pandas converts SQL NULL to np.nan for float columns, None for object columns
**How to avoid:**
- Use pd.isna() for NULL checks (handles both None and NaN)
- Verify existing _get_risk_level_for_df() wrapper still works with view data
**Warning signs:** TypeError: unsupported operand type(s) for comparison

### Pitfall 5: Test Coverage Gaps
**What goes wrong:** Tests pass but dashboard breaks in production
**Why it happens:** Tests only verify calculations, not actual view data structure
**How to avoid:**
- Add integration test that fetches from actual quota_metrics view (if service role key available)
- OR add unit test mocking view response with all columns (remaining_pct, risk_level, etc.)
**Warning signs:** Unit tests pass but manual testing shows errors

## Code Examples

Verified patterns from existing codebase and official sources:

### Testing DataFrame Equality with Tolerances
```python
# Source: https://pandas.pydata.org/docs/reference/api/pandas.testing.assert_frame_equal.html
import pandas.testing as pdt

def test_quota_metrics_matches_python_calculation(mock_supabase):
    """Verify quota_metrics view returns same values as Python calculation."""
    # Arrange: Mock quota_metrics view response
    view_response = MagicMock()
    view_response.data = [{
        'llp': 'LLP1',
        'species_code': 141,
        'allocation_lbs': 10000,
        'remaining_lbs': 2500,
        'remaining_pct': 25.00,  # SQL NUMERIC
        'risk_level': 'warning'
    }]

    # Expected Python calculation
    expected_data = [{
        'llp': 'LLP1',
        'species_code': 141,
        'allocation_lbs': 10000,
        'remaining_lbs': 2500,
        'pct_remaining': 25.0,  # Python float
        'calculated_risk': 'warning'
    }]

    actual_df = pd.DataFrame(view_response.data)
    expected_df = pd.DataFrame(expected_data)

    # Assert: Allow minor float differences, ignore column order
    pdt.assert_frame_equal(
        actual_df[['llp', 'remaining_pct']],
        expected_df[['llp', 'pct_remaining']],
        check_exact=False,
        rtol=0.01,  # 1% relative tolerance
        check_like=True  # Ignore column/index order
    )
```

### Refactored get_quota_data() Function
```python
# Source: Derived from app/views/dashboard.py lines 25-60
def get_quota_data():
    """Fetch quota_metrics (with pre-calculated %) joined with vessel info"""
    # Use cached data fetchers - NOW FETCHING FROM VIEW
    quota_data = _fetch_quota_metrics(2026)  # Changed from _fetch_quota_remaining
    if not quota_data:
        return pd.DataFrame()

    df = pd.DataFrame(quota_data)

    # Get vessel info (cached for 5 min) - UNCHANGED
    members_data = _fetch_coop_members()
    members_df = pd.DataFrame(members_data) if members_data else pd.DataFrame()

    # Join - UNCHANGED
    df = df.merge(members_df, on="llp", how="left")

    # Map species codes to names - UNCHANGED
    df["species"] = df["species_code"].map(SPECIES_MAP)
    df = df[df["species"].notna()].copy()

    # REMOVED: Python calculation of pct_remaining (lines 54-58)
    # ADDED: Rename view column to match existing downstream code
    df = df.rename(columns={"remaining_pct": "pct_remaining"})

    # risk_level column already present from view, may need renaming in pivot

    return df
```

### Updated add_risk_flags() Using View Data
```python
# Source: Derived from app/views/dashboard.py lines 95-106
def add_risk_flags(df):
    """Add risk flags for each species and overall vessel risk"""
    # After pivot, risk_level from view becomes {species}_risk_level column
    # This example assumes pivot creates POP_risk_level, NR_risk_level, etc.

    for species in ["POP", "NR", "Dusky"]:
        risk_col = f"{species}_risk_level"  # From pivoted quota_metrics.risk_level
        target_col = f"{species}_risk"

        if risk_col in df.columns:
            # Direct assignment - no calculation needed
            df[target_col] = df[risk_col]
        # If column missing, could fall back to calculating from pct_remaining
        # But ideally all species have risk_level from view

    # Vessel is at risk if ANY species is critical - UNCHANGED LOGIC
    risk_cols = [f"{s}_risk" for s in ["POP", "NR", "Dusky"] if f"{s}_risk" in df.columns]
    df["vessel_at_risk"] = df[risk_cols].apply(lambda row: "critical" in row.values, axis=1)

    return df
```

**IMPORTANT:** The exact column names after pivot depend on pivot_quota_data() implementation. Planner must verify how MultiIndex flattening handles risk_level column.

### Testing with Mock Supabase Response
```python
# Source: Existing pattern from tests/test_dashboard.py lines 257-305
@patch('app.views.dashboard.supabase')
def test_quota_metrics_view_structure(mock_supabase):
    """Verify dashboard handles quota_metrics view structure correctly."""
    # Mock quota_metrics view response (includes new columns)
    quota_response = MagicMock()
    quota_response.data = [{
        'llp': 'LLP1',
        'species_code': 141,
        'year': 2026,
        'allocation_lbs': 10000,
        'transfers_in': 0,
        'transfers_out': 0,
        'harvested': 2500,
        'remaining_lbs': 7500,
        'remaining_pct': 75.00,  # NEW from view
        'risk_level': 'ok'       # NEW from view
    }]

    # Mock coop_members - UNCHANGED
    members_response = MagicMock()
    members_response.data = [{
        'llp': 'LLP1',
        'vessel_name': 'Test Vessel',
        'coop_code': 'SB'
    }]

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == 'quota_metrics':  # Changed from quota_remaining
            mock_table.select.return_value.eq.return_value.execute.return_value = quota_response
        else:
            mock_table.select.return_value.execute.return_value = members_response
        return mock_table

    mock_supabase.table.side_effect = table_side_effect

    from app.views.dashboard import get_quota_data

    result = get_quota_data()

    # Assertions: View columns properly mapped
    assert 'pct_remaining' in result.columns  # Renamed from remaining_pct
    assert result.iloc[0]['pct_remaining'] == 75.00
    # risk_level handled in pivot/add_risk_flags
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Application-layer calculations | Database view calculations | 2020s (metrics layer adoption) | Better performance, consistency, testability |
| st.cache (deprecated) | st.cache_data | Streamlit 1.18 (2023) | More granular caching control, TTL support |
| Manual DataFrame comparison | pandas.testing.assert_frame_equal() | pandas 1.0+ (2020) | Robust float/NaN handling |
| selenium + pytest-selenium | Playwright + pytest-playwright | 2021-2022 | Faster, more reliable browser automation |

**Deprecated/outdated:**
- **@st.cache**: Replaced by @st.cache_data (for data) and @st.cache_resource (for connections)
- **security_definer views**: Replaced by security_invoker=true for RLS enforcement (Postgres 15+, 2022)
- **pytest-selenium**: Community moved to Playwright for better async support and speed

## Open Questions

Things that couldn't be fully resolved:

1. **How does pivot_quota_data() handle risk_level column?**
   - What we know: Current pivot uses pivot_table() on remaining_lbs, allocation_lbs, pct_remaining
   - What's unclear: Will risk_level automatically pivot to POP_risk_level, NR_risk_level columns?
   - Recommendation: Planner should add risk_level to values parameter in pivot_table() call and verify column naming

2. **Should integration tests use actual quota_metrics view?**
   - What we know: test_quota_tracking.py has 26 integration tests with service role key
   - What's unclear: Whether to add quota_metrics-specific integration test or rely on unit mocks
   - Recommendation: If service role key available, add one integration test verifying view returns expected columns

3. **Does visual regression testing add value here?**
   - What we know: Streamlit has built-in AppTest framework; SeleniumBase offers visual diffing
   - What's unclear: Whether pixel-perfect comparison worth setup complexity for data-driven dashboard
   - Recommendation: Skip visual regression; use DataFrame assertions + manual smoke test

## Sources

### Primary (HIGH confidence)
- [Pandas assert_frame_equal documentation](https://pandas.pydata.org/docs/reference/api/pandas.testing.assert_frame_equal.html) - DataFrame comparison API
- [Streamlit Caching Docs](https://docs.streamlit.io/develop/concepts/architecture/caching) - Cache TTL best practices
- [Streamlit App Testing Docs](https://docs.streamlit.io/develop/concepts/app-testing/get-started) - Built-in testing framework
- [Supabase RLS Docs](https://supabase.com/docs/guides/database/postgres/row-level-security) - security_invoker views
- Existing codebase: app/views/dashboard.py, tests/test_dashboard.py - Current implementation patterns

### Secondary (MEDIUM confidence)
- [Supabase Security Invoker Views Deep Dive](https://git.flexsim.com/blog/supabase-security-invoker-views-a-deep-dive-1764805913) - RLS best practices
- [Testing Streamlit Apps with SeleniumBase](https://blog.streamlit.io/testing-streamlit-apps-using-seleniumbase/) - Visual regression approach (not recommended for this phase)

### Tertiary (LOW confidence)
- Web search results on Streamlit + Postgres integration (general patterns, no phase-specific insights)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in requirements.txt, pandas.testing is built-in
- Architecture: HIGH - Patterns derived from existing codebase (dashboard.py, test_dashboard.py)
- Pitfalls: MEDIUM - Column naming after pivot requires verification; float precision differences are common but manageable

**Research date:** 2026-01-28
**Valid until:** 2026-02-28 (30 days - stable libraries, well-established patterns)
