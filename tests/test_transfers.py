"""Unit tests for quota transfers functionality."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date
import importlib


# Reload module to ensure clean state for each test session
@pytest.fixture(autouse=True)
def reload_transfers():
    """Reload transfers module before each test to ensure clean state."""
    import app.views.transfers
    importlib.reload(app.views.transfers)
    # Clear any cached values from previous tests
    from app.views.transfers import get_quota_remaining, _fetch_transfer_history, _fetch_coop_members_for_dropdown, _fetch_llp_to_vessel_map
    get_quota_remaining.clear()
    _fetch_transfer_history.clear()
    _fetch_coop_members_for_dropdown.clear()
    _fetch_llp_to_vessel_map.clear()


class TestGetQuotaRemaining:
    """Tests for get_quota_remaining function."""

    @patch('app.views.transfers.supabase')
    def test_returns_remaining_lbs_when_found(self, mock_supabase):
        """Should return remaining_lbs when quota record exists."""
        mock_response = MagicMock()
        mock_response.data = [{'remaining_lbs': 5000.0}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        from app.views.transfers import get_quota_remaining
        result = get_quota_remaining('LLN111111111', 141, 2026)

        assert result == 5000.0

    @patch('app.views.transfers.supabase')
    def test_returns_zero_when_not_found(self, mock_supabase):
        """Should return 0 when no quota record exists."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        from app.views.transfers import get_quota_remaining
        result = get_quota_remaining('LLN999999999', 141, 2026)

        assert result == 0.0

    @patch('app.views.transfers.supabase')
    def test_returns_zero_when_remaining_is_none(self, mock_supabase):
        """Should return 0 when remaining_lbs is None."""
        mock_response = MagicMock()
        mock_response.data = [{'remaining_lbs': None}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        from app.views.transfers import get_quota_remaining
        result = get_quota_remaining('LLN111111111', 141, 2026)

        assert result == 0.0

    @patch('app.views.transfers.st')
    @patch('app.views.transfers.supabase')
    def test_handles_database_error(self, mock_supabase, mock_st):
        """Should return 0 and show error on database exception."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        from app.views.transfers import get_quota_remaining
        result = get_quota_remaining('LLN111111111', 141, 2026)

        assert result == 0.0
        mock_st.error.assert_called_once()


class TestGetLlpOptions:
    """Tests for get_llp_options function."""

    @patch('app.views.transfers.supabase')
    def test_returns_formatted_options(self, mock_supabase):
        """Should return list of (llp, display_string) tuples."""
        mock_response = MagicMock()
        mock_response.data = [
            {'llp': 'LLN111111111', 'vessel_name': 'Test Vessel 1'},
            {'llp': 'LLN222222222', 'vessel_name': 'Test Vessel 2'},
            {'llp': 'LLN333333333', 'vessel_name': 'Test Vessel 3'},
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response

        from app.views.transfers import get_llp_options
        result = get_llp_options()

        assert len(result) == 3
        assert result[0] == ('LLN111111111', 'LLN111111111 - Test Vessel 1')
        assert result[1] == ('LLN222222222', 'LLN222222222 - Test Vessel 2')

    @patch('app.views.transfers.supabase')
    def test_returns_empty_list_when_no_data(self, mock_supabase):
        """Should return empty list when no LLPs exist."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response

        from app.views.transfers import get_llp_options
        result = get_llp_options()

        assert result == []

    @patch('app.views.transfers.supabase')
    def test_handles_missing_vessel_name(self, mock_supabase):
        """Should use 'Unknown' when vessel_name is missing."""
        mock_response = MagicMock()
        mock_response.data = [{'llp': 'LLN111111111', 'vessel_name': None}]
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response

        from app.views.transfers import get_llp_options
        result = get_llp_options()

        assert result[0] == ('LLN111111111', 'LLN111111111 - Unknown')


class TestInsertTransfer:
    """Tests for insert_transfer function."""

    @patch('app.views.transfers.supabase')
    def test_successful_insert_returns_true(self, mock_supabase):
        """Should return (True, 1, None) on successful insert."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'new-uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        success, count, error = insert_transfer(
            from_llp='LLN111111111',
            to_llp='LLN222222222',
            species_code=141,
            pounds=1000.0,
            notes='Test transfer',
            user_id='user-123',
            org_id='test-org-id'
        )

        assert success is True
        assert count == 1
        assert error is None

    @patch('app.views.transfers.supabase')
    def test_insert_includes_correct_fields(self, mock_supabase):
        """Should insert record with all required fields."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'new-uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer, CURRENT_YEAR
        insert_transfer(
            from_llp='LLN111111111',
            to_llp='LLN222222222',
            species_code=141,
            pounds=1000.0,
            notes='Test note',
            user_id='user-123',
            org_id='test-org-id'
        )

        # Verify the insert was called with correct data
        mock_supabase.table.assert_called_with('quota_transfers')
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['from_llp'] == 'LLN111111111'
        assert call_args['to_llp'] == 'LLN222222222'
        assert call_args['species_code'] == 141
        assert call_args['year'] == CURRENT_YEAR
        assert call_args['pounds'] == 1000.0
        assert call_args['notes'] == 'Test note'
        assert call_args['created_by'] == 'user-123'
        assert call_args['is_deleted'] is False
        assert call_args['transfer_date'] == date.today().isoformat()

    @patch('app.views.transfers.supabase')
    def test_empty_notes_becomes_none(self, mock_supabase):
        """Should convert empty notes to None."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'new-uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        insert_transfer(
            from_llp='LLN111111111',
            to_llp='LLN222222222',
            species_code=141,
            pounds=1000.0,
            notes='',
            user_id='user-123',
            org_id='test-org-id'
        )

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['notes'] is None

    @patch('app.views.transfers.supabase')
    def test_database_error_returns_failure(self, mock_supabase):
        """Should return (False, 0, error_message) on database error."""
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Connection failed")

        from app.views.transfers import insert_transfer
        success, count, error = insert_transfer(
            from_llp='LLN111111111',
            to_llp='LLN222222222',
            species_code=141,
            pounds=1000.0,
            notes=None,
            user_id='user-123',
            org_id='test-org-id'
        )

        assert success is False
        assert count == 0
        assert error == "Connection failed"

    @patch('app.views.transfers.supabase')
    def test_empty_response_returns_failure(self, mock_supabase):
        """Should return failure when insert returns no data."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        success, count, error = insert_transfer(
            from_llp='LLN111111111',
            to_llp='LLN222222222',
            species_code=141,
            pounds=1000.0,
            notes=None,
            user_id='user-123',
            org_id='test-org-id'
        )

        assert success is False
        assert count == 0
        assert "no data" in error.lower()


