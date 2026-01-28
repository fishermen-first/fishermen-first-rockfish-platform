"""
Reusable haul entry component for bycatch alerts.

Each haul captures detailed fishing operation data including:
- Set and retrieval times/locations
- Depth information
- RPCA area for reporting
- Amount caught
"""

import streamlit as st
from datetime import date, time
from typing import Callable

from app.utils.coordinates import decimal_to_dms
from app.components.coordinate_input import (
    render_coordinate_inputs,
    render_decimal_coordinate_inputs
)


def render_haul_form(
    haul_number: int,
    key_prefix: str,
    rpca_areas: list[dict],
    existing_data: dict | None = None,
    use_dms_format: bool = True,
    show_remove_button: bool = True,
    on_remove: Callable[[int], None] | None = None,
    amount_unit: str = "lbs"
) -> dict | None:
    """
    Render a single haul entry form.

    Args:
        haul_number: Display number (1-based)
        key_prefix: Unique key prefix for widgets
        rpca_areas: List of {id, code, name} dicts for dropdown
        existing_data: Pre-fill values for edit mode
        use_dms_format: True for DMS, False for decimal coordinates
        show_remove_button: Whether to show remove option
        on_remove: Callback when remove is clicked
        amount_unit: Unit label for amount field ("lbs" or "count")

    Returns:
        Dict of haul data or None if removed
    """
    with st.container():
        # Header with haul number and optional remove button
        col_title, col_remove = st.columns([4, 1])
        with col_title:
            st.markdown(f"### Haul {haul_number}")
        with col_remove:
            if show_remove_button and haul_number > 1:
                if st.button("Remove", key=f"{key_prefix}_remove", type="secondary"):
                    if on_remove:
                        on_remove(haul_number)
                    return None

        # Row 1: Location name and salmon encounter flag
        col1, col2 = st.columns([3, 1])
        with col1:
            location_name = st.text_input(
                "Location Name (optional)",
                value=existing_data.get("location_name", "") if existing_data else "",
                key=f"{key_prefix}_location",
                placeholder="e.g., Tater, Shit Hole, etc."
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            high_salmon = st.checkbox(
                "High Salmon",
                value=existing_data.get("high_salmon_encounter", False) if existing_data else False,
                key=f"{key_prefix}_salmon",
                help="Flag this haul for high salmon bycatch attention"
            )

        # SET Information Section
        st.markdown("**Set Information** (gear deployment)")
        col_date, col_time = st.columns(2)
        with col_date:
            set_date_val = date.today()
            if existing_data and existing_data.get("set_date"):
                set_date_val = existing_data["set_date"]
                if isinstance(set_date_val, str):
                    set_date_val = date.fromisoformat(set_date_val)
            set_date = st.date_input(
                "Set Date *",
                value=set_date_val,
                key=f"{key_prefix}_set_date"
            )
        with col_time:
            set_time_val = None
            if existing_data and existing_data.get("set_time"):
                set_time_val = existing_data["set_time"]
                if isinstance(set_time_val, str):
                    set_time_val = time.fromisoformat(set_time_val)
            set_time = st.time_input(
                "Set Time (optional)",
                value=set_time_val,
                key=f"{key_prefix}_set_time"
            )

        # Set coordinates
        if use_dms_format:
            # Get defaults from existing data
            default_lat_deg = 57
            default_lon_deg = 152
            default_lat_min = 0.0
            default_lon_min = 0.0
            if existing_data and existing_data.get("set_latitude"):
                deg, mins, _ = decimal_to_dms(existing_data["set_latitude"], is_latitude=True)
                default_lat_deg = deg
                default_lat_min = mins
            if existing_data and existing_data.get("set_longitude"):
                deg, mins, _ = decimal_to_dms(existing_data["set_longitude"], is_latitude=False)
                default_lon_deg = deg
                default_lon_min = mins

            set_lat, set_lon = render_coordinate_inputs(
                lat_key_prefix=f"{key_prefix}_set_",
                lon_key_prefix=f"{key_prefix}_set_",
                default_lat_deg=default_lat_deg,
                default_lon_deg=default_lon_deg,
                default_lat_min=default_lat_min,
                default_lon_min=default_lon_min,
                label_prefix="Set "
            )
        else:
            default_lat = existing_data.get("set_latitude", 57.0) if existing_data else 57.0
            default_lon = existing_data.get("set_longitude", -152.0) if existing_data else -152.0
            set_lat, set_lon = render_decimal_coordinate_inputs(
                lat_key_prefix=f"{key_prefix}_set_",
                lon_key_prefix=f"{key_prefix}_set_",
                label_prefix="Set ",
                default_lat=default_lat,
                default_lon=default_lon
            )

        # RETRIEVAL Information Section (optional)
        st.markdown("**Retrieval Information** (optional)")
        col_rdate, col_rtime = st.columns(2)
        with col_rdate:
            ret_date_val = None
            if existing_data and existing_data.get("retrieval_date"):
                ret_date_val = existing_data["retrieval_date"]
                if isinstance(ret_date_val, str):
                    ret_date_val = date.fromisoformat(ret_date_val)
            retrieval_date = st.date_input(
                "Retrieval Date",
                value=ret_date_val,
                key=f"{key_prefix}_ret_date"
            )
        with col_rtime:
            ret_time_val = None
            if existing_data and existing_data.get("retrieval_time"):
                ret_time_val = existing_data["retrieval_time"]
                if isinstance(ret_time_val, str):
                    ret_time_val = time.fromisoformat(ret_time_val)
            retrieval_time = st.time_input(
                "Retrieval Time",
                value=ret_time_val,
                key=f"{key_prefix}_ret_time"
            )

        # Retrieval coordinates (optional)
        if use_dms_format:
            default_ret_lat_deg = 57
            default_ret_lon_deg = 152
            default_ret_lat_min = 0.0
            default_ret_lon_min = 0.0
            if existing_data and existing_data.get("retrieval_latitude"):
                deg, mins, _ = decimal_to_dms(existing_data["retrieval_latitude"], is_latitude=True)
                default_ret_lat_deg = deg
                default_ret_lat_min = mins
            if existing_data and existing_data.get("retrieval_longitude"):
                deg, mins, _ = decimal_to_dms(existing_data["retrieval_longitude"], is_latitude=False)
                default_ret_lon_deg = deg
                default_ret_lon_min = mins

            ret_lat, ret_lon = render_coordinate_inputs(
                lat_key_prefix=f"{key_prefix}_ret_",
                lon_key_prefix=f"{key_prefix}_ret_",
                default_lat_deg=default_ret_lat_deg,
                default_lon_deg=default_ret_lon_deg,
                default_lat_min=default_ret_lat_min,
                default_lon_min=default_ret_lon_min,
                label_prefix="Retrieval ",
                allow_empty=True
            )
        else:
            default_ret_lat = existing_data.get("retrieval_latitude") if existing_data else None
            default_ret_lon = existing_data.get("retrieval_longitude") if existing_data else None
            ret_lat, ret_lon = render_decimal_coordinate_inputs(
                lat_key_prefix=f"{key_prefix}_ret_",
                lon_key_prefix=f"{key_prefix}_ret_",
                label_prefix="Retrieval ",
                default_lat=default_ret_lat,
                default_lon=default_ret_lon,
                allow_empty=True
            )

        # Depth and RPCA row
        st.markdown("**Depth & Area**")
        col_bd, col_sd, col_rpca = st.columns(3)
        with col_bd:
            bottom_depth_val = existing_data.get("bottom_depth") if existing_data else None
            bottom_depth = st.number_input(
                "Bottom Depth (fathoms)",
                min_value=0,
                max_value=2000,
                value=bottom_depth_val,
                key=f"{key_prefix}_bottom_depth",
                help="Ocean floor depth"
            )
        with col_sd:
            sea_depth_val = existing_data.get("sea_depth") if existing_data else None
            sea_depth = st.number_input(
                "Sea Depth (fathoms)",
                min_value=0,
                max_value=2000,
                value=sea_depth_val,
                key=f"{key_prefix}_sea_depth",
                help="Depth gear was fishing"
            )
        with col_rpca:
            # Build RPCA options
            rpca_options = {"-- Select --": None}
            for area in rpca_areas:
                rpca_options[f"{area['code']} - {area['name']}"] = area["id"]

            # Find current selection
            current_rpca_id = existing_data.get("rpca_area_id") if existing_data else None
            current_display = "-- Select --"
            for name, id_ in rpca_options.items():
                if id_ == current_rpca_id:
                    current_display = name
                    break

            selected_rpca_name = st.selectbox(
                "RPCA Area",
                options=list(rpca_options.keys()),
                index=list(rpca_options.keys()).index(current_display),
                key=f"{key_prefix}_rpca"
            )
            rpca_area_id = rpca_options[selected_rpca_name]

        # Amount
        amount_val = existing_data.get("amount", 100.0) if existing_data else 100.0
        amount = st.number_input(
            f"Amount ({amount_unit}) *",
            min_value=1.0,
            value=float(amount_val),
            step=10.0,
            key=f"{key_prefix}_amount"
        )

        st.divider()

        return {
            "haul_number": haul_number,
            "location_name": location_name.strip() if location_name else None,
            "high_salmon_encounter": high_salmon,
            "set_date": set_date,
            "set_time": set_time,
            "set_latitude": set_lat,
            "set_longitude": set_lon,
            "retrieval_date": retrieval_date,
            "retrieval_time": retrieval_time,
            "retrieval_latitude": ret_lat,
            "retrieval_longitude": ret_lon,
            "bottom_depth": bottom_depth if bottom_depth and bottom_depth > 0 else None,
            "sea_depth": sea_depth if sea_depth and sea_depth > 0 else None,
            "rpca_area_id": rpca_area_id,
            "amount": amount
        }


def render_multi_haul_section(
    key_prefix: str,
    rpca_areas: list[dict],
    use_dms_format: bool = True,
    amount_unit: str = "lbs",
    existing_hauls: list[dict] | None = None
) -> list[dict]:
    """
    Render a multi-haul section with Add/Remove functionality.

    Args:
        key_prefix: Unique key prefix for session state and widgets
        rpca_areas: List of {id, code, name} dicts for dropdown
        use_dms_format: True for DMS, False for decimal coordinates
        amount_unit: Unit label for amount field
        existing_hauls: Pre-fill hauls for edit mode

    Returns:
        List of haul data dicts
    """
    # Initialize hauls in session state
    state_key = f"{key_prefix}_haul_numbers"
    if state_key not in st.session_state:
        if existing_hauls:
            st.session_state[state_key] = [h["haul_number"] for h in existing_hauls]
        else:
            st.session_state[state_key] = [1]  # Start with haul 1

    # Build existing data map
    existing_data_map = {}
    if existing_hauls:
        for h in existing_hauls:
            existing_data_map[h["haul_number"]] = h

    haul_data_list = []

    def remove_haul(haul_num: int):
        if haul_num in st.session_state[state_key]:
            st.session_state[state_key].remove(haul_num)
            st.rerun()

    for haul_num in st.session_state[state_key]:
        existing = existing_data_map.get(haul_num)
        haul_data = render_haul_form(
            haul_number=haul_num,
            key_prefix=f"{key_prefix}_haul_{haul_num}",
            rpca_areas=rpca_areas,
            existing_data=existing,
            use_dms_format=use_dms_format,
            show_remove_button=len(st.session_state[state_key]) > 1,
            on_remove=remove_haul,
            amount_unit=amount_unit
        )
        if haul_data:
            haul_data_list.append(haul_data)

    # Add Haul button
    if st.button("+ Add Haul", key=f"{key_prefix}_add_haul", type="secondary"):
        next_num = max(st.session_state[state_key]) + 1
        st.session_state[state_key].append(next_num)
        st.rerun()

    return haul_data_list


def validate_haul_data(haul: dict) -> tuple[bool, str | None]:
    """
    Validate haul data before saving.

    Args:
        haul: Haul data dict from render_haul_form

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Required fields
    if not haul.get("set_date"):
        return False, "Set date is required"

    if haul.get("set_latitude") is None:
        return False, "Set latitude is required"

    if haul.get("set_longitude") is None:
        return False, "Set longitude is required"

    if not haul.get("amount") or haul["amount"] <= 0:
        return False, "Amount must be greater than zero"

    # Coordinate bounds (Alaska waters)
    lat = haul.get("set_latitude")
    if lat is not None and (lat < 50.0 or lat > 72.0):
        return False, f"Set latitude {lat} is outside Alaska bounds (50-72° N)"

    lon = haul.get("set_longitude")
    if lon is not None and (lon < -180.0 or lon > -130.0):
        return False, f"Set longitude {lon} is outside Alaska bounds (130-180° W)"

    # Optional retrieval coordinates
    ret_lat = haul.get("retrieval_latitude")
    if ret_lat is not None and (ret_lat < 50.0 or ret_lat > 72.0):
        return False, f"Retrieval latitude {ret_lat} is outside Alaska bounds (50-72° N)"

    ret_lon = haul.get("retrieval_longitude")
    if ret_lon is not None and (ret_lon < -180.0 or ret_lon > -130.0):
        return False, f"Retrieval longitude {ret_lon} is outside Alaska bounds (130-180° W)"

    return True, None
