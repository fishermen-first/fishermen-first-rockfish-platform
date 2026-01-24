---
name: Supabase Migration Generator
description: This skill should be used when the user asks to "create a migration", "add a table", "add a column", "create RLS policies", "generate migration SQL", "add database schema", or needs to modify the Supabase database schema for the Fishermen First multi-tenant application.
version: 0.1.0
---

# Supabase Migration Generator

Generate properly formatted Supabase migration SQL files with Row-Level Security (RLS) policies for the Fishermen First multi-tenant application.

## Overview

This skill creates migration files that follow project conventions:
- Numbered migration files in `sql/migrations/`
- Multi-tenant isolation via `org_id` column
- RLS policies using `get_user_org_id()` helper function
- Role-based access control (admin, manager, processor, vessel_owner)
- Soft delete pattern with `is_deleted` flag
- Standard audit columns

## Migration File Naming

Determine the next migration number by checking existing files:

```bash
ls sql/migrations/*.sql | tail -1
```

Name format: `NNN_description_in_snake_case.sql`

Examples:
- `008_add_species_unit.sql`
- `009_create_delivery_notes.sql`
- `010_add_vessel_contacts_phone.sql`

## Standard Table Structure

Every new table should include these standard columns:

```sql
CREATE TABLE table_name (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),

    -- Business columns here

    -- Audit columns
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES auth.users(id),
    updated_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES auth.users(id)
);
```

## RLS Policy Patterns

Enable RLS on every table and create policies based on access requirements.

### Basic Org Isolation (Most Common)

For tables where all org users can read/write:

```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation_table_name ON table_name
    FOR ALL USING (org_id = get_user_org_id());
```

### Role-Based Access

For tables with different access levels:

```sql
-- Managers and admins only
CREATE POLICY manager_access_table_name ON table_name
    FOR ALL USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

-- Vessel owners: own records only
CREATE POLICY vessel_owner_select_table_name ON table_name
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
    );
```

### Separate Read/Write Policies

For tables where read and write permissions differ:

```sql
-- Everyone can read
CREATE POLICY org_select_table_name ON table_name
    FOR SELECT USING (org_id = get_user_org_id());

-- Only managers can write
CREATE POLICY manager_insert_table_name ON table_name
    FOR INSERT WITH CHECK (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

CREATE POLICY manager_update_table_name ON table_name
    FOR UPDATE USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );
```

## Index Patterns

Add indexes for common query patterns:

```sql
-- Org isolation (most queries filter by org_id)
CREATE INDEX idx_table_name_org ON table_name(org_id) WHERE NOT is_deleted;

-- Common filter combinations
CREATE INDEX idx_table_name_org_status ON table_name(org_id, status) WHERE NOT is_deleted;

-- Foreign key lookups
CREATE INDEX idx_table_name_llp ON table_name(org_id, llp) WHERE NOT is_deleted;

-- Time-based queries
CREATE INDEX idx_table_name_created ON table_name(org_id, created_at DESC) WHERE NOT is_deleted;
```

## Migration File Structure

Organize migrations with clear sections:

```sql
-- Migration: Brief description
-- Run this in Supabase SQL Editor

-- =============================================================================
-- 1. TABLE CREATION / SCHEMA CHANGES
-- =============================================================================

-- Create table or alter existing

-- =============================================================================
-- 2. INDEXES
-- =============================================================================

-- Add performance indexes

-- =============================================================================
-- 3. ROW-LEVEL SECURITY
-- =============================================================================

-- Enable RLS and create policies

-- =============================================================================
-- 4. SEED DATA (if needed)
-- =============================================================================

-- Bootstrap data or backfills
```

## Common Migration Types

### Adding a New Table

1. Create table with standard columns
2. Add business-specific columns with constraints
3. Create indexes for common queries
4. Enable RLS with appropriate policies
5. Add seed data if needed

### Adding a Column

```sql
-- Add column with default
ALTER TABLE table_name ADD COLUMN IF NOT EXISTS column_name TYPE DEFAULT value;

-- Backfill existing rows if needed
UPDATE table_name SET column_name = computed_value WHERE column_name IS NULL;
```

### Adding a Foreign Key Relationship

```sql
-- Add column
ALTER TABLE child_table ADD COLUMN IF NOT EXISTS parent_id UUID REFERENCES parent_table(id);

-- Add index for FK lookups
CREATE INDEX idx_child_table_parent ON child_table(parent_id) WHERE NOT is_deleted;
```

### Creating a View

```sql
CREATE OR REPLACE VIEW view_name AS
SELECT
    t.id,
    t.org_id,
    -- computed columns
FROM table_name t
WHERE NOT t.is_deleted;
```

## Validation Checklist

Before finalizing a migration:

- [ ] Migration number is sequential (no gaps or duplicates)
- [ ] All tables have `org_id` for multi-tenant isolation
- [ ] RLS is enabled on all new tables
- [ ] RLS policies use `get_user_org_id()` function
- [ ] Indexes exist for `org_id` and common query patterns
- [ ] `WHERE NOT is_deleted` included in partial indexes
- [ ] Constraints validate business rules
- [ ] Foreign keys reference correct tables
- [ ] Seed data uses proper org_id values

## Project-Specific References

### Key Tables
- `organizations` - Multi-tenant root
- `user_profiles` - User roles and LLP assignments
- `coop_members` - Vessels identified by LLP
- `species` - Species codes (POP=141, NR=136, Dusky=172)

### Helper Functions
- `get_user_org_id()` - Returns current user's org_id
- `auth.uid()` - Returns current user's UUID

### User Roles
- `admin` - Full access
- `manager` - Transfers, uploads, dashboards
- `processor` - Processor view only
- `vessel_owner` - Own vessel data (read-only)

## Additional Resources

### Reference Files

For detailed patterns and examples:
- **`references/rls-patterns.md`** - Complete RLS policy patterns for all scenarios
- **`references/schema-conventions.md`** - Column naming, data types, constraints

### Example Files

Working migrations from the project:
- **`examples/007_add_bycatch_alerts.md`** - Complex table with multiple RLS policies
- **`examples/008_add_species_unit.md`** - Simple column addition with backfill

## Workflow

To create a migration:

1. Determine next migration number from `sql/migrations/`
2. Identify schema changes needed
3. Write migration SQL following section structure
4. Include RLS policies appropriate for access requirements
5. Add indexes for query performance
6. Save to `sql/migrations/NNN_description.sql`
7. Validate against checklist
8. Run in Supabase SQL Editor
