"""
Quota Transfers page - Record and view quota transfers between cooperatives.
"""

import streamlit as st
import pandas as pd
from datetime import date
from app.config import supabase
from app.auth import require_auth, handle_jwt_error


def show():
    """Display the quota transfers page."""
    if not require_auth():
        st.stop()

    st.title("Quota Transfers")

    # New transfer form
    show_transfer_form()

    st.divider()

    # Recent transfers
    show_recent_transfers()


def show_transfer_form():
    """Display form to record a new transfer."""
    st.subheader("Record New Transfer")

    # Fetch dropdown data
    seasons = fetch_seasons()
    cooperatives = fetch_cooperatives()
    species = fetch_species()

    if not seasons:
        st.warning("No seasons found. Please add a season first.")
        return
    if not cooperatives or len(cooperatives) < 2:
        st.warning("Need at least 2 cooperatives to record transfers.")
        return
    if not species:
        st.warning("No species found. Please add species first.")
        return

    with st.form("transfers_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            # Season dropdown
            season_options = {s["id"]: s["year"] for s in seasons}
            season_ids = list(season_options.keys())
            selected_season_id = st.selectbox(
                "Season *",
                options=season_ids,
                format_func=lambda x: str(season_options.get(x, "Unknown")),
                key="transfers_form_season",
            )

            # From Cooperative
            coop_options = {c["id"]: c["cooperative_name"] for c in cooperatives}
            coop_ids = list(coop_options.keys())
            from_coop_id = st.selectbox(
                "From Cooperative *",
                options=coop_ids,
                format_func=lambda x: coop_options.get(x, "Unknown"),
                key="transfers_form_from_coop",
            )

            # Species
            species_options = {s["id"]: s["species_name"] for s in species}
            species_ids = list(species_options.keys())
            selected_species_id = st.selectbox(
                "Species *",
                options=species_ids,
                format_func=lambda x: species_options.get(x, "Unknown"),
                key="transfers_form_species",
            )

        with col2:
            # Transfer Date
            transfer_date = st.date_input(
                "Transfer Date *",
                value=date.today(),
                key="transfers_form_date",
            )

            # To Cooperative (exclude "from" selection)
            to_coop_ids = [cid for cid in coop_ids if cid != from_coop_id]
            to_coop_id = st.selectbox(
                "To Cooperative *",
                options=to_coop_ids if to_coop_ids else coop_ids,
                format_func=lambda x: coop_options.get(x, "Unknown"),
                key="transfers_form_to_coop",
            )

            # Amount
            amount = st.number_input(
                "Amount (lbs) *",
                min_value=0.0,
                value=0.0,
                step=1000.0,
                format="%.0f",
                key="transfers_form_amount",
            )

        # Notes (full width)
        notes = st.text_area(
            "Notes (optional)",
            placeholder="Reason for transfer, agreement details, etc.",
            key="transfers_form_notes",
        )

        submitted = st.form_submit_button("Record Transfer", type="primary", use_container_width=True)

        if submitted:
            # Validation
            if from_coop_id == to_coop_id:
                st.error("From and To cooperatives must be different.")
                return
            if amount <= 0:
                st.error("Amount must be greater than 0.")
                return

            # Create transfer record
            transfer_data = {
                "season_id": selected_season_id,
                "from_cooperative_id": from_coop_id,
                "to_cooperative_id": to_coop_id,
                "species_id": selected_species_id,
                "amount": amount,
                "transfer_date": transfer_date.isoformat(),
                "notes": notes.strip() if notes else None,
            }

            success = create_transfer(transfer_data)
            if success:
                from_name = coop_options.get(from_coop_id, "Unknown")
                to_name = coop_options.get(to_coop_id, "Unknown")
                species_name = species_options.get(selected_species_id, "Unknown")
                st.success(f"Transfer recorded: {amount:,.0f} lbs of {species_name} from {from_name} to {to_name}")
                st.rerun()


def show_recent_transfers():
    """Display list of recent transfers."""
    st.subheader("Recent Transfers")

    transfers = fetch_transfers()

    if not transfers:
        st.info("No transfers recorded yet.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(transfers)

    # Format for display
    display_columns = ["transfer_date", "from_coop_name", "to_coop_name", "species_name", "amount"]
    if "notes" in df.columns:
        df["notes"] = df["notes"].fillna("")
        display_columns.append("notes")

    display_df = df[display_columns].copy()
    display_df = display_df.sort_values("transfer_date", ascending=False)

    column_config = {
        "transfer_date": st.column_config.DateColumn("Date"),
        "from_coop_name": st.column_config.TextColumn("From Co-op"),
        "to_coop_name": st.column_config.TextColumn("To Co-op"),
        "species_name": st.column_config.TextColumn("Species"),
        "amount": st.column_config.NumberColumn("Amount (lbs)", format="%.0f"),
    }
    if "notes" in display_columns:
        column_config["notes"] = st.column_config.TextColumn("Notes")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        key="transfers_table",
    )

    # Show total transferred
    total = df["amount"].sum()
    st.caption(f"Total transferred: {total:,.0f} lbs across {len(df)} transfers")


# =============================================================================
# Data Operations
# =============================================================================

def create_transfer(data: dict) -> bool:
    """Create a new transfer record."""
    try:
        supabase.table("quota_transfers").insert(data).execute()
        return True
    except Exception as e:
        if handle_jwt_error(e):
            st.rerun()
        st.error(f"Error recording transfer: {e}")
        return False


def fetch_transfers(limit: int = 50) -> list[dict]:
    """Fetch recent transfers with joined data."""
    try:
        response = supabase.table("quota_transfers").select("*").order("transfer_date", desc=True).limit(limit).execute()
        if not response.data:
            return []

        transfers = response.data

        # Get lookup data
        cooperatives = fetch_cooperatives_lookup()
        species = fetch_species_lookup()

        # Add names
        for t in transfers:
            t["from_coop_name"] = cooperatives.get(t.get("from_cooperative_id"), "N/A")
            t["to_coop_name"] = cooperatives.get(t.get("to_cooperative_id"), "N/A")
            t["species_name"] = species.get(t.get("species_id"), "Unknown")

        return transfers

    except Exception as e:
        if handle_jwt_error(e):
            st.rerun()
        return []


def fetch_seasons() -> list[dict]:
    """Fetch all seasons, ordered by year descending."""
    try:
        response = supabase.table("seasons").select("id, year").order("year", desc=True).execute()
        return response.data or []
    except Exception as e:
        if handle_jwt_error(e):
            st.rerun()
        return []


def fetch_cooperatives() -> list[dict]:
    """Fetch all cooperatives."""
    try:
        response = supabase.table("cooperatives").select("id, cooperative_name").order("cooperative_name").execute()
        return response.data or []
    except Exception as e:
        if handle_jwt_error(e):
            st.rerun()
        return []


def fetch_species() -> list[dict]:
    """Fetch all species."""
    try:
        response = supabase.table("species").select("id, species_name").order("species_name").execute()
        return response.data or []
    except Exception as e:
        if handle_jwt_error(e):
            st.rerun()
        return []


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
