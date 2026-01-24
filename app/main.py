"""Main entry point for Fishermen First Analytics."""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Fishermen First Analytics",
    page_icon="🐟",
    layout="wide",
    initial_sidebar_state="expanded"
)

from app.auth import init_session_state, is_authenticated, login, logout, get_current_user


def _get_pending_bycatch_count() -> int:
    """Get pending bycatch alert count for sidebar badge."""
    org_id = st.session_state.get("org_id")
    if not org_id:
        return 0
    try:
        from app.views.bycatch_alerts import get_pending_alert_count
        return get_pending_alert_count(org_id)
    except Exception:
        return 0


@st.cache_data(ttl=300)
def get_filter_options():
    """Cached: Fetch coop members for filter dropdowns."""
    from collections import defaultdict
    from app.config import supabase

    response = supabase.table("coop_members").select("coop_code, vessel_name").execute()
    members_data = response.data if response.data else []

    # Build lookup: coop -> vessels, vessel -> coop
    all_coops = sorted(set(m["coop_code"] for m in members_data if m.get("coop_code")))
    all_vessels = sorted(set(m["vessel_name"] for m in members_data if m.get("vessel_name")))
    coop_to_vessels = defaultdict(list)
    vessel_to_coop = {}

    for m in members_data:
        coop = m.get("coop_code")
        vessel = m.get("vessel_name")
        if coop and vessel:
            coop_to_vessels[coop].append(vessel)
            vessel_to_coop[vessel] = coop

    return {
        "all_coops": all_coops,
        "all_vessels": all_vessels,
        "coop_to_vessels": dict(coop_to_vessels),
        "vessel_to_coop": vessel_to_coop,
    }


def main():
    init_session_state()

    if not is_authenticated():
        show_login()
        return

    show_sidebar()
    show_current_page()


