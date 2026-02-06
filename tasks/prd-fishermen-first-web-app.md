[PRD]
# PRD: Fishermen First Rockfish Platform - Web Application

## 1. Overview

**Product Name:** Fishermen First Rockfish Platform
**Version:** 2.0 (Next.js Rebuild)
**Last Updated:** January 2026

Rebuild the Fishermen First Rockfish Platform as a production-grade Next.js web application. The platform enables Alaska fishing cooperatives participating in the Central Gulf of Alaska (CGOA) Rockfish Program to track quota allocations, manage transfers between vessels, coordinate bycatch alerts, and reconcile with eLandings/eFish data.

This PRD is **self-contained** - an AI agent should be able to build the complete application from this document without access to any other codebase or external documentation.

---

## 2. Domain Background

### 2.1 The CGOA Rockfish Program

The **Central Gulf of Alaska (CGOA) Rockfish Program** is a catch share program managed by NOAA Fisheries that allocates quota for three target rockfish species to harvester cooperatives. The program runs annually from **April 1 through November 15**.

**Key Concepts:**
- **LLP (License Limitation Program):** A federal fishing permit that is the primary identifier for quota holders. Each LLP is associated with one vessel.
- **Cooperative:** A group of LLP holders who pool and manage their quota collectively.
- **TAC (Total Allowable Catch):** The total amount of each species that can be harvested in a year.
- **IFQ (Individual Fishing Quota):** Quota allocated to individual LLPs based on historical catch.
- **PSC (Prohibited Species Catch):** Non-target species (like halibut) that must be limited as bycatch.

### 2.2 Participating Cooperatives

Four cooperatives participate in the Rockfish Program:

| Code | Full Name | Coop ID |
|------|-----------|---------|
| NP | North Pacific Seafoods Cooperative | 408 |
| SBS | Silver Bay Seafoods Cooperative | 407 |
| OBSI | Ocean Beauty Seafoods Inc. Cooperative | 409 |
| SOK | Southeast Ocean Klawock Cooperative | 411 |

### 2.3 Target Species

Three primary rockfish species are managed:

| Code | Common Name | Scientific Name |
|------|-------------|-----------------|
| 141 | Pacific Ocean Perch (POP) | *Sebastes alutus* |
| 136 | Northern Rockfish (NR) | *Sebastes polyspinis* |
| 172 | Dusky Rockfish | *Sebastes ciliatus* |

### 2.4 Prohibited Species Catch (PSC)

Bycatch limits for non-target species:

| Code | Species | Limit |
|------|---------|-------|
| 200 | Pacific Halibut | CV Sector allocation (lbs) |
| - | Chinook Salmon | 1,200 fish shared across entire fleet |

### 2.5 Processors

Each cooperative is associated with a processing facility:

| Processor Name | Processor Code | Associated Coop |
|----------------|----------------|-----------------|
| North Pacific Seafoods | 5342 | NP |
| Silver Bay Seafoods | 35457 | SBS |
| Silver Bay Seafoods (Old OBI Plant) | 36289 | OBSI |
| Pacific Seafoods | 36268 | SOK |

### 2.6 The Quota Formula

**Quota Remaining** is calculated as:

```
Remaining = Allocation + Transfers_In - Transfers_Out - Harvested
```

Where:
- **Allocation:** Starting quota assigned to the LLP for the season
- **Transfers_In:** Quota received from other vessels (to_llp = this LLP)
- **Transfers_Out:** Quota sent to other vessels (from_llp = this LLP)
- **Harvested:** Actual pounds landed and recorded in eLandings

---

## 3. Goals

- Achieve 100% feature parity with existing Streamlit application
- Improve page load performance (dashboard <2s, API responses <500ms)
- Provide polished, accessible UI with shadcn/ui components
- Enable data export in CSV, PDF, and Excel formats
- Maintain zero-downtime migration with parallel deployment
- Achieve comprehensive test coverage (unit + integration + E2E)

---

## 4. Quality Gates

These commands must pass for every user story:

```bash
npm run typecheck    # TypeScript compilation
npm run lint         # ESLint + Prettier
npm run test:unit    # Jest/Vitest unit tests
```

For UI stories, also include:
- Visual verification in browser for layout and interactions
- Playwright E2E tests for critical user flows

---

## 5. User Roles and Permissions

### 5.1 Role Definitions

| Role | Description | Access Level |
|------|-------------|--------------|
| `admin` | Full system access, user management | All features |
| `manager` | Co-op manager, day-to-day operations | Dashboard, Transfers, Alerts, Upload, Rosters |
| `processor` | Processing plant staff (future) | Processor view (placeholder) |
| `vessel_owner` | Individual vessel owner | Own vessel quota/transfers/harvests (read-only), Report bycatch |

### 5.2 Role-Based Navigation

**Admin/Manager sees:**
- Dashboard
- Transfers
- Alerts
- Upload
- Rosters
- Allocations

**Vessel Owner sees:**
- My Vessel
- Report Bycatch

---

## 6. Database Schema

### 6.1 Multi-Tenancy Model

All data is isolated by `org_id`. Row-Level Security (RLS) policies enforce this at the database level.

```sql
-- Helper function for RLS policies
CREATE OR REPLACE FUNCTION get_user_org_id()
RETURNS UUID AS $$
  SELECT org_id FROM user_profiles WHERE user_id = auth.uid()
$$ LANGUAGE SQL SECURITY DEFINER STABLE;
```

### 6.2 Core Tables

```sql
-- Organizations (tenants)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- User profiles with role and org assignment
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id),
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'processor', 'vessel_owner')),
    llp TEXT,  -- Only populated for vessel_owner role
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)
);

-- Cooperatives
CREATE TABLE cooperatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    code TEXT NOT NULL,  -- NP, SBS, OBSI, SOK
    coop_id TEXT,        -- 408, 407, 409, 411
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Coop members (LLP holders)
CREATE TABLE coop_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    coop_id UUID NOT NULL REFERENCES cooperatives(id),
    llp TEXT NOT NULL,
    company_name TEXT,
    vessel_name TEXT,
    representative TEXT,
    adfg_number TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, llp)
);

-- Processors
CREATE TABLE processors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    code TEXT NOT NULL,  -- Processor code (e.g., 5342)
    associated_coop_id UUID REFERENCES cooperatives(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Species reference
CREATE TABLE species (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    is_psc BOOLEAN DEFAULT false,
    unit TEXT DEFAULT 'lbs'  -- 'lbs' or 'count'
);

-- Annual TAC (Total Allowable Catch)
CREATE TABLE annual_tac (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    year INTEGER NOT NULL,
    species_code INTEGER NOT NULL,
    tac_mt NUMERIC,        -- Metric tons
    qs_pool_percent NUMERIC,
    tac_lbs NUMERIC,       -- Pounds
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, year, species_code)
);

-- Vessel allocations (starting quota per LLP)
CREATE TABLE vessel_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    year INTEGER NOT NULL,
    llp TEXT NOT NULL,
    species_code INTEGER NOT NULL,
    allocation_lbs NUMERIC NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, year, llp, species_code)
);
```

### 6.3 Transaction Tables (Affect Quota)

```sql
-- Quota transfers between vessels
CREATE TABLE quota_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    from_llp TEXT NOT NULL,
    to_llp TEXT NOT NULL,
    species_code INTEGER NOT NULL,
    pounds NUMERIC NOT NULL CHECK (pounds > 0),
    transfer_date DATE NOT NULL,
    notes TEXT,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false,
    deleted_by UUID REFERENCES auth.users(id),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT different_llps CHECK (from_llp != to_llp)
);

-- Harvest records (from eLandings)
CREATE TABLE harvests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    llp TEXT NOT NULL,
    species_code INTEGER NOT NULL,
    pounds NUMERIC NOT NULL,
    landing_date DATE NOT NULL,
    vessel_name TEXT,
    vessel_id TEXT,         -- ADFG number
    processor_code TEXT,
    processor_name TEXT,
    stat_area TEXT,
    trip_id TEXT,
    report_number TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false
);
```

