# SATC design principles — the ideal state

**This is the anti-drift document. Read it before building; update it when a
decision changes it. It is the one place that says what "right" looks like.**

Every principle below was earned by a real decision on real code, and almost all
of them are enforced by a test rather than by intention. That is the point: a
principle nothing checks is a preference, and preferences drift.

Companions, each with a different job: `LOCAL-LLM-PATTERN.md` is the doctrine for
anything touching the local model. `satc_system/ARCHITECTURE.md` says *which
layer* a change belongs in. This says *what the change has to be true of*.

---

## 1 · Never invent a value

A merge field, a deadline, a state deadline, a taxpayer figure — if the practice
holds no fact for it, the system says so **visibly**. It never guesses, and it
never silently blanks.

> `[[ Fee: fill in ]]` — not an empty line, not a plausible default.

*Enforced:* `RenderedDraft.unfilled`; `build_context` OMITS keys rather than
blanking them; `test_comms.py::test_an_unknown_value_is_marked_not_guessed`.

## 2 · Facts are recorded, never inferred

Every fact about a client carries **how we know it** — `agency_notice`,
`stated_by_client`, `prior_filing`, `observed_document`, `assumed_default`.

The tempting inferences are the wrong ones. Whether an employer files a 941 or a
944 is *assigned by the IRS in writing*; it is not derivable from what they filed
last year. A duty built on an unsourced fact is flagged `is_assumed` — a guess
wearing a deadline — and says so in the queue.

Corollary: **an explicit "no" is not the same as an unanswered question.**

*Enforced:* `ProfileFact.basis`; `ObligationInstance.from_assumed_facts`;
`test_obligations_profile.py`.

## 3 · Computed, never stored

A due date is a *rule* landed on a calendar, never a constant. "March 15" is true
until the year it is a Sunday. `configs/obligations/*.yaml` contains **no dates
at all** — every date in it would be wrong in some year.

*Enforced:* `obligations/due_dates.py`; `test_obligations_calendar.py` asserts a
deadline may only ever move later and always lands on a business day.

## 4 · Law and firm policy never look alike

Statute is computed from a cited rule and cannot be argued with. A firm cutoff is
a preference the owner changes over coffee. They live in **different folders**,
load through **different functions**, and anything derived from policy is flagged
so the UI can render it differently.

The statutory loader *refuses* an uncited rule. The policy loader requires no
citation at all — because nothing in it has an authority behind it.

*Enforced:* `configs/obligations/` vs `configs/firm_policy.yaml`;
`documents_due_is_firm_policy`.

## 5 · Refuse rather than default

The most dangerous thing this system can do is answer confidently. A state with
no sourced rules **raises**; it does not fall back to the federal calendar. A tax
parameter with no citation **fails to load**; it does not become folklore.

> `No obligation rules on file for jurisdiction 'OH'. SATC will not fall back to
> the federal calendar — a state deadline guessed from the federal one is a
> confident wrong answer. Add configs/obligations/oh.yaml with cited rules.`

*Enforced:* `rules_for_jurisdiction`; `load_rules` rejects a sourceless rule.

## 6 · The model proposes; the engine disposes

The model never computes a number that matters and never writes state directly.
It chooses *what to do next*; code decides *whether that's allowed*.

And the actor is **derived from context, never accepted as an argument**. Nothing
can *claim* to be the owner — it can only *be* in a live browser request. A
script, a sweep, an API tool or a model rung gets a system actor and is refused,
including from paths that do not exist yet.

*Enforced:* `models/actor.py`; `acting_actor()`; `test_actor_gate.py`, mutation-
tested both ways.

## 7 · Provenance is sticky and transitive

A model taint follows the **value**, not the reader that last touched it.
Deterministic post-processing cannot launder model output clean. Defining "is
this model output?" on the reader is how a model-corrected string reaches the
gate looking deterministic.

Only a human hand-correction clears it — because a human read the document and
decided.

*Enforced:* `Provenance.derive`; the round-trip test through SQLite, because this
invariant once died silently at the database boundary.

## 8 · Idempotent by construction

Re-running anything is safe and cheap. "Already exists as requested" is
**success**, never a conflict. Ids derive from what a thing *is*, never from when
it was generated — content hashes for documents, `{taxpayer, kind, form,
jurisdiction, period_key}` for obligations, subject-derived ids for actions.

Consequence: a half-finished run is inert, and a dismissed item stays dismissed.

*Enforced:* `merge()`; `StagingGate.add`; `content_document_id`.

## 9 · Propose, never dispose

Nothing sends, signs, files, or transmits. The system reduces a decision to one
click; it does not remove the decision. Sending stays a human act, so the value
has to come from making the click cheap — the draft already written, the evidence
already gathered, the timing already noticed.

*Enforced:* no SMTP anywhere (an ast-parsing test proves it); the action queue
writes nothing; a model-classified arrival cannot close a client request.

## 10 · Errors name the right next step

A refusal that only says "no" ends a run — on a small model, and on a tired
human at 9pm in March. Every refusal names what would have been right.

*Enforced:* `require_human`; `ConfigError` messages name the file to create.

## 11 · Only masked identifiers leave the machine

Full TINs live in the encrypted vault and nowhere else. Artifacts, logs,
workbooks and exports carry masked values only. **Client filenames count as
PII** — they routinely contain the client's name, which is why document ids are
content hashes and the readable name never leaves the local UI.

*Enforced:* `test_comms.py` scans every rendered draft for a TIN pattern; a test
asserts no filename can reach the exported `citation` column.

## 12 · A check that has never failed is not evidence

Invariants get **mutation-tested**: break the rule on purpose, confirm the suite
catches it, restore. Seven false-passing checks on the sister project is where
this came from.

Also: the suite must actually render what it claims to cover. A route nothing
walks is a route that will 500 in front of the owner.

*Enforced:* the mutation runs recorded in commit messages; `test_app_routes.py`.

## 13 · A queue that becomes noise is worse than no queue

Two rows never say the same thing. Every entry carries its evidence in one line,
in the owner's language, auditable without opening anything. An item the owner
learns to scroll past has negative value — it trains them to ignore the one that
mattered.

*Enforced:* `test_actions.py::test_the_queue_does_not_say_chase_them_twice`;
every action asserts a non-empty `why`.

## 14 · Drake stays the system of record

SATC never recomputes tax and never e-files. It prepares, reconciles, chases, and
remembers. Where a number comes from Drake, SATC records the number Drake
produced and the fact that the owner keyed it — it does not derive a competing
one.

---

## Keeping this current

**When a decision here changes, this file changes in the same commit.** Not
afterwards, and not in a commit message alone — a principle that lives only in
git history is one the next session will not read.

Three questions for anything new:

1. **Which principle does it rest on?** If none, either it needs a new one, or
   it does not belong.
2. **Which principle does it strain?** Say so out loud and decide deliberately.
   Silent exceptions are how a codebase drifts while every individual commit
   looks reasonable.
3. **What test makes it stick?** A principle nothing checks is a preference.

Bloat has a specific smell here: a field nobody writes, a status nobody sets, a
config knob with one caller, a "future-proof" table with no producer. The
research pass produced a whole list of these and they were cut before they
shipped — see `docs/research/tax-practice/04-critique.md` §c. Cut them again.
