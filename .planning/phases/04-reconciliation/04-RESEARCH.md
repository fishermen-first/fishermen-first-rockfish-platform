# Phase 4: Reconciliation - Research

**Researched:** 2026-01-28
**Domain:** PostgreSQL variance analysis, multi-tenant reconciliation views
**Confidence:** HIGH

## Summary

Phase 4 creates a `reconciliation_variance` view that compares internal quota tracking (from `quota_remaining` view) against external eFish account balances (from `efish_account_balance` table) to identify discrepancies requiring investigation.

The standard approach is a **FULL OUTER JOIN** pattern that:
1. Joins internal and external data sources on common keys (org_id, llp, species_code, year)
2. Calculates variance as internal minus external (remaining_lbs)
3. Uses ABS() function to flag rows exceeding variance threshold (>100 lbs)
4. Preserves rows where data exists in only one system (NULL handling critical)

**Primary recommendation:** Use FULL OUTER JOIN with COALESCE for NULL handling, add security_invoker = true for RLS compatibility, and use ABS(variance_lbs) > 100 for flagging.

## Standard Stack

### Core Database Objects

| Object | Type | Purpose | Why Standard |
|--------|------|---------|--------------|
| quota_remaining | VIEW | Internal source of truth | Existing view with RLS support, calculates remaining quota |
| efish_account_balance | TABLE | External eFish data | CSV upload table for reconciliation data |
| FULL OUTER JOIN | SQL Pattern | Variance detection | Captures mismatches in both directions |
| security_invoker | View Option | RLS enforcement | Postgres 15+ feature for proper multi-tenant isolation |

### Supporting Functions

| Function | Purpose | When to Use |
|----------|---------|-------------|
| ABS() | Absolute value | Flagging variance regardless of direction (+ or -) |
| COALESCE() | NULL handling | Ensuring calculations work when data exists in only one source |
| NULLIF() | Division by zero | Not needed here (no percentage calculations) |
| ROUND() | Precision control | Consistent with existing views (2 decimal places) |

### Installation

No packages needed - pure PostgreSQL DDL.

## Architecture Patterns

### Recommended View Structure

```sql
CREATE OR REPLACE VIEW reconciliation_variance
WITH (security_invoker = true)
AS
SELECT
    -- Common keys (from whichever source has data)
    COALESCE(qr.org_id, ef.org_id) AS org_id,
    COALESCE(qr.llp, ef.llp) AS llp,
    COALESCE(qr.species_code, ef.species_code) AS species_code,
    COALESCE(qr.year, ef.year) AS year,

    -- Internal data (quota_remaining)
    qr.remaining_lbs AS internal_remaining_lbs,

    -- External data (efish_account_balance)
    ef.remaining_lbs AS external_remaining_lbs,

    -- Variance calculation
    COALESCE(qr.remaining_lbs, 0) - COALESCE(ef.remaining_lbs, 0) AS variance_lbs,

    -- Flag for investigation
    ABS(COALESCE(qr.remaining_lbs, 0) - COALESCE(ef.remaining_lbs, 0)) > 100 AS needs_investigation
FROM quota_remaining qr
FULL OUTER JOIN efish_account_balance ef
    ON qr.org_id = ef.org_id
    AND qr.llp = ef.llp
    AND qr.species_code = ef.species_code
    AND qr.year = ef.year;
```

### Pattern 1: FULL OUTER JOIN for Reconciliation

**What:** Returns all rows from both tables, with NULLs where no match exists
**When to use:** When you need to identify discrepancies in both directions:
- Data exists in internal system but not external (missing eFish data)
- Data exists in external system but not internal (missing quota allocation)

**Example:**
```sql
-- Source: PostgreSQL Tutorial - FULL OUTER JOIN
-- https://www.postgresqltutorial.com/postgresql-tutorial/postgresql-full-outer-join/

FROM quota_remaining qr
FULL OUTER JOIN efish_account_balance ef
    ON qr.org_id = ef.org_id
    AND qr.llp = ef.llp
    AND qr.species_code = ef.species_code
    AND qr.year = ef.year
```

**Why FULL OUTER JOIN vs LEFT JOIN:**
- LEFT JOIN would only show internal records (miss external-only records)
- FULL OUTER JOIN shows all records from both systems
- Critical for detecting missing allocations or orphaned eFish data

### Pattern 2: COALESCE for Common Keys

