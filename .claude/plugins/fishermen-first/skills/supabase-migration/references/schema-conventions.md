# Schema Conventions for Fishermen First

Database naming conventions, data types, and constraint patterns.

## Naming Conventions

### Tables

- Use `snake_case` for table names
- Use plural nouns: `harvests`, `transfers`, `alerts`
- Junction tables: combine both table names: `vessel_contacts`, `coop_members`

### Columns

- Use `snake_case` for column names
- Foreign keys: `{referenced_table_singular}_id` (e.g., `org_id`, `user_id`, `processor_id`)
- Booleans: prefix with `is_` or `has_` (e.g., `is_deleted`, `is_primary`, `has_verified`)
- Timestamps: suffix with `_at` (e.g., `created_at`, `shared_at`, `deleted_at`)
- Counts: suffix with `_count` (e.g., `recipient_count`, `harvest_count`)

### Indexes

- Pattern: `idx_{table}_{columns}`
- Examples: `idx_harvests_org`, `idx_alerts_org_status`, `idx_transfers_llp`

### Constraints

- Primary key: implicit from `PRIMARY KEY`
- Foreign key: `fk_{table}_{column}` (usually auto-named by Supabase)
- Check: `{table}_{description}` (e.g., `bycatch_alerts_valid_latitude`)
- Unique: `uq_{table}_{columns}`

## Standard Column Sets

### Primary Key

Always use UUID:

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

### Multi-Tenant Isolation

Required on every table:

```sql
org_id UUID NOT NULL REFERENCES organizations(id)
```

### Audit Columns (Creation)

For tracking who created records:

```sql
created_at TIMESTAMPTZ DEFAULT now(),
created_by UUID REFERENCES auth.users(id)
```

### Audit Columns (Updates)

For tables that track modifications:

```sql
updated_at TIMESTAMPTZ DEFAULT now(),
updated_by UUID REFERENCES auth.users(id)
```

### Soft Delete

For tables using soft delete pattern:

```sql
is_deleted BOOLEAN DEFAULT false,
deleted_at TIMESTAMPTZ,
deleted_by UUID REFERENCES auth.users(id)
```

### Complete Audit Set

Full audit trail:

```sql
-- Creation
created_at TIMESTAMPTZ DEFAULT now(),
created_by UUID REFERENCES auth.users(id),

-- Updates
updated_at TIMESTAMPTZ DEFAULT now(),

-- Soft delete
is_deleted BOOLEAN DEFAULT false,
deleted_at TIMESTAMPTZ,
deleted_by UUID REFERENCES auth.users(id)
```

## Data Types

### Identifiers

| Use Case | Type | Example |
|----------|------|---------|
| Primary key | `UUID` | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` |
| Foreign key | `UUID` | `org_id UUID REFERENCES organizations(id)` |
| LLP (license) | `TEXT` | `llp TEXT NOT NULL` |
| Species code | `INTEGER` | `species_code INTEGER NOT NULL` |
| Coop code | `TEXT` | `coop_code TEXT NOT NULL` |

### Text Fields

| Use Case | Type | Example |
|----------|------|---------|
| Short text | `TEXT` | `vessel_name TEXT` |
| Long text | `TEXT` | `details TEXT` |
| Enum-like | `TEXT` with CHECK | `status TEXT CHECK (status IN ('pending', 'shared'))` |
| Email | `TEXT` | `email TEXT NOT NULL` |

### Numbers

| Use Case | Type | Example |
|----------|------|---------|
| Quota amounts | `NUMERIC` | `amount NUMERIC NOT NULL` |
| Counts | `INTEGER` | `recipient_count INTEGER` |
| GPS latitude | `NUMERIC(9,6)` | `latitude NUMERIC(9,6) NOT NULL` |
| GPS longitude | `NUMERIC(10,6)` | `longitude NUMERIC(10,6) NOT NULL` |
| Percentages | `NUMERIC(5,2)` | `percentage NUMERIC(5,2)` |

### Timestamps

| Use Case | Type | Example |
|----------|------|---------|
| Any timestamp | `TIMESTAMPTZ` | `created_at TIMESTAMPTZ DEFAULT now()` |
| Date only | `DATE` | `landing_date DATE NOT NULL` |
| Year | `INTEGER` | `year INTEGER NOT NULL` |

### Booleans

| Use Case | Type | Example |
|----------|------|---------|
| Flags | `BOOLEAN` | `is_deleted BOOLEAN DEFAULT false` |
| PSC species | `BOOLEAN` | `is_psc BOOLEAN DEFAULT false` |

### JSON

| Use Case | Type | Example |
|----------|------|---------|
| Flexible data | `JSONB` | `metadata JSONB` |
| API responses | `JSONB` | `response_data JSONB` |

## Common Constraints

### NOT NULL

Apply to required business fields:

```sql
org_id UUID NOT NULL,
llp TEXT NOT NULL,
species_code INTEGER NOT NULL
```

### CHECK Constraints

#### Enum-style Status

```sql
status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'rejected'))
```

#### Positive Numbers

```sql
amount NUMERIC NOT NULL CHECK (amount > 0)
```

#### GPS Coordinates (Alaska)

```sql
CONSTRAINT valid_latitude CHECK (latitude BETWEEN 50.0 AND 72.0),
CONSTRAINT valid_longitude CHECK (longitude BETWEEN -180.0 AND -130.0)
```

#### Year Range

```sql
year INTEGER NOT NULL CHECK (year >= 2020 AND year <= 2100)
```

### UNIQUE Constraints

```sql
-- Single column
CONSTRAINT uq_vessel_contacts_email UNIQUE (org_id, llp, email)

