# Quota Transfer System

## Overview

The Quota Transfer System allows cooperative managers to transfer fishing quota (in pounds) between License Limitation Program holders (LLPs) within the Central GOA Rockfish Program. Transfers are tracked with a full audit trail and automatically update the remaining quota balances for both parties.

---

## Key Concepts

### LLP (License Limitation Program)
The primary identifier for quota holders. Each LLP represents a fishing operation that has been allocated quota for specific species. Example: `LLN921221203`

### Quota
The amount of fish (in pounds) that an LLP is authorized to harvest for a given species during a fishing season (year).

### Target Species
The three primary rockfish species that can be transferred:

| Code | Species | Common Name |
|------|---------|-------------|
| 141 | Pacific Ocean Perch | POP |
| 136 | Northern Rockfish | NR |
| 172 | Dusky Rockfish | Dusky |

> **Note:** PSC (Prohibited Species Catch) species like Halibut (200) cannot be transferred through this system.

---

## Database Schema

### Primary Tables

#### `vessel_allocations`
Stores the **initial/starting quota** for each LLP at the beginning of the season.

```sql
CREATE TABLE vessel_allocations (
    id UUID PRIMARY KEY,
    llp TEXT,                    -- LLP identifier (e.g., 'LLN921221203')
    species_code INTEGER,        -- Species code (141, 136, or 172)
    year INTEGER,                -- Fishing year (e.g., 2026)
    allocation_lbs NUMERIC,      -- Starting quota in pounds
    created_at TIMESTAMPTZ
);
```

#### `quota_transfers`
Records all quota transfers between LLPs. Supports soft deletes for audit trail.

```sql
CREATE TABLE quota_transfers (
    id UUID PRIMARY KEY,
    from_llp TEXT,               -- Source LLP (loses quota)
    to_llp TEXT,                 -- Destination LLP (gains quota)
    species_code INTEGER,        -- Species being transferred
    year INTEGER,                -- Fishing year
    pounds NUMERIC,              -- Amount transferred
    transfer_date DATE,          -- Date of transfer
    notes TEXT,                  -- Optional notes/comments

    -- Audit fields
    created_by TEXT,             -- User ID who created the transfer
    created_at TIMESTAMPTZ,      -- When transfer was created
    updated_by TEXT,             -- User ID who last updated
    updated_at TIMESTAMPTZ,      -- When last updated
    is_deleted BOOLEAN,          -- Soft delete flag (default: FALSE)
    deleted_by TEXT,             -- User ID who deleted
    deleted_at TIMESTAMPTZ       -- When deleted
);
```

#### `harvests`
Records actual fish harvested against quota. Used in remaining quota calculation.

```sql
CREATE TABLE harvests (
    id UUID PRIMARY KEY,
    llp TEXT,                    -- LLP that harvested
    species_code INTEGER,        -- Species harvested
    processor_code TEXT,         -- Processor who received the catch
    harvest_date DATE,           -- Date of harvest
    pounds NUMERIC,              -- Pounds harvested
    source_file TEXT,            -- Source data file
    notes TEXT,

    -- Audit fields (same pattern as quota_transfers)
    created_by TEXT,
    created_at TIMESTAMPTZ,
    is_deleted BOOLEAN,
    ...
);
```

### Calculated View

#### `quota_remaining`
A PostgreSQL view that calculates the current remaining quota for each LLP/species/year combination.

```sql
CREATE VIEW quota_remaining AS
SELECT
    va.llp,
    va.species_code,
    va.year,
    va.allocation_lbs,
    COALESCE(ti.transfers_in, 0) as transfers_in,
    COALESCE(tout.transfers_out, 0) as transfers_out,
    COALESCE(h.harvested, 0) as harvested,

    -- THE CORE CALCULATION:
    va.allocation_lbs
        + COALESCE(ti.transfers_in, 0)
        - COALESCE(tout.transfers_out, 0)
        - COALESCE(h.harvested, 0)
    as remaining_lbs

FROM vessel_allocations va
LEFT JOIN (
    -- Sum of all pounds transferred TO this LLP
    SELECT to_llp as llp, species_code, year, SUM(pounds) as transfers_in
    FROM quota_transfers
    WHERE is_deleted = FALSE
    GROUP BY to_llp, species_code, year
) ti ON va.llp = ti.llp
    AND va.species_code = ti.species_code
    AND va.year = ti.year

LEFT JOIN (
    -- Sum of all pounds transferred FROM this LLP
    SELECT from_llp as llp, species_code, year, SUM(pounds) as transfers_out
    FROM quota_transfers
    WHERE is_deleted = FALSE
    GROUP BY from_llp, species_code, year
) tout ON va.llp = tout.llp
    AND va.species_code = tout.species_code
    AND va.year = tout.year

LEFT JOIN (
    -- Sum of all pounds harvested by this LLP
    SELECT llp, species_code,
           EXTRACT(YEAR FROM harvest_date)::INTEGER as year,
           SUM(pounds) as harvested
    FROM harvests
    WHERE is_deleted = FALSE
    GROUP BY llp, species_code, EXTRACT(YEAR FROM harvest_date)
) h ON va.llp = h.llp
    AND va.species_code = h.species_code
    AND va.year = h.year;
```

