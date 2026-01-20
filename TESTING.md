# Testing Guide

This document covers the test suite for the Fishermen First Rockfish Platform.

## Test Summary

| Type | Count | Location |
|------|-------|----------|
| Unit Tests | 234 | `tests/` |
| Integration Tests | 15 | `tests/test_quota_tracking.py` |
| E2E Tests | 10 | `tests/e2e/` |
| **Total** | **259** | |

## Quick Start

```bash
# Run all unit tests (fast, ~4 seconds)
pytest tests/ --ignore=tests/e2e -v

# Run all tests including e2e (~80 seconds)
pytest tests/ -v

# Run specific test file
pytest tests/test_transfers.py -v

# Run with coverage report
pytest tests/ --ignore=tests/e2e --cov=app --cov-report=html
open htmlcov/index.html
```

## Test Structure

```
tests/
├── conftest.py            # Shared fixtures (mock Supabase, session state)
├── test_auth.py           # Authentication & authorization (47 tests)
├── test_dashboard.py      # Dashboard logic & formatting (27 tests)
├── test_quota_tracking.py # DB integration: quota math (15 tests) *
├── test_transfers.py      # Quota transfers (83 tests)
├── test_upload.py         # CSV upload & parsing (35 tests)
├── test_vessel_owner.py   # Vessel owner view (28 tests)
└── e2e/
    └── test_app.py        # Browser-based tests (10 tests) **

* Requires SUPABASE_SERVICE_ROLE_KEY
** Requires TEST_PASSWORD and ADMIN_PASSWORD
```

## Test Coverage by File

### test_auth.py (47 tests)

| Class | Tests | What It Covers |
|-------|-------|----------------|
| TestLogin | 4 | Successful login, failed login, invalid credentials, error handling |
| TestLogout | 2 | Session clearing, signout error handling |
| TestGetUserProfile | 3 | Profile data, missing profile, database errors |
| TestRequireRole | 5 | Admin access, manager access, role blocking |
| TestIsAuthenticated | 3 | Auth state checks |
| TestIsAdmin | 4 | Admin role detection |
| TestRefreshSession | 3 | Token refresh, missing token, refresh failure |
| TestHandleJwtError | 3 | JWT expiration detection and handling |
| TestAuthEdgeCases | 20 | Unknown roles, empty strings, edge cases |

### test_dashboard.py (27 tests)

| Class | Tests | What It Covers |
|-------|-------|----------------|
| TestSpeciesMap | 2 | Species code mapping (141, 136, 172) |
| TestGetRiskLevel | 3 | Critical (<10%), warning (10-50%), OK (>50%) |
| TestFormatLbs | 5 | Formatting: millions, thousands, small, negative, zero |
| TestGetPctColor | 4 | Color coding by percentage |
| TestKpiCard | 3 | KPI card HTML generation |
| TestGetQuotaData | 4 | Data fetching and joining |
| TestPivotQuotaData | 3 | Wide format pivot |
| TestAddRiskFlags | 3 | Risk flag calculation |

### test_transfers.py (83 tests)

| Class | Tests | What It Covers |
|-------|-------|----------------|
| TestGetQuotaRemaining | 4 | Quota lookup, missing data, errors |
| TestGetLlpOptions | 3 | LLP dropdown formatting |
| TestInsertTransfer | 5 | Insert success, field validation, errors |
| TestGetTransferHistory | 2 | History fetch, empty results |
| TestTransferValidation | 7 | Same LLP, quota limits, species codes |
| TestTransferIntegration | 5 | Math verification, boundary cases |
| TestTransferEdgeCases | 8 | Negative quota, long notes, whitespace |
| **TestTransferAuthorization** | 4 | Role-based access control |
| **TestTransferRoleHierarchy** | 3 | Admin > Manager > Others |
| **TestTransferMultiTenancy** | 4 | org_id isolation |
| **TestTransferCaching** | 4 | Cache behavior, TTL |
| **TestTransferConcurrency** | 3 | Race conditions (documented) |
| **TestTransferBusinessRules** | 7 | Min/max, audit trail, dates |
| **TestTransferToInactiveVessel** | 2 | Inactive vessel handling |
| **TestTransferSecurity** | 5 | SQL injection, XSS, unicode |
| **TestTransferInputSanitization** | 3 | Input validation |
| **TestTransferYearHandling** | 6 | Year constants, date format |
| **TestTransferDateEdgeCases** | 3 | Year boundaries |
| **TestTransferSoftDelete** | 2 | Soft delete behavior |
| **TestTransferDisplayFormatting** | 3 | Display formatting |

