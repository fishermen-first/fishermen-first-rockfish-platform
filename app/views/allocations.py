"""Allocations page - TAC and vessel allocations."""

import streamlit as st
import pandas as pd
from app.config import supabase

# Species code to name mapping
SPECIES_NAMES = {141: "POP", 136: "NR", 172: "Dusky"}

# PSC species code to name mapping
PSC_SPECIES_NAMES = {110: "Pacific Cod", 143: "Thornyhead", 200: "Halibut", 710: "Sablefish"}


def show():
    """Display the allocations page with tabs."""
    st.title("Allocations")

    tab1, tab2, tab3 = st.tabs(["Total Allocation", "Vessel Allocations", "PSC Allocations"])

    with tab1:
        show_total_allocation()

    with tab2:
        show_vessel_allocations()

    with tab3:
        show_psc_allocations()


def show_total_allocation():
    """Tab 1: Total Allocation (2026 TAC)."""
    st.subheader("2026 TAC")

    try:
        response = supabase.table("annual_tac").select(
            "species_code, tac_mt, qs_pool, tac_lbs"
        ).eq("year", 2026).order("species_code").execute()

        if response.data:
            df = pd.DataFrame(response.data)
            df["Species"] = df["species_code"].map(SPECIES_NAMES)
            df = df.rename(columns={
                "tac_mt": "TAC (mt)",
                "qs_pool": "QS Pool",
                "tac_lbs": "TAC (lbs)"
            })
            df = df[["Species", "TAC (mt)", "QS Pool", "TAC (lbs)"]]

            df_styled = df.style.format({
                'TAC (mt)': '{:,.0f}',
                'QS Pool': '{:,.0f}',
                'TAC (lbs)': '{:,.0f}'
            })
            st.dataframe(df_styled, use_container_width=True, hide_index=True)
        else:
            st.info("No TAC data for 2026.")
    except Exception as e:
        st.error(f"Error loading TAC data: {e}")


def show_vessel_allocations():
    """Tab 2: Vessel Allocations (Starting Quota)."""
    st.subheader("Starting Quota by Vessel")

    # Co-op filter (only applies to this tab)
    coop_options = ["All", "Silver Bay Seafoods", "NORTH PACIFIC", "OBSI", "STAR OF KODIAK"]
    selected_coop = st.selectbox("Filter by Co-Op", coop_options)

    try:
        # Get vessel allocations
        response = supabase.table("vessel_allocations").select(
            "llp, species_code, allocation_lbs"
        ).eq("year", 2026).execute()

        if not response.data:
            st.info("No vessel allocations for 2026.")
            return

        # Get coop_members for vessel names and coop codes
        members_response = supabase.table("coop_members").select(
            "llp, vessel_name, coop_code"
        ).execute()

        members_df = pd.DataFrame(members_response.data) if members_response.data else pd.DataFrame()

        # Pivot allocations to wide format
        alloc_df = pd.DataFrame(response.data)
        alloc_df["species_name"] = alloc_df["species_code"].map(SPECIES_NAMES)

        pivot_df = alloc_df.pivot_table(
            index="llp",
            columns="species_name",
            values="allocation_lbs",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        # Ensure all species columns exist
        for species in ["POP", "NR", "Dusky"]:
            if species not in pivot_df.columns:
                pivot_df[species] = 0

        # Join with coop_members
        if not members_df.empty:
            pivot_df = pivot_df.merge(members_df, on="llp", how="left")
        else:
            pivot_df["vessel_name"] = None
            pivot_df["coop_code"] = None

        # Calculate total
        pivot_df["Total"] = pivot_df["POP"] + pivot_df["NR"] + pivot_df["Dusky"]

        # Filter by coop if selected
        if selected_coop != "All":
            pivot_df = pivot_df[pivot_df["coop_code"] == selected_coop]

        # Reorder and rename columns
        pivot_df = pivot_df[["coop_code", "llp", "vessel_name", "POP", "NR", "Dusky", "Total"]]
        pivot_df = pivot_df.rename(columns={
            "coop_code": "Co-Op",
            "llp": "LLP",
            "vessel_name": "Vessel"
        })
        pivot_df = pivot_df.sort_values(["Co-Op", "LLP"])

        df_styled = pivot_df.style.format({
            'POP': '{:,.2f}',
            'NR': '{:,.2f}',
            'Dusky': '{:,.2f}',
            'Total': '{:,.2f}'
        })
        st.dataframe(df_styled, use_container_width=True, hide_index=True)
        st.caption(f"{len(pivot_df)} vessels")

    except Exception as e:
        st.error(f"Error loading vessel allocations: {e}")


def show_psc_allocations():
    """Tab 3: PSC Allocations."""
    st.subheader("PSC Allocations (2026)")

    try:
        response = supabase.table("psc_allocations").select(
            "species_code, cv_sector_lbs"
        ).eq("year", 2026).order("species_code").execute()

        if response.data:
            df = pd.DataFrame(response.data)
            df["Species"] = df["species_code"].map(PSC_SPECIES_NAMES)
            df = df.rename(columns={
                "cv_sector_lbs": "CV Sector (lbs)"
            })
            df = df[["Species", "CV Sector (lbs)"]]

            df_styled = df.style.format({
                'CV Sector (lbs)': '{:,.0f}'
            })
            st.dataframe(df_styled, use_container_width=True, hide_index=True)
        else:
            st.info("No PSC allocation data for 2026.")
    except Exception as e:
        st.error(f"Error loading PSC allocations: {e}")
