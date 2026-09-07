# PRD: `canon` — the practice brain, and Count Bassy

**Status:** Draft · **Owner:** the firm · **Last updated:** 2026-09-03

> Produced by `/occam` → `grill-me` on 3 September 2026. Every decision below was
> answered by the firm during that interview; nothing here is inferred. The
> seed corpus this PRD depends on is already extracted and in the firm's hands
> (see §6.5) — it was pulled out of a container that gets wiped.

---

## 1. Problem

**Every lesson this operation has learned is trapped in the repo that learned
it.** `SATC/docs/SOFTWARE-TENETS.md` holds 35 tenets, each one cited to a real
bug — "a check must report its denominator", "prevent, do not detect", "a test
that builds its own fixture proves the code agrees with itself". Roughly 33 of
them are about building software and have nothing to do with tax. The
`.claude/skills/` pipeline — `grill-me → to-prd → to-issues` — is titled
"SATC Skills" and lives in one folder.

Start a new project tomorrow and you start from nothing. The credit-risk suite
already rediscovers the same lessons independently.

**And there is a second thing nowhere at all.** The firm holds convictions about
how the business behaves — *charge working students less because "i just don't
think it's right to fuck them over"; deterministic outcomes wherever possible;
controls in place; be able to trust the results.* These live in conversation and
in a container that gets wiped. Nothing records them, and nothing holds the firm
to them.

The firm, 3 September 2026: *"I work best with a whiteboard, and I need someone
to keep me in check."* Not a task tracker. Something that knows what they
committed to and says so when they drift.

**Why now.** The transcripts holding the firm's reasoning are perishable, the
firm has just been reminded that archiving a session loses everything not
written down, and a second machine (the Forge) has come online — so work is
about to happen in more than one place.

## 2. Solution

`canon` is a **Claude Code plugin**. Installed into any repository, it brings
two records and one behaviour.

The records are **tenets** (how to build — each carrying the incidents that
proved it, accumulating across projects) and **convictions** (what the firm
believes and why — captured in their own words). The behaviour is **Count
Bassy**, called **Bassy**: a role any session steps into, which challenges the
firm *from their own record and never from its own opinion* — "you committed to
X because Y; this is Z; has Y changed?"

Bassy also keeps a **project register**: a thin identity card per project — what
it is, what it's for, where it lives — so the firm can ask questions across the
whole portfolio. Never a copy of what any code does.

## 3. Goals & Non-Goals

**Goals**
- One install carries the standards into any repo, active rather than readable.
- A tenet arrives with its evidence, and gains more each time it bites again.
- Convictions are recorded verbatim, challenged when contradicted, and retired
  with a reason rather than deleted.
- The firm can ask general questions across every project they run.
- It works in a repo that has nothing to do with accounting.

**Non-Goals — explicitly excluded**
- **Not a task tracker.** No todos, sprints or status. Those live in the repo
  doing the work. Two lists that must agree will not (S6).
- **Not a second source of truth about any project.** It never mirrors what code
  currently does; that drifts on the next commit. Bassy reads a repo when it
  needs to know.
- **Never decides for the firm.** It challenges and stops. It does not pick the
  option, act on a conviction, or substitute its judgement.
- **No client data, ever** — no names, TINs or engagement contents, in any form,
  including inside a quoted conviction. `canon` is the most portable thing the
  firm owns, which makes it the worst home for anything that must stay put.
- **Not the skills pipeline (yet).** Porting `grill-me`/`to-prd`/`to-issues` is
  roadmap, not v1. They work where they are.

## 4. User Stories

1. As the firm, I want to install one plugin in a brand-new repo and have the
   tenets already in force, so a new project starts where the last one ended.
2. As the firm, I want to be told when a decision cuts against something I
   committed to, so I either change my mind on purpose or don't change it by
   accident.
3. As the firm, I want the challenge to quote me, so I recognise the commitment
   instead of arguing with a paraphrase.
4. As the firm, I want to retire a conviction with a reason and keep the old
   one visible, so I can see what I used to believe and never re-litigate it.
5. As the firm, I want two conflicting convictions surfaced rather than
   resolved, so the disagreement stays mine — and I want how I resolved it
   recorded, because that is the most revealing entry of the three.
