"""
Manage Quota Allocations - CRUD operations for quota_allocations table.
"""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_role

TABLE_NAME = "quota_allocations"
PAGE_TITLE = "Manage Quota Allocations"
ITEM_NAME = "quota allocation"


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
        if st.button("+ Add Quota", key="quotas_add_btn", use_container_width=True):
            st.session_state.quotas_mode = "add"
            st.session_state.quotas_selected_id = None

    # Load and display data
    data = fetch_data()

    if data.empty:
        st.info("No quota allocations found. Click 'Add Quota' to create one.")
    else:
        display_data_table(data)
        show_action_buttons()

    # Show form if in add/edit mode
    if st.session_state.quotas_mode in ["add", "edit"]:
        show_form()

    # Delete confirmation dialog
    if st.session_state.quotas_show_delete_dialog:
        show_delete_dialog()


def init_session_state():
    """Initialize session state variables for this page."""
    defaults = {
        "quotas_mode": "view",
        "quotas_selected_id": None,
        "quotas_selected_ids": [],
        "quotas_show_delete_dialog": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_mode():
    """Reset to view mode and clear selections."""
    st.session_state.quotas_mode = "view"
    st.session_state.quotas_selected_id = None
    st.session_state.quotas_selected_ids = []


def fetch_data() -> pd.DataFrame:
    """Fetch all quota allocations with joined data."""
    try:
        response = supabase.table(TABLE_NAME).select("*").execute()
        if not response.data:
            return pd.DataFrame()

        quotas = pd.DataFrame(response.data)

        # Fetch related tables
        seasons = fetch_seasons_lookup()
        cooperatives = fetch_cooperatives_lookup()
        species = fetch_species_lookup()

        # Join data
        quotas["season_year"] = quotas["season_id"].map(seasons).fillna("Unknown")
        quotas["cooperative_name"] = quotas["cooperative_id"].map(cooperatives).fillna("Unknown")
        quotas["species_name"] = quotas["species_id"].map(species).fillna("Unknown")

        return quotas

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


def fetch_seasons_lookup() -> dict:
    """Fetch seasons as id -> year mapping."""
    try:
        response = supabase.table("seasons").select("id, year").execute()
        return {s["id"]: s["year"] for s in response.data} if response.data else {}
    except Exception:
        return {}


def fetch_cooperatives_lookup() -> dict:
    """Fetch cooperatives as id -> name mapping."""
    try:
        response = supabase.table("cooperatives").select("id, cooperative_name").execute()
        return {c["id"]: c["cooperative_name"] for c in response.data} if response.data else {}
    except Exception:
        return {}


def fetch_species_lookup() -> dict:
    """Fetch species as id -> name mapping."""
    try:
        response = supabase.table("species").select("id, species_name").execute()
        return {s["id"]: s["species_name"] for s in response.data} if response.data else {}
    except Exception:
        return {}


def fetch_seasons_for_dropdown() -> list[dict]:
    """Fetch seasons for dropdown selection."""
    try:
        response = supabase.table("seasons").select("id, year").order("year", desc=True).execute()
        return response.data or []
    except Exception:
        return []


def fetch_cooperatives_for_dropdown() -> list[dict]:
    """Fetch cooperatives for dropdown selection."""
    try:
        response = supabase.table("cooperatives").select("id, cooperative_name").order("cooperative_name").execute()
        return response.data or []
    except Exception:
        return []


def fetch_species_for_dropdown() -> list[dict]:
    """Fetch species for dropdown selection."""
    try:
        response = supabase.table("species").select("id, species_name").order("species_name").execute()
        return response.data or []
    except Exception:
        return []


def display_data_table(data: pd.DataFrame):
    """Display data table with row selection."""
    display_columns = ["season_year", "cooperative_name", "species_name", "amount"]

    display_df = data[display_columns].copy()
    display_df = display_df.sort_values(["season_year", "cooperative_name", "species_name"], ascending=[False, True, True])

    column_config = {
        "season_year": st.column_config.NumberColumn("Season", format="%d"),
        "cooperative_name": st.column_config.TextColumn("Cooperative"),
        "species_name": st.column_config.TextColumn("Species"),
        "amount": st.column_config.NumberColumn("Allocated (lbs)", format="%.0f"),
    }

    selection = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        on_select="rerun",
        selection_mode="multi-row",
        key="quotas_table",
    )

    if selection and selection.selection.rows:
        selected_indices = selection.selection.rows
        # Map back to original data indices
        sorted_data = data.sort_values(["season_year", "cooperative_name", "species_name"], ascending=[False, True, True])
        st.session_state.quotas_selected_ids = sorted_data.iloc[selected_indices]["id"].tolist()
    else:
        st.session_state.quotas_selected_ids = []


