# External Integrations

## Services

| Service | Purpose | Auth | Notes |
|---------|---------|------|-------|
| Supabase | DB + Auth + Storage + Edge Functions | `SUPABASE_URL` + `SUPABASE_KEY` | PostgreSQL 17, RLS enforced |
| Resend | Bycatch alert emails | `RESEND_API_KEY` (Edge Function secret) | Free tier: 100/day |
| eLandings | Harvest data import | Processor credentials (pending) | Training API tested |

## Required Env Vars

```
SUPABASE_URL          # Supabase project URL
SUPABASE_KEY          # Anon key (frontend)
SUPABASE_SERVICE_ROLE_KEY  # Tests only (bypasses RLS)
RESEND_API_KEY        # Email (Edge Function secret)
TEST_PASSWORD         # E2E tests
ADMIN_PASSWORD        # E2E tests
```

## Rate Limits

- Supabase Auth: 30 sign-in/5min/IP, 150 refresh/5min/IP
- Resend: 100 emails/day (free tier)
- PostgREST: max 1000 rows per query

## Cache TTLs

| Data | TTL | Why |
|------|-----|-----|
| Quota remaining | 60s | Frequently changing |
| Transfer history | 30s | Near-realtime |
| Reference data (LLPs, species, coops) | 300s | Rarely changes |
| Alerts | 60s | Moderate volatility |