6. As the firm, I want a tenet to show every project it has bitten in, so I can
   tell a real law from a local quirk by counting.
7. As the firm, I want to ask "which of my projects touch client money?" and get
   an answer, without `canon` holding a copy of any project's code.
8. As Bassy in any repo, I want the firm's standing behaviours loaded, so I
   report denominators, say what I did not check, and lead with what is wrong —
   without being told each session.
9. As the firm, I want convictions proposed for my confirmation rather than
   recorded silently, so the record stays something I will stand behind.

## 5. Requirements

1. **[P0]** A valid Claude Code plugin: `.claude-plugin/plugin.json` plus a
   `skills/` directory, installable into any repo — matching the shape already
   proven by `SATC/cowork-plugin/`.
2. **[P0]** `TENETS.md` — the ~35 rules carried over, each with an **evidence
   list**: one entry per incident, tagged with project, date and a citation
   (commit, quote, comment or test docstring). Same rule as today: *a rule with
   nothing under it does not belong in this file.*
3. **[P0]** `CONVICTIONS.md` — each entry carries the firm's own words, the
   reason, the date, where it applies (all / one venture / one project), and a
   state of `held` or `retired`. A retired entry keeps its text and gains a
   retirement date and reason. **Nothing is ever deleted.**
4. **[P0]** A `bassy` skill that challenges **only from the record**: names the
   conviction, quotes it, states what the current decision is, and asks whether
   the reason has changed. It never argues from its own preference and never
   resolves.
5. **[P0]** Convictions are captured by **propose-and-confirm**: Bassy drafts an
   entry quoting the firm and asks. Nothing enters the record without a yes.
6. **[P0]** On conflict — two convictions, or a conviction against a tenet —
   Bassy surfaces both and **refuses to resolve**. The firm's resolution is then
   offered as a new conviction recording the trade-off.
7. **[P0]** The record loads into context on session start in any repo where the
   plugin is enabled.
8. **[P0]** **Hard gates** fire deterministically at a small named set of
   moments regardless of whether anything was noticed: before a price changes,
   before a client-facing document is released, before a decision is recorded.
   Exact checks block; approximate ones advise — the rule the firm already set
   for the tenet linter.
9. **[P1]** `PROJECTS.md` — a register. One thin card per project, written on
   first run: name, purpose, stack, location, which convictions apply. **No
   code state, no file inventory, no status.**
10. **[P1]** `BEHAVIOURS.md` — the standing behaviours (from
    `SATC/docs/HOW-WE-WORK.md`), loaded every session: report the denominator,
    say what was not checked, findings before green, recommend rather than
    survey, never claim without opening, decisions as answerable questions.
11. **[P1]** A `canon-mine` skill: given a corpus, propose tenets and convictions
    for confirmation. Never writes to the record directly.
12. **[P2]** A running log in `canon` for roadmap and deferred items — the
    `[LOG]` target, since `SATC/PLAN.md` is not this repo's to write.

## 6. Implementation Decisions

**6.1 Shape.** A repo, `canon`, private, under the firm's GitHub account. It is
a plugin: manifest + `skills/` + the record as Markdown at the root. Markdown,
not a database — the record must be readable and diffable by a person, and its
history is the point.

**6.2 A tenet on disk.** Heading (rule), then an evidence list. Adding evidence
appends; it never rewrites. Tenets keep their existing `S<n>` identifiers so
every citation already in SATC still resolves.

**6.3 A conviction on disk.** Verbatim quote, reason, date, scope, state.
Retirement appends a dated reason and flips the state; the original text stays.

**6.4 Challenge contract.** Input: a decision in flight. Output: nothing, or a
named conviction with its quote, the apparent contradiction, and one question.
It never proposes the answer. This mirrors the boundary already drawn in
`satc_system/.../paystub_judgement.py`: *a contradiction is never handed to a
model, because a model will resolve it fluently and the finding is gone.*

**6.5 The seed corpus — already extracted, do not re-derive.**
- `the-firms-own-words.md` — 173 turns, 7,965 words, 21 Aug – 3 Sep.
- `decisions-in-their-words.md` — 44 decisions, **17 of them typed** rather than
  picked. A typed answer rejected the framing; those are the convictions.
