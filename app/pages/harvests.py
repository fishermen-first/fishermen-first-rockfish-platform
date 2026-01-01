"""
Harvests page - View harvest records with filters.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from app.config import supabase
from app.auth import require_auth


def show():
    """Display the harvests page."""
    if not require_auth():
        st.stop()

    st.title("Harvest Data")

    # Filters
    show_filters()

    st.divider()

    # Load and display data
    data = fetch_harvests()

    if data.empty:
        st.info("No harvest records found.")
        return

    # Apply filters
    filtered_data = apply_filters(data)

    # Display table
    display_harvests_table(filtered_data)

    # Show totals
    show_totals(filtered_data)


def show_filters():
    """Display filter controls."""
    # Initialize filter state
    if "harvests_date_from" not in st.session_state:
        st.session_state.harvests_date_from = date.today() - timedelta(days=30)
    if "harvests_date_to" not in st.session_state:
        st.session_state.harvests_date_to = date.today()

    # Fetch dropdown options
    vessels = fetch_vessels()
    species = fetch_species()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        date_from = st.date_input(
            "From Date",
            value=st.session_state.harvests_date_from,
            key="harvests_filter_date_from",
        )
        st.session_state.harvests_date_from = date_from

    with col2:
        date_to = st.date_input(
            "To Date",
            value=st.session_state.harvests_date_to,
            key="harvests_filter_date_to",
        )
        st.session_state.harvests_date_to = date_to

    with col3:
        vessel_options = ["All Vessels"] + [v["vessel_name"] for v in vessels]
        selected_vessel = st.selectbox(
            "Vessel",
            options=vessel_options,
            key="harvests_filter_vessel",
        )

    with col4:
        species_options = ["All Species"] + [s["species_name"] for s in species]
        selected_species = st.selectbox(
            "Species",
            options=species_options,
            key="harvests_filter_species",
        )


def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    """Apply filters to the data."""
    filtered = data.copy()

    # Date range filter
    date_from = st.session_state.get("harvests_date_from")
    date_to = st.session_state.get("harvests_date_to")

    if date_from:
        filtered = filtered[filtered["landed_date"] >= str(date_from)]
    if date_to:
        filtered = filtered[filtered["landed_date"] <= str(date_to)]

    # Vessel filter
    selected_vessel = st.session_state.get("harvests_filter_vessel", "All Vessels")
    if selected_vessel and selected_vessel != "All Vessels":
        filtered = filtered[filtered["vessel_name"] == selected_vessel]

    # Species filter
    selected_species = st.session_state.get("harvests_filter_species", "All Species")
    if selected_species and selected_species != "All Species":
        filtered = filtered[filtered["species_name"] == selected_species]

    return filtered


def display_harvests_table(data: pd.DataFrame):
    """Display the harvests table."""
    if data.empty:
        st.info("No records match the selected filters.")
        return

    st.subheader(f"Harvest Records ({len(data)} records)")

    display_df = data[["landed_date", "vessel_name", "species_name", "amount", "processor_name"]].copy()
    display_df = display_df.sort_values("landed_date", ascending=False)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "landed_date": st.column_config.DateColumn("Landed Date"),
            "vessel_name": st.column_config.TextColumn("Vessel"),
            "species_name": st.column_config.TextColumn("Species"),
            "amount": st.column_config.NumberColumn("Amount (lbs)", format="%.0f"),
            "processor_name": st.column_config.TextColumn("Processor"),
        },
        key="harvests_table",
    )


def show_totals(data: pd.DataFrame):
    """Display totals summary."""
    if data.empty:
        return

    st.subheader("Totals")

    # Overall total
    total_lbs = data["amount"].sum()

    # By species
    by_species = data.groupby("species_name")["amount"].sum().sort_values(ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Harvest", f"{total_lbs:,.0f} lbs")

    with col2:
        st.write("**By Species:**")
        for species_name, amount in by_species.items():
            st.write(f"- {species_name}: {amount:,.0f} lbs")


def fetch_harvests() -> pd.DataFrame:
    """Fetch all harvests with joined data."""
    try:
        # Fetch harvests
        response = supabase.table("harvests").select("*").execute()
        if not response.data:
            return pd.DataFrame()

        harvests = pd.DataFrame(response.data)

        # Fetch vessels
        vessels_response = supabase.table("vessels").select("id, vessel_name").execute()
        vessels = {v["id"]: v["vessel_name"] for v in vessels_response.data} if vessels_response.data else {}

        # Fetch species
        species_response = supabase.table("species").select("id, species_name").execute()
        species = {s["id"]: s["species_name"] for s in species_response.data} if species_response.data else {}

        # Fetch processors
        processors_response = supabase.table("processors").select("id, processor_name").execute()
        processors = {p["id"]: p["processor_name"] for p in processors_response.data} if processors_response.data else {}

        # Join data
        harvests["vessel_name"] = harvests["vessel_id"].map(vessels).fillna("Unknown")
        harvests["species_name"] = harvests["species_id"].map(species).fillna("Unknown")
        harvests["processor_name"] = harvests["processor_id"].map(processors).fillna("N/A")

        return harvests

    except Exception as e:
        st.error(f"Error fetching harvests: {e}")
        return pd.DataFrame()


def fetch_vessels() -> list[dict]:
    """Fetch vessels for dropdown."""
    try:
        response = supabase.table("vessels").select("id, vessel_name").order("vessel_name").execute()
        return response.data or []
    except Exception:
        return []


def fetch_species() -> list[dict]:
    """Fetch species for dropdown."""
    try:
        response = supabase.table("species").select("id, species_name").order("species_name").execute()
        return response.data or []
    except Exception:
        return []
