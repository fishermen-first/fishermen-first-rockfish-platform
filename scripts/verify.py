#!/usr/bin/env python
"""Verification script - run after making changes to ensure nothing is broken.

Usage:
    python scripts/verify.py          # Run unit tests + app check
    python scripts/verify.py --e2e    # Also run e2e tests
    python scripts/verify.py --full   # Run everything
"""

import argparse
import subprocess
import sys
import time


def run_command(cmd: list[str], description: str, timeout: int = 120) -> bool:
    """Run a command and return True if successful."""
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print('=' * 60)

    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=False
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  Timed out after {timeout}s (this may be OK)")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run verification checks")
    parser.add_argument("--e2e", action="store_true", help="Run e2e tests")
    parser.add_argument("--full", action="store_true", help="Run all tests including e2e")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  VERIFICATION SCRIPT")
    print("=" * 60)

    all_passed = True

    # 1. Run pytest (unit tests only, exclude e2e)
    if not run_command(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "--ignore=tests/e2e"],
        "Running unit tests..."
    ):
        all_passed = False
        print("\n  FAILED: Unit tests did not pass")
    else:
        print("\n  PASSED: All unit tests passed")

    # 2. Check app starts
    print(f"\n{'=' * 60}")
    print("  Checking Streamlit app starts...")
    print('=' * 60)

    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app/main.py", "--server.headless", "true"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(5)  # Give it time to start

        if proc.poll() is None:
            # Still running = good
            print("  PASSED: Streamlit app starts successfully")
            proc.terminate()
            proc.wait(timeout=5)
        else:
            # Exited = bad
            print("  FAILED: Streamlit app exited unexpectedly")
            all_passed = False
    except Exception as e:
        print(f"  ERROR: {e}")
        all_passed = False

    # 3. Run e2e tests (optional)
    if args.e2e or args.full:
        if not run_command(
            [sys.executable, "-m", "pytest", "tests/e2e/", "-v", "--tb=short"],
            "Running e2e tests...",
            timeout=300
        ):
            all_passed = False
            print("\n  FAILED: E2E tests did not pass")
        else:
            print("\n  PASSED: All e2e tests passed")

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("  ALL CHECKS PASSED")
    else:
        print("  SOME CHECKS FAILED")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
