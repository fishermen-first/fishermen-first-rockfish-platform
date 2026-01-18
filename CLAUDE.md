# Fishermen First - Rockfish Platform

Multi-tenant SaaS for Alaska fishing cooperatives to track quota allocations and harvests (Central GOA Rockfish Program).

## Tech Stack
- Frontend: Streamlit
- Backend: Supabase (PostgreSQL + Auth)
- Multi-tenancy: org_id + RLS policies

## Key Business Logic
- **LLP** is the primary identifier for quota holders
- **Quota Remaining** = Allocation + Transfers In - Transfers Out - Harvested
- Species codes: POP=141, NR=136, Dusky=172
- Soft deletes: `is_deleted` flag on transaction tables

## Database Schema

### Core Tables
- organizations, cooperatives, coop_members (KEY: llp), processors, species, annual_tac, vessel_allocations

### Transaction Tables (affect quota)
- quota_transfers, harvests (from eLandings API only)

### Reconciliation Tables (do NOT affect quota)
- efish_account_balance, efish_account_detail (CSV uploads)

### Views
- quota_remaining

## User Roles
- admin: full access
- manager: transfers, uploads, dashboard
- processor: processor view only
- vessel_owner: own vessel's quota/transfers/harvests (read-only)

## UI/Branding
- Brand color: #1e3a5f (navy)
- Use `page_header()` and `section_header()` from `app/utils/styles.py`

## Running the App
```bash
streamlit run app/main.py
```

## Tests
See [TESTING.md](TESTING.md) for details.

```bash
# Unit tests (~4s)
pytest tests/ --ignore=tests/e2e -v

# All tests (~35s)
TEST_PASSWORD=xxx pytest tests/ -v
```

## Known Issues
- Race condition in transfers (no DB-level locking)
- Inactive vessels not filtered from transfer dropdowns
