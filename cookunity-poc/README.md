# cookunity-poc

Proof of concept: reliably access CookUnity meal data (read-only) for the
owner's own account, as groundwork for meal personalization, explanations, and
eventually safe auto-selection.

**Status:** prompt-only. Nothing is built yet.

`PROMPT.md` holds the paste-able Claude Code prompt that builds the POC. It
must be run in a **local** Claude Code session — it launches a headed browser
and pauses for manual login, which won't work remotely/headless.

Ground rules baked into the prompt:

- Playwright + TypeScript, session persisted so login happens once.
- Prefer detected meal API calls; fall back to scraping rendered pages.
- Output is `output/meals.json` plus a `FINDINGS.md` documenting which
  approach worked and why; a HAR is captured for debugging.
- Strictly read-only — no orders, no cart/subscription changes.
- Session state, HARs, and outputs are gitignored (they carry auth tokens).
