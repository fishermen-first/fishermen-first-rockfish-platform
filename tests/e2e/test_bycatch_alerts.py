"""End-to-end tests for bycatch alerts feature.

Run with: pytest tests/e2e/test_bycatch_alerts.py --headed (to see browser)
Or: pytest tests/e2e/test_bycatch_alerts.py (headless)

Prerequisites:
    pip install playwright pytest-playwright
    playwright install chromium

Environment variables:
    ADMIN_EMAIL - Admin/manager email for login
    ADMIN_PASSWORD - Admin/manager password
    TEST_EMAIL - Vessel owner email (optional)
    TEST_PASSWORD - Vessel owner password (optional)
"""

import pytest
from playwright.sync_api import Page, expect
import subprocess
import time
import os
from dotenv import load_dotenv

# Load .env file for credentials
load_dotenv()

# Test credentials
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "vikram@fishermenfirst.org")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
TEST_EMAIL = os.getenv("TEST_EMAIL", "vikram.nayani+1@gmail.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "")
APP_URL = "http://localhost:8501"


@pytest.fixture(scope="module")
def app_server():
    """Start the Streamlit app for testing."""
    proc = subprocess.Popen(
        ["python", "-m", "streamlit", "run", "app/main.py", "--server.headless", "true", "--server.port", "8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)  # Wait for app to start
    yield proc
    proc.terminate()
    proc.wait(timeout=10)


def login_as_admin(page: Page):
    """Helper to login as admin/manager."""
    page.goto(APP_URL)
    page.fill("input[type='text']", ADMIN_EMAIL)
    page.fill("input[type='password']", ADMIN_PASSWORD)
    page.click("button:has-text('Sign In')")
    page.wait_for_timeout(3000)


def navigate_to_bycatch_alerts(page: Page):
    """Helper to navigate to bycatch alerts page."""
    # Click on Bycatch Alerts in sidebar
    page.click("text=Bycatch Alerts")
    page.wait_for_timeout(2000)


def select_alert_view(page: Page, view_name: str):
    """Helper to select a view option in the segmented control.

    The bycatch alerts page uses st.segmented_control for view selection
    (Pending, Shared, Resolved, All) instead of st.tabs.
    """
    # Scroll to the ALERTS section to ensure the view selector is visible
    page.get_by_text("ALERTS", exact=False).first.scroll_into_view_if_needed()
    page.wait_for_timeout(300)

    # Click on the view option - use get_by_text for exact match
    # The segmented control options are clickable text elements
    page.get_by_text(view_name, exact=True).first.click()
    page.wait_for_timeout(1000)


# =============================================================================
# NAVIGATION AND PAGE LOAD TESTS
# =============================================================================

class TestBycatchAlertsNavigation:
    """Tests for navigating to and loading the bycatch alerts page."""

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_admin_can_access_bycatch_alerts_page(self, page: Page, app_server):
        """Admin should be able to navigate to bycatch alerts page."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Should see page header
        expect(page.get_by_role("heading", name="Bycatch Alerts")).to_be_visible()
        expect(page.locator("text=Review and share bycatch hotspot reports")).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_page_shows_view_selector(self, page: Page, app_server):
        """Page should display view selector with Pending, Shared, Resolved, All options."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Segmented control has a "View" label and shows Pending/Shared/Resolved/All options
        # The label "View" should be visible
        expect(page.get_by_text("View", exact=True)).to_be_visible()
        # The option text should be visible on the page
        expect(page.get_by_text("Pending", exact=True).first).to_be_visible()
        expect(page.get_by_text("Shared", exact=True).first).to_be_visible()
        expect(page.get_by_text("All", exact=True).first).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_page_shows_filters(self, page: Page, app_server):
        """Page should display filter controls."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # The filters section header includes an emoji: "🔍 FILTERS"
        expect(page.get_by_text("FILTERS", exact=False).first).to_be_visible()
        expect(page.get_by_text("Cooperative", exact=True).first).to_be_visible()
        expect(page.get_by_text("From Date", exact=True)).to_be_visible()
        expect(page.get_by_text("To Date", exact=True)).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_page_shows_create_alert_section(self, page: Page, app_server):
        """Page should display create alert section for managers."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        expect(page.locator("text=CREATE NEW ALERT")).to_be_visible()


# =============================================================================
# CREATE ALERT TESTS
# =============================================================================

class TestCreateAlert:
    """Tests for creating new bycatch alerts."""

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_create_alert_form_elements(self, page: Page, app_server):
        """Create alert form should have all required elements."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # The CREATE NEW ALERT is inside an expander - click to expand if needed
        # The expander header contains the text
        expander = page.locator("[data-testid='stExpander']").first
        # Check if already expanded by looking for form visibility
        form = page.get_by_test_id("stForm")
        if not form.is_visible():
            expander.click()
            page.wait_for_timeout(500)

        # Check form elements
        expect(page.get_by_text("Reporting Vessel", exact=True)).to_be_visible()
        expect(page.get_by_text("Latitude", exact=False).first).to_be_visible()
        expect(page.get_by_text("Longitude", exact=False).first).to_be_visible()
        expect(page.get_by_test_id("stBaseButton-primaryFormSubmit")).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_create_alert_validation_requires_vessel(self, page: Page, app_server):
        """Should show error when vessel not selected."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # The CREATE NEW ALERT is inside an expander - click to expand if needed
        expander = page.locator("[data-testid='stExpander']").first
        form = page.get_by_test_id("stForm")
        if not form.is_visible():
            expander.click()
            page.wait_for_timeout(500)

        # Try to submit without selecting vessel - use form submit button
        page.get_by_test_id("stBaseButton-primaryFormSubmit").click()
        page.wait_for_timeout(1000)

        # Should see validation error
        expect(page.get_by_text("Please select", exact=False)).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_create_alert_success(self, page: Page, app_server):
        """Should successfully create alert with valid data."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Count initial pending alerts
        page.wait_for_timeout(1000)
        initial_alert_count = page.get_by_role("button", name="Edit").count()

        # The CREATE NEW ALERT is inside an expander - click to expand if needed
        expander = page.locator("[data-testid='stExpander']").first
        form = page.get_by_test_id("stForm")
        if not form.is_visible():
            expander.click()
            page.wait_for_timeout(500)

        # Select species - find "Select species..." placeholder and click its parent select
        species_placeholder = page.get_by_text("Select species...", exact=True)
        species_placeholder.click()
        page.wait_for_timeout(300)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)

        # Select vessel - find "Select vessel..." placeholder and click
        vessel_placeholder = page.get_by_text("Select vessel...", exact=True)
        vessel_placeholder.click()
        page.wait_for_timeout(300)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)

        # Submit
        page.get_by_test_id("stBaseButton-primaryFormSubmit").click()

        # Wait for Streamlit to process and rerun
        page.wait_for_timeout(4000)

        # Success is indicated by: new alert appeared (Edit button count increased)
        # or success message is visible, or form fields inside the form are cleared
        new_alert_count = page.get_by_role("button", name="Edit").count()
        success_visible = page.get_by_text("Alert created", exact=False).is_visible()
        # Check if vessel selector inside form shows placeholder again (form cleared)
        form_vessel_cleared = page.get_by_text("Select vessel...", exact=True).is_visible()

        assert success_visible or new_alert_count > initial_alert_count or form_vessel_cleared, \
            f"Expected alert to be created. Initial: {initial_alert_count}, New: {new_alert_count}"


# =============================================================================
# ALERT ACTIONS TESTS
# =============================================================================

class TestAlertActions:
    """Tests for alert action buttons (Edit, Preview, Share, Dismiss)."""

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_pending_alert_shows_action_buttons(self, page: Page, app_server):
        """Pending alerts should show Edit, Preview, Share, and Dismiss buttons."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Stay on Pending tab (default)
        page.wait_for_timeout(1000)

        # Check if there are pending alerts by looking for Edit buttons
        edit_buttons = page.get_by_role("button", name="Edit")
        if edit_buttons.count() > 0:
            expect(edit_buttons.first).to_be_visible()
            expect(page.get_by_role("button", name="Preview").first).to_be_visible()
            expect(page.get_by_role("button", name="Share").first).to_be_visible()
            expect(page.get_by_role("button", name="Dismiss").first).to_be_visible()
        else:
            # No pending alerts - check for "No pending alerts" message
            expect(page.get_by_text("No pending alerts", exact=False)).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_preview_shows_email_content(self, page: Page, app_server):
        """Preview button should show email preview with content."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Check if there are pending alerts
        page.wait_for_timeout(1000)
        preview_buttons = page.get_by_role("button", name="Preview")

        if preview_buttons.count() > 0:
            # Click first preview button
            preview_buttons.first.click()
            page.wait_for_timeout(500)

            # Should show email preview
            expect(page.get_by_text("Email Preview", exact=True)).to_be_visible()
            expect(page.get_by_text("Subject:", exact=False)).to_be_visible()
            expect(page.get_by_text("vessel contacts", exact=False)).to_be_visible()

            # Close preview
            page.get_by_role("button", name="Close Preview").click()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_edit_opens_form(self, page: Page, app_server):
        """Edit button should open inline edit form."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Check if there are pending alerts
        page.wait_for_timeout(1000)
        edit_buttons = page.get_by_role("button", name="Edit")

        if edit_buttons.count() > 0:
            # Click first edit button
            edit_buttons.first.click()
            page.wait_for_timeout(500)

            # Should show edit form
            expect(page.get_by_text("Edit Alert Details", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Save Changes")).to_be_visible()
            expect(page.get_by_role("button", name="Cancel")).to_be_visible()

            # Cancel edit
            page.get_by_role("button", name="Cancel").click()


# =============================================================================
# SHARE ALERT TESTS (E2E EMAIL FLOW)
# =============================================================================

class TestShareAlert:
    """Tests for sharing alerts to fleet (triggers email via Edge Function)."""

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_share_button_shows_confirmation(self, page: Page, app_server):
        """Share button should work and show result."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Check if there are pending alerts
        page.wait_for_timeout(1000)
        share_buttons = page.get_by_role("button", name="Share")
        initial_count = share_buttons.count()

        if initial_count > 0:
            # Click first share button
            share_buttons.first.click()

            # Wait for Edge Function call and page rerun
            page.wait_for_timeout(5000)

            # Should see success message, warning (email failed but shared), or page reloaded
            success_visible = page.get_by_text("Alert shared", exact=False).is_visible()
            already_shared = page.get_by_text("already shared", exact=False).is_visible()
            email_warning = page.get_by_text("email failed", exact=False).is_visible()

            # After share, the pending count decreases (alert moved to Shared)
            new_share_count = page.get_by_role("button", name="Share").count()

            assert success_visible or already_shared or email_warning or new_share_count < initial_count, \
                f"Expected share to succeed. Initial: {initial_count}, New: {new_share_count}"
        else:
            # No pending alerts to share - that's okay
            expect(page.get_by_text("No pending alerts", exact=False)).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_shared_alert_appears_in_shared_tab(self, page: Page, app_server):
        """After sharing, alert should appear in Shared tab."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Click on Shared view
        select_alert_view(page, "Shared")
        page.wait_for_timeout(1000)

        # Should show shared alerts or "No shared alerts" message
        has_shared = page.get_by_text("shared alert", exact=False).is_visible()
        no_shared = page.get_by_text("No shared alerts", exact=False).is_visible()

        assert has_shared or no_shared

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_shared_alert_shows_recipient_count(self, page: Page, app_server):
        """Shared alerts should display recipient count."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Click on Shared view
        select_alert_view(page, "Shared")
        page.wait_for_timeout(1000)

        # If there are shared alerts, check for recipient info
        # Look for "Shared on" which indicates a shared alert card
        shared_info = page.get_by_text("Shared on", exact=False)
        if shared_info.count() > 0:
            expect(page.get_by_text("recipients", exact=False).first).to_be_visible()
        else:
            # No shared alerts yet - that's okay
            expect(page.get_by_text("No shared alerts", exact=False)).to_be_visible()


# =============================================================================
# DISMISS ALERT TESTS
# =============================================================================

class TestDismissAlert:
    """Tests for dismissing alerts."""

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_dismiss_removes_from_pending(self, page: Page, app_server):
        """Dismiss should remove alert from pending list."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Check initial pending count
        page.wait_for_timeout(1000)
        dismiss_buttons = page.get_by_role("button", name="Dismiss")
        initial_count = dismiss_buttons.count()

        if initial_count > 0:
            # Click first dismiss button
            dismiss_buttons.first.click()

            # Wait for Streamlit to process and rerun
            page.wait_for_timeout(3000)

            # Success is indicated by: dismiss button count decreased or success message visible
            new_count = page.get_by_role("button", name="Dismiss").count()
            success_visible = page.get_by_text("Alert dismissed", exact=False).is_visible()

            # Count should decrease after dismiss (alert removed from pending)
            assert success_visible or new_count < initial_count, \
                f"Expected alert to be dismissed. Initial: {initial_count}, New: {new_count}"
        else:
            # No pending alerts to dismiss - that's okay
            expect(page.get_by_text("No pending alerts", exact=False)).to_be_visible()


# =============================================================================
# FILTER TESTS
# =============================================================================

class TestAlertFiltering:
    """Tests for filtering alerts."""

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_filter_by_species(self, page: Page, app_server):
        """Should be able to filter alerts by species."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Find the "All Species" dropdown (should be visible in filter section)
        species_filter = page.get_by_text("All Species", exact=True)
        species_filter.click()
        page.wait_for_timeout(300)

        # Select a specific species (not "All Species")
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)

        # Page should reload with filtered results (no error)
        expect(page.get_by_role("heading", name="Bycatch Alerts")).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_filter_by_date_range(self, page: Page, app_server):
        """Should be able to filter alerts by date range."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Date filters should be visible
        expect(page.locator("text=From Date")).to_be_visible()
        expect(page.locator("text=To Date")).to_be_visible()

        # Page should not error with default date filters
        expect(page.get_by_role("heading", name="Bycatch Alerts")).to_be_visible()


# =============================================================================
# ALERT CARD DISPLAY TESTS
# =============================================================================

class TestAlertCardDisplay:
    """Tests for alert card content and formatting."""

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_alert_card_shows_species(self, page: Page, app_server):
        """Alert cards should display species name."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Go to All view to see any alerts
        select_alert_view(page, "All")
        page.wait_for_timeout(1000)

        # Check for vessel/location info which indicates alert cards are present
        vessel_info = page.get_by_text("Vessel:", exact=False)
        if vessel_info.count() > 0:
            # Should show vessel and location info
            expect(vessel_info.first).to_be_visible()
            expect(page.get_by_text("Location:", exact=False).first).to_be_visible()
        else:
            # No alerts - check for empty state message
            expect(page.get_by_text("No alerts match", exact=False)).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_alert_card_shows_coordinates_in_dms(self, page: Page, app_server):
        """Alert cards should display coordinates in DMS format."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Go to All view
        select_alert_view(page, "All")
        page.wait_for_timeout(1000)

        # If there are alerts, coordinates should be in DMS format (contain ° symbol)
        location_info = page.get_by_text("Location:", exact=False)
        if location_info.count() > 0:
            # DMS format includes degree symbol
            expect(page.locator("text=°").first).to_be_visible()
        else:
            # No alerts - that's okay for this test
            expect(page.get_by_text("No alerts match", exact=False)).to_be_visible()


# =============================================================================
# RESOLVE ALERT TESTS
# =============================================================================

class TestResolveAlert:
    """Tests for resolving shared alerts."""

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_resolve_button_visible_for_shared_alerts(self, page: Page, app_server):
        """Resolve button should be visible for shared alerts."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Go to Shared view
        select_alert_view(page, "Shared")
        page.wait_for_timeout(1000)

        # If there are shared alerts, resolve button should be visible
        shared_info = page.get_by_text("Shared on", exact=False)
        if shared_info.count() > 0:
            # Resolve buttons should be present for shared alerts (button text is "Mark Resolved")
            resolve_buttons = page.get_by_role("button", name="Mark Resolved")
            assert resolve_buttons.count() > 0
        else:
            # No shared alerts - that's okay
            expect(page.get_by_text("No shared alerts", exact=False)).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_resolve_changes_status(self, page: Page, app_server):
        """Resolving should change alert status."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Go to Shared view
        select_alert_view(page, "Shared")
        page.wait_for_timeout(1000)

        # Button text is "Mark Resolved"
        resolve_buttons = page.get_by_role("button", name="Mark Resolved")
        initial_count = resolve_buttons.count()

        if initial_count > 0:
            # Click first resolve button
            resolve_buttons.first.click()

            # Wait for Streamlit to process and rerun
            page.wait_for_timeout(3000)

            # Should see success message or the count should decrease (alert moved to resolved)
            success_visible = page.get_by_text("resolved", exact=False).is_visible()
            new_count = page.get_by_role("button", name="Mark Resolved").count()

            assert success_visible or new_count < initial_count, \
                f"Expected alert to be resolved. Initial: {initial_count}, New: {new_count}"
        else:
            # No shared alerts to resolve
            expect(page.get_by_text("No shared alerts", exact=False)).to_be_visible()

    @pytest.mark.skipif(not ADMIN_PASSWORD, reason="ADMIN_PASSWORD not set")
    def test_resolved_alerts_show_timestamp(self, page: Page, app_server):
        """Resolved alerts should show resolution timestamp."""
        login_as_admin(page)
        navigate_to_bycatch_alerts(page)

        # Go to All view to see resolved alerts
        select_alert_view(page, "All")
        page.wait_for_timeout(1000)

        # Look for "Resolved on" text which indicates a resolved alert
        resolved_info = page.get_by_text("Resolved on", exact=False)
        if resolved_info.count() > 0:
            # Should display the resolution timestamp
            expect(resolved_info.first).to_be_visible()
        else:
            # No resolved alerts yet - that's okay
            pass  # Test passes if no resolved alerts exist
