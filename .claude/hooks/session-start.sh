#!/bin/bash
set -euo pipefail

# Only needed for Claude Code on the web — each session runs in its own
# ephemeral container, so plugin installs from a prior session never carry
# over. Re-running these on every session start is safe: both commands are
# idempotent and no-op with exit 0 when the marketplace/plugin are already
# present.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

claude plugin marketplace add AJSethuraman/SATC
claude plugin install canon@satc --yes

# The install above only takes effect from the *next* session: plugin skills are
# discovered before SessionStart hooks run, so the session that installs canon
# is the one session without it. Emit the record directly so Bassy is the
# standing behaviour here too. Hook stdout is added to the session's context.
#
# Read the files, never a summary of them: a conviction paraphrased is one the
# firm will disown the moment it is read back at them.
if [ -f "$CLAUDE_PROJECT_DIR/canon/skills/bassy/SKILL.md" ]; then
  echo "# Standing behaviour for this session: Count Bassy"
  echo
  echo "The canon plugin was installed above but is not loaded in this session."
  echo "The record below is read from this repository's working tree, which is"
  echo "where canon is written. Step into the role from it."
  echo
  cat "$CLAUDE_PROJECT_DIR/canon/skills/bassy/SKILL.md"
  echo
  cat "$CLAUDE_PROJECT_DIR/canon/CONVICTIONS.md"
fi
