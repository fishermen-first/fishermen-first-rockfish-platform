#!/usr/bin/env node
/**
 * PreCompact Hook - Save state before context compaction
 * Cross-platform Node.js version for Windows/Mac/Linux
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const SESSIONS_DIR = path.join(os.homedir(), '.claude', 'sessions');
const COMPACTION_LOG = path.join(SESSIONS_DIR, 'compaction-log.txt');

// Ensure sessions directory exists
if (!fs.existsSync(SESSIONS_DIR)) {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
}

const now = new Date();
const timestamp = now.toISOString().replace('T', ' ').slice(0, 19);
const timeStr = now.toTimeString().slice(0, 5);

// Log compaction event
fs.appendFileSync(COMPACTION_LOG, `[${timestamp}] Context compaction triggered\n`);

// Find active session file and note the compaction
try {
  const files = fs.readdirSync(SESSIONS_DIR)
    .filter(f => f.endsWith('.tmp'))
    .map(f => ({
      path: path.join(SESSIONS_DIR, f),
      mtime: fs.statSync(path.join(SESSIONS_DIR, f)).mtimeMs
    }))
    .sort((a, b) => b.mtime - a.mtime);

  if (files.length > 0) {
    const activeSession = files[0].path;
    fs.appendFileSync(activeSession, `\n---\n**[Compaction occurred at ${timeStr}]** - Context was summarized\n`);
  }
} catch (e) {
  // Ignore errors
}

console.error('[PreCompact] State saved before compaction');

// Pass through stdin to stdout (required for hooks)
let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => console.log(data));