def show_action_buttons():
    """Display Edit and Delete buttons."""
    selected_ids = st.session_state.quotas_selected_ids

    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        edit_disabled = len(selected_ids) != 1
        if st.button("Edit", key="quotas_edit_btn", disabled=edit_disabled, use_container_width=True):
            st.session_state.quotas_mode = "edit"
            st.session_state.quotas_selected_id = selected_ids[0]
            st.rerun()

    with col2:
        delete_disabled = len(selected_ids) == 0
        if st.button("Delete", key="quotas_delete_btn", disabled=delete_disabled, use_container_width=True):
            st.session_state.quotas_show_delete_dialog = True
            st.rerun()


def show_form():
    """Display add/edit form in an expander."""
    mode = st.session_state.quotas_mode
    is_edit = mode == "edit"

    existing = {}
    if is_edit:
        existing = fetch_record(st.session_state.quotas_selected_id) or {}

    title = "Edit Quota Allocation" if is_edit else "Add New Quota Allocation"

    # Fetch dropdown options
    seasons = fetch_seasons_for_dropdown()
    cooperatives = fetch_cooperatives_for_dropdown()
    species = fetch_species_for_dropdown()

    if not seasons:
        st.warning("No seasons found. Please add a season first.")
        return
    if not cooperatives:
        st.warning("No cooperatives found. Please add a cooperative first.")
        return
    if not species:
        st.warning("No species found. Please add species first.")
        return

    with st.expander(title, expanded=True):
        with st.form("quotas_form"):
            # Season dropdown
            season_options = {s["id"]: s["year"] for s in seasons}
            season_ids = list(season_options.keys())

            existing_season_idx = 0
            if existing.get("season_id") in season_ids:
                existing_season_idx = season_ids.index(existing["season_id"])

            selected_season_id = st.selectbox(
                "Season *",
                options=season_ids,
                index=existing_season_idx,
                format_func=lambda x: str(season_options.get(x, "Unknown")),
                key="quotas_form_season",
            )

            # Cooperative dropdown
            coop_options = {c["id"]: c["cooperative_name"] for c in cooperatives}
            coop_ids = list(coop_options.keys())

            existing_coop_idx = 0
            if existing.get("cooperative_id") in coop_ids:
                existing_coop_idx = coop_ids.index(existing["cooperative_id"])

            selected_coop_id = st.selectbox(
                "Cooperative *",
                options=coop_ids,
                index=existing_coop_idx,
                format_func=lambda x: coop_options.get(x, "Unknown"),
                key="quotas_form_coop",
            )

            # Species dropdown
            species_options = {s["id"]: s["species_name"] for s in species}
            species_ids = list(species_options.keys())

            existing_species_idx = 0
            if existing.get("species_id") in species_ids:
                existing_species_idx = species_ids.index(existing["species_id"])

            selected_species_id = st.selectbox(
                "Species *",
                options=species_ids,
                index=existing_species_idx,
                format_func=lambda x: species_options.get(x, "Unknown"),
                key="quotas_form_species",
            )

            # Amount
            amount = st.number_input(
                "Allocated Amount (lbs) *",
                min_value=0.0,
                value=float(existing.get("amount", 0)),
                step=1000.0,
                format="%.0f",
                key="quotas_form_amount",
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
                if amount <= 0:
                    st.error("Allocated Amount must be greater than 0.")
                    return

                record_data = {
                    "season_id": selected_season_id,
                    "cooperative_id": selected_coop_id,
                    "species_id": selected_species_id,
                    "amount": amount,
                }

                if is_edit:
                    success = update_record(st.session_state.quotas_selected_id, record_data)
                else:
                    success = create_record(record_data)

                if success:
                    st.success(f"Quota allocation {'updated' if is_edit else 'created'} successfully!")
                    reset_mode()
                    st.rerun()


def show_delete_dialog():
    """Display delete confirmation dialog."""
    selected_ids = st.session_state.quotas_selected_ids
    count = len(selected_ids)

    @st.dialog("Delete Quota Allocation(s)")
    def confirm_delete():
        st.warning(f"Are you sure you want to delete {count} quota allocation(s)? This cannot be undone.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", key="quotas_confirm_delete", use_container_width=True, type="primary"):
                success_count = 0
                for record_id in selected_ids:
                    if delete_record(record_id):
                        success_count += 1

                if success_count == count:
                    st.success(f"Deleted {count} quota allocation(s).")
                else:
                    st.warning(f"Deleted {success_count} of {count} quota allocation(s).")

                st.session_state.quotas_show_delete_dialog = False
                reset_mode()
                st.rerun()

        with col2:
            if st.button("Cancel", key="quotas_cancel_delete", use_container_width=True):
                st.session_state.quotas_show_delete_dialog = False
                st.rerun()

    confirm_delete()


def create_record(data: dict) -> bool:
    """Create a new record."""
    try:
        supabase.table(TABLE_NAME).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error creating quota allocation: {e}")
        return False


def update_record(record_id: str, data: dict) -> bool:
    """Update an existing record."""
    try:
        supabase.table(TABLE_NAME).update(data).eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating quota allocation: {e}")
        return False


def delete_record(record_id: str) -> bool:
    """Delete a record by ID."""
    try:
        supabase.table(TABLE_NAME).delete().eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting quota allocation: {e}")
        return False