### test_quota_tracking.py (15 tests) - Integration

**Requires:** `SUPABASE_SERVICE_ROLE_KEY` in `.env`

| Class | Tests | What It Covers |
|-------|-------|----------------|
| TestQuotaAllocation | 2 | Fresh allocation display, zero handling |
| TestQuotaTransfers | 4 | In/out reduces/increases, accumulation, soft delete |
| TestQuotaHarvests | 3 | Harvest deduction, accumulation, soft delete |
| TestQuotaIsolation | 2 | Species independence, year independence |
| TestQuotaEdgeCases | 4 | Full formula, zero remaining, overage, decimals |

### test_upload.py (35 tests)

| Class | Tests | What It Covers |
|-------|-------|----------------|
| TestBalanceColumnMap | 2 | Column mapping validation |
| TestDetailColumnMap | 2 | Excel column mapping |
| TestDetectBalanceDuplicates | 4 | Duplicate detection in CSV |
| TestDetectDetailDuplicates | 4 | Duplicate report numbers |
| TestImportAccountBalance | 6 | Balance import, duplicates, errors |
| TestImportAccountDetail | 6 | Detail import, date handling |
| TestUploadEdgeCases | 11 | Empty files, special characters, nulls |

### test_vessel_owner.py (28 tests)

| Class | Tests | What It Covers |
|-------|-------|----------------|
| TestVesselOwnerAuth | 3 | LLP retrieval from profile |
| TestVesselOwnerRoleCheck | 3 | Role verification |
| TestGetUserLlp | 2 | LLP session state |
| TestVesselOwnerViewFunctions | 5 | Data fetching (vessel, quota, harvests) |
| TestVesselOwnerViewHelpers | 9 | Formatting, colors |
| TestVesselOwnerTransferDirection | 2 | IN/OUT direction |
| TestVesselOwnerNavigation | 4 | Nav options by role |

### test_app.py - E2E Tests (10 tests)

| Class | Tests | What It Covers |
|-------|-------|----------------|
| TestLoginPage | 3 | Page loads, empty form error, invalid credentials |
| TestVesselOwnerView | 3 | Login flow, quota cards, logout |
| TestAdminTransferFlow | 4 | Transfers page access, form elements, validation, quota display |

## E2E Tests

### Prerequisites

```bash
pip install playwright pytest-playwright
playwright install chromium
```

### Running E2E Tests

```bash
# Headless (CI/CD)
pytest tests/e2e/ -v

# With browser visible (debugging)
pytest tests/e2e/ --headed

# With credentials (required for login tests)
TEST_PASSWORD="password" pytest tests/e2e/ -v
```

### Test Accounts

| Role | Email | Env Variable | Notes |
|------|-------|--------------|-------|
| Vessel Owner | `vikram.nayani+1@gmail.com` | `TEST_PASSWORD` | Used for vessel owner e2e tests |
| Admin | `vikram@fishermenfirst.org` | `ADMIN_PASSWORD` | Used for admin transfer e2e tests |

**Important:** Never commit passwords. Use environment variables.

## Writing New Tests

### Unit Test Template

