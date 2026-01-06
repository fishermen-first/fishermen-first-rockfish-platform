"""Dashboard page - quota remaining."""

import streamlit as st
import pandas as pd
from app.config import supabase

SPECIES_MAP = {141: 'POP', 136: 'NR', 172: 'Dusky'}


def get_quota_data():
    """Fetch quota_remaining joined with coop_members for vessel info"""
    response = supabase.table("quota_remaining").select("*").eq("year", 2026).execute()
    if not response.data:
        return pd.DataFrame()

    df = pd.DataFrame(response.data)

    # Get vessel info
    members = supabase.table("coop_members").select("llp, vessel_name, coop_code").execute()
    members_df = pd.DataFrame(members.data)

    # Join
    df = df.merge(members_df, on="llp", how="left")

    # Map species codes to names
    df["species"] = df["species_code"].map(SPECIES_MAP)

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


def get_risk_level(pct):
    """Return risk level based on percent remaining"""
    if pct is None or pd.isna(pct):
        return "na"  # Not applicable - no allocation
    if pct < 10:
        return "critical"
    elif pct < 50:
        return "warning"
    return "ok"


def add_risk_flags(df):
    """Add risk flags for each species and overall vessel risk"""
    for species in ["POP", "NR", "Dusky"]:
        col = f"{species}_pct_remaining"
        if col in df.columns:
            df[f"{species}_risk"] = df[col].apply(get_risk_level)

    # Vessel is at risk if ANY species is critical
    risk_cols = [f"{s}_risk" for s in ["POP", "NR", "Dusky"] if f"{s}_risk" in df.columns]
    df["vessel_at_risk"] = df[risk_cols].apply(lambda row: "critical" in row.values, axis=1)

    return df


# =============================================================================
# Display functions
# =============================================================================

def show():
    """Entry point for the dashboard page."""
    render_dashboard()


