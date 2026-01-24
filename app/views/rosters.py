"""Rosters page - view cooperatives, members, vessels, processors."""

import streamlit as st
import pandas as pd
from app.config import supabase


def _show_roster_table(
    table: str,
    columns: str,
    order_by: str,
    label: str,
    column_renames: dict | None = None
) -> None:
    """
    Generic helper to display a roster table.

    Args:
        table: Supabase table name
        columns: Comma-separated column list for select
        order_by: Column name to order results by
        label: Display label for subheader and messages (e.g., "cooperatives")
        column_renames: Optional dict mapping old column names to new display names
    """
    st.subheader(label.title())

    try:
        response = supabase.table(table).select(columns).order(order_by).execute()

        if response.data:
            df = pd.DataFrame(response.data)
            if column_renames:
                df = df.rename(columns=column_renames)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(df)} {label}")
        else:
            st.info(f"No {label} found.")
    except Exception as e:
        st.error(f"Error loading {label}: {e}")


def show():
    """Display the rosters page with 5 tabs."""
    from app.utils.styles import page_header
    page_header("Rosters", "Cooperatives, members, vessels, and reference data")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Cooperatives", "Members", "Vessels", "Processors", "Species"])

    with tab1:
        _show_roster_table(
            "cooperatives",
            "coop_name, coop_code, coop_id",
            "coop_name",
            "cooperatives"
        )

    with tab2:
        _show_roster_table(
            "coop_members",
            "coop_code, coop_id, llp, company_name, vessel_name, representative",
            "coop_code",
            "members"
        )

    with tab3:
        _show_roster_table(
            "vessels",
            "coop_code, vessel_name, adfg_number, is_active",
            "vessel_name",
            "vessels"
        )

    with tab4:
        _show_roster_table(
            "processors",
            "processor_name, processor_code, associated_coop",
            "processor_name",
            "processors"
        )

    with tab5:
        _show_roster_table(
            "species",
            "code, species_name, is_psc",
            "code",
            "species",
            column_renames={"code": "Code", "species_name": "Species Name", "is_psc": "PSC?"}
        )
