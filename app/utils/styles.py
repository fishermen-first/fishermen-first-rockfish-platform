"""Shared styling utilities for consistent branding across all pages."""

import streamlit as st

# Brand colors
NAVY = "#1e3a5f"
GRAY_TEXT = "#64748b"
GRAY_BG = "#f8fafc"
WHITE = "#ffffff"


def page_header(title: str, subtitle: str = None):
    """Render a consistent page header with title and optional subtitle."""
    html = f"<h1 style='margin: 0 0 0.25rem 0; font-size: 2rem;'>{title}</h1>"
    if subtitle:
        html += f"<p style='color: {GRAY_TEXT}; margin: 0 0 1.5rem 0;'>{subtitle}</p>"
    st.markdown(html, unsafe_allow_html=True)


def section_header(text: str, icon: str = None):
    """Render a consistent section header (uppercase with optional icon)."""
    icon_str = f"{icon} " if icon else ""
    st.markdown(
        f"<p style='color: {GRAY_TEXT}; font-size: 1.1rem; font-weight: 600; "
        f"margin: 1.5rem 0 1rem 0; text-transform: uppercase; letter-spacing: 0.5px;'>"
        f"{icon_str}{text}</p>",
        unsafe_allow_html=True
    )


def card_container(content: str):
    """Wrap content in a styled card container."""
    return f"""
    <div style="background: {WHITE}; padding: 1.5rem; border-radius: 10px;
                border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
                margin-bottom: 1rem;">
        {content}
    </div>
    """


def info_card(label: str, value: str, subtitle: str = None):
    """Render an info/KPI card."""
    subtitle_html = f'<div style="color: {GRAY_TEXT}; font-size: 14px; margin-top: 8px;">{subtitle}</div>' if subtitle else ''
    return f"""
    <div style="background: {WHITE}; border: 1px solid #e2e8f0; border-radius: 10px;
                padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center;">
        <div style="color: {GRAY_TEXT}; font-size: 16px; margin-bottom: 8px;
                    text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">{label}</div>
        <div style="font-size: 36px; font-weight: 700; color: #1e293b;">{value}</div>
        {subtitle_html}
    </div>
    """


def apply_page_styling():
    """Apply consistent page styling CSS. Call this at the top of each page."""
    st.markdown("""
    <style>
        /* Light background for main area */
        .stMainBlockContainer {
            background-color: #f8fafc;
        }
        /* Style dataframe headers */
        .stDataFrame thead tr th {
            background-color: #1e3a5f !important;
            color: white !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            padding: 0.75rem 0.5rem !important;
        }
        /* Style metrics */
        [data-testid="stMetric"] {
            background-color: white;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        [data-testid="stMetric"] label {
            color: #64748b;
        }
    </style>
    """, unsafe_allow_html=True)
