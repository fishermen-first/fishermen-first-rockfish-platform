"""Bycatch Alerts Management - Manager/Admin page for reviewing and sharing alerts."""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from app.config import supabase
from app.utils.styles import page_header, section_header, NAVY, GRAY_TEXT
from app.utils.coordinates import (
    dms_to_decimal,
    decimal_to_dms,
    format_coordinates_dms,
    validate_latitude_dms,
    validate_longitude_dms
)

# Brand colors for create alert section
TEAL = "#0d9488"


def _apply_create_alert_styles():
    """Apply CSS for the maritime-styled create alert section."""
    st.markdown(f"""
    <style>
        /* Create alert container styling */
        .create-alert-container {{
            background: white;
            border-left: 4px solid {NAVY};
            border-radius: 0 8px 8px 0;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .create-alert-header {{
            color: {NAVY};
            font-size: 1.1rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .create-alert-subtext {{
            color: {GRAY_TEXT};
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }}
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# CACHED DATA FETCHING
# =============================================================================

@st.cache_data(ttl=60)
def _fetch_alerts(org_id: str, status: str | None = None):
    """Cached: Fetch bycatch alerts with optional status filter."""
    query = supabase.table("bycatch_alerts").select(
        "id, org_id, reported_by_llp, species_code, latitude, longitude, "
        "amount, details, status, created_at, created_by, "
        "shared_at, shared_by, shared_recipient_count"
    ).eq("org_id", org_id).eq("is_deleted", False)

    if status:
        query = query.eq("status", status)

    response = query.order("created_at", desc=True).execute()
    return response.data if response.data else []


@st.cache_data(ttl=300)
def _fetch_psc_species():
    """Cached: Fetch PSC species for display."""
    response = supabase.table("species").select(
        "code, species_name, unit"
    ).eq("is_psc", True).order("species_name").execute()
    return response.data if response.data else []


@st.cache_data(ttl=300)
def _fetch_coop_members():
    """Cached: Fetch coop members for filtering and display."""
    response = supabase.table("coop_members").select(
        "llp, vessel_name, coop_code"
    ).order("llp").execute()
    return response.data if response.data else []


@st.cache_data(ttl=300)
def _fetch_coops():
    """Cached: Fetch cooperatives for filter dropdown."""
    response = supabase.table("cooperatives").select(
        "coop_code, coop_name"
    ).order("coop_name").execute()
    return response.data if response.data else []


@st.cache_data(ttl=300)
def _fetch_vessels_for_dropdown():
    """Cached: Fetch vessels with LLP and name for dropdown."""
    response = supabase.table("coop_members").select(
        "llp, vessel_name"
    ).order("vessel_name").execute()
    return response.data if response.data else []


@st.cache_data(ttl=60)
def _fetch_vessel_contacts_count(org_id: str):
    """Cached: Get count of vessel contacts for recipient display."""
    response = supabase.table("vessel_contacts").select(
        "id", count="exact"
    ).eq("org_id", org_id).eq("is_deleted", False).execute()
    return response.count if response.count else 0


def clear_alerts_cache():
    """Clear alerts cache after modifications."""
    _fetch_alerts.clear()


# =============================================================================
# DATA ACCESS FUNCTIONS
# =============================================================================

def get_pending_alert_count(org_id: str) -> int:
    """
    Get count of pending bycatch alerts for sidebar badge.

    Args:
        org_id: Organization ID

    Returns:
        Count of pending alerts
    """
    try:
        response = supabase.table("bycatch_alerts").select(
            "id", count="exact"
        ).eq("org_id", org_id).eq("status", "pending").eq("is_deleted", False).execute()
        return response.count if response.count else 0
    except Exception:
        return 0


def fetch_alerts(
    org_id: str,
    status: str | None = None,
    species_code: int | None = None,
    coop_code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None
) -> list[dict]:
    """
    Fetch alerts with optional filters.

    Args:
        org_id: Organization ID
        status: Filter by status (pending, shared, dismissed)
        species_code: Filter by PSC species
        coop_code: Filter by cooperative (filters LLPs in that coop)
        date_from: Filter alerts created on or after this date
        date_to: Filter alerts created on or before this date

    Returns:
        List of alert records
    """
    try:
        # Start with cached base query
        alerts = _fetch_alerts(org_id, status)

        # Apply additional filters in Python (for combined filters)
        if species_code:
            alerts = [a for a in alerts if a["species_code"] == species_code]

        if coop_code:
            # Get LLPs for this coop
            members = _fetch_coop_members()
            coop_llps = {m["llp"] for m in members if m.get("coop_code") == coop_code}
            alerts = [a for a in alerts if a["reported_by_llp"] in coop_llps]

        if date_from:
            alerts = [a for a in alerts if datetime.fromisoformat(
                a["created_at"].replace("Z", "+00:00")
            ).date() >= date_from]

        if date_to:
            alerts = [a for a in alerts if datetime.fromisoformat(
                a["created_at"].replace("Z", "+00:00")
            ).date() <= date_to]

        return alerts
    except Exception as e:
        st.error(f"Error fetching alerts: {e}")
        return []


def update_alert(
    alert_id: str,
    latitude: float | None = None,
    longitude: float | None = None,
    amount: float | None = None,
    details: str | None = None
) -> tuple[bool, str | None]:
    """
    Update alert details (for manager edits before sharing).

    Args:
        alert_id: Alert UUID
        latitude: New latitude (optional)
        longitude: New longitude (optional)
        amount: New amount (optional)
        details: New details (optional)

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # First check if alert is still pending
        check = supabase.table("bycatch_alerts").select(
            "status"
        ).eq("id", alert_id).execute()

        if not check.data:
            return False, "Alert not found"

        if check.data[0]["status"] != "pending":
            return False, "Cannot edit alert that is already shared or dismissed"

        # Build update payload
        updates = {}
        if latitude is not None:
            updates["latitude"] = latitude
        if longitude is not None:
            updates["longitude"] = longitude
        if amount is not None:
            updates["amount"] = amount
        if details is not None:
            updates["details"] = details.strip() if details else None

        if not updates:
            return True, None  # Nothing to update

        response = supabase.table("bycatch_alerts").update(
            updates
        ).eq("id", alert_id).execute()

        if response.data:
            clear_alerts_cache()
            return True, None
        return False, "Update returned no data"

    except Exception as e:
        return False, str(e)


def dismiss_alert(alert_id: str, user_id: str) -> tuple[bool, str | None]:
    """
    Dismiss an alert (soft delete workflow).

    Args:
        alert_id: Alert UUID
        user_id: ID of user dismissing the alert

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Check current status
        check = supabase.table("bycatch_alerts").select(
            "status"
        ).eq("id", alert_id).execute()

        if not check.data:
            return False, "Alert not found"

        if check.data[0]["status"] == "shared":
            return False, "Cannot dismiss alert that is already shared"

        response = supabase.table("bycatch_alerts").update({
            "status": "dismissed",
            "is_deleted": True,
            "deleted_by": user_id,
            "deleted_at": datetime.utcnow().isoformat()
        }).eq("id", alert_id).execute()

        if response.data:
            clear_alerts_cache()
            return True, None
        return False, "Dismiss operation returned no data"

    except Exception as e:
        return False, str(e)


def share_alert(alert_id: str, user_id: str) -> tuple[bool, dict]:
    """
    Share alert to fleet (marks as shared, email via Edge Function later).

    Args:
        alert_id: Alert UUID
        user_id: ID of user sharing the alert

    Returns:
        Tuple of (success, result_dict)
    """
    try:
        # Check current status
        check = supabase.table("bycatch_alerts").select(
            "status, shared_at"
        ).eq("id", alert_id).execute()

        if not check.data:
            return False, {"error": "Alert not found"}

        if check.data[0]["status"] == "shared":
            return True, {"already_shared": True, "shared_at": check.data[0]["shared_at"]}

        if check.data[0]["status"] == "dismissed":
            return False, {"error": "Cannot share a dismissed alert"}

        # Get recipient count
        org_id = st.session_state.get("org_id")
        recipient_count = _fetch_vessel_contacts_count(org_id) if org_id else 0

        # Update alert status
        response = supabase.table("bycatch_alerts").update({
            "status": "shared",
            "shared_at": datetime.utcnow().isoformat(),
            "shared_by": user_id,
            "shared_recipient_count": recipient_count
        }).eq("id", alert_id).execute()

        if response.data:
            clear_alerts_cache()
            # TODO: Call Edge Function to send emails
            # For now, just mark as shared
            return True, {"sent_count": recipient_count, "email_pending": True}

        return False, {"error": "Share operation returned no data"}

    except Exception as e:
        return False, {"error": str(e)}


def validate_alert_edit(
    latitude: float | None = None,
    longitude: float | None = None,
    amount: float | None = None
) -> tuple[bool, str | None]:
    """
    Validate alert edit values.

    Args:
        latitude: Latitude to validate
        longitude: Longitude to validate
        amount: Amount to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if latitude is not None:
        if latitude < 50.0 or latitude > 72.0:
            return False, "Latitude must be between 50.0 and 72.0 for Alaska waters"

    if longitude is not None:
        if longitude < -180.0 or longitude > -130.0:
            return False, "Longitude must be between -180.0 and -130.0 for Alaska waters"

    if amount is not None:
        if amount <= 0:
            return False, "Amount must be greater than zero"

    return True, None


def create_alert(
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
    Create a new bycatch alert on behalf of a vessel.

    Args:
        llp: Vessel LLP identifier
        species_code: PSC species code
        latitude: GPS latitude
        longitude: GPS longitude
        amount: Amount of bycatch
        unit: Unit of measurement ('lbs' or 'count')
        details: Optional details/notes
        user_id: ID of user creating the alert
        org_id: Organization ID

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Validate inputs
        valid, error = validate_alert_edit(
            latitude=latitude,
            longitude=longitude,
            amount=amount
        )
        if not valid:
            return False, error

        # Insert alert
        response = supabase.table("bycatch_alerts").insert({
            "org_id": org_id,
            "reported_by_llp": llp,
            "species_code": species_code,
            "latitude": latitude,
            "longitude": longitude,
            "amount": amount,
            "unit": unit,
            "details": details.strip() if details else None,
            "status": "pending",
            "created_by": user_id,
            "is_deleted": False
        }).execute()

        if response.data:
            clear_alerts_cache()
            return True, None
        return False, "Insert returned no data"

    except Exception as e:
        return False, str(e)


def generate_email_preview(alert: dict, species_list: list[dict]) -> dict:
    """
    Generate email preview content for an alert.

    Args:
        alert: Alert record
        species_list: List of species for name lookup

    Returns:
        Dict with 'subject' and 'body' keys
    """
    species_name = get_species_name(alert["species_code"], species_list)

    subject = f"Bycatch Alert - {species_name} Reported"

    body_parts = [
        f"**Species:** {species_name}",
        f"**Amount:** {alert['amount']:,.0f}",
        f"**Location:** {alert['latitude']:.4f}N, {abs(alert['longitude']):.4f}W",
        f"**Reported:** {format_timestamp(alert['created_at'])}",
    ]

    if alert.get("details"):
        body_parts.append(f"**Details:** {alert['details']}")

    body = "\n".join(body_parts)

    return {"subject": subject, "body": body}


def get_recipient_count(org_id: str) -> int:
    """Get count of email recipients for the organization."""
    return _fetch_vessel_contacts_count(org_id)


def fetch_delivery_log(alert_id: str) -> list[dict]:
    """
    Fetch email delivery log for an alert.

    Args:
        alert_id: Alert UUID

    Returns:
        List of log records
    """
    try:
        response = supabase.table("alert_email_log").select(
            "id, recipient_count, status, error_message, created_at"
        ).eq("alert_id", alert_id).order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception:
        return []


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def get_species_name(species_code: int, species_list: list[dict]) -> str:
    """Get species display name from code."""
    for s in species_list:
        if s["code"] == species_code:
            return s.get("species_name") or s.get("name") or f"Code {species_code}"
    return f"Unknown ({species_code})"


def get_vessel_name(llp: str, members: list[dict]) -> str:
    """Get vessel name from LLP."""
    for m in members:
        if m["llp"] == llp:
            return m.get("vessel_name") or llp
    return llp


def format_coordinates(lat: float, lon: float) -> str:
    """Format GPS coordinates for display in captain-friendly DMS format."""
    return format_coordinates_dms(lat, lon)


def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return timestamp_str


def truncate_details(text: str | None, max_length: int = 100) -> str:
    """Truncate long text with ellipsis."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def check_access() -> bool:
    """Check if current user has access to bycatch alerts management."""
    role = st.session_state.get("user_role")
    return role in ["admin", "manager"]


# =============================================================================
# CREATE ALERT SECTION
# =============================================================================

def _render_create_alert_section(
    species_list: list[dict],
    vessels: list[dict],
    user_id: str,
    org_id: str
):
    """Render styled create alert section with form."""

    # Build vessel options: "F/V Name (LLP-XXXXX)"
    vessel_options = {}
    for v in vessels:
        vessel_name = v.get("vessel_name") or "Unknown"
        llp = v.get("llp")
        if llp:
            label = f"{vessel_name} ({llp})"
            vessel_options[label] = llp

    if not vessel_options:
        st.warning("No vessels available for alert creation.")
        return

    # Build species options with unit info: {name: {code, unit}}
    species_info = {
        s["species_name"]: {"code": s["code"], "unit": s.get("unit", "lbs")}
        for s in species_list
    }

    if not species_info:
        st.warning("No PSC species configured.")
        return

    # Styled container
    with st.expander("CREATE NEW ALERT", expanded=True, icon=":material/pin_drop:"):
        st.caption("Report a bycatch hotspot on behalf of a vessel (e.g., from radio call)")

        # Species selector OUTSIDE form for dynamic label updates
        selected_species = st.selectbox(
            "Species",
            options=list(species_info.keys()),
            index=None,
            placeholder="Select species...",
            key="create_species_select"
        )

        # Determine unit based on selected species
        if selected_species:
            unit = species_info[selected_species]["unit"]
            amount_label = "Count (number of fish)" if unit == "count" else "Amount (lbs)"
        else:
            unit = "lbs"
            amount_label = "Amount (lbs)"

        with st.form("create_alert_form", clear_on_submit=True):
            # Vessel selector
            selected_vessel = st.selectbox(
                "Reporting Vessel",
                options=list(vessel_options.keys()),
                index=None,
                placeholder="Select vessel...",
                key="create_vessel"
            )

            # Latitude in DMS format (degrees + minutes)
            st.caption("**Latitude** (50° - 72° N for Alaska)")
            lat_col1, lat_col2, lat_col3 = st.columns([2, 2, 1])
            with lat_col1:
                lat_deg = st.number_input(
                    "Degrees",
                    min_value=50,
                    max_value=72,
                    value=57,
                    step=1,
                    key="create_lat_deg"
                )
            with lat_col2:
                lat_min = st.number_input(
                    "Minutes",
                    min_value=0.0,
                    max_value=59.9,
                    value=0.0,
                    step=0.1,
                    format="%.1f",
                    key="create_lat_min"
                )
            with lat_col3:
                st.markdown("<br>", unsafe_allow_html=True)
                st.write("**N**")

            # Longitude in DMS format (degrees + minutes)
            st.caption("**Longitude** (130° - 180° W for Alaska)")
            lon_col1, lon_col2, lon_col3 = st.columns([2, 2, 1])
            with lon_col1:
                lon_deg = st.number_input(
                    "Degrees",
                    min_value=130,
                    max_value=180,
                    value=152,
                    step=1,
                    key="create_lon_deg"
                )
            with lon_col2:
                lon_min = st.number_input(
                    "Minutes",
                    min_value=0.0,
                    max_value=59.9,
                    value=0.0,
                    step=0.1,
                    format="%.1f",
                    key="create_lon_min"
                )
            with lon_col3:
                st.markdown("<br>", unsafe_allow_html=True)
                st.write("**W**")

            # Convert DMS to decimal for storage
            latitude = dms_to_decimal(lat_deg, lat_min, 'N')
            longitude = dms_to_decimal(lon_deg, lon_min, 'W')

            # Amount with dynamic label
            amount = st.number_input(
                amount_label,
                min_value=1.0,
                value=100.0,
                step=10.0 if unit == "lbs" else 1.0,
                key="create_amount"
            )

            # Details
            details = st.text_area(
                "Details (optional)",
                placeholder="e.g., High concentration at 50 fathoms, moving NE...",
                max_chars=1000,
                key="create_details"
            )

            # Submit button
            submitted = st.form_submit_button(
                "Submit Alert",
                type="primary",
                use_container_width=True,
                icon=":material/warning:"
            )

            if submitted:
                # Validation
                if not selected_vessel:
                    st.error("Please select a reporting vessel.")
                elif not selected_species:
                    st.error("Please select a species.")
                else:
                    llp = vessel_options[selected_vessel]
                    species_code = species_info[selected_species]["code"]

                    success, error = create_alert(
                        llp=llp,
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
                        st.success(f"Alert created for {selected_vessel}!")
                        st.rerun()
                    else:
                        st.error(f"Failed to create alert: {error}")


# =============================================================================
# MAIN PAGE
# =============================================================================

def show():
    """Display the bycatch alerts management page."""

    # Access check
    if not check_access():
        st.error("You don't have permission to access this page.")
        return

    page_header(
        "Bycatch Alerts",
        "Review and share bycatch hotspot reports with the fleet"
    )

    # Apply custom styles
    _apply_create_alert_styles()

    org_id = st.session_state.get("org_id")
    if not org_id:
        st.error("Organization not set. Please log out and log back in.")
        return

    user_id = st.session_state.user.id if st.session_state.user else None

    # Load reference data
    species_list = _fetch_psc_species()
    members = _fetch_coop_members()
    coops = _fetch_coops()
    vessels = _fetch_vessels_for_dropdown()

    # --- CREATE ALERT SECTION ---
    _render_create_alert_section(species_list, vessels, user_id, org_id)

    # --- FILTERS ---
    section_header("FILTERS", "🔍")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        coop_options = {"All Co-ops": None}
        coop_options.update({c["coop_name"]: c["coop_code"] for c in coops})
        selected_coop_name = st.selectbox(
            "Cooperative",
            options=list(coop_options.keys()),
            key="alert_coop_filter"
        )
        selected_coop = coop_options[selected_coop_name]

    with col2:
        species_options = {"All Species": None}
        species_options.update({
            s["species_name"]: s["code"]
            for s in species_list
        })
        selected_species_name = st.selectbox(
            "Species",
            options=list(species_options.keys()),
            key="alert_species_filter"
        )
        selected_species = species_options[selected_species_name]

    with col3:
        date_from = st.date_input(
            "From Date",
            value=date.today() - timedelta(days=30),
            key="alert_date_from"
        )

    with col4:
        date_to = st.date_input(
            "To Date",
            value=date.today(),
            key="alert_date_to"
        )

    # --- TABS ---
    tab_pending, tab_shared, tab_all = st.tabs(["Pending", "Shared", "All"])

    # --- PENDING TAB ---
    with tab_pending:
        pending_alerts = fetch_alerts(
            org_id,
            status="pending",
            species_code=selected_species,
            coop_code=selected_coop,
            date_from=date_from,
            date_to=date_to
        )

        if not pending_alerts:
            st.info("No pending alerts match your filters.")
        else:
            st.markdown(f"**{len(pending_alerts)} pending alert(s)**")

            for alert in pending_alerts:
                _render_alert_card(
                    alert,
                    species_list,
                    members,
                    user_id,
                    org_id,
                    show_actions=True
                )

    # --- SHARED TAB ---
    with tab_shared:
        shared_alerts = fetch_alerts(
            org_id,
            status="shared",
            species_code=selected_species,
            coop_code=selected_coop,
            date_from=date_from,
            date_to=date_to
        )

        if not shared_alerts:
            st.info("No shared alerts match your filters.")
        else:
            st.markdown(f"**{len(shared_alerts)} shared alert(s)**")

            for alert in shared_alerts:
                _render_alert_card(
                    alert,
                    species_list,
                    members,
                    user_id,
                    org_id,
                    show_actions=False
                )

    # --- ALL TAB ---
    with tab_all:
        all_alerts = fetch_alerts(
            org_id,
            status=None,
            species_code=selected_species,
            coop_code=selected_coop,
            date_from=date_from,
            date_to=date_to
        )

        if not all_alerts:
            st.info("No alerts match your filters.")
        else:
            st.markdown(f"**{len(all_alerts)} total alert(s)**")

            for alert in all_alerts:
                show_actions = alert["status"] == "pending"
                _render_alert_card(
                    alert,
                    species_list,
                    members,
                    user_id,
                    org_id,
                    show_actions=show_actions
                )


def _render_alert_card(
    alert: dict,
    species_list: list[dict],
    members: list[dict],
    user_id: str | None,
    org_id: str,
    show_actions: bool = True
):
    """Render a single alert card with optional actions."""

    species_name = get_species_name(alert["species_code"], species_list)
    vessel_name = get_vessel_name(alert["reported_by_llp"], members)
    coords = format_coordinates(alert["latitude"], alert["longitude"])
    timestamp = format_timestamp(alert["created_at"])

    status_badges = {
        "pending": "🟡 Pending",
        "shared": "✅ Shared",
        "dismissed": "❌ Dismissed"
    }
    status_badge = status_badges.get(alert["status"], alert["status"])

    # Card container
    with st.container():
        st.markdown(f"""
        <div style="background: white; padding: 1rem; border-radius: 8px;
                    border: 1px solid #e2e8f0; margin-bottom: 1rem;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <span style="font-size: 1.2rem; font-weight: 600;">{species_name}</span>
                    <span style="margin-left: 1rem; color: {GRAY_TEXT};">{status_badge}</span>
                </div>
                <div style="color: {GRAY_TEXT}; font-size: 0.9rem;">{timestamp}</div>
            </div>
            <div style="margin-top: 0.5rem; color: {GRAY_TEXT};">
                <strong>Vessel:</strong> {vessel_name} ({alert['reported_by_llp']}) &nbsp;|&nbsp;
                <strong>Amount:</strong> {alert['amount']:,.0f} &nbsp;|&nbsp;
                <strong>Location:</strong> {coords}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Details if present
        if alert.get("details"):
            st.markdown(f"*Details:* {alert['details']}")

        # Shared info
        if alert["status"] == "shared" and alert.get("shared_at"):
            shared_time = format_timestamp(alert["shared_at"])
            recipient_count = alert.get("shared_recipient_count", 0)
            st.caption(f"Shared on {shared_time} to {recipient_count} recipients")

        # Action buttons for pending alerts
        if show_actions and alert["status"] == "pending":
            col1, col2, col3, col4 = st.columns([1, 1, 1, 2])

            with col1:
                if st.button("Edit", key=f"edit_{alert['id']}", use_container_width=True):
                    st.session_state[f"editing_{alert['id']}"] = True
                    st.rerun()

            with col2:
                if st.button("Preview", key=f"preview_{alert['id']}", use_container_width=True):
                    st.session_state[f"preview_{alert['id']}"] = True
                    st.rerun()

            with col3:
                if st.button("Share", key=f"share_{alert['id']}", type="primary", use_container_width=True):
                    if user_id:
                        success, result = share_alert(alert["id"], user_id)
                        if success:
                            if result.get("already_shared"):
                                st.info("Alert was already shared.")
                            else:
                                st.success(f"Alert shared to {result.get('sent_count', 0)} recipients!")
                            st.rerun()
                        else:
                            st.error(f"Failed to share: {result.get('error', 'Unknown error')}")

            with col4:
                if st.button("Dismiss", key=f"dismiss_{alert['id']}", use_container_width=True):
                    if user_id:
                        success, error = dismiss_alert(alert["id"], user_id)
                        if success:
                            st.success("Alert dismissed.")
                            st.rerun()
                        else:
                            st.error(f"Failed to dismiss: {error}")

            # Edit form (shown when editing)
            if st.session_state.get(f"editing_{alert['id']}"):
                _render_edit_form(alert, user_id)

            # Email preview (shown when previewing)
            if st.session_state.get(f"preview_{alert['id']}"):
                _render_email_preview(alert, species_list, org_id)

        st.divider()


def _render_edit_form(alert: dict, user_id: str | None):
    """Render inline edit form for an alert."""

    with st.expander("Edit Alert Details", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            new_lat = st.number_input(
                "Latitude",
                min_value=50.0,
                max_value=72.0,
                value=float(alert["latitude"]),
                step=0.001,
                format="%.6f",
                key=f"edit_lat_{alert['id']}"
            )

        with col2:
            new_lon = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=-130.0,
                value=float(alert["longitude"]),
                step=0.001,
                format="%.6f",
                key=f"edit_lon_{alert['id']}"
            )

        new_amount = st.number_input(
            "Amount",
            min_value=1.0,
            value=float(alert["amount"]),
            step=10.0,
            key=f"edit_amount_{alert['id']}"
        )

        new_details = st.text_area(
            "Details",
            value=alert.get("details") or "",
            max_chars=1000,
            key=f"edit_details_{alert['id']}"
        )

        col_save, col_cancel = st.columns(2)

        with col_save:
            if st.button("Save Changes", key=f"save_{alert['id']}", type="primary", use_container_width=True):
                # Validate
                valid, error = validate_alert_edit(
                    latitude=new_lat,
                    longitude=new_lon,
                    amount=new_amount
                )

                if not valid:
                    st.error(error)
                else:
                    success, error = update_alert(
                        alert["id"],
                        latitude=new_lat,
                        longitude=new_lon,
                        amount=new_amount,
                        details=new_details
                    )

                    if success:
                        st.success("Alert updated!")
                        st.session_state[f"editing_{alert['id']}"] = False
                        st.rerun()
                    else:
                        st.error(f"Failed to update: {error}")

        with col_cancel:
            if st.button("Cancel", key=f"cancel_{alert['id']}", use_container_width=True):
                st.session_state[f"editing_{alert['id']}"] = False
                st.rerun()


def _render_email_preview(alert: dict, species_list: list[dict], org_id: str):
    """Render email preview for an alert."""

    preview = generate_email_preview(alert, species_list)
    recipient_count = get_recipient_count(org_id)

    with st.expander("Email Preview", expanded=True):
        st.markdown(f"**Subject:** {preview['subject']}")
        st.divider()
        st.markdown(preview["body"])
        st.divider()
        st.caption(f"This email will be sent to **{recipient_count}** vessel contacts.")

        if st.button("Close Preview", key=f"close_preview_{alert['id']}", use_container_width=True):
            st.session_state[f"preview_{alert['id']}"] = False
            st.rerun()
