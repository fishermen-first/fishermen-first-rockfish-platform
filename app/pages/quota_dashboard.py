"""
Quota Dashboard - View quota allocations vs harvests by cooperative and species.
"""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_auth, handle_jwt_error


def show():
    """Display the quota dashboard."""
    if not require_auth():
        st.stop()

    st.title("Quota Management")

    # Season selector
    seasons = fetch_seasons()
    if not seasons:
        st.warning("No seasons found. Please add a season in Admin Settings.")
        return

    selected_season = show_season_selector(seasons)
    if not selected_season:
        return

    season_id = selected_season["id"]
    season_year = selected_season["year"]

    st.divider()

    # Fetch data
    quotas = fetch_quotas(season_id)
    harvests = fetch_harvests(season_id)

    if quotas.empty:
        st.info(f"No quota allocations found for {season_year}. Add quotas in Admin Settings → Quota Allocations.")
        return

    # Build summary data
    summary_data = build_summary_data(quotas, harvests)

    # Summary cards
    show_summary_cards(summary_data)

    st.divider()

    # Detailed table
    show_quota_table(summary_data)

    st.divider()

    # Bar chart
    show_quota_chart(summary_data)


def show_season_selector(seasons: list[dict]) -> dict | None:
    """Display season selector dropdown."""
    season_options = {s["id"]: s["year"] for s in seasons}
    season_ids = list(season_options.keys())

    # Default to most recent season
    if "quota_dash_season" not in st.session_state:
        st.session_state.quota_dash_season = season_ids[0]

    col1, col2 = st.columns([1, 3])
    with col1:
        selected_id = st.selectbox(
            "Season",
            options=season_ids,
            format_func=lambda x: str(season_options.get(x, "Unknown")),
            key="quota_dash_season_select",
        )

    # Find and return selected season
    for s in seasons:
        if s["id"] == selected_id:
            return s
    return None


def build_summary_data(quotas: pd.DataFrame, harvests: pd.DataFrame) -> pd.DataFrame:
    """Build summary data combining quotas and harvests."""
    # Get lookup tables
    cooperatives = fetch_cooperatives_lookup()
    species = fetch_species_lookup()

    # Add names to quotas
    quotas = quotas.copy()
    quotas["cooperative_name"] = quotas["cooperative_id"].map(cooperatives).fillna("Unknown")
    quotas["species_name"] = quotas["species_id"].map(species).fillna("Unknown")
    quotas["allocated"] = quotas["amount"]

    # Aggregate harvests by cooperative (via vessel) and species
    harvest_totals = {}
    if not harvests.empty:
        # Get vessel to cooperative mapping
        vessel_coops = fetch_vessel_cooperative_mapping()

        harvests = harvests.copy()
        harvests["cooperative_id"] = harvests["vessel_id"].map(vessel_coops)

        # Group by cooperative and species
        for _, row in harvests.iterrows():
            coop_id = row.get("cooperative_id")
            species_id = row.get("species_id")
            amount = row.get("amount", 0) or 0

            if coop_id and species_id:
                key = (coop_id, species_id)
                harvest_totals[key] = harvest_totals.get(key, 0) + amount

    # Build summary rows
    summary_rows = []
    for _, quota in quotas.iterrows():
        coop_id = quota["cooperative_id"]
        species_id = quota["species_id"]
        allocated = quota["allocated"]

        harvested = harvest_totals.get((coop_id, species_id), 0)
        remaining = allocated - harvested
        pct_used = (harvested / allocated * 100) if allocated > 0 else 0

        summary_rows.append({
            "cooperative_id": coop_id,
            "cooperative_name": quota["cooperative_name"],
            "species_id": species_id,
            "species_name": quota["species_name"],
            "allocated": allocated,
            "harvested": harvested,
            "remaining": remaining,
            "pct_used": pct_used,
        })

    return pd.DataFrame(summary_rows)