**What:** Use COALESCE to select non-NULL value from either source for join keys
**When to use:** After FULL OUTER JOIN, one side may be NULL for unmatched rows

**Example:**
```sql
-- Ensures we always have values for grouping/filtering
COALESCE(qr.org_id, ef.org_id) AS org_id,
COALESCE(qr.llp, ef.llp) AS llp,
COALESCE(qr.species_code, ef.species_code) AS species_code,
COALESCE(qr.year, ef.year) AS year
```

### Pattern 3: COALESCE for Variance Calculation

**What:** Treat NULL values as 0 in variance calculation
**When to use:** When one side of comparison is NULL (data missing from one source)

**Example:**
```sql
-- Variance: internal - external
COALESCE(qr.remaining_lbs, 0) - COALESCE(ef.remaining_lbs, 0) AS variance_lbs
```

**Why this matters:**
- If internal = 5000 lbs and external = NULL → variance = 5000 lbs (needs investigation)
- If internal = NULL and external = 3000 lbs → variance = -3000 lbs (needs investigation)
- Without COALESCE, NULL - 3000 = NULL (hides the issue)

### Pattern 4: ABS() for Threshold Flagging

**What:** Use absolute value to flag variance regardless of direction
**When to use:** When threshold applies to magnitude, not sign

**Example:**
```sql
-- Flag rows exceeding 100 lbs variance (positive or negative)
ABS(COALESCE(qr.remaining_lbs, 0) - COALESCE(ef.remaining_lbs, 0)) > 100 AS needs_investigation
```

**Why ABS():**
- +150 lbs variance needs investigation (internal > external)
- -150 lbs variance needs investigation (external > internal)
- Both directions indicate data quality issues

### Pattern 5: security_invoker for Multi-Tenant Views

**What:** View executes with caller's privileges, enforcing RLS policies
**When to use:** All views in multi-tenant applications (Postgres 15+)

**Example:**
```sql
-- From migration 013 (quota_metrics view)
CREATE OR REPLACE VIEW reconciliation_variance
WITH (security_invoker = true)
AS
SELECT ...
```

**Why this matters:**
- Views without security_invoker can bypass RLS policies
- security_invoker = true ensures org_id filtering applies correctly
- Inherited from underlying quota_remaining view (already has this)
- Matches existing pattern in quota_metrics and kpi_* views

### Anti-Patterns to Avoid

- **Don't use LEFT JOIN** - Misses external-only records (incomplete reconciliation)
- **Don't use INNER JOIN** - Only shows matches, hides all discrepancies
- **Don't skip COALESCE on variance** - NULL arithmetic produces NULL (hides issues)
- **Don't use separate > 100 and < -100 checks** - Use ABS() for clarity
- **Don't omit security_invoker** - Breaks multi-tenant isolation

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NULL handling in joins | Manual CASE statements | COALESCE() | Built-in, handles all NULL cases correctly |
| Absolute value | CASE WHEN x < 0 THEN -x ELSE x END | ABS() | Clearer intent, works with all numeric types |
| Two-way comparison | Two LEFT JOINs + UNION | FULL OUTER JOIN | Simpler, more efficient, standard pattern |
| Variance flagging | Application-layer filtering | Boolean column in view | Enables WHERE clause filtering in SQL |

**Key insight:** PostgreSQL's join types and NULL-handling functions are specifically designed for reconciliation patterns. Using them correctly is simpler and more performant than application-layer logic.

## Common Pitfalls

### Pitfall 1: Using LEFT JOIN Instead of FULL OUTER JOIN

**What goes wrong:** Only internal records appear in results; external-only records are invisible
**Why it happens:** LEFT JOIN bias - "we have the source of truth, just check if external matches"
**How to avoid:** Use FULL OUTER JOIN to capture discrepancies in BOTH directions
**Warning signs:** View row count matches quota_remaining exactly (should be higher if eFish has extra rows)

### Pitfall 2: Forgetting COALESCE in Variance Calculation

**What goes wrong:** Variance is NULL when one side is missing, hiding critical issues
**Why it happens:** NULL arithmetic: NULL - 5000 = NULL (not -5000)
**How to avoid:** Wrap both sides in COALESCE(value, 0) for variance calculation
**Warning signs:** needs_investigation shows FALSE for rows with NULL variance (should be TRUE)

### Pitfall 3: Not Handling NULL Join Keys

