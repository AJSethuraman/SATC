# PRD: Expert desks — a mechanism for building experts, and the first one

**Status:** Draft · **Owner:** the firm · **Last updated:** 2026-09-04
**Plugin:** `desk` (`satc/desk`), depending on `canon`

> Grilled 4 September 2026. Authority research: `docs/research/accounting-authority-sources.md`.
> Governed by C7, C8, C9 and C10 in `canon/CONVICTIONS.md`, the ten rules in
> `docs/LOCAL-LLM-PATTERN.md`, and the fifteen behaviours in `canon:how-we-work`.

---

## 1. Problem

An agent doing real work knows its job but not everything around it. It hits a
question — *is this depreciable? how do I accrue this?* — and has three bad
options: guess, stop, or ask the firm. Guessing is the worst, and it is what
actually happens, because a model asked a question it cannot answer produces a
fluent answer anyway.

Today every one of those questions that isn't guessed reaches the firm. The firm
is the final decision layer and should be; they should not be the *first* one.

The failure this exists to prevent is narrower than "the agent is wrong." It is
**a confident wrong answer that nobody ever sees**, because the agent absorbed a
question it had no business absorbing. That costs more than an escalation, and
it costs more than a visible error, because it destroys the reason to trust any
of the other answers.

## 2. Solution

A **desk**: an expert an agent consults so a question does not reach the firm.
A desk answers only from authority it can cite, states how binding that authority
is, and **escalates rather than guesses** — with the reason it could not answer
diagnosed, so most escalations get fixed rather than repeated.

The desk is not a smarter model. It is a small deterministic engine wrapped
around whatever model is available: the engine verifies every citation before an
answer is allowed out, refuses uncited answers as a matter of code, and routes
questions to the right desk by a lookup rather than a judgement.

v1 ships **the mechanism plus exactly one desk**. Accounting is the first
subject, not the point — law, prompting, market research and anything else with
a body of authority use the same machinery. Nothing accounting-specific is
allowed into the shared layer, and a test enforces that.

## 3. Goals & Non-Goals

**Goals**

- A doer agent can ask a question and get an answer that is cited, tiered and
  checkable — or an escalation that says why.
- The firm receives only the questions that are genuinely theirs: the ones where
  authority allows a choice.
- Every claim about how good it is comes with a denominator, measured against
  reality rather than the model's prose.
- The shared layer is domain-neutral by construction, so the second desk is a
  configuration exercise and not a rewrite.
- Nothing enters the record that the firm did not ratify.
- A new desk can be created by interview rather than by hand, and the interview
  is written from what building the first one actually took.

**Non-Goals / Out of scope for v1**

- **Client data or real books.** v1 runs entirely on public regulation examples.
  Not masked, not de-identified — *absent*. This is what lets the scoreboard run
  in public CI.
- **Writing to any ledger or system of record.** A desk answers and cites. It
  never posts, closes a period, or moves a number. Occam owns posting.
- **The second desk.** v1 is one desk plus the shared layer. The second desk is
  v2 and it is the *proof*: the metric is how many changes it forces on the
  shared layer.
- **GAAP / ASC content of any kind.** Cannot be stored (see §6.3) and has no
  public worked-example set to grade against. v1 answers under federal authority
  only and refuses anything needing the Codification, saying why.
- **Contacting a client.** Not in any version of this.

## 4. User Stories

1. As a **doer agent**, I want to ask a subject-matter question without knowing
   which desk exists, so that I do not have to carry a directory of experts in a
   context window that cannot hold one.
2. As a **doer agent**, I want the engine to stop me and name the desk when I
   attempt a judgement outside my authority, so that asking is not something I
   have to remember to do.
3. As a **doer agent**, I want an answer that carries its citation and its tier,
   so that I can record *why* rather than only *what*.
4. As a **desk**, I want an answer with no resolvable citation to be refused
   before it leaves me, so that "never invent a position" is enforced by code
   rather than by a prompt I might not have received.
5. As a **desk**, I want to escalate when the only support is interpretive, so
   that a Big 4 guide's reading is never handed over in the same voice as a
   regulation.
6. As a **desk**, I want every escalation to carry a diagnosed reason, so that a
   missing site or a missing citation gets fixed instead of recurring.
7. As **the firm**, I want to see how many questions were absorbed *wrongly*
   before I see how many were right, so that the number that costs me something
   is not buried under the numbers that do not.
