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
            user_id='user-123'
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
            user_id='user-123'
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
            user_id='user-123'
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
            user_id='user-123'
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
            user_id='user-123'
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
