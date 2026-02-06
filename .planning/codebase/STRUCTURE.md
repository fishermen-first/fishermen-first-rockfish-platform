# Codebase Structure

```
app/
├── main.py                 # Entry point: router, sidebar, auth check
├── auth.py                 # Login/logout, JWT refresh, role checks
├── config.py               # Supabase client, CURRENT_YEAR, LBS_PER_MT
├── components/             # Reusable UI: haul_form.py, coordinate_input.py
├── views/                  # Pages (each has show() entry point)
│   ├── dashboard.py        # Quota remaining dashboard
│   ├── transfers.py        # Transfer entry/history
│   ├── bycatch_alerts.py   # Alert management (manager)
│   ├── report_bycatch.py   # Report form (vessel owner)
│   ├── allocations.py      # Allocation lookup
│   ├── account_balances.py # eFish reconciliation
│   ├── account_detail.py   # eFish detail
│   ├── upload.py           # CSV/Excel uploads
│   ├── rosters.py          # Reference data
│   ├── vessel_owner_view.py # Read-only dashboard
│   └── processor_view.py   # Processor role
└── utils/                  # Shared: styles, formatting, coordinates, parsers, storage

sql/
├── schema.sql              # Core tables, quota_remaining view, RLS
├── checks.sql              # Data quality sanity checks
└── migrations/             # 001-015 sequential migrations

tests/                      # 362 unit + 26 integration + 10 e2e
supabase/functions/         # Edge Functions (send-bycatch-alert)
```

## Adding New Code

- **New page**: Create `app/views/<name>.py` with `show()`, add to `main.py` nav_options + page_modules
- **New component**: Create `app/components/<name>.py`, import from views
- **New utility**: Add to existing `app/utils/<category>.py`
- **New migration**: `sql/migrations/0XX_<description>.sql`
- **New tests**: `tests/test_<feature>.py`
