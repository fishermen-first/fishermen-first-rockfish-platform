"""Unit tests for bycatch alerts management functionality.

Tests cover manager scenarios for reviewing, editing, filtering, and sharing bycatch alerts.
Following TDD approach - skeletons defined first, implementation to follow.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, date
import importlib


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def clear_streamlit_caches():
    """Clear Streamlit caches before each test to prevent cross-test contamination."""
    yield
    # Clear after each test
    try:
        from app.views.bycatch_alerts import _fetch_alerts, get_pending_alert_count, _fetch_coop_members, _fetch_vessel_contacts_count
        _fetch_alerts.clear()
        get_pending_alert_count.clear()
        _fetch_coop_members.clear()
        _fetch_vessel_contacts_count.clear()
    except Exception:
        pass


@pytest.fixture
def sample_pending_alerts():
    """Sample pending bycatch alerts for testing."""
    return [
        {
            'id': 'alert-uuid-1',
            'org_id': 'test-org-id',
            'reported_by_llp': 'LLN111111111',
            'species_code': 200,  # Halibut
            'latitude': 57.5,
            'longitude': -152.3,
            'amount': 500,
            'details': 'High bycatch area near reef',
            'status': 'pending',
            'created_at': '2026-01-15T10:30:00Z',
            'created_by': 'vessel-owner-user-1',
            'shared_at': None,
            'shared_by': None,
        },
        {
            'id': 'alert-uuid-2',
            'org_id': 'test-org-id',
            'reported_by_llp': 'LLN222222222',
            'species_code': 110,  # Pacific Cod
            'latitude': 58.1,
            'longitude': -151.8,
            'amount': 250,
            'details': None,
            'status': 'pending',
            'created_at': '2026-01-15T14:45:00Z',
            'created_by': 'vessel-owner-user-2',
            'shared_at': None,
            'shared_by': None,
        },
    ]


@pytest.fixture
def sample_shared_alerts():
    """Sample shared bycatch alerts for testing."""
    return [
        {
            'id': 'alert-uuid-3',
            'org_id': 'test-org-id',
            'reported_by_llp': 'LLN333333333',
            'species_code': 200,
            'latitude': 56.8,
            'longitude': -153.2,
            'amount': 800,
            'details': 'Large school spotted',
            'status': 'shared',
            'created_at': '2026-01-14T08:00:00Z',
            'created_by': 'vessel-owner-user-3',
            'shared_at': '2026-01-14T09:15:00Z',
            'shared_by': 'manager-user-1',
            'shared_recipient_count': 12,
        },
    ]


@pytest.fixture
def sample_vessel_contacts():
    """Sample vessel contacts for email broadcast."""
    return [
        {'id': 'contact-1', 'llp': 'LLN111111111', 'name': 'John Doe', 'email': 'john@vessel1.com', 'is_primary': True},
        {'id': 'contact-2', 'llp': 'LLN222222222', 'name': 'Jane Smith', 'email': 'jane@vessel2.com', 'is_primary': True},
        {'id': 'contact-3', 'llp': 'LLN222222222', 'name': 'Bob Jones', 'email': 'bob@vessel2.com', 'is_primary': False},
        {'id': 'contact-4', 'llp': 'LLN333333333', 'name': 'Alice Brown', 'email': 'alice@vessel3.com', 'is_primary': True},
    ]


@pytest.fixture
def sample_species():
    """Sample PSC species for testing."""
    return [
        {'code': 200, 'name': 'Halibut', 'abbreviation': 'HLBT', 'is_psc': True},
        {'code': 110, 'name': 'Pacific Cod', 'abbreviation': 'PCOD', 'is_psc': True},
        {'code': 710, 'name': 'Sablefish', 'abbreviation': 'SABL', 'is_psc': True},
    ]


@pytest.fixture
def sample_coop_members():
    """Sample coop members for filter dropdown."""
    return [
        {'llp': 'LLN111111111', 'vessel_name': 'F/V Endeavor', 'coop_code': 'SBS'},
        {'llp': 'LLN222222222', 'vessel_name': 'F/V Horizon', 'coop_code': 'SBS'},
        {'llp': 'LLN333333333', 'vessel_name': 'F/V Pacific Star', 'coop_code': 'NP'},
    ]


# =============================================================================
# MANAGER SCENARIO 1: See pending alerts at a glance (sidebar badge)
# =============================================================================

class TestPendingAlertCount:
    """Tests for fetching pending alert count for sidebar badge."""

    @patch('app.views.bycatch_alerts.supabase')
    def test_returns_pending_count(self, mock_supabase):
        """Should return count of pending alerts for org."""
        mock_response = MagicMock()
        mock_response.count = 5
        # Chain: .eq(org_id).eq(status).eq(is_deleted).execute()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import get_pending_alert_count
        result = get_pending_alert_count('test-org-id')

        assert result == 5

    @patch('app.views.bycatch_alerts.supabase')
    def test_returns_zero_when_no_pending(self, mock_supabase):
        """Should return 0 when no pending alerts exist."""
        mock_response = MagicMock()
        mock_response.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import get_pending_alert_count
        result = get_pending_alert_count('test-org-id')

        assert result == 0

    @patch('app.views.bycatch_alerts.supabase')
    def test_handles_database_error(self, mock_supabase):
        """Should return 0 on database error."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        from app.views.bycatch_alerts import get_pending_alert_count
        result = get_pending_alert_count('test-org-id')

        assert result == 0


