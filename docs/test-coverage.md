# Test Coverage Documentation

**Last Updated:** 2026-01-08
**Total Tests:** 148
**Pass Rate:** 100%
**Test Duration:** ~4.4 seconds

---

## Summary by Module

| Module | Test File | Tests | Status |
|--------|-----------|-------|--------|
| Authentication | `test_auth.py` | 41 | All Pass |
| Dashboard | `test_dashboard.py` | 46 | All Pass |
| Transfers | `test_transfers.py` | 33 | All Pass |
| Upload | `test_upload.py` | 28 | All Pass |

---

## test_auth.py (41 tests)

Tests for `app/auth.py` - Authentication, authorization, and session management.

### TestLogin (4 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_successful_login` | Returns (True, 'Login successful') on valid credentials | Pass |
| `test_failed_login_no_user` | Returns (False, 'Login failed') when no user returned | Pass |
| `test_invalid_credentials_error` | Returns friendly message for invalid credentials | Pass |
| `test_generic_error_handling` | Returns error message for other exceptions | Pass |

### TestLogout (2 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_clears_session_state` | Clears all session state variables on logout | Pass |
| `test_handles_signout_error` | Still clears session even if remote signout fails | Pass |

### TestGetUserProfile (3 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_returns_profile_data` | Returns role and processor_code from database | Pass |
| `test_returns_default_when_no_profile` | Returns None values when no profile exists | Pass |
| `test_handles_database_error` | Returns None values on database error | Pass |

### TestRequireRole (5 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_admin_has_access_to_everything` | Admin can access any required role | Pass |
| `test_manager_has_manager_access` | Manager can access manager role | Pass |
| `test_manager_blocked_from_admin` | Manager cannot access admin-only pages | Pass |
| `test_processor_blocked_from_manager` | Processor cannot access manager pages | Pass |
| `test_unauthenticated_blocked` | Unauthenticated users are blocked | Pass |

### TestIsAuthenticated (3 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_returns_true_when_authenticated` | Returns True when user is authenticated | Pass |
| `test_returns_false_when_not_authenticated` | Returns False when not authenticated | Pass |
| `test_returns_false_when_no_user` | Returns False when authenticated but no user object | Pass |

### TestIsAdmin (4 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_returns_true_for_admin` | Returns True for admin role | Pass |
| `test_returns_false_for_manager` | Returns False for manager role | Pass |
| `test_returns_false_for_processor` | Returns False for processor role | Pass |
| `test_returns_false_for_none` | Returns False when no role | Pass |

### TestRefreshSession (3 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_successful_refresh` | Updates session state on successful refresh | Pass |
| `test_no_refresh_token` | Returns False when no refresh token available | Pass |
| `test_refresh_failure` | Returns False on refresh error | Pass |

### TestHandleJwtError (3 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_detects_jwt_expired_error` | Detects JWT expiration errors and refreshes | Pass |
| `test_ignores_non_jwt_errors` | Returns False for non-JWT errors | Pass |
| `test_logs_out_on_refresh_failure` | Logs out and warns user if refresh fails | Pass |

### TestAuthEdgeCases (14 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_unknown_role_blocked_from_admin` | Unknown role cannot access admin pages | Pass |
| `test_unknown_role_blocked_from_manager` | Unknown role cannot access manager pages | Pass |
| `test_empty_string_role` | Empty string role has no access | Pass |
| `test_is_admin_with_unknown_role` | Unknown role is not admin | Pass |
| `test_is_admin_case_sensitive` | Admin check is case sensitive ('Admin' != 'admin') | Pass |
| `test_is_authenticated_missing_authenticated_key` | Handles missing 'authenticated' key gracefully | Pass |
| `test_is_authenticated_missing_user_key` | Handles missing 'user' key gracefully | Pass |
| `test_logout_with_empty_session_state` | Handles logout when session state is empty | Pass |
| `test_get_user_profile_with_unexpected_fields` | Handles profile with extra/missing fields | Pass |
| `test_login_with_empty_email` | Handles empty email | Pass |
| `test_login_with_empty_password` | Handles empty password | Pass |
| `test_refresh_session_with_none_refresh_token` | Handles None refresh token | Pass |
| `test_require_role_with_none_role` | Handles None role from get_current_role | Pass |
| `test_get_user_profile_with_multiple_profiles` | Takes first profile when multiple exist | Pass |