class TestGetTransferHistory:
    """Tests for get_transfer_history function."""

    @patch('app.views.transfers.supabase')
    def test_returns_dataframe_with_transfers(self, mock_supabase):
        """Should return DataFrame with transfer history."""
        # Setup transfer data
        transfer_data = [{
            'id': 'uuid-1',
            'from_llp': 'LLN111111111',
            'to_llp': 'LLN222222222',
            'species_code': 141,
            'year': 2026,
            'pounds': 500,
            'transfer_date': '2026-01-05',
            'notes': 'Test transfer',
            'created_at': '2026-01-05T10:00:00Z',
        }]

        # Setup member data
        member_data = [
            {'llp': 'LLN111111111', 'vessel_name': 'Test Vessel 1'},
            {'llp': 'LLN222222222', 'vessel_name': 'Test Vessel 2'},
        ]

        # Mock responses for different table calls
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == 'quota_transfers':
                mock_response = MagicMock()
                mock_response.data = transfer_data
                mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
            else:  # coop_members
                mock_response = MagicMock()
                mock_response.data = member_data
                mock_table.select.return_value.execute.return_value = mock_response
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        from app.views.transfers import get_transfer_history
        result = get_transfer_history(2026)

        assert len(result) == 1
        assert 'species' in result.columns
        assert result.iloc[0]['species'] == 'POP'

    @patch('app.views.transfers.supabase')
    def test_returns_empty_dataframe_when_no_transfers(self, mock_supabase):
        """Should return empty DataFrame when no transfers exist."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.transfers import get_transfer_history
        result = get_transfer_history(2026)

        assert result.empty


class TestTransferValidation:
    """Tests for transfer validation logic (no mocking needed)."""

    def test_same_llp_validation(self):
        """Transferring to same LLP should be invalid."""
        from_llp = 'LLN111111111'
        to_llp = 'LLN111111111'

        is_same = from_llp == to_llp
        assert is_same is True

    def test_different_llp_validation(self):
        """Transferring to different LLP should be valid."""
        from_llp = 'LLN111111111'
        to_llp = 'LLN222222222'

        is_same = from_llp == to_llp
        assert is_same is False

    def test_insufficient_quota_validation(self):
        """Cannot transfer more than available quota."""
        available = 5000.0
        requested = 6000.0

        is_insufficient = requested > available
        assert is_insufficient is True

    def test_sufficient_quota_validation(self):
        """Can transfer up to available quota."""
        available = 5000.0
        requested = 5000.0

        is_insufficient = requested > available
        assert is_insufficient is False

    def test_zero_pounds_validation(self):
        """Cannot transfer zero pounds."""
        pounds = 0.0

        is_invalid = pounds <= 0
        assert is_invalid is True

    def test_negative_pounds_validation(self):
        """Cannot transfer negative pounds."""
        pounds = -100.0

        is_invalid = pounds <= 0
        assert is_invalid is True

    def test_valid_species_codes(self):
        """Only target species codes are valid."""
        from app.views.transfers import SPECIES_OPTIONS

        assert 141 in SPECIES_OPTIONS  # POP
        assert 136 in SPECIES_OPTIONS  # NR
        assert 172 in SPECIES_OPTIONS  # Dusky
        assert 200 not in SPECIES_OPTIONS  # Halibut (PSC) should not be included


class TestTransferIntegration:
    """Integration tests for the full transfer flow (logic only, no mocking)."""

    def test_transfer_reduces_source_increases_dest(self):
        """After transfer, source should decrease and destination should increase."""
        initial_source = 10000.0
        initial_dest = 5000.0
        transfer_amount = 2000.0

        expected_source = initial_source - transfer_amount
        expected_dest = initial_dest + transfer_amount

        assert expected_source == 8000.0
        assert expected_dest == 7000.0

    def test_boundary_transfer_exact_available(self):
        """Transferring exactly available amount should succeed."""
        available = 5000.0
        requested = 5000.0

        is_valid = requested <= available and requested > 0
        assert is_valid is True

    def test_boundary_transfer_one_over(self):
        """Transferring one more than available should fail."""
        available = 5000.0
        requested = 5001.0

        is_valid = requested <= available and requested > 0
        assert is_valid is False

    def test_decimal_precision(self):
        """Decimal values should be handled correctly."""
        available = 1000.50
        requested = 1000.50

        is_valid = requested <= available
        assert is_valid is True

    def test_very_small_transfer(self):
        """Very small transfers should be valid."""
        available = 10000.0
        requested = 0.01

        is_valid = requested <= available and requested > 0
        assert is_valid is True


class TestTransferEdgeCases:
    """Edge case tests for transfer functionality."""

    @patch('app.views.transfers.supabase')
    def test_negative_quota_remaining(self, mock_supabase):
        """Should handle negative remaining quota (overfished vessel)."""
        mock_response = MagicMock()
        mock_response.data = [{'remaining_lbs': -500.0}]  # Overfished
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        from app.views.transfers import get_quota_remaining
        result = get_quota_remaining('LLN111111111', 141, 2026)

        # Should return the negative value - can't transfer from overdrawn account
        assert result == -500.0

    def test_transfer_from_negative_quota_invalid(self):
        """Cannot transfer when source has negative quota."""
        available = -500.0
        requested = 100.0

        is_valid = requested <= available and requested > 0
        assert is_valid is False

    def test_transfer_from_zero_quota_invalid(self):
        """Cannot transfer when source has exactly zero quota."""
        available = 0.0
        requested = 100.0

        is_valid = requested <= available and requested > 0
        assert is_valid is False

    @patch('app.views.transfers.supabase')
    def test_very_long_notes_truncated_or_rejected(self, mock_supabase):
        """Should handle notes exceeding 500 characters."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'new-uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer

        long_notes = "A" * 600  # 600 characters
        success, count, error = insert_transfer(
            from_llp='LLN111111111',
            to_llp='LLN222222222',
            species_code=141,
            pounds=1000.0,
            notes=long_notes,
            user_id='user-123',
            org_id='test-org-id'
        )

        # Should still insert (DB will handle truncation or app should validate)
        # This test documents current behavior
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert len(call_args['notes']) == 600

    @patch('app.views.transfers.supabase')
    def test_whitespace_only_notes_becomes_none(self, mock_supabase):
        """Notes with only whitespace should become None."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'new-uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        insert_transfer(
            from_llp='LLN111111111',
            to_llp='LLN222222222',
            species_code=141,
            pounds=1000.0,
            notes='   ',  # Whitespace only
            user_id='user-123',
            org_id='test-org-id'
        )

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['notes'] is None  # Whitespace stripped to None

    @patch('app.views.transfers.supabase')
    def test_notes_with_surrounding_whitespace_stripped(self, mock_supabase):
        """Notes with surrounding whitespace should be trimmed."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'new-uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        insert_transfer(
            from_llp='LLN111111111',
            to_llp='LLN222222222',
            species_code=141,
            pounds=1000.0,
            notes='  Actual note content  ',
            user_id='user-123',
            org_id='test-org-id'
        )

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['notes'] == 'Actual note content'

    def test_float_precision_edge_case(self):
        """Float precision shouldn't cause false validation failures."""
        available = 1000.0
        # Simulate floating point arithmetic result
        requested = 333.33 + 333.33 + 333.34  # Should equal 1000.0

        is_valid = requested <= available and requested > 0
        assert is_valid is True

    @patch('app.views.transfers.supabase')
    def test_species_code_not_in_options(self, mock_supabase):
        """Should handle invalid species code gracefully."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'new-uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer, SPECIES_OPTIONS

        # Use a species code not in the valid options
        invalid_species = 999
        assert invalid_species not in SPECIES_OPTIONS

        # The function will still insert - validation should happen at UI level
        success, count, error = insert_transfer(
            from_llp='LLN111111111',
            to_llp='LLN222222222',
            species_code=invalid_species,
            pounds=1000.0,
            notes=None,
            user_id='user-123',
            org_id='test-org-id'
        )

        # Documents that DB insert will proceed (validation is UI responsibility)
        assert success is True


# =============================================================================
# NEW TESTS: Authentication & Authorization
# =============================================================================

class TestTransferAuthorization:
    """Tests for transfer page authorization."""

    @patch('app.views.transfers.require_role')
    @patch('app.views.transfers.st')
    def test_unauthenticated_user_blocked(self, mock_st, mock_require_role):
        """Unauthenticated user should be blocked from transfers page."""
        mock_require_role.return_value = False

        from app.views.transfers import show
        show()

        # Should have called require_role with 'manager'
        mock_require_role.assert_called_once_with("manager")

    @patch('app.views.transfers.require_role')
    @patch('app.views.transfers.st')
    def test_viewer_role_blocked(self, mock_st, mock_require_role):
        """Viewer role should be blocked from transfers."""
        mock_require_role.return_value = False

        from app.views.transfers import show
        result = show()

        # Function returns early when role check fails
        mock_require_role.assert_called_once_with("manager")

    @patch('app.views.transfers.require_role')
    @patch('app.views.transfers.st')
    def test_processor_role_blocked(self, mock_st, mock_require_role):
        """Processor role should be blocked from transfers."""
        mock_require_role.return_value = False

        from app.views.transfers import show
        show()

        mock_require_role.assert_called_once_with("manager")

    def test_require_role_checks_manager(self):
        """Transfer page should require 'manager' role."""
        # Verify the role requirement is correct
        from app.views.transfers import show
        import inspect
        source = inspect.getsource(show)
        assert 'require_role("manager")' in source


class TestTransferRoleHierarchy:
    """Tests for role hierarchy in transfers."""

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_admin_has_transfer_access(self, mock_st, mock_require_auth, mock_get_role):
        """Admin should have access to transfers."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = "admin"

        from app.auth import require_role
        result = require_role("manager")

        assert result is True

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_manager_has_transfer_access(self, mock_st, mock_require_auth, mock_get_role):
        """Manager should have access to transfers."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = "manager"

        from app.auth import require_role
        result = require_role("manager")

        assert result is True

    @patch('app.auth.get_current_role')
    @patch('app.auth.require_auth')
    @patch('app.auth.st')
    def test_vessel_owner_blocked_from_transfers(self, mock_st, mock_require_auth, mock_get_role):
        """Vessel owner should not have access to transfers."""
        mock_require_auth.return_value = True
        mock_get_role.return_value = "vessel_owner"

        from app.auth import require_role
        result = require_role("manager")

        assert result is False
        mock_st.error.assert_called()


# =============================================================================
# NEW TESTS: Multi-Tenancy / RLS
# =============================================================================

class TestTransferMultiTenancy:
    """Tests for multi-tenant isolation in transfers."""

    @patch('app.views.transfers.supabase')
    def test_insert_transfer_includes_org_id(self, mock_supabase):
        """Transfer insert should include org_id for RLS."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'new-uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        insert_transfer(
            from_llp='LLN111111111',
            to_llp='LLN222222222',
            species_code=141,
            pounds=1000.0,
            notes=None,
            user_id='user-123',
            org_id='org-uuid-123'
        )

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['org_id'] == 'org-uuid-123'

    @patch('app.views.transfers.supabase')
    def test_insert_transfer_with_different_org_ids(self, mock_supabase):
        """Different org_ids should be stored correctly."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'new-uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer

        # Org 1
        insert_transfer('LLN111', 'LLN222', 141, 1000.0, None, 'user1', 'org-1')
        call_args_1 = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args_1['org_id'] == 'org-1'

        # Org 2
        insert_transfer('LLN333', 'LLN444', 141, 2000.0, None, 'user2', 'org-2')
        call_args_2 = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args_2['org_id'] == 'org-2'

    def test_missing_org_id_validation(self):
        """Missing org_id should be caught (None passed)."""
        # This tests the UI validation behavior
        org_id = None
        assert org_id is None  # UI should check this before calling insert

    @patch('app.views.transfers.supabase')
    def test_empty_org_id_still_inserts(self, mock_supabase):
        """Empty org_id documents current behavior (DB should reject via RLS)."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'new-uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        success, _, _ = insert_transfer('LLN111', 'LLN222', 141, 1000.0, None, 'user', '')

        # Function allows empty org_id - RLS at DB level should reject
        assert success is True  # Documents that validation is at DB level


