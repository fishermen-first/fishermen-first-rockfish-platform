"""
Manage Cooperatives - Admin CRUD page for cooperatives table.
"""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_role

# Table and display configuration
TABLE_NAME = "cooperatives"
PAGE_TITLE = "Manage Cooperatives"
ITEM_NAME = "cooperative"


def show():
    """Main entry point for the page."""
    if not require_role("admin"):
        st.stop()

    init_session_state()

    st.subheader(PAGE_TITLE)

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
        f"{TABLE_NAME}_mode": "view",
        f"{TABLE_NAME}_selected_id": None,
        f"{TABLE_NAME}_selected_ids": [],
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
    """Fetch all cooperatives from the table."""
    try:
        response = supabase.table(TABLE_NAME).select("*").order("cooperative_name").execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()


def fetch_record(record_id: str) -> dict | None:
    """Fetch a single cooperative by ID."""
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
    display_columns = ["cooperative_name", "contact_info"]

    column_config = {
        "cooperative_name": st.column_config.TextColumn("Cooperative Name"),
        "contact_info": st.column_config.TextColumn("Contact Info"),
    }

    selection = st.dataframe(
        data[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        on_select="rerun",
        selection_mode="multi-row",
    )

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

    existing = {}
    if is_edit:
        existing = fetch_record(st.session_state[f"{TABLE_NAME}_selected_id"]) or {}

    title = f"Edit {ITEM_NAME.title()}" if is_edit else f"Add New {ITEM_NAME.title()}"

    with st.expander(title, expanded=True):
        with st.form(f"{TABLE_NAME}_form"):
            cooperative_name = st.text_input(
                "Cooperative Name *",
                value=existing.get("cooperative_name", ""),
                placeholder="Enter cooperative name"
            )

            contact_info = st.text_area(
                "Contact Info",
                value=existing.get("contact_info", "") or "",
                placeholder="Address, phone, email, etc.",
                height=100
            )

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
                if not cooperative_name:
                    st.error("Cooperative Name is required.")
                    return

                record_data = {
                    "cooperative_name": cooperative_name.strip(),
                    "contact_info": contact_info.strip() if contact_info else None,
                }

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
        st.caption("Note: Cooperatives with associated members or vessels cannot be deleted.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", use_container_width=True, type="primary"):
                success_count = 0
                for record_id in selected_ids:
                    if delete_record(record_id):
                        success_count += 1

                if success_count == count:
                    st.success(f"Deleted {count} {ITEM_NAME}(s).")
                elif success_count > 0:
                    st.warning(f"Deleted {success_count} of {count} {ITEM_NAME}(s). Some could not be deleted due to existing relationships.")
                else:
                    st.error("Could not delete. Cooperatives may have associated members or vessels.")

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
    """Create a new cooperative."""
    try:
        supabase.table(TABLE_NAME).insert(data).execute()
        return True
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower():
            st.error("A cooperative with this name already exists.")
        else:
            st.error(f"Error creating {ITEM_NAME}: {e}")
        return False


def update_record(record_id: str, data: dict) -> bool:
    """Update an existing cooperative."""
    try:
        supabase.table(TABLE_NAME).update(data).eq("id", record_id).execute()
        return True
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower():
            st.error("A cooperative with this name already exists.")
        else:
            st.error(f"Error updating {ITEM_NAME}: {e}")
        return False


def delete_record(record_id: str) -> bool:
    """Delete a cooperative by ID."""
    try:
        supabase.table(TABLE_NAME).delete().eq("id", record_id).execute()
        return True
    except Exception as e:
        error_msg = str(e)
        if "foreign key" in error_msg.lower():
            st.error("Cannot delete: this cooperative has associated members or vessels.")
        else:
            st.error(f"Error deleting {ITEM_NAME}: {e}")
        return False
