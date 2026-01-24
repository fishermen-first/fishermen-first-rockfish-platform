#!/usr/bin/env node
/**
 * PreToolUse Hook - Remind to run tests before pushing
 */

let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(data);
    const cmd = input.tool_input?.command || '';

    if (/git push/.test(cmd)) {
      console.error('[Hook] Before pushing, consider:');
      console.error('[Hook]   pytest tests/ --ignore=tests/e2e -v');
      console.error('[Hook]   git diff HEAD~1 --stat');
    }
  } catch (e) {
    // Ignore
  }

  console.log(data);
});
