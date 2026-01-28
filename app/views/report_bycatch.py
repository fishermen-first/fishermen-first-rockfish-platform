"""Report Bycatch Hotspot - Vessel owner form to report bycatch encounters with multi-haul support."""

import streamlit as st
from datetime import datetime
from app.config import supabase
from app.auth import require_role
from app.utils.coordinates import format_coordinates_dms
from app.components.coordinate_input import render_coordinate_format_toggle
from app.components.haul_form import render_multi_haul_section, validate_haul_data


@st.cache_data(ttl=300)
def _fetch_psc_species():
    """Cached: Fetch PSC (Prohibited Species Catch) species for dropdown."""
    response = supabase.table("species").select(
        "code, species_name, unit"
    ).eq("is_psc", True).order("species_name").execute()
    return response.data if response.data else []


@st.cache_data(ttl=300)
def _fetch_rpca_areas():
    """Cached: Fetch RPCA areas for dropdown."""
    response = supabase.table("rpca_areas").select(
        "id, code, name"
    ).order("code").execute()
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


def insert_bycatch_alert_with_hauls(
    llp: str,
    species_code: int,
    hauls: list[dict],
    details: str | None,
    user_id: str,
    org_id: str
) -> tuple[bool, str | None]:
    """
    Insert a new bycatch alert with multiple hauls.

    Args:
        llp: Reporting vessel's LLP
        species_code: PSC species code
        hauls: List of haul data dicts
        details: Optional free-form details
        user_id: ID of user creating the report
        org_id: Organization ID for multi-tenant isolation

    Returns:
        Tuple of (success: bool, error: str | None)
    """
    try:
        if not hauls:
            return False, "At least one haul is required"

        # Validate all hauls
        for haul in hauls:
            valid, error = validate_haul_data(haul)
            if not valid:
                return False, f"Haul {haul.get('haul_number', '?')}: {error}"

        first_haul = hauls[0]
        total_amount = sum(h["amount"] for h in hauls)
        clean_details = details.strip() if details else None

        # Create parent alert with legacy columns
        alert_record = {
            "org_id": org_id,
            "reported_by_llp": llp,
            "species_code": species_code,
            "latitude": first_haul["set_latitude"],
            "longitude": first_haul["set_longitude"],
            "amount": total_amount,
            "details": clean_details,
            "status": "pending",
            "created_by": user_id,
            "is_deleted": False
        }

        response = supabase.table("bycatch_alerts").insert(alert_record).execute()

        if not response.data:
            return False, "Failed to create alert"

        alert_id = response.data[0]["id"]

        # Create hauls
        haul_records = []
        for i, haul in enumerate(hauls, 1):
            record = {
                "alert_id": alert_id,
                "haul_number": i,
                "location_name": haul.get("location_name"),
                "high_salmon_encounter": haul.get("high_salmon_encounter", False),
                "set_date": haul["set_date"].isoformat() if haul.get("set_date") else None,
                "set_time": haul["set_time"].isoformat() if haul.get("set_time") else None,
                "set_latitude": haul["set_latitude"],
                "set_longitude": haul["set_longitude"],
                "retrieval_date": haul["retrieval_date"].isoformat() if haul.get("retrieval_date") else None,
                "retrieval_time": haul["retrieval_time"].isoformat() if haul.get("retrieval_time") else None,
                "retrieval_latitude": haul.get("retrieval_latitude"),
                "retrieval_longitude": haul.get("retrieval_longitude"),
                "bottom_depth": haul.get("bottom_depth"),
                "sea_depth": haul.get("sea_depth"),
                "rpca_area_id": haul.get("rpca_area_id"),
                "amount": haul["amount"]
            }
            haul_records.append(record)

        haul_response = supabase.table("bycatch_hauls").insert(haul_records).execute()

        if not haul_response.data:
            # Rollback: soft delete the alert
            supabase.table("bycatch_alerts").update({
                "is_deleted": True
            }).eq("id", alert_id).execute()
            return False, "Failed to create hauls"

        return True, None

    except Exception as e:
        return False, str(e)


def show():
    """Display the bycatch report form for vessel owners with multi-haul support."""
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
    rpca_areas = _fetch_rpca_areas()

    if not psc_species:
        st.warning("No PSC species found. Please ensure species table has is_psc=true entries.")
        return

    # --- SPECIES SELECTION ---
    section_header("SPECIES", "🐟")

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
        amount_unit = "count" if unit == "count" else "lbs"
    else:
        amount_unit = "lbs"

    # --- COORDINATE FORMAT ---
    section_header("COORDINATE FORMAT", "🧭")
    use_dms = render_coordinate_format_toggle(key="report_coord_format")

    # --- HAUL DETAILS ---
    section_header("HAUL DETAILS", "📍")
    st.caption("Enter details for each haul/tow where bycatch was encountered")

    haul_data_list = render_multi_haul_section(
        key_prefix="report",
        rpca_areas=rpca_areas,
        use_dms_format=use_dms,
        amount_unit=amount_unit
    )

    # --- DETAILS AND SUBMIT ---
    section_header("ADDITIONAL DETAILS", "📝")

    with st.form("bycatch_report_form", clear_on_submit=False):
        details = st.text_area(
            "Details (optional)",
            max_chars=1000,
            placeholder="Describe conditions, gear type, observations, etc.",
            help="Any additional information that might help other vessels"
        )

        submitted = st.form_submit_button("Submit Report", use_container_width=True, type="primary")

    # Handle submission
    if submitted:
        if not haul_data_list:
            st.error("At least one haul is required.")
        else:
            species_code = psc_species[selected_species_name]["code"]

            # Get user ID and org_id
            user_id = st.session_state.user.id if st.session_state.user else "unknown"
            org_id = st.session_state.get("org_id")

            if not org_id:
                st.error("Organization not set. Please log out and log back in.")
                return

            # Use user's LLP
            reporting_llp = user_llp
            if not reporting_llp:
                st.error("No LLP associated with your account. Cannot submit report.")
                return

            success, error = insert_bycatch_alert_with_hauls(
                llp=reporting_llp,
                species_code=species_code,
                hauls=haul_data_list,
                details=details,
                user_id=user_id,
                org_id=org_id
            )

            if success:
                total_amount = sum(h["amount"] for h in haul_data_list)
                unit_display = "fish" if amount_unit == "count" else "lbs"
                # Clear session state for hauls
                if "report_haul_numbers" in st.session_state:
                    del st.session_state["report_haul_numbers"]
                st.success(
                    f"Bycatch report submitted with {len(haul_data_list)} haul(s)! "
                    f"Species: {selected_species_name} | "
                    f"Total: {total_amount:,.0f} {unit_display}"
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
                        "dismissed": "❌",
                        "resolved": "🔵"
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
