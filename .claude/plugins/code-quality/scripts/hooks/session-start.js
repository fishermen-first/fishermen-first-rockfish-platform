#!/usr/bin/env node
/**
 * SessionStart Hook - Load previous context on new session
 * Cross-platform Node.js version for Windows/Mac/Linux
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const SESSIONS_DIR = path.join(os.homedir(), '.claude', 'sessions');
const PLANNING_DIR = path.join(process.cwd(), '.planning');

// Check for project SESSION.md
const sessionMd = path.join(PLANNING_DIR, 'SESSION.md');
if (fs.existsSync(sessionMd)) {
  const stat = fs.statSync(sessionMd);
  const ageHours = (Date.now() - stat.mtimeMs) / (1000 * 60 * 60);

  if (ageHours < 48) {
    console.error(`[SessionStart] Found .planning/SESSION.md (${Math.round(ageHours)}h old)`);
    console.error('[SessionStart] Run "catch up" or read SESSION.md for context');
  } else {
    console.error(`[SessionStart] SESSION.md is stale (${Math.round(ageHours)}h old) - rely on git`);
  }
}

// Check for recent global session files (last 7 days)
if (fs.existsSync(SESSIONS_DIR)) {
  try {
    const files = fs.readdirSync(SESSIONS_DIR)
      .filter(f => f.endsWith('.tmp'))
      .map(f => ({
        name: f,
        mtime: fs.statSync(path.join(SESSIONS_DIR, f)).mtimeMs
      }))
      .filter(f => Date.now() - f.mtime < 7 * 24 * 60 * 60 * 1000)
      .sort((a, b) => b.mtime - a.mtime);

    if (files.length > 0) {
      console.error(`[SessionStart] ${files.length} recent session(s) in ~/.claude/sessions`);
    }
  } catch (e) {
    // Ignore errors
  }
}

// Pass through stdin to stdout (required for hooks)
let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => console.log(data));
