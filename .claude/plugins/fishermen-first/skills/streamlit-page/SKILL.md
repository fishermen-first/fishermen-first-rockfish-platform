---
name: Streamlit Page Generator
description: This skill should be used when the user asks to "create a page", "add a new view", "scaffold a page", "create a Streamlit page", "add a dashboard", or needs to create a new page in the Fishermen First Streamlit application following project conventions.
version: 0.1.0
---

# Streamlit Page Generator

Generate properly structured Streamlit pages for the Fishermen First application following project conventions for styling, caching, access control, and form patterns.

## Overview

This skill creates Streamlit pages that follow project standards:
- Consistent imports and module structure
- `@st.cache_data` for data fetching with appropriate TTL
- Role-based access control via `require_role()`
- `page_header()` and `section_header()` for consistent styling
- Form patterns with validation
- Tab-based layouts for multi-section pages

## File Location

All pages go in `app/views/` with snake_case naming:
- `app/views/page_name.py`

## Page Structure Template

```python
"""Page Title - Brief description of what the page does."""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from app.config import supabase
from app.auth import require_role


# =============================================================================
# CACHED DATA FETCHING
# =============================================================================

@st.cache_data(ttl=300)
def _fetch_reference_data():
    """Cached: Fetch reference data (rarely changes)."""
    response = supabase.table("table_name").select(
        "col1, col2"
    ).order("col1").execute()
    return response.data if response.data else []


@st.cache_data(ttl=60)
def _fetch_dynamic_data(filter_value: str):
    """Cached: Fetch dynamic data (shorter TTL)."""
    response = supabase.table("table_name").select(
        "col1, col2, col3"
    ).eq("filter_col", filter_value).eq("is_deleted", False).execute()
    return response.data if response.data else []


def clear_page_cache():
    """Clear page caches after modifications."""
    _fetch_dynamic_data.clear()


# =============================================================================
# DATA ACCESS FUNCTIONS
# =============================================================================

def get_display_options() -> dict:
    """Get options for dropdowns."""
    data = _fetch_reference_data()
    return {row["col1"]: row["col2"] for row in data}


def insert_record(field1: str, field2: int, user_id: str, org_id: str) -> tuple[bool, str | None]:
    """Insert a new record."""
    try:
        response = supabase.table("table_name").insert({
            "org_id": org_id,
            "field1": field1,
            "field2": field2,
            "created_by": user_id,
            "is_deleted": False
        }).execute()

        if response.data:
            clear_page_cache()
            return True, None
        return False, "Insert returned no data"
    except Exception as e:
        return False, str(e)


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def format_value(value: float) -> str:
    """Format value for display."""
    return f"{value:,.0f}"


# =============================================================================
# MAIN PAGE
# =============================================================================

def show():
    """Display the page."""
    from app.utils.styles import page_header, section_header

    # Access check
    if not require_role("manager"):
        return

    page_header("Page Title", "Subtitle describing the page purpose")

    org_id = st.session_state.get("org_id")
    if not org_id:
        st.error("Organization not set. Please log out and log back in.")
        return

    user_id = st.session_state.user.id if st.session_state.user else None

    # Load reference data
    options = get_display_options()

    # --- MAIN CONTENT ---
    section_header("SECTION NAME", "icon")

    # Page content here...
```

## Access Control

Use `require_role()` at the start of `show()`:

```python
# Single role
if not require_role("manager"):
    return

# Multiple roles (check manually)
role = st.session_state.get("user_role")
if role not in ["admin", "manager"]:
    st.error("You don't have permission to access this page.")
    return
```

## Caching Strategy

| Data Type | TTL | Example |
|-----------|-----|---------|
| Reference data (species, coops) | 300s (5 min) | `@st.cache_data(ttl=300)` |
| User-specific data | 60s (1 min) | `@st.cache_data(ttl=60)` |
| Real-time data | 30s | `@st.cache_data(ttl=30)` |
| Static lookups | No TTL | `@st.cache_data` |

Always provide `clear_*_cache()` functions for invalidation after writes.

## Styling Functions

Import from `app/utils/styles.py`:

```python
from app.utils.styles import page_header, section_header, NAVY, GRAY_TEXT

# Page title with subtitle
page_header("Title", "Subtitle")

# Section headers with icons
section_header("SECTION NAME", "📊")
section_header("FILTERS", "🔍")
section_header("DATA TABLE", "📋")
```

## Form Patterns

### Dynamic Selects Outside Form

For selects that affect other fields, place outside form:

```python
# Outside form - changes trigger immediate updates
selected_option = st.selectbox("Option", options, key="option_select")

# Show computed values based on selection
if selected_option:
    value = compute_something(selected_option)
    st.info(f"Computed: {value}")

# Form for submission
with st.form("form_name", clear_on_submit=True):
    other_field = st.text_input("Field")
    submitted = st.form_submit_button("Submit", use_container_width=True)
```

### Standard Form Pattern

```python
with st.form("form_name", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        field1 = st.text_input("Field 1")
    with col2:
        field2 = st.number_input("Field 2", min_value=0.0)

    notes = st.text_area("Notes (optional)", max_chars=1000)

    submitted = st.form_submit_button(
        "Submit",
        type="primary",
        use_container_width=True
    )

    if submitted:
        if not field1:
            st.error("Field 1 is required.")
        else:
            success, error = insert_record(field1, field2, user_id, org_id)
            if success:
                st.success("Record created!")
                st.rerun()
            else:
                st.error(f"Failed: {error}")
```

## Layout Patterns

### Two-Column Layout

```python
col1, col2 = st.columns(2)
with col1:
    # Left content
with col2:
    # Right content
```

### Tabs for Multi-Section

```python
tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])

with tab1:
    # Tab 1 content

with tab2:
    # Tab 2 content
```

### Expander for Optional Content

```python
with st.expander("Advanced Options", expanded=False):
    # Hidden by default content
```

## Registration

After creating the page, register in `app/main.py`:

1. Add import
2. Add to navigation/sidebar
3. Add route handling

## Additional Resources

### Reference Files

For detailed patterns:
- **`references/page-patterns.md`** - Complete page structure patterns
- **`references/form-patterns.md`** - Form validation and submission patterns

### Example Files

Working pages from the project:
- **`examples/transfers.md`** - Form with dynamic validation
- **`examples/bycatch_alerts.md`** - Tabs, filters, and action buttons
