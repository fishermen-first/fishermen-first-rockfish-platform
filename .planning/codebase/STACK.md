# Technology Stack

**Analysis Date:** 2026-01-28

## Languages

**Primary:**
- Python 3.12 - Frontend application with Streamlit, backend utilities, and test suite

**Secondary:**
- TypeScript - Supabase Edge Functions (Deno runtime)
- SQL - Database migrations and schema management
- CSS - Inline styles embedded in Streamlit components and HTML emails

## Runtime

**Environment:**
- Python 3.12.9
- Deno 2 (for Edge Functions)
- Streamlit server

**Package Manager:**
- pip (Python)
- npm (for Supabase Functions dependencies)
- Lockfile: `requirements.txt` (present)

## Frameworks

**Core:**
- Streamlit 1.28.0+ - Web UI framework for data applications, interactive dashboard
- Supabase 2.0.0+ - Backend as a Service (PostgreSQL + Auth + Edge Functions)

**Testing:**
- pytest 7.0.0+ - Unit and integration test runner
- pytest-mock 3.10.0+ - Mocking framework for tests

**Build/Dev:**
- Supabase CLI - Local development and schema management
- openpyxl 3.1.0+ - Excel file parsing for CSV uploads

## Key Dependencies

**Critical:**
- supabase - Python SDK for Supabase (PostgREST API, Auth, Realtime)
- streamlit - Frontend framework (1.28.0+)
- pandas 2.0.0+ - Data manipulation and analysis
- python-dotenv 1.0.0+ - Environment variable management

**Infrastructure:**
- openpyxl - Excel file reading (.xlsx format) for roster/harvest uploads
- Requests (via Edge Function calls) - HTTP client for calling Supabase Edge Functions

**Database:**
- PostgreSQL 17 (via Supabase) - Primary database
- Supabase storage - File uploads

## Configuration

**Environment:**
- `.env` file (not committed) - Required environment variables:
  - `SUPABASE_URL` - Supabase project URL
  - `SUPABASE_KEY` - Anonymous/public key for frontend
  - `SUPABASE_SERVICE_ROLE_KEY` - Service role key (for tests only, bypasses RLS)
  - `TEST_PASSWORD` - Test user password for E2E tests
  - `ADMIN_PASSWORD` - Admin test password for E2E tests

**Build:**
- `supabase/config.toml` - Local Supabase configuration
  - API port: 54321
  - Database port: 54322
  - Studio port: 54323
  - Inbucket (email testing): 54324
  - Analytics: 54327
  - Chrome inspector: 8083
- `requirements.txt` - Python dependencies with pinned versions

**Streamlit:**
- Default config in Streamlit cache (no `.streamlit/config.toml` checked in)
- Page config: wide layout, expanded sidebar, title "Fishermen First Analytics"

## Platform Requirements

**Development:**
- Python 3.12+
- Node.js 18+ (for Supabase CLI and deno functions)
- Git (for version control)
- Supabase CLI for local database
- `python-dotenv` for local .env file loading

**Production:**
- Deployment target: Supabase (managed PostgreSQL), Streamlit Cloud or custom server
- Environment variables must be set via platform (not .env file)

## External Services

**Email Delivery:**
- Resend API - Via Supabase Edge Function `send-bycatch-alert`
  - Sendgrid integration possible via SMTP (configured but not enabled locally)

**Authentication:**
- Supabase Auth - Built-in Postgres-based authentication
  - JWT tokens (3600 second expiry)
  - Refresh token rotation enabled
  - Email-based signup and login

**Database Hosting:**
- Supabase - PostgreSQL 17 with PostgREST API
- Local development via Supabase CLI (Docker-based)

**Storage:**
- Supabase Storage - File uploads (50MiB limit)

## Versioning

- Python: 3.12
- PostgreSQL: 17
- Deno: 2
- Streamlit: 1.28.0+
- Supabase Python SDK: 2.0.0+
- Pandas: 2.0.0+

---

*Stack analysis: 2026-01-28*