### 6.4 Bycatch Alerts Tables

```sql
-- Bycatch alerts reported by vessel owners
CREATE TABLE bycatch_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    reported_by_llp TEXT NOT NULL,
    species_code INTEGER NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(10,6) NOT NULL,
    amount NUMERIC NOT NULL CHECK (amount > 0),
    details TEXT,

    -- Status workflow: pending -> shared/dismissed
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'shared', 'dismissed', 'resolved')),
    shared_at TIMESTAMPTZ,
    shared_by UUID REFERENCES auth.users(id),
    shared_recipient_count INTEGER,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES auth.users(id),

    -- Audit
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false,
    deleted_by UUID REFERENCES auth.users(id),
    deleted_at TIMESTAMPTZ,

    -- GPS validation (Alaska fishing areas)
    CONSTRAINT valid_latitude CHECK (latitude BETWEEN 50.0 AND 72.0),
    CONSTRAINT valid_longitude CHECK (longitude BETWEEN -180.0 AND -130.0)
);

-- Vessel contacts for email alerts
CREATE TABLE vessel_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    llp TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    is_deleted BOOLEAN DEFAULT false
);

-- Alert email log (for debugging)
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

### 6.5 Reconciliation Tables (Do NOT Affect Quota)

These tables store eFish data for reconciliation purposes only.

```sql
-- eFish account balance snapshots
CREATE TABLE efish_account_balance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    balance_date DATE NOT NULL,
    account_id TEXT NOT NULL,
    account_name TEXT,
    species_group TEXT,
    initial_balance NUMERIC,
    transfers_in NUMERIC,
    transfers_out NUMERIC,
    total_balance NUMERIC,
    catch_amount NUMERIC,
    remaining NUMERIC,
    percent_taken NUMERIC,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, balance_date, account_id, species_group)
);

-- eFish catch detail records
CREATE TABLE efish_account_detail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    landing_date DATE,
    vessel_name TEXT,
    adfg_number TEXT,
    species_group TEXT,
    weight NUMERIC,
    processor_name TEXT,
    report_number TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 6.6 Quota Remaining View

```sql
CREATE OR REPLACE VIEW quota_remaining AS
WITH allocations AS (
    SELECT
        org_id,
        llp,
        species_code,
        SUM(allocation_lbs) as allocation
    FROM vessel_allocations
    WHERE year = EXTRACT(YEAR FROM CURRENT_DATE)
    GROUP BY org_id, llp, species_code
),
transfers_in AS (
    SELECT
        org_id,
        to_llp as llp,
        species_code,
        SUM(pounds) as transferred_in
    FROM quota_transfers
    WHERE NOT is_deleted
    GROUP BY org_id, to_llp, species_code
),
transfers_out AS (
    SELECT
        org_id,
        from_llp as llp,
        species_code,
        SUM(pounds) as transferred_out
    FROM quota_transfers
    WHERE NOT is_deleted
    GROUP BY org_id, from_llp, species_code
),
harvested AS (
    SELECT
        org_id,
        llp,
        species_code,
        SUM(pounds) as total_harvested
    FROM harvests
    WHERE NOT is_deleted
    GROUP BY org_id, llp, species_code
)
SELECT
    a.org_id,
    a.llp,
    cm.vessel_name,
    c.code as coop_code,
    c.name as coop_name,
    a.species_code,
    s.name as species_name,
    a.allocation,
    COALESCE(ti.transferred_in, 0) as transfers_in,
    COALESCE(tou.transferred_out, 0) as transfers_out,
    COALESCE(h.total_harvested, 0) as harvested,
    (a.allocation + COALESCE(ti.transferred_in, 0)
        - COALESCE(tou.transferred_out, 0)
        - COALESCE(h.total_harvested, 0)) as remaining,
    CASE
        WHEN a.allocation > 0 THEN
            ROUND(((a.allocation + COALESCE(ti.transferred_in, 0)
                - COALESCE(tou.transferred_out, 0)
                - COALESCE(h.total_harvested, 0)) / a.allocation * 100)::numeric, 1)
        ELSE 0
    END as percent_remaining
FROM allocations a
JOIN coop_members cm ON a.org_id = cm.org_id AND a.llp = cm.llp
JOIN cooperatives c ON cm.coop_id = c.id
JOIN species s ON a.species_code = s.code
LEFT JOIN transfers_in ti ON a.org_id = ti.org_id AND a.llp = ti.llp AND a.species_code = ti.species_code
LEFT JOIN transfers_out tou ON a.org_id = tou.org_id AND a.llp = tou.llp AND a.species_code = tou.species_code
LEFT JOIN harvested h ON a.org_id = h.org_id AND a.llp = h.llp AND a.species_code = h.species_code
WHERE cm.is_active = true;
```

### 6.7 Row-Level Security Policies

```sql
-- Enable RLS on all tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE cooperatives ENABLE ROW LEVEL SECURITY;
ALTER TABLE coop_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE processors ENABLE ROW LEVEL SECURITY;
ALTER TABLE annual_tac ENABLE ROW LEVEL SECURITY;
ALTER TABLE vessel_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE quota_transfers ENABLE ROW LEVEL SECURITY;
ALTER TABLE harvests ENABLE ROW LEVEL SECURITY;
ALTER TABLE bycatch_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE vessel_contacts ENABLE ROW LEVEL SECURITY;

-- Example RLS policy pattern (org isolation)
CREATE POLICY org_isolation ON cooperatives
    FOR ALL USING (org_id = get_user_org_id());

-- Vessel owner restrictions for quota_transfers
CREATE POLICY vessel_owner_select_transfers ON quota_transfers
    FOR SELECT USING (
        from_llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
        OR to_llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
    );

-- Vessel owner restrictions for harvests
CREATE POLICY vessel_owner_select_harvests ON harvests
    FOR SELECT USING (
        llp = (SELECT llp FROM user_profiles WHERE user_id = auth.uid())
    );
```

---

## 7. Business Rules

### 7.1 Transfer Validation Rules

1. **Same vessel check:** `from_llp` and `to_llp` must be different
2. **Sufficient quota:** Transfer amount cannot exceed sender's remaining quota
3. **Positive amount:** Amount must be greater than 0
4. **Same species:** Cannot transfer between different species
5. **Same organization:** Both LLPs must belong to the same org_id
6. **Valid date:** Transfer date cannot be in the future

### 7.2 GPS Coordinate Validation (Alaska Waters)

- **Latitude:** Must be between 50.0 and 72.0 (North)
- **Longitude:** Must be between -180.0 and -130.0 (West)

### 7.3 Risk Level Thresholds

| Level | Condition | Color |
|-------|-----------|-------|
| Critical | <10% remaining | Red |
| Warning | 10-50% remaining | Yellow |
| Good | >50% remaining | Green |

### 7.4 Season Dates

- Season start: April 1
- Season end: November 15

### 7.5 Soft Delete Pattern

All transaction tables use soft deletes:
- `is_deleted BOOLEAN DEFAULT false`
- `deleted_by UUID REFERENCES auth.users(id)`
- `deleted_at TIMESTAMPTZ`

Queries should filter `WHERE NOT is_deleted` unless viewing audit history.

---

