"""
Shared coordinate input component for DMS (degrees/minutes) entry.

This component provides a captain-friendly interface for coordinate entry,
using degrees and decimal minutes rather than decimal degrees. It consolidates
duplicate coordinate input UI from report_bycatch.py and bycatch_alerts.py.
"""

import streamlit as st
from app.utils.coordinates import dms_to_decimal


def render_coordinate_inputs(
    lat_key_prefix: str = "",
    lon_key_prefix: str = "",
    default_lat_deg: int = 57,
    default_lon_deg: int = 152
) -> tuple[float, float]:
    """
    Render latitude/longitude input fields in DMS format.

    This component provides a captain-friendly interface for coordinate entry,
    using degrees and decimal minutes rather than decimal degrees.

    Args:
        lat_key_prefix: Prefix for latitude widget keys (for multiple instances on same page)
        lon_key_prefix: Prefix for longitude widget keys
        default_lat_deg: Default latitude degrees (57° for Gulf of Alaska)
        default_lon_deg: Default longitude degrees (152° for Gulf of Alaska)

    Returns:
        Tuple of (latitude_decimal, longitude_decimal)

    Note:
        Widget keys are prefixed to allow multiple instances on the same page.
        The dms_to_decimal utility is assumed to exist in app/utils/coordinates.py.
    """
    # Latitude input
    st.caption("**Latitude** (50° - 72° N for Alaska)")
    lat_col1, lat_col2, lat_col3 = st.columns([2, 2, 1])
    with lat_col1:
        lat_deg = st.number_input(
            "Degrees",
            min_value=50,
            max_value=72,
            value=default_lat_deg,
            step=1,
            key=f"{lat_key_prefix}lat_deg"
        )
    with lat_col2:
        lat_min = st.number_input(
            "Minutes",
            min_value=0.0,
            max_value=59.9,
            value=0.0,
            step=0.1,
            format="%.1f",
            key=f"{lat_key_prefix}lat_min"
        )
    with lat_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("**N**")

    # Longitude input
    st.caption("**Longitude** (130° - 180° W for Alaska)")
    lon_col1, lon_col2, lon_col3 = st.columns([2, 2, 1])
    with lon_col1:
        lon_deg = st.number_input(
            "Degrees",
            min_value=130,
            max_value=180,
            value=default_lon_deg,
            step=1,
            key=f"{lon_key_prefix}lon_deg"
        )
    with lon_col2:
        lon_min = st.number_input(
            "Minutes",
            min_value=0.0,
            max_value=59.9,
            value=0.0,
            step=0.1,
            format="%.1f",
            key=f"{lon_key_prefix}lon_min"
        )
    with lon_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("**W**")

    # Convert DMS to decimal for storage
    latitude = dms_to_decimal(lat_deg, lat_min, 'N')
    longitude = dms_to_decimal(lon_deg, lon_min, 'W')

    return latitude, longitude
