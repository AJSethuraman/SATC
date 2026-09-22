# Dayboard — canon ADOPT proposal

**Status: PROPOSAL ONLY.** Nothing here has been written to the record. No file
under `/root/.claude/plugins/...` was modified, `CONVICTIONS.md` and `TENETS.md`
were read and not touched anywhere on this machine, and nothing was committed,
pushed or opened as a PR. Every item below waits on an explicit yes.

Record read from the plugin root: `/root/.claude/plugins/cache/satc/canon/1.12.0`
(35 tenets, 12 convictions — 11 held). Not from `/home/user/SATC/canon/`.

---

## 1. The denominator

### 1a. What `adopt.py` reported, verbatim

```
dayboard — 55 of 55 commit(s) read, 2026-07-30 to 2026-08-26
  4 changed a test and something else in the same commit
  2 document(s) read

NOT examined, and it matters which:
  - the code itself — adoption reads history and documents, never behaviour
  - anything not in git: untracked files, ignored files, local data
  - nothing was truncated by the commit limit
  - documents below the top level of the project
  - whether any test in this repository actually passes
```

Tier sizes: **certain tier 4 commits, guessed tier 2 commits.**

**The certain tier is 4 of 55 — 7%, well under half — so the skill's
"read this as history, not a shortlist" note did not fire.** See 1c: it should
have been larger than 4, and the reason it wasn't is a tool blind spot.

**The guessed tier returned 2, not 0.** Both are from the same afternoon
(2026-07-31) and both touch the same one file. Per the skill, the shape of that
tier is a fact about how commits are written here, and the fact is this: subjects
in this repo are almost never fix-shaped. They are written as the *outcome the
household gets* — "Stop overlapping plans from hiding each other", "Tell the
household when connecting Google fails", "Show all seven days in landscape".
Those are all bug fixes. None of them carries a fix-word. **The fix-word tier
under-reads this repository by roughly an order of magnitude, and a session that
treated 2 as the bug count would be wrong.**

### 1b. What I did not examine, on top of the tool's list

- **I ran nothing.** No `npm run verify`, no build, no test, no browser. I make
  no claim about whether anything passes or renders. Everything below is read
  from commits, diffs and source.
- **I did not read the 30-odd commits before `bd7dd5d`** in full — the pre-Phase-0
  era (v7 import, D1 bootstrap, household profiles). I read their subjects and
  the diffs of the two that the guessed tier named.
- **No branches other than `main`** — there are none; `git branch -a` shows
  `main` and `origin/main` only.
- **No GitHub state** — issues, PR review conversations, CI history.

### 1c. Two corrections to the tool's own denominator

**(i) `adopt.py`'s certain tier misses this repo's test convention.** The regex
at `adopt.py:48` is

```
(^|/)(tests?|spec)(/|$)|(^|/)test_[^/]*\.py$|_test\.[a-z]+$|\.spec\.[a-z]+$
```

It matches a `tests/` directory, `test_*.py`, `*_test.ext` and `*.spec.ext`. It
does **not** match `*.test.ts` — the Vitest/Jest convention, and the one used by
all eleven unit test files in `app/lib/`. So the only commits it could see were
the four that happened to touch the `tests/` directory at the repo root.

Re-run with `.test.ts` included: **18 of 55 commits (33%) changed a test and a
source file together**, not 4. Still under half, so the skill's threshold note
still would not have fired — but the tool understated its own signal by 4.5x.
The fourteen it missed include every one of the design-handoff commits.

*This is a canon defect, not a Dayboard defect. Worth a one-line fix to
`adopt.py`; not something to record about this repository.*