---

## Quota Calculation Formula

```
Remaining Quota = Starting Allocation
                + Transfers In
                - Transfers Out
                - Harvested
```

### Example

| Field | Value |
|-------|-------|
| Starting Allocation | 10,000 lbs |
| Transfers In | 2,000 lbs |
| Transfers Out | 1,500 lbs |
| Harvested | 3,000 lbs |
| **Remaining** | **7,500 lbs** |

Calculation: `10,000 + 2,000 - 1,500 - 3,000 = 7,500`

---

## Transfer Flow

### 1. User Initiates Transfer
A manager or admin selects:
- **From LLP**: The source LLP that will lose quota
- **To LLP**: The destination LLP that will gain quota
- **Species**: Which species quota to transfer (POP, NR, or Dusky)
- **Pounds**: Amount to transfer
- **Notes**: Optional description

### 2. Validation
Before the transfer is allowed, the system validates:

| Check | Rule | Error Message |
|-------|------|---------------|
| Different LLPs | `from_llp != to_llp` | "Source and destination LLP cannot be the same." |
| Positive amount | `pounds > 0` | "Transfer amount must be greater than zero." |
| Sufficient quota | `pounds <= available` | "Insufficient quota. {LLP} only has {X} lbs remaining." |

### 3. Database Insert
If validation passes, a record is inserted into `quota_transfers`:

```python
{
    "from_llp": "LLN921221203",
    "to_llp": "LLN831028070",
    "species_code": 141,
    "year": 2026,
    "pounds": 2000.0,
    "transfer_date": "2026-01-08",
    "notes": "Seasonal quota balance",
    "created_by": "user-uuid-here",
    "is_deleted": False
}
```

### 4. Automatic Balance Update
The `quota_remaining` view automatically recalculates. No additional updates needed.

**Before transfer:**
| LLP | Species | Remaining |
|-----|---------|-----------|
| LLN921221203 | POP | 8,000 lbs |
| LLN831028070 | POP | 5,000 lbs |

**After 2,000 lb transfer:**
| LLP | Species | Remaining |
|-----|---------|-----------|
| LLN921221203 | POP | 6,000 lbs |
| LLN831028070 | POP | 7,000 lbs |

---

## Access Control

| Role | Can Transfer? | Can View History? |
|------|---------------|-------------------|
| Admin | Yes | Yes |
| Manager | Yes | Yes |
| Processor | No | No |

Transfers are **not** restricted by cooperative membership - managers can transfer between any LLPs in the system.

---

## Audit Trail

Every transfer maintains a complete audit trail:

| Field | Purpose |
|-------|---------|
| `created_by` | User ID who created the transfer |
| `created_at` | Timestamp when transfer was created |
| `is_deleted` | Soft delete flag (preserves record) |
| `deleted_by` | User ID who deleted (if applicable) |
| `deleted_at` | Timestamp of deletion (if applicable) |

### Soft Deletes
Records are never physically deleted. Instead, `is_deleted` is set to `TRUE`. This:
- Preserves historical data for auditing
- Allows recovery if needed
- Excludes deleted records from quota calculations (via `WHERE is_deleted = FALSE`)

---

## Data Integrity

### Constraints
- Transfers must reference valid LLPs (foreign key to `coop_members`)
- Species codes must be valid (141, 136, or 172)
- Pounds must be positive
- Year must be valid fishing year

### Race Condition Consideration
If two users attempt to transfer from the same LLP simultaneously, both validation checks might pass before either insert completes. This could result in over-transferring quota (negative balance).

**Current mitigation:** The UI displays available quota and validates before insert, but this is not atomic.

**Future improvement:** Implement database-level constraints or use transactions with row-level locking for production use.

---

## Unit Tests

### Running Tests

```bash
# Run all transfer tests
python -m pytest tests/test_transfers.py -v

# Run with coverage
python -m pytest tests/test_transfers.py -v --cov=app.views.transfers
```

### Test Results Summary

```
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-9.0.2
collected 26 items

tests/test_transfers.py .......................... 26 passed in 4.04s
```

### Test Categories

#### 1. `TestGetQuotaRemaining` (4 tests)
Tests the function that retrieves remaining quota for an LLP/species.

| Test | Purpose | Result |
|------|---------|--------|
| `test_returns_remaining_lbs_when_found` | Verifies correct quota is returned when record exists | PASSED |
| `test_returns_zero_when_not_found` | Returns 0 when LLP has no allocation | PASSED |
| `test_returns_zero_when_remaining_is_none` | Handles NULL values gracefully | PASSED |
| `test_handles_database_error` | Returns 0 and shows error on DB failure | PASSED |

#### 2. `TestGetLlpOptions` (3 tests)
Tests the dropdown population for LLP selection.

| Test | Purpose | Result |
|------|---------|--------|
| `test_returns_formatted_options` | Returns list of (llp, "LLP - Vessel Name") tuples | PASSED |
| `test_returns_empty_list_when_no_data` | Handles empty database gracefully | PASSED |
| `test_handles_missing_vessel_name` | Shows "Unknown" when vessel_name is NULL | PASSED |