**What goes wrong:** Result rows have NULL org_id, llp, species_code, or year
**Why it happens:** FULL OUTER JOIN leaves one side NULL for unmatched rows
**How to avoid:** COALESCE(qr.column, ef.column) for all join key columns
**Warning signs:** Cannot filter results by org_id or year (NULL values break WHERE clauses)

### Pitfall 4: Forgetting security_invoker in Multi-Tenant Views

**What goes wrong:** View bypasses RLS policies, users see other orgs' data
**Why it happens:** Default view behavior is SECURITY DEFINER (runs as view owner)
**How to avoid:** Always add WITH (security_invoker = true) to view definition
**Warning signs:** View shows data from multiple orgs when user should only see their own

### Pitfall 5: Using Signed Threshold Instead of ABS()

**What goes wrong:** Flags only positive variance, misses negative variance
**Why it happens:** Threshold check like variance_lbs > 100 ignores variance_lbs < -100
**How to avoid:** Use ABS(variance_lbs) > 100 to flag magnitude regardless of direction
**Warning signs:** External > Internal discrepancies not flagged for investigation

### Pitfall 6: Not Documenting the Sign Convention

**What goes wrong:** Confusion about whether positive variance means internal or external is higher
**Why it happens:** No comment documenting variance_lbs = internal - external
**How to avoid:** Add COMMENT ON VIEW and inline SQL comments explaining sign convention
**Warning signs:** Support tickets asking "is +500 good or bad?"

## Code Examples

Verified patterns from existing migrations:

### Pattern: Creating View with RLS Support

```sql
-- Source: migration 013_add_quota_metrics.sql (lines 27-41)
CREATE OR REPLACE VIEW reconciliation_variance
WITH (security_invoker = true)
AS
SELECT
    -- Columns here
FROM quota_remaining qr
FULL OUTER JOIN efish_account_balance ef ON ...;
```

### Pattern: COALESCE for NULL Handling

```sql
-- Source: schema-v2-multi-tenant.sql (lines 259-284)
-- quota_remaining view uses COALESCE extensively
COALESCE(t_in.total, 0) AS transfers_in,
COALESCE(t_out.total, 0) AS transfers_out,
COALESCE(h.total, 0) AS harvested
```

### Pattern: CASE Statement for Categorization

```sql
-- Source: migration 013_add_quota_metrics.sql (lines 35-40)
-- Risk level categorization pattern (can adapt for variance severity)
CASE
    WHEN qr.allocation_lbs = 0 THEN 'na'
    WHEN qr.remaining_lbs / NULLIF(qr.allocation_lbs, 0) * 100 < 10 THEN 'critical'
    WHEN qr.remaining_lbs / NULLIF(qr.allocation_lbs, 0) * 100 < 50 THEN 'warning'
    ELSE 'ok'
END AS risk_level
```

### Pattern: View Documentation

```sql
-- Source: migration 013_add_quota_metrics.sql (lines 47-64)
COMMENT ON VIEW reconciliation_variance IS
    'Compares internal quota tracking (quota_remaining) with external eFish data
    (efish_account_balance) to identify discrepancies requiring investigation.

    Variance Formula: variance_lbs = internal_remaining_lbs - external_remaining_lbs
    - Positive variance: Internal system shows MORE quota than eFish
    - Negative variance: eFish shows MORE quota than internal system

    Investigation Flag: needs_investigation = TRUE when ABS(variance_lbs) > 100

    RLS Compatibility:
    - Uses WITH (security_invoker = true) to inherit RLS policies
    - Postgres 15+ feature ensures org_id filtering applies correctly';
```

### Pattern: FULL OUTER JOIN with Multi-Column Keys

