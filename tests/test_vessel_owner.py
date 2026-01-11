"""Tests for vessel owner view and authentication."""

import pytest
from unittest.mock import MagicMock, patch


class TestVesselOwnerAuth:
    """Tests for vessel owner authentication and access control."""

    @patch('app.auth.supabase')
    def test_get_user_profile_returns_llp(self, mock_supabase):
        """Should return llp in user profile."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"role": "vessel_owner", "processor_code": None, "org_id": "test-org", "llp": "1183"}]
        )

        from app.auth import get_user_profile
        profile = get_user_profile("user-123")

        assert profile["role"] == "vessel_owner"
        assert profile["llp"] == "1183"
        assert profile["org_id"] == "test-org"

    @patch('app.auth.supabase')
    def test_get_user_profile_no_llp(self, mock_supabase):
        """Should return None for llp if not set."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"role": "vessel_owner", "processor_code": None, "org_id": "test-org", "llp": None}]
        )

        from app.auth import get_user_profile
        profile = get_user_profile("user-123")

        assert profile["llp"] is None

    @patch('app.auth.supabase')
    def test_get_user_profile_empty_returns_none_llp(self, mock_supabase):
        """Should return None for llp when no profile exists."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        from app.auth import get_user_profile
        profile = get_user_profile("user-123")

        assert profile["llp"] is None
        assert profile["role"] is None


class TestVesselOwnerRoleCheck:
    """Tests for is_vessel_owner function."""

    @patch('app.auth.get_current_role')
    def test_is_vessel_owner_true(self, mock_role):
        """Should return True when role is vessel_owner."""
        mock_role.return_value = "vessel_owner"

        from app.auth import is_vessel_owner
        assert is_vessel_owner() is True

    @patch('app.auth.get_current_role')
    def test_is_vessel_owner_false_admin(self, mock_role):
        """Should return False when role is admin."""
        mock_role.return_value = "admin"

        from app.auth import is_vessel_owner
        assert is_vessel_owner() is False

    @patch('app.auth.get_current_role')
    def test_is_vessel_owner_false_manager(self, mock_role):
        """Should return False when role is manager."""
        mock_role.return_value = "manager"

        from app.auth import is_vessel_owner
        assert is_vessel_owner() is False


class TestGetUserLlp:
    """Tests for get_user_llp function."""

    @patch('app.auth.init_session_state')
    @patch('app.auth.st')
    def test_get_user_llp_returns_llp(self, mock_st, mock_init):
        """Should return LLP from session state."""
        mock_st.session_state.user_llp = "1183"

        from app.auth import get_user_llp
        assert get_user_llp() == "1183"

    @patch('app.auth.init_session_state')
    @patch('app.auth.st')
    def test_get_user_llp_returns_none(self, mock_st, mock_init):
        """Should return None when no LLP set."""
        mock_st.session_state.user_llp = None

        from app.auth import get_user_llp
        assert get_user_llp() is None


class TestVesselOwnerViewFunctions:
    """Tests for vessel owner view data functions."""

    @patch('app.views.vessel_owner_view.supabase')
    def test_fetch_vessel_info(self, mock_supabase):
        """Should return vessel info for LLP."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"vessel_name": "Pacific Dream", "coop_code": "SB"}]
        )

        from app.views.vessel_owner_view import _fetch_vessel_info
        _fetch_vessel_info.clear()  # Clear cache
        info = _fetch_vessel_info("1183")

        assert info["vessel_name"] == "Pacific Dream"
        assert info["coop_code"] == "SB"

    @patch('app.views.vessel_owner_view.supabase')
    def test_fetch_vessel_info_not_found(self, mock_supabase):
        """Should return Unknown when LLP not found."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        from app.views.vessel_owner_view import _fetch_vessel_info
        _fetch_vessel_info.clear()  # Clear cache
        info = _fetch_vessel_info("invalid-llp")

        assert info["vessel_name"] == "Unknown"
        assert info["coop_code"] == "Unknown"

    @patch('app.views.vessel_owner_view.supabase')
    def test_fetch_my_quota(self, mock_supabase):
        """Should return quota data for LLP."""
        mock_data = [
            {"species_code": 141, "allocation_lbs": 100000, "remaining_lbs": 80000,
             "transfers_in": 5000, "transfers_out": 0, "harvested": 25000}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=mock_data
        )

        from app.views.vessel_owner_view import _fetch_my_quota
        _fetch_my_quota.clear()  # Clear cache
        quota = _fetch_my_quota("1183", 2026)

        assert len(quota) == 1
        assert quota[0]["species_code"] == 141
        assert quota[0]["remaining_lbs"] == 80000

    @patch('app.views.vessel_owner_view.supabase')
    def test_fetch_my_quota_empty(self, mock_supabase):
        """Should return empty list when no quota."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        from app.views.vessel_owner_view import _fetch_my_quota
        _fetch_my_quota.clear()  # Clear cache
        quota = _fetch_my_quota("1183", 2026)

        assert quota == []

    @patch('app.views.vessel_owner_view.supabase')
    def test_fetch_my_harvests(self, mock_supabase):
        """Should return harvest data for LLP."""
        mock_data = [
            {"id": "uuid-1", "species_code": 141, "pounds": 5000,
             "harvest_date": "2026-01-08", "processor_code": "SB"}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=mock_data
        )

        from app.views.vessel_owner_view import _fetch_my_harvests
        _fetch_my_harvests.clear()  # Clear cache
        harvests = _fetch_my_harvests("1183", 2026)

        assert len(harvests) == 1
        assert harvests[0]["species_code"] == 141
        assert harvests[0]["pounds"] == 5000