def render_dashboard():
    """Main dashboard layout with filters and KPI cards."""
    # Handle clear filters action BEFORE widgets render
    if st.session_state.get("clear_filters_clicked", False):
        st.session_state.filter_coop = "All"
        st.session_state.filter_species = "All"
        st.session_state.filter_risk = "All"
        st.session_state.clear_filters_clicked = False
        st.rerun()

    # Custom CSS for KPI cards
    st.markdown("""
    <style>
        [data-testid="stMetric"] {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        [data-testid="stMetric"] label {
            color: #64748b;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("Dashboard")
    st.caption("Quota overview across all co-ops")
    st.caption(f"Season: 2026 | Last updated: {pd.Timestamp.now().strftime('%B %d, %Y')}")

    # Get and process data
    raw_df = get_quota_data()
    if raw_df.empty:
        st.warning("No quota data found")
        return

    pivot_df = pivot_quota_data(raw_df)
    pivot_df = add_risk_flags(pivot_df)

    # --- FILTER BAR ---
    with st.expander("Filters", expanded=False):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:
            coops = ["All"] + sorted(pivot_df["coop_code"].dropna().unique().tolist())
            selected_coop = st.selectbox("Co-Op", coops, key="filter_coop")

        with col2:
            selected_species = st.selectbox("Species", ["All", "POP", "NR", "Dusky"], key="filter_species")

        with col3:
            selected_risk = st.selectbox("Risk Level", ["All", ">50% Remaining", "10-50% Remaining", "<10% Remaining"], key="filter_risk")

        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Clear Filters"):
                st.session_state.clear_filters_clicked = True
                st.rerun()

    # Apply filters
    filtered_df = pivot_df.copy()

    if selected_coop != "All":
        filtered_df = filtered_df[filtered_df["coop_code"] == selected_coop]

    if selected_risk == "<10% Remaining":
        filtered_df = filtered_df[filtered_df["vessel_at_risk"] == True]
    elif selected_risk == "10-50% Remaining":
        mask = False
        for species in ["POP", "NR", "Dusky"]:
            col = f"{species}_pct_remaining"
            if col in filtered_df.columns:
                mask = mask | ((filtered_df[col] >= 10) & (filtered_df[col] < 50))
        filtered_df = filtered_df[mask]
    elif selected_risk == ">50% Remaining":
        mask = True
        for species in ["POP", "NR", "Dusky"]:
            col = f"{species}_pct_remaining"
            if col in filtered_df.columns:
                mask = mask & (filtered_df[col] >= 50)
        filtered_df = filtered_df[mask]

    st.markdown("<br>", unsafe_allow_html=True)

    # --- KPI CARDS ---
    total_vessels = len(filtered_df)
    vessels_at_risk = filtered_df["vessel_at_risk"].sum()

    avg_pct_cols = [f"{s}_pct_remaining" for s in ["POP", "NR", "Dusky"] if f"{s}_pct_remaining" in filtered_df.columns]
    avg_pct = filtered_df[avg_pct_cols].mean().mean() if avg_pct_cols else 0

    total_pop = filtered_df["POP_remaining_lbs"].sum() if "POP_remaining_lbs" in filtered_df.columns else 0
    total_nr = filtered_df["NR_remaining_lbs"].sum() if "NR_remaining_lbs" in filtered_df.columns else 0
    total_dusky = filtered_df["Dusky_remaining_lbs"].sum() if "Dusky_remaining_lbs" in filtered_df.columns else 0

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

    with kpi1:
        st.metric("Vessels Tracked", f"{total_vessels}")
    with kpi2:
        if vessels_at_risk > 0:
            st.markdown(f"""
                <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 15px;">
                    <p style="color: #64748b; font-size: 14px; margin: 0;">Vessels at Risk</p>
                    <p style="color: #dc2626; font-size: 32px; font-weight: bold; margin: 0;">{vessels_at_risk}</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.metric("Vessels at Risk", f"{vessels_at_risk}")
    with kpi3:
        st.metric("Avg % Remaining", f"{avg_pct:.1f}%")
    with kpi4:
        st.metric("Total POP (lbs)", f"{total_pop:,.0f}")
    with kpi5:
        st.metric("Total NR (lbs)", f"{total_nr:,.0f}")
    with kpi6:
        st.metric("Total Dusky (lbs)", f"{total_dusky:,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- VESSELS NEEDING ATTENTION ---
    st.subheader("⚠️ Vessels Needing Attention")

    # Get vessels at risk (any species <10%)
    at_risk_df = filtered_df[filtered_df["vessel_at_risk"] == True].copy()

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

            dot_str = " &nbsp;&nbsp; ".join(dots)
            st.markdown(f"**{vessel_name}** (LLP: {llp}) &nbsp;&nbsp; {dot_str}", unsafe_allow_html=True)

        if len(filtered_df[filtered_df["vessel_at_risk"] == True]) > 7:
            st.markdown("*View all at-risk vessels in the table below*")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- MAIN DATA TABLE ---
    st.subheader("Quota Remaining by Vessel")

    # Prepare display dataframe
    display_df = filtered_df.copy()

    # Select and rename columns for display
    display_cols = {
        "coop_code": "Co-Op",
        "vessel_name": "Vessel",
        "llp": "LLP"
    }

    for species in ["POP", "NR", "Dusky"]:
        lbs_col = f"{species}_remaining_lbs"
        pct_col = f"{species}_pct_remaining"
        if lbs_col in display_df.columns:
            display_cols[lbs_col] = f"{species} (lbs)"
        if pct_col in display_df.columns:
            display_cols[pct_col] = f"{species} %"

    # Filter to only columns we want
    available_cols = [c for c in display_cols.keys() if c in display_df.columns]
    display_df = display_df[available_cols].rename(columns=display_cols)

    # Sort by lowest % remaining
    pct_cols = [c for c in display_df.columns if "%" in c]
    if pct_cols:
        display_df["_min_pct"] = display_df[pct_cols].min(axis=1)
        display_df = display_df.sort_values("_min_pct").drop(columns=["_min_pct"])

    # Apply styling with progress bars
    def color_pct(val):
        """Color based on risk level"""
        if pd.isna(val):
            return ""
        if val < 10:
            return "color: #dc2626"  # red
        elif val < 50:
            return "color: #d97706"  # amber
        return "color: #059669"  # green

    # Format and style
    lbs_cols = [c for c in display_df.columns if "(lbs)" in c]
    pct_cols = [c for c in display_df.columns if "%" in c]

    format_dict = {c: "{:,.0f}" for c in lbs_cols}
    format_dict.update({c: "{:.1f}%" for c in pct_cols})

    styled_df = display_df.style.format(format_dict, na_rep="-")

    # Add bars to percent columns
    for col in pct_cols:
        styled_df = styled_df.bar(
            subset=[col],
            vmin=0,
            vmax=100,
            color="#e0e7ff"  # light indigo
        )

    # Color the percent text
    styled_df = styled_df.applymap(color_pct, subset=pct_cols)

    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=500)

    st.caption(f"Showing {len(display_df)} vessels")

    # Store filtered_df for next sections
    st.session_state.dashboard_filtered_df = filtered_df