---

## test_dashboard.py (46 tests)

Tests for `app/views/dashboard.py` - Quota dashboard display and calculations.

### TestSpeciesMap (2 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_species_map_contains_target_species` | Contains POP (141), NR (136), Dusky (172) | Pass |
| `test_species_map_excludes_psc` | Does not contain PSC species (Halibut, Pacific Cod) | Pass |

### TestGetRiskLevel (5 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_critical_under_10_percent` | Returns 'critical' for <10% | Pass |
| `test_warning_10_to_50_percent` | Returns 'warning' for 10-50% | Pass |
| `test_ok_over_50_percent` | Returns 'ok' for >50% | Pass |
| `test_na_for_none` | Returns 'na' for None | Pass |
| `test_na_for_nan` | Returns 'na' for NaN | Pass |

### TestFormatLbs (3 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_formats_millions` | Formats millions with M suffix (1.0M, 2.5M) | Pass |
| `test_formats_thousands` | Formats thousands with K suffix (1.0K, 5.5K) | Pass |
| `test_formats_small_numbers` | Formats small numbers as-is (0, 500, 999) | Pass |

### TestGetPctColor (3 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_red_for_critical` | Returns red (#dc2626) for <10% | Pass |
| `test_amber_for_warning` | Returns amber (#d97706) for 10-50% | Pass |
| `test_dark_for_ok` | Returns dark (#1e293b) for >=50% | Pass |

### TestPivotQuotaData (3 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_empty_dataframe_returns_empty` | Returns empty DataFrame for empty input | Pass |
| `test_pivots_species_to_columns` | Creates columns for each species | Pass |
| `test_preserves_vessel_info` | Keeps llp, vessel_name, coop_code | Pass |

### TestAddRiskFlags (4 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_adds_species_risk_columns` | Adds risk column for each species | Pass |
| `test_vessel_at_risk_when_any_critical` | Flags vessel at risk if any species critical | Pass |
| `test_vessel_not_at_risk_when_all_ok` | Does not flag vessel when all species OK | Pass |
| `test_vessel_not_at_risk_when_only_warning` | Does not flag vessel when only warning level | Pass |

### TestGetQuotaData (5 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_returns_empty_when_no_data` | Returns empty DataFrame when no quota data | Pass |
| `test_joins_with_coop_members` | Joins quota data with vessel info | Pass |
| `test_maps_species_codes` | Maps species codes to names (141->POP) | Pass |
| `test_calculates_percent_remaining` | Calculates pct_remaining correctly | Pass |
| `test_handles_zero_allocation` | Handles zero allocation without division error | Pass |

### TestKpiCard (2 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_generates_html` | Generates HTML string with label and value | Pass |
| `test_includes_subtitle_when_provided` | Includes subtitle in HTML | Pass |

### TestSpeciesKpiCard (3 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_includes_percentage` | Includes formatted percentage | Pass |
| `test_includes_remaining_and_allocated` | Shows remaining of allocated | Pass |
| `test_uses_correct_color_for_risk` | Uses red color for critical percentage | Pass |

### TestEdgeCases (16 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_risk_level_exactly_10_percent` | Exactly 10% is 'warning', not 'critical' | Pass |
| `test_risk_level_exactly_50_percent` | Exactly 50% is 'ok', not 'warning' | Pass |
| `test_risk_level_just_under_10` | 9.99% is still 'critical' | Pass |
| `test_risk_level_just_under_50` | 49.99% is still 'warning' | Pass |
| `test_negative_percentage_is_critical` | Negative percentage (overdrawn) is 'critical' | Pass |
| `test_negative_percentage_color` | Negative percentage shows red color | Pass |
| `test_format_lbs_negative` | Formats negative numbers correctly (-5.0K) | Pass |
| `test_format_lbs_very_large` | Handles very large numbers | Pass |
| `test_percentage_over_100` | Handles >100% remaining | Pass |
| `test_unknown_species_code_in_data` | Handles species codes not in SPECIES_MAP | Pass |
| `test_pivot_with_missing_species` | Handles vessel with only some species data | Pass |
| `test_add_risk_flags_with_nan_percentages` | Handles NaN percentages in risk calculation | Pass |
| `test_species_kpi_card_with_zero_allocation` | Handles zero allocation gracefully (shows N/A) | Pass |
| `test_species_kpi_card_with_negative_remaining` | Displays negative remaining (overdrawn) | Pass |

---

## test_transfers.py (33 tests)

Tests for `app/views/transfers.py` - Quota transfer functionality.

### TestGetQuotaRemaining (4 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_returns_remaining_lbs_when_found` | Returns remaining_lbs when quota record exists | Pass |
| `test_returns_zero_when_not_found` | Returns 0 when no quota record exists | Pass |
| `test_returns_zero_when_remaining_is_none` | Returns 0 when remaining_lbs is None | Pass |
| `test_handles_database_error` | Returns 0 and shows error on database exception | Pass |

### TestGetLlpOptions (3 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_returns_formatted_options` | Returns list of (llp, display_string) tuples | Pass |
| `test_returns_empty_list_when_no_data` | Returns empty list when no LLPs exist | Pass |
| `test_handles_missing_vessel_name` | Uses 'Unknown' when vessel_name is None | Pass |

### TestInsertTransfer (5 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_successful_insert_returns_true` | Returns (True, 1, None) on successful insert | Pass |
| `test_insert_includes_correct_fields` | Inserts record with all required fields | Pass |
| `test_empty_notes_becomes_none` | Converts empty notes to None | Pass |
| `test_database_error_returns_failure` | Returns (False, 0, error) on database error | Pass |
| `test_empty_response_returns_failure` | Returns failure when insert returns no data | Pass |

### TestGetTransferHistory (2 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_returns_dataframe_with_transfers` | Returns DataFrame with transfer history | Pass |
| `test_returns_empty_dataframe_when_no_transfers` | Returns empty DataFrame when no transfers | Pass |

### TestTransferValidation (7 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_same_llp_validation` | Same source/dest LLP is invalid | Pass |
| `test_different_llp_validation` | Different source/dest LLP is valid | Pass |
| `test_insufficient_quota_validation` | Cannot transfer more than available | Pass |
| `test_sufficient_quota_validation` | Can transfer up to available quota | Pass |
| `test_zero_pounds_validation` | Cannot transfer zero pounds | Pass |
| `test_negative_pounds_validation` | Cannot transfer negative pounds | Pass |
| `test_valid_species_codes` | Only target species codes are valid | Pass |

### TestTransferIntegration (5 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_transfer_reduces_source_increases_dest` | Source decreases, destination increases | Pass |
| `test_boundary_transfer_exact_available` | Transferring exactly available succeeds | Pass |
| `test_boundary_transfer_one_over` | Transferring one more than available fails | Pass |
| `test_decimal_precision` | Decimal values handled correctly | Pass |
| `test_very_small_transfer` | Very small transfers (0.01 lbs) are valid | Pass |

### TestTransferEdgeCases (7 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_negative_quota_remaining` | Handles negative remaining quota (overfished) | Pass |
| `test_transfer_from_negative_quota_invalid` | Cannot transfer from negative quota | Pass |
| `test_transfer_from_zero_quota_invalid` | Cannot transfer from zero quota | Pass |
| `test_very_long_notes_truncated_or_rejected` | Handles notes exceeding 500 characters | Pass |
| `test_whitespace_only_notes_becomes_none` | Whitespace-only notes handling | Pass |
| `test_float_precision_edge_case` | Float precision doesn't cause false failures | Pass |
| `test_species_code_not_in_options` | Handles invalid species code | Pass |

---

## test_upload.py (28 tests)

Tests for `app/views/upload.py` - eFish data import functionality.

### TestBalanceColumnMap (2 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_balance_column_map_has_required_keys` | All expected balance columns in mapping | Pass |
| `test_detail_column_map_has_required_keys` | All expected detail columns in mapping | Pass |

### TestImportAccountBalance (7 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_successful_import` | Returns (True, count, None) on success | Pass |
| `test_duplicate_detection_silver_bay` | Detects duplicates for Silver Bay | Pass |
| `test_duplicate_detection_north_pacific` | Detects duplicates for North Pacific | Pass |
| `test_duplicate_detection_obsi` | Detects duplicates for OBSI | Pass |
| `test_duplicate_detection_star_of_kodiak` | Detects duplicates for Star of Kodiak | Pass |
| `test_database_error_handling` | Returns error message on database failure | Pass |
| `test_adds_source_file_metadata` | Adds source_file to imported records | Pass |

### TestImportAccountDetail (7 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_successful_import` | Returns (True, count, None) on success | Pass |
| `test_duplicate_report_number_detection` | Detects duplicate report numbers | Pass |
| `test_date_conversion` | Converts date columns to ISO format | Pass |
| `test_handles_null_dates` | Handles NULL/NaT dates gracefully | Pass |
| `test_handles_nan_values` | Converts NaN to None for JSON | Pass |
| `test_database_error_handling` | Returns error on database failure | Pass |
| `test_empty_report_numbers_handled` | Handles empty/null report numbers | Pass |

### TestColumnValidation (3 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_missing_balance_columns_detected` | Identifies missing columns in balance CSV | Pass |
| `test_all_balance_columns_present` | Passes when all columns present | Pass |
| `test_missing_detail_columns_detected` | Identifies missing columns in detail Excel | Pass |

### TestUploadEdgeCases (12 tests)

| Test | Description | Status |
|------|-------------|--------|
| `test_csv_with_extra_columns` | Handles CSV with extra columns | Pass |
| `test_csv_with_reordered_columns` | Handles CSV with columns in different order | Pass |
| `test_negative_quota_values` | Handles negative quota values (overfished) | Pass |
| `test_duplicate_rows_within_file` | Handles duplicate rows within same file | Pass |
| `test_file_with_only_headers` | Handles file with headers but no data | Pass |
| `test_empty_dataframe_import` | Handles empty dataframe gracefully | Pass |
| `test_whitespace_in_column_names` | Handles columns with whitespace | Pass |
| `test_unicode_in_vessel_names` | Handles unicode in vessel/account names | Pass |
| `test_very_large_quota_values` | Handles very large quota values | Pass |
| `test_detail_with_special_characters_in_report_number` | Handles special chars in report numbers | Pass |
| `test_zero_weight_posted` | Handles zero weight posted records | Pass |

---

## Bugs Found and Fixed

During edge case testing, 2 bugs were discovered and fixed:

### Bug 1: `format_lbs` didn't handle negative numbers

**Location:** `app/views/dashboard.py:88`

**Problem:** The function used `>=` comparisons which failed for negative numbers.
```python
# Before: -5000 would return "-5000" instead of "-5.0K"
if value >= 1_000_000:  # -5000 is NOT >= 1,000,000
```

**Fix:** Use `abs(value)` for threshold checks:
```python
abs_value = abs(value)
sign = "-" if value < 0 else ""
if abs_value >= 1_000_000:
    return f"{sign}{abs_value / 1_000_000:.1f}M"
```

### Bug 2: `get_pct_color` crashed on None

**Location:** `app/views/dashboard.py:100`

**Problem:** No None check before comparison.
```python
# Before: TypeError when pct is None
if pct < 10:
```

**Fix:** Add None check at start:
```python
if pct is None:
    return "#94a3b8"  # gray for N/A
```

**Related Fix:** Updated `species_kpi_card` to display "N/A" when percentage is None.

---

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_auth.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html

# Run specific test class
python -m pytest tests/test_dashboard.py::TestEdgeCases -v

# Run single test
python -m pytest tests/test_dashboard.py::TestEdgeCases::test_format_lbs_negative -v
```

---

## Test Infrastructure

### Configuration (`pytest.ini`)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Shared Fixtures (`tests/conftest.py`)
- `mock_supabase` - Mocked Supabase client
- `mock_session_state` - Mocked Streamlit session state
- `sample_llp_data` - Sample LLP/vessel data
- `sample_quota_remaining` - Sample quota data
- `sample_transfer_history` - Sample transfer records

### Mock Utilities (`tests/test_auth.py`)
- `MockSessionState` - Dict subclass supporting both dict and attribute access for Streamlit session state mocking