**(ii) 4 of the 55 commits are merge commits and carry no diff of their own.**
`666602b` (#8), `a2d6cde` (#7), `eb170de` (#6), `033acf3` (#5) each duplicate a
branch tip that is also counted. Distinct work is closer to **47 commits**.
"55 of 55" is honest about what was *read*; it is not 55 pieces of work.

**(iii) "2 document(s) read" means `CLAUDE.md` and `README.md` only.** The tool
says it skips documents below the top level. `docs/DESIGN-BRIEF.md` and
`docs/DEPLOY.md` were therefore never opened by the run — and the design brief is
the one that is wrong (§2a).

---

## 2. Findings that need a decision

### 2a. `docs/DESIGN-BRIEF.md` is stale, confirmed, and worse than reported

The brief was added in **`87f6b64` (2026-08-26, "Add a design brief")** and
`git log -- docs/DESIGN-BRIEF.md` shows **one commit, ever**. It has not been
touched since. `CLAUDE.md`, over the same period, was changed by twelve commits.

Checked against commits and code, not against other documents. Of the seven
things listed under *"Where ideas are genuinely wanted"*, **four are built**:

| Brief says | Built by | Evidence in code |
|---|---|---|
| 1. "Overlaps now split the column into lanes" — asks what a busy Tuesday should look like | `a6662d0` | `app/lib/day-layout.ts` header: *"concurrency **collapses** instead of splitting"*, `MIN_LANE_WIDTH = 96`. Splitting was **reversed**, so the brief also misdescribes the current behaviour. |
| 2. "There is no month view and no agenda view" | `c7153f0` | `app/lib/horizon.ts` — the eight-week Coming up rail, plus a Today panel reading the same list |
| 3. "The wall display at rest… what should it be doing at 2pm on a Wednesday?" | `b951b3e` | `app/lib/rest-state.ts` — three faces, a fixed dim window |
| 5. "Colour per member is the whole system today… fails for anyone colour-blind" | `a6662d0` | `app/globals.css` member tokens: circle / diamond / rounded square / pill, household as a hatch |

Two further staleness points the brief carries that the parent's brief did not name:

- **"A left sidebar with six destinations."** `app/dayboard-client.tsx:62` says
  *"Five destinations, not six"* — Today and Week were merged into one Calendar
  destination in `624bd24`.
- **"Chores — one card per occurrence."** Reversed by `a063981` ("Make the Chores
  list a list of chores, not of occurrences"); `app/lib/chore-list.ts` collapses
  to one row per definition.
- The brief's **Current visual language** block hardcodes twelve colour values
  (`--navy #102f49` …). `a6662d0` moved colour into `app/palettes.css` under
  different names (`--db-bar`, `--db-ground`, …) and states it is *"now the only
  place colour is defined"*. The brief is a second, divergent copy of the palette.

**This is not the first time.** `e41f184` records the README as still titled
`# vinext-starter`, still describing `db/schema.ts` as *"intentionally empty"*
when it defined ten tables, and documenting commands that no longer existed.
Same species, four weeks earlier. That repeat is what turns it into a proposed
tenet (**D6**).

**Decision wanted:** update the brief, or mark it at the top as a snapshot of
2026-08-26 and stop treating it as current. Either is fine; leaving it is the
one that keeps costing.

### 2b. Conviction **C5** fires on this repository, and the standing permission is time-limited by its own terms

`convictions_for` returns **C2, C5** for Dayboard's card. C5 says the control is
the publish path, not the branch name, and that it *"is answerable by looking:
CI workflows, a Pages or hosting config, a domain."*

Looked. `.github/workflows/deploy.yml` triggers `on: push: branches: [main]` and
runs migrations then `wrangler deploy` against the household's Cloudflare
account. **Dayboard's `main` publishes to a tablet on a kitchen wall.**

`fa7833e` ("Record that merging is now part of finishing a change") records the
owner granting merge authority, with its own limits — never merge red, never
merge someone else's work or a questioned change — and its own expiry, stated in
the commit:

> *"The permission was given specifically because nothing depends on the board
> yet; once it is live in a kitchen a bad merge costs a real person a real day,
> and it goes back to being the owner's call."*

So this is a **recorded exception to C5, not a breach** — and it is exactly the
case C5's own "How it could be wrong" warns about: *"if a repository gains a
publish path later and nobody re-checks, this reads as permission that was never
given."* The publish path already exists (`ac84576`). What has not been re-checked
is the condition the permission rests on.

**Decision wanted:** is the board in daily use yet? If yes, `fa7833e`'s own terms
retire the permission and it goes back to the owner's call.

### 2c. `adopt.py` under-reads JS/TS repositories

Covered in §1c(i). Needs a canon-side fix, not a Dayboard tenet.

---

## 3. Proposed tenets

Six. All read from diffs I opened; each cites a real SHA and subject from
`/home/user/dayboard`. Wording is mine, not the commit subject's.

Before these, the honest framing: **this repository already keeps its own
tenets.** `CLAUDE.md` has a "Hard rules" section of ~20 rules, each already tied
to the incident that produced it, and it is edited by the commit that changes the
behaviour. Adoption did not discover these rules; it found them already written
down. What follows is the subset that **generalises past a kitchen wall** and is
**not already one of canon's 35**. Everything else stays local, and should.

---

### D1 · Empty, broken, and not-yet-loaded must never look alike

**Cited to `c7153f0` (2026-08-26) "Add the eight-week Coming up rail".**
`app/lib/horizon.ts`, in the file it introduced:

> *"A week with nothing in it is stated in words rather than omitted — an omitted
> week reads as a week the board failed to load, and those are the two things
> that must never look alike."*

It ships a named constant for it: `EMPTY_WEEK = "Nothing on either calendar"`.

Corroborated twice more. **`bd7dd5d`** — `fallbackEvents` *"painted 21 invented
events on the first paint of every load and permanently on any API failure"*, so
loading, failure and real data were one appearance. **`d4b7173`** — a week grid
overflowing its container: *"Nothing looked broken; the week just quietly stopped
at Saturday."*

**How this could be wrong:** it is a *display* rule and canon's S11 already
covers the checker-side twin ("Absence leaves no token"). If the firm reads them
as one tenet, this belongs as evidence under S11 instead of standing alone. I
propose it separately because S11 is about a guard being blind, and this is about
a reader being misled — different victim, different fix.

---

### D2 · An outcome nobody could see was not reported

**Cited to `7486635` (2026-08-26) "Stop the OAuth flow reporting its outcome in a
flash nobody can see".** The comment the fix left in `app/dayboard-client.tsx`:

> *"the banner vanished after about 80ms. The whole OAuth flow therefore reported
> its outcome — including 'this provider isn't set up on this server' — in a flash
> too short to read, which is indistinguishable from a button that does nothing."*

The same commit carries its sibling: a provider with no credentials on the server
was still rendering as a live link, and the fix is a disabled span. Its own words:
*"A control that looks like it works has to work."*

Corroborated by **`100932d`** — six distinct OAuth outcomes all redirected to
`/?calendar=<code>` and *nothing read the param*, so *"pressing 'Connect Google'
appeared to do nothing at all"*, hit for real on the first live deployment.

**How this could be wrong:** the 80ms number was measured in a browser, but "long
enough to read" is not a constant — it depends on the reader and the surface, and
a rule stated without a threshold can be argued either way. If the firm wants it
enforceable rather than quotable, it needs a number, and this repo does not have
one yet.

---

### D3 · When the design asks for a fact the system does not hold, say less. Never fill the gap

**Cited to `b951b3e` (2026-08-26) "Add Rest — what the wall does when nobody is
using it".** The module header it introduced, `app/lib/rest-state.ts`:

> *"The design's copy leans on facts Dayboard does not hold. […] there is no
> presence data; a sunset-to-sunrise dim window needs the household's location,
> and there is no location. Where that happens this module says something it can
> prove instead, or says nothing. Never invent the difference."*

The dim window ships as fixed hours rather than a computed sunset, and says so.

Corroborated by **`bd7dd5d`**, which deleted a mock layer that had pinned a
heading to one invented day for every user on every date, showed a hardcoded
temperature, and advertised a dinner nobody had planned — *"rendering fiction
indistinguishably from real data"*.

**How this could be wrong:** it is close to SATC's existing "never invent a value"
principle and to canon's S5, and the firm may reasonably rule it a restatement.
The part I think is genuinely new is the *source of the pressure* — the demand to
invent came from an approved design document, not from a defaulting bug, and
"the spec asked for it" is the excuse this tenet has to refuse.

---

### D4 · Nothing that runs unattended may wait for a person — and nothing that heals itself may try twice

**Cited to `37cc472` (2026-08-25) "Fail loudly: logging, health, error boundaries,
backups"** and **`ac84576` (2026-08-26) "Make merging the deploy, and let the
board update itself".**

`37cc472`: *"Dayboard runs unattended on a kitchen wall. There was not one
console.log, console.error or console.warn anywhere […] so the only signal that
anything had broken was the screen itself, and the cause was gone by the time
anyone looked."* `app/error.tsx` retries itself after 15s and `app/global-error.tsx`
reloads after 30s — *"Neither waits for a human to tap 'try again', because on a
wall display nobody is there to."*

The second half is the part that stops this being naive. `ac84576` gives the
self-reload two guards: **never while busy** (a reload landing between a tick and
its save costs more than the update is worth) and **exactly one attempt per served
build**, held in `sessionStorage` so the answer survives the reload it guards —
*"a wall tablet stuck in a loop is worse than one running last week's build."*

**How this could be wrong:** this is the most Dayboard-shaped rule in the list.
The practice's software runs with a person in front of it, so the firm may hold
this locally rather than in canon. Its second clause travels further than its
first — an unbounded self-heal is a hazard whether or not anyone is watching.

---

### D5 · A name that something outside your control has recorded is data, not a detail

**Cited to `4b230f9` (2026-08-25) "Recover an already-deployed database, and stop
squashing migrations".** From the commit body:

> *"The squashed `0000` migration was regenerated several times while the chores
> model was being built, and drizzle names each regeneration differently. A
> database deployed before the chores rebuild recorded one of the earlier names,
> so `wrangler d1 migrations apply` now sees an unfamiliar file, tries to run it
> against tables that already exist, and the deploy fails before it deploys."*

The migration's *contents* were fine. Its **filename** had been recorded in a
ledger inside a live database, and regenerating it made the two disagree. Recovery
was a hand-written one-off, `scripts/one-off/2026-08-chores.sql`, whose header
says a fresh database must not run it. The rule was written into `CLAUDE.md` in
the same commit: *"The schema has shipped. Migrations are ADDITIVE from here —
never squashed."*

**How this could be wrong:** stated too broadly it forbids ordinary renaming.
The line is narrower than "never rename": it is that once a *system you do not
control* has written down an identifier, that identifier has become part of your
interface. If the firm cannot state which systems those are for a given project,
the tenet has no edge and will be argued away.

---

### D6 · A document not touched by the commit that changed the behaviour is stale by default

**Cited to `87f6b64` (2026-08-26) "Add a design brief"** — one commit, never
amended, and wrong within the same day (see §2a for the itemised list) — and to
**`e41f184` (2026-08-25) "Commit to Cloudflare only"**, which records the README
as still titled `# vinext-starter` and still calling `db/schema.ts`
*"intentionally empty"* when it defined ten tables.

The control that works is visible in the same history: `CLAUDE.md` was edited by
twelve of the design-era commits — `d8d2670`, `a6662d0`, `624bd24`, `2d40a2f`,
`9fe93b7`, `c7153f0`, `b951b3e`, `ac84576`, `a063981`, `fa7833e`, `7486635` and
`08993b0` — because each of those changes carried its own rule. The brief was
edited by none. **The difference is not diligence; it is whether the document is
changed by the commit or by a separate act of remembering.**

Operationally: cite commits and code. A document's claim about what exists is a
claim about the day it was written.

**How this could be wrong:** it can be read as licence to stop maintaining
documents, which is the opposite of the point. It also cannot distinguish a
document that is *deliberately* a snapshot (a design brief arguably is one) from
one that claims to be current — the fix for the brief may be a dated header
rather than an update.

---

## 4. Proposed evidence for tenets canon already holds

Cheaper than new tenets and, I think, the larger part of what this repository
actually proves. `record.add_evidence`, behind a yes.

| Tenet | Evidence from Dayboard |
|---|---|
| **S28** — don't call it delivered because tests pass; walk the path and open what comes out | Six commits verify in a real browser with numbers, not impressions. `51e87ab`: two overlapping items *"now sit side by side at 58px each"* at 1194×834. `d4b7173`: *"Measured in Chromium by counting day headers actually inside the scroll container"*, across six device configurations. `e41f184`: measured the wall layout losing a CSS specificity tie — *"834px → board 196px (24% of the screen)"*. `d8d2670`: browser set to Asia/Tokyo against an America/New_York household, *"genuinely a day apart at the time of the run"*. `a063981`: *"Two decisions worth stating, both found by driving it rather than by reading."* `7486635`: the 80ms flash. This is the most-proven rule in the repository. |
| **S6** — two lists that must agree will not; derive one from the other or make them one | `f4d9e02`: *"The schema also existed in four hand-maintained places […] one of which was already two tables stale."* `d8d2670`: server timezone vs client `new Date()` — *"one mechanism is better than two that can disagree."* `c7153f0`: *"Giving either its own ordering is how two surfaces start contradicting each other about what is coming, so a test pins them to the same source."* |
| **S14** — unreachable code is unchecked code | `bd7dd5d`: a `profileKey` compared against two hardcoded initials *"could never match a v2 session"*, and `ensureHousehold` plus its email-only lookup were *"both dead and the weaker of the two scoping rules"*. `7486635`: *"`isProviderConfigured` existed and nothing called it — dead code since the provider seam went in"*, which is why a dead control shipped as a live link. |
| **S15** — a test must be able to fail for the reason its name gives | `bd7dd5d`: *"Add regression tests for the identity boundary, verified red-capable by reintroducing the header trust and confirming exactly those three tests fail."* Named the count. |
| **S4** — a tool that overstates what is broken destroys belief in the part that is true | `a063981`: counting future occurrences made an up-to-date daily chore report six outstanding — *"which is the kind of number that teaches people to stop reading the number."* Same law, household vocabulary. |
| **S1** — "produced" must never mean "wrote bytes" *(loose fit — firm's call)* | `f4d9e02`: 26 `CREATE TABLE IF NOT EXISTS` statements ran on the request path, *"which only ever creates tables that do not exist yet — against an existing database it is a no-op, so adding a column would appear to deploy successfully and silently do nothing."* A deploy that reported success and produced nothing. S1 is about artifacts and their consumers; this is about a mechanism that can only ever add. Include only if the firm reads the fit as close enough. |

---

## 5. Considered and not proposed

- **CSS specificity ties are decided by source order** (`e41f184`). Real bug, cost
  the wall layout on both portrait widths of the household's device. Not a law —
  it is a language fact, and `CLAUDE.md` already records the four viewports.
- **Ordering must be explicit, never incidental** (`a063981`: *"leaving the
  tiebreak to whatever order the board happened to send would hold today and stop
  holding tomorrow"*). True and well put, but it is one line in one module and
  canon's S19 is close enough to it.
- **Make DDL idempotent** (`2a4a12a`, `c461353` — the entire guessed tier). Both
  patched a hand-maintained bootstrap SQL file: statements jammed together on one
  line, tables created before the tables they reference, no `IF NOT EXISTS`, and
  then a `SELECT 1 AS bootstrap_complete` sentinel appended because Cloudflare's
  mobile D1 console needs a non-empty final query. **The repo did not land on
  "write better DDL" — it deleted the file.** `bd7dd5d` removed it as *"a
  hand-maintained fourth copy of the schema, already two tables stale"* and
  `f4d9e02` left one mechanism. The lesson the history actually teaches here is
  S6, above, not idempotence.
- **Make the toolchain run where the owner works** (`ce428ec` — bash-only scripts
  failed on Windows). Environmental, not a rule.
- **A control that looks tickable must tick** — already `CLAUDE.md`'s own hard
  rule; folded into D2's citation rather than proposed twice.

---

## 6. Draft identity card

Built with `adopt.Card` and `adopt.convictions_for` against the plugin's
`CONVICTIONS.md`. **It passed the drift guard on the first attempt** — no counts,
no status, no "currently", and it names no governing document. Rendered output:

```markdown
## dayboard

**What it is:** A shared household calendar and organiser for one family, built
for a tablet mounted on a kitchen wall that stays on all day, with the same board
opened on phones and laptops.

**What it is for:** The household, not the practice. It is the shared surface
rather than the entry point: everyone keeps the calendar already on their phone,
and the board pulls those together and owns the recurring things nobody's phone
owns — chores, meals and lists.

**Stack:** TypeScript, React on vinext, Cloudflare Workers and D1, Drizzle, Vitest

**Where it lives:** Its own GitHub repository, outside the SATC monorepo. Deployed
to the household's own Cloudflare account; a merge to main is the deploy.

**Convictions that apply:** C2, C5
```

Two notes on it:

- **C2 and C5 are what the matching rule returns** — both fire on "cloudflare",
  "deploy" and "main". That is the right answer and §2b is the live consequence.
- **C12 ("the gate is on how hard the call is, not how serious it is") does not
  fire, because the card does not use the word "unattended".** It would fire if I
  wrote "a wall tablet nobody attends" instead of "stays on all day". I have left
  the wording honest rather than tuned to trip a keyword, but the firm may want
  C12 on this card deliberately — the merge-authority question in §2b is exactly
  a how-hard-is-the-call question.

Append to `canon/projects/REGISTER.md` only on a yes, and by hand.

---

## 7. What is fine

Recorded so the findings above are not read as a verdict on the repository.

- **The commit messages are the best artifact in it.** Nearly every one states the
  bug, the mechanism, the fix, the alternative rejected and how it was verified —
  including the pixel measurements. Almost every proposal above was readable
  because the message said what happened, not what changed.
- **`CLAUDE.md` is a working rulebook, not a description.** Twelve edits in the
  design era, each landing the rule the commit discovered. It is the reason this
  adoption found so few rules that were *not* already written down, and that is a
  good outcome, not a thin one.
- **The two-tier test split is deliberate and documented** — unit tests on pure
  functions in `app/lib/`, worker tests driving the built artifact — and
  `CLAUDE.md` names the harness that does **not** exist yet (a real D1 binding)
  rather than pretending the gap is covered.
- **The deploy workflow's comments state their own reasoning**: migrations before
  the Worker goes live, never cancel an in-flight deploy because *"a half-applied
  schema is the one state this repo cannot recover from automatically"*, and
  main-only because *"a wall in someone's kitchen is production."*
- **No household personal data appears in any proposal above.** Where a commit
  message or code comment used a household member's name or initials, it is
  paraphrased.
