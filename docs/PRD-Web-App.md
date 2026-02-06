# Product Requirements Document: Fishermen First Web Application

**Document Version:** 1.0
**Date:** January 24, 2026
**Status:** Draft
**Author:** Product Team

---

## Executive Summary

Fishermen First is a multi-tenant SaaS platform for Alaska fishing cooperatives participating in the Central GOA Rockfish Program. The platform enables real-time quota tracking, inter-vessel transfers, bycatch coordination, and regulatory compliance.

This PRD defines requirements for rebuilding the current Streamlit prototype as a production-grade web application with improved performance, mobile support, and scalability.

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Goals & Success Metrics](#2-goals--success-metrics)
3. [User Personas](#3-user-personas)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Technical Architecture](#6-technical-architecture)
7. [Data Model](#7-data-model)
8. [API Specification](#8-api-specification)
9. [Security Requirements](#9-security-requirements)
10. [Integration Requirements](#10-integration-requirements)
11. [UI/UX Requirements](#11-uiux-requirements)
12. [Deployment & Operations](#12-deployment--operations)
13. [Migration Plan](#13-migration-plan)
14. [Appendices](#appendices)

---

## 1. Product Overview

### 1.1 Problem Statement

Alaska fishing cooperatives manage quota allocations across 46+ vessels and 3 target species. Current challenges include:

- **No real-time visibility** into fleet-wide quota consumption
- **Manual transfer tracking** via spreadsheets prone to errors
- **Delayed bycatch communication** putting fleet at regulatory risk
- **Reconciliation pain** between internal tracking and official eLandings records

### 1.2 Solution

A web-based platform providing:

- **Real-time dashboard** showing quota status with risk indicators
- **Digital transfer workflow** with validation and audit trails
- **Fleet-wide bycatch alerts** via email broadcast
- **eLandings reconciliation** via CSV/XLSX upload
- **Role-based access** for managers, vessel owners, and processors

### 1.3 Scope

| In Scope | Out of Scope (v1) |
|----------|-------------------|
| Quota dashboard & monitoring | Mobile native app |
| Transfer management | Offline mode |
| Bycatch alert system | Real-time WebSocket updates |
| File upload reconciliation | Advanced analytics/forecasting |
| Vessel owner self-service | Multi-language support |
| User management | Custom report builder |

### 1.4 Target Users

- **4 cooperatives** (Silver Bay, North Pacific, OBSI, Star of Kodiak)
- **46 LLP holders** (vessel owners/operators)
- **~10 manager users** per organization
- **4 processor contacts**

---

## 2. Goals & Success Metrics

### 2.1 Business Goals

| Goal | Target | Measurement |
|------|--------|-------------|
| Reduce quota tracking errors | 90% reduction | Error reports vs baseline |
| Speed up transfer processing | <5 min per transfer | Time from request to completion |
| Improve bycatch response time | <30 min to fleet notification | Time from report to email delivery |
| Increase user adoption | 80% of vessel owners active | Monthly active users |

### 2.2 Product Goals

| Goal | Success Criteria |
|------|-----------------|
| Feature parity with Streamlit | All 11 features ported |
| Improved performance | Dashboard load <2s (p95) |
| Mobile responsiveness | Usable on tablet/phone |
| Zero data loss | 100% audit trail preservation |

### 2.3 Key Performance Indicators (KPIs)

- **Daily Active Users (DAU):** Target 30+
- **Transfer completion rate:** >95% success
- **Alert delivery rate:** >98% email delivery
- **System uptime:** 99.5%
- **Error rate:** <0.1% of requests

---

## 3. User Personas

### 3.1 Cooperative Manager (Primary)

**Profile:** Sarah, Operations Manager at Silver Bay Seafoods

**Demographics:**
- 45 years old, based in Sitka, AK
- 15+ years in fishing industry
- Moderate technical proficiency
- Uses laptop primarily, tablet occasionally

**Goals:**
- Monitor fleet quota status at a glance
- Process transfer requests quickly
- Notify fleet of bycatch hotspots immediately
- Reconcile records with eLandings monthly

**Pain Points:**
- Current spreadsheet tracking is error-prone
- Phone calls to coordinate transfers are time-consuming
- Delayed bycatch info leads to regulatory issues

**Key Tasks:**
1. Check dashboard for at-risk vessels (daily)
2. Process 2-3 transfers per week
3. Review and share bycatch alerts (as needed)
4. Upload eLandings reconciliation files (monthly)

### 3.2 Vessel Owner (Secondary)

**Profile:** Captain Mike, Owner/Operator of F/V Northern Star

**Demographics:**
- 52 years old, based in Kodiak, AK
- Limited connectivity while at sea
- Basic smartphone proficiency
- Accesses system via phone/tablet

**Goals:**
- Know remaining quota before each trip
- See transfer history for verification
- Report bycatch encounters quickly
- Trust the system matches official records

**Pain Points:**
- Can't easily check quota status at sea
- Transfer confirmations are slow
- No easy way to report bycatch to managers

**Key Tasks:**
1. Check own quota remaining (before trips)
2. View transfer history (weekly)
3. Report bycatch encounters (as needed)
4. Verify harvest records match expectations

### 3.3 System Administrator (Tertiary)

**Profile:** IT Admin managing user access

**Goals:**
- Onboard new users efficiently
- Manage role assignments
- Monitor system health

**Key Tasks:**
1. Create user accounts
2. Assign roles and permissions
3. Reset passwords
4. View audit logs

### 3.4 Processor Contact (Tertiary)

**Profile:** Plant manager at processing facility

**Goals:**
- View incoming catch expectations
- Track processor-specific limits

**Key Tasks:**
1. View processor dashboard (future feature)
2. Receive bycatch alerts

---

## 4. Functional Requirements

### 4.1 Authentication & Authorization

#### FR-AUTH-001: User Login
**Priority:** P0 (Critical)

**Description:** Users authenticate with email and password.

**Acceptance Criteria:**
- [ ] Email/password login form
- [ ] Password requirements: 8+ chars, 1 uppercase, 1 number
- [ ] "Forgot password" flow with email reset
- [ ] Session persists for 24 hours
- [ ] Automatic logout after 30 min inactivity
- [ ] Clear error messages for invalid credentials

#### FR-AUTH-002: Role-Based Access Control
**Priority:** P0 (Critical)

**Description:** Features restricted by user role.

| Role | Dashboard | Transfers | Bycatch Mgmt | Upload | My Vessel | Report Bycatch |
|------|-----------|-----------|--------------|--------|-----------|----------------|
| admin | ✓ Full | ✓ Full | ✓ Full | ✓ | - | - |
| manager | ✓ Full | ✓ Full | ✓ Full | ✓ | - | - |
| vessel_owner | - | - | - | - | ✓ Own | ✓ |
| processor | - | - | View only | - | - | - |

**Acceptance Criteria:**
- [ ] Unauthorized routes redirect to appropriate page
- [ ] Navigation only shows permitted features
- [ ] API returns 403 for unauthorized requests
- [ ] Role stored in user_profiles table

#### FR-AUTH-003: Multi-Tenancy Isolation
**Priority:** P0 (Critical)

**Description:** Users only see data for their organization.

**Acceptance Criteria:**
- [ ] All queries filtered by org_id
- [ ] RLS policies enforce at database level
- [ ] No cross-org data leakage possible
- [ ] Org context set on login, verified on each request

---

### 4.2 Dashboard

#### FR-DASH-001: Quota Summary Cards
**Priority:** P0 (Critical)

**Description:** Display fleet-wide quota metrics.

**Display Elements:**
- Total vessels in fleet
- Vessels at critical risk (<10% any species)
- POP remaining (lbs + % of total allocation)
- Northern Rockfish remaining (lbs + %)
- Dusky remaining (lbs + %)

**Acceptance Criteria:**
- [ ] Data refreshes every 60 seconds
- [ ] Shows loading state while fetching
- [ ] Handles empty state gracefully
- [ ] Numbers formatted with thousands separators

#### FR-DASH-002: At-Risk Vessels Panel
**Priority:** P0 (Critical)

**Description:** Highlight vessels needing attention.

**Risk Levels:**
- 🔴 Critical: <10% remaining (any species)
- 🟡 Warning: 10-50% remaining
- 🟢 OK: >50% remaining

**Acceptance Criteria:**
- [ ] Shows top 7 at-risk vessels
- [ ] Sorted by lowest % remaining
- [ ] Color-coded status indicators
- [ ] Clicking vessel filters main table

#### FR-DASH-003: Quota Data Table
**Priority:** P0 (Critical)

**Description:** Detailed quota breakdown per vessel.

**Columns:**
| Column | Sort | Filter |
|--------|------|--------|
| Co-Op | ✓ | ✓ (dropdown) |
| Vessel | ✓ | ✓ (search) |
| LLP | ✓ | - |
| Species | - | ✓ (multi-select) |
| Allocation | ✓ | - |
| Remaining | ✓ | - |
| % Remaining | ✓ (default) | - |

**Acceptance Criteria:**
- [ ] Default sort: % remaining ascending (lowest first)
- [ ] Pagination: 25/50/100 rows per page
- [ ] % column color-coded by risk level
- [ ] Inline progress bar visualization
- [ ] Export to CSV button

#### FR-DASH-004: Cooperative Filter
**Priority:** P1 (High)

**Description:** Filter dashboard by cooperative.

**Acceptance Criteria:**
- [ ] Dropdown with all cooperatives
- [ ] "All Cooperatives" default option
- [ ] Selecting co-op filters all dashboard components
- [ ] Vessel dropdown cascades (shows only co-op's vessels)
- [ ] Clear filters button resets to default

---

### 4.3 Quota Transfers

#### FR-XFER-001: Create Transfer
**Priority:** P0 (Critical)

**Description:** Record quota movement between vessels.

**Form Fields:**
| Field | Type | Validation |
|-------|------|------------|
| From LLP | Dropdown | Required |
| To LLP | Dropdown | Required, ≠ From |
| Species | Dropdown | Required (POP/NR/Dusky) |
| Amount (lbs) | Number | 1 - 10,000,000 |
| Transfer Date | Date | Required, ≤ today |
| Notes | Text | Optional, max 500 chars |

**Acceptance Criteria:**
- [ ] Show available quota for selected From LLP
- [ ] Validate amount ≤ available quota (real-time)
- [ ] Prevent same LLP in From and To
- [ ] Success message with transfer details
- [ ] Transfer appears in history immediately
- [ ] Quota remaining updates without page refresh

#### FR-XFER-002: Transfer History
**Priority:** P0 (Critical)

**Description:** View all transfers with filtering.

**Columns:**
- Date
- From LLP / Vessel
- To LLP / Vessel
- Species
- Amount (lbs)
- Notes
- Created By

**Acceptance Criteria:**
- [ ] Reverse chronological order (newest first)
- [ ] Filter by date range
- [ ] Filter by species
- [ ] Search by vessel name or LLP
- [ ] Export to CSV

#### FR-XFER-003: Transfer Validation
**Priority:** P0 (Critical)

**Description:** Prevent invalid transfers.

**Validation Rules:**
1. Source vessel must have sufficient quota
2. Amount must be positive
3. Cannot transfer to same vessel
4. Species must be valid target species
5. Year must be current fishing year

**Acceptance Criteria:**
- [ ] Real-time validation as user types
- [ ] Clear error messages for each rule
- [ ] Submit button disabled until valid
- [ ] Server-side validation as backup

---

### 4.4 Bycatch Alerts

#### FR-BYCA-001: Alert List View
**Priority:** P0 (Critical)

**Description:** Display bycatch alerts with status tabs.

**Tabs:**
- Pending (actionable by manager)
- Shared (sent to fleet)
- Resolved (historical)
- All (combined view)

**Alert Card Display:**
- Species + Status badge
- Vessel name (LLP)
- Amount + unit (lbs or count)
- GPS coordinates (DMS format)
- Reported timestamp
- Details (expandable)

**Acceptance Criteria:**
- [ ] Pending count shown as badge on tab
- [ ] Filter by cooperative, species, date range
- [ ] Sort by date (newest first)
- [ ] Responsive card layout

#### FR-BYCA-002: Create Alert (Manager)
**Priority:** P0 (Critical)

**Description:** Manager creates alert on behalf of vessel.

**Form Fields:**
| Field | Type | Validation |
|-------|------|------------|
| Vessel (LLP) | Dropdown | Required |
| Species | Dropdown | Required (PSC only) |
| Latitude | Coordinate | 50-72°N (Alaska) |
| Longitude | Coordinate | 130-180°W (Alaska) |
| Amount | Number | >0 |
| Details | Text | Optional, max 1000 chars |

**Acceptance Criteria:**
- [ ] GPS input supports both DMS and decimal
- [ ] Real-time coordinate validation
- [ ] Map preview of location (optional)
- [ ] Creates alert with status="pending"

#### FR-BYCA-003: Share Alert
**Priority:** P0 (Critical)

**Description:** Send alert to all fleet vessel contacts.

**Workflow:**
1. Manager clicks "Share" on pending alert
2. Preview modal shows email content + recipient count
3. Confirm triggers email send
4. Alert status → "shared"

**Email Content:**
```
Subject: Bycatch Alert - {Species} Reported Near {Location}

A bycatch hotspot has been reported:

Species: {species_name}
Amount: {amount} {unit}
Location: {latitude}, {longitude}
Reported: {timestamp}

Details: {details}

Please take precautions when fishing in this area.

- Fishermen First Alert System
```

**Acceptance Criteria:**
- [ ] Preview shows exact email to be sent
- [ ] Recipient count from vessel_contacts table
- [ ] Loading state during send
- [ ] Success/error feedback
- [ ] Records shared_at, shared_by, recipient_count
- [ ] Email delivery logged in alert_email_log

#### FR-BYCA-004: Resolve Alert
**Priority:** P1 (High)

**Description:** Mark shared alert as resolved.

**Acceptance Criteria:**
- [ ] Only available for "shared" status alerts
- [ ] Confirmation dialog before resolving
- [ ] Records resolved_at and resolved_by
- [ ] Alert moves to Resolved tab

#### FR-BYCA-005: Dismiss Alert
**Priority:** P1 (High)

**Description:** Dismiss irrelevant pending alert.

**Acceptance Criteria:**
- [ ] Only available for "pending" status alerts
- [ ] Confirmation dialog with reason field
- [ ] Soft deletes (is_deleted=true, status="dismissed")
- [ ] Alert removed from active views

---

### 4.5 Vessel Owner Features

#### FR-VO-001: My Vessel Dashboard
**Priority:** P0 (Critical)

**Description:** Vessel owner views own quota status.

**Sections:**
1. **Quota Cards** (3 species)
   - Remaining lbs + % of allocation
   - Color-coded risk indicator

2. **Transfer History**
   - Direction: IN (received) / OUT (given)
   - Species, amount, date, other party

3. **Harvest Records**
   - Date, species, pounds, processor
   - From eLandings sync

**Acceptance Criteria:**
- [ ] Only shows data for user's linked LLP
- [ ] Read-only (no editing capabilities)
- [ ] Mobile-optimized layout
- [ ] Clear labeling of data sources

#### FR-VO-002: Report Bycatch
**Priority:** P1 (High)

**Description:** Vessel owner reports bycatch encounter.

**Form Fields:**
- GPS coordinates (current location default if available)
- Bycatch species (PSC dropdown)
- Amount (with appropriate unit)
- Details (optional)

**Acceptance Criteria:**
- [ ] Creates alert with status="pending"
- [ ] Pre-fills vessel's LLP
- [ ] Confirmation message explains manager review
- [ ] Shows recent 5 reports from this vessel

---

### 4.6 File Upload & Reconciliation

#### FR-FILE-001: Account Balance Upload
**Priority:** P1 (High)

**Description:** Import eFish balance CSV.

**File Format:** CSV (coopaccountbalance.csv)

**Required Columns:**
- Balance Date, Account Id, Account Name
- Species Group, Species Group Id
- Initial Quota, Transfers In, Transfers Out
- Total Quota, Total Catch, Remaining Quota
- Percent Taken

**Acceptance Criteria:**
- [ ] Drag-and-drop or file picker
- [ ] Column validation with clear errors
- [ ] Duplicate detection (date + account + species)
- [ ] Preview before import
- [ ] Progress indicator for large files
- [ ] Success count + any skipped records

#### FR-FILE-002: Catch Detail Upload
**Priority:** P1 (High)

**Description:** Import eFish detail XLSX.

**File Format:** XLSX (coopaccountdetail.xlsx)

**Required Columns:**
- Catch Activity Date, Vessel Name, ADFG
- Report Number, Species Name, Weight Posted
- Processor Permit, Landing Date
- Gear Code, Reporting Area

**Acceptance Criteria:**
- [ ] Handles Excel date formats
- [ ] Duplicate detection by Report Number
- [ ] Preview first 10 rows
- [ ] Import progress indicator
- [ ] Error log for failed rows

#### FR-FILE-003: Account Balance View
**Priority:** P1 (High)

**Description:** Display imported balance records.

**Acceptance Criteria:**
- [ ] Shows latest balance per coop/species
- [ ] Last upload timestamp
- [ ] Sortable columns
- [ ] Compare with quota_remaining (visual diff)

#### FR-FILE-004: Catch Detail View
**Priority:** P2 (Medium)

**Description:** Display imported catch records.

**Acceptance Criteria:**
- [ ] All records from account_detail_raw
- [ ] Filter by date range, vessel
- [ ] Species code mapping display
- [ ] Export capability

---

### 4.7 Reference Data Views

#### FR-REF-001: Cooperatives List
**Priority:** P2 (Medium)

**Description:** View all cooperatives.

**Columns:** Name, Code, ID, Vessel Count

#### FR-REF-002: Members/Vessels List
**Priority:** P2 (Medium)

**Description:** View all coop members with vessels.

**Columns:** Coop, LLP, Company Name, Vessel, Representative
**Filter:** By cooperative

#### FR-REF-003: Allocations View
**Priority:** P2 (Medium)

**Description:** View annual allocations.

**Tabs:**
1. TAC Summary (annual totals by species)
2. Vessel Allocations (per-vessel starting quota)
3. PSC Allocations (halibut limits)

#### FR-REF-004: Species Reference
**Priority:** P3 (Low)

**Description:** View species codes and types.

**Columns:** Code, Name, Is PSC, Unit

---

### 4.8 User Management (Admin)

#### FR-USER-001: User List
**Priority:** P1 (High)

**Description:** View all users in organization.

**Columns:** Email, Name, Role, LLP (if vessel_owner), Last Login, Status

#### FR-USER-002: Create User
**Priority:** P1 (High)

**Description:** Invite new user to platform.

**Form Fields:**
- Email (required)
- Role (dropdown)
- LLP (if vessel_owner role)
- Processor Code (if processor role)

**Acceptance Criteria:**
- [ ] Sends invitation email
- [ ] User sets password on first login
- [ ] Validates email format
- [ ] Prevents duplicate emails

#### FR-USER-003: Edit User
**Priority:** P1 (High)

**Description:** Modify user role or linked entity.

**Acceptance Criteria:**
- [ ] Cannot change email
- [ ] Role change takes effect immediately
- [ ] Audit log of changes

#### FR-USER-004: Deactivate User
**Priority:** P1 (High)

**Description:** Disable user access.

**Acceptance Criteria:**
- [ ] User cannot log in after deactivation
- [ ] Data preserved for audit
- [ ] Can be reactivated later

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| Dashboard load | <2s (p95) | Time to interactive |
| API response | <500ms (p95) | Server response time |
| File upload | <30s for 10MB | Upload + processing |
| Concurrent users | 100+ | Without degradation |

### 5.2 Scalability

- Support 10x current user base without architecture change
- Horizontal scaling capability for API layer
- Database connection pooling
- CDN for static assets

### 5.3 Availability

| Metric | Target |
|--------|--------|
| Uptime | 99.5% |
| Planned maintenance | <4 hours/month |
| Recovery Time Objective (RTO) | <1 hour |
| Recovery Point Objective (RPO) | <5 minutes |

### 5.4 Compatibility

**Browsers:**
- Chrome 90+ (primary)
- Safari 14+
- Firefox 88+
- Edge 90+

**Devices:**
- Desktop (1280px+)
- Tablet (768px - 1279px)
- Mobile (320px - 767px)

### 5.5 Accessibility

- WCAG 2.1 Level AA compliance
- Keyboard navigation support
- Screen reader compatibility
- Color contrast ratios ≥4.5:1
- Focus indicators visible

---

## 6. Technical Architecture

### 6.1 Recommended Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14 + React 18 | SSR, API routes, excellent DX |
| **Styling** | Tailwind CSS + shadcn/ui | Rapid development, accessible components |
| **State** | TanStack Query + Zustand | Server state + client state separation |
| **Forms** | React Hook Form + Zod | Type-safe validation |
| **Backend** | Next.js API Routes | Co-located with frontend |
| **Database** | Supabase (PostgreSQL) | Existing infrastructure |
| **Auth** | Supabase Auth | Existing infrastructure |
| **Email** | Resend | Existing integration |
| **Hosting** | Vercel | Optimized for Next.js |

### 6.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Client                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Next.js App                           │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │ │
│  │  │  Pages   │  │Components│  │  Hooks   │              │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘              │ │
│  │       │              │              │                    │ │
│  │  ┌────▼──────────────▼──────────────▼────┐              │ │
│  │  │         TanStack Query                 │              │ │
│  │  │      (Server State Management)         │              │ │
│  │  └────────────────┬──────────────────────┘              │ │
│  └───────────────────│──────────────────────────────────────┘ │
└──────────────────────│──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│                    Next.js API Routes                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ /api/quota  │  │/api/transfer│  │ /api/alerts │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                 │                 │                │
│  ┌──────▼─────────────────▼─────────────────▼──────┐        │
│  │              Supabase Client                     │        │
│  │         (with Service Role for API)              │        │
│  └──────────────────────┬──────────────────────────┘        │
└─────────────────────────│───────────────────────────────────┘
                          │ HTTPS
┌─────────────────────────▼───────────────────────────────────┐
│                      Supabase                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ PostgreSQL │  │    Auth    │  │   Storage  │            │
│  │  + RLS     │  │            │  │            │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│                                                              │
│  ┌────────────────────────────────────────────┐             │
│  │           Edge Functions                    │             │
│  │      (Email sending via Resend)             │             │
│  └────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Project Structure

```
fishermen-first-web/
├── app/                      # Next.js App Router
│   ├── (auth)/              # Auth routes (login, reset)
│   │   ├── login/
│   │   └── reset-password/
│   ├── (dashboard)/         # Protected routes
│   │   ├── dashboard/
│   │   ├── transfers/
│   │   ├── alerts/
│   │   ├── upload/
│   │   ├── rosters/
│   │   ├── allocations/
│   │   └── my-vessel/
│   ├── api/                 # API routes
│   │   ├── quota/
│   │   ├── transfers/
│   │   ├── alerts/
│   │   ├── upload/
│   │   └── users/
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── ui/                  # shadcn/ui components
│   ├── dashboard/
│   ├── transfers/
│   ├── alerts/
│   └── shared/
├── lib/
│   ├── supabase/           # Supabase clients
│   ├── validators/         # Zod schemas
│   └── utils/
├── hooks/                   # Custom React hooks
├── types/                   # TypeScript types
├── styles/
│   └── globals.css
├── public/
├── tests/
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.js
```

### 6.4 Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SSR vs CSR | Hybrid (Next.js) | SSR for SEO pages, CSR for dashboard |
| API style | REST | Simpler than GraphQL for this scope |
| Auth strategy | JWT (Supabase) | Existing infrastructure |
| Caching | TanStack Query | Automatic cache invalidation |
| File uploads | Direct to API | Under 10MB typical |
| Real-time | Polling (60s) | WebSocket overkill for v1 |

---

## 7. Data Model

### 7.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐
│  organizations  │───────│   cooperatives  │
│  (multi-tenant) │ 1:N   │                 │
└────────┬────────┘       └────────┬────────┘
         │                         │
         │ 1:N                     │ 1:N
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│  user_profiles  │       │  coop_members   │
│  (auth users)   │       │  (LLP holders)  │
└─────────────────┘       └────────┬────────┘
                                   │
                          ┌────────┴────────┐
                          │                 │
                          ▼                 ▼
                 ┌─────────────────┐ ┌─────────────────┐
                 │vessel_allocations│ │ quota_transfers │
                 │ (starting quota)│ │  (movements)    │
                 └────────┬────────┘ └────────┬────────┘
                          │                   │
                          └────────┬──────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ quota_remaining │
                          │    (VIEW)       │
                          └─────────────────┘
```

### 7.2 Core Tables

*(See existing schema in CLAUDE.md - preserved as-is)*

### 7.3 New Tables for Web App

#### **sessions** (if not using Supabase Auth sessions)
```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  ip_address INET,
  user_agent TEXT
);
```

#### **audit_log** (enhanced tracking)
```sql
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id),
  user_id UUID REFERENCES auth.users(id),
  action TEXT NOT NULL, -- 'create', 'update', 'delete', 'login', etc.
  entity_type TEXT NOT NULL, -- 'transfer', 'alert', 'user', etc.
  entity_id UUID,
  old_values JSONB,
  new_values JSONB,
  ip_address INET,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 8. API Specification

### 8.1 Authentication

#### POST /api/auth/login
```typescript
Request:
{
  email: string;
  password: string;
}

Response (200):
{
  user: {
    id: string;
    email: string;
    role: 'admin' | 'manager' | 'vessel_owner' | 'processor';
    org_id: string;
    llp?: string;
  };
  session: {
    access_token: string;
    refresh_token: string;
    expires_at: number;
  };
}

Response (401):
{ error: 'Invalid credentials' }
```

### 8.2 Dashboard

#### GET /api/quota/summary
```typescript
Query: { year?: number }

Response (200):
{
  total_vessels: number;
  critical_count: number;
  species_summary: {
    species_code: number;
    species_name: string;
    total_allocation: number;
    total_remaining: number;
    percent_remaining: number;
  }[];
  at_risk_vessels: {
    llp: string;
    vessel_name: string;
    coop_code: string;
    lowest_percent: number;
    critical_species: string;
  }[];
}
```

#### GET /api/quota/remaining
```typescript
Query: {
  year?: number;
  coop_code?: string;
  llp?: string;
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

Response (200):
{
  data: {
    llp: string;
    vessel_name: string;
    coop_code: string;
    species_code: number;
    allocation: number;
    transfers_in: number;
    transfers_out: number;
    harvested: number;
    remaining: number;
    percent_remaining: number;
  }[];
  pagination: {
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
  };
}
```

### 8.3 Transfers

#### POST /api/transfers
```typescript
Request:
{
  from_llp: string;
  to_llp: string;
  species_code: number;
  pounds: number;
  transfer_date: string; // ISO date
  notes?: string;
}

Response (201):
{
  id: string;
  from_llp: string;
  to_llp: string;
  species_code: number;
  pounds: number;
  transfer_date: string;
  created_at: string;
}

Response (400):
{ error: 'Insufficient quota' | 'Cannot transfer to self' | ... }
```

#### GET /api/transfers
```typescript
Query: {
  year?: number;
  llp?: string;
  species_code?: number;
  from_date?: string;
  to_date?: string;
  page?: number;
  per_page?: number;
}

Response (200):
{
  data: Transfer[];
  pagination: Pagination;
}
```

### 8.4 Alerts

#### POST /api/alerts
```typescript
Request:
{
  reported_by_llp: string;
  species_code: number;
  latitude: number;
  longitude: number;
  amount: number;
  details?: string;
}

Response (201):
{ id: string; status: 'pending'; ... }
```

#### PUT /api/alerts/:id/share
```typescript
Response (200):
{
  id: string;
  status: 'shared';
  shared_at: string;
  shared_recipient_count: number;
}
```

#### PUT /api/alerts/:id/resolve
```typescript
Response (200):
{
  id: string;
  status: 'resolved';
  resolved_at: string;
}
```

### 8.5 File Upload

#### POST /api/upload/balance
```typescript
Request: multipart/form-data
  - file: CSV file

Response (200):
{
  imported: number;
  skipped: number;
  errors: { row: number; message: string }[];
}
```

#### POST /api/upload/detail
```typescript
Request: multipart/form-data
  - file: XLSX file

Response (200):
{
  imported: number;
  skipped: number;
  errors: { row: number; message: string }[];
}
```

---

## 9. Security Requirements

### 9.1 Authentication Security

| Requirement | Implementation |
|-------------|----------------|
| Password hashing | bcrypt (via Supabase Auth) |
| Password requirements | 8+ chars, uppercase, number |
| Session tokens | JWT with 1-hour expiry |
| Refresh tokens | Secure, httpOnly cookie |
| Rate limiting | 5 login attempts per minute |
| Brute force protection | Account lockout after 10 failures |

### 9.2 Authorization Security

| Requirement | Implementation |
|-------------|----------------|
| Row-Level Security | Supabase RLS policies |
| API authorization | Middleware role checks |
| CORS | Whitelist production domains |
| CSRF protection | SameSite cookies + tokens |

### 9.3 Data Security

| Requirement | Implementation |
|-------------|----------------|
| Encryption at rest | Supabase default (AES-256) |
| Encryption in transit | TLS 1.3 |
| PII handling | Minimize storage, encrypt sensitive |
| Audit logging | All data modifications logged |
| Backup encryption | Encrypted backups |

### 9.4 Infrastructure Security

| Requirement | Implementation |
|-------------|----------------|
| DDoS protection | Vercel/Cloudflare |
| WAF | Vercel built-in |
| Secrets management | Environment variables |
| Dependency scanning | Dependabot, npm audit |
| Security headers | Strict CSP, HSTS |

### 9.5 Compliance

- SOC 2 Type II (Supabase, Vercel)
- GDPR-ready data handling
- Data retention policies (7 years for fishing records)

---

## 10. Integration Requirements

### 10.1 eLandings API

**Status:** Pending (awaiting credentials)

**Integration Type:** One-way sync (eLandings → Fishermen First)

**Data Flow:**
1. Scheduled job fetches new harvest records
2. Maps to internal schema (llp, species_code, pounds)
3. Creates records in harvests table
4. Triggers quota_remaining recalculation

**Endpoints (TBD):**
- `GET /harvests?since={timestamp}`
- Authentication: API key

**Error Handling:**
- Retry failed syncs 3x with exponential backoff
- Alert on persistent failures
- Manual upload fallback

### 10.2 Email Service (Resend)

**Integration Type:** Outbound transactional email

**Use Cases:**
- Bycatch alert notifications
- Password reset emails
- User invitation emails

**Configuration:**
```typescript
{
  from: 'alerts@fishermenFirst.com',
  reply_to: 'support@fishermenFirst.com'
}
```

**Rate Limits:**
- 100 emails/second (Resend limit)
- Batch recipients for fleet-wide alerts

### 10.3 Future Integrations

| System | Purpose | Priority |
|--------|---------|----------|
| NOAA VMS | Vessel position tracking | P2 |
| Alaska DFG | Permit verification | P3 |
| Accounting system | Financial reconciliation | P3 |

---

## 11. UI/UX Requirements

### 11.1 Design System

**Brand Colors:**
```css
--color-primary: #1e3a5f;      /* Navy - primary actions */
--color-primary-light: #2d5a8a; /* Hover state */
--color-success: #10b981;       /* Green - positive/OK */
--color-warning: #f59e0b;       /* Amber - warning */
--color-danger: #ef4444;        /* Red - critical/error */
--color-neutral: #6b7280;       /* Gray - secondary text */
```

**Typography:**
- Font family: Inter (primary), system-ui (fallback)
- Base size: 16px
- Scale: 1.25 (major third)

**Spacing:**
- Base unit: 4px
- Scale: 4, 8, 12, 16, 24, 32, 48, 64

### 11.2 Component Library

Use shadcn/ui components with customizations:

| Component | Customization |
|-----------|---------------|
| Button | Primary uses brand navy |
| Card | Subtle border, slight shadow |
| Table | Striped rows, sticky header |
| Badge | Risk-level color variants |
| Input | Consistent with card borders |
| Select | Searchable for long lists |
| Dialog | Centered, max-width 600px |

### 11.3 Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | <768px | Single column, hamburger nav |
| Tablet | 768-1023px | 2-column, collapsible sidebar |
| Desktop | 1024-1439px | Full sidebar, 3-column grid |
| Large | 1440px+ | Max-width container |

### 11.4 Key Page Layouts

**Dashboard:**
```
┌─────────────────────────────────────────────┐
│ Header (Logo, User Menu)                    │
├─────────────────────────────────────────────┤
│ ┌─────────────┐                             │
│ │   Sidebar   │  ┌─────────────────────────┐│
│ │             │  │ KPI Cards (5 across)    ││
│ │ • Dashboard │  ├─────────────────────────┤│
│ │ • Transfers │  │ At-Risk Vessels Panel   ││
│ │ • Alerts    │  ├─────────────────────────┤│
│ │ • Upload    │  │ Filters Row             ││
│ │ • Rosters   │  ├─────────────────────────┤│
│ │             │  │ Data Table              ││
│ │             │  │ (Sortable, Paginated)   ││
│ └─────────────┘  └─────────────────────────┘│
└─────────────────────────────────────────────┘
```

**Transfer Form:**
```
┌─────────────────────────────────────────────┐
│ Header                                       │
├─────────────────────────────────────────────┤
│ ┌─────────────┐  ┌─────────────────────────┐│
│ │   Sidebar   │  │ Transfer Form Card      ││
│ │             │  │ ┌─────────┐ ┌─────────┐ ││
│ │             │  │ │From LLP │ │ To LLP  │ ││
│ │             │  │ └─────────┘ └─────────┘ ││
│ │             │  │ ┌─────────┐ ┌─────────┐ ││
│ │             │  │ │ Species │ │ Amount  │ ││
│ │             │  │ └─────────┘ └─────────┘ ││
│ │             │  │ Available: XX,XXX lbs   ││
│ │             │  │ [Submit Transfer]       ││
│ │             │  ├─────────────────────────┤│
│ │             │  │ Transfer History Table  ││
│ └─────────────┘  └─────────────────────────┘│
└─────────────────────────────────────────────┘
```

### 11.5 Loading & Error States

**Loading:**
- Skeleton loaders for tables
- Spinner for buttons during submit
- Progress bar for file uploads

**Errors:**
- Inline validation messages (red, below field)
- Toast notifications for API errors
- Full-page error for critical failures
- Retry buttons where applicable

**Empty States:**
- Friendly illustration + message
- Call-to-action when applicable
- Example: "No transfers yet. Create your first transfer."

---

## 12. Deployment & Operations

### 12.1 Environments

| Environment | URL | Purpose |
|-------------|-----|---------|
| Development | localhost:3000 | Local development |
| Staging | staging.fishermenFirst.com | Testing & QA |
| Production | app.fishermenFirst.com | Live users |

### 12.2 CI/CD Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Push    │───▶│  Lint +  │───▶│  Build   │───▶│  Deploy  │
│  to Git  │    │  Test    │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                     │                               │
                     ▼                               ▼
                ┌──────────┐                   ┌──────────┐
                │  Fail:   │                   │ Preview/ │
                │  Block   │                   │ Prod URL │
                └──────────┘                   └──────────┘
```

**Pipeline Steps:**
1. **Lint:** ESLint + Prettier check
2. **Type Check:** tsc --noEmit
3. **Unit Tests:** Jest
4. **E2E Tests:** Playwright (staging only)
5. **Build:** next build
6. **Deploy:** Vercel (auto on merge to main)

### 12.3 Monitoring

| Tool | Purpose |
|------|---------|
| Vercel Analytics | Performance, Web Vitals |
| Sentry | Error tracking |
| Supabase Dashboard | Database metrics |
| Uptime Robot | Availability monitoring |

### 12.4 Alerting

| Alert | Condition | Channel |
|-------|-----------|---------|
| High error rate | >1% errors in 5 min | Slack + Email |
| API latency | p95 >2s for 10 min | Slack |
| Database connections | >80% pool used | Slack |
| Downtime | 3 failed health checks | Slack + SMS |

### 12.5 Backup & Recovery

| Item | Frequency | Retention |
|------|-----------|-----------|
| Database | Continuous (Supabase) | 7 days point-in-time |
| Daily snapshots | Daily | 30 days |
| Monthly archives | Monthly | 7 years |

---

## 13. Migration Plan

### 13.1 Phase 1: Foundation (Weeks 1-2)

**Goals:**
- Project setup with Next.js + TypeScript
- Supabase client integration
- Authentication flow
- Basic layout and navigation

**Deliverables:**
- [ ] Repository initialized
- [ ] Auth working (login/logout)
- [ ] Role-based routing
- [ ] Sidebar navigation
- [ ] CI/CD pipeline

### 13.2 Phase 2: Core Features (Weeks 3-5)

**Goals:**
- Dashboard with full functionality
- Transfer management
- Quota calculations verified

**Deliverables:**
- [ ] Dashboard KPI cards
- [ ] At-risk vessels panel
- [ ] Quota data table with filters
- [ ] Transfer form with validation
- [ ] Transfer history

### 13.3 Phase 3: Bycatch & Upload (Weeks 6-7)

**Goals:**
- Bycatch alert system
- File upload functionality
- Email integration

**Deliverables:**
- [ ] Alert list view with tabs
- [ ] Alert create/share/resolve
- [ ] Email delivery
- [ ] CSV upload
- [ ] XLSX upload

### 13.4 Phase 4: Vessel Owner & Polish (Weeks 8-9)

**Goals:**
- Vessel owner features
- Reference data views
- UI polish and accessibility

**Deliverables:**
- [ ] My Vessel dashboard
- [ ] Report bycatch form
- [ ] Roster views
- [ ] Allocation views
- [ ] Mobile responsiveness
- [ ] Accessibility audit

### 13.5 Phase 5: Testing & Launch (Weeks 10-11)

**Goals:**
- Comprehensive testing
- Data migration
- Production launch

**Deliverables:**
- [ ] Unit test coverage >80%
- [ ] E2E test suite
- [ ] Performance testing
- [ ] Security audit
- [ ] User acceptance testing
- [ ] Production deployment
- [ ] User training materials

### 13.6 Data Migration Strategy

1. **Freeze Streamlit writes** (read-only mode)
2. **Export current data** (pg_dump)
3. **Import to new environment** (if separate)
4. **Verify data integrity** (row counts, checksums)
5. **Switch DNS** to new app
6. **Monitor closely** for 48 hours
7. **Decommission Streamlit** after 2 weeks

---

## Appendices

### Appendix A: Glossary

| Term | Definition |
|------|------------|
| **LLP** | Limited Liability Permit - unique vessel identifier |
| **TAC** | Total Allowable Catch - annual quota in metric tons |
| **Allocation** | Starting quota per vessel per species |
| **PSC** | Prohibited Species Catch - bycatch species |
| **RLS** | Row-Level Security - database access control |

### Appendix B: Species Reference

| Code | Name | Type | Unit |
|------|------|------|------|
| 141 | Pacific Ocean Perch (POP) | Target | lbs |
| 136 | Northern Rockfish (NR) | Target | lbs |
| 172 | Dusky Rockfish | Target | lbs |
| 200 | Halibut | PSC | count |
| 110 | Pacific Cod | PSC | lbs |
| 710 | Sablefish | PSC | lbs |
| 143 | Thornyhead | PSC | lbs |

### Appendix C: User Stories

**US-001:** As a manager, I want to see which vessels are at risk so I can prioritize transfers.

**US-002:** As a manager, I want to create transfers between vessels so quota is used efficiently.

**US-003:** As a vessel owner, I want to see my remaining quota so I can plan my trips.

**US-004:** As a manager, I want to share bycatch alerts with the fleet so they avoid hotspots.

**US-005:** As a vessel owner, I want to report bycatch encounters so the fleet is informed.

**US-006:** As a manager, I want to upload eLandings files so I can reconcile records.

### Appendix D: Open Questions

1. **Real-time updates:** Should we implement WebSocket for live quota updates?
   - *Recommendation:* Defer to v2; polling sufficient for MVP

2. **Mobile app:** Native or responsive web?
   - *Recommendation:* Responsive web first; native if needed later

3. **Offline support:** Required for vessels at sea?
   - *Recommendation:* Defer; connectivity improving, low priority

4. **Multi-language:** Support for non-English users?
   - *Recommendation:* Defer; 100% English-speaking user base currently

---

*Document maintained by Product Team. Last updated: January 24, 2026*
