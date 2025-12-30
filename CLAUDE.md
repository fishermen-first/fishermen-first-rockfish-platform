# CLAUDE.md
## Fishermen First Analytics Platform

---

## Build Context

**IMPORTANT:** Before starting work, read these files for full project context and current progress:

1. **fishermen_first_build_guide_final.md** - Complete build guide with all prompts and implementation details
2. **fishermen_first_checklist_final.md** - Current progress checklist showing what's done and what's next

**Current Status:** Starting at Prompt 9. Prompts 1-8 have been completed (project setup, auth, navigation, CRUD template).

---

## Overview

A lightweight analytics platform for commercial fishing cooperatives to track quotas, harvests, and prohibited species catch (PSC). Built for the Rockfish Program in Alaska.

---

## Tech Stack

- **Database:** Supabase (PostgreSQL)
- **Auth:** Supabase Auth
- **File Storage:** Supabase Storage
- **Frontend:** Streamlit
- **Data Processing:** Python, pandas
- **Deployment:** Streamlit Community Cloud

---

## Project Structure

```
fishermen-first/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .streamlit/
│   └── config.toml
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
│   ├── components/
│   │   └── [reusable UI components]
│   └── utils/
│       ├── parsers.py          # CSV/Excel file parsing
│       ├── validators.py       # Data validation
│       └── queries.py          # Common database queries
├── sql/
│   └── schema.sql              # Database schema
└── tests/
    └── [test files]
```

---

## User Roles

| Role | Access |
|------|--------|
| admin | Full access: system config, user management, all data |
| co_op_manager | Dashboards, file uploads, manage operational data (vessels, members, quotas) for all cooperatives |

---

## Data Model

### Reference Tables

**users** (extends Supabase Auth)
- id (uuid, PK)
- email (text)
- role (text: 'admin' or 'co_op_manager')
- created_at (timestamp)

**seasons**
- id (uuid, PK)
- year (integer)
- start_date (date)
- end_date (date)

**species**
- id (uuid, PK)
- species_code (text)
- species_name (text)
- is_psc (boolean)

**processors**
- id (uuid, PK)
- processor_name (text)
- contact_info (text)

### Core Entities

**cooperatives**
- id (uuid, PK)
- cooperative_name (text)
- contact_info (text)

**members**
- id (uuid, PK)
- member_name (text)
- contact_info (text)

**vessels**
- id (uuid, PK)
- member_id (uuid, FK to members)
- vessel_name (text)
- vessel_id_number (text)

### Relationship Tables (historical tracking)

**cooperative_memberships**
- id (uuid, PK)
- member_id (uuid, FK)
- cooperative_id (uuid, FK)
- effective_from (date)
- effective_to (date, null if current)

**vessel_cooperative_assignments**
- id (uuid, PK)
- vessel_id (uuid, FK)
- cooperative_id (uuid, FK)
- effective_from (date)
- effective_to (date, null if current)

### Quota & Limits

**quota_allocations**
- id (uuid, PK)
- season_id (uuid, FK)
- cooperative_id (uuid, FK)
- member_id (uuid, FK, optional)
- vessel_id (uuid, FK, optional)
- species_id (uuid, FK)
- amount (numeric)

**quota_transfers**
- id (uuid, PK)
- season_id (uuid, FK)
- from_cooperative_id (uuid, FK, optional)
- from_member_id (uuid, FK, optional)
- to_cooperative_id (uuid, FK, optional)
- to_member_id (uuid, FK, optional)
- species_id (uuid, FK)
- amount (numeric)
- transfer_date (date)

**psc_limits**
- id (uuid, PK)
- season_id (uuid, FK)
- cooperative_id (uuid, FK)
- species_id (uuid, FK)
- limit_amount (numeric)

### Transactional Data

**harvests**
- id (uuid, PK)
- season_id (uuid, FK)
- vessel_id (uuid, FK)
- processor_id (uuid, FK, optional)
- species_id (uuid, FK)
- amount (numeric)
- landed_date (date)

