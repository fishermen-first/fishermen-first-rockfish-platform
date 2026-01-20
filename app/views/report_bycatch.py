"""Report Bycatch Hotspot - Vessel owner form to report bycatch encounters."""

import streamlit as st
from datetime import datetime
from app.config import supabase
from app.auth import require_role
from app.utils.coordinates import (
    dms_to_decimal,
    decimal_to_dms,
    format_coordinates_dms,
    validate_latitude_dms,
    validate_longitude_dms
)


@st.cache_data(ttl=300)
def _fetch_psc_species():
    """Cached: Fetch PSC (Prohibited Species Catch) species for dropdown."""
    response = supabase.table("species").select(
        "code, species_name, unit"
    ).eq("is_psc", True).order("species_name").execute()
    return response.data if response.data else []


def get_psc_species_options() -> dict[str, dict]:
    """
    Get PSC species for dropdown display with unit info.

    Returns:
        Dict mapping species_name -> {code, unit}
    """
    data = _fetch_psc_species()
    return {
        row["species_name"]: {"code": row["code"], "unit": row.get("unit", "lbs")}
        for row in data
    }


def insert_bycatch_alert(
    llp: str,
    species_code: int,
    latitude: float,
    longitude: float,
    amount: float,
    unit: str,
    details: str | None,
    user_id: str,
    org_id: str
) -> tuple[bool, str | None]:
    """
    Insert a new bycatch alert report.

    Args:
        llp: Reporting vessel's LLP
        species_code: PSC species code
        latitude: GPS latitude
        longitude: GPS longitude
        amount: Estimated amount/count
        unit: Unit of measurement ('lbs' or 'count')
        details: Optional free-form details
        user_id: ID of user creating the report
        org_id: Organization ID for multi-tenant isolation

    Returns:
        Tuple of (success: bool, error: str | None)
    """
    try:
        clean_details = details.strip() if details else None
        clean_details = clean_details if clean_details else None

        record = {
            "org_id": org_id,
            "reported_by_llp": llp,
            "species_code": species_code,
            "latitude": latitude,
            "longitude": longitude,
            "amount": amount,
            "unit": unit,
            "details": clean_details,
            "status": "pending",
            "created_by": user_id,
            "is_deleted": False
        }

        response = supabase.table("bycatch_alerts").insert(record).execute()

        if response.data:
            return True, None
        return False, "Insert returned no data"

    except Exception as e:
        return False, str(e)


