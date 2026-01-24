"""
Shared formatting utilities for display and styling.

This module consolidates formatting functions previously duplicated across
dashboard.py and vessel_owner_view.py. Minor behavioral differences have been
intentionally standardized to ensure consistent display across all views.
"""


# Risk level color definitions
RISK_COLORS = {
    "critical": "#dc2626",  # red - <10%
    "warning": "#d97706",   # amber - <50%
    "ok": "#059669",        # green - >=50%
    "na": "#94a3b8",        # gray - N/A
}


def format_lbs(value, na_text: str = "N/A") -> str:
    """
    Format pounds as M, K, or raw number with sign handling.

    Args:
        value: Numeric value to format, or None
        na_text: Text to display for None values

    Returns:
        Formatted string (e.g., "1.5M", "250K", "500")

    Standardization note: This consolidates minor differences between
    dashboard and vessel_owner_view implementations. The unified version
    handles None values consistently and uses integer formatting for
    values under 1K.
    """
    if value is None:
        return na_text
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{sign}{abs_value / 1_000:.1f}K"
    return f"{value:.0f}"


def get_risk_level(pct) -> str:
    """
    Return risk level category based on percent remaining.

    Args:
        pct: Percentage value (0-100), or None

    Returns:
        Risk level string: "critical", "warning", "ok", or "na"
    """
    if pct is None:
        return "na"
    if pct < 10:
        return "critical"
    if pct < 50:
        return "warning"
    return "ok"


def get_pct_color(pct, ok_color: str = "#059669") -> str:
    """
    Return color hex code based on percent remaining.

    Args:
        pct: Percentage value (0-100), or None
        ok_color: Color to use for "ok" status (default green)

    Returns:
        Color hex code string

    Standardization note: The dashboard previously used a dark default color
    (#1e293b) for "ok" status while vessel_owner_view used green (#059669).
    This consolidation standardizes on green with an optional override,
    reducing visual inconsistency across views.
    """
    risk = get_risk_level(pct)
    if risk == "ok":
        return ok_color
    return RISK_COLORS.get(risk, RISK_COLORS["na"])
