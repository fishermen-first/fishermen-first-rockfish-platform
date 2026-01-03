"""
Manage LLP Permits - CRUD operations for llp_permits table.
"""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_role

TABLE_NAME = "llp_permits"
PAGE_TITLE = "Manage LLP Permits"
ITEM_NAME = "LLP permit"


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
        if st.button("+ Add LLP Permit", key="llp_permits_add_btn", use_container_width=True):
            st.session_state.llp_permits_mode = "add"
            st.session_state.llp_permits_selected_id = None

    # Filters
    show_filters()

    # Load and display data
    data = fetch_data()

    if data.empty:
        st.info("No LLP permits found. Click 'Add LLP Permit' to create one.")
    else:
        # Apply filters
        filtered_data = apply_filters(data)
        display_data_table(filtered_data)
        show_action_buttons()

    # Show form if in add/edit mode
    if st.session_state.llp_permits_mode in ["add", "edit"]:
        show_form()

    # Delete confirmation dialog
    if st.session_state.llp_permits_show_delete_dialog:
        show_delete_dialog()


def init_session_state():
    """Initialize session state variables for this page."""
    defaults = {
        "llp_permits_mode": "view",
        "llp_permits_selected_id": None,
        "llp_permits_selected_ids": [],
        "llp_permits_show_delete_dialog": False,
        "llp_permits_filter_season": 2026,
        "llp_permits_filter_coop": "All",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_mode():
    """Reset to view mode and clear selections."""
    st.session_state.llp_permits_mode = "view"
    st.session_state.llp_permits_selected_id = None
    st.session_state.llp_permits_selected_ids = []


def show_filters():
    """Display filter controls."""
    cooperatives = fetch_cooperatives_for_dropdown()
    coop_names = ["All"] + [c["cooperative_name"] for c in cooperatives]

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        season_year = st.number_input(
            "Season Year",
            min_value=2020,
            max_value=2100,
            value=st.session_state.llp_permits_filter_season,
            step=1,
            key="llp_permits_filter_season_input",
        )
        st.session_state.llp_permits_filter_season = season_year

    with col2:
        selected_coop = st.selectbox(
            "Cooperative",
            options=coop_names,
            index=coop_names.index(st.session_state.llp_permits_filter_coop) if st.session_state.llp_permits_filter_coop in coop_names else 0,
            key="llp_permits_filter_coop_select",
        )
        st.session_state.llp_permits_filter_coop = selected_coop


def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    """Apply filters to the data."""
    filtered = data.copy()

    # Season filter
    season = st.session_state.llp_permits_filter_season
    if season:
        filtered = filtered[filtered["season_year"] == season]

    # Cooperative filter
    coop = st.session_state.llp_permits_filter_coop
    if coop and coop != "All":
        filtered = filtered[filtered["cooperative_name"] == coop]

    return filtered


def fetch_data() -> pd.DataFrame:
    """Fetch all LLP permits with joined data."""
    try:
        response = supabase.table(TABLE_NAME).select("*").execute()
        if not response.data:
            return pd.DataFrame()

        permits = pd.DataFrame(response.data)

        # Fetch related tables
        cooperatives = fetch_cooperatives_lookup()
        members = fetch_members_lookup()
        vessels = fetch_vessels_lookup()

        # Join data
        permits["cooperative_name"] = permits["cooperative_id"].map(cooperatives).fillna("")
        permits["member_name"] = permits["member_id"].map(members).fillna("")
        permits["vessel_name"] = permits["vessel_id"].map(vessels).fillna("")

        return permits

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


def fetch_cooperatives_lookup() -> dict:
    """Fetch cooperatives as id -> name mapping."""
    try:
        response = supabase.table("cooperatives").select("id, cooperative_name").execute()
        return {c["id"]: c["cooperative_name"] for c in response.data} if response.data else {}
    except Exception:
        return {}


def fetch_members_lookup() -> dict:
    """Fetch members as id -> name mapping."""
    try:
        response = supabase.table("members").select("id, member_name").execute()
        return {m["id"]: m["member_name"] for m in response.data} if response.data else {}
    except Exception:
        return {}


def fetch_vessels_lookup() -> dict:
    """Fetch vessels as id -> name mapping."""
    try:
        response = supabase.table("vessels").select("id, vessel_name").execute()
        return {v["id"]: v["vessel_name"] for v in response.data} if response.data else {}
    except Exception:
        return {}


def fetch_cooperatives_for_dropdown() -> list[dict]:
    """Fetch cooperatives for dropdown selection."""
    try:
        response = supabase.table("cooperatives").select("id, cooperative_name").order("cooperative_name").execute()
        return response.data or []
    except Exception:
        return []


def fetch_members_for_dropdown() -> list[dict]:
    """Fetch members for dropdown selection."""
    try:
        response = supabase.table("members").select("id, member_name").order("member_name").execute()
        return response.data or []
    except Exception:
        return []


def fetch_vessels_for_dropdown() -> list[dict]:
    """Fetch vessels for dropdown selection."""
    try:
        response = supabase.table("vessels").select("id, vessel_name").order("vessel_name").execute()
        return response.data or []
    except Exception:
        return []


def display_data_table(data: pd.DataFrame):
    """Display data table with row selection."""
    if data.empty:
        st.info("No permits match the selected filters.")
        return

    display_columns = ["llp_number", "cooperative_name", "member_name", "vessel_name", "representative_name", "representative_title", "notes", "season_year"]

    # Ensure columns exist
    for col in display_columns:
        if col not in data.columns:
            data[col] = ""

    display_df = data[display_columns].copy()
    display_df = display_df.sort_values(["season_year", "cooperative_name", "llp_number"], ascending=[False, True, True])

    column_config = {
        "llp_number": st.column_config.TextColumn("LLP Number"),
        "cooperative_name": st.column_config.TextColumn("Cooperative"),
        "member_name": st.column_config.TextColumn("Member"),
        "vessel_name": st.column_config.TextColumn("Vessel"),
        "representative_name": st.column_config.TextColumn("Representative"),
        "representative_title": st.column_config.TextColumn("Title"),
        "notes": st.column_config.TextColumn("Notes"),
        "season_year": st.column_config.NumberColumn("Season", format="%d"),
    }

    selection = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        on_select="rerun",
        selection_mode="multi-row",
        key="llp_permits_table",
    )

    if selection and selection.selection.rows:
        selected_indices = selection.selection.rows
        sorted_data = data.sort_values(["season_year", "cooperative_name", "llp_number"], ascending=[False, True, True])
        st.session_state.llp_permits_selected_ids = sorted_data.iloc[selected_indices]["id"].tolist()
    else:
        st.session_state.llp_permits_selected_ids = []