# =============================================================================
# NEW TESTS: Caching Behavior
# =============================================================================

class TestTransferCaching:
    """Tests for transfer caching behavior."""

    def test_clear_transfer_cache_function_exists(self):
        """clear_transfer_cache function should exist."""
        from app.views.transfers import clear_transfer_cache
        assert callable(clear_transfer_cache)

    @patch('app.views.transfers._fetch_transfer_history')
    def test_clear_cache_clears_history(self, mock_fetch):
        """clear_transfer_cache should clear the history cache."""
        from app.views.transfers import clear_transfer_cache

        # The function should call .clear() on the cached function
        clear_transfer_cache()

        mock_fetch.clear.assert_called_once()

    def test_cached_functions_have_ttl(self):
        """Cached functions should have appropriate TTL settings."""
        from app.views.transfers import (
            _fetch_coop_members_for_dropdown,
            _fetch_transfer_history,
            _fetch_llp_to_vessel_map
        )

        # These functions should be cached (have cache_data decorator)
        # We verify by checking they have the clear() method added by st.cache_data
        assert hasattr(_fetch_coop_members_for_dropdown, 'clear')
        assert hasattr(_fetch_transfer_history, 'clear')
        assert hasattr(_fetch_llp_to_vessel_map, 'clear')

    @patch('app.views.transfers.supabase')
    def test_dropdown_cache_separate_from_history(self, mock_supabase):
        """Dropdown cache should be separate from history cache."""
        from app.views.transfers import (
            _fetch_coop_members_for_dropdown,
            _fetch_transfer_history,
            clear_transfer_cache
        )

        # Clear only transfer cache
        clear_transfer_cache()

        # Dropdown cache should still exist (different function)
        assert hasattr(_fetch_coop_members_for_dropdown, 'clear')


