#!/bin/bash
set -euo pipefail

# What every cloud session in this repository is told before its first reply.
#
# ONE SCRIPT, FOUR HOOK COMMANDS: `.claude/settings.json` runs it once per part,
# as `session-start.sh bassy`, `record`, `role` and `talking`. Each is its own
# command because Claude Code shows a hook's stdout in full only up to 10,000
# characters. Past that it saves the output to a file and shows a
# 2,000-character preview, and nothing asks the session to read the rest. This
# script used to print Bassy and the whole of CONVICTIONS.md in one go, about
# 37,000 characters, so every session saw the first 2,000 of Bassy and nothing
# of the record. Found by a review on 14 October 2026; the firm: "Ok fix it".
#
# Only needed for Claude Code on the web — each session runs in its own
# ephemeral container, so plugin installs from a prior session never carry
# over, and canon's own plugin hook does not run in the session that installs
# it. Elsewhere, canon is installed already and prints what it needs.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

CANON="$CLAUDE_PROJECT_DIR/canon"
CAP=10000

# Print a part, and say so on its first line if it would be cut. The first line
# is in the preview, so a part that has outgrown the cap still tells the session
# what to go and read, instead of failing silently the way the old one did.
emit() {
  local out="$1" whole="$2" chars
  chars=$(wc -m < "$out")
  if [ "$chars" -ge "$CAP" ]; then
    echo "WARNING: this part is $chars characters, past Claude Code's $CAP-character limit, so only a preview is shown. Read $whole in full before relying on it."
    echo
  fi
  cat "$out"
}

OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT

case "${1:-bassy}" in

bassy)
  # Re-running these on every session start is safe: they are idempotent and
  # no-op with exit 0 when the marketplace and plugins are already present.
  # Their progress lines go to stderr, so they do not use up the cap.
  claude plugin marketplace add AJSethuraman/SATC >&2
  claude plugin install canon@satc --yes >&2
  # `desk` was NOT installed here until 7 September 2026, and the omission was
  # only found when the firm asked a desk a question in a fresh session and
  # there was no desk to ask. The practice's own tooling should be present
  # wherever the practice's work is done.
  claude plugin install desk@satc --yes >&2

  # The install above only takes effect from the *next* session: plugin skills
  # are discovered before SessionStart hooks run, so the session that installs
  # canon is the one session without it. Print the role directly so Bassy is
  # the standing behavior here too.
  if [ -f "$CANON/skills/bassy/SKILL.md" ]; then
    {
      echo "# Standing behavior for this session: Count Bassy"
      echo
      echo "The canon plugin was installed above but is not loaded in this session."
      echo "Bassy is read from this repository's working tree, which is where canon"
      echo "is written. Step into the role from it. The record of convictions"
      echo "follows in its own part."
      echo
      cat "$CANON/skills/bassy/SKILL.md"
    } > "$OUT"
    emit "$OUT" "canon/skills/bassy/SKILL.md"
  fi
  ;;

record)
  # READ THE FIRM'S WORDS, NEVER A SUMMARY OF THEM: a conviction paraphrased is
  # one the firm will disown the moment it is read back at them. The whole file
  # is 28,000 characters and cannot be shown in full, so this prints every held
  # conviction's own quote, verbatim, with what brings it into play. The why,
  # the challenge and the rulings by project stay in the file, which is named.
  [ -f "$CANON/CONVICTIONS.md" ] || exit 0
  {
    echo "# The record Bassy challenges from"
    echo
    echo "Every held conviction, in the firm's own words. The full entries, the"
    echo "declined proposals and the rulings by project are in"
    echo "\`canon/CONVICTIONS.md\`. Read the entry before you challenge from it,"
    echo "and read *Rulings by project* before challenging on a project that is"
    echo "not the practice's own software."
    echo
    python3 - "$CANON" <<'PY' || echo "(The index could not be built here. Read canon/CONVICTIONS.md.)"
import sys
sys.path.insert(0, sys.argv[1])
import record
from pathlib import Path
convictions = record.parse_convictions(
    (Path(sys.argv[1]) / "CONVICTIONS.md").read_text(encoding="utf-8"))
for c in convictions:
    if c.state != "held":
        print(f"- **{c.id} · {c.title}**: {c.state}, so it does not fire.")
        continue
    print(f"- **{c.id} · {c.title}** (applies: {c.applies}; recorded {c.recorded})")
    print(f"  > *{c.quote}*")
    print(f"  Fires on: {', '.join(c.fires_on)}")
PY
  } > "$OUT"
  emit "$OUT" "canon/CONVICTIONS.md"
  ;;

role)
  # THE ROLE, read out of the repository rather than pasted into a prompt.
  #
  # A session starts blank, so everything it knows about its job arrives in a
  # prompt somebody types or in a hook — and a pasted prompt dies with the
  # container. That is continuity through memory, which is the exact thing
  # canon exists to replace.
  #
  # NAMED, NEVER ASSUMED. A session building the website must not be told it is
  # the research desk: C7 says the context follows the role, and the challenge
  # it names is "an agent given a role name whose tools and context do not
  # match it". So an unset variable, or a name with no file, prints nothing —
  # refuse rather than default, the same rule the rest of this repository runs
  # on.
  ROLE_FILE="$CLAUDE_PROJECT_DIR/.claude/roles/${SATC_ROLE:-}.md"
  if [ -n "${SATC_ROLE:-}" ] && [ "${SATC_ROLE}" != "README" ] \
     && [ -f "$ROLE_FILE" ]; then
    {
      echo "# This session has a role: ${SATC_ROLE}"
      echo
      echo "Read from \`.claude/roles/${SATC_ROLE}.md\` in this repository, so it"
      echo "survives the container. It says what this session is FOR."
      echo
      cat "$ROLE_FILE"
    } > "$OUT"
    emit "$OUT" ".claude/roles/${SATC_ROLE}.md"
  fi
  ;;

talking)
  # How to talk to the firm: the same file canon's own plugin hook prints,
  # generated from canon/VOICE.md. If both fire, it appears twice, identical.
  if [ -f "$CANON/hooks/session-start.md" ]; then
    cat "$CANON/hooks/session-start.md" > "$OUT"
    emit "$OUT" "canon/VOICE.md"
  fi
  ;;

*)
  echo "session-start.sh: unknown part '$1' (expected bassy, record, role or talking)" >&2
  exit 1
  ;;
esac
