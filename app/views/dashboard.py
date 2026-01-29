"""Dashboard page - quota remaining."""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.utils.formatting import format_lbs, get_risk_level

SPECIES_MAP = {141: 'POP', 136: 'NR', 172: 'Dusky'}


@st.cache_data(ttl=60)
def _fetch_quota_remaining(year: int):
    """Cached: Fetch raw quota_remaining data from database."""
    response = supabase.table("quota_remaining").select("*").eq("year", year).execute()
    return response.data if response.data else []


@st.cache_data(ttl=300)
def _fetch_coop_members():
    """Cached: Fetch coop_members reference data (rarely changes)."""
    response = supabase.table("coop_members").select("llp, vessel_name, coop_code").execute()
    return response.data if response.data else []


def get_quota_data():
    """Fetch quota_remaining joined with coop_members for vessel info"""
    # Use cached data fetchers
    quota_data = _fetch_quota_remaining(2026)
    if not quota_data:
        return pd.DataFrame()

    df = pd.DataFrame(quota_data)

    # Get vessel info (cached for 5 min)
    members_data = _fetch_coop_members()
    members_df = pd.DataFrame(members_data) if members_data else pd.DataFrame()

    # Join
    df = df.merge(members_df, on="llp", how="left")

    # Map species codes to names and filter to only known target species
    df["species"] = df["species_code"].map(SPECIES_MAP)

    # Filter out unknown species codes (non-target species like PSC)
    unknown_count = df["species"].isna().sum()
    if unknown_count > 0:
        # Log for debugging but don't show to user
        unknown_codes = df[df["species"].isna()]["species_code"].unique().tolist()
        print(f"Filtered {unknown_count} rows with unknown species codes: {unknown_codes}")

    df = df[df["species"].notna()].copy()

    # Calculate percent remaining (handle 0 allocation)
    df["pct_remaining"] = df.apply(
        lambda row: (row["remaining_lbs"] / row["allocation_lbs"] * 100)
        if row["allocation_lbs"] > 0 else None,
        axis=1
    )

    return df


def pivot_quota_data(df):
    """Pivot to wide format: one row per vessel with columns for each species"""
    if df.empty:
        return pd.DataFrame()

    pivot = df.pivot_table(
        index=["llp", "vessel_name", "coop_code"],
        columns="species",
        values=["remaining_lbs", "allocation_lbs", "pct_remaining"],
        aggfunc="first"
    ).reset_index()

    # Flatten column names
    pivot.columns = [f"{col[1]}_{col[0]}" if col[1] else col[0] for col in pivot.columns]

    # Rename for clarity
    pivot = pivot.rename(columns={
        "llp_": "llp",
        "vessel_name_": "vessel_name",
        "coop_code_": "coop_code"
    })

    return pivot


def _get_risk_level_for_df(pct):
    """Wrapper for get_risk_level that handles pandas NA values."""
    if pd.isna(pct):
        return "na"
    return get_risk_level(pct)


def add_risk_flags(df):
    """Add risk flags for each species and overall vessel risk"""
    for species in ["POP", "NR", "Dusky"]:
        col = f"{species}_pct_remaining"
        if col in df.columns:
            df[f"{species}_risk"] = df[col].apply(_get_risk_level_for_df)

    # Vessel is at risk if ANY species is critical
    risk_cols = [f"{s}_risk" for s in ["POP", "NR", "Dusky"] if f"{s}_risk" in df.columns]
    df["vessel_at_risk"] = df[risk_cols].apply(lambda row: "critical" in row.values, axis=1)

    return df


