# Phase 3: Serving Views - Research

**Researched:** 2026-01-28
**Domain:** PostgreSQL aggregation views, dashboard-ready data layers, multi-tenant RLS
**Confidence:** HIGH

## Summary

This research investigated PostgreSQL best practices for creating "serving views" - aggregated, dashboard-ready views that pre-compute expensive GROUP BY operations for UI consumption. The focus is on two specific views required for the Rockfish quota tracking dashboard:

1. **kpi_daily_by_species**: Time-series harvest data grouped by date and species
2. **kpi_coop_summary**: Cooperative-level quota metrics with risk counts

The standard approach is to create SQL views with GROUP BY aggregations, leveraging PostgreSQL's FILTER clause for conditional counting, DATE_TRUNC for date grouping, and security_invoker for RLS compatibility. These views serve as a data API contract between PostgreSQL and the Streamlit dashboard, separating concerns and enabling potential BI tool integration later.

The research identified critical patterns for multi-tenant aggregations (respecting org_id via RLS), performance considerations (indexing strategies, materialized views), and conditional aggregation techniques (COUNT FILTER for risk level counts).

**Primary recommendation:** Create two regular (non-materialized) views in a new migration file (014_add_serving_views.sql) using security_invoker = true for RLS inheritance. Use COUNT FILTER for conditional aggregations, DATE_TRUNC for date grouping, and JOIN to coop_members for coop_code. Document formulas and assumptions with COMMENT ON VIEW.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL | 15+ | Database with security_invoker views | Supabase uses Postgres 15+; security_invoker enables RLS-aware views |
| Regular Views | Built-in | Pre-defined query abstractions | Sufficient for current data volume; easier to maintain than materialized views |
| GROUP BY | Built-in | Data aggregation by dimensions | Standard SQL aggregation mechanism |

### Supporting
| Function/Feature | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| COUNT() FILTER (WHERE ...) | Postgres 9.4+ | Conditional aggregation | Counting rows meeting specific criteria (e.g., critical_count) |
| DATE_TRUNC('day', date) | Built-in | Date grouping by day | Aggregating time-series data by date |
| COALESCE() | Built-in | NULL handling in aggregates | Ensuring predictable output (e.g., 0 instead of NULL for counts) |
| security_invoker = true | Postgres 15+ | RLS policy inheritance | Multi-tenant views that respect org_id filtering |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Regular views | Materialized views | Materialized faster to read but require REFRESH; premature optimization for current data volume |
| DATE_TRUNC | EXTRACT(YEAR/MONTH/DAY) | DATE_TRUNC preserves date type, works better with indexes and time-series queries |
| COUNT FILTER | SUM(CASE WHEN...) | CASE more verbose; FILTER is cleaner, more readable, similar performance |
| Views | Application-level aggregation | SQL aggregation leverages indexes, reduces data transfer, enables BI tools |
| JOIN to coop_members | Denormalized coop_code | Join maintains normalization; coop_code rarely changes but view is flexible |

**Installation:**
Built-in PostgreSQL features. No installation needed.

## Architecture Patterns

### Recommended Project Structure
```
sql/
├── schema-v2-multi-tenant.sql        # Main schema
├── migrations/
│   ├── 013_add_quota_metrics.sql    # Phase 1 output
│   └── 014_add_serving_views.sql    # NEW: Phase 3 output
```