def show():
    """Display the bycatch report form for vessel owners."""
    from app.utils.styles import page_header, section_header

    # Role check - vessel_owner can access, but admin/manager can too
    role = st.session_state.get("user_role")
    if role not in ["vessel_owner", "admin", "manager"]:
        st.error("You don't have permission to access this page.")
        return

    # Get user's LLP (required for vessel_owner, optional for admin/manager)
    user_llp = st.session_state.get("user_llp")

    if role == "vessel_owner" and not user_llp:
        st.error("Your account is not linked to a vessel. Please contact your administrator.")
        return

    page_header(
        "Report Bycatch Hotspot",
        "Alert the fleet to high bycatch areas"
    )

    # Get PSC species options: {species_name: {code, unit}}
    psc_species = get_psc_species_options()

    if not psc_species:
        st.warning("No PSC species found. Please ensure species table has is_psc=true entries.")
        return

    # --- REPORT FORM ---
    section_header("LOCATION & SPECIES", "📍")

    # Latitude in DMS format (captain-friendly)
    st.caption("**Latitude** (50° - 72° N for Alaska)")
    lat_col1, lat_col2, lat_col3 = st.columns([2, 2, 1])
    with lat_col1:
        lat_deg = st.number_input(
            "Degrees",
            min_value=50,
            max_value=72,
            value=57,
            step=1,
            key="lat_deg"
        )
    with lat_col2:
        lat_min = st.number_input(
            "Minutes",
            min_value=0.0,
            max_value=59.9,
            value=0.0,
            step=0.1,
            format="%.1f",
            key="lat_min"
        )
    with lat_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("**N**")

    # Longitude in DMS format (captain-friendly)
    st.caption("**Longitude** (130° - 180° W for Alaska)")
    lon_col1, lon_col2, lon_col3 = st.columns([2, 2, 1])
    with lon_col1:
        lon_deg = st.number_input(
            "Degrees",
            min_value=130,
            max_value=180,
            value=152,
            step=1,
            key="lon_deg"
        )
    with lon_col2:
        lon_min = st.number_input(
            "Minutes",
            min_value=0.0,
            max_value=59.9,
            value=0.0,
            step=0.1,
            format="%.1f",
            key="lon_min"
        )
    with lon_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("**W**")

    # Convert DMS to decimal for storage
    latitude = dms_to_decimal(lat_deg, lat_min, 'N')
    longitude = dms_to_decimal(lon_deg, lon_min, 'W')

    # Species selection (outside form for dynamic label updates)
    species_options = list(psc_species.keys())

    selected_species_name = st.selectbox(
        "Bycatch Species",
        options=species_options,
        key="bycatch_species_select"
    )

    # Get unit for selected species
    if selected_species_name:
        species_info = psc_species[selected_species_name]
        unit = species_info["unit"]
    else:
        unit = "lbs"

    section_header("AMOUNT & DETAILS", "📊")

    # Amount with dynamic label based on species
    amount_label = "Count (number of fish)" if unit == "count" else "Amount (lbs)"
    amount = st.number_input(
        amount_label,
        min_value=1.0,
        max_value=1000000.0,
        value=100.0,
        step=1.0 if unit == "count" else 10.0,
        help="Estimated count of fish" if unit == "count" else "Estimated pounds of bycatch"
    )

    # Form for details and submit
    with st.form("bycatch_report_form", clear_on_submit=True):
        details = st.text_area(
            "Details (optional)",
            max_chars=1000,
            placeholder="Describe conditions, depth, time of day, gear type, etc.",
            help="Any additional information that might help other vessels"
        )

        submitted = st.form_submit_button("Submit Report", use_container_width=True)

    # Handle submission
    if submitted:
        species_code = psc_species[selected_species_name]["code"]

        # Validation (DMS inputs have built-in range constraints)
        if amount <= 0:
            st.error("Amount must be greater than zero.")
        else:
            # Get user ID and org_id
            user_id = st.session_state.user.id if st.session_state.user else "unknown"
            org_id = st.session_state.get("org_id")

            if not org_id:
                st.error("Organization not set. Please log out and log back in.")
                return

            # Use user's LLP or prompt for selection (for admin/manager testing)
            reporting_llp = user_llp
            if not reporting_llp:
                st.error("No LLP associated with your account. Cannot submit report.")
                return

            success, error = insert_bycatch_alert(
                llp=reporting_llp,
                species_code=species_code,
                latitude=latitude,
                longitude=longitude,
                amount=amount,
                unit=unit,
                details=details,
                user_id=user_id,
                org_id=org_id
            )

            if success:
                unit_display = "fish" if unit == "count" else "lbs"
                coords_display = format_coordinates_dms(latitude, longitude)
                st.success(
                    f"Bycatch report submitted! "
                    f"Location: {coords_display} | "
                    f"Species: {selected_species_name} | "
                    f"Amount: {amount:,.0f} {unit_display}"
                )
                st.info("Your co-op manager will review and share this alert with the fleet.")
                st.rerun()
            else:
                st.error(f"Failed to submit report: {error}")

    # Show recent reports from this vessel
    st.divider()
    section_header("YOUR RECENT REPORTS", "📜")

    if user_llp:
        try:
            response = supabase.table("bycatch_alerts").select(
                "id, species_code, latitude, longitude, amount, unit, status, created_at"
            ).eq("reported_by_llp", user_llp).eq(
                "is_deleted", False
            ).order("created_at", desc=True).limit(5).execute()

            if response.data:
                # Build species code -> name lookup
                species_code_to_name = {
                    info["code"]: name for name, info in psc_species.items()
                }

                for alert in response.data:
                    status_emoji = {
                        "pending": "⏳",
                        "shared": "✅",
                        "dismissed": "❌"
                    }.get(alert["status"], "❓")

                    species_name = species_code_to_name.get(
                        alert["species_code"], f"Code {alert['species_code']}"
                    )
                    created = datetime.fromisoformat(alert["created_at"].replace("Z", "+00:00"))
                    alert_unit = alert.get("unit", "lbs")
                    unit_display = "fish" if alert_unit == "count" else "lbs"
                    coords_display = format_coordinates_dms(
                        float(alert['latitude']), float(alert['longitude'])
                    )

                    st.markdown(
                        f"{status_emoji} **{species_name}** - {alert['amount']:,.0f} {unit_display} @ "
                        f"{coords_display} - "
                        f"*{created.strftime('%b %d, %H:%M')}* - Status: {alert['status']}"
                    )
            else:
                st.info("No recent reports from your vessel.")
        except Exception as e:
            st.warning(f"Could not load recent reports: {e}")
    else:
        st.info("Link your account to a vessel to see your report history.")
