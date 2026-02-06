# Testing Patterns

**Analysis Date:** 2026-01-28

## Test Framework

**Runner:**
- pytest 7.0.0+
- Config: `pytest.ini`

**Assertion Library:**
- Standard pytest assertions and unittest.mock

**Run Commands:**
```bash
pytest tests/ --ignore=tests/e2e -v              # Run all unit tests (~4 seconds)
pytest tests/ -v                                   # Run all tests including e2e (~80 seconds)
pytest tests/test_transfers.py -v                 # Run specific test file
pytest tests/ --ignore=tests/e2e --cov=app --cov-report=html  # With coverage report
```

## Test File Organization

**Location:**
- Unit/integration tests colocated in `tests/` directory, parallel to source
- E2E tests in `tests/e2e/` subdirectory
- Shared fixtures in `tests/conftest.py`

**Naming:**
- Test modules: `test_<feature>.py` (e.g., `test_auth.py`, `test_transfers.py`, `test_quota_tracking.py`)
- Test classes: `Test<Feature>` (e.g., `TestLogin`, `TestGetQuotaRemaining`)
- Test functions: `test_<scenario_description>` (e.g., `test_successful_login`, `test_returns_remaining_lbs_when_found`)

**Structure:**
```
tests/
├── conftest.py                  # Shared fixtures and autouse cache clearing
├── test_auth.py                 # Authentication tests (47 tests)
├── test_dashboard.py            # Dashboard logic tests (27 tests)
├── test_quota_tracking.py       # Integration tests: DB quota calculations (26 tests)
├── test_transfers.py            # Transfer business logic tests (83 tests)
├── test_upload.py               # CSV upload/parsing tests (35 tests)
├── test_vessel_owner.py         # Vessel owner view tests (28 tests)
├── test_bycatch_alerts.py       # Bycatch alert tests
├── test_bycatch_hauls.py        # Bycatch haul tests
└── e2e/
    ├── test_app.py              # Browser-based Playwright tests (10 tests)
    ├── test_bycatch_alerts.py   # E2E bycatch alert tests
    └── test_bycatch_hauls.py    # E2E haul tests
```

## Test Structure

**Suite Organization:**
```python
"""Tests for [feature]."""

import pytest
from unittest.mock import MagicMock, patch

class TestLoginSuccess:
    """Group related test cases in descriptive class."""

    @patch('app.auth.supabase')
    @patch('app.auth.st')
    def test_successful_login(self, mock_st, mock_supabase):
        """Test description as docstring (one sentence, testing behavior not implementation)."""
        # Setup
        mock_response = MagicMock()
        mock_response.user = MagicMock(id='user-123')
        mock_supabase.auth.sign_in_with_password.return_value = mock_response
        mock_st.session_state = {}

        # Execute
        from app.auth import login
        success, message = login('test@example.com', 'password123')

        # Assert
        assert success is True
        assert message == "Login successful"
```

**Patterns:**
- Arrange-Act-Assert (AAA) pattern with setup, execution, assertions separated by comments
- Docstrings document what the test verifies (behavior), not the test mechanics
- Each test is focused and tests one behavior
- Use `@patch()` decorators to mock external dependencies (Supabase, Streamlit)
- Mock objects created with `MagicMock()` for complex objects like responses

## Mocking

**Framework:** unittest.mock (standard library)

**Patterns:**
```python
# Mock Supabase responses (common pattern in transfers tests)
@patch('app.views.transfers.supabase')
def test_returns_remaining_lbs_when_found(self, mock_supabase):
    mock_response = MagicMock()
    mock_response.data = [{'remaining_lbs': 5000.0}]
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

    from app.views.transfers import get_quota_remaining
    result = get_quota_remaining('LLN111111111', 141, 2026)

    assert result == 5000.0

# Mock Streamlit session state (auth tests)
class MockSessionState(dict):
    """Mock session state supporting dict and attribute access."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

mock_st.session_state = MockSessionState({'authenticated': True, 'user': MagicMock()})

# Assert mock was called correctly
mock_supabase.auth.sign_in_with_password.assert_called_once()
mock_st.error.assert_called_once()
mock_refresh.assert_not_called()
```

**What to Mock:**
- External services: Supabase client (`supabase.table()`, `supabase.auth`)
- Streamlit globals: `st.session_state`, `st.error()`, `st.warning()`
- External APIs in views (though most are Supabase)