### Pattern 1: Time-Series Aggregation View
**What:** Aggregate transaction data by date and dimension (species)
**When to use:** Dashboard time-series charts, daily trends
**Example:**
```sql
-- Source: PostgreSQL aggregation best practices + project requirements
CREATE OR REPLACE VIEW kpi_daily_by_species
WITH (security_invoker = true)
AS
SELECT
    org_id,
    DATE_TRUNC('day', harvest_date) AS harvest_day,
    species_code,
    SUM(pounds) AS total_harvested_lbs,
    COUNT(*) AS harvest_count
FROM harvests
WHERE is_deleted = FALSE
GROUP BY org_id, DATE_TRUNC('day', harvest_date), species_code
ORDER BY harvest_day DESC, species_code;

COMMENT ON VIEW kpi_daily_by_species IS
'Daily harvest totals aggregated by species for KPI dashboard.

Columns:
  - org_id: Organization identifier (for RLS filtering)
  - harvest_day: Date of harvest (truncated to day, no time component)
  - species_code: Species identifier (141=POP, 136=NR, 172=Dusky, etc.)
  - total_harvested_lbs: Sum of pounds harvested that day for that species
  - harvest_count: Number of harvest records (for data quality monitoring)

Filters:
  - Only non-deleted harvests (is_deleted = FALSE)

RLS Compatibility:
  - Uses WITH (security_invoker = true) to inherit RLS policies from harvests table
  - org_id filtering applies automatically based on user permissions

Performance:
  - Regular view (not materialized) sufficient for current data volume
  - If performance degrades, consider: (1) materialized view with scheduled refresh,
    (2) expression index on DATE_TRUNC(harvest_date), (3) BRIN index on harvest_date';
```

### Pattern 2: Cooperative-Level Summary View
**What:** Aggregate quota metrics by cooperative with risk level counts
**When to use:** Dashboard summary cards, coop-level reporting
**Example:**
```sql
-- Source: PostgreSQL FILTER clause best practices + project requirements
CREATE OR REPLACE VIEW kpi_coop_summary
WITH (security_invoker = true)
AS
SELECT
    qm.org_id,
    cm.coop_code,
    qm.species_code,
    qm.year,
    -- Aggregated quota metrics
    SUM(qm.allocation_lbs) AS total_allocation_lbs,
    SUM(qm.transfers_in) AS total_transfers_in,
    SUM(qm.transfers_out) AS total_transfers_out,
    SUM(qm.harvested) AS total_harvested,
    SUM(qm.remaining_lbs) AS total_remaining_lbs,
    -- Calculated percentage (handle division by zero)
    ROUND((SUM(qm.remaining_lbs) / NULLIF(SUM(qm.allocation_lbs), 0) * 100)::NUMERIC, 2) AS remaining_pct,
    -- Risk level counts (conditional aggregation)
    COUNT(*) FILTER (WHERE qm.risk_level = 'critical') AS critical_count,
    COUNT(*) FILTER (WHERE qm.risk_level = 'warning') AS warning_count,
    COUNT(*) FILTER (WHERE qm.risk_level = 'ok') AS ok_count,
    COUNT(*) FILTER (WHERE qm.risk_level = 'na') AS na_count,
    -- Vessel counts
    COUNT(DISTINCT qm.llp) AS vessel_count
FROM quota_metrics qm
JOIN coop_members cm ON qm.llp = cm.llp AND qm.org_id = cm.org_id
GROUP BY qm.org_id, cm.coop_code, qm.species_code, qm.year
ORDER BY cm.coop_code, qm.species_code;

COMMENT ON VIEW kpi_coop_summary IS
'Cooperative-level quota summary with risk counts for dashboard KPI cards.

Aggregation Level: coop_code, species_code, year

Columns:
  - org_id: Organization identifier (for RLS filtering)
  - coop_code: Cooperative identifier (SBS, NP, OBSI, SOK)
  - species_code: Species identifier
  - year: Fishing year
  - total_allocation_lbs: Sum of all vessel allocations in this coop/species/year
  - total_transfers_in/out: Sum of quota transfers
  - total_harvested: Sum of harvested pounds
  - total_remaining_lbs: Sum of remaining quota across all vessels
  - remaining_pct: Percentage of original allocation remaining (coop-wide)
  - critical_count: Number of vessels at critical risk (<10% remaining)
  - warning_count: Number of vessels at warning level (10-50% remaining)
  - ok_count: Number of vessels at healthy level (>=50% remaining)
  - na_count: Number of vessels with zero allocation
  - vessel_count: Total vessels in this coop/species/year

Dependencies:
  - quota_metrics view (Phase 1) - provides remaining_lbs and risk_level
  - coop_members table - maps LLPs to cooperatives

RLS Compatibility:
  - Uses WITH (security_invoker = true) to inherit RLS policies
  - org_id filtering applies automatically via quota_metrics and coop_members

Use Cases:
  - Dashboard summary cards: "3 vessels at critical risk in SBS POP"
  - Coop-level reporting and alerts
  - Executive summaries';
```

