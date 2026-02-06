# Phase 1: Derived Metrics - Research

**Researched:** 2026-01-28
**Domain:** PostgreSQL view design, calculated columns, division-by-zero handling
**Confidence:** HIGH

## Summary

This research investigated PostgreSQL best practices for creating derived metrics (calculated columns) in database views, specifically focusing on:
1. Division-by-zero handling using NULLIF
2. CASE expressions for categorical risk levels
3. View documentation using SQL COMMENT
4. Performance implications of views vs generated columns

The standard approach is to extend the existing `quota_remaining` view with calculated columns for `remaining_pct` and `risk_level`. PostgreSQL's NULLIF function is the idiomatic solution for safe division, and CASE expressions provide clean categorical column creation. This approach maintains the existing architecture pattern (views for derived data) while moving Python-based calculations to SQL.

**Primary recommendation:** Create a new `quota_metrics` view (or extend `quota_remaining`) using NULLIF for safe division, CASE for risk categorization, and NUMERIC type for percentage precision. Document the view with COMMENT ON VIEW to explain formulas and assumptions.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL | 15+ | Database with view support | Supabase uses modern Postgres; 15+ supports `security_invoker` for RLS-aware views |
| NUMERIC type | Built-in | Exact decimal arithmetic | Prevents floating-point errors in financial/quota calculations; recommended over FLOAT/REAL |

### Supporting
| Function | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| NULLIF() | Built-in | Division-by-zero prevention | Any division where denominator could be zero |
| CASE WHEN | Built-in | Categorical column creation | Converting continuous values to categories (risk levels, grades, etc.) |
| COMMENT ON | Built-in | Database object documentation | Documenting formulas, assumptions, and business logic |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| View with calculations | Generated STORED columns | Stored columns faster to read but slower to write; views more flexible for multi-table calculations |
| View with calculations | Generated VIRTUAL columns | Similar to views but limited to single-table, single-row, immutable functions only |
| NULLIF for div-by-zero | CASE WHEN denominator = 0 | CASE more verbose; NULLIF is idiomatic PostgreSQL |
| NUMERIC type | INTEGER (basis points) | Integer faster but requires multiply/divide by 100 everywhere; less readable |

**Installation:**
Built-in PostgreSQL features. No installation needed.

## Architecture Patterns

### Recommended Project Structure
Current schema already follows best practices:
```
sql/
├── schema-v2-multi-tenant.sql    # Main schema with views
├── migrations/                   # Incremental changes
    └── 00X_add_quota_metrics.sql # New migration for this phase
```

### Pattern 1: View Extension (Recommended)
**What:** Create new view that builds on existing `quota_remaining` view
**When to use:** When adding derived metrics to existing calculation
**Example:**
```sql
-- Source: PostgreSQL official docs + project schema analysis
CREATE OR REPLACE VIEW quota_metrics
WITH (security_invoker = true)  -- Respect RLS policies (Postgres 15+)
AS
SELECT
    qr.*,
    -- Percentage remaining (safe division)
    (qr.remaining_lbs / NULLIF(qr.allocation_lbs, 0) * 100) AS remaining_pct,
    -- Risk level categorical
    CASE
        WHEN qr.allocation_lbs = 0 THEN 'na'
        WHEN (qr.remaining_lbs / qr.allocation_lbs * 100) < 10 THEN 'critical'
        WHEN (qr.remaining_lbs / qr.allocation_lbs * 100) < 50 THEN 'warning'
        ELSE 'healthy'
    END AS risk_level
FROM quota_remaining qr;

COMMENT ON VIEW quota_metrics IS
'Derived metrics for quota tracking.
Formulas:
  - remaining_pct = (remaining_lbs / allocation_lbs) * 100
  - risk_level: critical (<10%), warning (<50%), healthy (>=50%), na (zero allocation)
Assumptions:
  - Zero allocations return NULL for percentage, "na" for risk_level
  - Based on quota_remaining view formula (see quota_remaining view comment)';

COMMENT ON VIEW quota_remaining IS
'Core quota calculation view.
Formula: remaining_lbs = allocation_lbs + transfers_in - transfers_out - harvested
Assumptions:
  - Only non-deleted transfers and harvests counted (is_deleted = false)
  - All amounts in pounds (lbs)
  - Harvests come from eLandings API only';
```

### Pattern 2: Inline View (Alternative)
**What:** Extend `quota_remaining` directly with calculated columns
**When to use:** When metrics are tightly coupled to base calculation
**Tradeoff:** Less modular; harder to version independently

### Anti-Patterns to Avoid

