"""Quota Transfers page - transfer quota between LLPs."""

import streamlit as st
import pandas as pd
from datetime import date
from app.config import supabase
from app.auth import require_role

# Species mapping for target species only (non-PSC)
SPECIES_OPTIONS = {
    141: "POP (Pacific Ocean Perch)",
    136: "NR (Northern Rockfish)",
    172: "Dusky (Dusky Rockfish)"
}

CURRENT_YEAR = 2026


@st.cache_data(ttl=300)
def _fetch_coop_members_for_dropdown():
    """Cached: Fetch coop_members for LLP dropdown (rarely changes)."""
    response = supabase.table("coop_members").select("llp, vessel_name").order("llp").execute()
    return response.data if response.data else []


@st.cache_data(ttl=30)
def _fetch_transfer_history(year: int):
    """Cached: Fetch transfer history (short TTL for near-realtime)."""
    response = supabase.table("quota_transfers").select(
        "id, from_llp, to_llp, species_code, pounds, transfer_date, notes, created_at"
    ).eq("year", year).eq("is_deleted", False).order("created_at", desc=True).execute()
    return response.data if response.data else []


@st.cache_data(ttl=300)
def _fetch_llp_to_vessel_map():
    """Cached: Fetch LLP to vessel name mapping."""
    response = supabase.table("coop_members").select("llp, vessel_name").execute()
    if response.data:
        return {m["llp"]: m["vessel_name"] for m in response.data}
    return {}


def clear_transfer_cache():
    """Clear transfer-related caches after successful transfer."""
    _fetch_transfer_history.clear()
    get_quota_remaining.clear()


def get_llp_options() -> list[tuple[str, str]]:
    """
    Fetch all LLPs with vessel names for dropdown display.

    Returns:
        List of tuples: (llp, "LLP - Vessel Name")
    """
    try:
        # Use cached data
        data = _fetch_coop_members_for_dropdown()
        if data:
            return [
                (row["llp"], f"{row['llp']} - {row.get('vessel_name') or 'Unknown'}")
                for row in data
            ]
        return []
    except Exception as e:
        st.error(f"Error loading LLPs: {e}")
        return []


@st.cache_data(ttl=30)
def get_quota_remaining(llp: str, species_code: int, year: int = CURRENT_YEAR) -> float:
    """
    Get remaining quota for a specific LLP and species.

    Args:
        llp: The LLP identifier
        species_code: The species code (141, 136, or 172)
        year: The fishing year (default 2026)

    Returns:
        Remaining quota in pounds, or 0 if not found
    """
    try:
        response = supabase.table("quota_remaining").select(
            "remaining_lbs"
        ).eq("llp", llp).eq("species_code", species_code).eq("year", year).execute()

        if response.data and len(response.data) > 0:
            return float(response.data[0]["remaining_lbs"] or 0)
        return 0.0
    except Exception as e:
        st.error(f"Error checking quota: {e}")
        return 0.0


def get_transfer_history(year: int = CURRENT_YEAR) -> pd.DataFrame:
    """
    Fetch all non-deleted transfers for the year.

    Returns:
        DataFrame with transfer records joined with vessel names
    """
    try:
        # Use cached data
        data = _fetch_transfer_history(year)
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Get vessel names for display (cached)
        llp_to_vessel = _fetch_llp_to_vessel_map()
        if llp_to_vessel:
            df["from_vessel"] = df["from_llp"].map(llp_to_vessel)
            df["to_vessel"] = df["to_llp"].map(llp_to_vessel)

        # Map species codes to names
        species_map = {141: "POP", 136: "NR", 172: "Dusky"}
        df["species"] = df["species_code"].map(species_map)

        return df
    except Exception as e:
        st.error(f"Error loading transfer history: {e}")
        return pd.DataFrame()


def insert_transfer(
    from_llp: str,
    to_llp: str,
    species_code: int,
    pounds: float,
    notes: str | None,
    user_id: str,
    org_id: str
) -> tuple[bool, int, str | None]:
    """
    Insert a new quota transfer record.

    Args:
        from_llp: Source LLP
        to_llp: Destination LLP
        species_code: Species code (141, 136, 172)
        pounds: Amount to transfer
        notes: Optional notes
        user_id: ID of user creating the transfer
        org_id: Organization ID for multi-tenant isolation

    Returns:
        Tuple of (success: bool, count: int, error: str | None)
    """
    try:
        # Strip whitespace and convert empty/whitespace-only to None
        clean_notes = (notes.strip() or None) if notes else None

        record = {
            "org_id": org_id,
            "from_llp": from_llp,
            "to_llp": to_llp,
            "species_code": species_code,
            "year": CURRENT_YEAR,
            "pounds": pounds,
            "transfer_date": date.today().isoformat(),
            "notes": clean_notes,
            "created_by": user_id,
            "is_deleted": False
        }

        response = supabase.table("quota_transfers").insert(record).execute()

        if response.data:
            return True, 1, None
        return False, 0, "Insert returned no data"

    except Exception as e:
        return False, 0, str(e)


