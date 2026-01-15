"""Vessel Owner View - read-only view of own vessel's quota, transfers, and harvests."""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_auth, is_vessel_owner, get_user_llp

CURRENT_YEAR = 2026
SPECIES_MAP = {141: "POP", 136: "NR", 172: "Dusky"}


# =============================================================================
# Cached data fetchers
# =============================================================================

@st.cache_data(ttl=300)
def _fetch_vessel_info(llp: str) -> dict:
    """Fetch vessel name and coop for this LLP."""
    try:
        response = supabase.table("coop_members").select(
            "vessel_name, coop_code"
        ).eq("llp", llp).execute()
        if response.data:
            return response.data[0]
        return {"vessel_name": "Unknown", "coop_code": "Unknown"}
    except Exception:
        return {"vessel_name": "Unknown", "coop_code": "Unknown"}


@st.cache_data(ttl=60)
def _fetch_my_quota(llp: str, year: int) -> list:
    """Fetch quota_remaining for this LLP."""
    try:
        response = supabase.table("quota_remaining").select(
            "species_code, allocation_lbs, transfers_in, transfers_out, harvested, remaining_lbs"
        ).eq("llp", llp).eq("year", year).execute()
        return response.data if response.data else []
    except Exception:
        return []


@st.cache_data(ttl=60)
def _fetch_my_transfers(llp: str, year: int) -> list:
    """Fetch transfers involving this LLP (in or out)."""
    try:
        response = supabase.table("quota_transfers").select(
            "id, from_llp, to_llp, species_code, pounds, transfer_date, notes, created_at"
        ).eq("year", year).eq("is_deleted", False).or_(
            f"from_llp.eq.{llp},to_llp.eq.{llp}"
        ).order("transfer_date", desc=True).execute()
        return response.data if response.data else []
    except Exception:
        return []


@st.cache_data(ttl=60)
def _fetch_my_harvests(llp: str, year: int) -> list:
    """Fetch harvests for this LLP."""
    try:
        response = supabase.table("harvests").select(
            "id, species_code, pounds, harvest_date, processor_code"
        ).eq("llp", llp).eq("is_deleted", False).order("harvest_date", desc=True).execute()
        return response.data if response.data else []
    except Exception:
        return []


@st.cache_data(ttl=300)
def _fetch_llp_vessel_map() -> dict:
    """Fetch LLP to vessel name mapping for transfer display."""
    try:
        response = supabase.table("coop_members").select("llp, vessel_name").execute()
        if response.data:
            return {r["llp"]: r["vessel_name"] for r in response.data}
        return {}
    except Exception:
        return {}


@st.cache_data(ttl=300)
def _fetch_processor_map() -> dict:
    """Fetch processor code to name mapping."""
    try:
        response = supabase.table("processors").select("processor_code, name").execute()
        if response.data:
            return {r["processor_code"]: r["name"] for r in response.data}
        return {}
    except Exception:
        return {}


# =============================================================================
# Helper functions
# =============================================================================

def format_lbs(value) -> str:
    """Format pounds as M, K, or raw number."""
    if value is None:
        return "N/A"
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.1f}M"
    elif abs_value >= 1_000:
        return f"{sign}{abs_value / 1_000:.1f}K"
    else:
        return f"{int(value)}"


def get_pct_color(pct) -> str:
    """Return color based on percent remaining."""
    if pct is None:
        return "#94a3b8"  # gray
    if pct < 10:
        return "#dc2626"  # red
    elif pct < 50:
        return "#d97706"  # amber
    return "#059669"  # green


def quota_card(species: str, remaining: float, allocation: float) -> str:
    """Generate HTML for a quota card."""
    if allocation and allocation > 0:
        pct = (remaining / allocation) * 100
    else:
        pct = None

    color = get_pct_color(pct)
    pct_display = f"{pct:.0f}%" if pct is not None else "N/A"

    return f"""
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); text-align: center;">
        <div style="color: #64748b; font-size: 14px; margin-bottom: 4px;">{species}</div>
        <div style="font-size: 28px; font-weight: bold; color: {color};">{format_lbs(remaining)}</div>
        <div style="color: #64748b; font-size: 13px; margin-top: 6px;">{pct_display} remaining</div>
    </div>
    """


