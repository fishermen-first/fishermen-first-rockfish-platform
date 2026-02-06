# Bycatch Hotspot Alert Feature – Implementation Plan (Revised)

## Overview

Vessel owners report bycatch hotspots via a form. Managers receive in-app notifications (badge + alerts page), can review and preview alerts, and broadcast them org-wide to all vessels via email (Supabase Edge Functions + Resend).

The feature prioritizes:
- Operational safety (confirmation, idempotency)
- Clear auditability
- Minimal friction for vessel reporting
- Consistency with existing platform patterns

## Requirements Summary

- **Report fields**: GPS coordinates, PSC species, amount/count, free-form details
- **Email service**: Supabase Edge Functions + Resend
- **Email source**: `vessel_contacts` table (multiple contacts per LLP)
- **Alert scope**: Org-wide broadcast to all vessels
- **In-app notification**:
  - Sidebar badge for pending alerts
  - Dedicated alerts management page
- **Operational guardrails**:
  - Preview + confirmation before broadcast
  - Idempotent share behavior
  - Basic delivery metadata captured

---

## Database Schema

### 1. New Table: `bycatch_alerts`

```sql
CREATE TABLE bycatch_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    reported_by_llp TEXT NOT NULL REFERENCES llps(llp),
    species_code INTEGER NOT NULL REFERENCES species(code),
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(10,6) NOT NULL,
    amount NUMERIC NOT NULL CHECK (amount > 0),
    details TEXT,

    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'shared', 'dismissed')),

    shared_at TIMESTAMPTZ,
    shared_by UUID REFERENCES auth.users(id),
    shared_recipient_count INTEGER,

    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now(),

    is_deleted BOOLEAN DEFAULT false,
    deleted_by UUID REFERENCES auth.users(id),
    deleted_at TIMESTAMPTZ
);
```

**Notes:**
- `shared_recipient_count` provides lightweight observability
- Status transitions are strictly one-way for broadcast safety

### 2. New Table: `vessel_contacts`

```sql
CREATE TABLE vessel_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    llp TEXT NOT NULL REFERENCES llps(llp),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false
);
```

### 3. New Table: `alert_email_log` (for debugging)

```sql
CREATE TABLE alert_email_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES bycatch_alerts(id),
    org_id UUID NOT NULL REFERENCES organizations(id),
    recipient_count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'partial', 'failed')),
    error_message TEXT,
    resend_response JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**Notes:**
- Captures email delivery attempts for debugging
- `partial` status indicates some emails failed
- `resend_response` stores raw API response for troubleshooting

### 4. Row-Level Security Policies

```sql
-- =============================================================================
-- BYCATCH ALERTS RLS
-- =============================================================================

ALTER TABLE bycatch_alerts ENABLE ROW LEVEL SECURITY;

-- Vessel owners can insert alerts for their own LLP only
CREATE POLICY vessel_owner_insert_alerts ON bycatch_alerts
    FOR INSERT WITH CHECK (
        org_id = get_user_org_id()
        AND reported_by_llp = (
            SELECT llp FROM user_profiles WHERE user_id = auth.uid()
        )
    );

-- Vessel owners can view their own alerts
CREATE POLICY vessel_owner_select_alerts ON bycatch_alerts
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND reported_by_llp = (
            SELECT llp FROM user_profiles WHERE user_id = auth.uid()
        )
    );

-- Managers and admins can view all org alerts
CREATE POLICY manager_select_alerts ON bycatch_alerts
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

-- Managers and admins can update org alerts (share/dismiss)
CREATE POLICY manager_update_alerts ON bycatch_alerts
    FOR UPDATE USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );

-- =============================================================================
-- VESSEL CONTACTS RLS
-- =============================================================================

ALTER TABLE vessel_contacts ENABLE ROW LEVEL SECURITY;

-- Org isolation for vessel contacts
CREATE POLICY org_isolation_vessel_contacts ON vessel_contacts
    FOR ALL USING (org_id = get_user_org_id());

-- =============================================================================
-- ALERT EMAIL LOG RLS
-- =============================================================================

ALTER TABLE alert_email_log ENABLE ROW LEVEL SECURITY;

-- Only managers/admins can view email logs
CREATE POLICY manager_select_email_log ON alert_email_log
    FOR SELECT USING (
        org_id = get_user_org_id()
        AND (SELECT role FROM user_profiles WHERE user_id = auth.uid()) IN ('admin', 'manager')
    );
```

### 5. Migration File

`sql/migrations/007_add_bycatch_alerts.sql`

Includes:
- All tables above
- Index on `bycatch_alerts(org_id, status)` for pending count queries
- Index on `bycatch_alerts(org_id, created_at DESC)` for history
- All RLS policies

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `sql/migrations/007_add_bycatch_alerts.sql` | Alerts + contacts + email log schema |
| `app/views/report_bycatch.py` | Vessel owner report form |
| `app/views/bycatch_alerts.py` | Manager review / preview / share page |
| `supabase/functions/send-bycatch-alert/index.ts` | Email broadcast Edge Function |

### Modified Files

| File | Changes |
|------|---------|
| `app/main.py` | Sidebar nav + badge |
| `app/auth.py` | Pending alert count helper |

---

## Implementation Steps

### Phase 1: Database

Create migration with:
- `bycatch_alerts` table
- `vessel_contacts` table
- `alert_email_log` table
- RLS policies (detailed above)
- Status + org indexes

### Phase 1.5: Bootstrap Contact Data

Seed `vessel_contacts` from existing data so the feature works on day one:

```sql
-- Seed contacts from existing vessel_owner user_profiles
INSERT INTO vessel_contacts (org_id, llp, name, email, is_primary)
SELECT
    up.org_id,
    up.llp,
    COALESCE(SPLIT_PART(up.email, '@', 1), 'Vessel Owner'),
    up.email,
    true
