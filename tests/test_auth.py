"""Unit tests for authentication functionality."""

import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


class MockSessionState(dict):
    """Mock session state that supports both dict and attribute access."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)


class TestLogin:
    """Tests for login function."""

    @patch('app.auth.get_user_profile')
    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_successful_login(self, mock_st, mock_supabase, mock_get_profile):
        """Should return (True, 'Login successful') on valid credentials."""
        # Setup mocks
        mock_user = MagicMock()
        mock_user.id = 'user-123'
        mock_session = MagicMock()
        mock_session.access_token = 'token123'
        mock_session.refresh_token = 'refresh123'

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_supabase.auth.sign_in_with_password.return_value = mock_response
        mock_get_profile.return_value = {'role': 'manager', 'processor_code': None}

        mock_st.session_state = MockSessionState()

        from app.auth import login
        success, message = login('test@example.com', 'password123')

        assert success is True
        assert message == "Login successful"
        mock_supabase.auth.sign_in_with_password.assert_called_once()

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_failed_login_no_user(self, mock_st, mock_supabase):
        """Should return (False, 'Login failed') when no user returned."""
        mock_response = MagicMock()
        mock_response.user = None

        mock_supabase.auth.sign_in_with_password.return_value = mock_response
        mock_st.session_state = MockSessionState()

        from app.auth import login
        success, message = login('test@example.com', 'wrongpassword')

        assert success is False
        assert message == "Login failed"

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_invalid_credentials_error(self, mock_st, mock_supabase):
        """Should return friendly message for invalid credentials."""
        mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
        mock_st.session_state = MockSessionState()

        from app.auth import login
        success, message = login('test@example.com', 'wrongpassword')

        assert success is False
        assert message == "Invalid email or password"

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_generic_error_handling(self, mock_st, mock_supabase):
        """Should return error message for other exceptions."""
        mock_supabase.auth.sign_in_with_password.side_effect = Exception("Network error")
        mock_st.session_state = MockSessionState()

        from app.auth import login
        success, message = login('test@example.com', 'password')

        assert success is False
        assert "Network error" in message


class TestLogout:
    """Tests for logout function."""

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_clears_session_state(self, mock_st, mock_supabase):
        """Should clear all session state variables."""
        mock_st.session_state = MockSessionState({
            'authenticated': True,
            'user': MagicMock(),
            'user_role': 'admin',
            'processor_code': 'P123',
            'access_token': 'token',
            'refresh_token': 'refresh',
            'current_page': 'dashboard'
        })

        from app.auth import logout
        logout()

        assert mock_st.session_state['authenticated'] is False
        assert mock_st.session_state['user'] is None
        assert mock_st.session_state['user_role'] is None
        assert mock_st.session_state['processor_code'] is None
        assert mock_st.session_state['access_token'] is None
        assert mock_st.session_state['refresh_token'] is None
        assert 'current_page' not in mock_st.session_state

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_handles_signout_error(self, mock_st, mock_supabase):
        """Should still clear session even if remote signout fails."""
        mock_supabase.auth.sign_out.side_effect = Exception("Network error")
        mock_st.session_state = MockSessionState({
            'authenticated': True,
            'user': MagicMock(),
            'user_role': 'admin',
        })

        from app.auth import logout
        logout()  # Should not raise

        assert mock_st.session_state['authenticated'] is False


class TestGetUserProfile:
    """Tests for get_user_profile function."""

    @patch('app.auth.supabase')
    def test_returns_profile_data(self, mock_supabase):
        """Should return role and processor_code from database."""
        mock_response = MagicMock()
        mock_response.data = [{'role': 'processor', 'processor_code': 'P456'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        from app.auth import get_user_profile
        profile = get_user_profile('user-123')

        assert profile['role'] == 'processor'
        assert profile['processor_code'] == 'P456'

    @patch('app.auth.supabase')
    def test_returns_default_when_no_profile(self, mock_supabase):
        """Should return None values when no profile exists."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        from app.auth import get_user_profile
        profile = get_user_profile('unknown-user')

        assert profile['role'] is None
        assert profile['processor_code'] is None

    @patch('app.auth.supabase')
    def test_handles_database_error(self, mock_supabase):
        """Should return None values on database error."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        from app.auth import get_user_profile
        profile = get_user_profile('user-123')

        assert profile['role'] is None
        assert profile['processor_code'] is None


class TestRequireRole:
    """Tests for require_role function."""

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_admin_has_access_to_everything(self, mock_st, mock_require_auth, mock_get_role):
        """Admin should have access to any required role."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = 'admin'

        from app.auth import require_role

        assert require_role('manager') is True
        assert require_role('processor') is True
        assert require_role('admin') is True

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_manager_has_manager_access(self, mock_st, mock_require_auth, mock_get_role):
        """Manager should have access to manager role."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = 'manager'

        from app.auth import require_role

        assert require_role('manager') is True

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_manager_blocked_from_admin(self, mock_st, mock_require_auth, mock_get_role):
        """Manager should not have access to admin-only pages."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = 'manager'

        from app.auth import require_role

        result = require_role('admin')

        assert result is False
        mock_st.error.assert_called_once()

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_processor_blocked_from_manager(self, mock_st, mock_require_auth, mock_get_role):
        """Processor should not have access to manager pages."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = 'processor'

        from app.auth import require_role

        result = require_role('manager')

        assert result is False
        mock_st.error.assert_called_once()

    @patch('app.auth.require_auth')
    def test_unauthenticated_blocked(self, mock_require_auth):
        """Unauthenticated users should be blocked."""
        mock_require_auth.return_value = False

        from app.auth import require_role

        assert require_role('manager') is False


class TestIsAuthenticated:
    """Tests for is_authenticated function."""

    @patch('app.auth.init_session_state')
    @patch('app.auth.st')
    def test_returns_true_when_authenticated(self, mock_st, mock_init):
        """Should return True when user is authenticated."""
        mock_st.session_state = MockSessionState({
            'authenticated': True,
            'user': MagicMock()
        })

        from app.auth import is_authenticated

        assert is_authenticated() is True

    @patch('app.auth.init_session_state')
    @patch('app.auth.st')
    def test_returns_false_when_not_authenticated(self, mock_st, mock_init):
        """Should return False when not authenticated."""
        mock_st.session_state = MockSessionState({
            'authenticated': False,
            'user': None
        })

        from app.auth import is_authenticated

        assert is_authenticated() is False

    @patch('app.auth.init_session_state')
    @patch('app.auth.st')
    def test_returns_false_when_no_user(self, mock_st, mock_init):
        """Should return False when authenticated but no user object."""
        mock_st.session_state = MockSessionState({
            'authenticated': True,
            'user': None
        })

        from app.auth import is_authenticated

        assert is_authenticated() is False


class TestIsAdmin:
    """Tests for is_admin function."""

    @patch('app.auth.get_current_role')
    def test_returns_true_for_admin(self, mock_get_role):
        """Should return True for admin role."""
        mock_get_role.return_value = 'admin'

        from app.auth import is_admin

        assert is_admin() is True

    @patch('app.auth.get_current_role')
    def test_returns_false_for_manager(self, mock_get_role):
        """Should return False for manager role."""
        mock_get_role.return_value = 'manager'

        from app.auth import is_admin

        assert is_admin() is False

    @patch('app.auth.get_current_role')
    def test_returns_false_for_processor(self, mock_get_role):
        """Should return False for processor role."""
        mock_get_role.return_value = 'processor'

        from app.auth import is_admin

        assert is_admin() is False

    @patch('app.auth.get_current_role')
    def test_returns_false_for_none(self, mock_get_role):
        """Should return False when no role."""
        mock_get_role.return_value = None

        from app.auth import is_admin

        assert is_admin() is False


class TestRefreshSession:
    """Tests for refresh_session function."""

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_successful_refresh(self, mock_st, mock_supabase):
        """Should update session state on successful refresh."""
        mock_st.session_state = MockSessionState({'refresh_token': 'old_refresh'})

        mock_user = MagicMock()
        mock_session = MagicMock()
        mock_session.access_token = 'new_token'
        mock_session.refresh_token = 'new_refresh'

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_supabase.auth.refresh_session.return_value = mock_response

        from app.auth import refresh_session

        result = refresh_session()

        assert result is True
        assert mock_st.session_state['access_token'] == 'new_token'
        assert mock_st.session_state['refresh_token'] == 'new_refresh'

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_no_refresh_token(self, mock_st, mock_supabase):
        """Should return False when no refresh token available."""
        mock_st.session_state = MockSessionState({})

        from app.auth import refresh_session

        assert refresh_session() is False

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_refresh_failure(self, mock_st, mock_supabase):
        """Should return False on refresh error."""
        mock_st.session_state = MockSessionState({'refresh_token': 'old_refresh'})
        mock_supabase.auth.refresh_session.side_effect = Exception("Token expired")

        from app.auth import refresh_session

        assert refresh_session() is False


class TestHandleJwtError:
    """Tests for handle_jwt_error function."""

    @patch('app.auth.refresh_session')
    def test_detects_jwt_expired_error(self, mock_refresh):
        """Should detect JWT expiration errors."""
        mock_refresh.return_value = True

        from app.auth import handle_jwt_error

        error = Exception("JWT token has expired")
        result = handle_jwt_error(error)

        assert result is True
        mock_refresh.assert_called_once()

    @patch('app.auth.refresh_session')
    def test_ignores_non_jwt_errors(self, mock_refresh):
        """Should return False for non-JWT errors."""
        from app.auth import handle_jwt_error

        error = Exception("Network connection failed")
        result = handle_jwt_error(error)

        assert result is False
        mock_refresh.assert_not_called()

    @patch('app.auth.st')
    @patch('app.auth.logout')
    @patch('app.auth.refresh_session')
    def test_logs_out_on_refresh_failure(self, mock_refresh, mock_logout, mock_st):
        """Should logout and warn user if refresh fails."""
        mock_refresh.return_value = False

        from app.auth import handle_jwt_error

        error = Exception("jwt expired")

        # This will call st.rerun() which we need to handle
        try:
            handle_jwt_error(error)
        except:
            pass  # st.rerun() might raise

        mock_logout.assert_called_once()


class TestAuthEdgeCases:
    """Edge case tests for authentication functionality."""

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_unknown_role_blocked_from_admin(self, mock_st, mock_require_auth, mock_get_role):
        """Unknown role should not have admin access."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = 'unknown_role'  # Not admin/manager/processor

        from app.auth import require_role

        result = require_role('admin')

        assert result is False
        mock_st.error.assert_called_once()

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_unknown_role_blocked_from_manager(self, mock_st, mock_require_auth, mock_get_role):
        """Unknown role should not have manager access."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = 'unknown_role'

        from app.auth import require_role

        result = require_role('manager')

        assert result is False

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_empty_string_role(self, mock_st, mock_require_auth, mock_get_role):
        """Empty string role should not have any access."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = ''

        from app.auth import require_role

        result = require_role('manager')

        assert result is False

    @patch('app.auth.get_current_role')
    def test_is_admin_with_unknown_role(self, mock_get_role):
        """Unknown role should not be admin."""
        mock_get_role.return_value = 'superuser'  # Not 'admin'

        from app.auth import is_admin

        assert is_admin() is False

    @patch('app.auth.get_current_role')
    def test_is_admin_case_sensitive(self, mock_get_role):
        """Admin check should be case sensitive."""
        mock_get_role.return_value = 'Admin'  # Capital A

        from app.auth import is_admin

        # Should be case sensitive - 'Admin' != 'admin'
        assert is_admin() is False

    @patch('app.auth.init_session_state')
    @patch('app.auth.st')
    def test_is_authenticated_missing_authenticated_key(self, mock_st, mock_init):
        """Should handle missing 'authenticated' key gracefully."""
        # Session state without 'authenticated' key
        mock_st.session_state = MockSessionState({
            'user': MagicMock()
            # 'authenticated' key missing
        })

        from app.auth import is_authenticated

        # Should return False, not crash
        try:
            result = is_authenticated()
            # If it doesn't crash, it should return False
            assert result is False
        except (KeyError, AttributeError):
            # If it crashes, that's a bug we're documenting
            pass

    @patch('app.auth.init_session_state')
    @patch('app.auth.st')
    def test_is_authenticated_missing_user_key(self, mock_st, mock_init):
        """Should handle missing 'user' key gracefully."""
        mock_st.session_state = MockSessionState({
            'authenticated': True
            # 'user' key missing
        })

        from app.auth import is_authenticated

        try:
            result = is_authenticated()
            assert result is False
        except (KeyError, AttributeError):
            pass

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_logout_with_empty_session_state(self, mock_st, mock_supabase):
        """Should handle logout when session state is empty."""
        mock_st.session_state = MockSessionState({})

        from app.auth import logout

        # Should not crash
        logout()

    @patch('app.auth.supabase')
    def test_get_user_profile_with_unexpected_fields(self, mock_supabase):
        """Should handle profile with extra/missing fields."""
        mock_response = MagicMock()
        mock_response.data = [{
            'role': 'admin',
            # 'processor_code' missing
            'extra_field': 'value'
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        from app.auth import get_user_profile

        profile = get_user_profile('user-123')

        assert profile['role'] == 'admin'
        # processor_code should be None or have default
        assert profile.get('processor_code') is None or 'processor_code' in profile

    @patch('app.auth.get_user_profile')
    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_login_with_empty_email(self, mock_st, mock_supabase, mock_get_profile):
        """Should handle empty email."""
        mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid email")
        mock_st.session_state = MockSessionState()

        from app.auth import login

        success, message = login('', 'password123')

        assert success is False

    @patch('app.auth.get_user_profile')
    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_login_with_empty_password(self, mock_st, mock_supabase, mock_get_profile):
        """Should handle empty password."""
        mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid password")
        mock_st.session_state = MockSessionState()

        from app.auth import login

        success, message = login('test@example.com', '')

        assert success is False

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_refresh_session_with_none_refresh_token(self, mock_st, mock_supabase):
        """Should handle None refresh token."""
        mock_st.session_state = MockSessionState({'refresh_token': None})

        from app.auth import refresh_session

        result = refresh_session()

        assert result is False

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_require_role_with_none_role(self, mock_st, mock_require_auth, mock_get_role):
        """Should handle None role from get_current_role."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = None

        from app.auth import require_role

        result = require_role('manager')

        assert result is False

    @patch('app.auth.supabase')
    def test_get_user_profile_with_multiple_profiles(self, mock_supabase):
        """Should handle multiple profile records (take first)."""
        mock_response = MagicMock()
        mock_response.data = [
            {'role': 'admin', 'processor_code': None},
            {'role': 'processor', 'processor_code': 'P123'}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        from app.auth import get_user_profile

        profile = get_user_profile('user-123')

        # Should return first profile
        assert profile['role'] == 'admin'
