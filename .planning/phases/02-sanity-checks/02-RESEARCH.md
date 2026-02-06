# Phase 2: Sanity Checks - Research

**Researched:** 2026-01-28
**Domain:** PostgreSQL data quality validation, SQL sanity checks, data integrity queries
**Confidence:** HIGH

## Summary

This research investigated PostgreSQL best practices for implementing data quality sanity checks via SQL queries. The standard approach is to create dedicated validation queries in a single SQL file (`checks.sql`) that can be run manually or automated to detect data quality issues such as negative allocations, over-transferred quota, future-year data, and referential integrity violations.

The research focused on five specific sanity checks required for the Rockfish quota tracking system:
1. Detecting negative allocations (invalid business rule)
2. Detecting over-transferred quota where remaining < 0
3. Detecting future-year data (year > current year)
4. Detecting invalid species codes (foreign key violations)
5. Ensuring all checks are runnable via a single file

PostgreSQL's built-in constraint checking mechanisms (CHECK constraints, foreign keys) prevent many issues at write-time, but sanity checks serve as **detective controls** that identify data quality problems that may have bypassed constraints or arose from complex multi-table interactions (like the quota_metrics view calculations).

**Primary recommendation:** Create `sql/checks.sql` with SELECT queries that return problematic rows (zero rows = all good). Use COMMENT ON queries to document expected results. Structure checks to be self-documenting with descriptive column aliases and UNION ALL for consolidated reporting.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL | 15+ | Database with advanced query features | Supabase uses modern Postgres; supports CTEs, window functions, sophisticated filtering |
| SQL SELECT queries | Built-in | Read-only validation queries | Standard mechanism for data quality checks; no side effects |

### Supporting
| Function/Feature | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| EXTRACT(YEAR FROM date) | Built-in | Extract year component from dates | Comparing years, detecting future dates |
| NOT EXISTS | Built-in | Referential integrity checks | Detecting orphaned foreign keys |
| WHERE NOT IN | Built-in | Set-based validation | Checking against allowed value lists |
| UNION ALL | Built-in | Combining check results | Consolidating multiple checks into single output |
| CTE (WITH clause) | Postgres 8.4+ | Temporary named result sets | Breaking complex checks into readable steps |
| CURRENT_DATE | Built-in | Server's current date | Comparing against "now" for future-year checks |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SELECT queries in .sql file | CHECK constraints | Constraints enforce at write-time but can't report existing violations; both are needed |
| SELECT queries | Triggers for validation | Triggers prevent writes but don't identify existing bad data; checks are detective, triggers preventive |
| UNION ALL results | Separate query files | Single file easier to run; UNION ALL provides consolidated report |
| Manual queries | pg_check tool | pg_check is for physical file corruption; our checks are for business logic violations |
| SQL checks | Application-level validation | SQL runs server-side, no data transfer; catches issues at source |

**Installation:**
Built-in PostgreSQL features. No installation needed.

## Architecture Patterns

### Recommended Project Structure
```
sql/
├── schema-v2-multi-tenant.sql    # Main schema with constraints
├── migrations/                   # Incremental changes
│   └── 013_add_quota_metrics.sql # Phase 1 output
└── checks.sql                    # NEW: Data quality sanity checks (Phase 2)
```

### Pattern 1: Self-Documenting Check Queries (Recommended)
**What:** SELECT queries that return problematic rows with descriptive columns
**When to use:** Always - makes output immediately actionable
**Example:**
```sql
-- Source: PostgreSQL data quality best practices + current codebase patterns
-- CHEK-01: Detect negative allocations
SELECT
    'CHEK-01: Negative allocation' AS check_name,
    org_id,
    llp,
    species_code,
    year,
    allocation_lbs,
    'Allocation cannot be negative' AS issue
FROM allocations
WHERE allocation_lbs < 0
ORDER BY allocation_lbs ASC;  -- Most negative first

-- Expected: 0 rows (no negative allocations should exist)
```