def render_species_metric(label: str, pct: float, remaining: float, allocated: float):
    """Render a species quota metric using native st.metric with border.

    Uses delta_color to indicate risk level:
    - inverse (red arrow): critical (<10%)
    - off (gray): warning (<50%)
    - normal (green arrow): healthy
    """
    pct_display = f"{pct:.0f}%" if pct is not None else "N/A"
    detail = f"{format_lbs(remaining)} of {format_lbs(allocated)} lbs"

    # Determine delta color based on risk level
    if pct is not None and pct < 10:
        delta_color = "inverse"  # Red - critical
    elif pct is not None and pct < 50:
        delta_color = "off"  # Gray - warning
    else:
        delta_color = "normal"  # Green - healthy

    st.metric(
        label=label,
        value=pct_display,
        delta=detail,
        delta_color=delta_color,
        border=True
    )


# =============================================================================
# Display functions
# =============================================================================

def show():
    """Entry point for the dashboard page."""
    render_dashboard()


def render_dashboard():
    """Main dashboard layout with filters and KPI cards."""
    from app.utils.styles import page_header, section_header

    # Header
    page_header("Dashboard", f"Season 2026 • Last updated: {pd.Timestamp.now().strftime('%B %d, %Y')}")

    # Get and process data
    raw_df = get_quota_data()
    if raw_df.empty:
        st.warning("No quota data found")
        return

    pivot_df = pivot_quota_data(raw_df)
    pivot_df = add_risk_flags(pivot_df)

    # Apply filters from sidebar
    filtered_df = pivot_df.copy()
    selected_coop = st.session_state.get("filter_coop", "All")
    selected_vessel = st.session_state.get("filter_vessel", "All")

    if selected_coop != "All":
        filtered_df = filtered_df[filtered_df["coop_code"] == selected_coop]

    if selected_vessel != "All":
        filtered_df = filtered_df[filtered_df["vessel_name"] == selected_vessel]

    # Show active filters if any
    if selected_coop != "All" or selected_vessel != "All":
        filter_text = []
        if selected_coop != "All":
            filter_text.append(f"Co-Op: {selected_coop}")
        if selected_vessel != "All":
            filter_text.append(f"Vessel: {selected_vessel}")
        st.caption(f"Filtered by: {', '.join(filter_text)}")

    # --- KPI CARDS ---
    total_vessels = len(filtered_df)
    vessels_at_risk = filtered_df["vessel_at_risk"].sum()

    # Calculate totals for each species
    total_pop_remaining = filtered_df["POP_remaining_lbs"].sum() if "POP_remaining_lbs" in filtered_df.columns else 0
    total_pop_allocated = filtered_df["POP_allocation_lbs"].sum() if "POP_allocation_lbs" in filtered_df.columns else 0
    total_pop_pct = (total_pop_remaining / total_pop_allocated * 100) if total_pop_allocated > 0 else 0

    total_nr_remaining = filtered_df["NR_remaining_lbs"].sum() if "NR_remaining_lbs" in filtered_df.columns else 0
    total_nr_allocated = filtered_df["NR_allocation_lbs"].sum() if "NR_allocation_lbs" in filtered_df.columns else 0
    total_nr_pct = (total_nr_remaining / total_nr_allocated * 100) if total_nr_allocated > 0 else 0

    total_dusky_remaining = filtered_df["Dusky_remaining_lbs"].sum() if "Dusky_remaining_lbs" in filtered_df.columns else 0
    total_dusky_allocated = filtered_df["Dusky_allocation_lbs"].sum() if "Dusky_allocation_lbs" in filtered_df.columns else 0
    total_dusky_pct = (total_dusky_remaining / total_dusky_allocated * 100) if total_dusky_allocated > 0 else 0

    # Section label for KPIs
    section_header("OVERVIEW", "📊")

    # Use horizontal container for responsive metric row (wraps on small screens)
    with st.container(horizontal=True):
        st.metric("Vessels", total_vessels, border=True)
        st.metric(
            "At Risk",
            int(vessels_at_risk),
            delta="critical" if vessels_at_risk > 0 else None,
            delta_color="inverse" if vessels_at_risk > 0 else "off",
            border=True
        )
        render_species_metric("POP Remaining", total_pop_pct, total_pop_remaining, total_pop_allocated)
        render_species_metric("NR Remaining", total_nr_pct, total_nr_remaining, total_nr_allocated)
        render_species_metric("Dusky Remaining", total_dusky_pct, total_dusky_remaining, total_dusky_allocated)

    # --- VESSELS NEEDING ATTENTION ---
    section_header("VESSELS NEEDING ATTENTION", "⚠️")

    # Get vessels at risk (any species <10%)
    at_risk_df = filtered_df[filtered_df["vessel_at_risk"] == True].copy()

    with st.container(border=True):
        if at_risk_df.empty:
            st.success("No vessels currently at critical risk levels")
        else:
            # Sort by lowest percent remaining across any species
            at_risk_df["min_pct"] = at_risk_df[[f"{s}_pct_remaining" for s in ["POP", "NR", "Dusky"] if f"{s}_pct_remaining" in at_risk_df.columns]].min(axis=1)
            at_risk_df = at_risk_df.sort_values("min_pct").head(7)

            # Display as simple rows with colored dots
            for _, row in at_risk_df.iterrows():
                vessel_name = row.get("vessel_name", "Unknown")
                llp = row.get("llp", "")

                # Build status dots
                dots = []
                for species in ["POP", "NR", "Dusky"]:
                    pct_col = f"{species}_pct_remaining"
                    if pct_col in row and pd.notna(row[pct_col]):
                        pct = row[pct_col]
                        if pct < 10:
                            color = "🔴"
                        elif pct < 50:
                            color = "🟡"
                        else:
                            color = "🟢"
                        dots.append(f"{color} {species}: {pct:.1f}%")

                dot_str = "  ".join(dots)
                st.markdown(f"**{vessel_name}** (LLP: {llp})  {dot_str}")

            if len(filtered_df[filtered_df["vessel_at_risk"] == True]) > 7:
                st.caption("View all at-risk vessels in the table below")

    # --- MAIN DATA TABLE ---
    section_header("QUOTA REMAINING BY VESSEL", "📋")

    # Prepare display dataframe
    display_df = filtered_df.copy()

    # Select columns for display
    selected_cols = ["coop_code", "vessel_name", "llp"]
    for species in ["POP", "NR", "Dusky"]:
        lbs_col = f"{species}_remaining_lbs"
        pct_col = f"{species}_pct_remaining"
        if lbs_col in display_df.columns:
            selected_cols.append(lbs_col)
        if pct_col in display_df.columns:
            selected_cols.append(pct_col)

    # Filter to available columns
    available_cols = [c for c in selected_cols if c in display_df.columns]
    display_df = display_df[available_cols]

    # Sort by lowest % remaining
    pct_cols = [c for c in display_df.columns if "pct_remaining" in c]
    if pct_cols:
        display_df["_min_pct"] = display_df[pct_cols].min(axis=1)
        display_df = display_df.sort_values("_min_pct").drop(columns=["_min_pct"])

    # Build column_config for formatting
    column_config = {
        "coop_code": st.column_config.TextColumn("Co-Op"),
        "vessel_name": st.column_config.TextColumn("Vessel"),
        "llp": st.column_config.TextColumn("LLP"),
    }

    # Add species columns with proper formatting
    for species in ["POP", "NR", "Dusky"]:
        lbs_col = f"{species}_remaining_lbs"
        pct_col = f"{species}_pct_remaining"

        if lbs_col in display_df.columns:
            column_config[lbs_col] = st.column_config.NumberColumn(
                f"{species} (lbs)",
                format="%,.0f"
            )
        if pct_col in display_df.columns:
            column_config[pct_col] = st.column_config.ProgressColumn(
                f"{species} %",
                min_value=0,
                max_value=100,
                format="%.1f%%"
            )

    st.dataframe(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=500
    )

    st.caption(f"Showing {len(display_df)} vessels")