FROM user_profiles up
WHERE up.role = 'vessel_owner'
  AND up.llp IS NOT NULL
ON CONFLICT DO NOTHING;
```

**Notes:**
- This creates one contact per vessel owner account
- Admins can add additional contacts later (Phase 6)
- `is_primary = true` for seeded contacts

### Phase 2: Vessel Owner Report Form

Create `app/views/report_bycatch.py`:
- Latitude / longitude inputs with bounds validation
- PSC species dropdown (`is_psc = true`)
- Amount numeric input (> 0)
- Optional details
- Insert alert with `status = 'pending'`
- No email side effects at this stage

### Phase 3: Manager Alerts Page

Create `app/views/bycatch_alerts.py`:
- Page header: "Bycatch Alerts"
- Tabs: Pending | Shared | All
- Alert cards include:
  - Reporting vessel
  - Species
  - Coordinates
  - Amount
  - Details
  - Timestamp
- Actions:
  - **Preview Email**
  - **Share to Fleet**
  - **Dismiss**

**Preview Flow:**
1. Renders email content inline
2. Displays recipient count
3. Requires explicit confirmation before sharing

### Phase 4: Sidebar Badge

Modify `app/main.py`:
- `get_pending_alert_count()` (TTL = 30s)
- Manager/admin nav item with badge
- Vessel owner nav item: "Report Bycatch"
- Route guards by role

**Scaling Note:**
The current `COUNT(*)` approach works for low-to-moderate alert volume. If alert volume grows significantly (100+ pending alerts), consider:
- A trigger-maintained counter column on `organizations`
- Or a materialized view refreshed on insert/update

For now, the 30s cache TTL keeps query load manageable.

### Phase 5: Email Integration (Edge Function)

Create `send-bycatch-alert` Edge Function:

**Authentication:**
- Uses Supabase service role key (stored in Supabase secrets as `SUPABASE_SERVICE_ROLE_KEY`)
- Called from authenticated manager session via `supabase.functions.invoke()`
- Edge Function validates the alert belongs to the caller's org

**Input:** `{ alert_id: UUID }`

**Guardrails:**
1. Fetch alert with `status = 'pending'`
2. **Abort if already shared or dismissed** (idempotent - return success, no-op)
3. Fetch all non-deleted contacts for org
4. **Rate limit check**: If recipient count > 90, warn in response (Resend free tier = 100/day)
5. Send email via Resend API

**On Success:**
- Update alert:
  - `status = 'shared'`
  - `shared_at = now()`
  - `shared_by = caller user_id`
  - `shared_recipient_count = N`
- Insert success record to `alert_email_log`

**On Failure:**
- Do NOT update alert status (remains `pending`)
- Insert failure record to `alert_email_log` with error details
- Return error to client for display

**On Partial Failure (some emails failed):**
- Still update alert to `shared` (primary path succeeded)
- Log with `status = 'partial'` and error details
- Return warning to client

**Email Template (v1):**

Subject: `⚠️ Bycatch Alert – {Species} Reported`

Body includes:
- Species
- Amount
- Coordinates
- Reporting vessel
- Timestamp
- Optional details

### Phase 6: Contacts Management (Optional / v1.1)

Admin UI to:
- Add/edit/remove vessel contacts
- Set primary contacts
- Soft-delete obsolete emails

---

## Testing Strategy

### Unit Tests (`tests/test_bycatch_alerts.py`)

- Report validation (GPS bounds, species code, amount > 0)
- Status transitions (pending → shared, pending → dismissed)
- Idempotent share behavior (share already-shared alert = no-op)
- Permission enforcement (vessel_owner can report, manager can share)
- Pending badge count calculation

### Integration Tests

- Full flow: report → preview → share → status update
- Org isolation (alerts scoped to org_id)
- Double-click / retry protection (idempotency)
- Email log creation on success/failure

### E2E Tests

- Vessel owner submits report
- Manager sees badge
- Manager previews and shares alert
- Contacts receive email (mock Resend in test)

---

## Key Patterns to Follow

From existing codebase:
- **Form pattern**: Inputs outside form, only submit button inside (transfers.py)
- **Caching**: TTL=30 for realtime data, TTL=300 for reference data
- **Soft deletes**: `is_deleted`, `deleted_by`, `deleted_at` fields
- **Styling**: Use `page_header()`, `section_header()` from styles.py
- **Auth**: `require_role("manager")` at top of manager views
- **Multi-tenancy**: Include `org_id` in all queries

---

## Dependencies

- Resend account + API key (add to Supabase secrets as `RESEND_API_KEY`)
- Supabase Edge Functions enabled
- Supabase service role key in secrets (`SUPABASE_SERVICE_ROLE_KEY`)
- PSC species flagged in species table (`is_psc` column exists per migration 003)

---

## Notes for Future Enhancements

- Geo-visualization (map preview)
- Alert expiration / archival
- Severity levels
- Alert history analytics
- SMS / WhatsApp delivery add-ons