### Pattern 2: Consolidated Check Report (Recommended for Multiple Checks)
**What:** Use UNION ALL to combine all checks into single query output
**When to use:** When running all checks at once for reporting
**Example:**
```sql
-- Source: PostgreSQL UNION documentation + data quality practices
-- All sanity checks in one query
SELECT * FROM (
    -- Check 1: Negative allocations
    SELECT 'CHEK-01' AS check_id, llp, species_code, year, 'Negative allocation' AS issue
    FROM allocations WHERE allocation_lbs < 0

    UNION ALL

    -- Check 2: Over-transferred quota
    SELECT 'CHEK-02' AS check_id, llp, species_code, year, 'Over-transferred (remaining < 0)' AS issue
    FROM quota_metrics WHERE remaining_lbs < 0

    UNION ALL

    -- Check 3: Future year
    SELECT 'CHEK-03' AS check_id, llp, species_code, year, 'Future year data' AS issue
    FROM allocations WHERE year > EXTRACT(YEAR FROM CURRENT_DATE)

) all_checks
ORDER BY check_id, year DESC, llp;

-- Expected: 0 rows means all checks pass
```

### Pattern 3: Parameterized Checks with Variables
**What:** Use variables for year, thresholds to make checks reusable
**When to use:** When checks need to be run for different years/orgs
**Example:**
```sql
-- Source: PostgreSQL variable usage in scripts
-- Check for specific year (run for current season)
DO $$
DECLARE
    check_year INTEGER := EXTRACT(YEAR FROM CURRENT_DATE);
BEGIN
    -- Checks use check_year variable
    RAISE NOTICE 'Running checks for year: %', check_year;
END $$;
```
**Note:** For simplicity, Phase 2 will use static queries without variables. Pattern documented for future enhancement.

### Pattern 4: Referential Integrity Checks
**What:** Use NOT EXISTS or LEFT JOIN to find orphaned records
**When to use:** When checking foreign key relationships not enforced by constraints
**Example:**
```sql
-- Source: PostgreSQL foreign key validation patterns
-- CHEK-04: Detect invalid species codes
SELECT DISTINCT
    'CHEK-04: Invalid species_code' AS check_name,
    a.species_code,
    'Species code not in species table' AS issue
FROM allocations a
WHERE NOT EXISTS (
    SELECT 1 FROM species s WHERE s.code = a.species_code
)
ORDER BY a.species_code;

-- Expected: 0 rows (all species codes should exist in species table)
```

### Anti-Patterns to Avoid

- **Using UPDATE/DELETE in checks:** Sanity checks should be read-only SELECT queries, never modify data
  - Source: Data quality best practices - checks are detective, not corrective

- **Checks without ORDER BY:** Makes output non-deterministic and hard to review
  - Source: SQL best practices - always order validation query results

- **Generic error messages:** "Invalid data" is useless; describe the specific violation
  - Source: Debugging best practices - actionable error messages

- **Checking views without checking base tables:** Always check source tables first; view issues often stem from bad base data
  - Source: PostgreSQL debugging patterns

- **No documentation of expected results:** Readers don't know if results are bad without context
  - Source: Code review best practices - document expected outcomes

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Physical corruption checks | Custom queries reading pg_* tables | pg_check tool, pg_verify_checksums | Physical corruption needs specialized tools; our checks are for business logic |
| Automated scheduling | Custom cron scripts | PostgreSQL pg_cron extension or CI/CD pipeline | Cron extension is database-native; CI/CD integrates with deployment |
| Check result storage | Custom logging tables | PostgreSQL logs or monitoring tools (pgBadger, DataDog) | Monitoring infrastructure already exists; don't duplicate |
| Data repair scripts | Manual UPDATE queries in checks.sql | Separate migration files | Checks detect, migrations fix; separation of concerns |

**Key insight:** Sanity checks are **detective controls** (find problems), not **corrective controls** (fix problems). Keep them read-only and create separate migration scripts for fixes.

## Common Pitfalls

### Pitfall 1: Checking Views Instead of Source Tables
**What goes wrong:** View-based checks miss issues in base tables or give misleading results
**Why it happens:** Views like `quota_metrics` aggregate data; issues may be masked or duplicated
**How to avoid:** Check base tables first (`allocations`, `transfers`, `harvests`), then check derived views
**Warning signs:** Check returns duplicates, or issues disappear when checking base tables

