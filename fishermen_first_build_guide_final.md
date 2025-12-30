# Fishermen First Build Guide
## Prompts, Manual Steps & Dependencies

---

## Before You Start

### Manual Setup (Do These First)
- [x] Create GitHub account (if needed)
- [x] Create new GitHub repo called "fishermen-first"
- [x] Create Supabase account at supabase.com
- [x] Create new Supabase project (save the URL and anon key)
- [x] Create Streamlit account at streamlit.io
- [x] Install Claude Code on your machine
- [x] Clone your GitHub repo locally
- [x] Copy CLAUDE.md into the project root

### Info Needed from Co-op Manager
- [ ] Sample eFish file
- [ ] Sample eLandings file
- [ ] Sample fish ticket file
- [ ] Sample VMS file (if using in year one)
- [ ] Initial roster data (cooperatives, members, vessels)
- [ ] Species list with PSC flags
- [ ] Processor list
- [ ] Quota allocation hierarchy clarification

---

## Setup (January 2026)

### Prompt 1: Initialize Project ✅
```
Create the project structure for a Streamlit app as defined in CLAUDE.md. Include:
- All folders (app, pages, components, utils, sql, tests)
- Empty __init__.py files where needed
- requirements.txt with streamlit, supabase, pandas, openpyxl
- .gitignore for Python projects (include .env)
- .env.example with SUPABASE_URL and SUPABASE_KEY placeholders
- README.md with basic project description
```

### Manual Step ✅
- [x] Create .env file with your actual Supabase URL and anon key

### Prompt 2: Supabase Connection ✅
```
Create app/config.py that:
- Loads environment variables from .env
- Creates and exports a Supabase client
- Follow the conventions in CLAUDE.md
```

### Prompt 3: Database Schema ✅
```
Create sql/schema.sql with CREATE TABLE statements for all tables in the CLAUDE.md data model. Include:
- All columns with correct types
- Primary keys as uuid with default gen_random_uuid()
- Foreign key constraints
- created_at timestamps where appropriate
- Comments explaining each table
```

### Manual Step ✅
- [x] Run schema.sql in Supabase SQL editor to create tables

### Prompt 4: Test Connection ✅
```
Create a simple test script at scripts/test_connection.py that:
- Connects to Supabase
- Queries the cooperatives table
- Prints "Connection successful" if it works
```

### Manual Step ✅
- [x] Run the test script to verify connection works

---

## Foundation (January 2026)

### Prompt 5: Authentication ✅
```
Create app/auth.py that:
- Uses Supabase Auth for email/password login
- Stores user session in st.session_state
- Includes functions for login, logout, and checking auth status
- Fetches user role from users table after login
```

### Prompt 6: Login Page ✅
```
Create app/pages/login.py that:
- Shows a login form with email and password fields
- Calls auth.py functions to authenticate
- Redirects to dashboard on success
- Shows error message on failure
- Keep the UI simple and clean
```

### Prompt 7: Navigation ✅
```
Create app/main.py as the app entry point that:
- Checks if user is logged in (redirect to login if not)
- Shows a sidebar with navigation links
- Shows different nav options based on user role (admin vs co_op_manager)
- Uses st.navigation or page switching pattern
- Admin sees: Dashboard, Rosters, Uploads, Quotas, Harvests, PSC, Admin Settings
- Co-op Manager sees: Dashboard, Rosters, Uploads, Quotas, Harvests, PSC
```

### Manual Step ✅
- [x] Create a test user in Supabase Auth
- [x] Add a row to users table with that user's ID and role='admin'
- [x] Test login flow

---

## CRUD Template (January 2026)

### Prompt 8: Create CRUD Template ✅
```
Create templates/crud_page_template.md that documents the standard pattern for admin management pages. Include:
- Page structure (header with add button, data table with selection, action buttons, form)
- Session state initialization pattern
- Data fetching function pattern
- Table display with row selection
- Add/Edit form in expander
- Delete with confirmation dialog
- Variations for: foreign key dropdowns, date fields, boolean fields, historical tracking tables
- Error handling pattern
- Checklist for testing each CRUD page

This template will be referenced by all admin pages to ensure consistency.
```

### Manual Step
- [x] Review the template and adjust if needed

---

## Rosters (January 2026)

