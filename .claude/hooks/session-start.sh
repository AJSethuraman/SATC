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

# `desk` was NOT installed here until 7 September 2026, and the omission was
# only found when the firm asked a desk a question in a fresh session and there
# was no desk to ask. It had to be installed by hand, and then its skills could
# not be called until the session reloaded. The practice's own tooling should be
# present wherever the practice's work is done.
claude plugin install desk@satc --yes

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

# THE ROLE, read out of the repository rather than pasted into a prompt.
#
# A session starts blank, so everything it knows about its job arrives in a
# prompt somebody types or in a hook — and a pasted prompt dies with the
# container. That is continuity through memory, which is the exact thing canon
# exists to replace.
#
# NAMED, NEVER ASSUMED. A session building the website must not be told it is
# the research desk: C7 says the context follows the role, and the challenge it
# names is "an agent given a role name whose tools and context do not match it".
# So an unset variable, or a name with no file, prints nothing — refuse rather
# than default, the same rule the rest of this repository runs on.
ROLE_FILE="$CLAUDE_PROJECT_DIR/.claude/roles/${SATC_ROLE:-}.md"
if [ -n "${SATC_ROLE:-}" ] && [ "${SATC_ROLE}" != "README" ] \
   && [ -f "$ROLE_FILE" ]; then
  echo
  echo "# This session has a role: ${SATC_ROLE}"
  echo
  echo "Read from \`.claude/roles/${SATC_ROLE}.md\` in this repository, so it"
  echo "survives the container. It says what this session is FOR."
  echo
  cat "$ROLE_FILE"
fi