## 8. File Format Specifications

### 8.1 eFish Account Balance CSV

**Filename pattern:** `account_balance_*.csv`

| Column | Type | Description |
|--------|------|-------------|
| Balance Date | Date | Snapshot date (YYYY-MM-DD) |
| Account Id | String | Cooperative ID |
| Account Name | String | Cooperative name |
| Species Group | String | Species name |
| Initial | Number | Starting allocation |
| Transfers In | Number | Quota received |
| Transfers Out | Number | Quota sent |
| Total | Number | Net total |
| Catch | Number | Harvested amount |
| Remaining | Number | Quota remaining |
| % Taken | Number | Percentage used |

### 8.2 eFish Catch Detail XLSX

**Filename pattern:** `catch_detail_*.xlsx`

| Column | Type | Description |
|--------|------|-------------|
| Landing Date | Date | Date of landing |
| Vessel Name | String | Vessel name |
| ADFG # | String | ADF&G vessel number |
| Species Group | String | Species name |
| Weight | Number | Pounds landed |
| Processor | String | Processing plant name |
| Report # | String | eLandings report number |

### 8.3 Sample eFish Landing Data CSV

Used for importing harvest records:

```csv
landing_date,vessel_name,vessel_id,species_code,species_name,pounds,price_per_lb,processor_name,stat_area,trip_id
2026-04-15,Leslie Lee,56119,141,Pacific Ocean Perch,12500,0.45,North Pacific Seafoods,525630,TRP-2026-0001
```

| Column | Type | Description |
|--------|------|-------------|
| landing_date | Date | YYYY-MM-DD |
| vessel_name | String | Vessel name |
| vessel_id | String | ADF&G number |
| species_code | Integer | 141, 136, or 172 |
| species_name | String | Species common name |
| pounds | Number | Pounds landed |
| price_per_lb | Number | Price (for info only) |
| processor_name | String | Processing facility |
| stat_area | String | Statistical area code |
| trip_id | String | Trip identifier |

---

## 9. User Stories

### Phase 1: Project Foundation

#### US-001: Initialize Next.js Project with TypeScript
**Description:** As a developer, I want a properly configured Next.js 14 project so that I can build the application with type safety.

