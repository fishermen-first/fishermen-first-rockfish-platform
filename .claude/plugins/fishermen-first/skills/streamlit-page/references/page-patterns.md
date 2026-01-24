# Page Patterns for Fishermen First

Detailed patterns for different types of Streamlit pages.

## Page Type 1: Data Entry Form

For pages primarily focused on data input (transfers, reports).

### Structure

```python
"""Data Entry Page - Description."""

import streamlit as st
from app.config import supabase
from app.auth import require_role

# Constants
CURRENT_YEAR = 2026

# =============================================================================
# CACHED DATA FETCHING
# =============================================================================

@st.cache_data(ttl=300)
def _fetch_dropdown_options():
    """Fetch options for dropdowns."""
    response = supabase.table("reference_table").select("id, name").execute()
    return response.data if response.data else []


def clear_cache():
    """Clear caches after data modification."""
    _fetch_dropdown_options.clear()


# =============================================================================
# DATA OPERATIONS
# =============================================================================

def validate_input(field1, field2) -> tuple[bool, list[str]]:
    """Validate form input."""
    errors = []
    if not field1:
        errors.append("Field 1 is required.")
    if field2 <= 0:
        errors.append("Field 2 must be positive.")
    return len(errors) == 0, errors


def insert_record(data: dict) -> tuple[bool, str | None]:
    """Insert record to database."""
    try:
        response = supabase.table("table_name").insert(data).execute()
        if response.data:
            clear_cache()
            return True, None
        return False, "Insert returned no data"
    except Exception as e:
        return False, str(e)


# =============================================================================
# MAIN PAGE
# =============================================================================

def show():
    """Display the page."""
    from app.utils.styles import page_header, section_header

    if not require_role("manager"):
        return

    page_header("Data Entry", "Enter new records")

    org_id = st.session_state.get("org_id")
    user_id = st.session_state.user.id if st.session_state.user else None

    # Load options
    options = _fetch_dropdown_options()
    option_map = {o["name"]: o["id"] for o in options}

    # --- FORM SECTION ---
    section_header("NEW ENTRY", "➕")

    # Dynamic select outside form
    selected = st.selectbox("Select Option", list(option_map.keys()))

    with st.form("entry_form", clear_on_submit=True):
        value = st.number_input("Value", min_value=0.0)
        notes = st.text_area("Notes (optional)")

        submitted = st.form_submit_button("Submit", type="primary", use_container_width=True)

        if submitted:
            valid, errors = validate_input(selected, value)
            if not valid:
                for e in errors:
                    st.error(e)
            else:
                success, error = insert_record({
                    "org_id": org_id,
                    "option_id": option_map[selected],
                    "value": value,
                    "notes": notes.strip() if notes else None,
                    "created_by": user_id
                })
                if success:
                    st.success("Record created!")
                    st.rerun()
                else:
                    st.error(f"Failed: {error}")
```

## Page Type 2: Dashboard/View

For pages primarily focused on displaying data.

### Structure