**Code pattern:**
```sql
-- BAD: Only checking view
SELECT * FROM quota_metrics WHERE remaining_lbs < 0;
-- Misses cases where allocation itself is negative (different issue)

-- GOOD: Check base tables AND view
-- Check 1: Base table validation
SELECT * FROM allocations WHERE allocation_lbs < 0;

-- Check 2: Derived metric validation (different issue)
SELECT * FROM quota_metrics WHERE remaining_lbs < 0 AND allocation_lbs >= 0;
-- Remaining < 0 despite valid allocation = over-transferred
```

### Pitfall 2: Year Comparison with Dates vs Integers
**What goes wrong:** Comparing year (INTEGER) with dates directly causes type mismatch
**Why it happens:** Allocations store `year` as INTEGER, but CURRENT_DATE is a DATE
**How to avoid:** Always extract year component: `EXTRACT(YEAR FROM CURRENT_DATE)`
**Warning signs:** "Cannot compare INTEGER with DATE" error

**Code pattern:**
```sql
-- BAD: Type mismatch
SELECT * FROM allocations WHERE year > CURRENT_DATE;
-- ERROR: operator does not exist: integer > date

-- GOOD: Compare integers
SELECT * FROM allocations WHERE year > EXTRACT(YEAR FROM CURRENT_DATE);
-- Returns rows with future years
```

### Pitfall 3: Forgetting to Filter Soft-Deleted Records
**What goes wrong:** Checks report violations in deleted (inactive) records
**Why it happens:** Transfers and harvests have `is_deleted` flag; deleted records don't affect quota
**How to avoid:** Include `WHERE NOT is_deleted` when checking transaction tables
**Warning signs:** Check reports issues that users say are "already deleted"

**Code pattern:**
```sql
-- BAD: Includes deleted transfers
SELECT from_llp FROM transfers WHERE year > EXTRACT(YEAR FROM CURRENT_DATE);
-- Reports deleted future transfers

-- GOOD: Exclude soft-deleted
SELECT from_llp FROM transfers
WHERE year > EXTRACT(YEAR FROM CURRENT_DATE) AND NOT is_deleted;
-- Only reports active future transfers
```

### Pitfall 4: Species Table is Shared (No org_id)
**What goes wrong:** Checking species by org_id fails; species table is shared across orgs
**Why it happens:** Species reference data is global (same fish species for all organizations)
**How to avoid:** Don't filter species table by org_id; it has no org_id column
**Warning signs:** "Column org_id does not exist" error on species table queries

**Code pattern:**
```sql
-- BAD: Species has no org_id
SELECT * FROM species WHERE org_id = '...';
-- ERROR: column "org_id" does not exist

-- GOOD: Species is global reference data
SELECT * FROM species WHERE code NOT IN (141, 136, 172);
-- Check for unexpected species codes
```

### Pitfall 5: NULL vs Zero in Numeric Checks
**What goes wrong:** `remaining_lbs < 0` doesn't catch NULL values
**Why it happens:** NULL comparisons return NULL (not TRUE), so row is excluded
**How to avoid:** Decide business rule for NULL (should it be reported?), add explicit NULL check if needed
**Warning signs:** Known NULL rows missing from check results

**Code pattern:**
```sql
-- Potentially incomplete: Misses NULLs
SELECT * FROM quota_metrics WHERE remaining_lbs < 0;

-- Complete: Reports both negative AND null
SELECT * FROM quota_metrics WHERE remaining_lbs < 0 OR remaining_lbs IS NULL;

-- Or separate checks
SELECT * FROM quota_metrics WHERE remaining_lbs IS NULL;  -- CHEK-05a: NULL remaining
SELECT * FROM quota_metrics WHERE remaining_lbs < 0;      -- CHEK-05b: Negative remaining
```

## Code Examples

Verified patterns from official sources and current codebase:

