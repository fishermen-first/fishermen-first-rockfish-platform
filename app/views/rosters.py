"""Rosters page - view cooperatives, members, vessels, processors."""

import streamlit as st
import pandas as pd
from app.config import supabase


def show():
    """Display the rosters page with 5 tabs."""
    st.title("Rosters")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Cooperatives", "Members", "Vessels", "Processors", "Species"])

    with tab1:
        show_cooperatives()

    with tab2:
        show_members()

    with tab3:
        show_vessels()

    with tab4:
        show_processors()

    with tab5:
        show_species()


def show_cooperatives():
    """Display cooperatives list."""
    st.subheader("Cooperatives")

    try:
        response = supabase.table("cooperatives").select(
            "coop_name, coop_code, coop_id"
        ).order("coop_name").execute()

        if response.data:
            df = pd.DataFrame(response.data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(df)} cooperatives")
        else:
            st.info("No cooperatives found.")
    except Exception as e:
        st.error(f"Error loading cooperatives: {e}")


def show_members():
    """Display coop members."""
    st.subheader("Members")

    try:
        response = supabase.table("coop_members").select(
            "coop_code, coop_id, llp, company_name, vessel_name, representative"
        ).order("coop_code").execute()

        if response.data:
            df = pd.DataFrame(response.data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(df)} members")
        else:
            st.info("No members found.")
    except Exception as e:
        st.error(f"Error loading members: {e}")


def show_vessels():
    """Display vessels."""
    st.subheader("Vessels")

    try:
        response = supabase.table("vessels").select(
            "coop_code, vessel_name, adfg_number, is_active"
        ).order("vessel_name").execute()

        if response.data:
            df = pd.DataFrame(response.data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(df)} vessels")
        else:
            st.info("No vessels found.")
    except Exception as e:
        st.error(f"Error loading vessels: {e}")


def show_processors():
    """Display processors list."""
    st.subheader("Processors")

    try:
        response = supabase.table("processors").select(
            "processor_name, processor_code, associated_coop"
        ).order("processor_name").execute()

        if response.data:
            df = pd.DataFrame(response.data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(df)} processors")
        else:
            st.info("No processors found.")
    except Exception as e:
        st.error(f"Error loading processors: {e}")


def show_species():
    """Display species list."""
    st.subheader("Species")

    try:
        response = supabase.table("species").select(
            "code, species_name, is_psc"
        ).order("code").execute()

        if response.data:
            df = pd.DataFrame(response.data)
            df.columns = ["Code", "Species Name", "PSC?"]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(df)} species")
        else:
            st.info("No species found.")
    except Exception as e:
        st.error(f"Error loading species: {e}")