**Acceptance Criteria:**
- [ ] Next.js 14 app router project created in `web/` directory
- [ ] TypeScript configured with strict mode
- [ ] ESLint + Prettier configured with consistent rules
- [ ] Tailwind CSS configured with brand colors (#1e3a5f navy)
- [ ] Package.json scripts: `dev`, `build`, `start`, `typecheck`, `lint`, `test:unit`
- [ ] `.env.example` with required Supabase variables
- [ ] Basic folder structure: `app/`, `components/`, `lib/`, `hooks/`, `types/`

#### US-002: Configure Supabase Client
**Description:** As a developer, I want Supabase client utilities so that I can interact with the database and auth.

**Acceptance Criteria:**
- [ ] `lib/supabase/client.ts` - Browser client for client components
- [ ] `lib/supabase/server.ts` - Server client for API routes/RSC
- [ ] `lib/supabase/middleware.ts` - Auth middleware helper
- [ ] TypeScript types generated from database schema
- [ ] Environment variables properly typed

#### US-003: Install and Configure shadcn/ui
**Description:** As a developer, I want shadcn/ui components available so that I can build consistent, accessible interfaces.

**Acceptance Criteria:**
- [ ] shadcn/ui CLI initialized
- [ ] Base components installed: Button, Card, Input, Select, Table, Dialog, Badge, Tabs, Toast
- [ ] Theme configured with Fishermen First brand colors
- [ ] Dark mode support disabled (not in scope)
- [ ] Components available in `components/ui/`

#### US-004: Create Application Layout Shell
**Description:** As a user, I want a consistent layout with navigation so that I can move between features.

**Acceptance Criteria:**
- [ ] Root layout with header (logo, user menu)
- [ ] Sidebar navigation component with role-based menu items
- [ ] Sidebar shows: Dashboard, Transfers, Alerts, Upload, Rosters, Allocations (manager/admin)
- [ ] Sidebar shows: My Vessel, Report Bycatch (vessel_owner)
- [ ] Active route highlighted in sidebar
- [ ] Responsive: sidebar collapses on smaller screens
- [ ] Footer with version number

#### US-005: Set Up TanStack Query
**Description:** As a developer, I want TanStack Query configured so that I can manage server state efficiently.

**Acceptance Criteria:**
- [ ] QueryClientProvider in root layout
- [ ] Default stale time: 60 seconds
- [ ] Default cache time: 5 minutes
- [ ] React Query DevTools in development only
- [ ] Custom hooks pattern established in `hooks/` directory

---

### Phase 2: Authentication

#### US-006: Create Login Page
**Description:** As a user, I want to log in with email and password so that I can access the platform.

**Acceptance Criteria:**
- [ ] Login page at `/login`
- [ ] Email input with validation (valid email format)
- [ ] Password input with show/hide toggle
- [ ] "Sign In" button with loading state
- [ ] Error message display for invalid credentials
- [ ] "Forgot Password" link
- [ ] Redirect to dashboard on successful login
- [ ] Brand styling with navy color scheme (#1e3a5f)

#### US-007: Create Password Reset Flow
**Description:** As a user, I want to reset my password so that I can regain access if I forget it.

**Acceptance Criteria:**
- [ ] "Forgot Password" page at `/reset-password`
- [ ] Email input for reset request
- [ ] Success message: "Check your email for reset link"
- [ ] Reset confirmation page at `/reset-password/confirm`
- [ ] New password input with confirmation
- [ ] Password requirements displayed (8+ chars, 1 uppercase, 1 number)
- [ ] Redirect to login on successful reset

#### US-008: Implement Auth Middleware
**Description:** As a developer, I want route protection so that unauthorized users cannot access protected pages.

**Acceptance Criteria:**
- [ ] Middleware checks auth status on protected routes
- [ ] Unauthenticated users redirected to `/login`
- [ ] Authenticated users redirected from `/login` to dashboard
- [ ] User session refreshed automatically
- [ ] Role stored in middleware context for route guards

#### US-009: Create Auth Context and Hooks
**Description:** As a developer, I want auth utilities so that components can access user information.

**Acceptance Criteria:**
- [ ] `useAuth()` hook returns: user, role, org_id, llp, isLoading
- [ ] `useRequireAuth()` hook redirects if not authenticated
- [ ] `useRequireRole(roles)` hook checks role permissions
- [ ] Auth state persists across page refreshes
- [ ] Logout function clears session and redirects to login

#### US-010: Create User Menu Component
**Description:** As a user, I want a user menu in the header so that I can see my account and log out.

**Acceptance Criteria:**
- [ ] User menu dropdown in header (top-right)
- [ ] Shows user email and role badge
- [ ] "Log Out" option
- [ ] Logout clears session and redirects to login
- [ ] Menu closes when clicking outside

---

### Phase 3: Dashboard

#### US-011: Create Dashboard Page Structure
**Description:** As a manager, I want a dashboard page so that I can monitor fleet quota status.

**Acceptance Criteria:**
- [ ] Dashboard page at `/dashboard`
- [ ] Page header: "Quota Dashboard"
- [ ] Loading skeleton while data fetches
- [ ] Error state with retry button
- [ ] Protected route (manager/admin only)

#### US-012: Build KPI Summary Cards
**Description:** As a manager, I want KPI cards at the top of the dashboard so that I can see fleet-wide metrics at a glance.

**Acceptance Criteria:**
- [ ] 5 cards in a row: Total Vessels, Critical Risk Count, POP %, NR %, Dusky %
- [ ] "Total Vessels" shows count of active LLPs
- [ ] "Critical Risk" shows vessels with any species <10% remaining (red styling)
- [ ] Species cards show: remaining lbs + percentage of total allocation
- [ ] Numbers formatted with thousands separators (e.g., 1,234,567)
- [ ] Cards have subtle shadow and border

#### US-013: Build At-Risk Vessels Panel
**Description:** As a manager, I want to see at-risk vessels highlighted so that I can prioritize attention.

**Acceptance Criteria:**
- [ ] Panel below KPI cards titled "Vessels Needing Attention"
- [ ] Shows top 7 vessels sorted by lowest % remaining
- [ ] Each row: colored dot (red <10%, yellow 10-50%, green >50%), vessel name, LLP, lowest %
- [ ] Clicking a vessel filters the main table to that vessel
- [ ] "View All" link scrolls to main table

#### US-014: Create Quota Data Table
**Description:** As a manager, I want a sortable table of all vessel quotas so that I can analyze fleet status.

**Acceptance Criteria:**
- [ ] Table columns: Co-Op, Vessel, LLP, Species, Allocation, Remaining, % Remaining
- [ ] Default sort: % Remaining ascending (lowest first)
- [ ] All columns sortable (click header to toggle)
- [ ] % Remaining column color-coded by risk level
- [ ] Inline progress bar showing % visually
- [ ] Pagination: 25/50/100 rows per page selector
- [ ] Shows total record count

#### US-015: Add Dashboard Filters
**Description:** As a manager, I want to filter the dashboard by cooperative and vessel so that I can focus on specific data.

**Acceptance Criteria:**
- [ ] Filter row above table with: Co-Op dropdown, Vessel dropdown, Species multi-select
- [ ] Co-Op dropdown: "All Cooperatives" + list (NP, SBS, OBSI, SOK)
- [ ] Vessel dropdown: cascades based on selected co-op
- [ ] Species: checkboxes for POP, NR, Dusky (all selected by default)
- [ ] "Clear Filters" button resets to defaults
- [ ] Filters apply to both at-risk panel and main table
- [ ] Filter state preserved in URL query params

#### US-016: Implement Dashboard Data Fetching
**Description:** As a developer, I want efficient data fetching for the dashboard so that it loads quickly.

**Acceptance Criteria:**
- [ ] API route: `GET /api/quota/summary` returns KPI data
- [ ] API route: `GET /api/quota/remaining` returns paginated table data
- [ ] TanStack Query hooks: `useQuotaSummary()`, `useQuotaRemaining(filters)`
- [ ] Data cached for 60 seconds (staleTime)
- [ ] Loading states while fetching
- [ ] Error handling with user-friendly messages

#### US-017: Add CSV Export to Dashboard
**Description:** As a manager, I want to export dashboard data to CSV so that I can analyze it in Excel.

**Acceptance Criteria:**
- [ ] "Export CSV" button above table
- [ ] Exports all filtered data (not just current page)
- [ ] CSV includes all table columns
- [ ] Filename: `quota-remaining-{date}.csv`
- [ ] Button shows loading state during generation

---

### Phase 4: Quota Transfers

#### US-018: Create Transfers Page Structure
**Description:** As a manager, I want a transfers page so that I can manage quota movements between vessels.

**Acceptance Criteria:**
- [ ] Transfers page at `/transfers`
- [ ] Page header: "Quota Transfers"
- [ ] Two sections: Transfer Form (top), Transfer History (bottom)
- [ ] Protected route (manager/admin only)

#### US-019: Build Transfer Form
**Description:** As a manager, I want a transfer form so that I can move quota between vessels.

**Acceptance Criteria:**
- [ ] Card with form fields in 2-column grid
- [ ] "From LLP" dropdown: shows "LLP - Vessel Name" format
- [ ] "To LLP" dropdown: same format, excludes selected From LLP
- [ ] "Species" dropdown: POP (141), NR (136), Dusky (172)
- [ ] "Amount (lbs)" number input: min 1, max 10,000,000, step 100
- [ ] "Transfer Date" date picker: defaults to today, max today
- [ ] "Notes" textarea: optional, max 500 characters
- [ ] Available quota display updates when From LLP and Species selected

#### US-020: Implement Transfer Validation
**Description:** As a manager, I want real-time validation so that I cannot submit invalid transfers.

**Acceptance Criteria:**
- [ ] "From" and "To" cannot be the same LLP (error: "Cannot transfer to same vessel")
- [ ] Amount must be > 0 (error: "Amount must be greater than 0")
- [ ] Amount cannot exceed available quota (error: "Insufficient quota. Available: X lbs")
- [ ] All required fields must be filled
- [ ] Submit button disabled until form is valid
- [ ] Validation errors shown inline below fields (red text)

#### US-021: Implement Transfer Submission
**Description:** As a manager, I want to submit transfers so that quota moves between vessels.

**Acceptance Criteria:**
- [ ] API route: `POST /api/transfers` creates transfer record
- [ ] Request body: from_llp, to_llp, species_code, pounds, transfer_date, notes
- [ ] Server validates: sufficient quota, different LLPs, valid species
- [ ] On success: toast notification, form resets, history refreshes
- [ ] On error: toast with error message, form preserved
- [ ] Submit button shows loading spinner during request

#### US-022: Build Transfer History Table
**Description:** As a manager, I want to see transfer history so that I can review past movements.

**Acceptance Criteria:**
- [ ] Table below transfer form
- [ ] Columns: Date, From (LLP + Vessel), To (LLP + Vessel), Species, Amount, Notes, Created By
- [ ] Sorted by date descending (newest first)
- [ ] Pagination: 25 rows per page
- [ ] Filter by date range (last 30 days default)
- [ ] Filter by species
- [ ] Search by vessel name or LLP

#### US-023: Add Transfer Export
**Description:** As a manager, I want to export transfer history so that I can share records.

**Acceptance Criteria:**
- [ ] "Export" dropdown with CSV, Excel, PDF options
- [ ] CSV: standard comma-separated format
- [ ] Excel: .xlsx with formatted headers
- [ ] PDF: formatted table with title and date range
- [ ] Exports filtered data based on current filters
- [ ] Filename includes date range

---

### Phase 5: Bycatch Alerts

#### US-024: Create Alerts Page Structure
**Description:** As a manager, I want an alerts page so that I can manage bycatch notifications.

**Acceptance Criteria:**
- [ ] Alerts page at `/alerts`
- [ ] Page header: "Bycatch Alerts"
- [ ] Tabs: Pending, Shared, Resolved, All
- [ ] Pending tab shows count badge (e.g., "Pending (3)")
- [ ] Protected route (manager/admin only)

#### US-025: Build Alert List View
**Description:** As a manager, I want to see alerts in a list so that I can review and act on them.

**Acceptance Criteria:**
- [ ] Card-based list layout (not table)
- [ ] Each card shows: Species, Status badge, Vessel (LLP), Amount, Location (DMS format)
- [ ] Status badges: yellow=Pending, green=Shared, blue=Resolved, gray=Dismissed
- [ ] Expandable details section (click to expand)
- [ ] Shared alerts show: shared timestamp, recipient count
- [ ] Resolved alerts show: resolved timestamp, resolved by

#### US-026: Add Alert Filters
**Description:** As a manager, I want to filter alerts so that I can find specific ones.

**Acceptance Criteria:**
- [ ] Filter row: Cooperative dropdown, Species dropdown, Date range picker
- [ ] Cooperative cascades from coop_members
- [ ] Species shows all species (target + PSC)
- [ ] Date range defaults to last 30 days
- [ ] Clear filters button
- [ ] Filters apply to current tab

#### US-027: Build Create Alert Form
**Description:** As a manager, I want to create alerts on behalf of vessels so that I can report bycatch.

**Acceptance Criteria:**
- [ ] "Create Alert" button opens modal/dialog
- [ ] Vessel (LLP) dropdown: "LLP - Vessel Name" format
- [ ] Species dropdown: all species
- [ ] GPS Latitude input: validates 50-72 degrees North (Alaska)
- [ ] GPS Longitude input: validates 130-180 degrees West (Alaska)
- [ ] Amount input: min 1, label changes based on species unit (lbs/count)
- [ ] Details textarea: optional, max 1000 chars
- [ ] Coordinate input supports both decimal and DMS format
- [ ] "Create" button submits, "Cancel" closes modal

#### US-028: Implement Alert Sharing
**Description:** As a manager, I want to share alerts with the fleet so that vessels are notified.

**Acceptance Criteria:**
- [ ] "Share" button on pending alert cards
- [ ] Clicking opens preview modal showing email content
- [ ] Preview shows: subject line, body text, recipient count
- [ ] "Send to Fleet" button triggers email via Resend
- [ ] API route: `PUT /api/alerts/{id}/share`
- [ ] On success: alert moves to Shared tab, toast notification
- [ ] Records: shared_at, shared_by, shared_recipient_count

#### US-029: Implement Alert Resolution
**Description:** As a manager, I want to resolve alerts so that I can mark hotspots as no longer active.

**Acceptance Criteria:**
- [ ] "Resolve" button on shared alert cards
- [ ] Confirmation dialog: "Mark this alert as resolved?"
- [ ] API route: `PUT /api/alerts/{id}/resolve`
- [ ] On success: alert moves to Resolved tab, toast notification
- [ ] Records: resolved_at, resolved_by

#### US-030: Implement Alert Dismissal
**Description:** As a manager, I want to dismiss alerts so that I can remove irrelevant reports.

**Acceptance Criteria:**
- [ ] "Dismiss" button on pending alert cards
- [ ] Confirmation dialog with optional reason field
- [ ] API route: `PUT /api/alerts/{id}/dismiss`
- [ ] Soft deletes: is_deleted=true, status="dismissed"
- [ ] Alert removed from active views
- [ ] Toast notification on success

---

### Phase 6: Vessel Owner Features

#### US-031: Create My Vessel Page
**Description:** As a vessel owner, I want to see my vessel's quota status so that I can plan trips.

**Acceptance Criteria:**
- [ ] My Vessel page at `/my-vessel`
- [ ] Page header: "My Vessel: {Vessel Name}"
- [ ] Shows only data for user's linked LLP
- [ ] Protected route (vessel_owner only)
- [ ] Redirect to 403 if user has no linked LLP

#### US-032: Build Vessel Quota Cards
**Description:** As a vessel owner, I want to see my remaining quota per species so that I know my limits.

**Acceptance Criteria:**
- [ ] 3 cards in a row: POP, NR, Dusky
- [ ] Each card shows: remaining lbs, % of allocation
- [ ] Color-coded by risk: red <10%, yellow 10-50%, green >50%
- [ ] Shows allocation amount for reference
- [ ] Cards have clear species labels

#### US-033: Build Vessel Transfer History
**Description:** As a vessel owner, I want to see my transfer history so that I can verify movements.

**Acceptance Criteria:**
- [ ] Section titled "Transfer History"
- [ ] Table columns: Date, Direction (IN/OUT), Species, Amount, Other Vessel
- [ ] IN transfers styled green with "Received from" label
- [ ] OUT transfers styled red with "Sent to" label
- [ ] Sorted by date descending
- [ ] Shows notes if present
- [ ] Read-only (no edit/delete)

#### US-034: Build Vessel Harvest Records
**Description:** As a vessel owner, I want to see my harvest records so that I can verify catches.

**Acceptance Criteria:**
- [ ] Section titled "Harvest Records"
- [ ] Table columns: Date, Species, Pounds, Processor
- [ ] Sorted by date descending
- [ ] Data from harvests table (eLandings sync)
- [ ] Read-only display
- [ ] Note explaining data source: "Data synced from eLandings"

#### US-035: Create Report Bycatch Page
**Description:** As a vessel owner, I want to report bycatch encounters so that I can alert my co-op.

**Acceptance Criteria:**
- [ ] Report page at `/report-bycatch`
- [ ] Page header: "Report Bycatch"
- [ ] Protected route (vessel_owner only)
- [ ] Pre-fills vessel's LLP (not editable)

#### US-036: Build Bycatch Report Form
**Description:** As a vessel owner, I want a simple form to report bycatch so that I can submit quickly.

**Acceptance Criteria:**
- [ ] GPS Latitude input with Alaska validation (50-72 N)
- [ ] GPS Longitude input with Alaska validation (130-180 W)
- [ ] Species dropdown: all species
- [ ] Amount input: label based on species unit
- [ ] Details textarea: optional, max 1000 chars
- [ ] "Submit Report" button
- [ ] Success message: "Report submitted. Your co-op manager will review."

#### US-037: Show Recent Reports
**Description:** As a vessel owner, I want to see my recent reports so that I can track their status.

**Acceptance Criteria:**
- [ ] Section below form: "Your Recent Reports"
- [ ] Shows last 5 reports from this vessel
- [ ] Each shows: species, amount, location, date, status
- [ ] Status: Pending (yellow), Shared (green), Dismissed (gray)

---

### Phase 7: File Upload & Reconciliation

#### US-038: Create Upload Page Structure
**Description:** As a manager, I want an upload page so that I can import eLandings data.

**Acceptance Criteria:**
- [ ] Upload page at `/upload`
- [ ] Page header: "File Upload"
- [ ] Two sections: Account Balance Upload, Catch Detail Upload
- [ ] Protected route (manager/admin only)

#### US-039: Build Account Balance Upload
**Description:** As a manager, I want to upload balance CSV files so that I can import eFish snapshots.

**Acceptance Criteria:**
- [ ] Section titled "Account Balance (CSV)"
- [ ] Drag-and-drop zone or file picker
- [ ] Accepts only .csv files
- [ ] Shows file name after selection
- [ ] "Upload" button to process
- [ ] Progress indicator during upload
- [ ] Validates required columns before import
- [ ] Shows success count and any errors

#### US-040: Implement Balance CSV Processing
**Description:** As a developer, I want CSV processing logic so that balance files are imported correctly.

**Acceptance Criteria:**
- [ ] API route: `POST /api/upload/balance`
- [ ] Validates columns: Balance Date, Account Id, Account Name, Species Group, etc.
- [ ] Checks for duplicates in file (warns but allows)
- [ ] Checks for duplicates in DB (prevents import of existing)
- [ ] Inserts valid records to efish_account_balance
- [ ] Returns: imported count, skipped count, errors array

#### US-041: Build Catch Detail Upload
**Description:** As a manager, I want to upload detail XLSX files so that I can import catch records.

**Acceptance Criteria:**
- [ ] Section titled "Catch Detail (Excel)"
- [ ] Drag-and-drop zone or file picker
- [ ] Accepts only .xlsx files
- [ ] Shows file name after selection
- [ ] "Upload" button to process
- [ ] Progress indicator during upload

#### US-042: Implement Detail XLSX Processing
**Description:** As a developer, I want XLSX processing logic so that detail files are imported correctly.

**Acceptance Criteria:**
- [ ] API route: `POST /api/upload/detail`
- [ ] Parses XLSX using a library (e.g., xlsx or exceljs)
- [ ] Validates required columns
- [ ] Handles Excel date formats (converts to ISO)
- [ ] Checks for duplicate report numbers
- [ ] Inserts to efish_account_detail
- [ ] Returns: imported count, skipped count, errors array

#### US-043: Create Account Balances View
**Description:** As a manager, I want to view imported balances so that I can review reconciliation data.

**Acceptance Criteria:**
- [ ] Page at `/reconciliation/balances`
- [ ] Table showing latest balance per coop/species
- [ ] Columns: Co-Op, Species, Balance Date, Initial, Transfers In/Out, Total, Catch, Remaining, % Taken
- [ ] Shows last upload timestamp
- [ ] Sortable columns

#### US-044: Create Catch Detail View
**Description:** As a manager, I want to view imported catch details so that I can audit records.

**Acceptance Criteria:**
- [ ] Page at `/reconciliation/detail`
- [ ] Table showing all imported catch records
- [ ] Columns: Date, Vessel, ADFG, Species, Weight, Processor, Report #
- [ ] Filter by date range, vessel
- [ ] Sortable columns
- [ ] Pagination

---

### Phase 8: Reference Data & Rosters

#### US-045: Create Rosters Page with Tabs
**Description:** As a user, I want a rosters page so that I can view reference data.

**Acceptance Criteria:**
- [ ] Rosters page at `/rosters`
- [ ] Page header: "Rosters"
- [ ] Tabs: Cooperatives, Members, Vessels, Processors, Species
- [ ] Read-only tables in each tab

#### US-046: Build Cooperatives Tab
**Description:** As a user, I want to view cooperatives so that I can see org structure.

**Acceptance Criteria:**
- [ ] Table columns: Name, Code, Coop ID
- [ ] Shows all 4 cooperatives (NP, SBS, OBSI, SOK)
- [ ] Sortable columns

#### US-047: Build Members Tab
**Description:** As a user, I want to view coop members so that I can see LLP assignments.

**Acceptance Criteria:**
- [ ] Table columns: Coop, LLP, Company Name, Vessel, Representative
- [ ] Filter by cooperative dropdown
- [ ] Shows all 46 members
- [ ] Sortable columns

#### US-048: Build Vessels Tab
**Description:** As a user, I want to view vessels so that I can see fleet details.

**Acceptance Criteria:**
- [ ] Table columns: Coop, Vessel Name, ADFG Number, Is Active
- [ ] Shows active status clearly
- [ ] Sortable columns

#### US-049: Build Processors Tab
**Description:** As a user, I want to view processors so that I can see processing facilities.

**Acceptance Criteria:**
- [ ] Table columns: Name, Code, Associated Coop
- [ ] Shows all 4 processors
- [ ] Sortable columns

#### US-050: Build Species Tab
**Description:** As a user, I want to view species codes so that I can reference them.

**Acceptance Criteria:**
- [ ] Table columns: Code, Name, Is PSC, Unit
- [ ] Shows all species (target + PSC)
- [ ] PSC species flagged clearly
- [ ] Sortable columns

#### US-051: Create Allocations Page
**Description:** As a user, I want to view allocations so that I can see quota assignments.

**Acceptance Criteria:**
- [ ] Allocations page at `/allocations`
- [ ] Page header: "Allocations"
- [ ] Tabs: TAC Summary, Vessel Allocations, PSC Allocations

#### US-052: Build TAC Summary Tab
**Description:** As a user, I want to view annual TAC so that I can see total limits.

**Acceptance Criteria:**
- [ ] Table columns: Species, TAC (mt), QS Pool %, TAC (lbs)
- [ ] Shows current year data
- [ ] Formatted numbers with separators

#### US-053: Build Vessel Allocations Tab
**Description:** As a user, I want to view vessel allocations so that I can see starting quotas.

**Acceptance Criteria:**
- [ ] Table columns: Coop, LLP, Vessel, POP, NR, Dusky, Total
- [ ] Filter by cooperative
- [ ] All amounts in lbs with formatting
- [ ] Sortable columns

#### US-054: Build PSC Allocations Tab
**Description:** As a user, I want to view PSC allocations so that I can see bycatch limits.

**Acceptance Criteria:**
- [ ] Table showing Halibut CV sector allocation
- [ ] Shows Chinook salmon cap: 1,200 fish (fleet-wide)
- [ ] Columns: Species, Year, Allocation
- [ ] Formatted numbers

---

### Phase 9: Data Export

#### US-055: Implement CSV Export Utility
**Description:** As a developer, I want a CSV export utility so that tables can be exported consistently.

**Acceptance Criteria:**
- [ ] Utility function: `exportToCsv(data, columns, filename)`
- [ ] Handles special characters (commas, quotes)
- [ ] Triggers browser download
- [ ] Works with filtered data

#### US-056: Implement Excel Export Utility
**Description:** As a developer, I want an Excel export utility so that tables can be exported as .xlsx.

**Acceptance Criteria:**
- [ ] Utility function: `exportToExcel(data, columns, filename)`
- [ ] Uses xlsx or exceljs library
- [ ] Formats headers as bold
- [ ] Auto-sizes columns
- [ ] Triggers browser download

#### US-057: Implement PDF Export Utility
**Description:** As a developer, I want a PDF export utility so that tables can be exported as formatted PDFs.

**Acceptance Criteria:**
- [ ] Utility function: `exportToPdf(data, columns, title, filename)`
- [ ] Uses jspdf + jspdf-autotable or similar
- [ ] Includes title and generation date
- [ ] Proper page breaks for long tables
- [ ] Landscape orientation for wide tables

#### US-058: Add Export to All Data Tables
**Description:** As a user, I want export buttons on all tables so that I can download data.

**Acceptance Criteria:**
- [ ] Dashboard table: CSV, Excel, PDF
- [ ] Transfer history: CSV, Excel, PDF
- [ ] Alert history: CSV, Excel, PDF
- [ ] Rosters tabs: CSV, Excel
- [ ] Allocations tabs: CSV, Excel
- [ ] Consistent "Export" dropdown button style

---

### Phase 10: Error Handling & Monitoring

#### US-059: Set Up Sentry Error Tracking
**Description:** As a developer, I want Sentry configured so that errors are tracked in production.

**Acceptance Criteria:**
- [ ] @sentry/nextjs package installed
- [ ] Sentry initialized in `sentry.client.config.ts` and `sentry.server.config.ts`
- [ ] Environment-specific DSN (production only)
- [ ] Source maps uploaded on build
- [ ] User context attached to errors (user_id, org_id, role)

#### US-060: Create Error Boundary Components
**Description:** As a user, I want graceful error handling so that the app doesn't crash completely.

**Acceptance Criteria:**
- [ ] Global error boundary in root layout
- [ ] Feature-level error boundaries for each major section
- [ ] Error UI shows: "Something went wrong", Retry button, Report link
- [ ] Errors logged to Sentry automatically
- [ ] Development mode shows error details

#### US-061: Implement Toast Notification System
**Description:** As a user, I want toast notifications so that I receive feedback on actions.

**Acceptance Criteria:**
- [ ] Toast provider in root layout
- [ ] `useToast()` hook for triggering toasts
- [ ] Variants: success (green), error (red), warning (amber), info (blue)
- [ ] Auto-dismiss after 5 seconds
- [ ] Manual dismiss button
- [ ] Stacks multiple toasts

#### US-062: Create Loading States
**Description:** As a user, I want loading indicators so that I know when data is being fetched.

**Acceptance Criteria:**
- [ ] Skeleton components for cards and tables
- [ ] Spinner component for buttons and small areas
- [ ] Full-page loading for route transitions
- [ ] Consistent styling across app

#### US-063: Set Up Vercel Analytics
**Description:** As a developer, I want analytics so that I can monitor performance.

**Acceptance Criteria:**
- [ ] @vercel/analytics package installed
- [ ] Analytics component in root layout
- [ ] Web Vitals tracking enabled
- [ ] Works in production only

---

### Phase 11: Testing

#### US-064: Set Up Jest/Vitest for Unit Tests
**Description:** As a developer, I want a unit test framework so that I can test components and utilities.

**Acceptance Criteria:**
- [ ] Vitest configured (faster than Jest for Vite/Next)
- [ ] React Testing Library installed
- [ ] Test utilities for rendering with providers
- [ ] `npm run test:unit` script
- [ ] Coverage reporting configured

#### US-065: Write Unit Tests for Auth Hooks
**Description:** As a developer, I want auth hooks tested so that authentication logic is verified.

**Acceptance Criteria:**
- [ ] Tests for `useAuth()` hook
- [ ] Tests for `useRequireAuth()` hook
- [ ] Tests for `useRequireRole()` hook
- [ ] Mock Supabase client in tests
- [ ] >80% coverage for auth hooks

#### US-066: Write Unit Tests for Data Utilities
**Description:** As a developer, I want utility functions tested so that calculations are verified.

**Acceptance Criteria:**
- [ ] Tests for CSV export utility
- [ ] Tests for Excel export utility
- [ ] Tests for coordinate validation (Alaska bounds)
- [ ] Tests for number formatting
- [ ] >80% coverage for utilities

#### US-067: Set Up Playwright for E2E Tests
**Description:** As a developer, I want E2E tests so that critical flows are verified.

**Acceptance Criteria:**
- [ ] Playwright configured
- [ ] Test database or mocks for E2E
- [ ] `npm run test:e2e` script
- [ ] CI configuration for E2E runs

#### US-068: Write E2E Tests for Login Flow
**Description:** As a developer, I want login tested E2E so that auth works correctly.

**Acceptance Criteria:**
- [ ] Test: successful login redirects to dashboard
- [ ] Test: invalid credentials show error
- [ ] Test: logout redirects to login
- [ ] Test: protected route redirects when not logged in

#### US-069: Write E2E Tests for Transfer Flow
**Description:** As a developer, I want transfer flow tested E2E so that the critical path works.

**Acceptance Criteria:**
- [ ] Test: create transfer with valid data succeeds
- [ ] Test: transfer appears in history
- [ ] Test: validation prevents invalid transfers
- [ ] Test: quota updates after transfer

#### US-070: Write E2E Tests for Alert Flow
**Description:** As a developer, I want alert flow tested E2E so that bycatch notifications work.

**Acceptance Criteria:**
- [ ] Test: create alert succeeds
- [ ] Test: share alert changes status
- [ ] Test: resolve alert changes status
- [ ] Test: dismiss alert removes from view

---

### Phase 12: Deployment & Documentation

#### US-071: Configure Vercel Deployment
**Description:** As a developer, I want Vercel configured so that the app deploys automatically.

**Acceptance Criteria:**
- [ ] Vercel project created and linked
- [ ] Environment variables configured in Vercel
- [ ] Production branch: main
- [ ] Preview deployments for PRs
- [ ] Custom domain configured (if available)

#### US-072: Create Environment Configuration
**Description:** As a developer, I want environment configs so that dev/staging/prod are separate.

**Acceptance Criteria:**
- [ ] `.env.local` for development
- [ ] `.env.example` with all required variables documented
- [ ] Vercel environment variables for production
- [ ] Separate Supabase project for production (or same with caution)

#### US-073: Write Developer Documentation
**Description:** As a developer, I want documentation so that others can contribute.

**Acceptance Criteria:**
- [ ] README.md with: setup instructions, scripts, architecture overview
- [ ] CONTRIBUTING.md with: code style, PR process, testing requirements
- [ ] API documentation for all endpoints
- [ ] Component documentation (Storybook optional)

#### US-074: Create User Guide
**Description:** As a user, I want a help guide so that I can learn how to use the app.

**Acceptance Criteria:**
- [ ] Help page at `/help` or modal
- [ ] Sections for each major feature
- [ ] Screenshots or GIFs for key workflows
- [ ] FAQ section
- [ ] Contact support link

#### US-075: Final QA and Launch Checklist
**Description:** As a team, I want a launch checklist so that nothing is missed.

**Acceptance Criteria:**
- [ ] All user stories completed and tested
- [ ] Performance audit passed (Lighthouse >90)
- [ ] Accessibility audit passed (axe-core)
- [ ] Security review completed
- [ ] Data migration verified (if separate DB)
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented
- [ ] Stakeholder sign-off obtained

---

## 10. Functional Requirements

- FR-1: Users must authenticate with email/password via Supabase Auth
- FR-2: All data access must be filtered by org_id (multi-tenant isolation)
- FR-3: Role-based access must restrict features per user role
- FR-4: Dashboard must show real-time quota remaining (calculated view)
- FR-5: Transfers must validate sufficient quota before submission
- FR-6: Transfers must be recorded with full audit trail (created_by, timestamps)
- FR-7: Bycatch alerts must validate GPS coordinates are in Alaska waters (50-72 N, 130-180 W)
- FR-8: Alert sharing must send email to all vessel contacts in the organization (via Resend)
- FR-9: File uploads must validate format and detect duplicates before import
- FR-10: All data tables must support sorting, filtering, and pagination
- FR-11: All data tables must support export to CSV, Excel, and PDF
- FR-12: Vessel owners must only see their own vessel's data
- FR-13: Soft deletes must be used for transfers and alerts (is_deleted flag)
- FR-14: All forms must show loading states during submission
- FR-15: All errors must be logged to Sentry with user context

---

## 11. Non-Goals (Out of Scope)

- Mobile native app (iOS/Android)
- Offline mode / PWA capabilities
- Real-time WebSocket updates (polling is sufficient)
- Dark mode / theme customization
- Multi-language / internationalization
- Custom report builder
- Advanced analytics / forecasting
- User registration (admin creates accounts)
- Social login (Google, Microsoft, etc.)
- Two-factor authentication (MFA)
- Processor view implementation (placeholder only)
- eLandings API integration (manual upload only for v1)

---

## 12. Technical Considerations

### 12.1 Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript (strict mode) |
| Styling | Tailwind CSS |
| Components | shadcn/ui |
| State | TanStack Query (server state) |
| Forms | React Hook Form + Zod |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth |
| Email | Resend |
| Hosting | Vercel |
| Monitoring | Sentry |
| Analytics | Vercel Analytics |

### 12.2 Existing Infrastructure

- Supabase project with PostgreSQL database
- RLS policies already configured for multi-tenancy
- Supabase Auth with existing user accounts
- Resend configured for email delivery

### 12.3 Database Schema

- No schema changes required (preserve existing)
- Use existing views (quota_remaining)
- TypeScript types generated from schema via Supabase CLI

### 12.4 Performance Targets

| Metric | Target |
|--------|--------|
| Dashboard load | <2 seconds (p95) |
| API responses | <500ms (p95) |
| File upload | <30 seconds for 10MB files |
| Concurrent users | 100+ |

### 12.5 Browser Support

- Chrome 90+ (primary)
- Safari 14+
- Firefox 88+
- Edge 90+

### 12.6 Brand Colors

| Name | Hex | Usage |
|------|-----|-------|
| Navy (Primary) | #1e3a5f | Headers, buttons, links |
| Navy Light | #2d4a6f | Hover states |
| Success | #10b981 | Positive actions, good status |
| Warning | #f59e0b | Warning status (10-50%) |
| Error | #ef4444 | Errors, critical status (<10%) |

---

## 13. Success Metrics

- All 75 user stories completed and passing tests
- Test coverage >80% for unit tests
- Lighthouse performance score >90
- Zero critical accessibility violations
- Dashboard loads in <2 seconds
- Successful parallel operation with Streamlit app
- User acceptance testing passed by stakeholders

---

## 14. Open Questions

1. Should we implement session timeout with warning modal?
2. Do we need audit log viewing UI for admins?
3. Should export include timestamp in filename?
4. Do we need confirmation dialogs for all destructive actions?
5. Should filters be bookmarkable (URL state)?

---

## Appendix A: Cooperative Members (46 LLPs)

### NP - North Pacific Seafoods Cooperative (Coop ID: 408)

| LLP | Company Name | Vessel | Representative |
|-----|--------------|--------|----------------|
| LLP1 | Company A | Topaz | Rep A |
| LLP2 | Company B | Enterprise | Rep B |
| LLP3 | Company C | Alaskan | Rep C |
| LLP4 | Company D | Nichole | Rep D |
| LLP5 | Company E | Leslie Lee | Rep E |
| LLP6 | Company F | Sea Mac | Rep F |
| LLP7 | Company G | Caravelle | Rep G |

### SBS - Silver Bay Seafoods Cooperative (Coop ID: 407)

| LLP | Company Name | Vessel | Representative |
|-----|--------------|--------|----------------|
| LLP8 | Company H | Mar Del Norte | Rep H |
| LLP9 | Company I | Chellissa | Rep I |
| LLP10 | Company J | Mar Pacifico | Rep J |
| LLP11 | Company K | Vanguard | Rep K |
| LLP12 | Company L | Evie Grace | Rep L |
| LLP13 | Company M | American Eagle | Rep M |
| LLP14 | Company N | Dawn | Rep N |

### OBSI - Ocean Beauty Seafoods Inc. Cooperative (Coop ID: 409)

| LLP | Company Name | Vessel | Representative |
|-----|--------------|--------|----------------|
| LLP15 | Company O | Pacific Star | Rep O |
| LLP16 | Company P | Bay Islander | Rep P |
| LLP17 | Company Q | Marathon | Rep Q |
| LLP18 | Company R | Stella | Rep R |

### SOK - Southeast Ocean Klawock Cooperative (Coop ID: 411)

| LLP | Company Name | Vessel | Representative |
|-----|--------------|--------|----------------|
| LLP19 | Company S | Michelle Renee | Rep S |
| LLP20 | Company T | Excalibur II | Rep T |
| LLP21 | Company U | Collier Brothers | Rep U |
| LLP22 | Company V | Walter N | Rep V |
| LLP23 | Company W | Gold Rush | Rep W |
| LLP24 | Company X | Elizabeth F | Rep X |
| LLP25 | Company Y | Marcy J | Rep Y |
| LLP26 | Company Z | Rosella | Rep Z |

**Note:** The actual LLP numbers, company names, and representatives should be obtained from the client's roster files. The above are placeholders.

---

## Appendix B: Active Vessels

| Coop | Vessel Name | ADF&G # | Active? |
|------|-------------|---------|---------|
| NP | Topaz | 40250 | Yes |
| NP | Enterprise | 20339 | Yes |
| NP | Alaskan | 3734 | Yes |
| NP | Nichole | 60056 | Yes |
| NP | Alaska Beauty | 22011 | No |
| NP | Leslie Lee | 56119 | Yes |
| NP | Sea Mac | 6151 | Yes |
| NP | Caravelle | 57634 | Yes |
| OBI | Pacific Star | 55038 | Yes |
| OBI | Bay Islander | 49618 | Yes |
| OBI | New Life | 21845 | No |
| OBI | Marathon | 49617 | Sometimes |
| OBI | Taasinge | 38001 | No |
| OBI | Stella | 71208 | Yes |
| OBI | Green Hope | 47790 | No |
| OBI | Sunset Bay | 35527 | No |
| SBS | Mar Del Norte | 21650 | Sometimes |
| SBS | Chellissa | 70459 | Yes |
| SBS | Mar Pacifico | 23131 | Yes |
| SBS | Laura | 21591 | No |
| SBS | Vanguard | 39964 | Yes |
| SBS | Evie Grace | 78702 | Yes |
| SBS | American Eagle | 39 | Yes |
| SBS | Hickory Wind | 47795 | No |
| SBS | Dawn | 926 | Yes |
| SOK | Arctic Wind | 1112 | No |
| SOK | Cape Kiwanda | 61432 | No |
| SOK | Arctic Ram | 57117 | No |
| SOK | Traveler | 58821 | No |
| SOK | Marcy J | 55 | Sometimes |
| SOK | Rosella | 21732 | Sometimes |
| SOK | Michelle Renee | 61244 | Yes |
| SOK | Pacific Ram | 61792 | No |
| SOK | Ocean Storm | 64667 | No |
| SOK | Excalibur II | 54653 | Yes |
| SOK | Collier Brothers | 54648 | Yes |
| SOK | Walter N | 34919 | Yes |
| SOK | Gold Rush | 40309 | Yes |
| SOK | Elizabeth F | 14767 | Yes |
| SOK | Pacific Storm | 76731 | No |

---

## Appendix C: Processor Codes

| Processor Name | Processor Code | Associated Coop |
|----------------|----------------|-----------------|
| Pacific Seafoods | 36268 | SOK |
| Silver Bay Seafoods | 35457 | SBS |
| Silver Bay Seafoods (Old OBI Plant) | 36289 | OBSI |
| North Pacific Seafoods | 5342 | NP |

---

## Appendix D: Species Codes

### Target Species (Quota-Managed)

| Code | Name | Unit |
|------|------|------|
| 141 | Pacific Ocean Perch (POP) | lbs |
| 136 | Northern Rockfish (NR) | lbs |
| 172 | Dusky Rockfish | lbs |

### Prohibited Species Catch (PSC)

| Code | Name | Unit | Notes |
|------|------|------|-------|
| 200 | Pacific Halibut | lbs | CV Sector allocation |
| - | Chinook Salmon | count | 1,200 cap fleet-wide |

---

## Appendix E: Environment Variables

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Resend (Email)
RESEND_API_KEY=re_your_api_key
RESEND_FROM_EMAIL=alerts@fishermenfirst.com

# Sentry (Production only)
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_AUTH_TOKEN=your-auth-token

# Vercel (Auto-injected)
VERCEL_URL=your-deployment.vercel.app
```

---

## Appendix F: API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/quota/summary | Dashboard KPI data |
| GET | /api/quota/remaining | Paginated quota table |
| POST | /api/transfers | Create new transfer |
| GET | /api/transfers | List transfers (filtered) |
| GET | /api/alerts | List bycatch alerts |
| POST | /api/alerts | Create new alert |
| PUT | /api/alerts/[id]/share | Share alert to fleet |
| PUT | /api/alerts/[id]/resolve | Resolve alert |
| PUT | /api/alerts/[id]/dismiss | Dismiss alert |
| POST | /api/upload/balance | Upload eFish balance CSV |
| POST | /api/upload/detail | Upload eFish detail XLSX |
| GET | /api/rosters/cooperatives | List cooperatives |
| GET | /api/rosters/members | List coop members |
| GET | /api/rosters/vessels | List vessels |
| GET | /api/rosters/processors | List processors |
| GET | /api/rosters/species | List species |
| GET | /api/allocations/tac | Annual TAC |
| GET | /api/allocations/vessel | Vessel allocations |

---

[/PRD]