def show_login():
    """Display the login form with maritime-themed design."""
    # Wave SVG for animated background (encoded as data URI)
    wave_svg = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 120' preserveAspectRatio='none'%3E%3Cpath d='M0,60 C200,100 400,20 600,60 C800,100 1000,20 1200,60 L1200,120 L0,120 Z' fill='%23ffffff' fill-opacity='0.03'/%3E%3Cpath d='M0,80 C200,40 400,100 600,80 C800,40 1000,100 1200,80 L1200,120 L0,120 Z' fill='%23ffffff' fill-opacity='0.02'/%3E%3C/svg%3E"

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

        #MainMenu, footer, header {{visibility: hidden;}}

        /* Ocean depth gradient background */
        .stApp {{
            background:
                linear-gradient(
                    180deg,
                    #1a3d5c 0%,
                    #15304a 20%,
                    #0f2438 45%,
                    #0a1a2a 70%,
                    #06121c 100%
                );
            min-height: 100vh;
            position: relative;
        }}

        /* Subtle depth contour lines - bathymetric chart texture */
        .stApp::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image:
                repeating-linear-gradient(
                    180deg,
                    transparent,
                    transparent 60px,
                    rgba(255,255,255,0.015) 60px,
                    rgba(255,255,255,0.015) 61px
                ),
                repeating-linear-gradient(
                    90deg,
                    transparent,
                    transparent 80px,
                    rgba(255,255,255,0.008) 80px,
                    rgba(255,255,255,0.008) 81px
                );
            pointer-events: none;
            z-index: 0;
        }}

        /* Animated wave layer at bottom */
        .stApp::after {{
            content: '';
            position: fixed;
            bottom: 0;
            left: -100%;
            width: 300%;
            height: 180px;
            background-image: url("{wave_svg}");
            background-repeat: repeat-x;
            background-size: 33.33% 100%;
            animation: drift 25s linear infinite;
            z-index: 1;
            pointer-events: none;
        }}

        @keyframes drift {{
            0% {{ transform: translateX(0); }}
            100% {{ transform: translateX(33.33%); }}
        }}

        /* Centered form container */
        [data-testid="stMainBlockContainer"] {{
            max-width: 480px;
            margin: 0 auto;
            padding-top: 8vh;
            position: relative;
            z-index: 10;
        }}

        /* Frosted glass card effect */
        [data-testid="stForm"] {{
            background: rgba(255, 255, 255, 0.06);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            padding: 2.25rem 2rem 2rem 2rem;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.4),
                0 2px 8px rgba(0, 0, 0, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }}

        /* Form field spacing */
        [data-testid="stForm"] .stTextInput {{
            margin-bottom: 0.75rem;
        }}

        /* Input labels */
        [data-testid="stForm"] .stTextInput > label {{
            color: rgba(255, 255, 255, 0.85) !important;
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            font-weight: 500 !important;
            font-size: 0.875rem !important;
            letter-spacing: 0.01em;
        }}

        /* Text inputs */
        .stTextInput > div > div > input {{
            background: rgba(255, 255, 255, 0.95) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 10px !important;
            padding: 0.8rem 1rem !important;
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            font-size: 0.95rem !important;
            color: #0a1a2a !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
        }}

        .stTextInput > div > div > input:focus {{
            border-color: #4a9ead !important;
            box-shadow: 0 0 0 3px rgba(74, 158, 173, 0.2) !important;
            outline: none !important;
        }}

        .stTextInput > div > div > input::placeholder {{
            color: #94a3b8 !important;
        }}

        /* Hide helper text */
        .stTextInput div[data-testid="InputInstructions"] {{
            display: none;
        }}

        /* Submit button */
        .stFormSubmitButton > button {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2a4d6e 50%, #1e3a5f 100%) !important;
            background-size: 200% 200% !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.75rem 1.5rem !important;
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            letter-spacing: 0.02em !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 16px rgba(30, 58, 95, 0.4) !important;
            margin-top: 0.5rem !important;
        }}

        .stFormSubmitButton > button:hover {{
            background-position: 100% 0 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 24px rgba(30, 58, 95, 0.5) !important;
        }}

        .stFormSubmitButton > button:active {{
            transform: translateY(0) !important;
        }}

        /* Error/warning messages */
        [data-testid="stForm"] .stAlert {{
            background: rgba(239, 68, 68, 0.15) !important;
            border: 1px solid rgba(239, 68, 68, 0.3) !important;
            border-radius: 8px !important;
        }}

        [data-testid="stForm"] .stAlert p {{
            color: #fca5a5 !important;
        }}

        /* Spinner */
        [data-testid="stForm"] .stSpinner > div {{
            border-top-color: #4a9ead !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    # Branding header with refined maritime styling
    st.markdown("""
    <div style='text-align: center; margin-bottom: 1.75rem; position: relative; z-index: 10;'>
        <div style='
            font-size: 3.5rem;
            margin-bottom: 0.5rem;
            filter: drop-shadow(0 2px 8px rgba(0,0,0,0.3));
        '>🐟</div>
        <div style='
            font-family: "DM Sans", -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.01em;
            margin-bottom: 0.35rem;
            text-shadow: 0 2px 12px rgba(0,0,0,0.3);
        '>Fishermen First</div>
        <div style='
            font-family: "DM Sans", -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 0.9rem;
            font-weight: 500;
            color: rgba(255,255,255,0.6);
            letter-spacing: 0.08em;
            text-transform: uppercase;
        '>Rockfish Quota Management</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Signing in..."):
                    success, message = login(email, password)

                if success:
                    st.rerun()
                else:
                    st.error(message)


def show_sidebar():
    """Display sidebar with navigation and user info."""
    user = get_current_user()
    role = st.session_state.get("user_role")

    with st.sidebar:
        # Sidebar styling
        st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                background-color: #1e3a5f;
            }
            [data-testid="stSidebar"] * {
                color: white !important;
            }
            /* Fix selectbox text visibility */
            [data-testid="stSidebar"] [data-baseweb="select"] * {
                color: #1e293b !important;
            }
            [data-testid="stSidebar"] [data-baseweb="select"] {
                background-color: white !important;
            }
            [data-testid="stSidebar"] button {
                background-color: rgba(255,255,255,0.1) !important;
                border: 1px solid rgba(255,255,255,0.2) !important;
            }
            [data-testid="stSidebar"] button:hover {
                background-color: rgba(255,255,255,0.2) !important;
                border: 1px solid rgba(255,255,255,0.3) !important;
            }
            [data-testid="stSidebar"] button[kind="primary"] {
                background-color: rgba(255,255,255,0.25) !important;
                border: 1px solid rgba(255,255,255,0.4) !important;
            }
            [data-testid="stSidebar"] hr {
                border-color: rgba(255,255,255,0.2) !important;
            }
        </style>
        """, unsafe_allow_html=True)

        # Branding
        st.markdown("<div style='text-align: center; padding: 0.5rem 0;'><span style='font-size: 2rem;'>🐟</span></div>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; margin: 0; font-size: 1.4rem;'>Fishermen First</h2>", unsafe_allow_html=True)

        st.divider()

        # Role-based navigation with icons
        if role in ["admin", "manager"]:
            # Get pending bycatch alert count for badge
            pending_count = _get_pending_bycatch_count()
            bycatch_label = "⚠️  Bycatch Alerts"
            if pending_count > 0:
                bycatch_label = f"⚠️  Bycatch Alerts ({pending_count})"

            nav_options = {
                "dashboard": "📊  Dashboard",
                "bycatch_alerts": bycatch_label,
                "account_balances": "💰  Account Balances",
                "account_detail": "📋  Account Detail",
                "transfers": "🔄  Transfers",
                "allocations": "📈  Allocations",
                "rosters": "👥  Rosters",
                "upload": "📤  Upload",
            }
            default_page = "dashboard"
        elif role == "processor":
            nav_options = {
                "processor_view": "🏭  Processor View",
            }
            default_page = "processor_view"
        elif role == "vessel_owner":
            nav_options = {
                "vessel_owner_view": "🚢  My Vessel",
                "report_bycatch": "📍  Report Bycatch",
            }
            default_page = "vessel_owner_view"
        else:
            nav_options = {}
            default_page = None

        # If current_page is not set or not valid for this role, reset to default
        if "current_page" not in st.session_state or st.session_state.current_page not in nav_options:
            st.session_state.current_page = default_page

        for page_key, page_label in nav_options.items():
            is_current = st.session_state.current_page == page_key
            if st.button(
                page_label,
                use_container_width=True,
                type="primary" if is_current else "secondary"
            ):
                st.session_state.current_page = page_key
                st.rerun()

        # Dashboard filters (only show when on dashboard)
        if role in ["admin", "manager"] and st.session_state.current_page == "dashboard":
            st.divider()
            st.caption("🔍 Filters")

            # Get cached filter options
            filter_opts = get_filter_options()

            # Get current selections
            current_coop = st.session_state.get("filter_coop", "All")
            current_vessel = st.session_state.get("filter_vessel", "All")

            # Build co-op options (filter by selected vessel if one is chosen)
            if current_vessel != "All" and current_vessel in filter_opts["vessel_to_coop"]:
                coops = ["All", filter_opts["vessel_to_coop"][current_vessel]]
            else:
                coops = ["All"] + filter_opts["all_coops"]

            # Build vessel options (filter by selected co-op if one is chosen)
            if current_coop != "All" and current_coop in filter_opts["coop_to_vessels"]:
                vessels = ["All"] + sorted(filter_opts["coop_to_vessels"][current_coop])
            else:
                vessels = ["All"] + filter_opts["all_vessels"]

            # Reset vessel when coop changes
            def on_coop_change():
                st.session_state.filter_vessel = "All"

            st.selectbox("Co-Op", coops, key="filter_coop", on_change=on_coop_change)
            st.selectbox("Vessel", vessels, key="filter_vessel")

            if st.button("Clear Filters", use_container_width=True):
                st.session_state.filter_coop = "All"
                st.session_state.filter_vessel = "All"
                st.rerun()

        # Spacer to push user info to bottom
        st.markdown("<div style='flex-grow: 1; min-height: 2rem;'></div>", unsafe_allow_html=True)

        st.divider()

        # User info and logout at bottom
        st.caption(f"👤 {user.email}")
        st.caption(f"Role: {role}")

        if st.button("🚪  Log Out", use_container_width=True):
            logout()
            st.rerun()


def show_current_page():
    """Render the currently selected page."""
    import importlib

    # Apply global styling for all authenticated pages
    from app.utils.styles import apply_page_styling
    apply_page_styling()

    page = st.session_state.get("current_page", "dashboard")

    if page is None:
        st.warning("No pages available for your role.")
        return

    # Map page keys to module names (all in app.views package)
    page_modules = {
        "dashboard": "dashboard",
        "allocations": "allocations",
        "rosters": "rosters",
        "upload": "upload",
        "account_balances": "account_balances",
        "account_detail": "account_detail",
        "transfers": "transfers",
        "processor_view": "processor_view",
        "vessel_owner_view": "vessel_owner_view",
        "bycatch_alerts": "bycatch_alerts",
        "report_bycatch": "report_bycatch",
    }

    if page in page_modules:
        module = importlib.import_module(f"app.views.{page_modules[page]}")
        module.show()
    else:
        st.error("Page not found.")


if __name__ == "__main__":
    main()
