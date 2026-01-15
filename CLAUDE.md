# Fishermen First - Rockfish Platform

## Current Focus
- Processor view implementation (WIP - stub only)
- Additional e2e test coverage

## Recent Changes (Jan 2026)
- **Consistent branding across all pages** using shared styles (`app/utils/styles.py`)
- Modernized login page (centered card, navy branding, "Sign In" button)
- Styled sidebar (navy background, white text, icons on nav items)
- Dashboard improvements (KPI cards, section headers, styled table)
- Sidebar filters that cascade (Co-Op filters Vessels)
- Added 49 new transfer tests (authorization, multi-tenancy, security, etc.)
- Updated e2e tests for new UI (6 tests passing)

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
```
app/
├── main.py              # Navigation, role-based routing, sidebar filters
├── auth.py              # Login/logout, session state
├── config.py            # Supabase client (cached)
├── utils/
│   └── styles.py        # Shared styling (page_header, section_header, apply_page_styling)
└── views/
    ├── dashboard.py         # Quota overview, risk flags, KPI cards
    ├── transfers.py         # Create/view transfers (manager+ only)
    ├── allocations.py       # TAC, vessel allocations
    ├── rosters.py           # Reference data (coops, members, vessels, processors, species)
    ├── upload.py            # eFish CSV upload
    ├── vessel_owner_view.py # Read-only vessel view
    ├── account_balances.py  # eFish balances
    ├── account_detail.py    # eFish detail
    └── processor_view.py    # Processor view (WIP - stub only)
```

## UI/Branding
- Brand color: #1e3a5f (navy)
- Login: centered card, white form on light gray (#f0f4f8) background
- Sidebar: navy background, white text, icons on nav items
- All pages: use `page_header()` and `section_header()` from `app/utils/styles.py`
- Tables: navy header, styled with `st.dataframe()`

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
```bash
streamlit run app/main.py
```

## Tests

**See [TESTING.md](TESTING.md) for detailed test documentation.**

### Quick Reference

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_auth.py | 47 | Login, logout, roles, JWT refresh |
| test_dashboard.py | 27 | Risk levels, formatting, quota data |
| test_transfers.py | 83 | Authorization, multi-tenancy, security, validation |
| test_upload.py | 35 | CSV parsing, duplicates, imports |
| test_vessel_owner.py | 28 | Auth, quota display, transfers |
| test_app.py (e2e) | 6 | Login page, vessel owner flow |
| **Total** | **240** | |

### Running Tests
```bash
# Unit tests only (fast, ~4 seconds)
pytest tests/ --ignore=tests/e2e -v

# All tests including e2e (~35 seconds)
TEST_PASSWORD=xxx pytest tests/ -v
```

### Test Accounts
- Vessel owner: `vikram.nayani+1@gmail.com`
- Admin: `vikram@fishermenfirst.org`

## Known Issues / TODOs
- Race condition in transfers (no DB-level locking between quota check and insert)
- Inactive vessels not filtered from transfer dropdowns
- Deprecation warnings: `Styler.applymap` → `Styler.map`, `use_container_width` → `width`