- **Nested views beyond 2 levels:** Layering views on views creates unmanageable dependency chains and performance issues. Flatten if depth exceeds 2.
  - Source: [Database Anti-patterns: Performance Killers](https://blog.rustprooflabs.com/2018/01/db-anti-pattern)

- **Using FLOAT/REAL for percentages:** Floating-point errors in quota calculations could cause compliance issues. Always use NUMERIC.
  - Source: [PostgreSQL Documentation: Numeric Types](https://www.postgresql.org/docs/current/datatype-numeric.html)

- **CASE without ELSE clause:** Always include ELSE to handle unexpected values explicitly.
  - Source: [PostgreSQL CASE: A Comprehensive Guide](https://www.dbvis.com/thetable/postgresql-case-a-comprehensive-guide/)

- **Dividing without NULLIF:** Will throw error 22012 "division by zero" and crash queries.
  - Source: [PostgreSQL division_by_zero Error Explained](https://www.getgalaxy.io/learn/common-errors/postgresql-division-by-zero-error-code-22012-explained-and-fixed)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Division by zero | Manual IF checks in Python | NULLIF() in SQL | NULLIF is database-native, idiomatic, and handles NULL propagation correctly |
| Risk categorization | Python functions | CASE WHEN in SQL | SQL categorization computed once per query; Python requires fetching data and looping |
| View documentation | README files | COMMENT ON VIEW | Comments stored in database, visible in psql \d+ and schema browsers, versioned with migrations |
| Percentage rounding | Python round() | PostgreSQL ROUND() | Consistent rounding rules across all queries; Python could round differently per view |

**Key insight:** Moving calculations to SQL reduces data transfer (computed server-side), ensures consistency across all queries (no Python version differences), and enables query optimizer to use metrics in WHERE/ORDER BY efficiently.

## Common Pitfalls

### Pitfall 1: Using Wrong View Security Model
**What goes wrong:** Views bypass RLS policies by default, exposing data across tenants
**Why it happens:** Views created by superuser run with SECURITY DEFINER (creator's permissions)
**How to avoid:** Use `WITH (security_invoker = true)` in Postgres 15+ to make view respect RLS
**Warning signs:** Multi-tenant app shows data from other organizations

**Code pattern:**
```sql
-- BAD: Bypasses RLS policies
CREATE OR REPLACE VIEW quota_metrics AS ...;

-- GOOD: Respects RLS policies (Postgres 15+)
CREATE OR REPLACE VIEW quota_metrics
WITH (security_invoker = true)
AS ...;
```
Source: [Supabase RLS Documentation](https://supabase.com/docs/guides/database/postgres/row-level-security)

### Pitfall 2: Division Order Causing Truncation
**What goes wrong:** `remaining_lbs / allocation_lbs * 100` can truncate to integer division
**Why it happens:** PostgreSQL integer division truncates; NUMERIC types required for fractional results
**How to avoid:** Ensure at least one operand is NUMERIC, or multiply before dividing
**Warning signs:** Percentages always whole numbers (95.0, not 95.3)

**Code pattern:**
```sql
-- RISKY: If both are INTEGER, division truncates before multiply
remaining_lbs / allocation_lbs * 100

-- SAFE: NULLIF returns NUMERIC; multiply happens after fractional division
remaining_lbs / NULLIF(allocation_lbs, 0) * 100

-- ALSO SAFE: Force NUMERIC cast
remaining_lbs::NUMERIC / allocation_lbs * 100
```

### Pitfall 3: CASE Conditions Not Mutually Exclusive
**What goes wrong:** Wrong category assigned when condition overlaps
**Why it happens:** CASE evaluates conditions in order, returns first match
**How to avoid:** Order conditions from most specific to least specific; test boundary values
**Warning signs:** 10% showing as "warning" instead of "critical"

**Code pattern:**
```sql
-- BAD: 10% matches first condition (< 50), returns 'warning'
CASE
    WHEN pct < 50 THEN 'warning'
    WHEN pct < 10 THEN 'critical'
    ELSE 'healthy'
END

-- GOOD: Most restrictive first
CASE
    WHEN pct < 10 THEN 'critical'
    WHEN pct < 50 THEN 'warning'
    ELSE 'healthy'
END
```

### Pitfall 4: CREATE OR REPLACE Changes Column Types
**What goes wrong:** Application breaks when view columns change type/order
**Why it happens:** `CREATE OR REPLACE VIEW` allows adding columns at end but not changing existing
**How to avoid:** Test that new view definition produces same column names, order, and types as old
**Warning signs:** "column X is type TEXT but expression is type INTEGER" errors

**Prevention:**
```sql
-- Before CREATE OR REPLACE, check existing view structure
\d+ quota_remaining

-- OR in migration, explicitly DROP then CREATE (forces intentional change)
DROP VIEW IF EXISTS quota_metrics;
CREATE VIEW quota_metrics AS ...;
```

### Pitfall 5: Not Handling NULL Allocations
**What goes wrong:** NULL allocations crash division or produce misleading percentages
**Why it happens:** NULLIF(0, 0) returns NULL; NULL in arithmetic produces NULL
**How to avoid:** Decide business rule for NULL allocations (treat as 0? exclude? flag as 'na'?)
**Warning signs:** Rows disappearing from results (NULL filtered by WHERE conditions)

**Code pattern:**
```sql
-- Returns NULL for 0 allocations (good for percentages)
remaining_lbs / NULLIF(allocation_lbs, 0) * 100

-- For risk_level, explicitly handle the 0 allocation case
CASE
    WHEN allocation_lbs = 0 THEN 'na'
    WHEN (remaining_lbs / allocation_lbs * 100) < 10 THEN 'critical'
    -- ... etc
END
```

## Code Examples

Verified patterns from official sources and current codebase:

### Safe Division with NULLIF
```sql
-- Source: PostgreSQL NULLIF documentation
-- Pattern: Divide by NULLIF(denominator, 0) to return NULL instead of error
SELECT
    numerator / NULLIF(denominator, 0) AS safe_division
FROM my_table;

-- In context of quota percentages:
SELECT
    remaining_lbs,
    allocation_lbs,
    remaining_lbs / NULLIF(allocation_lbs, 0) * 100 AS pct_remaining
FROM quota_remaining;
```

### Risk Level Categorization
```sql
-- Source: Current app/utils/formatting.py (lines 46-62) + PostgreSQL CASE docs
-- Python version (current):
def get_risk_level(pct) -> str:
    if pct is None:
        return "na"
    if pct < 10:
        return "critical"
    if pct < 50:
        return "warning"
    return "ok"

-- SQL equivalent:
CASE
    WHEN allocation_lbs = 0 THEN 'na'
    WHEN (remaining_lbs / NULLIF(allocation_lbs, 0) * 100) < 10 THEN 'critical'
    WHEN (remaining_lbs / NULLIF(allocation_lbs, 0) * 100) < 50 THEN 'warning'
    ELSE 'healthy'
END AS risk_level
```

### Complete quota_metrics View
```sql
-- Source: Synthesized from PostgreSQL docs + current schema patterns
CREATE OR REPLACE VIEW quota_metrics
WITH (security_invoker = true)
AS
SELECT
    qr.org_id,
    qr.llp,
    qr.species_code,
    qr.year,
    qr.allocation_lbs,
    qr.transfers_in,
    qr.transfers_out,
    qr.harvested,
    qr.remaining_lbs,

    -- METR-01: remaining_pct (safe division)
    ROUND(
        (qr.remaining_lbs / NULLIF(qr.allocation_lbs, 0) * 100)::NUMERIC,
        2
    ) AS remaining_pct,

    -- METR-02: risk_level categorical
    CASE
        WHEN qr.allocation_lbs = 0 THEN 'na'
        WHEN (qr.remaining_lbs / NULLIF(qr.allocation_lbs, 0) * 100) < 10 THEN 'critical'
        WHEN (qr.remaining_lbs / NULLIF(qr.allocation_lbs, 0) * 100) < 50 THEN 'warning'
        ELSE 'healthy'
    END AS risk_level

FROM quota_remaining qr;
```

### View Documentation Pattern
```sql
-- Source: PostgreSQL COMMENT ON documentation + current schema patterns (sql/migrations/012_bycatch_hauls.sql)
COMMENT ON VIEW quota_metrics IS
'Derived metrics for quota tracking and risk assessment.

Formulas:
  - remaining_pct = (remaining_lbs / allocation_lbs) * 100, rounded to 2 decimals
  - risk_level: critical (<10%), warning (<50%), healthy (>=50%), na (zero allocation)

Assumptions:
  - Zero allocations return NULL for remaining_pct, "na" for risk_level
  - Percentages can exceed 100% (over-allocation via transfers)
  - Based on quota_remaining view; inherits its transaction filters (is_deleted = false)

Dependencies:
  - quota_remaining view (allocations, transfers, harvests)

RLS: Uses security_invoker=true to respect org_id policies from underlying tables.';
```

### Updating Python Code to Use New Columns
```python
# Source: Current app/views/dashboard.py (lines 52-58)
# BEFORE (Python calculation):
df["pct_remaining"] = df.apply(
    lambda row: (row["remaining_lbs"] / row["allocation_lbs"] * 100)
    if row["allocation_lbs"] > 0 else None,
    axis=1
)

# AFTER (use SQL column):
# Query quota_metrics instead of quota_remaining
response = supabase.table("quota_metrics").select("*").eq("year", year).execute()
# pct_remaining and risk_level already included in response.data
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python calculations on fetched data | SQL derived columns in views | Postgres 12+ (generated cols), 15+ (security_invoker) | Reduces data transfer, enables SQL filtering/sorting on metrics |
| CASE or IF for div-by-zero | NULLIF() function | Always available, but newly standard | Cleaner, more idiomatic SQL |
| Comments in migration files | COMMENT ON database objects | Always available, newly emphasized | Self-documenting schema; visible in tools |
| Views run as SECURITY DEFINER | Views with security_invoker=true | Postgres 15 (Sep 2022) | Views now respect RLS; critical for multi-tenancy |

**Deprecated/outdated:**
- Generated VIRTUAL columns (Postgres 14+): Exist but limited to single-table, immutable functions. Views more flexible for multi-table calculations like quota_remaining.
- Storing percentages as separate columns in base tables: Violates normalization; derived values should be in views or generated columns.

## Open Questions

Things that couldn't be fully resolved:

1. **Should risk_level match Python's "ok" or use "healthy"?**
   - What we know: Python code uses "ok", but SQL convention often uses positive terms like "healthy", "good", "safe"
   - What's unclear: User expectations and UI compatibility
   - Recommendation: Use "ok" to match existing Python for seamless migration; can rename later if needed

2. **Should quota_metrics be a separate view or extend quota_remaining?**
   - What we know: Separate view is more modular; extending quota_remaining keeps all quota data in one place
   - What's unclear: Future feature needs (other metrics, other views depending on quota_remaining)
   - Recommendation: Create separate `quota_metrics` view to avoid breaking existing queries to `quota_remaining`

3. **What Supabase/Postgres version is production using?**
   - What we know: Schema uses modern syntax; security_invoker supported in 15+
   - What's unclear: Exact production version
   - Recommendation: Assume Postgres 15+; Supabase defaults to modern versions. Add version check in migration if critical.

## Sources

### Primary (HIGH confidence)
- [PostgreSQL Documentation: COMMENT ON](https://www.postgresql.org/docs/current/sql-comment.html) - Official syntax and semantics
- [PostgreSQL Documentation: Conditional Expressions](https://www.postgresql.org/docs/current/functions-conditional.html) - NULLIF and CASE functions
- [PostgreSQL Documentation: Numeric Types](https://www.postgresql.org/docs/current/datatype-numeric.html) - NUMERIC vs DECIMAL vs FLOAT
- [PostgreSQL Documentation: Generated Columns](https://www.postgresql.org/docs/current/ddl-generated-columns.html) - Alternative to views
- [Supabase RLS Documentation](https://supabase.com/docs/guides/database/postgres/row-level-security) - security_invoker for views
- Current codebase:
  - `sql/schema-v2-multi-tenant.sql` (lines 252-284) - quota_remaining view
  - `app/utils/formatting.py` (lines 46-62) - get_risk_level() logic
  - `sql/migrations/012_bycatch_hauls.sql` (lines 181-186) - COMMENT ON pattern

### Secondary (MEDIUM confidence)
- [GeeksforGeeks: Division by Zero in PostgreSQL](https://www.geeksforgeeks.org/postgresql/how-to-avoid-division-by-zero-in-postgresql/) - NULLIF pattern
- [Neon Docs: PostgreSQL NULLIF](https://neon.com/postgresql/postgresql-tutorial/postgresql-nullif) - Examples
- [DataCamp: PostgreSQL CASE Statements](https://www.datacamp.com/tutorial/case-statements-in-postgresql) - Best practices
- [RustProof Labs: Database Anti-patterns](https://blog.rustprooflabs.com/2018/01/db-anti-pattern) - Nested views warning
- [Crunchy Data: Choosing a PostgreSQL Number Format](https://www.crunchydata.com/blog/choosing-a-postgresql-number-format) - NUMERIC recommendations

### Tertiary (LOW confidence)
- WebSearch: "PostgreSQL view performance" - General guidance, not version-specific
- WebSearch: "SQL metrics layer design patterns" - Conceptual, not Postgres-specific

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PostgreSQL built-in functions; official documentation verified
- Architecture: HIGH - View extension pattern standard in PostgreSQL; existing schema follows best practices
- Pitfalls: MEDIUM-HIGH - Division by zero and security_invoker verified from official docs; other pitfalls from credible sources

**Research date:** 2026-01-28
**Valid until:** 2026-03-28 (60 days) - PostgreSQL stable; syntax unlikely to change. Supabase may update default Postgres version.
