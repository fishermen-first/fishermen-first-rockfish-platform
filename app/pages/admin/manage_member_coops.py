"""
Manage Member-Cooperative Assignments - Admin CRUD page for cooperative_memberships table.
Historical tracking table with effective_from/effective_to dates.
"""

import streamlit as st
import pandas as pd
from datetime import date
from app.config import supabase
from app.auth import require_role

# Table and display configuration
TABLE_NAME = "cooperative_memberships"
PAGE_TITLE = "Member-Cooperative Assignments"
ITEM_NAME = "assignment"


def show():
    """Main entry point for the page."""
    if not require_role("admin"):
        st.stop()

    init_session_state()

    st.subheader(PAGE_TITLE)

    # Header with Add button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button(f"+ Add {ITEM_NAME.title()}", use_container_width=True, key="member_coops_add_btn"):
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
        show_form()

    # End assignment confirmation dialog
    if st.session_state[f"{TABLE_NAME}_show_end_dialog"]:
        show_end_dialog()


# =============================================================================
# Session State
# =============================================================================

def init_session_state():
    """Initialize session state variables for this page."""
    defaults = {
        f"{TABLE_NAME}_mode": "view",
        f"{TABLE_NAME}_selected_id": None,
        f"{TABLE_NAME}_selected_ids": [],
        f"{TABLE_NAME}_show_end_dialog": False,
        f"{TABLE_NAME}_show_historical": False,
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
    """Fetch all assignments with member and cooperative names."""
    try:
        response = supabase.table(TABLE_NAME).select("*").order("effective_from", desc=True).execute()
        if not response.data:
            return pd.DataFrame()

        assignments = pd.DataFrame(response.data)

        # Get member names
        member_response = supabase.table("members").select("id, member_name").execute()
        member_names = {}
        if member_response.data:
            member_names = {m["id"]: m["member_name"] for m in member_response.data}

        # Get cooperative names
        coop_response = supabase.table("cooperatives").select("id, cooperative_name").execute()
        coop_names = {}
        if coop_response.data:
            coop_names = {c["id"]: c["cooperative_name"] for c in coop_response.data}

        # Add display names
        assignments["member_name"] = assignments["member_id"].map(member_names)
        assignments["cooperative_name"] = assignments["cooperative_id"].map(coop_names)

        # Add status column
        assignments["status"] = assignments["effective_to"].apply(
            lambda x: "Current" if pd.isna(x) or x is None else "Historical"
        )

        return assignments

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()


def fetch_record(record_id: str) -> dict | None:
    """Fetch a single assignment by ID."""
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


def fetch_coops_for_dropdown() -> list[dict]:
    """Fetch cooperatives for dropdown selection."""
    try:
        response = supabase.table("cooperatives").select("id, cooperative_name").order("cooperative_name").execute()
        return response.data or []
    except Exception:
        return []


# =============================================================================
# Data Display
# =============================================================================

def display_data_table(data: pd.DataFrame):
    """Display data table with current/historical filter."""
    # Filter toggle
    show_historical = st.toggle(
        "Show historical assignments",
        value=st.session_state[f"{TABLE_NAME}_show_historical"],
        key="member_coops_show_historical_toggle",
    )
    st.session_state[f"{TABLE_NAME}_show_historical"] = show_historical

    # Filter data
    if not show_historical:
        filtered_data = data[data["status"] == "Current"].copy()
    else:
        filtered_data = data.copy()

    if filtered_data.empty:
        if show_historical:
            st.info("No assignments found.")
        else:
            st.info("No current assignments. Toggle 'Show historical' to see past assignments.")
        return

    display_columns = ["member_name", "cooperative_name", "effective_from", "effective_to", "status"]

    column_config = {
        "member_name": st.column_config.TextColumn("Member"),
        "cooperative_name": st.column_config.TextColumn("Cooperative"),
        "effective_from": st.column_config.DateColumn("From"),
        "effective_to": st.column_config.DateColumn("To"),
        "status": st.column_config.TextColumn("Status"),
    }

    selection = st.dataframe(
        filtered_data[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        on_select="rerun",
        selection_mode="single-row",
        key="member_coops_table",
    )

    if selection and selection.selection.rows:
        selected_indices = selection.selection.rows
        st.session_state[f"{TABLE_NAME}_selected_ids"] = filtered_data.iloc[selected_indices]["id"].tolist()
    else:
        st.session_state[f"{TABLE_NAME}_selected_ids"] = []


def show_action_buttons():
    """Display Edit and End Assignment buttons."""
    selected_ids = st.session_state[f"{TABLE_NAME}_selected_ids"]

    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        edit_disabled = len(selected_ids) != 1
        if st.button("Edit Selected", disabled=edit_disabled, use_container_width=True, key="member_coops_edit_btn"):
            st.session_state[f"{TABLE_NAME}_mode"] = "edit"
            st.session_state[f"{TABLE_NAME}_selected_id"] = selected_ids[0]
            st.rerun()

    with col2:
        end_disabled = len(selected_ids) != 1
        if st.button("End Assignment", disabled=end_disabled, use_container_width=True, key="member_coops_end_btn"):
            # Check if assignment is already ended
            if selected_ids:
                record = fetch_record(selected_ids[0])
                if record and record.get("effective_to") is not None:
                    st.warning("This assignment has already ended.")
                else:
                    st.session_state[f"{TABLE_NAME}_show_end_dialog"] = True
                    st.rerun()


# =============================================================================
# Add/Edit Form
# =============================================================================

def show_form():
    """Display add/edit form in an expander."""
    mode = st.session_state[f"{TABLE_NAME}_mode"]
    is_edit = mode == "edit"

    existing = {}
    if is_edit:
        existing = fetch_record(st.session_state[f"{TABLE_NAME}_selected_id"]) or {}

    title = f"Edit {ITEM_NAME.title()}" if is_edit else f"Add New {ITEM_NAME.title()}"

    # Fetch dropdown options
    members = fetch_members_for_dropdown()
    coops = fetch_coops_for_dropdown()

    if not members:
        st.warning("No members found. Please add members first.")
        return
    if not coops:
        st.warning("No cooperatives found. Please add cooperatives first.")
        return

    member_options = {m["id"]: m["member_name"] for m in members}
    member_ids = list(member_options.keys())

    coop_options = {c["id"]: c["cooperative_name"] for c in coops}
    coop_ids = list(coop_options.keys())

    with st.expander(title, expanded=True):
        with st.form(key="member_coops_form"):
            # Member dropdown
            existing_member_id = existing.get("member_id")
            member_default_index = 0
            if existing_member_id and existing_member_id in member_ids:
                member_default_index = member_ids.index(existing_member_id)

            selected_member_id = st.selectbox(
                "Member *",
                options=member_ids,
                index=member_default_index,
                format_func=lambda x: member_options.get(x, "Unknown"),
                key="member_coops_member_select",
            )

            # Cooperative dropdown
            existing_coop_id = existing.get("cooperative_id")
            coop_default_index = 0
            if existing_coop_id and existing_coop_id in coop_ids:
                coop_default_index = coop_ids.index(existing_coop_id)

            selected_coop_id = st.selectbox(
                "Cooperative *",
                options=coop_ids,
                index=coop_default_index,
                format_func=lambda x: coop_options.get(x, "Unknown"),
                key="member_coops_coop_select",
            )

            # Date fields
            col1, col2 = st.columns(2)
            with col1:
                existing_from = existing.get("effective_from")
                if existing_from:
                    if isinstance(existing_from, str):
                        existing_from = date.fromisoformat(existing_from)
                else:
                    existing_from = date.today()

                effective_from = st.date_input(
                    "Effective From *",
                    value=existing_from,
                    key="member_coops_from_date",
                )

            with col2:
                existing_to = existing.get("effective_to")
                if existing_to:
                    if isinstance(existing_to, str):
                        existing_to = date.fromisoformat(existing_to)
                else:
                    existing_to = None

                effective_to = st.date_input(
                    "Effective To (blank if current)",
                    value=existing_to,
                    key="member_coops_to_date",
                )

            # Form buttons
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                submitted = st.form_submit_button(
                    "Save" if is_edit else "Create",
                    use_container_width=True,
                    type="primary"
                )
            with btn_col2:
                cancelled = st.form_submit_button("Cancel", use_container_width=True)

            if cancelled:
                reset_mode()
                st.rerun()

            if submitted:
                # Validation
                errors = []
                if not selected_member_id:
                    errors.append("Member is required.")
                if not selected_coop_id:
                    errors.append("Cooperative is required.")
                if not effective_from:
                    errors.append("Effective From date is required.")
                if effective_to and effective_from and effective_to < effective_from:
                    errors.append("Effective To must be after Effective From.")

                if errors:
                    for error in errors:
                        st.error(error)
                    return

                record_data = {
                    "member_id": selected_member_id,
                    "cooperative_id": selected_coop_id,
                    "effective_from": effective_from.isoformat(),
                    "effective_to": effective_to.isoformat() if effective_to else None,
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
# End Assignment Dialog
# =============================================================================

def show_end_dialog():
    """Display end assignment confirmation dialog."""
    selected_ids = st.session_state[f"{TABLE_NAME}_selected_ids"]

    @st.dialog("End Assignment")
    def confirm_end():
        st.warning("This will end the current assignment by setting today as the end date.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, End Assignment", use_container_width=True, type="primary", key="member_coops_confirm_end_btn"):
                if selected_ids:
                    success = end_assignment(selected_ids[0])
                    if success:
                        st.success("Assignment ended.")
                        st.session_state[f"{TABLE_NAME}_show_end_dialog"] = False
                        reset_mode()
                        st.rerun()

        with col2:
            if st.button("Cancel", use_container_width=True, key="member_coops_cancel_end_btn"):
                st.session_state[f"{TABLE_NAME}_show_end_dialog"] = False
                st.rerun()

    confirm_end()


# =============================================================================
# CRUD Operations
# =============================================================================

def create_record(data: dict) -> bool:
    """Create a new assignment."""
    try:
        supabase.table(TABLE_NAME).insert(data).execute()
        return True
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower():
            st.error("This member-cooperative assignment already exists.")
        else:
            st.error(f"Error creating {ITEM_NAME}: {e}")
        return False


def update_record(record_id: str, data: dict) -> bool:
    """Update an existing assignment."""
    try:
        supabase.table(TABLE_NAME).update(data).eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating {ITEM_NAME}: {e}")
        return False


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
