# Testing Patterns

## Run Commands

```bash
pytest tests/ --ignore=tests/e2e -v              # Unit tests (~29s, 362 tests)
pytest tests/ -v                                   # All tests incl e2e (~80s)
pytest tests/test_transfers.py -v                 # Single file
pytest tests/ --ignore=tests/e2e --cov=app --cov-report=html  # Coverage
```

## Structure

```
tests/
├── conftest.py              # Autouse cache clearing, shared fixtures
├── test_auth.py             # 47 tests
├── test_dashboard.py        # 27 tests
├── test_transfers.py        # 83 tests
├── test_bycatch_alerts.py   # 61 tests
├── test_bycatch_hauls.py    # Haul capture tests
├── test_quota_tracking.py   # 26 integration tests (needs SUPABASE_SERVICE_ROLE_KEY)
├── test_upload.py           # 35 tests
├── test_vessel_owner.py     # 28 tests
└── e2e/                     # Playwright, needs TEST_PASSWORD + ADMIN_PASSWORD
    ├── test_app.py           # 10 tests
    ├── test_bycatch_alerts.py
    └── test_bycatch_hauls.py
```

## Key Patterns

- **AAA pattern**: Arrange/Act/Assert with comments
- **Mocking**: `@patch('app.module.supabase')` + `MagicMock()` for Supabase responses
- **Session state**: Use plain dict or `MockSessionState(dict)` for `st.session_state`
- **Cache clearing**: `conftest.py` autouse fixture clears `@st.cache_data` between tests
- **Safe defaults**: Functions return 0, [], None on error — tests verify this
- **Integration tests**: Use `SUPABASE_SERVICE_ROLE_KEY`, test org `00000000-...-000000000099`, year 2099

## Adding New Tests

1. Create `tests/test_<feature>.py`
2. Use `@patch('app.views.<module>.supabase')` for DB mocks
3. Mock chain: `mock_supabase.table().select().eq().eq().execute().data = [...]`
4. Group in `class Test<Feature>:` with docstrings
5. Clear caches if feature uses `@st.cache_data`

## E2E Test Accounts

| Role | Email | Env Var |
|------|-------|---------|
| Vessel Owner | `vikram.nayani+1@gmail.com` | `TEST_PASSWORD` |
| Admin | `vikram@fishermenfirst.org` | `ADMIN_PASSWORD` |