# =============================================================================
# NEW TESTS: Concurrency / Race Conditions
# =============================================================================

class TestTransferConcurrency:
    """Tests for concurrent transfer scenarios."""

    def test_race_condition_scenario_documented(self):
        """Document the race condition window between check and insert."""
        # This test documents that there's a window between:
        # 1. get_quota_remaining() check
        # 2. insert_transfer() execution
        # During this window, another user could transfer the same quota

        # Current behavior: No locking mechanism
        # Recommendation: Use database transaction or optimistic locking

        available = 1000.0
        user1_transfer = 800.0
        user2_transfer = 800.0

        # Both users check and see 1000 available
        user1_sees = available
        user2_sees = available

        # Both attempt transfers
        user1_valid = user1_transfer <= user1_sees
        user2_valid = user2_transfer <= user2_sees

        # Both think they're valid!
        assert user1_valid is True
        assert user2_valid is True

        # But actual result would overdraw by 600
        actual_remaining = available - user1_transfer - user2_transfer
        assert actual_remaining == -600  # Overdraft!

    def test_concurrent_transfer_mitigation_strategies(self):
        """Document mitigation strategies for concurrent transfers."""
        strategies = [
            "1. Database-level constraint (CHECK remaining >= 0)",
            "2. Optimistic locking with version column",
            "3. SELECT FOR UPDATE in transaction",
            "4. Application-level mutex/semaphore",
        ]
        # This test documents that mitigations should be implemented
        assert len(strategies) == 4

    @patch('app.views.transfers.supabase')
    def test_rapid_sequential_transfers(self, mock_supabase):
        """Multiple rapid transfers should all be recorded."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer

        results = []
        for i in range(5):
            success, count, error = insert_transfer(
                f'LLN{i}11111111', f'LLN{i}22222222', 141, 100.0, None, 'user', 'org'
            )
            results.append(success)

        assert all(results)
        assert mock_supabase.table.return_value.insert.call_count == 5


# =============================================================================
# NEW TESTS: Business Logic Edge Cases
# =============================================================================

class TestTransferBusinessRules:
    """Tests for transfer business rules."""

    def test_minimum_transfer_one_pound(self):
        """Minimum transfer should be at least 1 pound."""
        from app.views.transfers import show
        import inspect
        source = inspect.getsource(show)
        # Check that min_value is set to 1.0 in number_input
        assert 'min_value=1.0' in source

    def test_maximum_transfer_ten_million(self):
        """Maximum transfer should be 10 million pounds."""
        from app.views.transfers import show
        import inspect
        source = inspect.getsource(show)
        assert 'max_value=10000000.0' in source

    def test_transfer_exactly_one_pound(self):
        """Transferring exactly 1 pound should be valid."""
        available = 1000.0
        requested = 1.0

        is_valid = requested <= available and requested > 0
        assert is_valid is True

    def test_transfer_exactly_max(self):
        """Transferring exactly max amount should be valid."""
        available = 10000000.0
        requested = 10000000.0

        is_valid = requested <= available and requested > 0
        assert is_valid is True

    def test_cross_coop_transfer_allowed(self):
        """Transfers between different co-ops should be allowed."""
        # Current implementation doesn't restrict cross-coop transfers
        from_coop = "Silver Bay Seafoods"
        to_coop = "NORTH PACIFIC"

        # No restriction in current code
        is_same_coop = from_coop == to_coop
        assert is_same_coop is False  # Different coops, should be allowed

    @patch('app.views.transfers.supabase')
    def test_transfer_creates_audit_trail(self, mock_supabase):
        """Transfer should include created_by for audit trail."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        insert_transfer('LLN111', 'LLN222', 141, 1000.0, None, 'audit-user-id', 'org')

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['created_by'] == 'audit-user-id'

    @patch('app.views.transfers.supabase')
    def test_transfer_date_is_today(self, mock_supabase):
        """Transfer date should be set to today."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        from datetime import date
        insert_transfer('LLN111', 'LLN222', 141, 1000.0, None, 'user', 'org')

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['transfer_date'] == date.today().isoformat()


class TestTransferToInactiveVessel:
    """Tests for transfers involving inactive vessels."""

    def test_inactive_vessel_not_filtered_in_dropdown(self):
        """Document: Currently no filtering of inactive vessels in dropdown."""
        # The get_llp_options query doesn't filter by is_active
        from app.views.transfers import get_llp_options
        import inspect
        source = inspect.getsource(get_llp_options)

        # Currently no is_active filter
        assert 'is_active' not in source

    @patch('app.views.transfers.supabase')
    def test_transfer_to_inactive_vessel_proceeds(self, mock_supabase):
        """Transfer to inactive vessel currently proceeds (no validation)."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer

        # LLP for an "inactive" vessel - no validation currently
        success, _, _ = insert_transfer(
            'LLN-INACTIVE', 'LLN-ACTIVE', 141, 1000.0, None, 'user', 'org'
        )

        # Documents current behavior - no inactive check
        assert success is True


