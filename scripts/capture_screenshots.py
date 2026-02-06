"""
Automated screenshot capture for marketing materials.

This script:
1. Launches the demo Streamlit app as a subprocess
2. Uses Playwright to navigate to each page and capture screenshots
3. Saves screenshots to marketing/screenshots/

Usage:
    python scripts/capture_screenshots.py

Requirements:
    pip install playwright
    playwright install chromium
"""

import subprocess
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

# Configuration
PORT = 8502
BASE_URL = f"http://localhost:{PORT}"
OUTPUT_DIR = Path(__file__).parent.parent / "marketing" / "screenshots"
VIEWPORT = {"width": 1920, "height": 1080}

# Pages to capture
PAGES = [
    {"name": "dashboard", "nav_text": "Dashboard"},
    {"name": "transfers", "nav_text": "Transfers"},
    {"name": "vessel-owner", "nav_text": "Vessel Owner"},
]


def wait_for_streamlit(url: str, timeout: int = 60) -> bool:
    """Wait for Streamlit app to be ready."""
    print(f"Waiting for Streamlit at {url}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print("Streamlit is ready!")
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def capture_screenshots():
    """Launch Streamlit and capture screenshots of each page."""
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Launch Streamlit subprocess
    streamlit_script = Path(__file__).parent / "generate_marketing_screenshots.py"
    print(f"Starting Streamlit on port {PORT}...")

    process = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            str(streamlit_script),
            "--server.port", str(PORT),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for app to be ready
        if not wait_for_streamlit(BASE_URL):
            print("ERROR: Streamlit failed to start within timeout")
            return False

        # Give it a moment to fully initialize
        time.sleep(2)

        # Launch Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport=VIEWPORT)
            page = context.new_page()

            for page_config in PAGES:
                name = page_config["name"]
                nav_text = page_config["nav_text"]
                output_path = OUTPUT_DIR / f"{name}.png"

                print(f"Capturing {name}...")

                # Navigate to base URL
                page.goto(BASE_URL)

                # Wait for page to load
                page.wait_for_load_state("networkidle")
                time.sleep(1)

                # Click the navigation radio button
                # Streamlit radio buttons have the label text visible
                try:
                    page.locator(f"label:has-text('{nav_text}')").click()
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)  # Allow charts/tables to render
                except Exception as e:
                    print(f"  Warning: Could not click nav '{nav_text}': {e}")
                    # Try alternative selector for radio option
                    try:
                        page.locator(f"text={nav_text}").first.click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(2)
                    except Exception:
                        pass

                # Capture screenshot
                page.screenshot(path=str(output_path), full_page=False)
                print(f"  Saved: {output_path}")

            browser.close()

        print(f"\nAll screenshots saved to: {OUTPUT_DIR}")
        return True

    finally:
        # Clean up Streamlit process
        print("Shutting down Streamlit...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def main():
    """Main entry point."""
    print("=" * 60)
    print("Marketing Screenshot Capture")
    print("=" * 60)

    success = capture_screenshots()

    if success:
        print("\nScreenshot capture complete!")
        print(f"\nOutput files:")
        for page_config in PAGES:
            path = OUTPUT_DIR / f"{page_config['name']}.png"
            if path.exists():
                size = path.stat().st_size / 1024
                print(f"  - {path.name} ({size:.1f} KB)")
    else:
        print("\nScreenshot capture failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