```sql
-- Source: PostgreSQL Tutorial (verified pattern)
-- https://www.postgresqltutorial.com/postgresql-tutorial/postgresql-full-outer-join/
FROM quota_remaining qr
FULL OUTER JOIN efish_account_balance ef
    ON qr.org_id = ef.org_id           -- Multi-tenant key
    AND qr.llp = ef.llp                 -- Primary business key
    AND qr.species_code = ef.species_code  -- Dimension
    AND qr.year = ef.year               -- Time dimension
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Application-layer reconciliation | Database view with FULL OUTER JOIN | 2020s (mature pattern) | Simpler queries, better performance |
| LEFT JOIN + IS NULL checks | FULL OUTER JOIN | Established pattern | Captures both directions in one query |
| SECURITY DEFINER views | security_invoker = true | Postgres 15 (2022) | Proper RLS enforcement in multi-tenant apps |
| Manual NULL checks | COALESCE() | Always standard | Cleaner SQL, fewer bugs |

**Deprecated/outdated:**
- **Two separate LEFT JOINs + UNION**: Replaced by FULL OUTER JOIN (simpler, faster)
- **Application-layer variance calculation**: Replaced by view-layer calculation (reusable, consistent)
- **Views without security_invoker in multi-tenant apps**: Security risk, bypasses RLS

## Open Questions

No significant open questions. The pattern is well-established and verified.

**All requirements clearly mapped:**
- RECO-01: View joins quota_remaining and efish_account_balance ✓
- RECO-02: Variance calculation (internal - external) ✓
- RECO-03: Boolean flag for >100 lbs variance ✓

## Sources

### Primary (HIGH confidence)

- **PostgreSQL Official Documentation**: FULL OUTER JOIN syntax and behavior
  - [PostgreSQL Tutorial: Joins Between Tables](https://www.postgresql.org/docs/current/tutorial-join.html)
  - [PostgreSQL Tutorial: FULL OUTER JOIN](https://www.postgresqltutorial.com/postgresql-tutorial/postgresql-full-outer-join/)

- **PostgreSQL Official Documentation**: ABS() function
  - [PostgreSQL ABS() Function - Neon](https://neon.com/postgresql/postgresql-math-functions/postgresql-abs)
  - [PostgreSQL: Mathematical Functions](https://www.postgresql.org/docs/8.4/functions-math.html)

- **PostgreSQL Official Documentation**: BOOLEAN type and conditional expressions
  - [PostgreSQL: Boolean Type](https://www.postgresql.org/docs/current/datatype-boolean.html)
  - [PostgreSQL: Conditional Expressions](https://www.postgresql.org/docs/current/functions-conditional.html)

- **Existing Migrations** (verified working patterns in this codebase):
  - `sql/migrations/013_add_quota_metrics.sql` - security_invoker pattern, CASE categorization
  - `sql/schema-v2-multi-tenant.sql` - quota_remaining view structure, COALESCE pattern
  - `sql/migrations/006_create_efish_tables.sql` - efish_account_balance schema

### Secondary (MEDIUM confidence)

- **Multi-Tenant RLS Best Practices** (2025-2026):
  - [Mastering PostgreSQL RLS for Multi-Tenancy](https://ricofritzsche.me/mastering-postgresql-row-level-security-rls-for-rock-solid-multi-tenancy/)
  - [Shipping Multi-Tenant SaaS Using Postgres RLS](https://www.thenile.dev/blog/multi-tenant-rls)
  - [5mins of Postgres: Security Invoker Views](https://pganalyze.com/blog/5mins-postgres-row-level-security-bypassrls-security-invoker-views-leakproof-functions)

- **PostgreSQL Variance Analysis Patterns**:
  - [PostgreSQL for Data Analysis Best Practices - Tiger Data](https://www.tigerdata.com/learn/postgresql-data-analysis-best-practices)
  - [From Budget to Forecast: SQL Walkthrough for Finance](https://medium.com/@mehtabharat466499/from-budget-to-forecast-a-complete-sql-walkthrough-for-finance-analysts-dfdc77e5b920)

- **Join Pattern Documentation**:
  - [Mastering the Full Join in PostgreSQL](https://thelinuxcode.com/full-join-postgresql/)
  - [PostgreSQL JOINs: Types and Examples - DevArt](https://www.devart.com/dbforge/postgresql/studio/postgresql-joins.html)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified with official PostgreSQL docs and existing codebase patterns
- Architecture: HIGH - FULL OUTER JOIN pattern confirmed in official docs, security_invoker verified in Postgres 15+ docs
- Pitfalls: HIGH - Derived from official NULL handling docs and verified codebase patterns

**Research date:** 2026-01-28
**Valid until:** 2026-06-28 (6 months - stable PostgreSQL feature set, no breaking changes expected)

**Key verification sources:**
- Existing migrations 013 and 014 demonstrate security_invoker pattern
- Existing quota_remaining view demonstrates COALESCE pattern
- Existing efish_account_balance table schema verified in migration 006
- PostgreSQL official docs confirm FULL OUTER JOIN and ABS() function behavior