```python
"""Tests for [module name]."""

import pytest
from unittest.mock import MagicMock, patch


class TestFeatureName:
    """Tests for [feature description]."""

    @patch('app.views.module.supabase')
    def test_successful_case(self, mock_supabase):
        """Should [expected behavior]."""
        # Arrange
        mock_response = MagicMock()
        mock_response.data = [{'id': 'test'}]
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_response

        # Act
        from app.views.module import function_name
        result = function_name()

        # Assert
        assert result is not None

    def test_validation_logic(self):
        """Should validate [condition]."""
        # Pure logic tests don't need mocking
        value = 100
        is_valid = value > 0
        assert is_valid is True
```

### E2E Test Template

```python
def test_feature_works(self, page: Page, app_server):
    """User should be able to [action]."""
    page.goto(APP_URL)

    # Interact
    page.fill("input[type='text']", "value")
    page.click("button:has-text('Submit')")

    # Assert
    expect(page.locator("text=Success")).to_be_visible()
```

### Test Naming Conventions

- Test files: `test_<module>.py`
- Test classes: `Test<Feature>`
- Test methods: `test_<scenario>` or `test_<action>_<expected_result>`

Examples:
- `test_returns_zero_when_not_found`
- `test_admin_has_transfer_access`
- `test_sql_injection_in_notes_escaped`

## Mocking Patterns

### Mock Supabase Client

```python
@patch('app.views.transfers.supabase')
def test_example(self, mock_supabase):
    mock_response = MagicMock()
    mock_response.data = [{'field': 'value'}]

    # Chain: table().select().eq().execute()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
```

### Mock Streamlit Session State

```python
@patch('app.auth.st')
def test_example(self, mock_st):
    mock_st.session_state = MagicMock()
    mock_st.session_state.authenticated = True
    mock_st.session_state.user_role = "admin"
```

### Mock Multiple Tables

```python
def table_side_effect(table_name):
    mock_table = MagicMock()
    if table_name == 'quota_transfers':
        mock_table.select.return_value.execute.return_value.data = [...]
    elif table_name == 'coop_members':
        mock_table.select.return_value.execute.return_value.data = [...]
    return mock_table

mock_supabase.table.side_effect = table_side_effect
```

## Test Categories

Tests are organized by what they verify:

| Category | Purpose | Example |
|----------|---------|---------|
| **Functional** | Core business logic works | Transfer reduces source quota |
| **Validation** | Invalid input rejected | Same LLP transfer blocked |
| **Authorization** | Role access enforced | Vessel owner can't create transfers |
| **Security** | Attacks handled safely | SQL injection in notes escaped |
| **Edge Cases** | Boundaries handled | Zero quota, negative values |
| **Integration** | Components work together | Transfer history shows vessel names |

## Known Test Gaps

These scenarios are **documented but not fully tested**:

1. **Concurrency** - Race condition between quota check and insert
2. **Inactive Vessels** - No filter in transfer dropdowns
3. **RLS Enforcement** - Relies on Supabase, not tested in unit tests

## CI/CD Integration

For GitHub Actions or similar:

```yaml
- name: Run Tests
  run: |
    pip install -r requirements.txt
    pip install pytest pytest-mock
    pytest tests/ --ignore=tests/e2e -v --tb=short

- name: Run E2E Tests
  env:
    TEST_PASSWORD: ${{ secrets.TEST_PASSWORD }}
    ADMIN_PASSWORD: ${{ secrets.ADMIN_PASSWORD }}
  run: |
    pip install playwright pytest-playwright
    playwright install chromium
    pytest tests/e2e/ -v
```

## Troubleshooting

### "No runtime found, using MemoryCacheStorageManager"
This is a Streamlit warning when running tests outside the Streamlit runtime. It's expected and harmless.

### E2E tests timeout
- Ensure no other Streamlit server is running on port 8501
- Increase timeout: `page.wait_for_timeout(5000)`

### Mock not working
- Check the patch path matches the import in the module being tested
- Use `@patch('app.views.transfers.supabase')` not `@patch('app.config.supabase')`
