# `canon` — the issue set

Thirteen vertical slices, dependency order. **Parent for all:** `docs/prd-canon.md`.

Slices **1–9 are v1**. 10, 12, 13 are M2. Label every unblocked, fully-specified
slice `ready-for-agent`.

> **Why this is a file and not a tracker.** The session that wrote it could not
> create the repo — GitHub access was scoped to one repository and
> `POST /user/repos` returned 403. The repo does not exist yet and was not
> created. Everything below is ready to publish the moment it does.

## Day one, before issue 1

Create `canon` (private), and commit these three, which already exist and must
not be re-derived:

- `docs/prd-canon.md` — the spec
- `corpus/the-firms-own-words.md` — 173 turns, 7,965 words, 21 Aug – 3 Sep 2026
- `corpus/decisions-in-their-words.md` — 44 decisions, 17 of them **typed**
  rather than picked

Both corpus files were scanned: no credentials, no client data, one email and it
is the firm's own. **Known gap, state it rather than let a reader assume
completeness:** transcripts from other containers — the Forge session, earlier
archived sessions — are not in them.

---

## 1 · Tracer bullet: a plugin that challenges

**Parent:** `docs/prd-canon.md` §5 r1, r4, r7 · stories 1, 2, 3

**What to build:** A Claude Code plugin that installs into a repository which is
not SATC, carrying exactly **one** tenet with **one** evidence entry and
**one** conviction. Plus a `bassy` skill that reads that record and challenges
from it — naming the conviction, quoting it, stating the apparent contradiction,
and asking whether the reason has changed. It never proposes the answer.

One of everything, deliberately. This proves plugin wiring, record parsing,
challenge and silence work together before any bulk work exists to hide behind.

**Acceptance criteria:**
- [ ] Installs into a repo with no relationship to SATC; the record loads
- [ ] A decision contradicting the one conviction produces a challenge naming it
      and quoting the firm's own words
- [ ] A decision contradicting nothing produces **silence** — silence is a
      tested behaviour, not an absence
- [ ] The challenge never proposes a resolution
- [ ] The record round-trips: parsed, re-serialised, byte-identical
- [ ] Mutation table reported. **Build the fixture the way the writer writes it**
      — a fixture that builds its own record proves only that the code agrees
      with itself, which is the failure that survived mutation twice in the
      source project

**Blocked by:** None — can start immediately.

---

## 2 · Nothing enters the record without a yes

**Parent:** §5 r5 · story 9

**What to build:** Capture by propose-and-confirm. Bassy drafts a conviction
**quoting the firm verbatim**, with the reason and the date, and asks. A draft
that is not confirmed is not recorded.

A conviction paraphrased is one the firm will disown the moment it is quoted
back at them, and a challenge built on a misquote burns the mechanism.

**Acceptance criteria:**
- [ ] A drafted conviction not confirmed does not appear in the record
- [ ] A confirmed one carries the firm's words verbatim, the reason, the date
      and its scope
- [ ] The confirm step shows the exact text that will be stored
- [ ] Mutation table reported; a mutant that writes without confirming dies

**Blocked by:** 1

---

## 3 · Retire, never delete

**Parent:** §5 r3 · story 4

**What to build:** A conviction can be retired: it gains a retirement date and
reason, stops firing challenges, and stays readable. The original text is never
removed.

The challenge *is* the review — retirement happens at the moment one bites, not
on a schedule. Keeping the retired text is what stops the same thing being
re-litigated in a year.

**Acceptance criteria:**
- [ ] A retired conviction never produces a challenge
- [ ] Its original text, reason and date remain readable
- [ ] The retirement reason and date are recorded
- [ ] Mutation table reported; a mutant that deletes rather than retires dies

**Blocked by:** 1

---

## 4 · A conflict is a finding, not a problem to solve

**Parent:** §5 r6 · story 5

**What to build:** When two convictions collide — or a conviction fights a tenet
— Bassy surfaces **both** and resolves **neither**. The firm's resolution is then
offered as a **new** conviction recording the trade-off.

The same boundary already drawn in `satc_system`'s paystub judgement: a
contradiction handed to a model gets resolved fluently and the finding is gone.

**Acceptance criteria:**
- [ ] Both sides are named and quoted
- [ ] No resolution is proposed, ranked or implied
- [ ] The firm's resolution is offered as a new conviction and not written
      without confirmation
- [ ] Mutation table reported; a mutant that picks a side dies

**Blocked by:** 1

---

## 5 · Hard gates at named moments

**Parent:** §5 r8

**What to build:** Deterministic firing at a small, named set of moments —
before a price changes, before a client-facing document is released, before a
decision is recorded — regardless of whether anything was noticed.

The firm's own recorded conviction: *"I want outcomes to be deterministic
whenever possible."* Same shape as the tenet linter already built in SATC: exact
checks block, approximate ones advise, and one is promoted only after a full
cycle with no false positive.

**Acceptance criteria:**
- [ ] Each named moment fires without depending on anything being noticed
- [ ] Blocking versus advisory is explicit per gate, and a new gate starts
      advisory
- [ ] A gate that examined nothing says so — it never reads as a pass
- [ ] Mutation table reported

**Blocked by:** 1

---

## 6 · Evidence accumulates

**Parent:** §5 r2 · story 6

**What to build:** A tenet holds a list of evidence entries — project, date,
citation. Adding evidence **appends**; it never rewrites. The count is reported
so a tenet with nothing under it is visible.

