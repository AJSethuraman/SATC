#!/bin/bash
# How to talk to the firm, printed by its own hook command.
#
# ITS OWN COMMAND, NOT A BLOCK IN session-start.sh, BECAUSE OF THE CAP. Claude
# Code shows a hook's stdout in full only up to 10,000 characters; past that it
# saves the output to a file and shows a 2,000-character preview, and nothing
# asks the session to read the rest. session-start.sh prints Bassy and the whole
# record, about 37,000 characters, so anything appended there is never seen. A
# separate command gets its own cap, and this text is about 2,100.
#
# Cloud sessions only, like session-start.sh: elsewhere canon is already
# installed and its own plugin hook prints the same file.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi
TEXT="$CLAUDE_PROJECT_DIR/canon/hooks/session-start.md"
if [ -f "$TEXT" ]; then
  cat "$TEXT"
fi
exit 0