# =============================================================================
# MANAGER SCENARIO 2: View all pending alerts with full details
# =============================================================================

class TestFetchAlerts:
    """Tests for fetching alerts with various filters."""

    @patch('app.views.bycatch_alerts.supabase')
    def test_fetch_pending_alerts(self, mock_supabase, sample_pending_alerts):
        """Should fetch all pending alerts for org."""
        mock_response = MagicMock()
        mock_response.data = sample_pending_alerts
        # With status filter: .eq(org_id).eq(is_deleted).eq(status).order().execute()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        result = fetch_alerts('test-org-id', status='pending')

        assert len(result) == 2
        assert all(a['status'] == 'pending' for a in result)

    @patch('app.views.bycatch_alerts.supabase')
    def test_fetch_shared_alerts(self, mock_supabase, sample_shared_alerts):
        """Should fetch all shared alerts for org."""
        mock_response = MagicMock()
        mock_response.data = sample_shared_alerts
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        result = fetch_alerts('test-org-id', status='shared')

        assert len(result) == 1
        assert result[0]['status'] == 'shared'

    @patch('app.views.bycatch_alerts.supabase')
    def test_fetch_all_alerts(self, mock_supabase, sample_pending_alerts, sample_shared_alerts):
        """Should fetch all alerts regardless of status."""
        mock_response = MagicMock()
        mock_response.data = sample_pending_alerts + sample_shared_alerts
        # Without status filter: .eq(org_id).eq(is_deleted).order().execute()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        result = fetch_alerts('test-org-id', status=None)

        assert len(result) == 3

    @patch('app.views.bycatch_alerts.supabase')
    def test_excludes_deleted_alerts(self, mock_supabase):
        """Should not return soft-deleted alerts."""
        mock_response = MagicMock()
        mock_response.data = []  # Deleted alerts filtered by query
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        result = fetch_alerts('test-org-id', status='pending')

        assert result == []


# =============================================================================
# MANAGER SCENARIO 9: Filter alerts by co-op, species, or date
# =============================================================================