8. As **the firm**, I want to approve every position in a pull request I can
   actually read, so that ratification is real and not a rubber stamp on a
   forty-five-entry diff.
9. As **the firm**, I want a desk that challenges me when I push back on it, so
   that agreement means something.
10. As **the firm**, I want to know what a desk did *not* check, stated plainly,
    so that a clean result is a finding rather than a silence.
11. As **the firm**, I want the score on my own hardware reported next to the
    score on a frontier model, so that I know what the local lean costs before I
    decide to keep paying it.
12. As **the firm**, I want to be told when a stored authority has been amended
    since it was checked, so that the record ages visibly rather than quietly.
13. As **the firm**, I want a source's storage rule recorded per source, so that
    nothing is copied into the repository on an assumption about a licence.
14. As a **future desk builder**, I want the shared layer to contain no
    accounting, so that building a legal or prompting desk does not mean
    untangling one.
15. As **the firm**, I want to create a new desk by being interviewed about the
    subject, so that adding an advisor does not require me to know the file
    format.
16. As **the firm**, I want the factory to research the authority for a new
    subject and tell me which sources are binding and which are somebody's
    reading, so that a desk does not launch treating a whitepaper as a rule.
17. As **the firm**, I want a new desk to arrive as a pull request I approve,
    so that creating an advisor is ratified the same way a position is.
18. As **the firm**, I want to read *why* a desk could not cite an answer, so
    that I can tell a missing source from a missing position from an invention —
    three different problems that look identical from outside.
19. As **the firm**, I want a refused answer's reasoning kept rather than thrown
    away, so that the desk's failures are the list of what to add next.

## 5. Requirements

**The record**

1. **[P0]** Two stores with different gates. `extracted/` holds authority text an
   agent may write. `positions/` holds what the firm does where authority allows
   a choice; an agent **proposes**, never writes.
2. **[P0]** A test fails the build if a position appears in `extracted/`.
3. **[P0]** Every entry carries `checked: YYYY-MM-DD`. An entry without one is a
   parse error, not a default.
4. **[P0]** Every source carries `may_store: full_text | citation_only | license_check`.
   Default is `license_check`, which stores nothing. Storing text under a
   `citation_only` or `license_check` source is a build failure.
4a. **[P0]** Every source carries `access: public_fetch | headless_browser | signed_in_browser | human_only`,
   and the engine uses the method named there. A source with no `access` is a parse
   error, not a default — the same discipline as `checked`.
4b. **[P0]** A denied fetch is **never** retried through a different client. It
   refuses — with `source_blocked_by_us` when our own egress policy refused the
   domain, and `source_refuses_us` when the source's origin refused this client.
   The two carry different fixes and must not be one reason. A transient failure
   retries the same method once. A JS-rendered empty response may use a headless browser, because that
   escalates rendering rather than authority.
5. **[P0]** Every entry carries `tier: primary | secondary | tertiary`.
6. **[P1]** A staleness check flags entries whose source has been amended since
   `checked`, using eCFR's `latest_amended_on`, and entries older than a
   configured interval.
7. **[P0]** Ratification is a pull request. Extraction PRs and position PRs are
   separate, because a forty-five-entry diff is skimmed and a one-position diff
   is read.

**The desk**

8. **[P0]** A desk declares the subjects it answers on, as a `Fires on` list.
9. **[P0]** An answer carries: the position, the citation, the tier, and the
   `checked` date of the authority relied on.
10. **[P0]** An answer whose highest supporting tier is secondary or tertiary is
    **not an answer** — it is an escalation. That is the case where authority
    permits a choice, and choices belong to the firm.
11. **[P0]** An answer with no resolvable citation is refused by the engine.
11a. **[P0]** A refused answer is **retained, with its reasoning**, in an
    `unsupported/` queue — never served to the caller, never scored correct.
    The entry records what it concluded, what authority it believed applied, and
    why verification failed. Discarding it throws away the best evidence of what
    the record is missing.
11b. **[P1]** An `unsupported/` entry can be promoted two ways, both by pull
    request: to a **source** (the authority existed and was not loaded) or to a
    **position** (the rules permit a choice and the firm takes one). Neither
    happens automatically. An entry that was simply invented is left where it is,
    which is itself the finding.
