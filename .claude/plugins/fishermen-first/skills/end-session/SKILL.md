---
name: End Session
description: This skill should be used when the user says "end session", "save progress", "shutting down", "end of day", "pause work", or wants to capture current state before closing Claude Code. Saves session context for easy restoration later.
version: 0.1.0
---

# End Session Skill

Capture current session state before closing Claude Code so context can be easily restored in the next session.

## What This Skill Does

1. Gathers current git state (branch, uncommitted changes, recent commits)
2. Optionally asks about current focus and next steps
3. Writes a structured SESSION.md file to `.planning/`

## Workflow

### Step 1: Gather Git State

Run these commands to capture current state:

```bash
# Current branch
git branch --show-current

# Uncommitted changes
git status --short

# Recent commits (today's work)
git log --oneline --since="6 hours ago" --format="%h %s"

# Files changed today
git diff --stat HEAD~5 2>/dev/null || git diff --stat
```

### Step 2: Ask User (Optional)

Use AskUserQuestion to ask:

**Question 1:** "What were you working on this session?"
- Options:
  - "Skip - detect from git" (let git history speak)
  - "Let me describe it" (free text)

**Question 2:** "What should we start with next session?"
- Options:
  - "Continue current work"
  - "Review/test changes"
  - "Let me specify"

### Step 3: Write SESSION.md

Create `.planning/SESSION.md` with this format:

```markdown
---
timestamp: [ISO 8601 timestamp]
branch: [current branch]
---

## Current Focus
[User description or auto-detected from git log/status]

## Completed This Session
[From git log - commits made during session]

## In Progress
[Files with uncommitted changes from git status]

## Next Steps
[User-specified priorities or inferred from state]

## Blockers/Notes
[Any issues mentioned during session]
```

### Step 4: Confirm

Tell the user:
- Session state saved to `.planning/SESSION.md`
- What was captured (branch, N commits, N uncommitted files)
- Reminder: Run `/resume` in next session to restore context

## Example Output

After running `/end-session`:

```
Session state saved to .planning/SESSION.md

Captured:
- Branch: feature/bycatch-manager-alerts
- Commits today: 3
- Uncommitted files: 2
- Next steps: Continue implementing vessel alerts UI

Run `/resume` in your next session to restore this context.
```

## Edge Cases

- **No commits today**: Note "Session focused on exploration/research"
- **Clean working tree**: Note "All changes committed"
- **No .planning directory**: Create it automatically
- **Existing SESSION.md**: Overwrite (it's meant to be ephemeral)