### Check Template: Single Issue Detection
```sql
-- Source: PostgreSQL SELECT documentation + data quality patterns
-- =============================================================================
-- CHEK-01: Negative Allocations
-- =============================================================================
-- Purpose: Detect allocations with negative values (business rule violation)
-- Expected: 0 rows (all allocations should be >= 0)

SELECT
    'CHEK-01' AS check_id,
    'Negative allocation' AS issue,
    org_id,
    llp,
    species_code,
    year,
    allocation_lbs,
    'Allocation cannot be negative' AS description
FROM allocations
WHERE allocation_lbs < 0
ORDER BY allocation_lbs ASC, year DESC, llp;

-- If any rows returned: Investigate how negative allocation was created
-- Likely fix: UPDATE allocations SET allocation_lbs = ABS(allocation_lbs) WHERE allocation_lbs < 0;
```

### Over-Transferred Quota Check
```sql
-- Source: Current codebase quota_metrics view + business requirements
-- =============================================================================
-- CHEK-02: Over-Transferred Quota
-- =============================================================================
-- Purpose: Detect when remaining quota is negative (more transferred out than available)
-- Expected: 0 rows (quota_metrics.remaining_lbs should be >= 0 for all active allocations)

SELECT
    'CHEK-02' AS check_id,
    'Over-transferred quota' AS issue,
    qm.org_id,
    qm.llp,
    qm.species_code,
    qm.year,
    qm.allocation_lbs,
    qm.transfers_in,
    qm.transfers_out,
    qm.harvested,
    qm.remaining_lbs,
    'Remaining quota is negative (over-transferred or over-harvested)' AS description
FROM quota_metrics qm
WHERE qm.remaining_lbs < 0
ORDER BY qm.remaining_lbs ASC, qm.year DESC, qm.llp;

-- If any rows returned: Review transfers and harvests for this LLP/species/year
-- Possible causes:
--   1. Transfer created without checking available quota (race condition)
--   2. Harvest exceeded available quota (eLandings data issue)
--   3. Multiple transfers processed simultaneously
```

### Future Year Data Check
```sql
-- Source: PostgreSQL date functions + temporal validation patterns
-- =============================================================================
-- CHEK-03: Future Year Data
-- =============================================================================
-- Purpose: Detect data with year > current year (should not exist in production)
-- Expected: 0 rows (current year is {{ current_year }})

WITH current_year AS (
    SELECT EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER AS year
)
SELECT
    'CHEK-03' AS check_id,
    'Future year data' AS issue,
    'allocations' AS table_name,
    a.org_id,
    a.llp,
    a.species_code,
    a.year,
    cy.year AS current_year,
    'Data should not exist for future years' AS description
FROM allocations a, current_year cy
WHERE a.year > cy.year

UNION ALL

SELECT
    'CHEK-03' AS check_id,
    'Future year data' AS issue,
    'transfers' AS table_name,
    t.org_id,
    t.from_llp AS llp,
    t.species_code,
    t.year,
    cy.year AS current_year,
    'Data should not exist for future years' AS description
FROM transfers t, current_year cy
WHERE t.year > cy.year AND NOT t.is_deleted

UNION ALL

SELECT
    'CHEK-03' AS check_id,
    'Future year data' AS issue,
    'harvests' AS table_name,
    h.org_id,
    h.llp,
    h.species_code,
    h.year,
    cy.year AS current_year,
    'Data should not exist for future years' AS description
FROM harvests h, current_year cy
WHERE h.year > cy.year AND NOT h.is_deleted

ORDER BY table_name, year DESC, llp;

-- If any rows returned: Data entry error or testing data in production
-- Fix: Delete future year data or correct year values
```