### Pattern 3: Security Invoker for Multi-Tenancy
**What:** Views that inherit RLS policies from underlying tables
**When to use:** Always in multi-tenant systems with org_id isolation
**Why important:** Without security_invoker, views execute with owner privileges, potentially bypassing RLS
**Example:**
```sql
-- CORRECT: Respects RLS policies
CREATE OR REPLACE VIEW my_view
WITH (security_invoker = true)
AS SELECT ...;

-- INCORRECT: Bypasses RLS (uses view owner's permissions)
CREATE OR REPLACE VIEW my_view
AS SELECT ...;
```

### Anti-Patterns to Avoid

1. **Aggregating Without Filtering Soft Deletes**
   - **Wrong:** `SELECT COUNT(*) FROM harvests GROUP BY ...`
   - **Right:** `SELECT COUNT(*) FROM harvests WHERE is_deleted = FALSE GROUP BY ...`
   - **Why:** Soft-deleted records should be excluded from all calculations

2. **Using SELECT * in Views**
   - **Wrong:** `CREATE VIEW v AS SELECT * FROM table JOIN ...`
   - **Right:** Explicitly list columns for clarity and stability
   - **Why:** Schema changes break views; explicit columns are self-documenting

3. **Missing NULL Handling in Aggregates**
   - **Wrong:** `SUM(remaining_lbs) / SUM(allocation_lbs)`
   - **Right:** `SUM(remaining_lbs) / NULLIF(SUM(allocation_lbs), 0)`
   - **Why:** Division by zero returns error; NULLIF returns NULL safely

4. **Forgetting org_id in GROUP BY**
   - **Wrong:** `GROUP BY coop_code, species_code`
   - **Right:** `GROUP BY org_id, coop_code, species_code`
   - **Why:** Multi-tenant aggregations must respect org boundaries

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Conditional counting | CASE WHEN + SUM | COUNT FILTER (WHERE ...) | FILTER clause is cleaner, more readable, PostgreSQL-native since 9.4 |
| Date grouping | EXTRACT + string concat | DATE_TRUNC('day', date) | DATE_TRUNC preserves date type, works with indexes, standard for time-series |
| Multi-table aggregation | Application-level joins + aggregation | SQL views with JOIN + GROUP BY | Database engines optimize joins/aggregates better than app code |
| Caching aggregate results | Redis/Memcached for view results | Materialized views (if needed) | PostgreSQL native, transactional, simpler operational model |
| Risk level categorization in Python | if/elif chains in dashboard code | Use risk_level column from quota_metrics | Single source of truth, consistency across tools |

**Key insight:** PostgreSQL's aggregate functions, FILTER clause, and view system provide powerful abstractions for serving layers. Building custom aggregation logic in application code duplicates database capabilities, introduces consistency issues (different tools calculate differently), and misses opportunities for query optimization.

## Common Pitfalls

### Pitfall 1: Materialized View Premature Optimization
**What goes wrong:** Creating materialized views before confirming performance issues
**Why it happens:** Assumption that "aggregates = slow, must materialize"
**How to avoid:** Start with regular views; only materialize if query time exceeds threshold (e.g., >2 seconds)
**Warning signs:** Need for manual REFRESH commands, stale data complaints, increased maintenance complexity
**Fix:** Regular views are sufficient for small-to-medium data (46 vessels × 3 species × 1 year = 138 rows in quota_metrics)

### Pitfall 2: Missing DATE_TRUNC Index
**What goes wrong:** DATE_TRUNC-based views perform full table scans
**Why it happens:** Regular indexes on raw date columns don't help DATE_TRUNC queries
**How to avoid:** Create expression index: `CREATE INDEX idx_harvests_day ON harvests (DATE_TRUNC('day', harvest_date));`
**Warning signs:** EXPLAIN shows Seq Scan on large harvests table, query time grows linearly with rows
**Fix:** Add expression index matching the DATE_TRUNC in the view's GROUP BY

