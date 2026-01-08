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


def main():
    init_session_state()

    if not is_authenticated():
        show_login()
        return

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
    role = st.session_state.get("user_role")

    with st.sidebar:
        st.title("Fishermen First")
        st.divider()

        st.caption(f"Logged in as: **{user.email}**")
        st.caption(f"Role: **{role}**")

        if st.button("Log Out", use_container_width=True):
            logout()
            st.rerun()

        st.divider()

        # Role-based navigation
        if role in ["admin", "manager"]:
            nav_options = {
                "dashboard": "Dashboard",
                "allocations": "Allocations",
                "rosters": "Rosters",
                "upload": "Upload",
                "account_balances": "Account Balances",
                "account_detail": "Account Detail",
            }
            default_page = "dashboard"
        elif role == "processor":
            nav_options = {
                "processor_view": "Processor View",
            }
            default_page = "processor_view"
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
    elif page == "processor_view":
        from app.views import processor_view
        processor_view.show()
    elif page is None:
        st.warning("No pages available for your role.")
    else:
        st.error("Page not found.")


if __name__ == "__main__":
    main()