### Invalid Foreign Key Check
```sql
-- Source: PostgreSQL foreign key validation patterns + referential integrity checks
-- =============================================================================
-- CHEK-04: Invalid Species Codes
-- =============================================================================
-- Purpose: Detect species codes that don't exist in species reference table
-- Expected: 0 rows (all species codes should be valid)

-- Known valid species codes: 141 (POP), 136 (NR), 172 (Dusky)

SELECT DISTINCT
    'CHEK-04' AS check_id,
    'Invalid species_code' AS issue,
    'allocations' AS table_name,
    a.species_code,
    COUNT(*) AS affected_rows,
    'Species code not in species table' AS description
FROM allocations a
WHERE NOT EXISTS (
    SELECT 1 FROM species s WHERE s.code = a.species_code
)
GROUP BY a.species_code

UNION ALL

SELECT DISTINCT
    'CHEK-04' AS check_id,
    'Invalid species_code' AS issue,
    'transfers' AS table_name,
    t.species_code,
    COUNT(*) AS affected_rows,
    'Species code not in species table' AS description
FROM transfers t
WHERE NOT EXISTS (
    SELECT 1 FROM species s WHERE s.code = t.species_code
)
AND NOT t.is_deleted
GROUP BY t.species_code

UNION ALL

SELECT DISTINCT
    'CHEK-04' AS check_id,
    'Invalid species_code' AS issue,
    'harvests' AS table_name,
    h.species_code,
    COUNT(*) AS affected_rows,
    'Species code not in species table' AS description
FROM harvests h
WHERE NOT EXISTS (
    SELECT 1 FROM species s WHERE s.code = h.species_code
)
AND NOT h.is_deleted
GROUP BY h.species_code

ORDER BY table_name, species_code;

-- If any rows returned: Either missing species in reference table or data entry error
-- Fix option 1: INSERT missing species into species table
-- Fix option 2: Correct the invalid species codes in affected tables
```

