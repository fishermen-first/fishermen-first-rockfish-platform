# Plan: Email Broadcasting for Bycatch Alerts

## Overview
Add email broadcasting so managers can actually notify the fleet when they click "Share to Fleet" on a bycatch alert.

**Current state:** The Share button updates database status but doesn't send emails (TODO at line 336 in bycatch_alerts.py)

---

## Pre-requisites (User Action Required)

### 1. Create Resend Account
1. Sign up at [resend.com](https://resend.com) (free tier: 100 emails/day)
2. Go to **API Keys** > **Create API Key**
3. Copy the key (starts with `re_`)

### 2. Install Supabase CLI (if not installed)
```bash
npm install -g supabase
```

---

## Implementation Steps

### Step 1: Initialize Supabase Functions Structure
```bash
cd C:\Users\vikra\Projects\fishermen-first-rockfish-platform
supabase init
```
Creates `supabase/config.toml` and `supabase/functions/`

### Step 2: Create Edge Function
**Create:** `supabase/functions/send-bycatch-alert/index.ts`

Function logic:
1. Parse `{ alert_id }` from request
2. Fetch alert, check status (idempotent: skip if already shared)
3. Fetch all vessel contacts for org
4. Send batch email via Resend API
5. Update alert status + log to `alert_email_log`
6. Return result

### Step 3: Store Resend API Key
```bash
supabase link --project-ref <your-project-ref>
supabase secrets set RESEND_API_KEY=re_xxxxxxxxxxxx
```

### Step 4: Update Python Code
**Modify:** `app/views/bycatch_alerts.py` - `share_alert()` function (line 296)

Change from:
```python
# TODO: Call Edge Function to send emails
return True, {"sent_count": recipient_count, "email_pending": True}
```

To:
```python
response = supabase.functions.invoke("send-bycatch-alert", {"body": {"alert_id": alert_id}})
# Handle response...
```

### Step 5: Deploy & Test
```bash
supabase functions deploy send-bycatch-alert
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `supabase/functions/send-bycatch-alert/index.ts` | Edge Function (~80 lines) |

## Files to Modify

| File | Changes |
|------|---------|
| `app/views/bycatch_alerts.py` | Update `share_alert()` to invoke Edge Function |
| `tests/test_bycatch_alerts.py` | Unskip Edge Function tests |
| `.env.example` | Document Resend setup |

---

## Edge Function Key Features

- **Idempotent:** Returns success (no-op) if alert already shared
- **Rate limit warning:** Warns if > 90 recipients (Resend free tier = 100/day)
- **Partial failure handling:** Logs failures but still marks as shared
- **Audit trail:** Logs all attempts to `alert_email_log` table

---

## Email Content

**Subject:** `Bycatch Alert - {Species} Reported`

**Body:**
- Species name
- Amount (with unit: lbs or count)
- Coordinates (DMS format)
- Reporting vessel
- Timestamp
- Details (if provided)

**Sender:** `Fishermen First <onboarding@resend.dev>` (Resend test domain - no DNS setup required)

---

## Verification

1. **Local test:** `supabase functions serve` + curl
2. **Unit tests:** Unskip tests in `test_bycatch_alerts.py`, run with mocked Edge Function
3. **E2E test scenarios:**
   - Vessel owner creates alert, manager shares it, verify email received
   - Manager/admin creates alert directly, shares it, verify email received
   - Share already-shared alert (should be idempotent, no duplicate email)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Rate limits (100/day free) | Show warning when > 90 recipients |
| Spam folder | Verify custom domain for production |
| Double-click | Edge Function idempotency check |

---

## Status
- [ ] Step 1: Initialize Supabase Functions
- [ ] Step 2: Create Edge Function
- [ ] Step 3: Store Resend API Key
- [ ] Step 4: Update Python Code
- [ ] Step 5: Deploy & Test