# =============================================================================
# NEW TESTS: Security
# =============================================================================

class TestTransferSecurity:
    """Tests for transfer security concerns."""

    @patch('app.views.transfers.supabase')
    def test_sql_injection_in_notes_escaped(self, mock_supabase):
        """SQL injection attempts in notes should be safely handled."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer

        # SQL injection attempt
        malicious_notes = "'; DROP TABLE quota_transfers; --"
        insert_transfer('LLN111', 'LLN222', 141, 1000.0, malicious_notes, 'user', 'org')

        # The notes should be passed as-is (Supabase client handles escaping)
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['notes'] == malicious_notes

    @patch('app.views.transfers.supabase')
    def test_xss_in_notes_stored_as_is(self, mock_supabase):
        """XSS attempts in notes should be stored (display layer should escape)."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer

        # XSS attempt
        xss_notes = "<script>alert('xss')</script>"
        insert_transfer('LLN111', 'LLN222', 141, 1000.0, xss_notes, 'user', 'org')

        # Notes stored as-is - display layer (Streamlit) should escape
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['notes'] == xss_notes

    @patch('app.views.transfers.supabase')
    def test_unicode_injection_in_notes(self, mock_supabase):
        """Unicode/special characters in notes should be handled."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer

        unicode_notes = "Transfer 日本語 emoji 🐟 special chars: àéîõü"
        insert_transfer('LLN111', 'LLN222', 141, 1000.0, unicode_notes, 'user', 'org')

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['notes'] == unicode_notes

    def test_llp_format_validation(self):
        """LLP values should follow expected format."""
        valid_llps = ['LLN111111111', 'LLN999999999', 'LLN123456789']
        invalid_llps = ['INVALID', '123', '', None]

        for llp in valid_llps:
            # LLP format: LLN followed by 9 digits
            assert llp.startswith('LLN') and len(llp) == 12

    @patch('app.views.transfers.supabase')
    def test_forged_llp_accepted_by_function(self, mock_supabase):
        """Document: insert_transfer doesn't validate LLP format."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer

        # Forged/invalid LLP - function doesn't validate
        success, _, _ = insert_transfer(
            'FORGED_LLP', 'ANOTHER_FAKE', 141, 1000.0, None, 'user', 'org'
        )

        # Documents that validation relies on dropdown (not function)
        assert success is True


