# Codebase Structure

**Analysis Date:** 2026-01-28

## Directory Layout

```
fishermen-first-rockfish-platform/
├── app/                        # Main application source code
│   ├── main.py                # Streamlit entry point (router, sidebar, auth)
│   ├── auth.py                # Authentication and session management
│   ├── config.py              # Supabase client, constants, env vars
│   ├── components/            # Reusable UI form components
│   │   ├── __init__.py
│   │   ├── haul_form.py       # Multi-haul capture form
│   │   └── coordinate_input.py # DMS/decimal coordinate input
│   ├── views/                 # Page implementations (role-based)
│   │   ├── __init__.py
│   │   ├── dashboard.py       # Quota remaining dashboard
│   │   ├── transfers.py       # Quota transfer entry/history
│   │   ├── bycatch_alerts.py  # Bycatch alert management (manager)
│   │   ├── report_bycatch.py  # Bycatch reporting (vessel owner)
│   │   ├── allocations.py     # Vessel allocation lookup
│   │   ├── account_balances.py# eFish account balance reconciliation
│   │   ├── account_detail.py  # eFish account detail transactions
│   │   ├── upload.py          # CSV/Excel file uploads
│   │   ├── rosters.py         # Reference data tables
│   │   ├── vessel_owner_view.py # Vessel owner read-only dashboard
│   │   └── processor_view.py  # Processor role view
│   └── utils/                 # Shared utilities
│       ├── __init__.py
│       ├── styles.py          # Branding, CSS, page/section headers
│       ├── formatting.py      # Number formatting, risk levels
│       ├── coordinates.py     # DMS ↔ decimal conversion
│       ├── parsers.py         # CSV/Excel parsing
│       └── storage.py         # File operations
├── sql/                       # Database schema and migrations
│   ├── schema.sql            # Core tables, views, RLS policies
│   ├── schema-v2-multi-tenant.sql # Multi-tenant version
│   ├── migrations/           # Sequential migration files
│   │   ├── 001_add_file_uploads_status.sql
│   │   ├── 002_add_quota_transfers_notes.sql
│   │   ├── 003_add_species_is_psc.sql
│   │   ├── 004_add_vessel_owner_support.sql
│   │   ├── 005_add_multi_tenant.sql
│   │   ├── 006_create_efish_tables.sql
│   │   ├── 007_add_bycatch_alerts.sql
│   │   ├── 008_add_species_unit.sql
│   │   ├── 009_add_manager_insert_alerts_policy.sql
│   │   ├── 010_add_resolved_status.sql
│   │   ├── 011_add_rls_security_fixes.sql
│   │   └── 012_bycatch_hauls.sql
│   └── README.md             # Migration instructions
├── supabase/                 # Supabase project configuration
│   └── functions/
│       └── send-bycatch-alert/ # Email notification function
├── tests/                    # Test suite
│   ├── conftest.py          # Pytest fixtures, cache clearing
│   ├── test_auth.py         # Authentication tests
│   ├── test_dashboard.py    # Dashboard data tests
│   ├── test_transfers.py    # Transfer validation tests
│   ├── test_bycatch_alerts.py # Bycatch alert tests
│   ├── test_bycatch_hauls.py  # Multi-haul capture tests
│   ├── test_quota_tracking.py # Quota calculation tests
│   ├── test_upload.py       # File upload validation
│   ├── test_vessel_owner.py # Vessel owner view tests
│   ├── __init__.py
│   └── e2e/                 # End-to-end tests
│       ├── conftest.py
│       ├── test_app.py
│       ├── test_bycatch_alerts.py
│       └── test_bycatch_hauls.py
├── .planning/codebase/      # GSD codebase analysis documents
├── docs/                    # Documentation
│   ├── PRD-Web-App.md      # Product requirements
│   └── test-coverage.md    # Coverage report
├── scripts/                 # Utility scripts
│   └── generate_marketing_screenshots.py
├── .streamlit/              # Streamlit config
├── .env.example            # Environment template
├── CLAUDE.md               # Project instructions
├── TESTING.md              # Testing guide
├── README.md               # Project overview
└── pytest.ini              # Pytest configuration
```

## Directory Purposes

**app/:**
- Purpose: All Python application code
- Contains: Streamlit pages, authentication, database access, utilities
- Key files: `main.py` (router), `config.py` (client init), `auth.py` (session)

**app/components/:**
- Purpose: Reusable form and UI components
- Contains: Parameterized Streamlit widget functions that return structured data
- Key files: `haul_form.py` (multi-haul capture), `coordinate_input.py` (coordinate input with DMS/decimal toggle)

**app/views/:**
- Purpose: Role-based page implementations
- Contains: One module per page, each with `show()` entry point
- Key files: `dashboard.py`, `transfers.py`, `bycatch_alerts.py` (admin/manager pages), `vessel_owner_view.py` (read-only)

**app/utils/:**
- Purpose: Shared functions across views
- Contains: Formatting, coordinate conversion, CSS/branding, file parsing
- Key files: `styles.py` (NAVY color, page_header/section_header functions), `formatting.py` (format_lbs, get_risk_level)

**sql/:**
- Purpose: Database schema definition and migrations
- Contains: PostgreSQL DDL, views, RLS policies, sequential migrations
- Key files: `schema.sql` (core tables), migrations `005_add_multi_tenant.sql` (org_id support), `012_bycatch_hauls.sql` (haul capture)

**sql/migrations/:**
- Purpose: Incremental schema changes
- Contains: Numbered SQL files applied in order
- Pattern: Each file has descriptive name and idempotent changes
- Key: Run migrations in sequence to evolve schema safely