> **Bug Found:** This test initially failed because `vessel_name: None` was displaying as "None" instead of "Unknown". Fixed by changing `.get('vessel_name', 'Unknown')` to `.get('vessel_name') or 'Unknown'`.

#### 3. `TestInsertTransfer` (5 tests)
Tests the database insert operation for transfers.

| Test | Purpose | Result |
|------|---------|--------|
| `test_successful_insert_returns_true` | Returns (True, 1, None) on success | PASSED |
| `test_insert_includes_correct_fields` | Verifies all fields are set correctly (from_llp, to_llp, species_code, year, pounds, transfer_date, notes, created_by, is_deleted) | PASSED |
| `test_empty_notes_becomes_none` | Empty string notes converted to NULL | PASSED |
| `test_database_error_returns_failure` | Returns (False, 0, error_message) on DB error | PASSED |
| `test_empty_response_returns_failure` | Handles unexpected empty response | PASSED |

#### 4. `TestGetTransferHistory` (2 tests)
Tests retrieval of transfer history for display.

| Test | Purpose | Result |
|------|---------|--------|
| `test_returns_dataframe_with_transfers` | Returns DataFrame with transfers, vessel names joined, species codes mapped to names | PASSED |
| `test_returns_empty_dataframe_when_no_transfers` | Returns empty DataFrame when no history | PASSED |

#### 5. `TestTransferValidation` (7 tests)
Tests validation logic (pure logic, no mocking required).

| Test | Purpose | Result |
|------|---------|--------|
| `test_same_llp_validation` | Detects when from_llp == to_llp | PASSED |
| `test_different_llp_validation` | Allows different LLPs | PASSED |
| `test_insufficient_quota_validation` | Detects when requested > available | PASSED |
| `test_sufficient_quota_validation` | Allows when requested <= available | PASSED |
| `test_zero_pounds_validation` | Rejects zero pound transfers | PASSED |
| `test_negative_pounds_validation` | Rejects negative pound transfers | PASSED |
| `test_valid_species_codes` | Only allows target species (141, 136, 172), not PSC (200) | PASSED |

#### 6. `TestTransferIntegration` (5 tests)
Tests business logic and edge cases.

| Test | Purpose | Result |
|------|---------|--------|
| `test_transfer_reduces_source_increases_dest` | Verifies math: source - amount, dest + amount | PASSED |
| `test_boundary_transfer_exact_available` | Allows transfer of exactly available amount | PASSED |
| `test_boundary_transfer_one_over` | Rejects transfer of available + 1 | PASSED |
| `test_decimal_precision` | Handles decimal values (e.g., 1000.50 lbs) | PASSED |
| `test_very_small_transfer` | Allows very small transfers (0.01 lbs) | PASSED |

### Edge Cases Covered

| Edge Case | Test Coverage |
|-----------|---------------|
| LLP with no allocation | `test_returns_zero_when_not_found` |
| NULL remaining_lbs value | `test_returns_zero_when_remaining_is_none` |
| NULL vessel_name | `test_handles_missing_vessel_name` |
| Database connection failure | `test_handles_database_error`, `test_database_error_returns_failure` |
| Empty notes field | `test_empty_notes_becomes_none` |
| Transfer to same LLP | `test_same_llp_validation` |
| Zero pound transfer | `test_zero_pounds_validation` |
| Negative pound transfer | `test_negative_pounds_validation` |
| Exact boundary transfer | `test_boundary_transfer_exact_available` |
| Over-limit transfer | `test_boundary_transfer_one_over`, `test_insufficient_quota_validation` |
| Decimal precision | `test_decimal_precision` |
| Very small amounts | `test_very_small_transfer` |
| PSC species exclusion | `test_valid_species_codes` |

### Test Infrastructure

| File | Purpose |
|------|---------|
| `tests/__init__.py` | Package marker |
| `tests/conftest.py` | Shared pytest fixtures (mock_supabase, sample data) |
| `tests/test_transfers.py` | All transfer-related tests |
| `pytest.ini` | Pytest configuration |

### Mocking Strategy

Tests use `unittest.mock.patch` to mock:
- `app.views.transfers.supabase` - Database client
- `app.views.transfers.st` - Streamlit UI functions (for error display tests)

This allows tests to run without a database connection and verify behavior in isolation.

---

## Related Files

| File | Purpose |
|------|---------|
| `app/views/transfers.py` | Transfer UI and business logic |
| `sql/schema.sql` | Database schema definitions |
| `tests/test_transfers.py` | Unit tests for transfer logic |

---

## Glossary

| Term | Definition |
|------|------------|
| **LLP** | License Limitation Program - the unique identifier for a quota holder |
| **TAC** | Total Allowable Catch - the total quota available for all participants |
| **PSC** | Prohibited Species Catch - species with special handling (not transferable) |
| **Soft Delete** | Marking a record as deleted without removing it from the database |
| **Allocation** | The initial quota assigned to an LLP at the start of the season |
| **Remaining** | Current available quota after transfers and harvests |
