"""End-to-end tests using Playwright.

Run with: pytest tests/e2e/ --headed (to see browser)
Or: pytest tests/e2e/ (headless)

Prerequisites:
    pip install playwright pytest-playwright
    playwright install chromium
"""

import pytest
from playwright.sync_api import Page, expect
import subprocess
import time
import os

# Test credentials - use test account
TEST_EMAIL = os.getenv("TEST_EMAIL", "vikram.nayani+1@gmail.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "")  # Set via environment variable
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


class TestLoginPage:
    """Tests for the login page."""

    def test_login_page_loads(self, page: Page, app_server):
        """Login page should display title and form."""
        page.goto(APP_URL)
        expect(page.locator("text=Fishermen First")).to_be_visible()
        expect(page.locator("input[type='text']").first).to_be_visible()  # Email input

    def test_login_shows_error_for_empty_fields(self, page: Page, app_server):
        """Should show error when submitting empty form."""
        page.goto(APP_URL)
        page.click("button:has-text('Sign In')")
        expect(page.locator("text=Please enter both email and password")).to_be_visible()

    @pytest.mark.skipif(not TEST_PASSWORD, reason="TEST_PASSWORD not set")
    def test_login_invalid_credentials(self, page: Page, app_server):
        """Should show error for invalid credentials."""
        page.goto(APP_URL)
        page.fill("input[type='text']", "invalid@example.com")
        page.fill("input[type='password']", "wrongpassword")
        page.click("button:has-text('Sign In')")
        page.wait_for_timeout(2000)
        expect(page.locator("text=Invalid email or password")).to_be_visible()


class TestVesselOwnerView:
    """Tests for vessel owner view."""

    @pytest.mark.skipif(not TEST_PASSWORD, reason="TEST_PASSWORD not set")
    def test_vessel_owner_login_shows_my_vessel(self, page: Page, app_server):
        """Vessel owner should see My Vessel page after login."""
        page.goto(APP_URL)

        # Login
        page.fill("input[type='text']", TEST_EMAIL)
        page.fill("input[type='password']", TEST_PASSWORD)
        page.click("button:has-text('Sign In')")

        # Wait for redirect
        page.wait_for_timeout(3000)

        # Should see vessel owner view (use heading to be specific)
        expect(page.get_by_role("heading", name="My Vessel")).to_be_visible()
        expect(page.locator("text=QUOTA REMAINING")).to_be_visible()

    @pytest.mark.skipif(not TEST_PASSWORD, reason="TEST_PASSWORD not set")
    def test_vessel_owner_sees_quota_cards(self, page: Page, app_server):
        """Vessel owner should see quota cards for all species."""
        page.goto(APP_URL)

        # Login
        page.fill("input[type='text']", TEST_EMAIL)
        page.fill("input[type='password']", TEST_PASSWORD)
        page.click("button:has-text('Sign In')")
        page.wait_for_timeout(3000)

        # Check for species cards
        expect(page.locator("text=POP")).to_be_visible()
        expect(page.locator("text=NR")).to_be_visible()
        expect(page.locator("text=Dusky")).to_be_visible()

    @pytest.mark.skipif(not TEST_PASSWORD, reason="TEST_PASSWORD not set")
    def test_vessel_owner_can_logout(self, page: Page, app_server):
        """Vessel owner should be able to log out."""
        page.goto(APP_URL)

        # Login
        page.fill("input[type='text']", TEST_EMAIL)
        page.fill("input[type='password']", TEST_PASSWORD)
        page.click("button:has-text('Sign In')")
        page.wait_for_timeout(3000)

        # Logout
        page.click("button:has-text('Log Out')")
        page.wait_for_timeout(2000)

        # Should see login form again
        expect(page.locator("text=Fishermen First")).to_be_visible()
        expect(page.locator("text=Sign In")).to_be_visible()