```python
"""Dashboard Page - View and analyze data."""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_role

# =============================================================================
# CACHED DATA FETCHING
# =============================================================================

@st.cache_data(ttl=60)
def _fetch_summary_data(org_id: str):
    """Fetch summary/KPI data."""
    response = supabase.table("summary_view").select("*").eq("org_id", org_id).execute()
    return response.data if response.data else []


@st.cache_data(ttl=300)
def _fetch_filter_options():
    """Fetch filter dropdown options."""
    response = supabase.table("reference_table").select("code, name").execute()
    return response.data if response.data else []


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def render_kpi_cards(data: list):
    """Render KPI metric cards."""
    if not data:
        st.info("No data available.")
        return

    cols = st.columns(len(data))
    for col, item in zip(cols, data):
        with col:
            st.metric(
                label=item["label"],
                value=f"{item['value']:,.0f}",
                delta=item.get("delta")
            )


def render_data_table(data: list):
    """Render data as styled table."""
    if not data:
        st.info("No records found.")
        return

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


# =============================================================================
# MAIN PAGE
# =============================================================================

def show():
    """Display the dashboard."""
    from app.utils.styles import page_header, section_header

    if not require_role("manager"):
        return

    page_header("Dashboard", "Overview of key metrics")

    org_id = st.session_state.get("org_id")

    # --- FILTERS ---
    section_header("FILTERS", "🔍")

    filter_options = _fetch_filter_options()
    col1, col2 = st.columns(2)

    with col1:
        selected_filter = st.selectbox(
            "Filter By",
            ["All"] + [o["name"] for o in filter_options]
        )

    with col2:
        date_range = st.date_input("Date Range", value=[])

    # --- KPIs ---
    section_header("KEY METRICS", "📊")

    summary = _fetch_summary_data(org_id)
    render_kpi_cards(summary)

    # --- DATA TABLE ---
    section_header("DETAILS", "📋")

    # Apply filters
    filtered_data = summary  # Apply filter logic here
    render_data_table(filtered_data)
```

## Page Type 3: Management Page (CRUD)

For pages with full create/read/update/delete operations.

### Structure

```python
"""Management Page - Full CRUD operations."""

import streamlit as st
from app.config import supabase
from app.auth import require_role

# =============================================================================
# CACHED DATA FETCHING
# =============================================================================

@st.cache_data(ttl=60)
def _fetch_records(org_id: str, status: str | None = None):
    """Fetch records with optional status filter."""
    query = supabase.table("table_name").select("*").eq("org_id", org_id).eq("is_deleted", False)
    if status:
        query = query.eq("status", status)
    response = query.order("created_at", desc=True).execute()
    return response.data if response.data else []


def clear_cache():
    _fetch_records.clear()


# =============================================================================
# CRUD OPERATIONS
# =============================================================================

def create_record(data: dict) -> tuple[bool, str | None]:
    """Create new record."""
    try:
        response = supabase.table("table_name").insert(data).execute()
        if response.data:
            clear_cache()
            return True, None
        return False, "Insert failed"
    except Exception as e:
        return False, str(e)


def update_record(record_id: str, updates: dict) -> tuple[bool, str | None]:
    """Update existing record."""
    try:
        response = supabase.table("table_name").update(updates).eq("id", record_id).execute()
        if response.data:
            clear_cache()
            return True, None
        return False, "Update failed"
    except Exception as e:
        return False, str(e)


def delete_record(record_id: str, user_id: str) -> tuple[bool, str | None]:
    """Soft delete record."""
    try:
        from datetime import datetime
        response = supabase.table("table_name").update({
            "is_deleted": True,
            "deleted_by": user_id,
            "deleted_at": datetime.utcnow().isoformat()
        }).eq("id", record_id).execute()
        if response.data:
            clear_cache()
            return True, None
        return False, "Delete failed"
    except Exception as e:
        return False, str(e)


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_record_card(record: dict, user_id: str):
    """Render a single record with action buttons."""
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.write(f"**{record['name']}**")
            st.caption(f"Created: {record['created_at']}")

        with col2:
            if st.button("Edit", key=f"edit_{record['id']}"):
                st.session_state[f"editing_{record['id']}"] = True
                st.rerun()

        with col3:
            if st.button("Delete", key=f"delete_{record['id']}"):
                success, error = delete_record(record["id"], user_id)
                if success:
                    st.success("Deleted!")
                    st.rerun()
                else:
                    st.error(error)

        # Inline edit form
        if st.session_state.get(f"editing_{record['id']}"):
            render_edit_form(record, user_id)

        st.divider()


def render_edit_form(record: dict, user_id: str):
    """Render inline edit form."""
    with st.expander("Edit", expanded=True):
        new_name = st.text_input("Name", value=record["name"], key=f"name_{record['id']}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save", key=f"save_{record['id']}"):
                success, error = update_record(record["id"], {"name": new_name})
                if success:
                    st.session_state[f"editing_{record['id']}"] = False
                    st.rerun()
                else:
                    st.error(error)
        with col2:
            if st.button("Cancel", key=f"cancel_{record['id']}"):
                st.session_state[f"editing_{record['id']}"] = False
                st.rerun()


# =============================================================================
# MAIN PAGE
# =============================================================================

def show():
    """Display the management page."""
    from app.utils.styles import page_header, section_header

    if not require_role("manager"):
        return

    page_header("Management", "Create and manage records")

    org_id = st.session_state.get("org_id")
    user_id = st.session_state.user.id if st.session_state.user else None

    # --- TABS ---
    tab_active, tab_all = st.tabs(["Active", "All"])

    with tab_active:
        records = _fetch_records(org_id, status="active")
        if not records:
            st.info("No active records.")
        else:
            for record in records:
                render_record_card(record, user_id)

    with tab_all:
        records = _fetch_records(org_id)
        if not records:
            st.info("No records found.")
        else:
            for record in records:
                render_record_card(record, user_id)
```