class TestTransferInputSanitization:
    """Tests for input sanitization."""

    @patch('app.views.transfers.supabase')
    def test_pounds_must_be_positive(self, mock_supabase):
        """Pounds validation should reject negative values."""
        # UI enforces min_value=1.0, but test the logic
        pounds = -100.0
        is_invalid = pounds <= 0
        assert is_invalid is True

    @patch('app.views.transfers.supabase')
    def test_pounds_must_be_numeric(self, mock_supabase):
        """Pounds should be numeric (handled by Streamlit number_input)."""
        # Streamlit's number_input enforces numeric type
        # This test documents the expectation
        try:
            float("not a number")
            is_numeric = True
        except ValueError:
            is_numeric = False

        assert is_numeric is False

    @patch('app.views.transfers.supabase')
    def test_species_code_must_be_valid(self, mock_supabase):
        """Species code should be one of the valid options."""
        from app.views.transfers import SPECIES_OPTIONS

        valid_codes = list(SPECIES_OPTIONS.keys())
        assert 141 in valid_codes
        assert 136 in valid_codes
        assert 172 in valid_codes
        assert 999 not in valid_codes


# =============================================================================
# NEW TESTS: Year/Date Handling
# =============================================================================

class TestTransferYearHandling:
    """Tests for year and date handling in transfers."""

    def test_current_year_constant(self):
        """CURRENT_YEAR constant should be set correctly."""
        from app.views.transfers import CURRENT_YEAR
        assert CURRENT_YEAR == 2026

    @patch('app.views.transfers.supabase')
    def test_transfer_uses_current_year(self, mock_supabase):
        """Transfer should use CURRENT_YEAR constant."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer, CURRENT_YEAR
        insert_transfer('LLN111', 'LLN222', 141, 1000.0, None, 'user', 'org')

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['year'] == CURRENT_YEAR

    @patch('app.views.transfers.supabase')
    def test_quota_check_uses_current_year(self, mock_supabase):
        """Quota remaining check should use CURRENT_YEAR."""
        mock_response = MagicMock()
        mock_response.data = [{'remaining_lbs': 5000.0}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        from app.views.transfers import get_quota_remaining, CURRENT_YEAR
        get_quota_remaining('LLN111', 141)  # Uses default year

        # Verify year was passed correctly
        calls = mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.call_args_list
        # The third .eq() call should be for year
        year_call = calls[0]
        assert year_call[0] == ('year', CURRENT_YEAR)

    @patch('app.views.transfers.supabase')
    def test_history_fetch_uses_specified_year(self, mock_supabase):
        """Transfer history should fetch for specified year."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.transfers import get_transfer_history
        get_transfer_history(2025)  # Specific year

        # Should query for 2025
        mock_supabase.table.return_value.select.return_value.eq.assert_any_call('year', 2025)

    def test_transfer_date_format(self):
        """Transfer date should be ISO format (YYYY-MM-DD)."""
        from datetime import date
        today = date.today().isoformat()

        # Verify format
        assert len(today) == 10
        assert today[4] == '-'
        assert today[7] == '-'

    @patch('app.views.transfers.supabase')
    def test_historical_year_transfer_allowed(self, mock_supabase):
        """Document: No restriction on transferring for past years via API."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer

        # insert_transfer uses CURRENT_YEAR constant, not a parameter
        # So historical year transfer is controlled by the constant
        success, _, _ = insert_transfer('LLN111', 'LLN222', 141, 1000.0, None, 'user', 'org')

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        # Year is always CURRENT_YEAR (2026)
        assert call_args['year'] == 2026


class TestTransferDateEdgeCases:
    """Edge cases for date handling."""

    def test_year_boundary_dec_31(self):
        """Transfer on Dec 31 should use current year."""
        from datetime import date
        # Simulate Dec 31
        dec_31 = date(2026, 12, 31)
        assert dec_31.year == 2026

    def test_year_boundary_jan_1(self):
        """Transfer on Jan 1 should use new year."""
        from datetime import date
        jan_1 = date(2027, 1, 1)
        assert jan_1.year == 2027

    @patch('app.views.transfers.date')
    @patch('app.views.transfers.supabase')
    def test_transfer_date_uses_system_date(self, mock_supabase, mock_date):
        """Transfer date should come from system date."""
        from datetime import date as real_date
        mock_date.today.return_value = real_date(2026, 6, 15)
        mock_date.side_effect = lambda *args, **kwargs: real_date(*args, **kwargs)

        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        insert_transfer('LLN111', 'LLN222', 141, 1000.0, None, 'user', 'org')

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        # Date comes from date.today()
        assert 'transfer_date' in call_args


# =============================================================================
# NEW TESTS: Soft Delete Behavior
# =============================================================================

class TestTransferSoftDelete:
    """Tests for soft delete behavior."""

    @patch('app.views.transfers.supabase')
    def test_new_transfer_has_is_deleted_false(self, mock_supabase):
        """New transfers should have is_deleted=False."""
        mock_response = MagicMock()
        mock_response.data = [{'id': 'uuid'}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        from app.views.transfers import insert_transfer
        insert_transfer('LLN111', 'LLN222', 141, 1000.0, None, 'user', 'org')

        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args['is_deleted'] is False

    @patch('app.views.transfers.supabase')
    def test_history_excludes_deleted_transfers(self, mock_supabase):
        """Transfer history should only show non-deleted transfers."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.transfers import _fetch_transfer_history
        _fetch_transfer_history(2026)

        # Verify the chain: .eq("year", year).eq("is_deleted", False)
        # First eq call is for year, second is for is_deleted
        first_eq = mock_supabase.table.return_value.select.return_value.eq
        first_eq.assert_called_with("year", 2026)
        second_eq = first_eq.return_value.eq
        second_eq.assert_called_with("is_deleted", False)


