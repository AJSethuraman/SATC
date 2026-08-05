# cookunity-poc

Read-only proof of concept for accessing CookUnity meal data, as groundwork for
meal personalization, explanations, and eventually safe auto-selection.

**Strictly read-only.** Nothing here places, modifies, or cancels an order, and
nothing touches cart, subscription, delivery, or payment settings.

## Status

| Piece | State |
|---|---|
| Extraction harness (API / embedded / DOM) | Built, 36 self-test checks passing |
| Session persistence | Verified — run 2 does not prompt for login |
| Works against CookUnity itself | **Yes** — 349 meals via the `api` path |

**The POC passes.** See [`FINDINGS.md`](FINDINGS.md) for the endpoint, field
coverage, and the two unresolved items (macros beyond calories are not served;
`price` is $0 for two-thirds of the catalog for reasons not yet explained).

The menu is at `/our-menu`, and Google SSO forces attach mode — see below.

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

## If login is behind "Sign in with Google"

Google refuses OAuth in an automated browser — you get **"Couldn't sign you in —
this browser or app may not be secure."** It detects Playwright regardless of
how the page looks. Two ways around it:

**Option 1 — use a password instead of Google (simplest).** If the CookUnity
account has an email/password login, use that in the Playwright window; no
Google involved. If it was created via Google, run CookUnity's "forgot
password" flow once to set one.

**Option 2 — attach to your own Chrome.** Log in as a normal human in a normal
Chrome, then point the harness at it. Nothing about that browser looks
automated, so Google is happy.

```bash
# 1. Start Chrome with debugging on, in a scratch profile (macOS):
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir=/tmp/cu-profile

# Windows (PowerShell):
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 --user-data-dir="$env:TEMP\cu-profile"

# 2. In that window, log into CookUnity by hand.
# 3. In a terminal, with that Chrome still open:
PLAYWRIGHT_CDP_URL=http://127.0.0.1:9222 npm run poc
```

The separate `--user-data-dir` keeps this away from your normal Chrome profile.
In this mode the harness attaches instead of launching, so it never pauses for
login and **no HAR is recorded** — `discovery.json` still lists every endpoint.

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

- `PLAYWRIGHT_CDP_URL` — attach to a browser you started yourself (see the
  Google sign-in section above) instead of launching one.
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
