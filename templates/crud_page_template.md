# CRUD Page Template

Standard pattern for admin management pages. Reference this template when building pages in `app/pages/admin/`.

---

## Page Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Page Title                              [+ Add New Button] │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Data Table (with row selection)                     │    │
│  │ ☐ │ Name        │ Field2      │ Field3    │ ...    │    │
│  │ ☐ │ Row 1       │ ...         │ ...       │        │    │
│  │ ☑ │ Row 2       │ ...         │ ...       │        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  [Edit Selected]  [Delete Selected]                         │
│                                                             │
│  ▶ Add/Edit Form (expander, opens when adding/editing)      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Field 1: [___________]                              │    │
│  │ Field 2: [___________]                              │    │
│  │ [Save]  [Cancel]                                    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Complete Code Template

```python
import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_role

# Table and display configuration
TABLE_NAME = "table_name"
PAGE_TITLE = "Manage Items"
ITEM_NAME = "item"  # Singular, lowercase (e.g., "cooperative", "member")


def show():
    """Main entry point for the page."""
    if not require_role("admin"):
        st.stop()

    init_session_state()

    st.title(PAGE_TITLE)

    # Header with Add button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button(f"+ Add {ITEM_NAME.title()}", use_container_width=True):
            st.session_state[f"{TABLE_NAME}_mode"] = "add"
            st.session_state[f"{TABLE_NAME}_selected_id"] = None

    # Load and display data
    data = fetch_data()

    if data.empty:
        st.info(f"No {ITEM_NAME}s found. Click 'Add {ITEM_NAME.title()}' to create one.")
    else:
        display_data_table(data)
        show_action_buttons()

    # Show form if in add/edit mode
    if st.session_state[f"{TABLE_NAME}_mode"] in ["add", "edit"]:
        show_form(data)

    # Delete confirmation dialog
    if st.session_state[f"{TABLE_NAME}_show_delete_dialog"]:
        show_delete_dialog()


# =============================================================================
# Session State
# =============================================================================

def init_session_state():
    """Initialize session state variables for this page."""
    defaults = {
        f"{TABLE_NAME}_mode": "view",           # "view", "add", "edit"
        f"{TABLE_NAME}_selected_id": None,       # UUID of selected row
        f"{TABLE_NAME}_selected_ids": [],        # List of selected UUIDs (multi-select)
        f"{TABLE_NAME}_show_delete_dialog": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_mode():
    """Reset to view mode and clear selections."""
    st.session_state[f"{TABLE_NAME}_mode"] = "view"
    st.session_state[f"{TABLE_NAME}_selected_id"] = None
    st.session_state[f"{TABLE_NAME}_selected_ids"] = []


# =============================================================================
# Data Fetching
# =============================================================================

def fetch_data() -> pd.DataFrame:
    """Fetch all records from the table."""
    try:
        response = supabase.table(TABLE_NAME).select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()


def fetch_record(record_id: str) -> dict | None:
    """Fetch a single record by ID."""
    try:
        response = supabase.table(TABLE_NAME).select("*").eq("id", record_id).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching record: {e}")
        return None


# =============================================================================
# Data Display
# =============================================================================

def display_data_table(data: pd.DataFrame):
    """Display data table with row selection."""
    # Configure columns to display (exclude internal fields)
    display_columns = ["name_field", "other_field"]  # Customize this

    # Rename columns for display
    column_config = {
        "name_field": st.column_config.TextColumn("Name"),
        "other_field": st.column_config.TextColumn("Other"),
    }

    # Display with selection
    selection = st.dataframe(
        data[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        on_select="rerun",
        selection_mode="multi-row",
    )

    # Store selected IDs
    if selection and selection.selection.rows:
        selected_indices = selection.selection.rows
        st.session_state[f"{TABLE_NAME}_selected_ids"] = data.iloc[selected_indices]["id"].tolist()
    else:
        st.session_state[f"{TABLE_NAME}_selected_ids"] = []


def show_action_buttons():
    """Display Edit and Delete buttons."""
    selected_ids = st.session_state[f"{TABLE_NAME}_selected_ids"]

    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        edit_disabled = len(selected_ids) != 1
        if st.button("Edit Selected", disabled=edit_disabled, use_container_width=True):
            st.session_state[f"{TABLE_NAME}_mode"] = "edit"
            st.session_state[f"{TABLE_NAME}_selected_id"] = selected_ids[0]
            st.rerun()

    with col2:
        delete_disabled = len(selected_ids) == 0
        if st.button("Delete Selected", disabled=delete_disabled, use_container_width=True):
            st.session_state[f"{TABLE_NAME}_show_delete_dialog"] = True
            st.rerun()


# =============================================================================
# Add/Edit Form
# =============================================================================

def show_form(data: pd.DataFrame):
    """Display add/edit form in an expander."""
    mode = st.session_state[f"{TABLE_NAME}_mode"]
    is_edit = mode == "edit"

    # Load existing data for edit mode
    existing = {}
    if is_edit:
        existing = fetch_record(st.session_state[f"{TABLE_NAME}_selected_id"]) or {}

    title = f"Edit {ITEM_NAME.title()}" if is_edit else f"Add New {ITEM_NAME.title()}"

    with st.expander(title, expanded=True):
        with st.form(f"{TABLE_NAME}_form"):
            # Form fields - customize these
            name = st.text_input(
                "Name *",
                value=existing.get("name_field", ""),
                placeholder=f"Enter {ITEM_NAME} name"
            )

            other_field = st.text_input(
                "Other Field",
                value=existing.get("other_field", "")
            )

            # Form buttons
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button(
                    "Save" if is_edit else "Create",
                    use_container_width=True,
                    type="primary"
                )
            with col2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)

            if cancelled:
                reset_mode()
                st.rerun()

            if submitted:
                # Validation
                if not name:
                    st.error("Name is required.")
                    return

                # Prepare data
                record_data = {
                    "name_field": name.strip(),
                    "other_field": other_field.strip() if other_field else None,
                }

                # Save
                if is_edit:
                    success = update_record(st.session_state[f"{TABLE_NAME}_selected_id"], record_data)
                else:
                    success = create_record(record_data)

                if success:
                    st.success(f"{ITEM_NAME.title()} {'updated' if is_edit else 'created'} successfully!")
                    reset_mode()
                    st.rerun()


# =============================================================================
# Delete Confirmation
# =============================================================================

def show_delete_dialog():
    """Display delete confirmation dialog."""
    selected_ids = st.session_state[f"{TABLE_NAME}_selected_ids"]
    count = len(selected_ids)

    @st.dialog(f"Delete {ITEM_NAME.title()}(s)")
    def confirm_delete():
        st.warning(f"Are you sure you want to delete {count} {ITEM_NAME}(s)? This cannot be undone.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", use_container_width=True, type="primary"):
                success_count = 0
                for record_id in selected_ids:
                    if delete_record(record_id):
                        success_count += 1

                if success_count == count:
                    st.success(f"Deleted {count} {ITEM_NAME}(s).")
                else:
                    st.warning(f"Deleted {success_count} of {count} {ITEM_NAME}(s).")

                st.session_state[f"{TABLE_NAME}_show_delete_dialog"] = False
                reset_mode()
                st.rerun()

        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state[f"{TABLE_NAME}_show_delete_dialog"] = False
                st.rerun()

    confirm_delete()


# =============================================================================
# CRUD Operations
# =============================================================================

def create_record(data: dict) -> bool:
    """Create a new record."""
    try:
        supabase.table(TABLE_NAME).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error creating {ITEM_NAME}: {e}")
        return False


def update_record(record_id: str, data: dict) -> bool:
    """Update an existing record."""
    try:
        supabase.table(TABLE_NAME).update(data).eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating {ITEM_NAME}: {e}")
        return False


def delete_record(record_id: str) -> bool:
    """Delete a record by ID."""
    try:
        supabase.table(TABLE_NAME).delete().eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting {ITEM_NAME}: {e}")
        return False
```

