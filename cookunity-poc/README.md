# cookunity-poc

Read-only proof of concept for accessing CookUnity meal data, as groundwork for
meal personalization, explanations, and eventually safe auto-selection.

**Strictly read-only.** Nothing here places, modifies, or cancels an order, and
nothing touches cart, subscription, delivery, or payment settings.

## Status

| Piece | State |
|---|---|
| Extraction harness (API / embedded / DOM) | Built, 36 self-test checks passing |
| Session persistence + HAR capture | Built and verified |
| Works against CookUnity itself | **Unverified** — requires a local run |

The harness is verified against a local fixture site, not against CookUnity.
`www.cookunity.com` is blocked by this environment's egress policy (the proxy
returns 403 on CONNECT), and the login step needs a human at a real browser
regardless. So the open question for a local run is only *"does the site expose
the data"* — not *"does this code run"*.

## Running it

Requires Node 20+. First run opens a browser and waits for you to log in by
hand; credentials are never read, stored, or transmitted by this tool.

```bash
npm install
npx playwright install chromium   # first time only
npm run poc                       # run 1: log in manually, session saved
npm run poc:again                 # run 2: must NOT prompt for login
```

Outputs (all gitignored — they contain auth tokens):

- `output/meals.json` — the meals, plus which approach produced them
- `output/discovery.json` — every meal-shaped API response seen, ranked, with
  URL, method, whether it used a bearer token, and the payload's key names
- `output/session.har` — full network capture for offline debugging

`npm run selftest` exercises the whole pipeline against a local fixture without
touching the network.

## How extraction works

Three paths are tried in order, and `meals.json` records which one won:

1. **`api`** — every JSON response is scored for meal-shaped arrays (keys like
   name, price, calories, protein, chef). The highest-scoring payload wins.
2. **`embedded`** — the menu serialised into the page itself (`__NEXT_DATA__`,
   `__NUXT__`, JSON-LD), which modern JS sites do often.
3. **`dom`** — the fallback. Rather than hardcoded selectors, it finds the
   *repeating structure*: elements containing a price, grouped by tag and class
   shape, largest group wins. Fields are then read by role (heading, link,
   image) and by regex over the card text.

The DOM path is deliberately structural because CookUnity's class names are not
knowable ahead of time and hashed class names change between deploys. Hashes are
normalised out of the signature so a deploy doesn't automatically break it.

## Environment overrides

Normal local runs need neither of these.

- `PLAYWRIGHT_CHROMIUM_EXECUTABLE` — use a pinned Chromium instead of
  Playwright's own download.
- `PLAYWRIGHT_NO_SANDBOX` — disable Chromium's setuid sandbox, which cannot
  start as root inside a container.

## What a local run still has to answer

These go in `FINDINGS.md` after the first real run:

- Which approach worked, and why the others didn't.
- If an API was found: can it be replayed with the saved session outside a full
  browser, or does it need the live page?
- Did run 2 genuinely skip login, and how long does the session survive?
- What's most likely to break, and how would we notice?
- Go / no-go for the personalization phase.