-- Composite
CONSTRAINT uq_allocations_vessel_year UNIQUE (org_id, llp, year, species_code)
```

### Foreign Keys

```sql
-- Simple reference
org_id UUID NOT NULL REFERENCES organizations(id),

-- With cascade
user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,

-- Named constraint
CONSTRAINT fk_alerts_species FOREIGN KEY (species_code) REFERENCES species(code)
```

## Domain-Specific Columns

### Vessel/LLP References

```sql
llp TEXT NOT NULL,  -- No FK; validated via RLS/app logic
-- or with comment
reported_by_llp TEXT NOT NULL,  -- LLP validated via RLS policies
```

### Species References

```sql
species_code INTEGER NOT NULL,  -- References species.code
-- Note: Often no FK constraint; validated via dropdown in app
```

### Money/Quota Amounts

```sql
amount NUMERIC NOT NULL CHECK (amount > 0),
allocation NUMERIC NOT NULL DEFAULT 0,
transferred_in NUMERIC NOT NULL DEFAULT 0,
transferred_out NUMERIC NOT NULL DEFAULT 0,
harvested NUMERIC NOT NULL DEFAULT 0
```

### Unit of Measure

```sql
unit TEXT DEFAULT 'lbs' CHECK (unit IN ('lbs', 'count'))
```

## Index Patterns

### Standard Org Index

Every table should have:

```sql
CREATE INDEX idx_{table}_org ON {table}(org_id) WHERE NOT is_deleted;
```

### Status Filter Index

For tables with status column:

```sql
CREATE INDEX idx_{table}_org_status ON {table}(org_id, status) WHERE NOT is_deleted;
```

### Time-Series Index

For tables queried by date:

```sql
CREATE INDEX idx_{table}_org_created ON {table}(org_id, created_at DESC) WHERE NOT is_deleted;
```

### LLP Lookup Index

For vessel-related tables:

```sql
CREATE INDEX idx_{table}_org_llp ON {table}(org_id, llp) WHERE NOT is_deleted;
```

### Partial Index for Active Status

For pending/active items:

```sql
CREATE INDEX idx_{table}_pending ON {table}(org_id)
    WHERE status = 'pending' AND NOT is_deleted;
```

## Existing Table Reference

### Core Tables

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `organizations` | `id`, `name` | Multi-tenant root |
| `user_profiles` | `user_id`, `org_id`, `role`, `llp` | User roles and vessel links |
| `cooperatives` | `coop_code`, `coop_name`, `org_id` | Fishing cooperatives |
| `coop_members` | `llp`, `vessel_name`, `coop_code` | Vessels in coops |
| `species` | `code`, `species_name`, `is_psc`, `unit` | Species reference data |
| `processors` | `id`, `processor_name`, `org_id` | Processing plants |

### Transaction Tables

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `vessel_allocations` | `llp`, `year`, `species_code`, `allocation` | Annual quota allocations |
| `quota_transfers` | `from_llp`, `to_llp`, `species_code`, `amount` | Quota transfers |
| `harvests` | `llp`, `species_code`, `amount`, `landing_date` | Harvest records |

### Bycatch Tables

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `bycatch_alerts` | `reported_by_llp`, `species_code`, `latitude`, `longitude` | Bycatch reports |
| `vessel_contacts` | `llp`, `email`, `is_primary` | Alert recipients |
| `alert_email_log` | `alert_id`, `status`, `recipient_count` | Email audit trail |

### Key Species Codes

| Species | Code | is_psc | unit |
|---------|------|--------|------|
| POP (Pacific Ocean Perch) | 141 | false | lbs |
| NR (Northern Rockfish) | 136 | false | lbs |
| Dusky Rockfish | 172 | false | lbs |
| Halibut | TBD | true | lbs |
| Salmon | TBD | true | count |
