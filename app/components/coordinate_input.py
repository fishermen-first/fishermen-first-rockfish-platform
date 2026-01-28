"""
Shared coordinate input component for DMS (degrees/minutes) entry.

This component provides a captain-friendly interface for coordinate entry,
using degrees and decimal minutes rather than decimal degrees. It consolidates
duplicate coordinate input UI from report_bycatch.py and bycatch_alerts.py.
"""

import streamlit as st
from app.utils.coordinates import dms_to_decimal, decimal_to_dms


def render_coordinate_format_toggle(key: str = "coord_format") -> bool:
    """
    Render a toggle between DMS and Decimal coordinate formats.

    Args:
        key: Unique key for the radio widget

    Returns:
        True for DMS format, False for Decimal format
    """
    format_option = st.radio(
        "Coordinate Format",
        options=["Degrees/Minutes (DMS)", "Decimal Degrees"],
        horizontal=True,
        key=key
    )
    return format_option == "Degrees/Minutes (DMS)"


def render_decimal_coordinate_inputs(
    lat_key_prefix: str = "",
    lon_key_prefix: str = "",
    label_prefix: str = "",
    default_lat: float | None = 57.0,
    default_lon: float | None = -152.0,
    allow_empty: bool = False
) -> tuple[float | None, float | None]:
    """
    Render latitude/longitude input fields in decimal format.

    Args:
        lat_key_prefix: Prefix for latitude widget keys
        lon_key_prefix: Prefix for longitude widget keys
        label_prefix: Label prefix (e.g., "Set " or "Retrieval ")
        default_lat: Default latitude value
        default_lon: Default longitude value
        allow_empty: If True, returns None for empty values

    Returns:
        Tuple of (latitude_decimal, longitude_decimal) or (None, None) if empty
    """
    col1, col2 = st.columns(2)

    with col1:
        lat_value = default_lat if default_lat is not None else 57.0
        latitude = st.number_input(
            f"{label_prefix}Latitude" + (" *" if not allow_empty else ""),
            min_value=50.0,
            max_value=72.0,
            value=lat_value if not allow_empty else None,
            format="%.6f",
            key=f"{lat_key_prefix}lat_decimal",
            help="Alaska waters: 50° - 72° N"
        )

    with col2:
        lon_value = default_lon if default_lon is not None else -152.0
        longitude = st.number_input(
            f"{label_prefix}Longitude" + (" *" if not allow_empty else ""),
            min_value=-180.0,
            max_value=-130.0,
            value=lon_value if not allow_empty else None,
            format="%.6f",
            key=f"{lon_key_prefix}lon_decimal",
            help="Alaska waters: 130° - 180° W"
        )

    # Handle empty values
    if allow_empty and (latitude is None or longitude is None):
        return None, None

    return latitude, longitude


def render_coordinate_inputs(
    lat_key_prefix: str = "",
    lon_key_prefix: str = "",
    default_lat_deg: int = 57,
    default_lon_deg: int = 152,
    label_prefix: str = "",
    allow_empty: bool = False,
    default_lat_min: float = 0.0,
    default_lon_min: float = 0.0
) -> tuple[float | None, float | None]:
    """
    Render latitude/longitude input fields in DMS format.

    This component provides a captain-friendly interface for coordinate entry,
    using degrees and decimal minutes rather than decimal degrees.

    Args:
        lat_key_prefix: Prefix for latitude widget keys (for multiple instances on same page)
        lon_key_prefix: Prefix for longitude widget keys
        default_lat_deg: Default latitude degrees (57° for Gulf of Alaska)
        default_lon_deg: Default longitude degrees (152° for Gulf of Alaska)
        label_prefix: Prefix for labels (e.g., "Set " or "Retrieval ")
        allow_empty: If True, shows optional inputs that can be skipped
        default_lat_min: Default latitude minutes
        default_lon_min: Default longitude minutes

    Returns:
        Tuple of (latitude_decimal, longitude_decimal) or (None, None) if empty

    Note:
        Widget keys are prefixed to allow multiple instances on the same page.
    """
    required_marker = "" if allow_empty else " *"

    # Latitude input
    st.caption(f"**{label_prefix}Latitude** (50° - 72° N for Alaska){required_marker}")
    lat_col1, lat_col2, lat_col3 = st.columns([2, 2, 1])
    with lat_col1:
        lat_deg = st.number_input(
            "Degrees",
            min_value=50 if not allow_empty else 0,
            max_value=72,
            value=default_lat_deg if not allow_empty else None,
            step=1,
            key=f"{lat_key_prefix}lat_deg"
        )
    with lat_col2:
        lat_min = st.number_input(
            "Minutes",
            min_value=0.0,
            max_value=59.9,
            value=default_lat_min if not allow_empty else None,
            step=0.1,
            format="%.1f",
            key=f"{lat_key_prefix}lat_min"
        )
    with lat_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("**N**")

    # Longitude input
    st.caption(f"**{label_prefix}Longitude** (130° - 180° W for Alaska){required_marker}")
    lon_col1, lon_col2, lon_col3 = st.columns([2, 2, 1])
    with lon_col1:
        lon_deg = st.number_input(
            "Degrees",
            min_value=130 if not allow_empty else 0,
            max_value=180,
            value=default_lon_deg if not allow_empty else None,
            step=1,
            key=f"{lon_key_prefix}lon_deg"
        )
    with lon_col2:
        lon_min = st.number_input(
            "Minutes",
            min_value=0.0,
            max_value=59.9,
            value=default_lon_min if not allow_empty else None,
            step=0.1,
            format="%.1f",
            key=f"{lon_key_prefix}lon_min"
        )
    with lon_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("**W**")

    # Handle empty values for optional fields
    if allow_empty and (lat_deg is None or lon_deg is None):
        return None, None

    # Convert DMS to decimal for storage
    latitude = dms_to_decimal(lat_deg, lat_min or 0.0, 'N')
    longitude = dms_to_decimal(lon_deg, lon_min or 0.0, 'W')

    return latitude, longitude