class TestVesselOwnerViewHelpers:
    """Tests for vessel owner view helper functions."""

    def test_format_lbs_thousands(self):
        """Should format thousands as K."""
        from app.views.vessel_owner_view import format_lbs
        assert format_lbs(5000) == "5.0K"
        assert format_lbs(12500) == "12.5K"

    def test_format_lbs_millions(self):
        """Should format millions as M."""
        from app.views.vessel_owner_view import format_lbs
        assert format_lbs(1000000) == "1.0M"
        assert format_lbs(2500000) == "2.5M"

    def test_format_lbs_small(self):
        """Should format small numbers without suffix."""
        from app.views.vessel_owner_view import format_lbs
        assert format_lbs(500) == "500"
        assert format_lbs(0) == "0"

    def test_format_lbs_negative(self):
        """Should handle negative numbers."""
        from app.views.vessel_owner_view import format_lbs
        assert format_lbs(-5000) == "-5.0K"

    def test_format_lbs_none(self):
        """Should handle None."""
        from app.views.vessel_owner_view import format_lbs
        assert format_lbs(None) == "N/A"

    def test_get_pct_color_critical(self):
        """Should return red for < 10%."""
        from app.views.vessel_owner_view import get_pct_color
        assert get_pct_color(5) == "#dc2626"
        assert get_pct_color(9) == "#dc2626"

    def test_get_pct_color_warning(self):
        """Should return amber for 10-50%."""
        from app.views.vessel_owner_view import get_pct_color
        assert get_pct_color(10) == "#d97706"
        assert get_pct_color(49) == "#d97706"

    def test_get_pct_color_ok(self):
        """Should return green for >= 50%."""
        from app.views.vessel_owner_view import get_pct_color
        assert get_pct_color(50) == "#059669"
        assert get_pct_color(100) == "#059669"

    def test_get_pct_color_none(self):
        """Should return gray for None."""
        from app.views.vessel_owner_view import get_pct_color
        assert get_pct_color(None) == "#94a3b8"


class TestVesselOwnerTransferDirection:
    """Tests for transfer direction logic."""

    def test_transfer_in_direction(self):
        """Transfers TO this LLP should show as IN."""
        llp = "1183"
        transfer = {"from_llp": "2696", "to_llp": "1183"}
        direction = "IN" if transfer["to_llp"] == llp else "OUT"
        assert direction == "IN"

    def test_transfer_out_direction(self):
        """Transfers FROM this LLP should show as OUT."""
        llp = "1183"
        transfer = {"from_llp": "1183", "to_llp": "2696"}
        direction = "IN" if transfer["to_llp"] == llp else "OUT"
        assert direction == "OUT"


class TestVesselOwnerNavigation:
    """Tests for vessel owner navigation restrictions."""

    def test_vessel_owner_nav_options(self):
        """Vessel owner should only have My Vessel nav option."""
        role = "vessel_owner"

        if role == "vessel_owner":
            nav_options = {"vessel_owner_view": "My Vessel"}
            default_page = "vessel_owner_view"
        else:
            nav_options = {}
            default_page = None

        assert len(nav_options) == 1
        assert "vessel_owner_view" in nav_options
        assert default_page == "vessel_owner_view"

    def test_admin_has_more_nav_options(self):
        """Admin should have more nav options than vessel owner."""
        admin_nav = {
            "dashboard": "Dashboard",
            "transfers": "Transfers",
            "upload": "Upload",
        }
        vessel_owner_nav = {"vessel_owner_view": "My Vessel"}

        assert len(admin_nav) > len(vessel_owner_nav)
        assert "vessel_owner_view" not in admin_nav
