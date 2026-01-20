"""
Coordinate conversion utilities for Fishermen First.

Converts between captain-friendly DMS format and database decimal format.
Captains report coordinates like: 57° 30.5' N, 152° 15.5' W
Database stores decimal degrees: 57.5083, -152.2583
"""


def dms_to_decimal(degrees: int, minutes: float, direction: str) -> float:
    """
    Convert degrees-minutes to decimal degrees.

    Args:
        degrees: Whole degrees (e.g., 57)
        minutes: Decimal minutes (e.g., 30.5)
        direction: 'N', 'S', 'E', or 'W'

    Returns:
        Decimal degrees (negative for S/W)

    Examples:
        dms_to_decimal(57, 30.5, 'N')  -> 57.5083
        dms_to_decimal(152, 15.5, 'W') -> -152.2583
    """
    decimal = degrees + (minutes / 60)
    if direction.upper() in ['S', 'W']:
        decimal = -decimal
    return round(decimal, 6)


def decimal_to_dms(decimal: float, is_latitude: bool) -> tuple[int, float, str]:
    """
    Convert decimal degrees to degrees-minutes tuple.

    Args:
        decimal: Decimal degrees (e.g., 57.5083 or -152.2583)
        is_latitude: True for latitude, False for longitude

    Returns:
        Tuple of (degrees, minutes, direction)

    Examples:
        decimal_to_dms(57.5083, True)   -> (57, 30.5, 'N')
        decimal_to_dms(-152.2583, False) -> (152, 15.5, 'W')
    """
    if is_latitude:
        direction = 'N' if decimal >= 0 else 'S'
    else:
        direction = 'E' if decimal >= 0 else 'W'

    decimal = abs(decimal)
    degrees = int(decimal)
    minutes = round((decimal - degrees) * 60, 1)

    return degrees, minutes, direction


def decimal_to_dms_string(decimal: float, is_latitude: bool) -> str:
    """
    Convert decimal degrees to formatted DMS string.

    Args:
        decimal: Decimal degrees
        is_latitude: True for latitude, False for longitude

    Returns:
        Formatted string like "57° 30.5' N"
    """
    degrees, minutes, direction = decimal_to_dms(decimal, is_latitude)
    return f"{degrees}° {minutes:.1f}' {direction}"


def format_coordinates_dms(lat: float, lon: float) -> str:
    """
    Format lat/lon pair as captain-friendly string.

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees

    Returns:
        Formatted string like "57° 30.5' N, 152° 15.5' W"
    """
    lat_str = decimal_to_dms_string(lat, is_latitude=True)
    lon_str = decimal_to_dms_string(lon, is_latitude=False)
    return f"{lat_str}, {lon_str}"


def validate_latitude_dms(degrees: int, minutes: float) -> tuple[bool, str | None]:
    """Validate latitude in DMS for Alaska waters (50-72° N)."""
    if degrees < 50 or degrees > 72:
        return False, "Latitude must be between 50° and 72° N for Alaska waters"
    if minutes < 0 or minutes >= 60:
        return False, "Minutes must be between 0 and 59.9"
    return True, None


def validate_longitude_dms(degrees: int, minutes: float) -> tuple[bool, str | None]:
    """Validate longitude in DMS for Alaska waters (130-180° W)."""
    if degrees < 130 or degrees > 180:
        return False, "Longitude must be between 130° and 180° W for Alaska waters"
    if minutes < 0 or minutes >= 60:
        return False, "Minutes must be between 0 and 59.9"
    return True, None
