# Fishermen First - Rockfish Platform

## Overview
SaaS platform for Alaska commercial fishing cooperatives to track quota allocations and harvests for Central GOA Rockfish Program.

## Tech Stack
- Frontend: Streamlit
- Backend: Supabase (PostgreSQL)
- Auth: Supabase Auth

## Database Schema

### Reference Tables
- cooperatives (4 co-ops)
- coop_members (46 LLPs) - KEY: llp
- vessels (41 vessels) - KEY: adfg_number
- processors (4 processors) - KEY: processor_code
- species (10 species) - KEY: code, includes is_psc flag
- annual_tac (TAC by species/year)
- vessel_allocations (starting quota by LLP/species/year)

### Transaction Tables
- quota_transfers (transfers between LLPs, has audit columns)
- harvests (eFish data, has audit columns)

### Views
- quota_remaining (calculated: allocation + transfers_in - transfers_out - harvested)

## App Structure
app/
├── main.py           # Navigation
├── auth.py           # Login/logout
├── config.py         # Supabase client
└── pages/
    ├── dashboard.py  # Quota remaining by vessel
    ├── allocations.py # 2 tabs: Total TAC, Vessel Allocations
    ├── rosters.py    # 5 tabs: Coops, Members, Vessels, Processors, Species
    └── upload.py     # eFish CSV upload (pending)

## Key Business Logic
- LLP is the primary identifier for quota holders
- Quota Remaining = Starting Allocation + Transfers In - Transfers Out - Harvests
- Species codes: POP=141, NR=136, Dusky=172
- Non-PSC species: 136, 141, 172 (target species)
- Audit trail: transaction tables use soft deletes (is_deleted flag)

## Local Dev
cd C:\Users\vikra\Projects\fishermen-first-rockfish-platform
streamlit run app/main.py
