#!/usr/bin/env node
/**
 * PostToolUse Hook - Warn about print() statements in Python files
 * Equivalent to console.log check for JS
 */

const fs = require('fs');

let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(data);
    const filePath = input.tool_input?.file_path;

    if (filePath && fs.existsSync(filePath) && filePath.endsWith('.py')) {
      const content = fs.readFileSync(filePath, 'utf8');
      const lines = content.split('\n');
      const matches = [];

      lines.forEach((line, idx) => {
        // Match print() but not # print or """print or logging.print
        if (/^\s*print\s*\(/.test(line) && !line.trim().startsWith('#')) {
          matches.push(`${idx + 1}: ${line.trim()}`);
        }
      });

      if (matches.length > 0) {
        console.error(`[Hook] WARNING: print() found in ${filePath}`);
        matches.slice(0, 5).forEach(m => console.error(m));
        if (matches.length > 5) {
          console.error(`... and ${matches.length - 5} more`);
        }
        console.error('[Hook] Consider using st.write() or logging instead');
      }
    }
  } catch (e) {
    // Ignore parse errors
  }

  console.log(data);
});
