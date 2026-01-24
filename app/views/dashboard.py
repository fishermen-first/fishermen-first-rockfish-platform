"""Dashboard page - quota remaining."""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.utils.formatting import format_lbs, get_pct_color, get_risk_level

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


def kpi_card(label, value, icon=None, subtitle=None):
    """Create a styled KPI card with consistent height"""
    icon_html = f'<span style="margin-right: 6px;">{icon}</span>' if icon else ''
    if subtitle:
        subtitle_html = f'<div style="color: #64748b; font-size: 13px; margin-top: 6px;"><strong style="color: #475569;">{subtitle}</strong></div>'
    else:
        subtitle_html = '<div style="color: #64748b; font-size: 13px; margin-top: 6px;">&nbsp;</div>'

    return f"""
    <div style="background-color: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center;">
        <div style="color: #64748b; font-size: 16px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">{icon_html}{label}</div>
        <div style="font-size: 36px; font-weight: 700; color: #1e293b;">{value}</div>
        {subtitle_html}
    </div>
    """


def species_kpi_card(label, pct, remaining, allocated, species_code=None):
    """Generate HTML for a species KPI card"""
    # Use dark color for "ok" status to match dashboard styling
    color = get_pct_color(pct, ok_color="#1e293b")
    pct_display = "N/A" if pct is None else f"{pct:.0f}%"

    return f"""
    <div style="background-color: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center;">
        <div style="color: #64748b; font-size: 16px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">{label}</div>
        <div style="font-size: 36px; font-weight: 700; color: {color};">{pct_display}</div>
        <div style="color: #64748b; font-size: 14px; margin-top: 8px;"><strong style="color: #475569;">{format_lbs(remaining)}</strong> of {format_lbs(allocated)} lbs</div>
    </div>
    """


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

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    with kpi1:
        st.markdown(kpi_card("Vessels", str(total_vessels)), unsafe_allow_html=True)
    with kpi2:
        if vessels_at_risk > 0:
            st.markdown(f"""
            <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center;">
                <div style="color: #dc2626; font-size: 16px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">At Risk</div>
                <div style="font-size: 36px; font-weight: 700; color: #dc2626;">{vessels_at_risk}</div>
                <div style="color: #64748b; font-size: 14px; margin-top: 8px;">&nbsp;</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(kpi_card("At Risk", "0"), unsafe_allow_html=True)
    with kpi3:
        st.markdown(species_kpi_card("POP Remaining", total_pop_pct, total_pop_remaining, total_pop_allocated, "POP"), unsafe_allow_html=True)
    with kpi4:
        st.markdown(species_kpi_card("NR Remaining", total_nr_pct, total_nr_remaining, total_nr_allocated, "NR"), unsafe_allow_html=True)
    with kpi5:
        st.markdown(species_kpi_card("Dusky Remaining", total_dusky_pct, total_dusky_remaining, total_dusky_allocated, "Dusky"), unsafe_allow_html=True)

    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)

    # --- VESSELS NEEDING ATTENTION ---
    section_header("VESSELS NEEDING ATTENTION", "⚠️")

    # Get vessels at risk (any species <10%)
    at_risk_df = filtered_df[filtered_df["vessel_at_risk"] == True].copy()

    with st.container():
        if at_risk_df.empty:
            st.markdown("""
            <div style='background: white; padding: 1rem 1.5rem; border-radius: 8px; border: 1px solid #e2e8f0; color: #059669;'>
                ✅ No vessels currently at critical risk levels
            </div>
            """, unsafe_allow_html=True)
        else:
            # Sort by lowest percent remaining across any species
            at_risk_df["min_pct"] = at_risk_df[[f"{s}_pct_remaining" for s in ["POP", "NR", "Dusky"] if f"{s}_pct_remaining" in at_risk_df.columns]].min(axis=1)
            at_risk_df = at_risk_df.sort_values("min_pct").head(7)

            st.markdown("<div style='background: white; padding: 1rem 1.5rem; border-radius: 8px; border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

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

            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)

    # --- MAIN DATA TABLE ---
    section_header("QUOTA REMAINING BY VESSEL", "📋")

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