12. **[P0]** Every escalation carries a diagnosed reason from a closed set
    (§6.5), and whether that reason is fixable.
12a. **[P1]** The `unsupported/` queue is reported alongside the scoreboard: how
    many entries, and how many resolved into a source or a position since the
    last run. A queue that only grows is a desk nobody is feeding.
13. **[P1]** A desk restates the firm's own challenge duty: when the firm pushes
    back, it engages rather than folding, from the record.

**Routing**

14. **[P0]** A doer holds exactly one tool schema for consulting desks, not one
    per desk.
15. **[P0]** Routing is a deterministic lookup over `Fires on`, never a model
    judgement about which desk to use.
16. **[P0]** The engine refuses out-of-authority acts and **names the desk** in
    the refusal.
17. **[P1]** A doer may consult a desk directly when merely unsure, without
    having been refused first.

**Scoring**

18. **[P0]** Four outcomes, reported in this order: **wrongly absorbed**,
    correct, wrong (caught), escalated. Never summed into a single figure.
19. **[P0]** The scoreboard reads engine state and the graded answer, never the
    model's account of what it did.
20. **[P0]** Scores are reported per model, side by side, never merged.
21. **[P0]** The report names what was **not** checked, in its own list.
22. **[P1]** A Forge failure is reported as a flag with the VRAM ceiling stated,
    and does not gate anything.

**The shared layer**

23. **[P0]** A test fails the build if the shared layer knows what domain it
    serves. The rule is **not** "accounting is forbidden" — it is that a shared
    interface or code path must not be meaningful only to an accountant. Prose
    explaining a concept is fine; a shared function that presupposes a domain is
    not. The firm, 4 September 2026: *"accounting-specific isn't the problem,
    it's just like… me saying it shouldn't be total jargin."*
24. **[P0]** The plugin reaches outside its own directory for nothing, matching
    canon's rule — it must lift out whole.

**The factory**

25. **[P0]** A skill interviews the firm about a new subject and emits a complete
    desk definition — subjects, sources, tiers, `may_store`, and a problem set.
26. **[P0]** The factory **proposes**: it opens a pull request and writes nothing
    to the record directly, matching `canon-mine`.
27. **[P0]** For each source it proposes, the factory resolves the storage
    question from the source's own terms and sets `may_store` accordingly,
    defaulting to `license_check` when it cannot.
28. **[P0]** A desk the factory emits passes the same record tests as a
    hand-built one — no separate, weaker path.
29. **[P1]** The factory refuses to emit a desk with no problem set, because a
    desk that cannot be scored cannot be trusted, and that is the failure this
    whole document exists to prevent.

## 6. Implementation Decisions

### 6.1 Where it lives, and how it arrives

**Name: `desk`.** Settled 4 September 2026. A sibling plugin in the existing
`satc` marketplace, beside `canon`; `.claude-plugin/marketplace.json` already
takes a `plugins` array and this adds a second entry.

Canon must stay neutral. `CONVICTIONS.md` is *what the firm believes, in their
own words, challengeable*. An ASC or IRC citation is what an authority requires —
not theirs, not challengeable. Merging them would have Bassy challenging the firm
from FASB, which is precisely the failure its one rule exists to prevent.

**`desk` depends on `canon`, and the arrow runs that way on the merits.** Desk
uses canon's `touches()` selector for routing (§6.6) and inherits Bassy's
challenge duty. Canon uses nothing from desk, and must not — its own skill
insists *"this folder lifts out whole."* A dependency in the other direction
would make the record unobtainable without the expert layer.

```json
{ "name": "desk", "version": "1.0.0", "dependencies": ["canon"] }
```

Claude Code resolves and installs declared dependencies automatically, and
enabling a plugin enables its dependencies. So **the session-start hook changes
by one word** — `claude plugin install desk@satc` — and canon still arrives on
every web session exactly as it does today.

A bundle plugin (a manifest that is only a `dependencies` array) is the
documented way to package several plugins behind one install. Not used here: a
two-link chain does not need it, and C9 says do not add the mechanism until there
is a third plugin to bundle.

**Invocation is namespaced and there is no bare form.** Plugin skills resolve as
`/plugin-name:skill-name`, so `desk` gives `/desk:ask`, `/desk:record`,
`/desk:score`. `/desk` alone is not available and designing for it would produce
`/desk:desk`. This matters less than it looks: the slash command is the third and
least important path in (§6.6) — skills load by description the way `canon:bassy`
does, and the engine's refusal routes a doer whether or not anyone remembers.

