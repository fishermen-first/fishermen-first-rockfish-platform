# RLS Policy Patterns for Fishermen First

Comprehensive Row-Level Security patterns for the multi-tenant Fishermen First application.

## Core Concepts

### The get_user_org_id() Function

All RLS policies rely on this helper function that returns the current user's organization ID:

```sql
-- This function already exists in the database
CREATE OR REPLACE FUNCTION get_user_org_id()
RETURNS UUID AS $$
    SELECT org_id FROM user_profiles WHERE user_id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER;
```

### Policy Naming Convention

Follow this pattern: `{role}_{action}_{table_name}`

Examples:
- `org_isolation_harvests` - All org users, all actions
- `manager_select_alerts` - Managers only, SELECT
- `vessel_owner_insert_reports` - Vessel owners, INSERT
- `admin_delete_transfers` - Admins only, DELETE

## Pattern 1: Simple Org Isolation

**Use when:** All authenticated users in an org should have full access.

**Tables:** `cooperatives`, `coop_members`, `species`, `processors`

```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation_table_name ON table_name
    FOR ALL USING (org_id = get_user_org_id());
```

## Pattern 2: Manager/Admin Only

**Use when:** Only managers and admins should access the table.

**Tables:** `quota_transfers`, `file_uploads`, `annual_tac`

```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

CREATE POLICY manager_all_table_name ON table_name
    FOR ALL USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );
```

## Pattern 3: Vessel Owner - Own Records Only

**Use when:** Vessel owners should only see/modify their own vessel's data.

**Tables:** `bycatch_alerts` (for vessel owner reporting)

```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

-- Vessel owners: own records only
CREATE POLICY vessel_owner_select_table_name ON table_name
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
    );

CREATE POLICY vessel_owner_insert_table_name ON table_name
    FOR INSERT WITH CHECK (
        org_id = get_user_org_id()
        AND reported_by_llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
    );

-- Managers: all org records
CREATE POLICY manager_select_table_name ON table_name
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

CREATE POLICY manager_update_table_name ON table_name
    FOR UPDATE USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );
```

## Pattern 4: Read-Only for Some Roles

**Use when:** Some users can read but not write.

**Tables:** `harvests` (vessel owners read-only), `vessel_allocations`

```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

-- Everyone in org can read
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

CREATE POLICY manager_delete_table_name ON table_name
    FOR DELETE USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );
```

## Pattern 5: Processor Role Access

**Use when:** Processors need limited access to specific data.

**Tables:** `processor_deliveries`

```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

-- Processors: own processor's records only
CREATE POLICY processor_select_table_name ON table_name
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND processor_id = (SELECT processor_id FROM user_profiles WHERE user_id = auth.uid())
    );

-- Managers: all records
CREATE POLICY manager_all_table_name ON table_name
    FOR ALL USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );
```

## Pattern 6: Admin-Only Operations

**Use when:** Certain operations should be admin-only.

**Tables:** `organizations`, `user_profiles` (for role changes)

```sql
-- Only admins can delete
CREATE POLICY admin_delete_table_name ON table_name
    FOR DELETE USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) = 'admin'
    );
```

## Pattern 7: Cross-Reference Tables

**Use when:** Junction tables link entities from same org.

**Tables:** `vessel_contacts`, `coop_membership`

```sql
ALTER TABLE junction_table ENABLE ROW LEVEL SECURITY;

-- Ensure both sides are in same org
CREATE POLICY org_isolation_junction_table ON junction_table
    FOR ALL USING (org_id = get_user_org_id());
```

## Pattern 8: Audit/Log Tables

**Use when:** Tables that should be append-only for most users.

**Tables:** `alert_email_log`, `audit_log`

```sql
ALTER TABLE log_table ENABLE ROW LEVEL SECURITY;

-- Everyone can insert (log their actions)
CREATE POLICY org_insert_log_table ON log_table
    FOR INSERT WITH CHECK (org_id = get_user_org_id());

-- Only managers can read
CREATE POLICY manager_select_log_table ON log_table
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

-- No updates or deletes (audit trail integrity)
```

## Pattern 9: Soft Delete Considerations

**Use when:** Tables use `is_deleted` flag instead of hard delete.

```sql
-- Include is_deleted check in policies for stricter security
CREATE POLICY org_select_active_table_name ON table_name
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND NOT is_deleted
    );

-- Or handle in application layer and keep policy simple
CREATE POLICY org_isolation_table_name ON table_name
    FOR ALL USING (org_id = get_user_org_id());
```

## Pattern 10: Status-Based Access

**Use when:** Access depends on record status.

**Tables:** `bycatch_alerts` (pending vs shared)

```sql
-- Vessel owners can only edit pending alerts
CREATE POLICY vessel_owner_update_pending ON bycatch_alerts
    FOR UPDATE USING (
        org_id = get_user_org_id()
        AND reported_by_llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
        AND status = 'pending'
    );
```

## Testing RLS Policies

To test policies in Supabase SQL Editor:

```sql
-- Temporarily become a specific user
SET LOCAL ROLE authenticated;
SET LOCAL request.jwt.claims = '{"sub": "user-uuid-here"}';

-- Run queries to test access
SELECT * FROM table_name;

-- Reset
RESET ROLE;
```

## Common Mistakes

### Mistake 1: Missing org_id Check

```sql
-- BAD: No org isolation
CREATE POLICY bad_policy ON table_name
    FOR SELECT USING (true);

-- GOOD: Always include org_id
CREATE POLICY good_policy ON table_name
    FOR SELECT USING (org_id = get_user_org_id());
```

### Mistake 2: Using auth.uid() Directly for org_id

```sql
-- BAD: auth.uid() is user ID, not org ID
CREATE POLICY bad_policy ON table_name
    FOR ALL USING (org_id = auth.uid());

-- GOOD: Use helper function
CREATE POLICY good_policy ON table_name
    FOR ALL USING (org_id = get_user_org_id());
```

### Mistake 3: Forgetting INSERT Uses WITH CHECK

```sql
-- BAD: USING doesn't work for INSERT
CREATE POLICY bad_insert ON table_name
    FOR INSERT USING (org_id = get_user_org_id());

-- GOOD: INSERT requires WITH CHECK
CREATE POLICY good_insert ON table_name
    FOR INSERT WITH CHECK (org_id = get_user_org_id());
```

### Mistake 4: Overlapping Policies

```sql
-- BAD: Two policies both allow all users
CREATE POLICY policy1 ON table FOR SELECT USING (org_id = get_user_org_id());
CREATE POLICY policy2 ON table FOR SELECT USING (org_id = get_user_org_id() AND role = 'admin');

-- GOOD: Policies are distinct by role
CREATE POLICY vessel_owner_select ON table FOR SELECT USING (
    org_id = get_user_org_id()
    AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) = 'vessel_owner'
    AND llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
);
CREATE POLICY manager_select ON table FOR SELECT USING (
    org_id = get_user_org_id()
    AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
);
```
