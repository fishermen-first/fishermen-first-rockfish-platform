#!/usr/bin/env node
/**
 * SessionEnd Hook - Persist session state when ending
 * Cross-platform Node.js version for Windows/Mac/Linux
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const SESSIONS_DIR = path.join(os.homedir(), '.claude', 'sessions');
const today = new Date().toISOString().split('T')[0];
const SESSION_FILE = path.join(SESSIONS_DIR, `${today}-session.tmp`);

// Ensure sessions directory exists
if (!fs.existsSync(SESSIONS_DIR)) {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
}

const now = new Date();
const timeStr = now.toTimeString().slice(0, 5);

if (fs.existsSync(SESSION_FILE)) {
  // Update existing session file
  let content = fs.readFileSync(SESSION_FILE, 'utf8');
  content = content.replace(/\*\*Last Updated:\*\* .+/, `**Last Updated:** ${timeStr}`);
  fs.writeFileSync(SESSION_FILE, content);
  console.error(`[SessionEnd] Updated session file: ${SESSION_FILE}`);
} else {
  // Create new session file
  const template = `# Session: ${today}
**Date:** ${today}
**Started:** ${timeStr}
**Last Updated:** ${timeStr}

---

## Current State

[Session context goes here]

### Completed
- [ ]

### In Progress
- [ ]

### Notes for Next Session
-

### Context to Load
\`\`\`
[relevant files]
\`\`\`
`;
  fs.writeFileSync(SESSION_FILE, template);
  console.error(`[SessionEnd] Created session file: ${SESSION_FILE}`);
}

// Pass through stdin to stdout (required for hooks)
let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => console.log(data));