**tests/:**
- Purpose: Unit and integration test suite
- Contains: Pytest tests with Supabase mocking via `mock_supabase` fixture
- Key files: `conftest.py` (cache clearing before each test), individual test modules per view

**tests/e2e/:**
- Purpose: End-to-end tests with real Supabase connection
- Contains: Full workflow tests (login → transfer → verify)
- Key files: `test_app.py` (login flow), `test_bycatch_alerts.py` (alert workflow)

## Key File Locations

**Entry Points:**
- `app/main.py`: Streamlit app router, authentication check, sidebar navigation, page loader
- `supabase/functions/send-bycatch-alert/`: Backend webhook handler for email notifications

**Configuration:**
- `app/config.py`: Supabase client init, CURRENT_YEAR, LBS_PER_MT constants
- `.env` (not in repo): SUPABASE_URL, SUPABASE_KEY
- `pytest.ini`: Pytest configuration (test discovery, markers)

**Core Logic:**
- `app/views/dashboard.py`: Quota remaining calculations and display
- `app/views/transfers.py`: Transfer form, validation, history display
- `sql/schema.sql`: `quota_remaining` view (SQL-based quota calculation)
- `sql/schema.sql`: `account_balances` view (eFish reconciliation)

**Testing:**
- `tests/conftest.py`: Pytest fixtures including `mock_supabase` and cache clearing
- `tests/test_transfers.py`: Transfer validation and quota check tests
- `tests/e2e/test_bycatch_alerts.py`: Full bycatch workflow test

**Authentication & Authorization:**
- `app/auth.py`: Login/logout, JWT refresh, role checking, session management
- `sql/schema.sql`: RLS policies for `user_profiles` and tenant-specific tables

**Styling & UI:**
- `app/utils/styles.py`: NAVY color constant, `page_header()`, `section_header()`, CSS injection
- `app/main.py` lines 75-256: Login page custom styling (glassmorphism, wave SVG)

## Naming Conventions

**Files:**
- **View modules:** Snake case, descriptive (e.g., `bycatch_alerts.py`, `vessel_owner_view.py`)
- **Utility modules:** Single responsibility (e.g., `styles.py`, `coordinates.py`, `formatting.py`)
- **Test files:** Prefix with `test_` (e.g., `test_transfers.py`)
- **Migrations:** Numbered prefix with description (e.g., `005_add_multi_tenant.sql`)

**Functions:**
- **Public:** Snake case, descriptive action verb (e.g., `show()`, `login()`, `format_lbs()`)
- **Private (views):** Underscore prefix (e.g., `_fetch_quota_remaining()`, `_apply_create_alert_styles()`)
- **Cached fetchers:** `_fetch_*` pattern (e.g., `_fetch_transfers()`, `_fetch_psc_species()`)

**Variables:**
- **Constants:** UPPER_CASE (e.g., `CURRENT_YEAR`, `LBS_PER_MT`, `SPECIES_MAP`, `NAVY`)
- **Session state keys:** Snake case, descriptive (e.g., `authenticated`, `user_role`, `org_id`, `filter_coop`)
- **Database columns:** Snake case (e.g., `balance_date`, `species_code`, `harvest_date`, `is_deleted`)

**Types:**
- **Classes:** PascalCase (None in app code, only Supabase Client)
- **View names:** Snake case (e.g., `quota_remaining`, `account_balances`)
- **Table names:** Snake case (e.g., `coop_members`, `quota_transfers`, `bycatch_alerts`)

## Where to Add New Code

**New Feature (e.g., new quota calculation):**
- **Primary code:** `app/views/[feature_name].py` with `show()` function
- **Tests:** `tests/test_[feature_name].py` with fixtures for data
- **Database:** Add columns to `sql/migrations/XXX_[feature_name].sql`
- **Navigation:** Add to `app/main.py` nav_options dict

**New Component/Module (e.g., new input form):**
- **Implementation:** `app/components/[component_name].py` with parameterized render function
- **Tests:** `tests/test_[component_name].py`
- **Usage:** Import and call from views that need it

**New Utility Function (e.g., new formatter):**
- **Implementation:** `app/utils/[category].py` (e.g., add to `formatting.py`)
- **Tests:** `tests/test_utils.py` or specific test file
- **Export:** Add to `app/utils/__init__.py` if used widely

**New Page View (e.g., analytics page):**
1. Create `app/views/analytics.py` with `show()` function
2. Add to page_modules dict in `app/main.py` line 463
3. Add to nav_options in `app/main.py` for appropriate roles
4. Create `tests/test_analytics.py`
5. Add any database queries as cached fetchers in the view module

**New Role:**
1. Add role string to `user_profiles.role` enum (SQL migration)
2. Add role check in `app/auth.py` if needed (role helpers)
3. Create views for the role in `app/views/`
4. Add role-based nav_options in `app/main.py` show_sidebar()

## Special Directories

**tests/.pytest_cache/:**
- Purpose: Pytest cache directory
- Generated: Yes (by pytest)
- Committed: No (.gitignore)

**.planning/codebase/:**
- Purpose: GSD codebase analysis documents
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md
- Generated: No (manually written)
- Committed: Yes

**supabase/.temp/:**
- Purpose: Supabase local dev temporary files
- Generated: Yes (by supabase CLI)
- Committed: No (.gitignore)

**.streamlit/:**
- Purpose: Streamlit configuration
- Contains: secrets.toml (local), config.toml (global settings)
- Generated: No (manually created, secrets auto-created by CLI)
- Committed: Partially (config.toml yes, secrets.toml no)

---

*Structure analysis: 2026-01-28*