## Page Type 4: Vessel Owner View (Read-Only)

For restricted role pages with limited functionality.

### Structure

```python
"""Vessel Owner View - Read-only view for vessel owners."""

import streamlit as st
from app.config import supabase

# =============================================================================
# CACHED DATA FETCHING
# =============================================================================

@st.cache_data(ttl=60)
def _fetch_vessel_data(llp: str):
    """Fetch data for specific vessel."""
    response = supabase.table("vessel_view").select("*").eq("llp", llp).execute()
    return response.data if response.data else []


# =============================================================================
# MAIN PAGE
# =============================================================================

def show():
    """Display vessel owner view."""
    from app.utils.styles import page_header, section_header

    # Access check - vessel_owner only
    role = st.session_state.get("user_role")
    if role != "vessel_owner":
        st.error("This page is for vessel owners only.")
        return

    user_llp = st.session_state.get("user_llp")
    if not user_llp:
        st.error("Your account is not linked to a vessel.")
        return

    # Get vessel name for display
    vessel_name = st.session_state.get("vessel_name", user_llp)

    page_header(f"My Vessel: {vessel_name}", f"LLP: {user_llp}")

    # --- QUOTA SUMMARY ---
    section_header("QUOTA REMAINING", "📊")

    data = _fetch_vessel_data(user_llp)

    if not data:
        st.info("No quota data available.")
        return

    # Display quota cards
    cols = st.columns(3)
    for col, item in zip(cols, data):
        with col:
            st.metric(
                label=item["species_name"],
                value=f"{item['remaining']:,.0f} lbs"
            )

    # --- READ-ONLY NOTE ---
    st.caption("Contact your co-op manager to request quota transfers.")
```

## Common Patterns

### Error Handling

```python
try:
    response = supabase.table("table").select("*").execute()
    return response.data or []
except Exception as e:
    st.error(f"Database error: {e}")
    return []
```

### Session State for UI State

```python
# Initialize state
if "show_form" not in st.session_state:
    st.session_state.show_form = False

# Toggle
if st.button("Show Form"):
    st.session_state.show_form = not st.session_state.show_form

# Conditional render
if st.session_state.show_form:
    # Render form
```

### Loading States

```python
with st.spinner("Loading data..."):
    data = fetch_large_dataset()

st.success("Data loaded!")
```

### Confirmation Dialogs

```python
if st.button("Delete"):
    st.session_state.confirm_delete = record_id

if st.session_state.get("confirm_delete") == record_id:
    st.warning("Are you sure?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, delete"):
            delete_record(record_id)
            st.session_state.confirm_delete = None
            st.rerun()
    with col2:
        if st.button("Cancel"):
            st.session_state.confirm_delete = None
            st.rerun()
```