### Prompt 9: Insert Test Data Script ✅
```
Create scripts/insert_test_data.py that inserts sample data into Supabase for testing:

Cooperatives (2):
- "Rockfish Co-op Alpha"
- "Rockfish Co-op Beta"

Members (4):
- "John Smith" (will be in Alpha)
- "Jane Doe" (will be in Alpha)
- "Bob Johnson" (will be in Beta)
- "Sarah Wilson" (will be in Beta)

Vessels (4):
- "F/V Northern Light" owned by John Smith
- "F/V Sea Spray" owned by Jane Doe
- "F/V Pacific Star" owned by Bob Johnson
- "F/V Ocean Quest" owned by Sarah Wilson

Cooperative Memberships:
- Link each member to their cooperative (effective_from: 2025-01-01, effective_to: null)

Vessel Cooperative Assignments:
- Link each vessel to their owner's cooperative (effective_from: 2025-01-01, effective_to: null)

The script should:
- Use the supabase client from app.config
- Insert in the correct order (cooperatives first, then members, etc.)
- Print what was inserted
- Handle errors gracefully
```

### Manual Step ✅
- [x] Run: `python scripts/insert_test_data.py`
- [x] Verify data appears in Supabase Table Editor

### Prompt 10: View Rosters Page
```
Create app/pages/rosters.py that shows three tabs:
- Cooperatives: table listing all cooperatives
- Members: table listing all members with their cooperative assignments
- Vessels: table listing all vessels with owner and cooperative assignment

Use the historical tracking tables to show current assignments (where effective_to is null).
Include search/filter capability.
```

### Prompt 11: Manage Cooperatives (Admin)
```
Create app/pages/admin/manage_coops.py following templates/crud_page_template.md

Table: cooperatives
Fields:
- cooperative_name (text, required)
- contact_info (text, optional)
```

### Prompt 12: Manage Members (Admin)
```
Create app/pages/admin/manage_members.py following templates/crud_page_template.md

Table: members
Fields:
- member_name (text, required)
- contact_info (text, optional)
```

### Prompt 13: Manage Vessels (Admin)
```
Create app/pages/admin/manage_vessels.py following templates/crud_page_template.md

Table: vessels
Fields:
- vessel_name (text, required)
- vessel_id_number (text, required)
- member_id (foreign key to members, required, show as dropdown of member names)
```

### Prompt 14: Manage Member-Cooperative Assignments (Admin)
```
Create app/pages/admin/manage_member_coops.py following templates/crud_page_template.md

Use the "Historical Tracking" variation from the template.

Table: cooperative_memberships
Fields:
- member_id (foreign key to members, required, dropdown)
- cooperative_id (foreign key to cooperatives, required, dropdown)
- effective_from (date, required)
- effective_to (date, null if current)

Show current assignments by default. Add toggle to show historical.
"End Assignment" sets effective_to instead of deleting.
```

### Prompt 15: Manage Vessel-Cooperative Assignments (Admin)
```
Create app/pages/admin/manage_vessel_coops.py following templates/crud_page_template.md

Use the "Historical Tracking" variation from the template.

Table: vessel_cooperative_assignments
Fields:
- vessel_id (foreign key to vessels, required, dropdown)
- cooperative_id (foreign key to cooperatives, required, dropdown)
- effective_from (date, required)
- effective_to (date, null if current)

Show current assignments by default. Add toggle to show historical.
"End Assignment" sets effective_to instead of deleting.
```

### Prompt 16: Manage Processors (Admin)
```
Create app/pages/admin/manage_processors.py following templates/crud_page_template.md

Table: processors
Fields:
- processor_name (text, required)
- contact_info (text, optional)
```

### Info Needed from Co-op Manager
- [ ] Initial roster data to load

### Prompt 17: Load Initial Data Script
```
Create scripts/load_initial_data.py that:
- Reads roster data from a CSV or Excel file
- Inserts cooperatives, members, vessels, and assignments
- Handles the relationships correctly
- Prints progress and any errors

I'll provide the data file format after I receive it from the co-op manager.
```

### Manual Step
- [ ] Get roster data from co-op manager
- [ ] Run the load script

---

## File Uploads (January 2026)

### Prompt 18: Set Up Storage
```
Create app/utils/storage.py that:
- Uploads files to Supabase Storage (bucket name: 'uploads')
- Generates unique filenames with timestamps
- Returns the storage path
- Handles errors gracefully
```

### Manual Step
- [ ] Create 'uploads' bucket in Supabase Storage dashboard

### Prompt 19: File Upload Page
```
Create app/pages/upload.py that:
- Lets user select a cooperative from dropdown
- Lets user select source type (eFish, eLandings, fish_ticket, VMS)
- Lets user upload a CSV or Excel file
- Saves file to Supabase Storage
- Logs upload to file_uploads table
- Shows success/error message
- Shows recent uploads for reference
```

### Info Needed from Co-op Manager
- [ ] Sample eLandings file with column descriptions
- [ ] Sample fish ticket file with column descriptions

