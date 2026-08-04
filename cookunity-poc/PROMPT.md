# Local run prompt — CookUnity meal data POC

The harness in this folder is already built and its self-test passes. What it
has never done is run against CookUnity, because the sandbox it was written in
can't reach the site and the login step needs a human at a real browser.

Paste everything below the line into a **local** Claude Code session, from the
repo root, to do the real run.

---

## Goal

Prove we can access CookUnity meal data reliably for my own logged-in account,
using the existing harness in `cookunity-poc/`. Read the README there first —
the extraction paths and outputs are already documented.

**Strictly read-only. Do not place, modify, or cancel any orders. Do not touch
cart, subscription, delivery, or payment settings. Navigation and reads only.**
If a page action is ambiguous (a button that might add to cart), skip it and
note it. Never automate my credentials, never ask me for them, never write them
anywhere.

## Steps

1. `cd cookunity-poc && npm install && npx playwright install chromium`
2. `npm run selftest` — confirm the harness is healthy before blaming the site.
3. `npm run poc`. A browser opens; I'll log in by hand and press Enter.
4. Read `output/discovery.json`. It ranks every meal-shaped JSON response seen,
   with URLs, methods, whether a bearer token was used, and payload key names.
5. Check `output/meals.json` — how many meals, which approach won, are the
   fields populated?
6. **If the extraction came up thin or empty, adapt the harness.** Likely fixes,
   in rough order of probability:
   - `SITE.menuPaths` in `src/config.ts` points at the wrong URLs — find the
     real menu URL in the browser and set it.
   - The menu needs a delivery ZIP or plan selection before it renders.
   - The meal array scores below threshold in `findMealArray` (`src/detect.ts`)
     — inspect the HAR and adjust `FIELD_PATTERNS` / the score cutoff.
   - The DOM cards don't contain a visible price, so the structural card finder
     in `src/scrape.ts` anchors on nothing — anchor on a different marker.
   Use `output/session.har` to debug rather than re-hitting the site.
7. `npm run poc:again` — this must NOT prompt for login. That's the reliability
   claim; if it fails, fix session persistence before declaring success.
8. Write `cookunity-poc/FINDINGS.md`:
   - Which approach worked (`api` / `embedded` / `dom`) and why the others
     didn't.
   - If an API was found: URL shape, auth mechanism, and whether it can be
     replayed with the saved session outside a full browser.
   - Whether run 2 skipped login, and anything learned about session lifetime.
   - Fragility notes: what breaks first, and how we'd notice.
   - Go / no-go for the personalization phase.
9. Commit the code changes and `FINDINGS.md`. Do **not** commit
   `output/`, `storage-state.json`, or any `.har` — they carry live auth tokens
   and are already gitignored. Keep them out of chat too.

## Pace

Navigate like a person browsing the menu. No parallel request hammering, no
replaying endpoints in a loop.

## Success criteria

- [ ] `npm run selftest` passes.
- [ ] Run 1: manual login once, session saved, HAR captured.
- [ ] Run 2: no login prompt.
- [ ] `output/meals.json` has the current menu (~20+ meals), each with a name
      and price, and macros wherever the site shows them.
- [ ] `FINDINGS.md` written, ending in a go/no-go.