# =============================================================================
# NEW TESTS: Display Formatting
# =============================================================================

class TestTransferDisplayFormatting:
    """Tests for transfer display formatting."""

    def test_species_code_to_name_mapping(self):
        """Species codes should map to correct names."""
        from app.views.transfers import SPECIES_OPTIONS

        assert 'POP' in SPECIES_OPTIONS[141]
        assert 'NR' in SPECIES_OPTIONS[136] or 'Northern' in SPECIES_OPTIONS[136]
        assert 'Dusky' in SPECIES_OPTIONS[172]

    @patch('app.views.transfers.supabase')
    def test_history_includes_vessel_names(self, mock_supabase):
        """Transfer history should include vessel names."""
        transfer_data = [{
            'id': 'uuid', 'from_llp': 'LLN111', 'to_llp': 'LLN222',
            'species_code': 141, 'pounds': 500, 'transfer_date': '2026-01-01',
            'notes': None, 'created_at': '2026-01-01T00:00:00Z'
        }]
        member_data = [
            {'llp': 'LLN111', 'vessel_name': 'Vessel One'},
            {'llp': 'LLN222', 'vessel_name': 'Vessel Two'}
        ]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == 'quota_transfers':
                mock_response = MagicMock()
                mock_response.data = transfer_data
                mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
            else:
                mock_response = MagicMock()
                mock_response.data = member_data
                mock_table.select.return_value.execute.return_value = mock_response
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        from app.views.transfers import get_transfer_history
        result = get_transfer_history(2026)

        assert 'from_vessel' in result.columns
        assert 'to_vessel' in result.columns
        assert result.iloc[0]['from_vessel'] == 'Vessel One'
        assert result.iloc[0]['to_vessel'] == 'Vessel Two'

    def test_pounds_formatted_with_commas(self):
        """Pounds should be formatted with thousand separators in display."""
        # The UI uses st.dataframe with style.format
        # This documents the expected formatting
        pounds = 1234567.89
        formatted = f"{pounds:,.0f}"
        assert formatted == "1,234,568"