### Prompt 20: eLandings Parser
```
Create app/utils/parsers.py with a function parse_elandings(file) that:
- Reads the uploaded CSV/Excel file
- Validates required columns exist
- Maps columns to our harvests table schema
- Returns a list of validated records ready for insert
- Raises clear errors for validation failures

Here is a sample file: [attach sample]
Here are the column mappings: [provide mappings after reviewing sample]
```

### Prompt 21: Fish Ticket Parser
```
Add to app/utils/parsers.py a function parse_fish_ticket(file) that:
- Reads the uploaded CSV/Excel file
- Validates required columns exist
- Maps columns to our harvests table schema
- Returns a list of validated records ready for insert
- Raises clear errors for validation failures

Here is a sample file: [attach sample]
Here are the column mappings: [provide mappings after reviewing sample]
```

### Prompt 22: Connect Parsers to Upload Page
```
Update app/pages/upload.py to:
- After file upload, call the appropriate parser based on source_type
- Show a preview of parsed data before inserting
- Let user confirm or cancel
- Insert validated records to the appropriate table
- Update file_uploads row with row_count
```

---

## Quota Tracking (February 2026)

### Info Needed from Co-op Manager
- [ ] Quota allocation hierarchy clarification
- [ ] Sample quota allocation data

### Prompt 23: Manage Seasons (Admin)
```
Create app/pages/admin/manage_seasons.py following templates/crud_page_template.md

Table: seasons
Fields:
- year (integer, required)
- start_date (date, required)
- end_date (date, required)

Note: Only allow delete if no data is linked to this season.
```

### Prompt 24: Manage Species (Admin)
```
Create app/pages/admin/manage_species.py following templates/crud_page_template.md

Table: species
Fields:
- species_code (text, required)
- species_name (text, required)
- is_psc (boolean, default false)

In the table view, highlight rows where is_psc is true.
Note: Only allow delete if no data is linked to this species.
```

### Prompt 25: View Quota Allocations
```
Create app/pages/quotas.py that shows:
- Filter by season (dropdown, default to current)
- Filter by cooperative (dropdown, or all)
- Table of quota allocations showing cooperative, member, vessel, species, amount
- Totals by cooperative and species
```

### Prompt 26: Manage Quota Allocations (Admin)
```
Create app/pages/admin/manage_quotas.py following templates/crud_page_template.md

Table: quota_allocations
Fields:
- season_id (foreign key to seasons, required, dropdown)
- cooperative_id (foreign key to cooperatives, required, dropdown)
- member_id (foreign key to members, optional, dropdown)
- vessel_id (foreign key to vessels, optional, dropdown)
- species_id (foreign key to species, required, dropdown)
- amount (numeric, required)

Add filters for season and cooperative at the top.
Include a bulk upload option for CSV/Excel files.
```

### Prompt 27: Record Quota Transfers
```
Create app/pages/quota_transfers.py that lets co-op manager:
- View recent transfers
- Record a new transfer (from cooperative/member, to cooperative/member, species, amount, date)
- This is available to co_op_manager role, not just admin
```

### Prompt 28: Quota Dashboard
```
Create app/pages/dashboard.py (or update if exists) with a quota section that shows:
- Filter by season and cooperative
- For each species: allocated amount, harvested amount, transferred in/out, remaining
- Visual indicator (progress bar or gauge) showing percent used
- Warning highlight when over 80% used
```

---

## PSC Tracking (February 2026)

### Prompt 29: Manage PSC Limits (Admin)
```
Create app/pages/admin/manage_psc_limits.py following templates/crud_page_template.md

Table: psc_limits
Fields:
- season_id (foreign key to seasons, required, dropdown)
- cooperative_id (foreign key to cooperatives, required, dropdown)
- species_id (foreign key to species where is_psc=true, required, dropdown)
- limit_amount (numeric, required)

Filter the species dropdown to only show PSC species.
Add filters for season and cooperative at the top.
```

### Prompt 30: View PSC Events
```
Create app/pages/psc.py that shows:
- Filter by season, cooperative
- Table of PSC events (date, vessel, species, amount)
- Running total vs limit for each species
```

### Prompt 31: PSC Dashboard
```
Update app/pages/dashboard.py to add a PSC section that shows:
- Filter by season and cooperative
- For each PSC species: limit, total caught, remaining, percent used
- Visual indicator showing percent of limit used
- Warning highlight when over 80% of limit
```

---

## Reporting - Pre-Season (February - March 2026)

### Info Needed from Co-op Manager
- [ ] Example of CQ application format
- [ ] Example of meeting packet format