### Complete checks.sql Structure
```sql
-- Source: Synthesized from patterns above + current codebase migration style
-- =============================================================================
-- Data Quality Sanity Checks
-- =============================================================================
-- Purpose: Detect data integrity issues in quota tracking system
-- Usage: Run manually via psql or SQL editor
-- Expected: All queries should return 0 rows if data is valid
--
-- Requirements:
--   CHEK-01: Negative allocations
--   CHEK-02: Over-transferred quota (remaining < 0)
--   CHEK-03: Future year data
--   CHEK-04: Invalid species codes
--   CHEK-05: All checks runnable via single file
-- =============================================================================

-- =============================================================================
-- CHEK-01: Negative Allocations
-- =============================================================================
[query from above]

-- =============================================================================
-- CHEK-02: Over-Transferred Quota
-- =============================================================================
[query from above]

-- =============================================================================
-- CHEK-03: Future Year Data
-- =============================================================================
[query from above]

-- =============================================================================
-- CHEK-04: Invalid Species Codes
-- =============================================================================
[query from above]

-- =============================================================================
-- Summary Report: Run All Checks
-- =============================================================================
-- Uncomment to run all checks in one query with consolidated output:

/*
SELECT * FROM (
    -- CHEK-01
    SELECT 'CHEK-01' AS check_id, 'Negative allocation' AS issue,
           llp, species_code, year, allocation_lbs::TEXT AS detail
    FROM allocations WHERE allocation_lbs < 0

    UNION ALL

    -- CHEK-02
    SELECT 'CHEK-02', 'Over-transferred quota',
           llp, species_code, year, remaining_lbs::TEXT
    FROM quota_metrics WHERE remaining_lbs < 0

    UNION ALL

    -- CHEK-03
    SELECT 'CHEK-03', 'Future year data',
           llp, species_code, year, 'allocations'::TEXT
    FROM allocations WHERE year > EXTRACT(YEAR FROM CURRENT_DATE)

    UNION ALL

    -- CHEK-04
    SELECT 'CHEK-04', 'Invalid species_code',
           ''::TEXT, species_code, 0, 'allocations'::TEXT
    FROM allocations WHERE NOT EXISTS (SELECT 1 FROM species s WHERE s.code = species_code)

) all_checks
ORDER BY check_id, year DESC, llp;
*/
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual ad-hoc queries | Documented checks.sql file | 2020s trend | Reproducible checks, easier onboarding |
| Separate query files | Single file with sections | Modern practice | Single execution point, easier to run all checks |
| Silent failures (no results documented) | Expected results documented | Data quality evolution | Clear pass/fail criteria |
| Application-level validation only | Database-level + application validation | Defense in depth | Catches issues at source, multiple layers |
| Preventive only (constraints) | Preventive + detective (checks) | Modern data quality | Constraints prevent future issues, checks find existing ones |

**Deprecated/outdated:**
- **Storing check results in tables:** Modern approach is to run checks on-demand or in CI/CD, not store results. Monitoring tools (DataDog, New Relic) handle time-series storage.
- **DBMS_ASSERT for validation (Oracle):** PostgreSQL uses CHECK constraints and application validation instead
- **Trigger-based validation for read-only checks:** Triggers modify state; sanity checks should be SELECT-only

## Open Questions

Things that couldn't be fully resolved:

1. **Should checks return summary counts or full row details?**
   - What we know: Full row details are more actionable; summary counts are faster for large datasets
   - What's unclear: Production data volume - will checks return thousands of rows?
   - Recommendation: Start with full row details (ORDER BY + LIMIT if needed). Add COUNT(*) summary if output is overwhelming.

2. **Should checks.sql be executable as a transaction?**
   - What we know: Checks are read-only SELECT queries; no transaction needed
   - What's unclear: Whether to wrap in DO block for variable support
   - Recommendation: Keep simple - no transaction, no variables for Phase 2. Future enhancement can add DO block.

3. **How to handle checks that span multiple orgs in multi-tenant setup?**
   - What we know: RLS policies enforce org isolation; checks may need to bypass for admin
   - What's unclear: Whether checks should be org-scoped or global
   - Recommendation: Run checks globally (as admin/service role) to detect issues across all orgs. RLS prevents users from seeing other org data.

4. **Should zero allocations be flagged as an issue?**
   - What we know: Zero allocation is valid (vessel not participating in species)
   - What's unclear: Business rule - is zero allocation ever suspicious?
   - Recommendation: Don't flag zero allocations in Phase 2. Can add as separate check if requested.

## Sources

### Primary (HIGH confidence)
- [PostgreSQL Documentation: SELECT](https://www.postgresql.org/docs/current/sql-select.html) - Official query syntax
- [PostgreSQL Documentation: Data Types](https://www.postgresql.org/docs/current/datatype.html) - Integer, Date, Numeric types
- [PostgreSQL Documentation: Date/Time Functions](https://www.postgresql.org/docs/current/functions-datetime.html) - EXTRACT, CURRENT_DATE
- [PostgreSQL Documentation: Subquery Expressions](https://www.postgresql.org/docs/current/functions-subquery.html) - EXISTS, NOT EXISTS
- [PostgreSQL Documentation: UNION](https://www.postgresql.org/docs/current/queries-union.html) - UNION ALL for combining results
- Current codebase:
  - `sql/schema-v2-multi-tenant.sql` - Table structures (allocations, transfers, harvests, species)
  - `sql/migrations/013_add_quota_metrics.sql` - quota_metrics view from Phase 1
  - `sql/migrations/005_add_multi_tenant.sql` - VERIFICATION QUERIES pattern (lines 251-282)

### Secondary (MEDIUM confidence)
- [Data Quality Checks: Best Practices & Examples](https://www.pantomath.com/data-pipeline-automation/data-quality-checks) - General data quality patterns
- [PostgreSQL Data Integrity](https://www.dbvis.com/thetable/understanding-postgresql-data-integrity/) - Constraint types and validation
- [Ensuring Data Integrity in PostgreSQL with Check Constraints](https://www.navicat.com/en/company/aboutus/blog/2412-ensuring-data-integrity-in-postgresql-with-check-constraints.html) - CHECK constraint usage
- [Find Violating SQL Server Foreign Key Values](https://www.mssqltips.com/sqlservertip/2326/find-violating-sql-server-foreign-key-values/) - Foreign key validation patterns (SQL Server, applicable to Postgres)
- [PostgreSQL: Documentation: Application Level Consistency](https://www.postgresql.org/docs/current/applevel-consistency.html) - Consistency checks under MVCC

### Tertiary (LOW confidence)
- WebSearch: "PostgreSQL sanity check queries" - General patterns, not version-specific
- WebSearch: "SQL data validation best practices 2026" - Generic advice, not Postgres-specific

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PostgreSQL built-in functions; official documentation verified
- Architecture: HIGH - Patterns match existing migration verification queries in codebase
- Pitfalls: MEDIUM-HIGH - Soft-delete filtering and year comparison verified from schema; other pitfalls from PostgreSQL best practices

**Research date:** 2026-01-28
**Valid until:** 2026-04-28 (90 days) - SQL syntax stable; business rules unlikely to change. May need updates if schema changes (new tables, columns).