### 6.2 Record shape

One entry, in YAML, for both stores:

```yaml
- id: FA-014
  subject: [depreciate, capitalize, improvement, basis, useful life]
  question: Is a roof replacement a repair or an improvement?
  position: An improvement — a restoration under the building-structure test.
  tier: primary
  citation: 26 CFR 1.263(a)-3(k)(1)(vi)
  url: https://www.ecfr.gov/current/title-26/section-1.263(a)-3
  may_store: full_text
  checked: 2026-09-04
  text: |
    (verbatim, only where may_store is full_text)
```

`positions/` entries additionally carry the firm's own words and the PR that
ratified them, mirroring how `CONVICTIONS.md` records a conviction.

### 6.3 What may be stored, and why it is per-source

Settled by research, not assumption — `docs/research/accounting-authority-sources.md`:

- **FASB ASC** — **`human_only`. A desk may cite it by reference and may never
  read it.** Settled 4 September 2026 when the firm opened the FAF **License
  Agreement** at source, which is stricter than the copyright notice this document
  first relied on. Three clauses decide it. **§3(a)(j)** prohibits use *"for
  commercial purposes"*, and SATC holds no paid subscription, so the free
  click-through is the only licence in force and it does not reach client work at
  all. **§3(b)(i)** prohibits use *"in connection with any… large language models
  (LLMs)… under any circumstances, including using any documents, content, or
  materials in the Codification… as input into"* AI. **§3(b)(iii)** prohibits
  access *"via mechanical, programmatic, robotic, scripted, or any other automated
  means."*

  An earlier draft of this section let a desk read ASC live and cache nothing.
  **That is not available** — §3(b)(i) covers content reaching a model by any
  route, a browser included, so `signed_in_browser` does not rescue it.

  What survives is the half that matters: a **citation** (`ASC 360-10-35-4`) is a
  reference, not Codification content; and the firm reading ASC in their own
  session and writing their own conclusion is the personal use the licence
  contemplates, and those words are the firm's. So a desk answers an ASC question
  **from the firm's ratified position in `positions/`**, cites the paragraph, and
  whoever wants the text opens it themselves. That is the better artifact anyway:
  a client memo should carry SATC's position with the paragraph behind it, never
  FASB's prose filtered through a model.
- **Federal authority** — 17 U.S.C. § 105 places IRC, Treasury Regulations and
  IRS publications in the public domain. **Storable in full.** The narrow
  exception: § 105 bars the government from *originating* copyright, not from
  holding it by assignment, so a `.gov` URL is not self-certifying.
- **AICPA** — same posture as FASB.
- **A licence the firm holds may permit an internal copy.** That is a per-source
  fact, which is why `may_store` is a field and `license_check` is the default.
  Offline storage does not change the analysis; a licence might.

### 6.3a How a source is reached — declared, never discovered

A source carries **`access`** beside `may_store`, and the engine uses the method
named there. There is no try-then-escalate.

```yaml
- source: Treas. Reg. § 1.263(a)-3
  access: public_fetch          # public, static, cheapest
  may_store: full_text

- source: <a JS-rendered public site>
  access: headless_browser      # rendering, not permission — no login
  may_store: full_text

- source: <a licensed source the firm subscribes to>
  access: signed_in_browser     # the firm's own profile, on the Forge
  requires: subscription
  may_store: citation_only

- source: FASB ASC
  access: human_only            # licence forbids it reaching a model at all
  may_store: citation_only      # the reference; never the text
```

**`human_only` is not a stricter fetch — it is the absence of one.** The engine
never reaches for the source at all. It answers from a ratified position in
`positions/`, citing the reference, or it escalates. That is what a licence
forbidding both automated *and* AI access leaves available, and FASB ASC is the
worked example (§6.3).

**Why declared rather than discovered.** If a failed fetch is what triggers a
heavier tool, then a site *refusing* automated access becomes the thing that makes
us reach for one — retry-on-denial, which is precisely the pattern ruled out for
the browser capability. Declaring it means the decision is made once, when someone
actually read the source's terms, instead of every time under time pressure. It is
also C8's test: a rule applied, not a judgement made.

**A failure is handled by its cause, not by climbing.**

