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

from app.auth import init_session_state, is_authenticated, login, logout, get_current_user, get_current_role


def main():
    init_session_state()

    # Show login form if not authenticated
    if not is_authenticated():
        show_login()
        return

    # User is authenticated - show main app
    show_sidebar()
    show_current_page()


def show_login():
    """Display the login form."""
    st.title("Fishermen First Analytics")
    st.subheader("Login")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Logging in..."):
                    success, message = login(email, password)

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


def show_sidebar():
    """Display sidebar with navigation and user info."""
    user = get_current_user()
    role = get_current_role()

    with st.sidebar:
        st.title("🐟 Fishermen First")
        st.divider()

        # User info
        st.caption(f"Logged in as: **{user.email}**")
        st.caption(f"Role: **{role}**")

        if st.button("Log Out", use_container_width=True):
            logout()
            st.rerun()

        st.divider()

        # Navigation
        st.subheader("Navigation")

        # Pages available to all authenticated users
        nav_options = {
            "dashboard": "📊 Dashboard",
            "rosters": "👥 Rosters",
            "upload": "📤 Uploads",
            "quotas": "📋 Quotas",
            "harvests": "🎣 Harvests",
            "psc": "⚠️ PSC Tracking",
        }

        # Admin-only pages
        if role == "admin":
            nav_options["admin"] = "⚙️ Admin Settings"

        # Initialize current page
        if "current_page" not in st.session_state:
            st.session_state.current_page = "dashboard"

        # Render nav buttons
        for page_key, page_label in nav_options.items():
            if st.button(
                page_label,
                use_container_width=True,
                type="primary" if st.session_state.current_page == page_key else "secondary"
            ):
                st.session_state.current_page = page_key
                st.rerun()


def show_current_page():
    """Render the currently selected page."""
    page = st.session_state.get("current_page", "dashboard")

    if page == "dashboard":
        show_placeholder("Dashboard", "Main dashboard with key metrics and summaries.")
    elif page == "rosters":
        from app.pages import rosters
        rosters.show()
    elif page == "upload":
        show_placeholder("File Uploads", "Upload eFish, eLandings, and fish ticket files.")
    elif page == "quotas":
        show_placeholder("Quota Management", "View and manage quota allocations and transfers.")
    elif page == "harvests":
        show_placeholder("Harvest Data", "View harvest records and reports.")
    elif page == "psc":
        show_placeholder("PSC Tracking", "Monitor prohibited species catch limits.")
    elif page == "admin":
        show_admin_page()
    else:
        st.error("Page not found.")


def show_admin_page():
    """Display admin settings with tabs for managing different entities."""
    st.title("Admin Settings")

    tabs = st.tabs(["Cooperatives", "Members", "Vessels", "Member Assignments", "Vessel Assignments", "Processors", "Species", "Seasons"])

    with tabs[0]:
        from app.pages.admin import manage_coops
        manage_coops.show()

    with tabs[1]:
        from app.pages.admin import manage_members
        manage_members.show()

    with tabs[2]:
        from app.pages.admin import manage_vessels
        manage_vessels.show()

    with tabs[3]:
        from app.pages.admin import manage_member_coops
        manage_member_coops.show()

    with tabs[4]:
        from app.pages.admin import manage_vessel_coops
        manage_vessel_coops.show()

    with tabs[5]:
        from app.pages.admin import manage_processors
        manage_processors.show()

    with tabs[6]:
        st.info("🚧 Manage Species - Coming soon")

    with tabs[7]:
        st.info("🚧 Manage Seasons - Coming soon")


def show_placeholder(title: str, description: str):
    """Show a placeholder page until the real page is implemented."""
    st.title(title)
    st.info(f"🚧 {description}")
    st.caption("This page is under construction.")


if __name__ == "__main__":
    main()