### Prompt 32: CQ Application Export
```
Create app/pages/exports.py with a CQ Application section that:
- Lets user select season and cooperative
- Generates quota allocation tables in the required format
- Includes historical harvest summaries if available
- Downloads as Excel file

Here is the required format: [provide format after receiving from co-op manager]
```

### Prompt 33: Meeting Packet Export
```
Update app/pages/exports.py to add a Meeting Packet section that:
- Lets user select season and cooperative
- Generates summary of quota allocations by species
- Generates summary of PSC limits
- Includes any relevant historical data
- Downloads as Excel or PDF

Here is an example: [provide example after receiving from co-op manager]
```

---

## Harvest Tracking (April 2026)

### Prompt 34: View Harvests
```
Create app/pages/harvests.py that shows:
- Filter by season, cooperative, vessel, date range
- Table of harvests (date, vessel, species, amount, processor)
- Totals by species
- Export to CSV option
```

### Prompt 35: Harvest vs Quota Dashboard
```
Update app/pages/dashboard.py to add a harvest section that shows:
- Filter by season and cooperative
- Summary cards: total harvested, total quota, percent used
- By-species breakdown with quota remaining
- By-vessel breakdown showing each vessel's quota usage
- Charts showing harvest over time
```

---

## Reporting - In-Season (June 2026)

### Info Needed from Co-op Manager
- [ ] Example of Intercooperative Report format

### Prompt 36: Intercooperative Report Export
```
Update app/pages/exports.py to add Intercooperative Report section that:
- Generates tables and figures required for the Council report
- Includes quota usage by cooperative
- Includes PSC usage by cooperative
- Includes harvest summaries
- Downloads as Excel or Word document

Here is the required format: [provide format after receiving from co-op manager]
```

---

## Refinements (July - September 2026)

### Info Needed from Co-op Manager
- [ ] Ex-vessel value calculation method
- [ ] Processor report format for reconciliation

### Prompt 37: Ex-Vessel Value Reports
```
[Prompt depends on clarification from co-op manager about how value is calculated]

Create reporting for ex-vessel value that:
- [Details TBD based on value calculation method]
```

### Prompt 38: Processor Report Parser
```
Add to app/utils/parsers.py a function parse_processor_report(file) that:
- Reads processor report CSV/Excel
- Maps columns to our schema
- Returns records for comparison

Here is a sample file: [attach sample]
```

### Prompt 39: Reconciliation Tool
```
Create app/pages/reconciliation.py that:
- Lets user upload a processor report
- Parses and compares against harvest records
- Shows discrepancies (missing records, amount differences)
- Allows user to flag or resolve discrepancies
```

---

## End of Season (October - November 2026)

### Prompt 40: Settlement Analytics
```
Create app/pages/settlement.py that shows:
- By cooperative: total harvest value, overages, amounts owed
- By vessel: individual settlement calculations
- Supports the processor withholding process
- Export settlement summaries
```

### Prompt 41: Final Summaries Export
```
Update app/pages/exports.py to add End of Season section that:
- Final quota usage by cooperative (for Board review)
- Final PSC usage by cooperative (for Board review)
- Ex-vessel value/volume validation for NMFS
- Downloads as Excel
```

---

## Wrap-up (December 2026)

### Prompt 42: Documentation
```
Update README.md with:
- Project overview
- Setup instructions (how to run locally)
- Deployment instructions (Streamlit Cloud)
- User guide (how to use each feature)
- Data model summary
- Troubleshooting common issues
```

### Prompt 43: Code Cleanup
```
Review the codebase and:
- Remove any unused code or comments
- Ensure consistent formatting
- Add docstrings to all functions
- Ensure error handling is consistent
- Check for any hardcoded values that should be config
```

---

## Summary: Dependencies Before Each Phase

| Phase | What You Need First |
|-------|---------------------|
| Setup | GitHub, Supabase, Streamlit accounts created manually |
| Foundation | Supabase URL and key in .env |
| Rosters | None (can use test data) |
| File Uploads | Sample files from co-op manager |
| Quota Tracking | Quota hierarchy clarification, sample data |
| PSC Tracking | Species list with PSC flags |
| Pre-Season Reporting | CQ and meeting packet format examples |
| Harvest Tracking | File parsers working |
| In-Season Reporting | Intercooperative Report format |
| Refinements | Ex-vessel value method, processor report samples |
| End of Season | Settlement calculation rules |

---

## Tips

1. **Run each prompt one at a time.** Test before moving on.
2. **Commit after each working feature.**
3. **Update CLAUDE.md** if you make decisions that change the plan.
4. **Don't skip the "Info Needed" items.** Building without that info means rework later.
5. **It's okay to adjust prompts.** If Claude Code asks for clarification or suggests a different approach, adapt.
