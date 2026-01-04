"""Dashboard page - quota remaining."""

import streamlit as st
import pandas as pd
from app.config import supabase

# Species code to name mapping
SPECIES_NAMES = {141: "POP", 136: "NR", 172: "Dusky"}


def show():
    """Display the dashboard with quota remaining."""
    st.title("Dashboard")

    # Co-op filter at top
    coop_options = ["All", "Silver Bay Seafoods", "NORTH PACIFIC", "OBSI", "STAR OF KODIAK"]
    selected_coop = st.selectbox("Filter by Co-Op", coop_options)

    # Quota Remaining section
    show_quota_remaining(selected_coop)


def show_quota_remaining(selected_coop: str):
    """Quota Remaining (What's Available)."""
    st.subheader("Quota Remaining (What's Available)")

    try:
        # Get quota remaining from view
        response = supabase.table("quota_remaining").select("*").eq("year", 2026).execute()

        if not response.data:
            st.info("No quota remaining data for 2026.")
            return

        # Get coop_members for vessel names and coop codes
        members_response = supabase.table("coop_members").select(
            "llp, vessel_name, coop_code"
        ).execute()

        members_df = pd.DataFrame(members_response.data) if members_response.data else pd.DataFrame()

        # Get allocations for percentage calculation
        alloc_response = supabase.table("vessel_allocations").select(
            "llp, species_code, allocation_lbs"
        ).eq("year", 2026).execute()

        alloc_df = pd.DataFrame(alloc_response.data) if alloc_response.data else pd.DataFrame()

        # Pivot remaining to wide format
        remaining_df = pd.DataFrame(response.data)
        remaining_df["species_name"] = remaining_df["species_code"].map(SPECIES_NAMES)

        pivot_df = remaining_df.pivot_table(
            index="llp",
            columns="species_name",
            values="remaining_lbs",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        # Ensure all species columns exist
        for species in ["POP", "NR", "Dusky"]:
            if species not in pivot_df.columns:
                pivot_df[species] = 0

        # Also pivot allocations for percentage calculation
        if not alloc_df.empty:
            alloc_df["species_name"] = alloc_df["species_code"].map(SPECIES_NAMES)
            alloc_pivot = alloc_df.pivot_table(
                index="llp",
                columns="species_name",
                values="allocation_lbs",
                aggfunc="sum",
                fill_value=0
            ).reset_index()

            # Merge to get allocation amounts
            for species in ["POP", "NR", "Dusky"]:
                if species in alloc_pivot.columns:
                    pivot_df = pivot_df.merge(
                        alloc_pivot[["llp", species]].rename(columns={species: f"{species}_alloc"}),
                        on="llp",
                        how="left"
                    )
                else:
                    pivot_df[f"{species}_alloc"] = 0

        # Join with coop_members
        if not members_df.empty:
            pivot_df = pivot_df.merge(members_df, on="llp", how="left")
        else:
            pivot_df["vessel_name"] = None
            pivot_df["coop_code"] = None

        # Filter by coop if selected
        if selected_coop != "All":
            pivot_df = pivot_df[pivot_df["coop_code"] == selected_coop]

        # Rename remaining columns
        pivot_df = pivot_df.rename(columns={
            "POP": "POP Remaining",
            "NR": "NR Remaining",
            "Dusky": "Dusky Remaining",
            "coop_code": "Co-Op",
            "llp": "LLP",
            "vessel_name": "Vessel"
        })

        pivot_df = pivot_df.sort_values(["Co-Op", "LLP"])

        # Select display columns
        display_cols = ["Co-Op", "LLP", "Vessel", "POP Remaining", "NR Remaining", "Dusky Remaining"]
        display_df = pivot_df[display_cols].copy()

        # Calculate percentages for color coding
        def get_color(remaining, alloc):
            if alloc == 0:
                return ""
            pct = remaining / alloc
            if pct > 0.5:
                return "background-color: #90EE90; color: black"  # Green
            elif pct >= 0.1:
                return "background-color: #FFFF99; color: black"  # Yellow
            else:
                return "background-color: #FFB6C1; color: black"  # Red

        # Apply styling
        def style_remaining(row):
            styles = [""] * len(row)
            for i, col in enumerate(display_cols):
                if "Remaining" in col:
                    species = col.replace(" Remaining", "")
                    alloc_col = f"{species}_alloc"
                    if alloc_col in pivot_df.columns:
                        llp_mask = pivot_df["LLP"] == row["LLP"]
                        if llp_mask.any():
                            alloc_val = pivot_df.loc[llp_mask, alloc_col].values[0]
                            styles[i] = get_color(row[col], alloc_val)
            return styles

        # Format numbers first, then apply color styling
        styled_df = display_df.style.format({
            'POP Remaining': '{:,.2f}',
            'NR Remaining': '{:,.2f}',
            'Dusky Remaining': '{:,.2f}'
        }).apply(style_remaining, axis=1)

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        st.caption(f"{len(display_df)} vessels")

        # Legend
        st.markdown("""
        **Legend:**
        <span style='background-color: #90EE90; padding: 2px 8px;'>Green: >50% remaining</span> |
        <span style='background-color: #FFFF99; padding: 2px 8px;'>Yellow: 10-50% remaining</span> |
        <span style='background-color: #FFB6C1; padding: 2px 8px;'>Red: <10% remaining</span>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error loading quota remaining: {e}")
