# Technology Stack

## Core

| Tech | Version | Purpose |
|------|---------|---------|
| Python | 3.12 | Application code |
| Streamlit | 1.28+ | Web UI framework |
| Supabase | 2.0+ (SDK) | Backend: PostgreSQL 17 + Auth + Storage + Edge Functions |
| pandas | 2.0+ | Data manipulation |
| Playwright | — | E2E testing |
| pytest | 7.0+ | Test runner |

## Secondary

- TypeScript/Deno — Edge Functions
- openpyxl — Excel parsing
- folium + streamlit-folium — Bycatch map
- python-dotenv — Env var management

## Infrastructure

- Supabase Cloud (PostgreSQL, Auth, Storage, Edge Functions)
- Streamlit Cloud or custom server for frontend
- Resend for email delivery