### Pitfall 3: Forgetting security_invoker in Multi-Tenant Views
**What goes wrong:** Views bypass RLS policies, exposing other organizations' data
**Why it happens:** Postgres defaults to security_definer (owner's permissions)
**How to avoid:** Always use `WITH (security_invoker = true)` in multi-tenant views
**Warning signs:** Users see data from other organizations, RLS tests fail for views
**Fix:** `ALTER VIEW view_name SET (security_invoker = true);`

### Pitfall 4: COUNT(*) vs COUNT(column) Confusion
**What goes wrong:** Unexpected counts due to NULL handling differences
**Why it happens:** COUNT(column) ignores NULLs; COUNT(*) counts all rows
**How to avoid:** Use COUNT(*) for row counts, COUNT(column) only when intentionally filtering NULLs
**Warning signs:** Counts don't match expected totals, discrepancies vs manual queries
**Example:**
```sql
-- WRONG: Might miss vessels with NULL coop_code
COUNT(coop_code)

-- RIGHT: Counts all vessels
COUNT(*)

-- ALSO RIGHT: Explicit NULL filtering
COUNT(CASE WHEN coop_code IS NOT NULL THEN 1 END)
```

### Pitfall 5: Aggregating Across Multiple Years Without year in GROUP BY
**What goes wrong:** Cross-year data mixed together, inaccurate totals
**Why it happens:** Forgetting that data spans multiple fishing years
**How to avoid:** Always include `year` in GROUP BY for quota-related aggregations
**Warning signs:** Totals unexpectedly large, reconciliation failures with annual reports
**Fix:** Add `year` to GROUP BY clause; verify output matches expected annual totals

## Code Examples

Verified patterns from official sources:

### Example 1: Conditional Counting with FILTER
```sql
-- Source: PostgreSQL 9.4+ documentation, modern-sql.com FILTER clause reference
-- Count vessels by risk level in a single query
SELECT
    coop_code,
    species_code,
    COUNT(*) AS total_vessels,
    COUNT(*) FILTER (WHERE risk_level = 'critical') AS critical_count,
    COUNT(*) FILTER (WHERE risk_level = 'warning') AS warning_count,
    COUNT(*) FILTER (WHERE risk_level = 'ok') AS ok_count
FROM quota_metrics qm
JOIN coop_members cm ON qm.llp = cm.llp
GROUP BY coop_code, species_code;
```

### Example 2: Date Aggregation with DATE_TRUNC
```sql
-- Source: PostgreSQL date/time functions documentation
-- Daily harvest totals with proper date handling
SELECT
    DATE_TRUNC('day', harvest_date) AS harvest_day,
    species_code,
    SUM(pounds) AS daily_total
FROM harvests
WHERE is_deleted = FALSE
  AND harvest_date >= '2026-01-01'
GROUP BY DATE_TRUNC('day', harvest_date), species_code
ORDER BY harvest_day DESC;

-- Performance index (if needed)
CREATE INDEX idx_harvests_day_species
ON harvests (DATE_TRUNC('day', harvest_date), species_code)
WHERE is_deleted = FALSE;
```

### Example 3: Safe Percentage Calculation in Aggregates
```sql
-- Source: Phase 1 research, PostgreSQL NULLIF documentation
-- Calculate coop-level percentage with division-by-zero safety
SELECT
    coop_code,
    species_code,
    SUM(remaining_lbs) AS total_remaining,
    SUM(allocation_lbs) AS total_allocation,
    -- NULLIF prevents division by zero; returns NULL if allocation = 0
    ROUND(
        (SUM(remaining_lbs) / NULLIF(SUM(allocation_lbs), 0) * 100)::NUMERIC,
        2
    ) AS remaining_pct
FROM quota_metrics qm
JOIN coop_members cm ON qm.llp = cm.llp
GROUP BY coop_code, species_code;
```

### Example 4: Multi-Tenant RLS-Aware View
```sql
-- Source: Supabase RLS documentation, PostgreSQL 15 security_invoker feature
-- View that respects org_id filtering via RLS
CREATE OR REPLACE VIEW my_aggregate_view
WITH (security_invoker = true)  -- CRITICAL for multi-tenancy
AS
SELECT
    org_id,  -- Must include org_id in GROUP BY
    dimension_col,
    COUNT(*) AS total_count
FROM base_table
WHERE is_deleted = FALSE
GROUP BY org_id, dimension_col;

-- Verify RLS inheritance with:
-- SET ROLE authenticated;
-- SELECT * FROM my_aggregate_view;  -- Should only see current user's org_id
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Application-level aggregation in Python/Streamlit | SQL views with aggregations | Ongoing (2024-2026) | Views enable BI tools, reduce data transfer, centralize logic |
| CASE WHEN for conditional counting | COUNT FILTER (WHERE ...) | Postgres 9.4 (2014) | Cleaner syntax, better readability, similar performance |
| Manual date string parsing | DATE_TRUNC for grouping | Always preferred, now standard | Type-safe, index-compatible, locale-independent |
| Materialized views everywhere | Regular views first, materialize only if slow | Recent (2023-2026) | Reduced complexity, fewer refresh jobs, KISS principle |
| Views without RLS awareness | security_invoker = true | Postgres 15 (2022) | Enables RLS-aware views in multi-tenant systems |

**Deprecated/outdated:**
- **EXTRACT + string concatenation for date grouping:** DATE_TRUNC is now standard, works better with indexes
- **SUM(CASE WHEN risk_level = 'critical' THEN 1 ELSE 0 END):** Replaced by COUNT FILTER for readability
- **Denormalizing coop_code into every table:** JOINs in views maintain normalization while providing convenience

## Performance Considerations

### When to Use Materialized Views

Current data volume (as of 2026-01-28):
- 46 vessels (LLPs) in coop_members
- 3 target species (POP, NR, Dusky) + PSC species
- 1 active year (2026)
- Estimated quota_metrics rows: 46 × 3-7 species = ~138-322 rows

**Decision:** Regular views sufficient. Consider materialized views if:
1. Query time exceeds 2 seconds consistently
2. Data volume exceeds 10K rows in base table (e.g., harvests table grows to 10K+ records)
3. Complex multi-table joins cause performance issues
4. Dashboard usage patterns show repeated queries within refresh window

**If materializing:**
```sql
CREATE MATERIALIZED VIEW kpi_coop_summary_mv AS
SELECT ... FROM quota_metrics ...;

-- Create unique index for CONCURRENTLY refresh
CREATE UNIQUE INDEX idx_kpi_coop_summary_pk
ON kpi_coop_summary_mv (org_id, coop_code, species_code, year);

-- Refresh strategy: scheduled job (cron/pg_cron)
REFRESH MATERIALIZED VIEW CONCURRENTLY kpi_coop_summary_mv;
```

### Index Recommendations

**For kpi_daily_by_species:**
```sql
-- If DATE_TRUNC aggregation becomes slow
CREATE INDEX idx_harvests_date_species_org
ON harvests (org_id, DATE_TRUNC('day', harvest_date), species_code)
WHERE is_deleted = FALSE;

-- For time-series data, BRIN index is space-efficient
CREATE INDEX idx_harvests_date_brin
ON harvests USING BRIN (harvest_date)
WHERE is_deleted = FALSE;
```

**For kpi_coop_summary:**
```sql
-- Composite index for JOIN + GROUP BY
CREATE INDEX idx_coop_members_org_llp_coop
ON coop_members (org_id, llp, coop_code);

-- Already exists via quota_remaining view optimization (assumed)
-- If not, add:
CREATE INDEX idx_quota_metrics_org_llp_species
ON quota_metrics (org_id, llp, species_code, year);
```

## Open Questions

Things that couldn't be fully resolved:

1. **Materialized View Necessity**
   - What we know: Current data volume is small (~138-322 rows), regular views should be fast
   - What's unclear: Dashboard usage patterns, concurrent user count, actual query times
   - Recommendation: Start with regular views, monitor with `EXPLAIN ANALYZE`, materialize only if query time >2s or user complaints

2. **Harvest Data Volume Growth Rate**
   - What we know: Harvests come from eLandings API, cumulative over season
   - What's unclear: How many harvest records per vessel per season (weekly? daily? per haul?)
   - Recommendation: Monitor harvests table size; if >10K rows, benchmark kpi_daily_by_species performance

3. **Coop Summary Use Cases Beyond Dashboard**
   - What we know: Requirements specify "dashboard-ready" views for KPI display
   - What's unclear: Will coops need downloadable reports? PDF exports? BI tool integration?
   - Recommendation: Build views for dashboard first; if reports needed, same views work for CSV exports

4. **Time-Series Granularity**
   - What we know: Requirements specify "daily" for kpi_daily_by_species
   - What's unclear: Do users need weekly/monthly rollups? Seasonal trends?
   - Recommendation: Daily view as specified; if rollups needed, add separate views or use DATE_TRUNC('week', ...) in dashboard queries

## Sources

### Primary (HIGH confidence)
- [PostgreSQL Official Documentation - Aggregation Functions](https://www.postgresql.org/docs/current/tutorial-agg.html) - Aggregate function syntax and behavior
- [PostgreSQL 15 Feature Matrix - security_invoker views](https://www.postgresql.org/about/featurematrix/detail/security-invoker-views/) - RLS inheritance for views
- [Supabase RLS Documentation](https://supabase.com/docs/guides/database/postgres/row-level-security) - Multi-tenant RLS patterns
- [Modern SQL - FILTER clause](https://modern-sql.com/feature/filter) - Conditional aggregation best practices
- [CYBERTEC - View permissions and row-level security](https://www.cybertec-postgresql.com/en/view-permissions-and-row-level-security-in-postgresql/) - security_invoker patterns

### Secondary (MEDIUM confidence)
- [Tiger Data - PostgreSQL Aggregation Best Practices](https://www.tigerdata.com/learn/postgresql-aggregation-best-practices) - Performance optimization strategies
- [Tiger Data - Speeding up Postgres Aggregations](https://www.tigerdata.com/blog/speeding-up-postgres-aggregations) - Index and query optimization
- [Crunchy Data - Postgres Date Functions](https://www.crunchydata.com/developers/playground/postgres-date-functions) - DATE_TRUNC usage patterns
- [Medium - Mastering PostgreSQL COUNT With FILTER](https://www.oreateai.com/blog/mastering-postgresql-the-power-of-count-with-filter/fbb82ecd286859b55de1872ce852fb6d) - FILTER clause examples

### Tertiary (LOW confidence)
- [CopyProgramming - PostgreSQL GROUP BY DATE INTERVAL 2026](https://copyprogramming.com/howto/sql-postgresql-group-by-date-interval-code-example) - Community examples (verify syntax with official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Built-in PostgreSQL features, well-documented, verified with official docs
- Architecture: HIGH - Patterns verified against Phase 1/2 research, existing codebase patterns, official Supabase/Postgres docs
- Pitfalls: HIGH - Common issues documented in CYBERTEC, Tiger Data, and community best practices

**Research date:** 2026-01-28
**Valid until:** ~60 days (2026-03-28) - PostgreSQL aggregation patterns are stable; security_invoker well-established since Postgres 15

**Key Codebase References:**
- `sql/migrations/013_add_quota_metrics.sql` - Phase 1 output, demonstrates view creation pattern
- `sql/checks.sql` - Phase 2 output, demonstrates aggregation query patterns
- `app/views/dashboard.py` - Current dashboard implementation showing aggregation needs (lines 183-197: species totals)
- `sql/README.md` - Example coop aggregation query (lines 69-78)
- `app/utils/formatting.py` - RISK_COLORS and risk_level definitions (must match SQL view)

**Decision Dependencies:**
- Phase 1 complete: quota_metrics view exists with risk_level column
- RISK_COLORS values: 'critical', 'warning', 'ok', 'na' (NOT 'healthy')
- Multi-tenant: org_id must be in GROUP BY, security_invoker = true required
- Soft deletes: is_deleted = FALSE filter required for harvests and quota_metrics aggregations
