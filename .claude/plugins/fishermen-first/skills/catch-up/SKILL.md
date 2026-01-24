---
name: Catch Up
description: This skill should be used when the user says "catch up", "catch me up", "get up to speed", "what's the status", "where were we", or is starting a new session and wants context restored from previous work.
version: 0.1.0
---

# Catch Up Skill

Quickly restore context when starting a new Claude Code session by reading saved state and git information.

## What This Skill Does

1. Reads `.planning/SESSION.md` if it exists
2. Gathers current git state
3. Checks for pending migrations
4. Presents a comprehensive summary with actionable next steps

## Workflow

### Step 1: Read Saved State

Check if `.planning/SESSION.md` exists:
- If yes: Parse the YAML frontmatter and markdown content
- If no: Proceed with git-only context

### Step 2: Gather Current Git State

Run these commands:

```bash
# Current branch
git branch --show-current

# Status overview
git status --short

# Recent commits (last 24 hours or last 10)
git log --oneline -10 --format="%h %s (%ar)"

# When was last commit?
git log -1 --format="%ar"
```

### Step 3: Check for Pending Work

```bash
# Pending migrations
ls -la sql/migrations/*.sql 2>/dev/null | tail -5

# Test status (quick check)
ls tests/*.py 2>/dev/null | wc -l
```

### Step 4: Build and Present Summary

Output format:

```markdown
# Session Resume: Fishermen First

## Quick Status
- **Branch**: [current branch]
- **Last session**: [from SESSION.md timestamp or git log]
- **Uncommitted changes**: [count] files

## What You Were Working On
[From SESSION.md "Current Focus" or inferred from git log]

## Completed Since Last Session
[From git log - list recent commits]

## Pending Work
- **Uncommitted files**: [list from git status]
- **Migrations**: [any .sql files not mentioned in commits]

## Suggested Next Steps
1. [From SESSION.md "Next Steps" or based on current state]
2. [Based on uncommitted changes - e.g., "Review and commit changes"]
3. [Any obvious follow-ups]

---

## Key Context Reminders

**This Project (Fishermen First Rockfish Platform):**
- Brand color: #1e3a5f (navy)
- Species codes: POP=141, NR=136, Dusky=172
- Quota formula: Allocation + Transfers In - Transfers Out - Harvested
- LLP is the primary identifier for quota holders

**Running the app:** `streamlit run app/main.py`
**Unit tests:** `pytest tests/ --ignore=tests/e2e -v`
```

## Example Output

When SESSION.md exists:

```markdown
# Session Resume: Fishermen First

## Quick Status
- **Branch**: feature/bycatch-manager-alerts
- **Last session**: 2026-01-18 (18 hours ago)
- **Uncommitted changes**: 2 files

## What You Were Working On
Adding bycatch alerts feature - manager create and vessel reporting UI

## Completed Since Last Session
- cde2815 Merge pull request #1 from fishermen-first/feature/bycatch-manager-alerts
- 4975688 Add bycatch alerts feature with manager create and vessel reporting

## Pending Work
- Uncommitted: sql/migrations/009_add_vessel_contacts_phone.sql
- Uncommitted: tests/test_quota_tracking.py

## Suggested Next Steps
1. Run pending migration: 009_add_vessel_contacts_phone.sql
2. Review and test quota tracking tests
3. Commit pending changes

---

## Key Context Reminders
[Standard project context]
```

When SESSION.md doesn't exist:

```markdown
# Session Resume: Fishermen First

## Quick Status
- **Branch**: main
- **Last commit**: 2 hours ago
- **Uncommitted changes**: 3 files

## What You Were Working On
(No SESSION.md found - inferring from git)

Recent activity suggests work on bycatch alerts and login page redesign.

## Recent Commits
- cde2815 Merge pull request #1 (2 hours ago)
- 4975688 Add bycatch alerts feature (3 hours ago)
- 87f6dfa Redesign login page (yesterday)

## Pending Work
- Uncommitted: .planning/ (new directory)
- Uncommitted: sql/migrations/009_add_vessel_contacts_phone.sql
- Uncommitted: tests/test_quota_tracking.py

## Suggested Next Steps
1. Review uncommitted changes
2. Run `git status` to see full details
3. Consider running `/end-session` before closing to save state

---

## Key Context Reminders
[Standard project context]
```

## Key Context to Always Include

From CLAUDE.md, always remind about:

1. **Tech stack**: Streamlit + Supabase
2. **Database**: Multi-tenant with org_id + RLS
3. **Key formula**: Quota Remaining = Allocation + In - Out - Harvested
4. **Species codes**: POP=141, NR=136, Dusky=172
5. **User roles**: admin, manager, processor, vessel_owner
6. **Branding**: #1e3a5f navy, use page_header()/section_header()

## Pro Tips

- If SESSION.md is stale (>48 hours), note it and rely more on git
- Highlight any test failures or migration issues prominently
- Keep output scannable - bullet points over paragraphs
- End with a clear "Start here" recommendation
