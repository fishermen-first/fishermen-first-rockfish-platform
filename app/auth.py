import streamlit as st
from app.config import supabase


def init_session_state():
    """Initialize authentication-related session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "access_token" not in st.session_state:
        st.session_state.access_token = None


def login(email: str, password: str) -> tuple[bool, str]:
    """
    Authenticate user with email and password.

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if response.user:
            st.session_state.authenticated = True
            st.session_state.user = response.user
            st.session_state.access_token = response.session.access_token

            # Fetch user role from users table
            role = fetch_user_role(response.user.id)
            st.session_state.user_role = role

            return True, "Login successful"
        else:
            return False, "Login failed"

    except Exception as e:
        error_message = str(e)
        if "Invalid login credentials" in error_message:
            return False, "Invalid email or password"
        return False, f"Login error: {error_message}"


def logout():
    """Sign out the current user and clear session state."""
    try:
        supabase.auth.sign_out()
    except Exception:
        pass  # Sign out locally even if remote fails

    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.user_role = None
    st.session_state.access_token = None


def is_authenticated() -> bool:
    """Check if a user is currently authenticated."""
    init_session_state()
    return st.session_state.authenticated and st.session_state.user is not None


def fetch_user_role(user_id: str) -> str | None:
    """
    Fetch user role from the users table.

    Args:
        user_id: The user's UUID from Supabase Auth

    Returns:
        The user's role ('admin' or 'co_op_manager') or None if not found
    """
    try:
        response = supabase.table("users").select("role").eq("id", user_id).single().execute()
        if response.data:
            return response.data.get("role")
        return None
    except Exception:
        return None


def get_current_user():
    """Get the current authenticated user object."""
    init_session_state()
    return st.session_state.user


def get_current_role() -> str | None:
    """Get the current user's role."""
    init_session_state()
    return st.session_state.user_role


def require_auth():
    """
    Decorator-style check that redirects to login if not authenticated.
    Call at the top of protected pages.

    Returns:
        bool: True if authenticated, False otherwise
    """
    if not is_authenticated():
        st.warning("Please log in to access this page.")
        return False
    return True


def require_role(required_role: str) -> bool:
    """
    Check if current user has the required role.

    Args:
        required_role: The role required ('admin' or 'co_op_manager')

    Returns:
        bool: True if user has the required role
    """
    if not require_auth():
        return False

    current_role = get_current_role()

    # Admin has access to everything
    if current_role == "admin":
        return True

    if current_role != required_role:
        st.error("You don't have permission to access this page.")
        return False

    return True


def is_admin() -> bool:
    """Check if current user is an admin."""
    return get_current_role() == "admin"