def show_summary_cards(data: pd.DataFrame):
    """Display summary metric cards."""
    total_allocated = data["allocated"].sum()
    total_harvested = data["harvested"].sum()
    total_remaining = data["remaining"].sum()
    overall_pct = (total_harvested / total_allocated * 100) if total_allocated > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Allocated", f"{total_allocated:,.0f} lbs")

    with col2:
        st.metric("Total Harvested", f"{total_harvested:,.0f} lbs")

    with col3:
        st.metric("Total Remaining", f"{total_remaining:,.0f} lbs")

    with col4:
        st.metric("% Used", f"{overall_pct:.1f}%")


def show_quota_table(data: pd.DataFrame):
    """Display quota status table with color coding."""
    st.subheader("Quota Status by Cooperative & Species")

    if data.empty:
        st.info("No data to display.")
        return

    # Prepare display data
    display_df = data[["cooperative_name", "species_name", "allocated", "harvested", "remaining", "pct_used"]].copy()
    display_df = display_df.sort_values(["cooperative_name", "species_name"])

    # Color code function
    def color_pct(val):
        if val > 95:
            return "background-color: #ffcccc"  # Red
        elif val > 80:
            return "background-color: #ffffcc"  # Yellow
        else:
            return "background-color: #ccffcc"  # Green

    # Style the dataframe
    styled_df = display_df.style.applymap(color_pct, subset=["pct_used"])

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "cooperative_name": st.column_config.TextColumn("Cooperative"),
            "species_name": st.column_config.TextColumn("Species"),
            "allocated": st.column_config.NumberColumn("Allocated (lbs)", format="%.0f"),
            "harvested": st.column_config.NumberColumn("Harvested (lbs)", format="%.0f"),
            "remaining": st.column_config.NumberColumn("Remaining (lbs)", format="%.0f"),
            "pct_used": st.column_config.ProgressColumn("% Used", min_value=0, max_value=100, format="%.1f%%"),
        },
        key="quota_dash_table",
    )

    # Show color legend
    st.caption("Status: 🟢 < 80% | 🟡 80-95% | 🔴 > 95%")


def show_quota_chart(data: pd.DataFrame):
    """Display bar chart comparing allocated vs harvested by species."""
    st.subheader("Quota Usage by Species")

    if data.empty:
        return

    # Aggregate by species
    by_species = data.groupby("species_name").agg({
        "allocated": "sum",
        "harvested": "sum",
    }).reset_index()

    # Create chart data
    chart_data = pd.DataFrame({
        "Species": by_species["species_name"],
        "Allocated": by_species["allocated"],
        "Harvested": by_species["harvested"],
    })

    st.bar_chart(
        chart_data.set_index("Species"),
        use_container_width=True,
    )


# =============================================================================
# Data Fetching
# =============================================================================

def fetch_seasons() -> list[dict]:
    """Fetch all seasons, ordered by year descending."""
    try:
        response = supabase.table("seasons").select("id, year").order("year", desc=True).execute()
        return response.data or []
    except Exception as e:
        if handle_jwt_error(e):
            st.rerun()
        return []


def fetch_quotas(season_id: str) -> pd.DataFrame:
    """Fetch quota allocations for a season."""
    try:
        response = supabase.table("quota_allocations").select("*").eq("season_id", season_id).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        if handle_jwt_error(e):
            st.rerun()
        return pd.DataFrame()


def fetch_harvests(season_id: str) -> pd.DataFrame:
    """Fetch harvests for a season."""
    try:
        response = supabase.table("harvests").select("*").eq("season_id", season_id).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        if handle_jwt_error(e):
            st.rerun()
        return pd.DataFrame()


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


def fetch_vessel_cooperative_mapping() -> dict:
    """Fetch current vessel to cooperative mapping."""
    try:
        # Get current assignments (effective_to is NULL)
        response = supabase.table("vessel_cooperative_assignments").select(
            "vessel_id, cooperative_id"
        ).is_("effective_to", "null").execute()

        if response.data:
            return {a["vessel_id"]: a["cooperative_id"] for a in response.data}
        return {}
    except Exception:
        return {}