**psc_events**
- id (uuid, PK)
- season_id (uuid, FK)
- vessel_id (uuid, FK)
- cooperative_id (uuid, FK)
- species_id (uuid, FK)
- amount (numeric)
- event_date (date)

### File Management

**file_uploads**
- id (uuid, PK)
- cooperative_id (uuid, FK)
- uploaded_by (uuid, FK to users)
- source_type (text: 'eFish', 'eLandings', 'fish_ticket', 'VMS')
- filename (text)
- storage_path (text)
- row_count (integer)
- uploaded_at (timestamp)

---

## Key Patterns

### Historical Queries

To find which cooperative a vessel belonged to on a specific date:

```sql
SELECT cooperative_id 
FROM vessel_cooperative_assignments
WHERE vessel_id = [vessel]
  AND effective_from <= [date]
  AND (effective_to IS NULL OR effective_to >= [date])
```

### File Upload Flow

1. User selects cooperative and source type
2. User uploads CSV/Excel file
3. App validates file format
4. App saves file to Supabase Storage
5. App logs metadata to file_uploads table
6. App parses file and writes data to appropriate table(s)

### Role-Based Views

Check user role from session and show/hide features accordingly:

```python
if st.session_state.user_role == 'admin':
    # Show admin features
else:
    # Show co_op_manager features
```

---

## Conventions

- Use uuid for all primary keys
- Use snake_case for table and column names
- All dates stored as date type, not timestamp (except created_at, uploaded_at)
- Nullable foreign keys indicate optional relationships
- effective_to = NULL means "current" for historical tracking tables
- Store raw files in Supabase Storage, never in the database

---

## Current Phase

**Phase 1: Discovery & Transition (January 2026)**

Working on:
- [ ] Supabase project setup
- [ ] Authentication (email/password)
- [ ] Storage bucket for file uploads
- [ ] Database schema (all tables above)
- [ ] Streamlit app scaffolding
- [ ] Login page
- [ ] Basic navigation
- [ ] Admin: manage cooperatives, members, vessels
- [ ] File upload UI

---

## Data Sources

| Source | Format | Purpose |
|--------|--------|---------|
| eFish | CSV/Excel | TBD |
| eLandings | CSV/Excel | Harvest data |
| Fish tickets | CSV/Excel | Harvest data |
| VMS | CSV/Excel | TBD (may defer) |

File formats TBD pending sample files from co-op manager.

---

## Key Dates

- Mid-February 2026: Ready for testing
- March 1, 2026: CQ applications due
- April 1, 2026: Fishery start, platform fully operational

---

## Git Workflow

**Repository:** [GitHub repo URL here]

**Branch strategy:** Keep it simple. Work on `main` for now. Create feature branches if a task gets complex or risky.

**Commit conventions:**
- Use present tense: "Add file upload UI" not "Added file upload UI"
- Keep messages short and descriptive
- One logical change per commit

**Workflow:**

1. Pull latest before starting work
   ```
   git pull
   ```

2. Build the feature (with Claude Code or manually)

3. Review changes
   ```
   git status
   git diff
   ```

4. Stage and commit
   ```
   git add .
   git commit -m "Add file upload UI"
   ```

5. Push to GitHub
   ```
   git push
   ```

**Asking Claude Code to handle git:**

```
You: Commit these changes with message "Add login page"
You: Push to GitHub
```

Or combine with the task:

```
You: Build the login page, then commit and push
```

**When to commit:**
- After completing a working feature or fix
- Before switching to a different task
- At the end of a work session

**Do not commit:**
- Broken code
- Secrets or credentials (use .env, add to .gitignore)
- Large data files (use Supabase Storage instead)

---

## TBD Items

- Quota allocation hierarchy (cooperative → member → vessel flow)
- Ex-vessel value structure
- VMS data usage
- Exact file formats for each data source
