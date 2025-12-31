"""
Manage Vessels - Admin CRUD page for vessels table.
"""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_role

# Table and display configuration
TABLE_NAME = "vessels"
PAGE_TITLE = "Manage Vessels"
ITEM_NAME = "vessel"


def show():
    """Main entry point for the page."""
    if not require_role("admin"):
        st.stop()

    init_session_state()

    st.subheader(PAGE_TITLE)

    # Header with Add button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button(f"+ Add {ITEM_NAME.title()}", use_container_width=True, key="vessels_add_btn"):
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
    """Fetch all vessels with owner names."""
    try:
        # Get vessels
        response = supabase.table(TABLE_NAME).select("*").order("vessel_name").execute()
        if not response.data:
            return pd.DataFrame()

        vessels = pd.DataFrame(response.data)

        # Get member names for display
        member_response = supabase.table("members").select("id, member_name").execute()
        member_names = {}
        if member_response.data:
            member_names = {m["id"]: m["member_name"] for m in member_response.data}

        vessels["owner_name"] = vessels["member_id"].map(member_names)

        return vessels

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()


def fetch_record(record_id: str) -> dict | None:
    """Fetch a single vessel by ID."""
    try:
        response = supabase.table(TABLE_NAME).select("*").eq("id", record_id).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching record: {e}")
        return None


def fetch_members_for_dropdown() -> list[dict]:
    """Fetch members for dropdown selection."""
    try:
        response = supabase.table("members").select("id, member_name").order("member_name").execute()
        return response.data or []
    except Exception:
        return []


# =============================================================================
# Data Display
# =============================================================================

def display_data_table(data: pd.DataFrame):
    """Display data table with row selection."""
    display_columns = ["vessel_name", "vessel_id_number", "owner_name"]

    column_config = {
        "vessel_name": st.column_config.TextColumn("Vessel Name"),
        "vessel_id_number": st.column_config.TextColumn("Vessel ID"),
        "owner_name": st.column_config.TextColumn("Owner"),
    }

    selection = st.dataframe(
        data[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        on_select="rerun",
        selection_mode="multi-row",
        key="vessels_table",
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
        if st.button("Edit Selected", disabled=edit_disabled, use_container_width=True, key="vessels_edit_btn"):
            st.session_state[f"{TABLE_NAME}_mode"] = "edit"
            st.session_state[f"{TABLE_NAME}_selected_id"] = selected_ids[0]
            st.rerun()

    with col2:
        delete_disabled = len(selected_ids) == 0
        if st.button("Delete Selected", disabled=delete_disabled, use_container_width=True, key="vessels_delete_btn"):
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

    # Fetch members for dropdown
    members = fetch_members_for_dropdown()
    if not members:
        st.warning("No members found. Please add members before adding vessels.")
        return

    member_options = {m["id"]: m["member_name"] for m in members}
    member_ids = list(member_options.keys())

    with st.expander(title, expanded=True):
        with st.form(key="vessels_form"):
            vessel_name = st.text_input(
                "Vessel Name *",
                value=existing.get("vessel_name", ""),
                placeholder="e.g., F/V Northern Light",
                key="vessels_name_input",
            )

            vessel_id_number = st.text_input(
                "Vessel ID (ADF&G) *",
                value=existing.get("vessel_id_number", ""),
                placeholder="e.g., AK-12345",
                key="vessels_id_input",
            )

            # Owner dropdown
            existing_member_id = existing.get("member_id")
            default_index = 0
            if existing_member_id and existing_member_id in member_ids:
                default_index = member_ids.index(existing_member_id)

            selected_member_id = st.selectbox(
                "Owner (Member) *",
                options=member_ids,
                index=default_index,
                format_func=lambda x: member_options.get(x, "Unknown"),
                key="vessels_owner_select",
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
                # Validation
                errors = []
                if not vessel_name:
                    errors.append("Vessel Name is required.")
                if not vessel_id_number:
                    errors.append("Vessel ID is required.")
                if not selected_member_id:
                    errors.append("Owner is required.")

                if errors:
                    for error in errors:
                        st.error(error)
                    return

                record_data = {
                    "vessel_name": vessel_name.strip(),
                    "vessel_id_number": vessel_id_number.strip(),
                    "member_id": selected_member_id,
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
        st.caption("Note: Vessels with associated harvests or assignments cannot be deleted.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", use_container_width=True, type="primary", key="vessels_confirm_delete_btn"):
                success_count = 0
                for record_id in selected_ids:
                    if delete_record(record_id):
                        success_count += 1

                if success_count == count:
                    st.success(f"Deleted {count} {ITEM_NAME}(s).")
                elif success_count > 0:
                    st.warning(f"Deleted {success_count} of {count} {ITEM_NAME}(s). Some could not be deleted due to existing relationships.")
                else:
                    st.error("Could not delete. Vessels may have associated data.")

                st.session_state[f"{TABLE_NAME}_show_delete_dialog"] = False
                reset_mode()
                st.rerun()

        with col2:
            if st.button("Cancel", use_container_width=True, key="vessels_cancel_delete_btn"):
                st.session_state[f"{TABLE_NAME}_show_delete_dialog"] = False
                st.rerun()

    confirm_delete()


# =============================================================================
# CRUD Operations
# =============================================================================

def create_record(data: dict) -> bool:
    """Create a new vessel."""
    try:
        supabase.table(TABLE_NAME).insert(data).execute()
        return True
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower():
            st.error("A vessel with this ID already exists.")
        else:
            st.error(f"Error creating {ITEM_NAME}: {e}")
        return False


def update_record(record_id: str, data: dict) -> bool:
    """Update an existing vessel."""
    try:
        supabase.table(TABLE_NAME).update(data).eq("id", record_id).execute()
        return True
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower():
            st.error("A vessel with this ID already exists.")
        else:
            st.error(f"Error updating {ITEM_NAME}: {e}")
        return False


def delete_record(record_id: str) -> bool:
    """Delete a vessel by ID."""
    try:
        supabase.table(TABLE_NAME).delete().eq("id", record_id).execute()
        return True
    except Exception as e:
        error_msg = str(e)
        if "foreign key" in error_msg.lower():
            st.error("Cannot delete: this vessel has associated data.")
        else:
            st.error(f"Error deleting {ITEM_NAME}: {e}")
        return False