**What NOT to Mock:**
- Internal utility functions (format_lbs, get_risk_level) - test as-is
- Data structures (DataFrames, dicts) - use real objects
- Pure functions - call directly without mocks

## Fixtures and Factories

**Test Data:**
```python
# From conftest.py - autouse fixture that clears caches
@pytest.fixture(autouse=True)
def clear_streamlit_caches():
    """Clear all Streamlit caches before each test to prevent data leakage."""
    from app.views.dashboard import _fetch_quota_remaining
    from app.views.transfers import _fetch_transfer_history

    _fetch_quota_remaining.clear()
    _fetch_transfer_history.clear()

    yield

    # Clear again after test
    _fetch_quota_remaining.clear()
    _fetch_transfer_history.clear()

# Integration test fixtures (test_quota_tracking.py)
@pytest.fixture(scope="module")
def supabase():
    """Create Supabase client for tests using service role key."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        pytest.skip("SUPABASE credentials required")

    return create_client(url, key)

@pytest.fixture(scope="module")
def test_org(supabase):
    """Create test organization."""
    TEST_ORG_ID = "00000000-0000-0000-0000-000000000099"
    result = supabase.table("organizations").select("id").eq("id", TEST_ORG_ID).execute()

    if not result.data:
        supabase.table("organizations").insert({
            "id": TEST_ORG_ID,
            "name": "Test Organization (DO NOT DELETE)",
            "slug": "test-org"
        }).execute()

    yield TEST_ORG_ID

@pytest.fixture(autouse=True)
def cleanup_test_data(supabase, test_org):
    """Clean up test data before and after each test."""
    def clean():
        supabase.table("vessel_allocations").delete().eq("org_id", TEST_ORG_ID).execute()
        supabase.table("quota_transfers").delete().eq("org_id", TEST_ORG_ID).execute()
        supabase.table("harvests").delete().eq("org_id", TEST_ORG_ID).execute()

    clean()  # Before test
    yield
    clean()  # After test
```

**Location:**
- Shared fixtures in `tests/conftest.py`
- Module-specific fixtures at top of test file or conftest
- Test data constants defined in test classes or module top

## Coverage

**Requirements:**
- No explicit coverage enforcement (no codecov config)
- 270 total tests across unit, integration, and e2e
- Coverage reports available: `pytest tests/ --cov=app --cov-report=html`

**View Coverage:**
```bash
open htmlcov/index.html  # View HTML report
```

## Test Types

**Unit Tests:**
- Scope: Individual functions with mocked dependencies
- Approach: Fast, isolated, mock all external calls
- Location: `tests/test_*.py` (except `test_quota_tracking.py`)
- Examples: `test_auth.py` (47 tests for auth functions), `test_transfers.py` (83 tests for transfer logic)
- Run time: ~4 seconds

**Integration Tests:**
- Scope: Database operations and quota calculations
- Approach: Use real Supabase connection with test org/year
- Location: `tests/test_quota_tracking.py` (26 tests)
- Requirements: `SUPABASE_SERVICE_ROLE_KEY` in `.env`
- Test data: Uses dedicated test org `TEST_ORG_ID = "00000000-0000-0000-0000-000000000099"` and far-future year `TEST_YEAR = 2099` to avoid conflicts
- Run time: ~20 seconds (depends on network)
- Verifies: Quota math, transfers, harvests, soft deletes, species isolation, year isolation

**E2E Tests:**
- Scope: Full Streamlit application workflows via browser
- Approach: Playwright browser automation
- Location: `tests/e2e/` (10+ tests)
- Tools: Playwright + pytest-playwright
- Requirements: `TEST_PASSWORD` and `ADMIN_PASSWORD` environment variables, running Streamlit app
- Startup: `subprocess.Popen(["python", "-m", "streamlit", "run", "app/main.py", ...])` in `@pytest.fixture(scope="module")`
- Run time: ~80 seconds per test suite
- Skipped if credentials not provided: `@pytest.mark.skipif(not TEST_PASSWORD, reason="TEST_PASSWORD not set")`

## Common Patterns

**Async Testing:**
- No async functions in codebase; all Supabase calls are synchronous
- Playwright tests handle async browser actions with `.wait_for_timeout(2000)` for waits