class TestAlertFiltering:
    """Tests for filtering alerts by various criteria.

    Note: fetch_alerts() fetches all alerts via _fetch_alerts (DB query),
    then applies species/coop/date filters in Python.
    """

    @patch('app.views.bycatch_alerts.supabase')
    def test_filter_by_coop(self, mock_supabase, sample_pending_alerts, sample_coop_members):
        """Should filter alerts by cooperative."""
        # Add a non-SBS alert to verify filtering
        all_alerts = sample_pending_alerts + [{
            'id': 'alert-uuid-np',
            'org_id': 'test-org-id',
            'reported_by_llp': 'LLN333333333',  # NP coop
            'species_code': 200,
            'latitude': 56.8, 'longitude': -153.2,
            'amount': 300, 'details': None,
            'status': 'pending',
            'created_at': '2026-01-15T16:00:00Z',
            'created_by': 'user-3',
            'shared_at': None, 'shared_by': None,
        }]
        # Alerts query (no status filter): .eq(org_id).eq(is_deleted).order().execute()
        mock_alerts = MagicMock()
        mock_alerts.data = all_alerts
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_alerts
        # Members query: .select().order().execute()
        mock_members = MagicMock()
        mock_members.data = sample_coop_members
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_members

        from app.views.bycatch_alerts import fetch_alerts
        result = fetch_alerts('test-org-id', coop_code='SBS')

        assert len(result) == 2
        assert all(a['reported_by_llp'] in ['LLN111111111', 'LLN222222222'] for a in result)

    @patch('app.views.bycatch_alerts.supabase')
    def test_filter_by_species(self, mock_supabase, sample_pending_alerts):
        """Should filter alerts by PSC species."""
        mock_response = MagicMock()
        mock_response.data = sample_pending_alerts  # has species 200 and 110
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        result = fetch_alerts('test-org-id', species_code=200)

        assert len(result) == 1
        assert result[0]['species_code'] == 200

    @patch('app.views.bycatch_alerts.supabase')
    def test_filter_by_date_range(self, mock_supabase, sample_pending_alerts):
        """Should filter alerts by date range."""
        mock_response = MagicMock()
        mock_response.data = sample_pending_alerts
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        result = fetch_alerts(
            'test-org-id',
            date_from=date(2026, 1, 15),
            date_to=date(2026, 1, 15)
        )

        # Both alerts are Jan 15 in Alaska time
        assert len(result) == 2

    @patch('app.views.bycatch_alerts.supabase')
    def test_combined_filters(self, mock_supabase, sample_coop_members):
        """Should apply multiple filters together."""
        # Mock alerts (with status: 3 eq's)
        mock_alerts = MagicMock()
        mock_alerts.data = [{
            'id': 'alert-uuid-1', 'org_id': 'test-org-id',
            'reported_by_llp': 'LLN111111111', 'species_code': 200,
            'latitude': 57.5, 'longitude': -152.3, 'amount': 500,
            'status': 'pending', 'created_at': '2026-01-15T10:30:00Z',
            'shared_at': None, 'shared_by': None,
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_alerts
        # Mock members
        mock_members = MagicMock()
        mock_members.data = sample_coop_members
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_members

        from app.views.bycatch_alerts import fetch_alerts
        result = fetch_alerts(
            'test-org-id',
            status='pending',
            species_code=200,
            coop_code='SBS',
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31)
        )

        assert isinstance(result, list)
        assert len(result) == 1


# =============================================================================
# MANAGER SCENARIO 10: Edit alert details before sharing
# =============================================================================

class TestEditAlert:
    """Tests for editing alert details before sharing."""

    @patch('app.views.bycatch_alerts.supabase')
    def test_update_latitude(self, mock_supabase):
        """Should update alert latitude."""
        # Check query returns pending status
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        # Update query
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1', 'latitude': 58.0}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        from app.views.bycatch_alerts import update_alert
        success, error = update_alert('alert-uuid-1', latitude=58.0)

        assert success is True
        assert error is None

    @patch('app.views.bycatch_alerts.supabase')
    def test_update_longitude(self, mock_supabase):
        """Should update alert longitude."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1', 'longitude': -151.0}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        from app.views.bycatch_alerts import update_alert
        success, error = update_alert('alert-uuid-1', longitude=-151.0)

        assert success is True

    @patch('app.views.bycatch_alerts.supabase')
    def test_update_amount(self, mock_supabase):
        """Should update alert amount."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1', 'amount': 750}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        from app.views.bycatch_alerts import update_alert
        success, error = update_alert('alert-uuid-1', amount=750)

        assert success is True

    @patch('app.views.bycatch_alerts.supabase')
    def test_update_multiple_fields(self, mock_supabase):
        """Should update multiple fields at once."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1'}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        from app.views.bycatch_alerts import update_alert
        success, error = update_alert(
            'alert-uuid-1',
            latitude=58.0,
            longitude=-151.0,
            amount=750,
            details='Updated details'
        )

        assert success is True

    @patch('app.views.bycatch_alerts.supabase')
    def test_cannot_edit_shared_alert(self, mock_supabase):
        """Should not allow editing already-shared alerts."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'shared'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check

        from app.views.bycatch_alerts import update_alert
        success, error = update_alert('shared-alert-uuid', latitude=58.0)

        assert success is False
        assert 'already shared' in error.lower()

    def test_validate_latitude_bounds(self):
        """Should reject latitude outside Alaska bounds."""
        from app.views.bycatch_alerts import validate_alert_edit

        valid, error = validate_alert_edit(latitude=45.0)  # Too far south
        assert valid is False
        assert 'latitude' in error.lower()

        valid, error = validate_alert_edit(latitude=75.0)  # Too far north
        assert valid is False

    def test_validate_longitude_bounds(self):
        """Should reject longitude outside Alaska bounds."""
        from app.views.bycatch_alerts import validate_alert_edit

        valid, error = validate_alert_edit(longitude=-120.0)  # Too far east
        assert valid is False
        assert 'longitude' in error.lower()

    def test_validate_amount_positive(self):
        """Should reject non-positive amounts."""
        from app.views.bycatch_alerts import validate_alert_edit

        valid, error = validate_alert_edit(amount=0)
        assert valid is False
        assert 'amount' in error.lower()

        valid, error = validate_alert_edit(amount=-100)
        assert valid is False


# =============================================================================
# MANAGER SCENARIO 5: Dismiss irrelevant or duplicate alerts
# =============================================================================

class TestDismissAlert:
    """Tests for dismissing alerts."""

    @patch('app.views.bycatch_alerts.supabase')
    def test_dismiss_sets_status(self, mock_supabase):
        """Should set status to dismissed."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1', 'status': 'dismissed'}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        from app.views.bycatch_alerts import dismiss_alert
        success, error = dismiss_alert('alert-uuid-1', 'manager-user-1')

        assert success is True

    @patch('app.views.bycatch_alerts.supabase')
    def test_dismiss_records_deleted_by(self, mock_supabase):
        """Should record who dismissed the alert."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1'}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        from app.views.bycatch_alerts import dismiss_alert
        dismiss_alert('alert-uuid-1', 'manager-user-1')

        # Verify update includes deleted_by
        update_call = mock_supabase.table.return_value.update.call_args
        assert 'deleted_by' in update_call[0][0]

    @patch('app.views.bycatch_alerts.supabase')
    def test_cannot_dismiss_shared_alert(self, mock_supabase):
        """Should not allow dismissing already-shared alerts."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'shared'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check

        from app.views.bycatch_alerts import dismiss_alert
        success, error = dismiss_alert('shared-alert-uuid', 'manager-user-1')

        assert success is False
        assert 'already shared' in error.lower()


# =============================================================================
# MANAGER SCENARIO 3: Preview email content before sending
# =============================================================================

class TestEmailPreview:
    """Tests for email preview generation."""

    def test_preview_includes_species(self, sample_pending_alerts, sample_species):
        """Should include species name in preview."""
        from app.views.bycatch_alerts import generate_email_preview

        preview = generate_email_preview(sample_pending_alerts[0], sample_species)

        assert 'Halibut' in preview['body']
        assert 'Halibut' in preview['subject']

    def test_preview_includes_coordinates(self, sample_pending_alerts, sample_species):
        """Should include GPS coordinates in preview."""
        from app.views.bycatch_alerts import generate_email_preview

        preview = generate_email_preview(sample_pending_alerts[0], sample_species)

        assert '57.5' in preview['body']
        # Code uses abs() for longitude display
        assert '152.3' in preview['body']

    def test_preview_includes_amount(self, sample_pending_alerts, sample_species):
        """Should include bycatch amount in preview."""
        from app.views.bycatch_alerts import generate_email_preview

        preview = generate_email_preview(sample_pending_alerts[0], sample_species)

        assert '500' in preview['body']

    def test_preview_includes_details_when_present(self, sample_pending_alerts, sample_species):
        """Should include details when provided."""
        from app.views.bycatch_alerts import generate_email_preview

        preview = generate_email_preview(sample_pending_alerts[0], sample_species)

        assert 'High bycatch area near reef' in preview['body']

    def test_preview_handles_missing_details(self, sample_pending_alerts, sample_species):
        """Should handle alerts without details gracefully."""
        from app.views.bycatch_alerts import generate_email_preview

        # Alert at index 1 has no details
        preview = generate_email_preview(sample_pending_alerts[1], sample_species)

        # Should not crash or include 'None'
        assert 'None' not in preview['body']

    @patch('app.views.bycatch_alerts.supabase')
    def test_preview_shows_recipient_count(self, mock_supabase):
        """Should show how many recipients will receive the email."""
        mock_response = MagicMock()
        # _fetch_vessel_contacts_count uses response.count, not response.data
        mock_response.count = 4
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import get_recipient_count
        count = get_recipient_count('test-org-id')

        assert count == 4


# =============================================================================
# MANAGER SCENARIO 4: Share/broadcast alert to entire fleet
# =============================================================================

class TestShareAlert:
    """Tests for sharing alerts to fleet."""

    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'})
    @patch('streamlit.session_state', {'org_id': 'test-org-id'})
    @patch('app.views.bycatch_alerts.supabase')
    @patch('requests.post')
    def test_share_updates_status(self, mock_requests_post, mock_supabase):
        """Should update alert status to shared."""
        # Check: pending
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending', 'shared_at': None}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        # Contacts count
        mock_contacts = MagicMock()
        mock_contacts.count = 10
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_contacts
        # Update
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1', 'status': 'shared'}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update
        # HTTP response
        mock_http = MagicMock()
        mock_http.status_code = 200
        mock_http.json.return_value = {'success': True, 'sent_count': 10}
        mock_requests_post.return_value = mock_http

        from app.views.bycatch_alerts import share_alert
        success, result = share_alert('alert-uuid-1', 'manager-user-1')

        assert success is True

    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'})
    @patch('streamlit.session_state', {'org_id': 'test-org-id'})
    @patch('app.views.bycatch_alerts.supabase')
    @patch('requests.post')
    def test_share_records_shared_by(self, mock_requests_post, mock_supabase):
        """Should record who shared the alert."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending', 'shared_at': None}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_contacts = MagicMock()
        mock_contacts.count = 5
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_contacts
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1'}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update
        mock_http = MagicMock()
        mock_http.status_code = 200
        mock_http.json.return_value = {'success': True}
        mock_requests_post.return_value = mock_http

        from app.views.bycatch_alerts import share_alert
        share_alert('alert-uuid-1', 'manager-user-1')

        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call is not None
        assert update_call[0][0].get('shared_by') == 'manager-user-1'

    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'})
    @patch('streamlit.session_state', {'org_id': 'test-org-id'})
    @patch('app.views.bycatch_alerts.supabase')
    @patch('requests.post')
    def test_share_records_recipient_count(self, mock_requests_post, mock_supabase):
        """Should record how many recipients received the email."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending', 'shared_at': None}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_contacts = MagicMock()
        mock_contacts.count = 15
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_contacts
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1'}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update
        mock_http = MagicMock()
        mock_http.status_code = 200
        mock_http.json.return_value = {'success': True, 'sent_count': 15}
        mock_requests_post.return_value = mock_http

        from app.views.bycatch_alerts import share_alert
        success, result = share_alert('alert-uuid-1', 'manager-user-1')

        assert result.get('sent_count') == 15

    @patch('app.views.bycatch_alerts.supabase')
    def test_share_already_shared_is_idempotent(self, mock_supabase):
        """Should return success without re-sending for already shared alert."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'shared', 'shared_at': '2026-01-15T10:00:00Z'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check

        from app.views.bycatch_alerts import share_alert
        success, result = share_alert('alert-uuid-1', 'manager-user-1')

        assert success is True
        assert result.get('already_shared') is True

    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'})
    @patch('streamlit.session_state', {'org_id': 'test-org-id'})
    @patch('app.views.bycatch_alerts.supabase')
    @patch('requests.post')
    def test_share_handles_edge_function_error(self, mock_requests_post, mock_supabase):
        """Should still mark alert as shared even if Edge Function fails."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending', 'shared_at': None}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_contacts = MagicMock()
        mock_contacts.count = 5
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_contacts
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1', 'status': 'shared'}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update
        mock_requests_post.side_effect = Exception("Edge Function error")

        from app.views.bycatch_alerts import share_alert
        success, result = share_alert('alert-uuid-1', 'manager-user-1')

        # Alert is still shared even though email failed
        assert success is True
        assert 'email_error' in result


# =============================================================================
# MANAGER SCENARIO 7: See email delivery status/errors
# =============================================================================

class TestEmailDeliveryLog:
    """Tests for viewing email delivery logs."""

    @patch('app.views.bycatch_alerts.supabase')
    def test_fetch_delivery_log(self, mock_supabase):
        """Should fetch delivery log for an alert."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                'id': 'log-uuid-1',
                'alert_id': 'alert-uuid-1',
                'recipient_count': 12,
                'status': 'success',
                'created_at': '2026-01-15T10:30:00Z',
            }
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_delivery_log
        result = fetch_delivery_log('alert-uuid-1')

        assert len(result) == 1
        assert result[0]['status'] == 'success'

    @patch('app.views.bycatch_alerts.supabase')
    def test_delivery_log_shows_partial_failures(self, mock_supabase):
        """Should show partial delivery status."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                'id': 'log-uuid-1',
                'alert_id': 'alert-uuid-1',
                'recipient_count': 10,
                'status': 'partial',
                'error_message': '2 emails bounced',
            }
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_delivery_log
        result = fetch_delivery_log('alert-uuid-1')

        assert result[0]['status'] == 'partial'
        assert 'bounced' in result[0]['error_message']


# =============================================================================
# AUTHORIZATION TESTS
# =============================================================================

class TestBycatchAlertsAuthorization:
    """Tests for role-based access control."""

    @patch('streamlit.session_state', {'user_role': 'manager'})
    def test_manager_can_access_alerts_page(self):
        """Managers should have access to bycatch alerts page."""
        from app.views.bycatch_alerts import check_access
        assert check_access() is True

    @patch('streamlit.session_state', {'user_role': 'admin'})
    def test_admin_can_access_alerts_page(self):
        """Admins should have access to bycatch alerts page."""
        from app.views.bycatch_alerts import check_access
        assert check_access() is True

    @patch('streamlit.session_state', {'user_role': 'vessel_owner'})
    def test_vessel_owner_cannot_access_alerts_page(self):
        """Vessel owners should NOT have access to manager alerts page."""
        from app.views.bycatch_alerts import check_access
        assert check_access() is False

    @patch('streamlit.session_state', {'user_role': 'processor'})
    def test_processor_cannot_access_alerts_page(self):
        """Processors should NOT have access to bycatch alerts."""
        from app.views.bycatch_alerts import check_access
        assert check_access() is False


# =============================================================================
# UI DISPLAY TESTS
# =============================================================================

class TestAlertDisplayFormatting:
    """Tests for alert display formatting."""

    def test_format_coordinates(self):
        """Should format coordinates in DMS format for display."""
        from app.views.bycatch_alerts import format_coordinates

        result = format_coordinates(57.5, -152.3)
        # DMS format: "57° 30.0' N, 152° 18.0' W"
        assert '57°' in result  # Degrees
        assert '30' in result   # Minutes (0.5 * 60 = 30)
        assert 'N' in result    # North
        assert '152°' in result # Degrees
        assert 'W' in result    # West

    def test_format_timestamp(self):
        """Should format timestamp in user-friendly format."""
        from app.views.bycatch_alerts import format_timestamp

        result = format_timestamp('2026-01-15T10:30:00Z')
        assert '2026' in result or 'Jan' in result

    def test_get_species_name(self, sample_species):
        """Should get species name from code."""
        from app.views.bycatch_alerts import get_species_name

        # Match actual DB schema: species_name column
        species_list = [
            {'code': 200, 'species_name': 'Halibut'},
            {'code': 110, 'species_name': 'Pacific Cod'},
        ]
        name = get_species_name(200, species_list)
        assert 'Halibut' in name

    def test_get_species_name_unknown(self, sample_species):
        """Should handle unknown species code."""
        from app.views.bycatch_alerts import get_species_name

        species_list = [{'code': 200, 'species_name': 'Halibut'}]
        name = get_species_name(999, species_list)
        assert 'Unknown' in name or '999' in name


# =============================================================================
# EDGE CASES
# =============================================================================

class TestBycatchAlertsEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @patch('app.views.bycatch_alerts.supabase')
    def test_empty_alerts_list(self, mock_supabase):
        """Should handle empty alerts list gracefully."""
        mock_response = MagicMock()
        mock_response.data = []
        # No status filter: .eq(org_id).eq(is_deleted).order().execute()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        result = fetch_alerts('test-org-id')

        assert result == []

    def test_very_long_details_truncated(self):
        """Should truncate very long details in preview."""
        from app.views.bycatch_alerts import truncate_details

        long_text = "A" * 2000
        result = truncate_details(long_text, max_length=500)

        assert len(result) <= 503  # 500 + "..."

    @patch('app.views.bycatch_alerts.supabase')
    def test_handles_null_fields(self, mock_supabase):
        """Should handle null optional fields."""
        mock_response = MagicMock()
        mock_response.data = [{
            'id': 'alert-uuid-1',
            'org_id': 'test-org-id',
            'status': 'pending',
            'details': None,
            'shared_at': None,
            'shared_by': None,
            'shared_recipient_count': None,
            'created_at': '2026-01-15T10:00:00Z',
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        result = fetch_alerts('test-org-id')

        # Should not crash with null fields
        assert len(result) == 1


# =============================================================================
# RESOLVE ALERT TESTS
# =============================================================================

class TestResolveAlert:
    """Tests for resolving shared alerts."""

    @patch('app.views.bycatch_alerts.supabase')
    def test_resolve_updates_status_to_resolved(self, mock_supabase):
        """Should update alert status to resolved."""
        # Mock check query - alert is shared
        mock_check = MagicMock()
        mock_check.data = [{'status': 'shared'}]

        # Mock update query
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1', 'status': 'resolved'}]

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        from app.views.bycatch_alerts import resolve_alert
        success, error = resolve_alert('alert-uuid-1', 'manager-user-1')

        assert success is True
        assert error is None

    @patch('app.views.bycatch_alerts.supabase')
    def test_resolve_records_resolved_by_and_timestamp(self, mock_supabase):
        """Should record who resolved the alert and when."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'shared'}]

        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1'}]

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        from app.views.bycatch_alerts import resolve_alert
        resolve_alert('alert-uuid-1', 'manager-user-1')

        # Verify update was called with resolved_by
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call is not None
        update_data = update_call[0][0]
        assert update_data.get('resolved_by') == 'manager-user-1'
        assert 'resolved_at' in update_data

    @patch('app.views.bycatch_alerts.supabase')
    def test_resolve_returns_error_for_pending_alert(self, mock_supabase):
        """Should not allow resolving pending alerts."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check

        from app.views.bycatch_alerts import resolve_alert
        success, error = resolve_alert('alert-uuid-1', 'manager-user-1')

        assert success is False
        assert 'shared' in error.lower()

    @patch('app.views.bycatch_alerts.supabase')
    def test_resolve_returns_error_for_dismissed_alert(self, mock_supabase):
        """Should not allow resolving dismissed alerts."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'dismissed'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check

        from app.views.bycatch_alerts import resolve_alert
        success, error = resolve_alert('alert-uuid-1', 'manager-user-1')

        assert success is False
        assert 'shared' in error.lower()

    @patch('app.views.bycatch_alerts.supabase')
    def test_resolve_returns_error_for_nonexistent_alert(self, mock_supabase):
        """Should return error for non-existent alert."""
        mock_check = MagicMock()
        mock_check.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check

        from app.views.bycatch_alerts import resolve_alert
        success, error = resolve_alert('nonexistent-uuid', 'manager-user-1')

        assert success is False
        assert 'not found' in error.lower()

    @patch('app.views.bycatch_alerts.supabase')
    def test_resolve_handles_database_error(self, mock_supabase):
        """Should handle database errors gracefully."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        from app.views.bycatch_alerts import resolve_alert
        success, error = resolve_alert('alert-uuid-1', 'manager-user-1')

        assert success is False
        assert 'DB error' in error


# =============================================================================
# HTTP EDGE FUNCTION TESTS
# =============================================================================

class TestShareAlertHTTP:
    """Tests for HTTP call to Edge Function when sharing alerts."""

    @patch('requests.post')
    @patch('app.views.bycatch_alerts.supabase')
    @patch('streamlit.session_state', {'org_id': 'test-org-id'})
    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'})
    def test_share_calls_edge_function_with_correct_url(self, mock_supabase, mock_requests_post):
        """Should call Edge Function with correct URL."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending', 'shared_at': None}]
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1'}]
        mock_contacts = MagicMock()
        mock_contacts.count = 2

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_contacts
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'sent_count': 10}
        mock_requests_post.return_value = mock_response

        from app.views.bycatch_alerts import share_alert
        share_alert('alert-uuid-1', 'manager-user-1')

        mock_requests_post.assert_called_once()
        call_args = mock_requests_post.call_args
        assert 'send-bycatch-alert' in call_args[0][0]

    @patch('requests.post')
    @patch('app.views.bycatch_alerts.supabase')
    @patch('streamlit.session_state', {'org_id': 'test-org-id'})
    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'})
    def test_share_includes_authorization_header(self, mock_supabase, mock_requests_post):
        """Should include Authorization header in HTTP call."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending', 'shared_at': None}]
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1'}]
        mock_contacts = MagicMock()
        mock_contacts.count = 0

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_contacts
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_requests_post.return_value = mock_response

        from app.views.bycatch_alerts import share_alert
        share_alert('alert-uuid-1', 'manager-user-1')

        call_args = mock_requests_post.call_args
        headers = call_args[1].get('headers', {})
        assert 'Authorization' in headers
        assert 'Bearer' in headers['Authorization']

    @patch('requests.post')
    @patch('app.views.bycatch_alerts.supabase')
    @patch('streamlit.session_state', {'org_id': 'test-org-id'})
    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'})
    def test_share_handles_http_timeout(self, mock_supabase, mock_requests_post):
        """Should handle HTTP timeout gracefully."""
        import requests as real_requests

        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending', 'shared_at': None}]
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1'}]
        mock_contacts = MagicMock()
        mock_contacts.count = 0

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_contacts
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        mock_requests_post.side_effect = real_requests.Timeout("Connection timed out")

        from app.views.bycatch_alerts import share_alert
        success, result = share_alert('alert-uuid-1', 'manager-user-1')

        # Alert is still shared even if email times out
        assert success is True
        assert 'email_error' in result

    @patch('requests.post')
    @patch('app.views.bycatch_alerts.supabase')
    @patch('streamlit.session_state', {'org_id': 'test-org-id'})
    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'})
    def test_share_returns_email_error_on_http_failure(self, mock_supabase, mock_requests_post):
        """Should return email_error when HTTP call fails."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending', 'shared_at': None}]
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1'}]
        mock_contacts = MagicMock()
        mock_contacts.count = 0

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_contacts
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {'error': 'Internal server error'}
        mock_requests_post.return_value = mock_response

        from app.views.bycatch_alerts import share_alert
        success, result = share_alert('alert-uuid-1', 'manager-user-1')

        assert success is True  # Alert is shared
        assert 'email_error' in result

    @patch('requests.post')
    @patch('app.views.bycatch_alerts.supabase')
    @patch('streamlit.session_state', {'org_id': 'test-org-id'})
    @patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'})
    def test_share_still_marks_shared_on_email_failure(self, mock_supabase, mock_requests_post):
        """Alert should be marked as shared even if email fails."""
        mock_check = MagicMock()
        mock_check.data = [{'status': 'pending', 'shared_at': None}]
        mock_update = MagicMock()
        mock_update.data = [{'id': 'alert-uuid-1', 'status': 'shared'}]
        mock_contacts = MagicMock()
        mock_contacts.count = 0

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_check
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_contacts
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

        mock_requests_post.side_effect = Exception("Network error")

        from app.views.bycatch_alerts import share_alert
        success, result = share_alert('alert-uuid-1', 'manager-user-1')

        # Alert is shared even if email fails
        assert success is True
        # Update was called with status='shared'
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call is not None


