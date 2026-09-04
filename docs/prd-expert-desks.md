# PRD: Expert desks — a mechanism for building experts, and the first one

**Status:** Draft · **Owner:** the firm · **Last updated:** 2026-09-04

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
12. **[P0]** Every escalation carries a diagnosed reason from a closed set
    (§6.5), and whether that reason is fixable.
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

23. **[P0]** A test fails the build if accounting vocabulary appears anywhere in
    the shared layer.
24. **[P0]** The plugin reaches outside its own directory for nothing, matching
    canon's rule — it must lift out whole.

## 6. Implementation Decisions

### 6.1 Where it lives

A sibling plugin in the existing `satc` marketplace, beside `canon`. **The
marketplace is the umbrella, not the plugin.** `.claude-plugin/marketplace.json`
already takes a `plugins` array; this adds a second entry.

Canon must stay neutral. `CONVICTIONS.md` is *what the firm believes, in their
own words, challengeable*. An ASC or IRC citation is what an authority requires —
not theirs, not challengeable. Merging them would have Bassy challenging the firm
from FASB, which is precisely the failure its one rule exists to prevent.

**Name — needs the firm's pick.** Recommendation: **`desk`** (`satc/desk`). It is
the word already in use for the thing, it is plain rather than clever, and it
generalises without strain: the standards desk, the credit desk, the legal desk.
Alternatives considered: `counsel` (legal-sounding in a way that misleads),
`authority` (claims more than it does), `bench` (opaque).

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

- **FASB ASC** — the copyright notice forbids content being *"reproduced, stored
  in a retrieval system, or transmitted"* without written permission. A git
  repository is a retrieval system; so is a vector index and so is a local cache.
  **Citation only.** The distinction is *storage*, not reading: a desk may fetch
  ASC to answer and must not cache it.
- **Federal authority** — 17 U.S.C. § 105 places IRC, Treasury Regulations and
  IRS publications in the public domain. **Storable in full.** The narrow
  exception: § 105 bars the government from *originating* copyright, not from
  holding it by assignment, so a `.gov` URL is not self-certifying.
- **AICPA** — same posture as FASB.
- **A licence the firm holds may permit an internal copy.** That is a per-source
  fact, which is why `may_store` is a field and `license_check` is the default.
  Offline storage does not change the analysis; a licence might.

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
| `source_unreachable` | yes | grant the domain in the environment's network policy |
| `authority_absent` | yes | add it to the record, cited, via PR |
| `model_gave_up` | yes | shrink the problem (LOCAL-LLM-PATTERN rule 8) |
| `authority_permits_choice` | **no** | this is a position, and positions are the firm's |

Only `authority_permits_choice` should reach the firm twice. The others are work
items, and a desk that keeps emitting the same fixable reason is reporting a
defect in itself.

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

### 6.10 The seam into Occam

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

3. **The shared layer, as a purity check.** `pytest` asserting no accounting
   vocabulary appears in the shared layer. Prior art:
   `canon/tests/test_installed_elsewhere.py`, which copies the tree into a fresh
   git repository and runs it there — the same idea, that a thing claiming to be
   portable must be proven outside its home.

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
- **v2's metric, recorded now:** the number of changes the second desk forces on
  the shared layer. Zero means the mechanism generalised.

## 9. Milestones / Rollout

- **M1 (MVP)** — the engine as a library, the record shape with its gates, the
  problem set extracted from § 1.263(a)-3, and the three gating test seams green
  in CI. No model yet: the engine is provably correct before anything is asked to
  use it.
- **M2** — the desk wired to a model, scored end to end, both scoreboards
  committed with their denominators and their not-checked lists.
- **M3** — routing from a doer: one tool schema, `touches()` lookup, engine
  refusal naming the desk.
- **v2 (out of scope here)** — the second desk, in a domain that is not
  accounting.

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
- **Open question (needs your decision):** the plugin's name. Recommendation
  `desk`; see §6.1.
- **Open question (needs you, and only you):** the egress allowlist. Verified
  blocked by test this session: `asc.fasb.org` and `viewpoint.pwc.com` both
  return `EGRESS_BLOCKED`. Add `asc.fasb.org`, `*.fasb.org`, `viewpoint.pwc.com`
  and `*.aicpa-cima.com` at claude.ai/code → cloud icon → gear → Network access →
  Custom → Allowed domains, keeping *"also include defaults"* checked. Until then
  the FASB restriction language is sourced from a search index rather than read
  at its source, and `docs/research/accounting-authority-sources.md` says so.
  **This does not block v1** — ASC is a non-goal — but it blocks closing the
  research properly.

## 11. Done Criteria

- [ ] Requirements 1–24 met and user stories 1–14 satisfied
- [ ] Three gating test seams green in CI, with a new `pytest (<plugin>)` matrix entry
- [ ] **Every assertion proved capable of failing** by mutation — no check that has only ever passed
- [ ] The problem set extracted from § 1.263(a)-3, each entry citing its paragraph
- [ ] Both scoreboards run and committed, with denominators and not-checked lists
- [ ] Wrongly-absorbed count reported first, and stated even when zero
- [ ] Shared-layer purity test passes with the accounting desk installed
- [ ] The plugin installs from the `satc` marketplace into a repository that is not this one, and works there
- [ ] `canon/projects/REGISTER.md` gains a card — what it IS, never what its code currently does
- [ ] The three `[LOG]` items appended to `PLAN.md` and committed