| Failed because | Response |
|---|---|
| **Denied by our own policy** — the egress proxy refuses the domain | Refuse with `source_blocked_by_us`. The allow-list is the fix |
| **Denied by the source** — 403 from its origin, bot management, terms forbid automation | Refuse with `source_refuses_us`. The allow-list is **not** the fix, and a different client is not the answer |
| **`human_only`** — the licence forbids the content reaching a model at all | Never attempted. Answer from `positions/` citing the reference, or escalate |
| **Empty** — JS-rendered, the fetch got a shell | A headless browser is fine. Nothing was denied and no authority changed |
| **Transient** — timeout, 5xx, reset | Retry the **same** method, once |
| **Licensed** — needs to be the firm | Never discovered at runtime; declared or unavailable |

Only the middle row is an escalation at all, and it escalates *capability*
(rendering) rather than *authority* (identity). Those two must never be conflated.

Cost ordering follows for free: a public fetch is milliseconds, a headless browser
seconds, and the signed-in desktop browser needs the Forge awake with a profile
actually logged in — the only rung that can be simply unavailable.

### 6.4 Authority tiers

The concept is domain-neutral; the contents are per-domain and declared by each
desk.

| Tier | Accounting | Law | Prompting |
|---|---|---|---|
| **primary** — binding | IRC, Treas. Reg., ASC | statute, regulation, case law | vendor docs, model cards |
| **secondary** — interpretive | Big 4 guides, AICPA practice aids | treatises, restatements | published papers, evals |
| **tertiary** — indicative | whitepapers, industry surveys | client alerts | blog posts, benchmarks |

**Big 4 guidance is not primary authority.** It is one firm's reading of the
standard. If the record flattens that distinction, a desk hands over a
whitepaper's opinion in the same voice as a regulation — which is the "large
conjecture" failure the tiering exists to stop. Secondary-or-below means
escalate.

### 6.5 Escalation reasons — a closed set

| Reason | Fixable | The fix |
|---|---|---|
| `source_blocked_by_us` | yes | grant the domain in the environment's network policy |
| `source_refuses_us` | sometimes | **not** the allow-list. The source's own origin is refusing this client — change the source's `access`, have a person open it, or accept that it is not automatable |
| `authority_absent` | yes | add it to the record, cited, via PR |
| `model_gave_up` | yes | shrink the problem (LOCAL-LLM-PATTERN rule 8) |
| `authority_permits_choice` | **no** | this is a position, and positions are the firm's |

**The first two were one reason, and collapsing them produced a real defect —
in this document, within hours of it being written.** A re-test session found
that `asc.fasb.org` was reachable and returning a **Cloudflare 403 from FASB's
own origin**, while the escalation table offered exactly one remedy: grant the
domain. The domain was already granted. A desk would have emitted that reason
forever and sent a person to a settings page to change something already
correct.

Telling them apart is mechanical, not a judgement — which is what makes it an
engine's job. **Our block** arrives as a structured refusal from the egress
proxy naming the domain. **Their refusal** arrives as an ordinary HTTP response
from the origin, carrying that origin's headers (`server: cloudflare`, a
`cf-ray`, a `__cf_bm` cookie scoped to their domain). Two different senders, two
different fixes.

This is the closed reason set doing the job it exists for: a diagnosis whose
stated fix cannot resolve the case is worse than no diagnosis, because somebody
acts on it.

Only `authority_permits_choice` should reach the firm twice. The others are work
items, and a desk that keeps emitting the same fixable reason is reporting a
defect in itself.

### 6.5a Refused, but kept — the `unsupported/` queue

A refusal is a **finding**, and throwing away the reasoning behind it destroys
the finding. The engine refuses to *serve* an uncited answer; it does not delete
it.

```yaml
# unsupported/2026-09-04-hvac-unit.yaml
question:   Is a replacement HVAC unit a repair or an improvement?
concluded:  Improvement — a betterment to the HVAC system.
believed_authority: "§1.263(a)-3(j), betterment"
failed_because: citation_not_resolvable   # the paragraph does not say this
model:      qwen3:8b
recorded:   2026-09-04
```

Three resolutions, none automatic, all by pull request:

| What the reasoning shows | Resolution |
|---|---|
| Real authority that was never loaded | promote to a **source** |
| A defensible call the rules do not settle | promote to a **position**, in the firm's words |
| An invention | leave it. Its visibility *is* the finding |

