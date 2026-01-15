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


@st.cache_data(ttl=300)
def get_filter_options():
    """Cached: Fetch coop members for filter dropdowns."""
    from app.config import supabase
    response = supabase.table("coop_members").select("coop_code, vessel_name").execute()
    members_data = response.data if response.data else []

    # Build lookup: coop -> vessels, vessel -> coop
    all_coops = sorted(set(m["coop_code"] for m in members_data if m.get("coop_code")))
    all_vessels = sorted(set(m["vessel_name"] for m in members_data if m.get("vessel_name")))
    coop_to_vessels = {}
    vessel_to_coop = {}

    for m in members_data:
        coop = m.get("coop_code")
        vessel = m.get("vessel_name")
        if coop and vessel:
            if coop not in coop_to_vessels:
                coop_to_vessels[coop] = []
            coop_to_vessels[coop].append(vessel)
            vessel_to_coop[vessel] = coop

    return {
        "all_coops": all_coops,
        "all_vessels": all_vessels,
        "coop_to_vessels": coop_to_vessels,
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
    """Display the login form."""
    st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .stApp {
            background-color: #f0f4f8;
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 480px;
            margin: 0 auto;
            padding-top: 12vh;
        }
        /* Style the form container */
        [data-testid="stForm"] {
            background: white;
            padding: 3rem;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: none;
        }
        /* More space between form fields */
        [data-testid="stForm"] .stTextInput {
            margin-bottom: 1rem;
        }
        .stFormSubmitButton > button {
            background-color: #1e3a5f !important;
            color: white !important;
            border-radius: 8px !important;
            padding: 0.6rem 1rem !important;
            font-weight: 500 !important;
            margin-top: 0.5rem;
        }
        .stFormSubmitButton > button:hover {
            background-color: #2c4a6e !important;
        }
        /* Clean up input styling */
        .stTextInput > div > div > input {
            border-radius: 8px;
            padding: 0.75rem 1rem !important;
            font-size: 1rem !important;
            width: 100% !important;
        }
        /* Hide "Press Enter to submit" helper text */
        .stTextInput div[data-testid="InputInstructions"] {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)

    # Branding header
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <div style='font-size: 3rem; margin-bottom: 0.25rem;'>🐟</div>
        <div style='font-size: 1.75rem; font-weight: 600; color: #1e3a5f; margin-bottom: 0.25rem;'>Fishermen First</div>
        <div style='font-size: 1rem; color: #64748b;'>Rockfish Quota Management</div>
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
            nav_options = {
                "dashboard": "📊  Dashboard",
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
    page = st.session_state.get("current_page", "dashboard")

    if page == "dashboard":
        from app.views import dashboard
        dashboard.show()
    elif page == "allocations":
        from app.views import allocations
        allocations.show()
    elif page == "rosters":
        from app.views import rosters
        rosters.show()
    elif page == "upload":
        from app.views import upload
        upload.show()
    elif page == "account_balances":
        from app.views import account_balances
        account_balances.show()
    elif page == "account_detail":
        from app.views import account_detail
        account_detail.show()
    elif page == "transfers":
        from app.views import transfers
        transfers.show()
    elif page == "processor_view":
        from app.views import processor_view
        processor_view.show()
    elif page == "vessel_owner_view":
        from app.views import vessel_owner_view
        vessel_owner_view.show()
    elif page is None:
        st.warning("No pages available for your role.")
    else:
        st.error("Page not found.")


if __name__ == "__main__":
    main()
