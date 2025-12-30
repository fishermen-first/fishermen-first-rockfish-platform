# Fishermen First Analytics Platform

A lightweight analytics platform for commercial fishing cooperatives to track quotas, harvests, and prohibited species catch (PSC). Built for the Rockfish Program in Alaska.

## Tech Stack

- **Database:** Supabase (PostgreSQL)
- **Auth:** Supabase Auth
- **File Storage:** Supabase Storage
- **Frontend:** Streamlit
- **Data Processing:** Python, pandas

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your Supabase credentials:
   ```bash
   cp .env.example .env
   ```
5. Run the app:
   ```bash
   streamlit run app/main.py
   ```

## Project Structure

```
fishermen-first/
├── app/
│   ├── main.py                 # App entry point, navigation
│   ├── auth.py                 # Login, session management
│   ├── config.py               # Supabase connection, settings
│   ├── pages/
│   │   ├── dashboard.py        # Main dashboard
│   │   ├── upload.py           # File upload interface
│   │   ├── rosters.py          # View cooperatives, members, vessels
│   │   ├── quotas.py           # Quota allocations and tracking
│   │   ├── harvests.py         # Harvest data and reporting
│   │   ├── psc.py              # PSC tracking and limits
│   │   └── admin/
│   │       ├── manage_users.py
│   │       ├── manage_coops.py
│   │       ├── manage_members.py
│   │       ├── manage_vessels.py
│   │       └── manage_processors.py
│   ├── components/             # Reusable UI components
│   └── utils/
│       ├── parsers.py          # CSV/Excel file parsing
│       ├── validators.py       # Data validation
│       └── queries.py          # Common database queries
├── sql/
│   └── schema.sql              # Database schema
└── tests/                      # Test files
```

## User Roles

| Role | Access |
|------|--------|
| admin | Full access: system config, user management, all data |
| co_op_manager | Dashboards, file uploads, manage operational data for all cooperatives |