This is what makes canon compound rather than merely persist: the third time a
rule bites in a third project, it carries three citations and is visibly a law
rather than a local quirk.

**Acceptance criteria:**
- [ ] Adding evidence appends and leaves prior entries byte-identical
- [ ] Every entry carries project, date and citation
- [ ] The evidence count is reported per tenet; a bare rule is visible as bare
- [ ] Mutation table reported; a mutant that overwrites prior evidence dies

**Blocked by:** 1

---

## 7 · Nothing sensitive can enter the record

**Parent:** §3 non-goals · §7 data handling

**What to build:** A check over the committed record for anything that must
never be there: email addresses, phone numbers, TIN-shaped strings, credentials.
It reports its denominator — what it scanned, not just what it found.

**Lands before slices 8 and 9 deliberately.** A guard that arrives after the
bulk import is guarding something that is already inside.

**Acceptance criteria:**
- [ ] Runs over the whole record and reports what it examined
- [ ] Fails on a planted email, phone, TIN-shape and credential
- [ ] Passes on the existing corpus, which was already scanned clean
- [ ] Runs in CI, not only on demand
- [ ] Mutation table reported

**Blocked by:** 1

---

## 8 · Bring the 35 tenets across

**Parent:** §5 r2 · story 1

**What to build:** Migrate every tenet from `SATC/docs/SOFTWARE-TENETS.md` with
its evidence, **preserving the `S<n>` identifiers** so every citation already
written across SATC still resolves.

A straight copy, not a re-mining — they are already curated, and re-deriving
them would lose the curation. Roughly 33 of the 35 are universal; the two or
three that are SATC-specific get scoped rather than dropped.

**Acceptance criteria:**
- [ ] Every tenet present, `S<n>` ids unchanged
- [ ] Every tenet carries at least one evidence entry; the count is reported
- [ ] Tenets that are not universal are scoped, not deleted
- [ ] The no-PII check passes over the result

**Blocked by:** 6, 7

---

## 9 · Mine the corpus, propose the convictions

**Parent:** §5 r11 · §6.5 · story 9

**What to build:** A `canon-mine` skill that reads the seed corpus and
**proposes** convictions for confirmation, one at a time. It never writes to the
record directly.

Start with the **17 typed answers** in `decisions-in-their-words.md`. A picked
answer accepted a framing; a typed one rejected it, and that is what a
conviction is. Then the 173 turns.

**Acceptance criteria:**
- [ ] Every proposal quotes the firm verbatim with its date
- [ ] Nothing is written without confirmation — the mining path uses slice 2 and
      does not bypass it
- [ ] The run reports its denominator: how much of the corpus was examined
- [ ] The no-PII check passes over the result
- [ ] Mutation table reported; a mutant that writes directly dies

**Blocked by:** 2, 7

---

## 10 · The standing behaviours

**Parent:** §5 r10 · §6.6 · story 8

**What to build:** The thirteen practices from `SATC/docs/HOW-WE-WORK.md`, loaded
every session in every repo: report the denominator, say what was **not**
checked, findings before green, recommend rather than survey, never claim
something works without opening it, hand decisions over as answerable questions.

Voice is standing behaviour, not personality — chosen deliberately, because a
strong persona makes an agent perform certainty it does not have.

**Acceptance criteria:**
- [ ] Loaded in any repo where the plugin is enabled, without being asked for
- [ ] Each behaviour is stated so it can be checked, not merely admired
- [ ] Carries the incident behind it, same rule as a tenet

**Blocked by:** 1

---

## 11 · *(absorbed into 13)*

The project register is not a separate slice: adopting a repo **is** how that
repo gets its identity card. See 13.

---

## 12 · The running log

**Parent:** §5 r12 · §9 M3

**What to build:** A running log in `canon` for roadmap and deferred items, and
the M3 roadmap recorded in it: port the skills pipeline into canon, the deeper
mining machinery, the new-project starter prompt.

`SATC/PLAN.md` is not this repo's to write, so the roadmap needs a home here or
it dies in a conversation.

**Acceptance criteria:**
- [ ] The log exists with the M3 items recorded and dated
- [ ] Later stages append to it rather than starting new files

**Blocked by:** 1

---

## 13 · Adopt a repo — the post-mortem

**Parent:** §5 r9 · story 7 · *added by the firm at the slicing gate*

**What to build:** Point Bassy at a repository that **predates canon** and let it
do a post-mortem: read the commit history, the docs and the tests, and propose
candidate tenets **with real evidence pulled from that repo** — plus write the
project's identity card for the register.

The card is thin by design: what the project is, what it is for, its stack,
where it lives, which convictions apply. **Never what the code currently does** —
that drifts on the next commit. Bassy reads a repo when it needs to know.

The real test is one of the nine credit-risk repos: no tenets, never mined,
nothing hand-prepared. Adopting SATC would prove nothing, because SATC's tenets
were already written.

**Acceptance criteria:**
- [ ] Runs against a repo it has never seen and produces candidate tenets, each
      citing something real in that repo
- [ ] Proposes; never writes to the record without confirmation
- [ ] Writes an identity card carrying no code state, no file inventory, no
      status — **with a test that fails if a card grows any of them**
- [ ] Reports its denominator: what it read, and what it could not
- [ ] Says plainly what it did **not** examine
- [ ] Proven on a repo with no prior tenets, not on SATC

**Blocked by:** 6, 9