**Retained is not accepted.** An `unsupported/` entry is never returned to a
caller and never counted as correct. It exists so that the desk's failures become
the list of what to add next, rather than a number that goes down for reasons
nobody can inspect.

This is `canon-mine`'s discipline applied to answers instead of convictions —
propose, never write — and Occam already holds the shape in its review queue.

### 6.6 Routing — reuse, do not invent

`canon/record.py` already implements exactly this. `Conviction.fires_on` is a
tuple of subjects, and `touches(text, term)` is documented there as **"the only
matching rule in this codebase"** — whole words, because substring matching once
made *"extension"* fire on *"extensive"*. A desk registry uses the same field and
the same function.

```
doer: ask_desk("is a new HVAC unit depreciable or expensed?")
        │
   router — touches() over each desk's Fires on. deterministic.
        ▼
  fixed-assets desk
        │
   ├─ primary authority found  → {position, citation, tier, checked}
   └─ otherwise                → escalate(reason)
```

The doer holds one schema. Rule 1 is why: an 8,192-token window against ~11k of
tool schemas *"silently truncates the model's own instructions — it then
'ignores' rules it never received."*

### 6.7 The engine is the scoreboard

The same code does both jobs, which is C9's shape — one mechanism, not two.

```
fact pattern → desk → {position, citation, tier}
                        │
                  verify citation resolves
                  verify it says what is claimed
                        │
     ┌──────────────────┴──────────────────┐
  verified                            not verified
     │                                      │
  grade against the known answer      REFUSED (never graded correct)
```

Policy lives here rather than in a prompt because rule 6 measured the
difference: as skill prose the same policy was obeyed *"100%, 4%, 0% of runs"*;
at the API choke point it *"is obeyed always, from every path."*

### 6.8 The problem set

26 CFR 1.263(a)-3 — **verified by opening it**, not assumed: roughly 40–50
numbered examples, each a fact pattern with a stated conclusion, on the exact
judgement in scope. Public domain, storable, citable, and it runs in CI on every
push. The verified sample is (e)(6) Example 3, the condominium plumbing fact
pattern.

### 6.9 Where it runs

Model-agnostic, scored on the Forge (`qwen3:8b`, 8 GB) and on a frontier model,
reported side by side and never summed. The firm's ruling: *"it's also acceptable
that it would not work on our current hardware, that should just be flagged. at
some point we will have enough vram, for now we are limited."* This is what
LOCAL-LLM-PATTERN already promises — *"a replaceable brain in a permanent
machine… upgrading the model is `ollama pull` + re-running the scoreboard."*

### 6.10 The factory — what it actually is

**A desk is a definition, not code.** That is what makes the factory cheap enough
to sit in v1: it is an interview that fills in a form, not a compiler.

```
desks/fixed-assets/
  subjects.yaml     depreciate, capitalize, improvement, basis, useful life
  sources.yaml      Treas. Reg. §1.263(a)-3   primary   · full_text
                    PwC Viewpoint PPE guide   secondary · license_check
  problems.yaml     the graded set, with citations
  extracted/        authority text, agent-written, PR-ratified
  positions/        what the firm does where the rules allow a choice
```

The factory is a skill in the same shape as `grill-me` — one question at a time,
recommendation first — but interviewing about a **subject** rather than a
project: what does this desk answer on, where is the authority, which sources
bind and which merely interpret, what may be stored, and what is the known-answer
set that proves it works. It then opens a PR containing the folder above.

**Sequencing is a hard constraint, not a preference.** The fixed-assets desk is
built **by hand first**, and the factory is written from what that took. An
interview authored before anyone has built a desk asks the wrong questions
confidently, and the answers then have to be lived with. This is why the factory
is M4 rather than M1 despite being in v1.

**Its acceptance test is the second desk**, and that is also v2's metric: the
factory produces a working desk in a non-accounting domain without the firm
touching a file.

### 6.11 The seam into Occam

Occam already implements doer → reviewer → firm for bookkeeping.
`principals.py` enforces role and assignment server-side, written after a real
incident in which an eval run *"called `occam_switch_client` onto a real
client's books… Three accounts on a live client were deactivated. Nothing in the
engine objected."* `reviewer_gate.py` holds the line in front of the client.

