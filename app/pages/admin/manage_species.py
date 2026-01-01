"""
Manage Species - CRUD operations for species table.
"""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_role

TABLE_NAME = "species"
PAGE_TITLE = "Manage Species"
ITEM_NAME = "species"


def show():
    """Main entry point for the page."""
    if not require_role("admin"):
        st.stop()

    init_session_state()

    # Header with Add button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(PAGE_TITLE)
    with col2:
        if st.button(f"+ Add Species", key="species_add_btn", use_container_width=True):
            st.session_state.species_mode = "add"
            st.session_state.species_selected_id = None

    # Load and display data
    data = fetch_data()

    if data.empty:
        st.info("No species found. Click 'Add Species' to create one.")
    else:
        display_data_table(data)
        show_action_buttons()

    # Show form if in add/edit mode
    if st.session_state.species_mode in ["add", "edit"]:
        show_form()

    # Delete confirmation dialog
    if st.session_state.species_show_delete_dialog:
        show_delete_dialog()


def init_session_state():
    """Initialize session state variables for this page."""
    defaults = {
        "species_mode": "view",
        "species_selected_id": None,
        "species_selected_ids": [],
        "species_show_delete_dialog": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_mode():
    """Reset to view mode and clear selections."""
    st.session_state.species_mode = "view"
    st.session_state.species_selected_id = None
    st.session_state.species_selected_ids = []


def fetch_data() -> pd.DataFrame:
    """Fetch all species from the table."""
    try:
        response = supabase.table(TABLE_NAME).select("*").order("species_code").execute()
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
    except Exception:
        return None


def display_data_table(data: pd.DataFrame):
    """Display data table with row selection."""
    display_columns = ["species_code", "species_name"]

    column_config = {
        "species_code": st.column_config.TextColumn("Code"),
        "species_name": st.column_config.TextColumn("Name"),
    }

    selection = st.dataframe(
        data[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        on_select="rerun",
        selection_mode="multi-row",
        key="species_table",
    )

    if selection and selection.selection.rows:
        selected_indices = selection.selection.rows
        st.session_state.species_selected_ids = data.iloc[selected_indices]["id"].tolist()
    else:
        st.session_state.species_selected_ids = []


def show_action_buttons():
    """Display Edit and Delete buttons."""
    selected_ids = st.session_state.species_selected_ids

    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        edit_disabled = len(selected_ids) != 1
        if st.button("Edit", key="species_edit_btn", disabled=edit_disabled, use_container_width=True):
            st.session_state.species_mode = "edit"
            st.session_state.species_selected_id = selected_ids[0]
            st.rerun()

    with col2:
        delete_disabled = len(selected_ids) == 0
        if st.button("Delete", key="species_delete_btn", disabled=delete_disabled, use_container_width=True):
            st.session_state.species_show_delete_dialog = True
            st.rerun()


def show_form():
    """Display add/edit form in an expander."""
    mode = st.session_state.species_mode
    is_edit = mode == "edit"

    existing = {}
    if is_edit:
        existing = fetch_record(st.session_state.species_selected_id) or {}

    title = "Edit Species" if is_edit else "Add New Species"

    with st.expander(title, expanded=True):
        with st.form("species_form"):
            species_code = st.text_input(
                "Species Code *",
                value=existing.get("species_code", ""),
                placeholder="e.g., 141",
                key="species_form_code",
            )

            species_name = st.text_input(
                "Species Name *",
                value=existing.get("species_name", ""),
                placeholder="e.g., Pacific Ocean Perch",
                key="species_form_name",
            )

            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button(
                    "Save" if is_edit else "Create",
                    use_container_width=True,
                    type="primary",
                )
            with col2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)

            if cancelled:
                reset_mode()
                st.rerun()

            if submitted:
                if not species_code:
                    st.error("Species Code is required.")
                    return
                if not species_name:
                    st.error("Species Name is required.")
                    return

                record_data = {
                    "species_code": species_code.strip(),
                    "species_name": species_name.strip(),
                }

                if is_edit:
                    success = update_record(st.session_state.species_selected_id, record_data)
                else:
                    success = create_record(record_data)

                if success:
                    st.success(f"Species {'updated' if is_edit else 'created'} successfully!")
                    reset_mode()
                    st.rerun()


def show_delete_dialog():
    """Display delete confirmation dialog."""
    selected_ids = st.session_state.species_selected_ids
    count = len(selected_ids)

    @st.dialog("Delete Species")
    def confirm_delete():
        st.warning(f"Are you sure you want to delete {count} species? This cannot be undone.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", key="species_confirm_delete", use_container_width=True, type="primary"):
                success_count = 0
                for record_id in selected_ids:
                    if delete_record(record_id):
                        success_count += 1

                if success_count == count:
                    st.success(f"Deleted {count} species.")
                else:
                    st.warning(f"Deleted {success_count} of {count} species.")

                st.session_state.species_show_delete_dialog = False
                reset_mode()
                st.rerun()

        with col2:
            if st.button("Cancel", key="species_cancel_delete", use_container_width=True):
                st.session_state.species_show_delete_dialog = False
                st.rerun()

    confirm_delete()


def create_record(data: dict) -> bool:
    """Create a new record."""
    try:
        supabase.table(TABLE_NAME).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error creating species: {e}")
        return False


def update_record(record_id: str, data: dict) -> bool:
    """Update an existing record."""
    try:
        supabase.table(TABLE_NAME).update(data).eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating species: {e}")
        return False


def delete_record(record_id: str) -> bool:
    """Delete a record by ID."""
    try:
        supabase.table(TABLE_NAME).delete().eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting species: {e}")
        return False