def show_action_buttons():
    """Display Edit and Delete buttons."""
    selected_ids = st.session_state.llp_permits_selected_ids

    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        edit_disabled = len(selected_ids) != 1
        if st.button("Edit", key="llp_permits_edit_btn", disabled=edit_disabled, use_container_width=True):
            st.session_state.llp_permits_mode = "edit"
            st.session_state.llp_permits_selected_id = selected_ids[0]
            st.rerun()

    with col2:
        delete_disabled = len(selected_ids) == 0
        if st.button("Delete", key="llp_permits_delete_btn", disabled=delete_disabled, use_container_width=True):
            st.session_state.llp_permits_show_delete_dialog = True
            st.rerun()


def show_form():
    """Display add/edit form in an expander."""
    mode = st.session_state.llp_permits_mode
    is_edit = mode == "edit"

    existing = {}
    if is_edit:
        existing = fetch_record(st.session_state.llp_permits_selected_id) or {}

    title = "Edit LLP Permit" if is_edit else "Add New LLP Permit"

    # Fetch dropdown options
    cooperatives = fetch_cooperatives_for_dropdown()
    members = fetch_members_for_dropdown()
    vessels = fetch_vessels_for_dropdown()

    with st.expander(title, expanded=True):
        with st.form("llp_permits_form"):
            col1, col2 = st.columns(2)

            with col1:
                llp_number = st.text_input(
                    "LLP Number *",
                    value=existing.get("llp_number", ""),
                    placeholder="e.g., LLP-12345",
                    key="llp_permits_form_number",
                )

                season_year = st.number_input(
                    "Season Year *",
                    min_value=2020,
                    max_value=2100,
                    value=existing.get("season_year", 2026),
                    step=1,
                    key="llp_permits_form_season",
                )

                # Cooperative dropdown
                coop_options = {"": "-- Select --"} | {c["id"]: c["cooperative_name"] for c in cooperatives}
                coop_ids = list(coop_options.keys())

                existing_coop_idx = 0
                if existing.get("cooperative_id") in coop_ids:
                    existing_coop_idx = coop_ids.index(existing["cooperative_id"])

                selected_coop_id = st.selectbox(
                    "Cooperative",
                    options=coop_ids,
                    index=existing_coop_idx,
                    format_func=lambda x: coop_options.get(x, "Unknown"),
                    key="llp_permits_form_coop",
                )

                # Member dropdown
                member_options = {"": "-- Select --"} | {m["id"]: m["member_name"] for m in members}
                member_ids = list(member_options.keys())

                existing_member_idx = 0
                if existing.get("member_id") in member_ids:
                    existing_member_idx = member_ids.index(existing["member_id"])

                selected_member_id = st.selectbox(
                    "Member",
                    options=member_ids,
                    index=existing_member_idx,
                    format_func=lambda x: member_options.get(x, "Unknown"),
                    key="llp_permits_form_member",
                )

            with col2:
                # Vessel dropdown
                vessel_options = {"": "-- Select --"} | {v["id"]: v["vessel_name"] for v in vessels}
                vessel_ids = list(vessel_options.keys())

                existing_vessel_idx = 0
                if existing.get("vessel_id") in vessel_ids:
                    existing_vessel_idx = vessel_ids.index(existing["vessel_id"])

                selected_vessel_id = st.selectbox(
                    "Vessel",
                    options=vessel_ids,
                    index=existing_vessel_idx,
                    format_func=lambda x: vessel_options.get(x, "Unknown"),
                    key="llp_permits_form_vessel",
                )

                representative_name = st.text_input(
                    "Representative Name",
                    value=existing.get("representative_name", ""),
                    key="llp_permits_form_rep_name",
                )

                representative_title = st.text_input(
                    "Representative Title",
                    value=existing.get("representative_title", ""),
                    key="llp_permits_form_rep_title",
                )

            notes = st.text_area(
                "Notes",
                value=existing.get("notes", ""),
                key="llp_permits_form_notes",
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
                if not llp_number:
                    st.error("LLP Number is required.")
                    return

                record_data = {
                    "llp_number": llp_number.strip(),
                    "season_year": season_year,
                    "cooperative_id": selected_coop_id if selected_coop_id else None,
                    "member_id": selected_member_id if selected_member_id else None,
                    "vessel_id": selected_vessel_id if selected_vessel_id else None,
                    "representative_name": representative_name.strip() if representative_name else None,
                    "representative_title": representative_title.strip() if representative_title else None,
                    "notes": notes.strip() if notes else None,
                }

                if is_edit:
                    success = update_record(st.session_state.llp_permits_selected_id, record_data)
                else:
                    success = create_record(record_data)

                if success:
                    st.success(f"LLP permit {'updated' if is_edit else 'created'} successfully!")
                    reset_mode()
                    st.rerun()


def show_delete_dialog():
    """Display delete confirmation dialog."""
    selected_ids = st.session_state.llp_permits_selected_ids
    count = len(selected_ids)

    @st.dialog("Delete LLP Permit(s)")
    def confirm_delete():
        st.warning(f"Are you sure you want to delete {count} LLP permit(s)? This cannot be undone.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", key="llp_permits_confirm_delete", use_container_width=True, type="primary"):
                success_count = 0
                for record_id in selected_ids:
                    if delete_record(record_id):
                        success_count += 1

                if success_count == count:
                    st.success(f"Deleted {count} LLP permit(s).")
                else:
                    st.warning(f"Deleted {success_count} of {count} LLP permit(s).")

                st.session_state.llp_permits_show_delete_dialog = False
                reset_mode()
                st.rerun()

        with col2:
            if st.button("Cancel", key="llp_permits_cancel_delete", use_container_width=True):
                st.session_state.llp_permits_show_delete_dialog = False
                st.rerun()

    confirm_delete()


def create_record(data: dict) -> bool:
    """Create a new record."""
    try:
        supabase.table(TABLE_NAME).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error creating LLP permit: {e}")
        return False


def update_record(record_id: str, data: dict) -> bool:
    """Update an existing record."""
    try:
        supabase.table(TABLE_NAME).update(data).eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating LLP permit: {e}")
        return False


def delete_record(record_id: str) -> bool:
    """Delete a record by ID."""
    try:
        supabase.table(TABLE_NAME).delete().eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting LLP permit: {e}")
        return False