---

## Variations

### Foreign Key Dropdown

For fields that reference another table (e.g., member_id → members):

```python
def fetch_members_for_dropdown() -> list[dict]:
    """Fetch members for dropdown selection."""
    try:
        response = supabase.table("members").select("id, member_name").order("member_name").execute()
        return response.data or []
    except Exception:
        return []


# In the form:
members = fetch_members_for_dropdown()
member_options = {m["id"]: m["member_name"] for m in members}

selected_member_id = st.selectbox(
    "Member *",
    options=list(member_options.keys()),
    format_func=lambda x: member_options.get(x, "Unknown"),
    index=list(member_options.keys()).index(existing.get("member_id")) if existing.get("member_id") in member_options else 0
)
```

### Date Fields

```python
from datetime import date

# In the form:
effective_from = st.date_input(
    "Effective From *",
    value=existing.get("effective_from") or date.today(),
)

effective_to = st.date_input(
    "Effective To (leave blank if current)",
    value=existing.get("effective_to"),
)

# When saving - convert to ISO format string:
record_data = {
    "effective_from": effective_from.isoformat(),
    "effective_to": effective_to.isoformat() if effective_to else None,
}
```

### Boolean Fields

```python
# In the form:
is_active = st.checkbox(
    "Active",
    value=existing.get("is_active", True)
)

is_psc = st.toggle(
    "Is PSC Species",
    value=existing.get("is_psc", False)
)
```