- Both scanned: no credentials, no client data. One email, the firm's own.
- **Known gap:** transcripts from other containers (the Forge session, earlier
  archived sessions) are not in it.

**6.6 Voice.** Standing behaviour, not personality. The firm chose this
explicitly: a strong persona makes an agent perform certainty it does not have,
and "confidently wrong" is a failure this operation hit twice in one week.

## 7. Testing Decisions

- **Seam(s):** the record files, and the challenge function. A challenge is a
  pure function of `(the record, a decision)` → `(a named conviction | nothing)`
  and must be testable without a session.
- **What a good test proves:**
  - A decision that contradicts a held conviction produces a challenge naming
    **that** conviction. A decision that does not produces **silence** — a
    challenge that fires on everything is a nag, and S4 says a tool that
    overstates what is broken destroys belief in the part that is true.
  - A **retired** conviction never fires a challenge, and is still readable.
  - Two conflicting convictions produce **both**, and no resolution.
  - No entry is ever written without a confirmation step.
  - The record round-trips: parsed, re-serialised, byte-identical.
- **Mutation is required, not optional.** Break each guard and confirm a test
  goes red. A survivor is the finding. Watch specifically for the failure that
  bit twice in the source project: **a fixture that builds its own record proves
  the code agrees with itself.** Build fixtures the way the writer writes them.
- **Data handling:** `canon` never holds client PII. A test asserts that the
  committed record contains no email, phone, TIN-shaped string or credential —
  the same scan already run over the seed corpus, kept as a check.

## 8. Success Metrics

- **The one that matters:** Bassy catches the firm contradicting themselves once,
  for real, in normal work. Not a demo, not a fixture.
- A new empty repo, plugin installed, has the tenets in force with no further
  setup.
- Every tenet carries at least one piece of evidence. Count is reported, so a
  bare rule is visible.
- At least one tenet accumulates evidence from a **second** project — the first
  proof the thing compounds rather than just persists.

## 9. Milestones / Rollout

- **M1 (v1):** the record + the challenge + plugin wiring, seeded by one mining
  pass over the corpus and the existing tenets. **Nothing else.**
- **M2:** the project register, and the standing behaviours as a loaded file.
- **M3 (roadmap, `[LOG]`):** port the skills pipeline into `canon`; the deeper
  mining machinery; the new-project starter prompt.

## 10. Risks & Open Questions

- **Risk — it becomes the folder nobody reads.** The named failure mode. Guarded
  by requirement 8: deterministic gates mean a catch does not depend on anyone
  choosing to look.
- **Risk — a wrong challenge burns the mechanism.** One misquote and the firm
  learns to click through. Guarded by verbatim capture and propose-and-confirm.
- **Risk — the register drifts into a mirror.** Guarded by requirement 9's
  explicit exclusions; worth a test that fails if a card grows code state.
- **Risk — the corpus is incomplete** (§6.5). Not fixable; state it rather than
  let a future reader assume completeness.
- **Open question (needs the firm):** confirm `canon` is a private repo under
  their GitHub account.
- **Open question (needs the firm):** who builds it. This session is off the
  SATC repo and `canon` does not exist; the Forge session or a fresh one does
  the work.

## 11. Done Criteria

- [ ] Plugin installs into a repo that is not SATC, and the record loads.
- [ ] `TENETS.md` carries every tenet, each with at least one evidence entry.
- [ ] `CONVICTIONS.md` seeded from the corpus, **every entry confirmed by the
      firm** — none inferred.
- [ ] A contradicting decision produces a challenge naming the right conviction;
      a non-contradicting one produces silence.
- [ ] Retire a conviction: it stops firing, stays readable, carries its reason.
- [ ] Two conflicting convictions surface both and resolve neither.
- [ ] Mutation table reported; every guard has a test that goes red when broken,
      and any survivor is reported rather than dropped.
- [ ] The no-PII check runs over the committed record and passes.
- [ ] **Verified by running it, not by tests:** installed in a real repo, used
      in real work, and it catches one real contradiction.
