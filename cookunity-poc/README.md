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

## Ranking meals against your preferences

```bash
npm run poc -- --url https://www.cookunity.com/our-menu   # refresh the menu
npm run rank                                              # rank it
npm run rank -- --top 30                                  # show more
```

`preferences.json` is created from `preferences.example.json` on first run and
is **git-ignored on purpose** — `npm run tune` rewrites it, so tracking it
would collide with every `git pull`. To reset to the shipped defaults, delete
it and re-run. Every score is explained — each line shows
exactly which rules fired and what each was worth, so a surprising result is
diagnosable rather than mysterious:

```
 1. [7.50] Chicken Broccoli Bowl — Jose Garces
    +3 chicken, +2 broccoli, +2 high protein, +0.5 rated 4.71
```

**How matching works.** Where a term is looked for depends on what it means:

| Section | Searched in | Why |
|---|---|---|
| `proteins` | name, description, cuisine, protein type, tags | What the meal **is** |
| `ingredients` | all of the above **plus** the ingredient list and sides | What the meal **contains** |
| `exclude` | everything, including trace ingredients | Avoidance must not miss |

That split is not cosmetic. CookUnity publishes a full ingredient declaration,
and **chicken stock appears in mole, dirty rice and most pilafs** — matching
protein preferences against it scored salmon, shrimp, pork and beef dishes all
as "chicken". Protein type and tags state the real answer.

Terms match whole words, with plurals allowed and nothing else: `beets` and
`green beans` hit, `broccolini` does not match `broccoli`.

**`limits` are hard gates**, applied before scoring; everything else is points.
The run prints a tally of what got filtered and why, which is how you notice a
limit set too tight.

### Choosing tags that actually discriminate

Tag frequencies across the live 349-meal menu are lopsided, and a penalty on a
near-universal tag mostly just shifts the whole board down:

| Tag | Meals | Useful as a signal? |
|---|---|---|
| `High Fat` | 249 (71%) | Barely — most meals carry it |
| `High Sodium` | 244 (70%) | Barely, same reason |
| `High Protein` | 215 (62%) | Weak-ish, but it is the only protein signal there is |
| `Spicy` | 131 (38%) | Good discriminator |
| `Low Calorie` | 105 (30%) | Good |
| `Low Sodium` | 41 (12%) | Strong — rewarding the rare positive beats penalising the common negative |
| `High Fiber` | 37 (11%) | Strong |

Cuisine tags are real and usable: `American` 87, `Asian` 80, `European` 75,
`Italian` 66, `Latin American` 60, `Mediterranean` 55, `Mexican` 47.

The shipped defaults follow from this — reward the scarce good tags rather
than penalise the ubiquitous bad ones. Regenerate the table any time with:

```bash
node -e "const m=JSON.parse(require('fs').readFileSync('output/meals.json','utf8')).meals;const c={};m.forEach(x=>(x.tags||[]).forEach(t=>c[t]=(c[t]||0)+1));console.log(Object.entries(c).sort((a,b)=>b[1]-a[1]).slice(0,60).map(([t,n])=>n+'  '+t).join('\n'))"
```

### What the data does and does not support

- **Trans fat cannot be limited.** The menu API sends `nutritional_facts` with
  calories and nothing else — no fat breakdown at all. The `tagBonuses` section
  works on the coarse buckets CookUnity does publish (`High Fat`, `High
  Protein`, `High Sodium`, `Low Sugar`). These are labels, not measurements.
- **No gram-level macros**, for the same reason. `High Protein` as a tag is the
  best available proxy.
- Calories, rating, and review count *are* real numbers and are gated exactly.

A meal has one protein identity, so overlapping protein terms count once —
salmon does not score as both `salmon` and `fish`. When a liked and a disliked
protein both match, the dislike wins.

## Learning the weights instead of guessing them

Hand-picking numbers is the wrong job for a human: you have opinions about
meals, not about whether chicken should be 3.0 or 3.4. So rate meals and let
the weights be fitted.

```bash
npm run tune                # rate ~12 meals, then refit
npm run tune -- --count 25  # rate more in one sitting
npm run tune -- --apply     # refit on existing ratings, rate nothing new
npm run rank                # see the new order
```

Ratings accumulate in `feedback.json`; each run tops them up rather than
starting over. The meals it asks about are spread across the current ranking,
not taken from the top — rating fifteen meals you already rank highly teaches
it nothing about what you dislike.

It reports what moved and on what evidence, so a weight change is never a
black box:

```
  Fitted on 12 ratings — agrees with 92% of them

  What changed:
    ↓ ingredients.cauliflower: -1 → -1.68  (0 yes / 3 no)
    ↑ proteins.chicken: 3 → 3.24           (5 yes / 0 no)

  No evidence yet for: proteins.lamb, ingredients.beet
```

**Your stated preferences are the prior, not a starting guess to be
discarded.** Fitting is logistic regression pulled back toward the numbers you
wrote, so a single rating nudges a weight rather than flipping it, and a term
rated consistently several times moves further. With twelve ratings the model
adjusts your intent; it does not replace it. Terms nothing was rated on are
left alone and listed, so you can see where it is still flying blind.

`preferences.json` is backed up to `preferences.json.bak` before every write.

## Tests

```bash
npm test            # ranking + tuning rules, pure, instant
npm run selftest    # extraction pipeline against a local fixture
```

`npm test` covers ordering, word-boundary matching, the identity/ingredient
split, every hard gate, the protein double-count, weight fitting,
determinism, and that fitting never mutates its input. No browser or network.

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