### Numeric Fields

```python
# Integer
year = st.number_input(
    "Year *",
    min_value=2020,
    max_value=2100,
    value=existing.get("year", date.today().year),
    step=1
)

# Decimal (e.g., quota amounts)
amount = st.number_input(
    "Amount (lbs) *",
    min_value=0.0,
    value=float(existing.get("amount", 0)),
    step=100.0,
    format="%.2f"
)
```

### Text Area (for longer text)

```python
contact_info = st.text_area(
    "Contact Info",
    value=existing.get("contact_info", ""),
    placeholder="Address, phone, email, etc.",
    height=100
)
```

---

## Historical Tracking Tables

For tables with `effective_from` and `effective_to` dates (e.g., `cooperative_memberships`, `vessel_cooperative_assignments`):

### Additional Display Logic

```python
def display_data_table(data: pd.DataFrame):
    """Display with current/historical indicator."""
    if data.empty:
        return

    # Add status column
    data = data.copy()
    data["status"] = data["effective_to"].apply(
        lambda x: "Current" if pd.isna(x) or x is None else "Historical"
    )

    # Filter options
    status_filter = st.radio(
        "Show:",
        ["Current Only", "All", "Historical Only"],
        horizontal=True
    )

    if status_filter == "Current Only":
        data = data[data["status"] == "Current"]
    elif status_filter == "Historical Only":
        data = data[data["status"] == "Historical"]

    # Display columns
    display_columns = ["entity_name", "effective_from", "effective_to", "status"]

    column_config = {
        "entity_name": st.column_config.TextColumn("Name"),
        "effective_from": st.column_config.DateColumn("From"),
        "effective_to": st.column_config.DateColumn("To"),
        "status": st.column_config.TextColumn("Status"),
    }

    # ... rest of display logic
```

### End Assignment (instead of delete)

For historical tables, "deleting" means ending the assignment:

```python
def end_assignment(record_id: str) -> bool:
    """End an assignment by setting effective_to to today."""
    try:
        supabase.table(TABLE_NAME).update({
            "effective_to": date.today().isoformat()
        }).eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error ending assignment: {e}")
        return False


# Replace delete button with end assignment:
if st.button("End Assignment", disabled=len(selected_ids) != 1):
    # Only allow ending current (active) assignments
    record = fetch_record(selected_ids[0])
    if record and record.get("effective_to") is None:
        if end_assignment(selected_ids[0]):
            st.success("Assignment ended.")
            st.rerun()
    else:
        st.warning("This assignment has already ended.")
```

---

## Error Handling Pattern

### Standard Try/Except with User Feedback

```python
def safe_operation(operation_name: str):
    """Wrapper for database operations with consistent error handling."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e)

                # Parse common Supabase errors
                if "duplicate key" in error_msg.lower():
                    st.error(f"A record with this value already exists.")
                elif "foreign key" in error_msg.lower():
                    st.error(f"Cannot complete operation: referenced record doesn't exist or is in use.")
                elif "not found" in error_msg.lower():
                    st.error(f"Record not found. It may have been deleted.")
                else:
                    st.error(f"Error during {operation_name}: {error_msg}")

                return None
        return wrapper
    return decorator


# Usage:
@safe_operation("create")
def create_record(data: dict):
    response = supabase.table(TABLE_NAME).insert(data).execute()
    return response.data
```