def show():
    """Display the quota transfers page."""
    from app.utils.styles import page_header, section_header

    # Role check - only admin and manager can access
    if not require_role("manager"):
        return

    page_header("Quota Transfers", f"Transfer quota between LLPs | Season: {CURRENT_YEAR}")

    # Get LLP options once for both dropdowns
    llp_options = get_llp_options()

    if not llp_options:
        st.warning("No LLPs found. Please ensure coop_members table is populated.")
        return

    # Create display options for selectbox
    llp_display = {display: llp for llp, display in llp_options}
    display_options = list(llp_display.keys())

    # Species options for selectbox
    species_display = {v: k for k, v in SPECIES_OPTIONS.items()}
    species_options = list(species_display.keys())

    # --- NEW TRANSFER FORM ---
    section_header("NEW TRANSFER", "➕")

    # Selectboxes OUTSIDE form so changes trigger immediate updates
    col1, col2 = st.columns(2)

    with col1:
        from_llp_display = st.selectbox(
            "From LLP (Source)",
            options=display_options,
            key="from_llp_select"
        )

    with col2:
        to_llp_display = st.selectbox(
            "To LLP (Destination)",
            options=display_options,
            key="to_llp_select"
        )

    col3, col4 = st.columns(2)

    with col3:
        species_display_selected = st.selectbox(
            "Species",
            options=species_options,
            key="species_select"
        )

    with col4:
        pounds = st.number_input(
            "Pounds",
            min_value=1.0,
            max_value=10000000.0,
            value=1000.0,
            step=100.0,
            key="pounds_input"
        )

    # Show available quota for BOTH vessels (updates immediately on selection change)
    if from_llp_display and to_llp_display and species_display_selected:
        from_llp = llp_display[from_llp_display]
        to_llp = llp_display[to_llp_display]
        species_code = species_display[species_display_selected]
        species_short = SPECIES_OPTIONS[species_code].split(" ")[0]

        from_available = get_quota_remaining(from_llp, species_code)
        to_available = get_quota_remaining(to_llp, species_code)

        col_from, col_to = st.columns(2)
        with col_from:
            st.info(f"**{from_llp}** has **{from_available:,.0f} lbs** {species_short}")
        with col_to:
            st.info(f"**{to_llp}** has **{to_available:,.0f} lbs** {species_short}")

    # Form for notes and submit only
    with st.form("transfer_form", clear_on_submit=True):
        notes = st.text_area(
            "Notes (optional)",
            max_chars=500,
            key="notes_input"
        )

        submitted = st.form_submit_button("Submit Transfer", use_container_width=True)

    # Handle form submission
    if submitted:
        # Extract actual values from display strings
        from_llp = llp_display[from_llp_display]
        to_llp = llp_display[to_llp_display]
        species_code = species_display[species_display_selected]

        # Validation
        errors = []

        if from_llp == to_llp:
            errors.append("Source and destination LLP cannot be the same.")

        if pounds <= 0:
            errors.append("Transfer amount must be greater than zero.")

        # Check available quota
        available = get_quota_remaining(from_llp, species_code)
        if pounds > available:
            errors.append(
                f"Insufficient quota. {from_llp} only has {available:,.0f} lbs "
                f"of {SPECIES_OPTIONS[species_code].split(' ')[0]} remaining."
            )

        if errors:
            for error in errors:
                st.error(error)
        else:
            # Get user ID and org_id for audit trail and RLS
            user_id = st.session_state.user.id if st.session_state.user else "unknown"
            org_id = st.session_state.get("org_id")

            if not org_id:
                st.error("Organization not set. Please log out and log back in.")
                return

            success, count, error = insert_transfer(
                from_llp=from_llp,
                to_llp=to_llp,
                species_code=species_code,
                pounds=pounds,
                notes=notes,
                user_id=user_id,
                org_id=org_id
            )

            if success:
                st.success(
                    f"Transfer complete: {pounds:,.0f} lbs of "
                    f"{SPECIES_OPTIONS[species_code].split(' ')[0]} "
                    f"from {from_llp} to {to_llp}"
                )
                clear_transfer_cache()  # Clear cache so history refreshes
                st.rerun()  # Refresh to show updated history
            else:
                st.error(f"Transfer failed: {error}")

    st.divider()

    # --- TRANSFER HISTORY ---
    section_header("TRANSFER HISTORY", "📜")

    history_df = get_transfer_history()

    if history_df.empty:
        st.info(f"No transfers recorded for {CURRENT_YEAR}.")
    else:
        # Prepare display columns
        display_df = history_df[[
            "transfer_date", "from_llp", "from_vessel",
            "to_llp", "to_vessel", "species", "pounds", "notes"
        ]].copy()

        display_df = display_df.rename(columns={
            "transfer_date": "Date",
            "from_llp": "From LLP",
            "from_vessel": "From Vessel",
            "to_llp": "To LLP",
            "to_vessel": "To Vessel",
            "species": "Species",
            "pounds": "Pounds",
            "notes": "Notes"
        })

        # Format and display
        styled_df = display_df.style.format({
            "Pounds": "{:,.0f}"
        })

        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        st.caption(f"{len(display_df)} transfers")
