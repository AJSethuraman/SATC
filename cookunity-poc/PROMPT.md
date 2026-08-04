# Claude Code Prompt — CookUnity Meal Data Access POC

> Paste everything below the line into a **local** Claude Code session (headed
> browser + manual login required — this will not work in a remote/headless
> sandbox). Run it from the repo root.

---

## Goal

Prove we can access CookUnity meal data **reliably** for my own logged-in
account. This is a read-only proof of concept: extract meal data, nothing else.
**Do not place, modify, or cancel any orders. Do not touch cart, subscription,
delivery, or payment settings. Navigation and reads only.**

If this POC passes, the next phase is personalization, explanations, and
eventually safe auto-selection — so structure the code and findings with that
in mind, but do not build any of it yet.

## Stack

- Playwright, **TypeScript preferred** (Node). Keep dependencies minimal:
  `playwright` plus a TS runner (`tsx` or `ts-node`).
- Build it as a small standalone project in `cookunity-poc/` with its own
  `package.json`, `README`, and npm scripts (`npm run poc`, `npm run poc:again`).

## Steps

1. **Open the site.** Launch headed Chromium and navigate to
   https://www.cookunity.com.

2. **Pause for manual login.** Stop and let me log in by hand (use
   `page.pause()` or wait on a terminal keypress / a logged-in DOM signal).
   Never automate credentials, never ask me for them, never write them
   anywhere.

3. **Persist the session.** Save auth state so the *second* run skips login
   entirely — either `context.storageState()` written to a local JSON file or a
   persistent `userDataDir`. On startup, reuse saved state if present and only
   pause for login when it's missing or expired.

4. **Capture a HAR file** of the whole menu-browsing session
   (`recordHar` on the context) so we can debug and inspect traffic offline.

5. **Approach A — detect meal API calls.** While navigating the menu/meal
   pages, listen to network traffic (`page.on('response')` or route
   interception). Filter for JSON/GraphQL responses whose payloads look like
   meal or menu data. For each candidate endpoint record: URL, method,
   auth mechanism (cookie vs. bearer token vs. other), and a payload sample.
   If a clean endpoint exists, prefer extracting meals from it.

6. **Approach B — fallback: scrape rendered pages.** If no usable API calls
   are obvious, extract meals from the rendered DOM instead: navigate the menu,
   scroll/paginate until everything is loaded, and parse the meal cards and/or
   meal detail pages.

7. **Output meals as JSON** to `cookunity-poc/output/meals.json`: an array of
   meal objects with `id`, `name`, and as many fields as are visible —
   description, chef, macros (calories, protein, carbs, fat, and anything else
   shown), price, rating, review count, dietary/allergen tags, category/cuisine,
   image URL, availability. Include a top-level block noting which approach
   produced the data, the capture timestamp, and the meal count. Missing fields
   are fine — capture what's there, don't fabricate.

8. **Document which approach worked and why** in `cookunity-poc/FINDINGS.md`:
   - API vs. scraping — which one worked, and why the other didn't (or wasn't
     needed).
   - Endpoint details if Approach A worked (URL shape, auth, whether it can be
     replayed with the saved session outside a full browser).
   - How session persistence behaved (did run #2 skip login?).
   - Fragility notes: what's likely to break (selectors, tokens, bot
     detection) and how we'd notice.
   - A go/no-go recommendation for the personalization phase.

## Guardrails

- **Read-only.** No clicks that mutate the account. If a page action is
  ambiguous (e.g., a button that might add to cart), skip it and note it in
  FINDINGS.md.
- **Never commit secrets or session material.** Add a `.gitignore` in
  `cookunity-poc/` covering the storage-state file, `userDataDir`, `*.har`,
  and `output/` — HARs and storage state contain auth tokens. Findings and
  code get committed; captures do not.
- **Human-paced.** Navigate like a person browsing the menu — no parallel
  request hammering, no replaying endpoints in a tight loop.

## Success criteria

- [ ] Run #1: manual login once, session saved, HAR captured.
- [ ] Run #2: **no login prompt** — saved session reused successfully.
- [ ] `output/meals.json` contains the current menu (at minimum ~20 meals),
      each with `name` + `price` and macros for meals that display them.
- [ ] `FINDINGS.md` written, including the go/no-go recommendation.
