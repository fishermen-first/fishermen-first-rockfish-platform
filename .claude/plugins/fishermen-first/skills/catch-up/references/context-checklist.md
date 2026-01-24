# Context Checklist for Session Management

A guide for capturing and restoring meaningful session context.

## What Makes Good Session State

### Essential Information
- [ ] Current branch and its purpose
- [ ] What feature/fix you're implementing
- [ ] Files with uncommitted changes
- [ ] Why those changes aren't committed yet

### Valuable Context
- [ ] Decisions made (and why)
- [ ] Approaches tried that didn't work
- [ ] External dependencies (waiting on API, design, etc.)
- [ ] Test status (passing/failing/not run)

### Future-You Helpers
- [ ] Where to pick up tomorrow
- [ ] What to test before committing
- [ ] Who to follow up with
- [ ] Links to relevant docs/issues

## Writing Useful "Next Steps"

### Good Examples
```markdown
## Next Steps
1. Finish implementing vessel_contacts migration - need to add phone field
2. Write tests for quota_tracking edge cases (negative transfers)
3. Run full test suite before creating PR
4. Update TESTING.md with new test scenarios
```

### Weak Examples (Avoid)
```markdown
## Next Steps
1. Continue working
2. Fix bugs
3. Test things
```

### The "Tomorrow You" Test
Ask: "If I read this with zero memory of today, would I know exactly where to start?"

## Git Hygiene for Sessions

### Before `/end-session`
- Commit logical chunks with meaningful messages
- Stage related changes together
- Leave uncommitted only what's truly in-progress

### Commit Message Tips
- Start with verb: "Add", "Fix", "Update", "Remove"
- Reference issue numbers when applicable
- Keep first line under 72 characters

### Branch Naming
- `feature/` for new features
- `fix/` for bug fixes
- `refactor/` for code improvements
- `docs/` for documentation

## When to Skip Saving State

You might not need `/end-session` if:
- All changes are committed
- You'll be back within a few hours
- Work is fully complete and merged
- You're just exploring/researching

## Restoring Context Efficiently

### Reading SESSION.md
1. Scan "Current Focus" first
2. Check "In Progress" for uncommitted work
3. Read "Next Steps" for direction
4. Note any "Blockers" before diving in

### When SESSION.md is Stale
If the timestamp is old (>24-48 hours):
1. Rely more on git history
2. Check if branch still exists
3. Look for related PRs/issues
4. Consider if priorities have changed

### When SESSION.md is Missing
1. `git log --oneline -20` for recent history
2. `git status` for current state
3. Check open PRs/issues
4. Review CLAUDE.md for project context

## Project-Specific Context

### Fishermen First Rockfish Platform

**Always remember:**
- Multi-tenant: org_id in most queries
- RLS policies: Supabase handles row-level security
- LLP: Primary identifier for quota holders
- Soft deletes: Check `is_deleted` flag

**Common tasks:**
- Migrations go in `sql/migrations/`
- New pages: Use `page_header()` from styles.py
- Tests: `pytest tests/ --ignore=tests/e2e -v`

**Key files to know:**
- `app/main.py` - Entry point
- `app/utils/styles.py` - Branding utilities
- `CLAUDE.md` - Full project context
- `TESTING.md` - Test documentation
