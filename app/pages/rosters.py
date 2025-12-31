"""
Rosters page - View cooperatives, members, and vessels.
"""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_auth


def show():
    """Display the rosters page with tabs for cooperatives, members, and vessels."""
    if not require_auth():
        st.stop()

    st.title("Rosters")

    tab_coops, tab_members, tab_vessels = st.tabs(["Cooperatives", "Members", "Vessels"])

    with tab_coops:
        show_cooperatives_tab()

    with tab_members:
        show_members_tab()

    with tab_vessels:
        show_vessels_tab()


# =============================================================================
# Cooperatives Tab
# =============================================================================

def show_cooperatives_tab():
    """Display cooperatives table."""
    st.subheader("Cooperatives")

    # Fetch data
    data = fetch_cooperatives()

    if data.empty:
        st.info("No cooperatives found.")
        return

    # Search filter
    search = st.text_input("Search cooperatives", key="coop_search", placeholder="Filter by name...")

    if search:
        data = data[data["cooperative_name"].str.contains(search, case=False, na=False)]

    if data.empty:
        st.warning("No cooperatives match your search.")
        return

    # Display table
    st.dataframe(
        data[["cooperative_name", "contact_info", "member_count", "vessel_count"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "cooperative_name": st.column_config.TextColumn("Cooperative Name"),
            "contact_info": st.column_config.TextColumn("Contact Info"),
            "member_count": st.column_config.NumberColumn("Members", format="%d"),
            "vessel_count": st.column_config.NumberColumn("Vessels", format="%d"),
        },
    )

    st.caption(f"Showing {len(data)} cooperative(s)")


def fetch_cooperatives() -> pd.DataFrame:
    """Fetch cooperatives with member and vessel counts."""
    try:
        # Get cooperatives
        coop_response = supabase.table("cooperatives").select("*").execute()
        if not coop_response.data:
            return pd.DataFrame()

        coops = pd.DataFrame(coop_response.data)

        # Get current member counts
        membership_response = supabase.table("cooperative_memberships").select(
            "cooperative_id"
        ).is_("effective_to", "null").execute()

        member_counts = {}
        if membership_response.data:
            for m in membership_response.data:
                cid = m["cooperative_id"]
                member_counts[cid] = member_counts.get(cid, 0) + 1

        # Get current vessel counts
        vessel_response = supabase.table("vessel_cooperative_assignments").select(
            "cooperative_id"
        ).is_("effective_to", "null").execute()

        vessel_counts = {}
        if vessel_response.data:
            for v in vessel_response.data:
                cid = v["cooperative_id"]
                vessel_counts[cid] = vessel_counts.get(cid, 0) + 1

        # Add counts to dataframe
        coops["member_count"] = coops["id"].map(lambda x: member_counts.get(x, 0))
        coops["vessel_count"] = coops["id"].map(lambda x: vessel_counts.get(x, 0))

        return coops.sort_values("cooperative_name")

    except Exception as e:
        st.error(f"Error fetching cooperatives: {e}")
        return pd.DataFrame()


# =============================================================================
# Members Tab
# =============================================================================

def show_members_tab():
    """Display members table with cooperative assignments."""
    st.subheader("Members")

    # Fetch data
    data = fetch_members_with_cooperatives()

    if data.empty:
        st.info("No members found.")
        return

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("Search members", key="member_search", placeholder="Filter by name...")
    with col2:
        coop_filter = st.selectbox(
            "Filter by cooperative",
            options=["All"] + sorted(data["cooperative_name"].dropna().unique().tolist()),
            key="member_coop_filter"
        )

    # Apply filters
    filtered = data.copy()
    if search:
        filtered = filtered[filtered["member_name"].str.contains(search, case=False, na=False)]
    if coop_filter != "All":
        filtered = filtered[filtered["cooperative_name"] == coop_filter]

    if filtered.empty:
        st.warning("No members match your filters.")
        return

    # Display table
    st.dataframe(
        filtered[["member_name", "contact_info", "cooperative_name", "vessel_count"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "member_name": st.column_config.TextColumn("Member Name"),
            "contact_info": st.column_config.TextColumn("Contact Info"),
            "cooperative_name": st.column_config.TextColumn("Cooperative"),
            "vessel_count": st.column_config.NumberColumn("Vessels", format="%d"),
        },
    )

    st.caption(f"Showing {len(filtered)} member(s)")


def fetch_members_with_cooperatives() -> pd.DataFrame:
    """Fetch members with their current cooperative assignments."""
    try:
        # Get members
        member_response = supabase.table("members").select("*").execute()
        if not member_response.data:
            return pd.DataFrame()

        members = pd.DataFrame(member_response.data)

        # Get current cooperative memberships
        membership_response = supabase.table("cooperative_memberships").select(
            "member_id, cooperative_id"
        ).is_("effective_to", "null").execute()

        member_to_coop = {}
        if membership_response.data:
            for m in membership_response.data:
                member_to_coop[m["member_id"]] = m["cooperative_id"]

        # Get cooperative names
        coop_response = supabase.table("cooperatives").select("id, cooperative_name").execute()
        coop_names = {}
        if coop_response.data:
            coop_names = {c["id"]: c["cooperative_name"] for c in coop_response.data}

        # Get vessel counts per member
        vessel_response = supabase.table("vessels").select("member_id").execute()
        vessel_counts = {}
        if vessel_response.data:
            for v in vessel_response.data:
                mid = v["member_id"]
                if mid:
                    vessel_counts[mid] = vessel_counts.get(mid, 0) + 1

        # Add cooperative name and vessel count to members
        members["cooperative_id"] = members["id"].map(member_to_coop)
        members["cooperative_name"] = members["cooperative_id"].map(coop_names)
        members["vessel_count"] = members["id"].map(lambda x: vessel_counts.get(x, 0))

        return members.sort_values("member_name")

    except Exception as e:
        st.error(f"Error fetching members: {e}")
        return pd.DataFrame()


# =============================================================================
# Vessels Tab
# =============================================================================

def show_vessels_tab():
    """Display vessels table with owner and cooperative assignments."""
    st.subheader("Vessels")

    # Fetch data
    data = fetch_vessels_with_details()

    if data.empty:
        st.info("No vessels found.")
        return

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("Search vessels", key="vessel_search", placeholder="Filter by name or ID...")
    with col2:
        coop_filter = st.selectbox(
            "Filter by cooperative",
            options=["All"] + sorted(data["cooperative_name"].dropna().unique().tolist()),
            key="vessel_coop_filter"
        )

    # Apply filters
    filtered = data.copy()
    if search:
        name_match = filtered["vessel_name"].str.contains(search, case=False, na=False)
        id_match = filtered["vessel_id_number"].str.contains(search, case=False, na=False)
        filtered = filtered[name_match | id_match]
    if coop_filter != "All":
        filtered = filtered[filtered["cooperative_name"] == coop_filter]

    if filtered.empty:
        st.warning("No vessels match your filters.")
        return

    # Display table
    st.dataframe(
        filtered[["vessel_name", "vessel_id_number", "owner_name", "cooperative_name"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "vessel_name": st.column_config.TextColumn("Vessel Name"),
            "vessel_id_number": st.column_config.TextColumn("Vessel ID"),
            "owner_name": st.column_config.TextColumn("Owner"),
            "cooperative_name": st.column_config.TextColumn("Cooperative"),
        },
    )

    st.caption(f"Showing {len(filtered)} vessel(s)")


def fetch_vessels_with_details() -> pd.DataFrame:
    """Fetch vessels with owner and current cooperative assignment."""
    try:
        # Get vessels
        vessel_response = supabase.table("vessels").select("*").execute()
        if not vessel_response.data:
            return pd.DataFrame()

        vessels = pd.DataFrame(vessel_response.data)

        # Get member names (owners)
        member_response = supabase.table("members").select("id, member_name").execute()
        member_names = {}
        if member_response.data:
            member_names = {m["id"]: m["member_name"] for m in member_response.data}

        # Get current vessel cooperative assignments
        assignment_response = supabase.table("vessel_cooperative_assignments").select(
            "vessel_id, cooperative_id"
        ).is_("effective_to", "null").execute()

        vessel_to_coop = {}
        if assignment_response.data:
            for a in assignment_response.data:
                vessel_to_coop[a["vessel_id"]] = a["cooperative_id"]

        # Get cooperative names
        coop_response = supabase.table("cooperatives").select("id, cooperative_name").execute()
        coop_names = {}
        if coop_response.data:
            coop_names = {c["id"]: c["cooperative_name"] for c in coop_response.data}

        # Add owner name and cooperative to vessels
        vessels["owner_name"] = vessels["member_id"].map(member_names)
        vessels["cooperative_id"] = vessels["id"].map(vessel_to_coop)
        vessels["cooperative_name"] = vessels["cooperative_id"].map(coop_names)

        return vessels.sort_values("vessel_name")

    except Exception as e:
        st.error(f"Error fetching vessels: {e}")
        return pd.DataFrame()