**Error Testing:**
```python
# Test exception handling
@patch('app.views.transfers.supabase')
def test_handles_database_error(self, mock_supabase):
    """Should return 0 and show error on database exception."""
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception("DB error")

    from app.views.transfers import get_quota_remaining
    result = get_quota_remaining('LLN111111111', 141, 2026)

    assert result == 0.0
    mock_st.error.assert_called_once()

# Test error messages
@patch('app.auth.supabase')
@patch('app.auth.st')
def test_invalid_credentials_error(self, mock_st, mock_supabase):
    """Should return friendly message for invalid credentials."""
    mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
    mock_st.session_state = MockSessionState()

    from app.auth import login
    success, message = login('test@example.com', 'wrongpassword')

    assert success is False
    assert message == "Invalid email or password"  # User-friendly, not raw exception
```

**Edge Case Testing:**
```python
# Test boundary conditions
def test_format_lbs_with_zero(self):
    """Should format zero correctly."""
    assert format_lbs(0) == "0"

def test_format_lbs_with_none(self):
    """Should return N/A for None."""
    assert format_lbs(None) == "N/A"

def test_format_lbs_with_negative(self):
    """Should handle negative values."""
    assert format_lbs(-1000) == "-1.0K"

def test_format_lbs_with_large_value(self):
    """Should format millions correctly."""
    assert format_lbs(5_000_000) == "5.0M"

# Test missing data
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

# Test data isolation
def test_species_independence(self, supabase, test_org):
    """Should calculate quota independently per species."""
    # Insert allocation for POP
    supabase.table("vessel_allocations").insert({
        "org_id": TEST_ORG_ID,
        "llp": TEST_LLP_A,
        "species_code": SPECIES_POP,
        "year": TEST_YEAR,
        "allocation_lbs": 1000
    }).execute()

    # Check POP remaining
    pop_quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)
    assert pop_quota['remaining_lbs'] == 1000

    # Check NR (different species) is unaffected
    nr_quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_NR, TEST_YEAR)
    assert nr_quota is None  # No allocation for NR
```

## Pytest Configuration

**Config File:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
filterwarnings =
    ignore::DeprecationWarning
```

## Test Accounts

**For E2E Tests:**

| Role | Email | Env Variable | Used In |
|------|-------|--------------|---------|
| Vessel Owner | `vikram.nayani+1@gmail.com` | `TEST_PASSWORD` | Vessel owner view tests |
| Admin | `vikram@fishermenfirst.org` | `ADMIN_PASSWORD` | Admin transfer flow tests |

**Important:** Never commit passwords. Use environment variables only.

```bash
TEST_PASSWORD="xxx" pytest tests/e2e/ -v
```

## Writing New Tests

**Template:**
```python
"""Tests for [module name]."""

import pytest
from unittest.mock import MagicMock, patch

class TestNewFeature:
    """Tests for [specific behavior]."""

    @patch('app.module.dependency')
    def test_describes_expected_behavior(self, mock_dependency):
        """One-sentence docstring describing what the test verifies."""
        # Arrange: Set up test data and mocks
        mock_dependency.method.return_value = expected_value

        # Act: Call the function being tested
        from app.module import function_to_test
        result = function_to_test(input)

        # Assert: Verify the behavior
        assert result == expected_value
        mock_dependency.method.assert_called_once()

    @patch('app.module.dependency')
    def test_error_handling(self, mock_dependency):
        """Should return safe default on error."""
        mock_dependency.method.side_effect = Exception("Something failed")

        from app.module import function_to_test
        result = function_to_test(input)

        assert result == default_safe_value  # 0, [], None, or False
```

## Test Execution

**Running Subsets:**
```bash
pytest tests/test_auth.py                        # Single file
pytest tests/test_auth.py::TestLogin              # Single class
pytest tests/test_auth.py::TestLogin::test_successful_login  # Single test
pytest tests/ -k "transfer"                       # Tests matching pattern
```

**With Output:**
```bash
pytest tests/ -v                                  # Verbose (show all test names)
pytest tests/ -vv                                 # Very verbose (show assertion details)
pytest tests/ -s                                  # Show print statements
pytest tests/ --tb=long                          # Long traceback format
```

## Integration Test Requirements

**Service Role Key:**
1. Go to Supabase dashboard → Settings → API
2. Copy the 'service_role' key (NOT the anon key)
3. Add to `.env`: `SUPABASE_SERVICE_ROLE_KEY=your-key`

**Why Service Role?**
- Needed to bypass RLS policies for test data insertion
- Allows cleanup of test records across organizations
- Only for testing; production uses anon key with RLS

---

*Testing analysis: 2026-01-28*