### Validation Pattern

```python
def validate_form(data: dict) -> list[str]:
    """Validate form data and return list of errors."""
    errors = []

    if not data.get("name"):
        errors.append("Name is required.")

    if data.get("email") and "@" not in data["email"]:
        errors.append("Invalid email format.")

    if data.get("effective_from") and data.get("effective_to"):
        if data["effective_from"] > data["effective_to"]:
            errors.append("Effective From must be before Effective To.")

    return errors


# In form submission:
if submitted:
    errors = validate_form(record_data)
    if errors:
        for error in errors:
            st.error(error)
        return

    # Proceed with save...
```

---

## Checklist for Testing CRUD Pages

### Setup
- [ ] Page loads without errors
- [ ] Page title and layout are correct
- [ ] Empty state message shows when no data exists
- [ ] Data table displays correctly with data

### Create (Add)
- [ ] "Add" button opens the form
- [ ] All required fields are marked with *
- [ ] Form validation shows errors for missing required fields
- [ ] Form validation shows errors for invalid data (format, range)
- [ ] Cancel button closes form without saving
- [ ] Successful create shows success message
- [ ] New record appears in table after create
- [ ] Foreign key dropdowns show correct options

### Read (View)
- [ ] All expected columns display in table
- [ ] Data is formatted correctly (dates, numbers, booleans)
- [ ] Sorting works (if enabled)
- [ ] Filtering works (if enabled)
- [ ] Row selection highlights correctly

### Update (Edit)
- [ ] "Edit" button is disabled when no row selected
- [ ] "Edit" button is disabled when multiple rows selected
- [ ] "Edit" button opens form with existing data populated
- [ ] All fields show current values
- [ ] Changes are saved correctly
- [ ] Success message appears after update
- [ ] Table refreshes with updated data

### Delete
- [ ] "Delete" button is disabled when no rows selected
- [ ] "Delete" button works with single selection
- [ ] "Delete" button works with multi-select
- [ ] Confirmation dialog appears before delete
- [ ] Cancel in dialog prevents deletion
- [ ] Confirm in dialog deletes record(s)
- [ ] Success message shows count of deleted records
- [ ] Table refreshes after deletion
- [ ] Foreign key constraints prevent invalid deletes (shows error)

### Historical Tables (if applicable)
- [ ] Status filter (Current/All/Historical) works
- [ ] Current records show "Current" status
- [ ] Historical records show dates correctly
- [ ] "End Assignment" sets effective_to date
- [ ] Cannot end already-ended assignments

### Permissions
- [ ] Page is only accessible to authorized roles
- [ ] Unauthorized users see error message

### Edge Cases
- [ ] Very long text values display correctly
- [ ] Special characters in text don't break display
- [ ] Empty optional fields save as NULL
- [ ] Concurrent edits are handled (record changed by another user)
- [ ] Network errors show user-friendly message

---

## Integration with main.py

To add a new CRUD page to the navigation:

1. Create the page file: `app/pages/admin/manage_<items>.py`
2. Import and call from `show_current_page()` in `main.py`:

```python
# In main.py show_current_page():
elif page == "admin":
    show_admin_submenu()

def show_admin_submenu():
    """Show admin sub-navigation."""
    admin_page = st.session_state.get("admin_page", "users")

    tabs = st.tabs(["Users", "Cooperatives", "Members", "Vessels", "Processors"])

    with tabs[0]:
        from app.pages.admin import manage_users
        manage_users.show()

    with tabs[1]:
        from app.pages.admin import manage_coops
        manage_coops.show()

    # ... etc
```

---

## File Naming Convention

```
app/pages/admin/
├── manage_users.py        # Users table
├── manage_coops.py        # Cooperatives table
├── manage_members.py      # Members table
├── manage_vessels.py      # Vessels table
├── manage_processors.py   # Processors table
├── manage_species.py      # Species table
└── manage_seasons.py      # Seasons table
```