# =============================================================================
# ALASKA TIMEZONE FILTERING TESTS
# =============================================================================

class TestAlaskaTimezoneFiltering:
    """Tests for Alaska timezone date filtering in fetch_alerts."""

    @patch('app.views.bycatch_alerts.supabase')
    def test_filter_converts_utc_to_alaska_time(self, mock_supabase):
        """Should convert UTC timestamps to Alaska time for filtering."""
        # Alert at 2026-01-15T08:00:00Z (UTC) = 2026-01-14T23:00:00 Alaska
        alerts_data = [{
            'id': 'alert-1',
            'org_id': 'test-org',
            'status': 'pending',
            'created_at': '2026-01-15T08:00:00Z',
            'is_deleted': False
        }]

        mock_response = MagicMock()
        mock_response.data = alerts_data
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        # Filter for Jan 15 Alaska time - should NOT include alert that's Jan 14 in AK
        result = fetch_alerts('test-org', date_from=date(2026, 1, 15))

        # Alert is Jan 14 in Alaska, so filtering from Jan 15 should exclude it
        assert len(result) == 0

    @patch('app.views.bycatch_alerts.supabase')
    def test_filter_by_date_uses_alaska_date_not_utc(self, mock_supabase):
        """Should use Alaska date, not UTC date, for filtering."""
        # Alert at 2026-01-15T20:00:00Z (UTC) = 2026-01-15T11:00:00 Alaska
        alerts_data = [{
            'id': 'alert-1',
            'org_id': 'test-org',
            'status': 'pending',
            'created_at': '2026-01-15T20:00:00Z',
            'is_deleted': False
        }]

        mock_response = MagicMock()
        mock_response.data = alerts_data
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        # Filter for Jan 15 Alaska time - should include this alert
        result = fetch_alerts('test-org', date_from=date(2026, 1, 15), date_to=date(2026, 1, 15))

        assert len(result) == 1

    @patch('app.views.bycatch_alerts.supabase')
    def test_alert_at_midnight_utc_filters_to_previous_alaska_date(self, mock_supabase):
        """Alert at midnight UTC should be on previous day in Alaska."""
        # 2026-01-15T00:00:00Z (UTC midnight) = 2026-01-14T15:00:00 Alaska (previous day)
        alerts_data = [{
            'id': 'alert-1',
            'org_id': 'test-org',
            'status': 'pending',
            'created_at': '2026-01-15T00:00:00Z',
            'is_deleted': False
        }]

        mock_response = MagicMock()
        mock_response.data = alerts_data
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        # Filter for Jan 14 Alaska time - should include this alert
        result = fetch_alerts('test-org', date_from=date(2026, 1, 14), date_to=date(2026, 1, 14))

        assert len(result) == 1

    @patch('app.views.bycatch_alerts.supabase')
    def test_filter_handles_daylight_saving_time(self, mock_supabase):
        """Should handle DST transition correctly (Alaska is AKDT in summer)."""
        # July 15, 2026: Alaska is UTC-8 (AKDT)
        # 2026-07-15T07:00:00Z (UTC) = 2026-07-14T23:00:00 Alaska (previous day)
        alerts_data = [{
            'id': 'alert-1',
            'org_id': 'test-org',
            'status': 'pending',
            'created_at': '2026-07-15T07:00:00Z',
            'is_deleted': False
        }]

        mock_response = MagicMock()
        mock_response.data = alerts_data
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        from app.views.bycatch_alerts import fetch_alerts
        # Filter for July 15 Alaska time - should NOT include (it's July 14 in Alaska during DST)
        result = fetch_alerts('test-org', date_from=date(2026, 7, 15))

        assert len(result) == 0