**What does not exist is the desk *below* the reviewer gate** — the thing a doer
consults so a question never becomes an escalation at all. That is where this
plugs in. **No Occam changes in v1** (Non-Goal: writing to a ledger); the seam is
recorded so v2 does not have to rediscover it.

## 7. Testing Decisions

**Seams — three, all at the highest level that can carry the behaviour:**

1. **The engine, as a library — the primary seam.** `pytest`, fixtures in, graded
   outcome out, **no model involved**. Everything that must never regress lives
   here: citation verification, refusal of uncited answers, tier-triggered
   escalation, the four-way classification, `may_store` enforcement, the
   `checked` requirement, and routing via `touches()`. Deterministic, fast, gates
   the build. Prior art: `canon/tests/test_challenge.py` tests candidate
   selection exactly this way — deterministic narrowing tested directly, the
   judgement left to a human.

2. **The record, as data.** `pytest` over the YAML: no position in `extracted/`,
   no stored text under a `citation_only` or `license_check` source, every entry
   has `tier` and `checked`, every citation is well-formed. Prior art:
   `canon/tests/test_canon.py` parses and validates the record the same way, and
   `record.py` raises rather than defaulting on a malformed block.

3. **The shared layer, as a domain-blindness check.** `pytest` asserting that no
   shared interface or code path presupposes a domain — checked at the seam of
   the shared layer's own API, not by grepping comments for banned words. Prior
   art:
   `canon/tests/test_installed_elsewhere.py`, which copies the tree into a fresh
   git repository and runs it there — the same idea, that a thing claiming to be
   portable must be proven outside its home.

**The factory needs no fourth seam, and that is the point.** What it emits is a
desk definition, so seam 2 grades it — a factory-built desk passes exactly the
tests a hand-built one does, or it fails the build. Requirement 28 exists to stop
a weaker parallel path being introduced for generated desks. The interview itself
is not unit-tested; its output is, which is the higher seam.

**Deliberately not a gating seam: the scoreboard against a real model.** It is
measured, reported and committed — never asserted. A non-deterministic run cannot
gate a build without either flaking or being weakened until it proves nothing.
It is a `tools/` script run at the desk, matching how `credit-suite` marks its
live pulls `live` and never collects them.

**CI:** one new `pytest (<plugin>)` entry in the existing matrix in
`.github/workflows/test.yml`, alongside `canon`. Same shape, same reason —
`install: pip install pytest`, no dependencies, because the plugin must lift out
whole.

**What a good test proves:**

- The engine refuses an uncited answer **and the refusal names the next step** —
  not merely that it returns an error.
- A secondary-tier-only answer escalates rather than answering, with reason
  `authority_permits_choice`.
- A wrongly-absorbed answer is classified as wrongly absorbed and **not** as
  wrong.
- `touches()` routing does not fire on a substring — the regression that produced
  the rule.
- **Every check is proved capable of failing.** LOCAL-LLM-PATTERN rule 10:
  *"Seven of our check bugs produced false passes; a check that has only ever
  passed is not evidence."* Each assertion gets a mutation that must turn it red.

**Data handling.** v1 touches no client data at all — not masked, not
de-identified, absent. The problem set is public regulation text. This is a
non-goal rather than a control, and the control that keeps it one is that the
scoreboard runs in public CI, where client data could not go. Should a later
version consult a desk about a real engagement, the question sent must carry the
fact pattern and never the identity: no names, no TINs, no account numbers.

## 8. Success Metrics

- **Wrongly absorbed → 0**, even at the cost of escalating more. This is the only
  metric with a target, and it is reported first.
- The four-way score is reported per model with a stated denominator, never as a
  single percentage.
- Every escalation carries a reason from the closed set; the proportion that are
  `authority_permits_choice` rises over time as the fixable ones get fixed.
- The shared-layer purity test passes with the accounting desk installed.
- A factory-built desk passes the same record tests as a hand-built one, with no
  separate path.
- **v2's metric, recorded now:** the number of changes the second desk forces on
  the shared layer, and whether the firm had to touch a file to get it. Zero and
  no, respectively, means the mechanism generalised.

## 9. Milestones / Rollout

- **M1 (MVP)** — the engine as a library, the record shape with its gates, the
  problem set extracted from § 1.263(a)-3, and the three gating test seams green
  in CI. No model yet: the engine is provably correct before anything is asked to
  use it.
