# Fishermen First - Rockfish Platform

## Current Focus
- UI/UX improvements to dashboard and login
- Sidebar filters for Co-Op and Vessel (with cascading options)
- Processor view still needs implementation

## Recent Changes (Jan 2026)
- Modernized login page (centered card, navy branding, clean form)
- Styled sidebar (navy background, white text, icons on nav items)
- Dashboard improvements (KPI cards, section headers, table styling)
- Added sidebar filters that cascade (Co-Op filters Vessels)

## Overview
Multi-tenant SaaS platform for Alaska commercial fishing cooperatives to track quota allocations and harvests for Central GOA Rockfish Program.

## Tech Stack
- Frontend: Streamlit
- Backend: Supabase (PostgreSQL)
- Auth: Supabase Auth
- Multi-tenancy: org_id + RLS policies

## Database Schema

### Core Tables
- organizations - multi-tenant root (Rockfish org: 06da23e7-4cce-446a-a9f7-67fc86094b98)
- cooperatives - 4 co-ops per org
- coop_members - 46 LLPs, KEY: llp
- processors - 4 processors
- species - 10 species (target: 141, 136, 172)
- annual_tac - TAC by species/year
- vessel_allocations - starting quota by LLP/species/year

### Transaction Tables (affect quota)
- quota_transfers - transfers between LLPs (soft delete, audit)
- harvests - from eLandings API only (soft delete)

### Reconciliation Tables (do NOT affect quota)
- efish_account_balance - CSV uploads for reconciliation
- efish_account_detail - CSV uploads for reconciliation

### Views
- quota_remaining = allocation + transfers_in - transfers_out - harvested

## App Structure
app/
├── main.py              # Navigation, role-based routing, sidebar filters
├── auth.py              # Login/logout, session state
├── config.py            # Supabase client (cached)
└── views/
    ├── dashboard.py         # Quota overview, risk flags, KPI cards
    ├── transfers.py         # Create/view transfers
    ├── allocations.py       # TAC, vessel allocations
    ├── rosters.py           # Reference data
    ├── upload.py            # eFish CSV upload
    ├── vessel_owner_view.py # Read-only vessel view
    ├── account_balances.py  # eFish balances
    ├── account_detail.py    # eFish detail
    └── processor_view.py    # Processor view (WIP - stub only)

## UI/Branding
- Brand color: #1e3a5f (navy)
- Login: centered card, white form on light gray background
- Sidebar: navy background, white text, icons on nav items
- Dashboard: white KPI cards, section headers, styled table

## User Roles
- admin: full access
- manager: transfers, uploads, dashboard
- processor: processor view only
- vessel_owner: own vessel's quota/transfers/harvests (read-only)

## Key Business Logic
- LLP is the primary identifier for quota holders
- Quota Remaining = Allocation + Transfers In - Transfers Out - Harvested
- Species codes: POP=141, NR=136, Dusky=172
- Soft deletes: is_deleted flag on transaction tables
- RLS: all tables filtered by org_id

## Data Sources
- eLandings API → harvests table (affects quota)
- eFish CSV → efish_* tables (reconciliation only)

## Local Dev
streamlit run app/main.py

## Verification (IMPORTANT)
After making any code changes, ALWAYS run verification:

```bash
# Quick: run unit tests
pytest tests/ -v --tb=short

# Full: run verification script
python scripts/verify.py
```

## Tests

### Unit Tests
pytest tests/ -v

### End-to-End Tests (Playwright)
```bash
# Install (one time)
pip install playwright pytest-playwright
playwright install chromium

# Run e2e tests (headless)
pytest tests/e2e/ -v

# Run e2e tests (see browser)
pytest tests/e2e/ --headed

# With test credentials
TEST_PASSWORD=xxx pytest tests/e2e/ -v
```