# =============================================================================
# Main view
# =============================================================================

def show():
    """Display the vessel owner view."""
    # Auth check
    if not require_auth():
        return

    if not is_vessel_owner():
        st.error("This page is only for vessel owners.")
        return

    llp = get_user_llp()
    if not llp:
        st.error("Your account is not linked to a vessel. Please contact the administrator.")
        return

    # Fetch vessel info
    vessel_info = _fetch_vessel_info(llp)
    vessel_name = vessel_info.get("vessel_name", "Unknown")
    coop_code = vessel_info.get("coop_code", "Unknown")

    # Header
    from app.utils.styles import page_header, section_header
    page_header(f"My Vessel: {vessel_name}", f"LLP: {llp} | Co-Op: {coop_code} | Season: {CURRENT_YEAR}")

    # --- QUOTA REMAINING ---
    section_header("QUOTA REMAINING", "📊")

    quota_data = _fetch_my_quota(llp, CURRENT_YEAR)

    if not quota_data:
        st.info("No quota data available.")
    else:
        cols = st.columns(3)
        for i, species_code in enumerate([141, 136, 172]):
            species_name = SPECIES_MAP.get(species_code, f"Species {species_code}")
            species_data = next((q for q in quota_data if q["species_code"] == species_code), None)

            with cols[i]:
                if species_data:
                    st.markdown(
                        quota_card(species_name, species_data["remaining_lbs"], species_data["allocation_lbs"]),
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(quota_card(species_name, 0, 0), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- TRANSFER HISTORY ---
    section_header("TRANSFER HISTORY", "🔄")

    transfers = _fetch_my_transfers(llp, CURRENT_YEAR)

    if not transfers:
        st.info("No transfers for this season.")
    else:
        llp_vessel_map = _fetch_llp_vessel_map()

        # Build display data
        transfer_rows = []
        for t in transfers:
            direction = "IN" if t["to_llp"] == llp else "OUT"
            other_llp = t["from_llp"] if direction == "IN" else t["to_llp"]
            other_vessel = llp_vessel_map.get(other_llp, "Unknown")
            species = SPECIES_MAP.get(t["species_code"], str(t["species_code"]))

            transfer_rows.append({
                "Date": t["transfer_date"],
                "Direction": direction,
                "Species": species,
                "Pounds": t["pounds"],
                "Other Vessel": f"{other_vessel} ({other_llp})",
                "Notes": t.get("notes") or ""
            })

        df = pd.DataFrame(transfer_rows)

        # Style direction column
        def style_direction(val):
            if val == "IN":
                return "color: #059669; font-weight: bold;"
            return "color: #dc2626; font-weight: bold;"

        styled_df = df.style.applymap(style_direction, subset=["Direction"]).format({
            "Pounds": "{:,.0f}"
        })

        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        st.caption(f"{len(transfers)} transfers")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- HARVEST RECORDS ---
    section_header("HARVEST RECORDS", "🐟")

    harvests = _fetch_my_harvests(llp, CURRENT_YEAR)

    if not harvests:
        st.info("No harvest records for this season.")
    else:
        processor_map = _fetch_processor_map()

        harvest_rows = []
        for h in harvests:
            species = SPECIES_MAP.get(h["species_code"], str(h["species_code"]))
            processor = processor_map.get(h["processor_code"], h["processor_code"] or "Unknown")

            harvest_rows.append({
                "Date": h["harvest_date"],
                "Species": species,
                "Pounds": h["pounds"],
                "Processor": processor
            })

        df = pd.DataFrame(harvest_rows)
        styled_df = df.style.format({"Pounds": "{:,.0f}"})

        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        st.caption(f"{len(harvests)} harvest records")
