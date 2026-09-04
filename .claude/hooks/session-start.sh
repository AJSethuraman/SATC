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