- **M2** — the desk wired to a model, scored end to end, both scoreboards
  committed with their denominators and their not-checked lists.
- **M3** — routing from a doer: one tool schema, `touches()` lookup, engine
  refusal naming the desk.
- **M4** — the factory: the interview, written *after* M1–M3, shaped by what
  building the fixed-assets desk by hand actually required. It emits a desk
  definition as a pull request and writes nothing directly.
- **v2 (out of scope here)** — the second desk, in a domain that is not
  accounting, produced by the factory. Two things are measured: the changes it
  forces on the shared layer, and whether the firm had to touch a file.

## 10. Risks & Open Questions

- **Risk — C8's own stated failure, and it is this design's exact trap:**
  *"'deterministic' can be claimed for a process whose inputs are judgements. An
  engine fed a date somebody guessed is only as deterministic as the guess."* The
  engine verifies citations; it cannot verify that the *fact pattern* handed to
  it was characterised correctly. **Mitigation:** the fact pattern is carried
  verbatim into the answer record, so a wrong answer traceable to a mis-stated
  question is visible as that rather than as a desk failure.
- **Risk — a desk starved of context becomes a rubber stamp.** C7 names it: *"a
  reviewer who cannot see enough to ask a question is a rubber stamp wearing the
  title."* **Mitigation:** the wrongly-absorbed count is exactly the measurement
  of this, which is why it is reported first.
- **Risk — the extraction PR is skimmed and a position rides along.** Mitigation:
  requirement 2, enforced by test, not by review discipline.
- **Risk — `Fires on` under-fires.** C9 already documents this about itself: the
  selector matches subjects, not shapes, so a question phrased without the
  subject word is not routed. Accepted; the fallback is that the doer asks
  directly (requirement 17).
- **Risk — the factory is written too early anyway.** The mitigation is a
  sequencing rule (§6.10), and sequencing rules are the kind that get skipped
  under time pressure. The check is concrete: M4 must not start before M1–M3 are
  green, and the factory's questions must be traceable to something the hand-built
  desk actually needed.
- ~~**Open question:** reading FASB's terms at their source.~~ **CLOSED
  4 September 2026** — the firm read the FAF License Agreement in an ordinary
  browser. It is stricter than assumed and produced the `human_only` access value
  (§6.3, §6.3a). The note below is kept because it records how the gap was
  actually closed.

  **How it closed, because the route matters.** The allow-list was added and was
  not enough: a re-test found `asc.fasb.org` reachable but its content pages
  returning a **Cloudflare 403 from FASB's own origin**, which no network setting
  can change. What closed it was a person — the firm opened the page in an
  ordinary browser and read the licence. That is `human_only` in action, arriving
  before the value existed to describe it.

  **What it changed:** the design had assumed a desk could read ASC live and cache
  nothing. The licence forbids the content reaching a model by any route, so ASC
  became `human_only` (§6.3) and a fourth access value now exists because of it.
  Confidence on the FASB position is **high**, read at source.

## 11. Done Criteria

- [ ] All requirements met (1–29, including 4a/4b, 11a/11b, 12a) and user stories 1–19 satisfied
- [ ] Three gating test seams green in CI, with a new `pytest (<plugin>)` matrix entry
- [ ] **Every assertion proved capable of failing** by mutation — no check that has only ever passed
- [ ] The problem set extracted from § 1.263(a)-3, each entry citing its paragraph
- [ ] Both scoreboards run and committed, with denominators and not-checked lists
- [ ] Wrongly-absorbed count reported first, and stated even when zero
- [ ] Shared-layer domain-blindness test passes with the accounting desk installed
- [ ] A refused answer appears in `unsupported/` with its reasoning, is not served to the caller, and is not scored correct
- [ ] An `unsupported/` entry has been promoted to a source and another to a position, both by PR
- [ ] The plugin installs from the `satc` marketplace into a repository that is not this one, and works there
- [ ] `canon/projects/REGISTER.md` gains a card — what it IS, never what its code currently does
- [ ] The factory emits a desk definition as a PR, and that desk passes the same record tests as the hand-built one
- [ ] The factory was written **after** the fixed-assets desk existed, and its questions trace to what that build needed
- [ ] `desk` declares `dependencies: ["canon"]`, and the session-start hook installs `desk@satc`
- [ ] The `[LOG]` items appended to `PLAN.md` and committed
