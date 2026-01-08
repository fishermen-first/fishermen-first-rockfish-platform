"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_supabase(mocker):
    """Mock the Supabase client where it's used in transfers module."""
    mock_client = MagicMock()
    # Patch where it's imported, not where it's defined
    mocker.patch('app.views.transfers.supabase', mock_client)
    return mock_client


@pytest.fixture
def mock_session_state(mocker):
    """Mock Streamlit session state with authenticated user."""
    mock_state = {
        'authenticated': True,
        'user': MagicMock(id='test-user-123', email='test@example.com'),
        'user_role': 'manager',
        'processor_code': None,
        'access_token': 'fake-token',
        'refresh_token': 'fake-refresh',
    }
    mocker.patch('streamlit.session_state', mock_state)
    return mock_state


@pytest.fixture
def sample_llp_data():
    """Sample LLP/coop_members data for testing."""
    return [
        {'llp': 'LLN111111111', 'vessel_name': 'Test Vessel 1', 'coop_code': 'SB'},
        {'llp': 'LLN222222222', 'vessel_name': 'Test Vessel 2', 'coop_code': 'SB'},
        {'llp': 'LLN333333333', 'vessel_name': 'Test Vessel 3', 'coop_code': 'NP'},
    ]


@pytest.fixture
def sample_quota_remaining():
    """Sample quota_remaining view data."""
    return [
        {'llp': 'LLN111111111', 'species_code': 141, 'year': 2026,
         'allocation_lbs': 10000, 'transfers_in': 0, 'transfers_out': 0,
         'harvested': 2000, 'remaining_lbs': 8000},
        {'llp': 'LLN111111111', 'species_code': 136, 'year': 2026,
         'allocation_lbs': 5000, 'transfers_in': 1000, 'transfers_out': 500,
         'harvested': 1000, 'remaining_lbs': 4500},
        {'llp': 'LLN222222222', 'species_code': 141, 'year': 2026,
         'allocation_lbs': 8000, 'transfers_in': 500, 'transfers_out': 0,
         'harvested': 1000, 'remaining_lbs': 7500},
    ]


@pytest.fixture
def sample_transfer_history():
    """Sample transfer history data."""
    return [
        {
            'id': 'uuid-1',
            'from_llp': 'LLN111111111',
            'to_llp': 'LLN222222222',
            'species_code': 141,
            'year': 2026,
            'pounds': 500,
            'transfer_date': '2026-01-05',
            'notes': 'Test transfer',
            'created_at': '2026-01-05T10:00:00Z',
        },
    ]
