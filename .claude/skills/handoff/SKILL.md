---
name: handoff
description: Condense the current conversation into a handoff document so a fresh session (or another agent) can pick up cleanly. Use when the user says "handoff", "hand this off", "wrap up for next session", or a session is getting long and work will continue later. Especially important here because sessions are ephemeral — the container is wiped, so a handoff must be committed to survive.
---

# Handoff

Produce a document that lets a brand-new session continue this work with no loss
of context.

## Critical adaptation for this environment

Sessions run in an **ephemeral container** that is wiped when it ends — only what
is **committed to the repo** survives. So do **not** save the handoff to a temp
directory (it would vanish). Instead save it to `docs/handoffs/<YYYY-MM-DD>-<topic>.md`
in the repo and **commit + push it** (or, if the user prefers, output it inline so
they can paste it into the next session). Confirm which they want.

## Process

1. **Synthesize the conversation** into a handoff doc (structure below). Capture
   decisions and current state, not a full transcript.
2. **Reference existing artifacts by path/URL** — PRDs, `PLAN.md`, ADRs, the open
   PR — rather than repeating their contents.
3. **Redact sensitive data.** Never include secrets, API keys, or client PII
   (names/SSNs/EINs). This is a tax practice — treat any real taxpayer detail as
   off-limits in the handoff.
4. **Add a "Suggested next skills" section** — which skills the next session
   should run (e.g. `/to-issues`, `/diagnosing-bugs`).
5. If the user gave a focus for the next session, make that the top priority.
6. Save + commit (or output inline) per the adaptation above.

## Handoff document contains

- **Goal / current task** — what we're trying to achieve.
- **State** — what's done, what's in flight, what's blocked. Name the branch and
  open PR.
- **Key decisions** — with one-line rationale each.
- **Next steps** — ordered, concrete, with suggested skills to run.
- **References** — paths/URLs to PRDs, plans, ADRs, issues, PR.
- **Watch out for** — gotchas, dead ends already tried.
