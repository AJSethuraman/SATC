# SATC — Defect Register

**Every known defect in this software that is not yet fixed, and every fix in
flight.** Started 3 September 2026 at the firm's instruction: *"always record
active fixes and bugs so you remember them and we can go over them together."*

## Why this is a third file and not one of the two that exist

- `docs/ERROR-LEDGER.md` records what the **agent** got wrong. A different
  question, and its answer — "reading the code caught nothing" — is the point of
  keeping it.
- `docs/SOFTWARE-TENETS.md` records what the **software** got wrong *after it was
  fixed*, as a lesson cited to a real bug.
- **This file is the part in between:** what is wrong *now*, what state the
  decision is in, and what proves it. An entry leaves here when it is fixed —
  and if it taught something general, it leaves a tenet behind.

**A defect is only listed here once it has been reproduced.** An unproven claim
belongs in a question to the firm, not in a register that reads as fact.

---

## Open — and this is the work queue, in order

Everything here is recoverable. The `satc_system` work that did not survive the
port is tagged **`parked/satc-system-pre-schema-port`** (= `055dcf3`, the tip of
PR #162 before it was closed). A tag rather than a branch, because branches get
deleted and a tag is how you say *keep this*. Recover any file with:

```
git show parked/satc-system-pre-schema-port:satc_system/src/satc/intake/chasing.py
```

| # | What | Costs | Needs |
|---|---|---|---|
| **S2** | **The chase panel** — "who owes us a document, longest wait first" — needs the bundle mechanism (`parts`, `is_bundle`, `outstanding`). Main did not rename it, it **deleted** it. Parked: `chasing.py` (171 lines), `test_chasing.py`, `test_bundle_stays_open.py` | the firm loses its morning list | **DECIDED 4 September: it stays open until every named part has arrived.** What is left is code — a `parts` column, a migration, and `chasing.py` back off the parked tag |

**S2 is the only thing left, and it is now code rather than a question.** S3,
S4 and S6 closed 4 September; S5 closed the same day when the firm settled the
ladder. S2's product decision came with them — a bundle request stays open
until every named part has arrived — so the `parts` column, the migration and
`chasing.py` off `parked/satc-system-pre-schema-port` are buildable without
asking anyone anything.

## Found by the WISP survey, 4 September 2026

Turned up while evidencing safeguards for `docs/WISP-DRAFT.md` (PR #187). Each
was read in source; the two marked **verified here** were re-checked
independently rather than taken from the survey.

| # | What | State |
|---|---|---|
| **W1** | `client-documents/web.py` started the browser front door with `debug=True`, and `make web` is that path. The Werkzeug interactive debugger offers a Python console on any traceback — arbitrary code execution, as whoever runs the app, to anything that can reach the port. Loopback-bound and PIN-gated, so never open to the network; still a debugger left on by default on the machine holding the client vault | **verified here. Fixed in this PR** — off unless `SATC_WEB_DEBUG=1` |
| **W2** | `satc.settings.ollama_host()` returned `$SATC_OLLAMA_HOST` unchecked, so an environment variable could point the document reader at a **remote** Ollama and send client documents to it — silently, because a working remote Ollama answers exactly like a local one. The Forge's standing rule keeps the *server* on `127.0.0.1`; nothing kept the *client* there | **Fixed 4 September.** Loopback only, and it **refuses** rather than falling back — a fallback would honour the safe behaviour while hiding that somebody asked for the unsafe one. Hostnames are refused too: a name that resolves to loopback today can resolve elsewhere tomorrow |
| **W3** | "Inference is local" is true *by default*, not absolutely: `ingest/readers/vision.py` can send document images to Anthropic behind two independent opt-ins (`settings.py:22-29`). Off today. If ever switched on, Anthropic becomes a §314.4(f) service provider | open — a decision, and a line in the WISP either way |
| **W4** | No login and no MFA on either local app (§314.4(c)(5)). The gate is physical access to the machine plus the Windows account | open — needs the firm's call on compensating controls **DECIDED 4 Sep 2026: no login is built.** The owner's reasoning, in his words: *"this is all local to here and you'd have to be literally on my lan"*. Written up as compensating controls in `docs/WISP-DRAFT.md` A4a, which still needs his signature as Qualified Individual — software describing controls is not the written approval the Rule asks for. |
| **W5** | **The firm has promised every client, in writing, that their records are destroyed — and nothing destroys them.** All four engagement letters carry it verbatim: *"We keep copies of your records and our work papers for **seven years**, after which they are destroyed"* (`satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:100`, and the same line in Bookkeeping :100, Business Return :120, C Corporation :107). There is a 90-day *prospect draft* purge and a manual `delete_client`; there is no seven-year anything. Secure disposal is **not** waived by the small-firm exemption | open — and it is a **published promise**, not an internal preference. The period was never the open question **DEFERRED 4 Sep 2026, deliberately.** Not "unknown" — the owner read the finding and chose to wait: *"one agent is working on a backup process so maybe you guys can kind of mirror"*. A disposal pass and a retention-aware backup are the same shape of problem (what is old enough to act on, prove it before acting), so building them twice from two directions is how they end up disagreeing about which copy is authoritative. Blocked on that work, not on a decision. |
| **W6** | `vault.key` still has no second copy, and sits beside the vault it opens. The backup deliberately excludes it — correctly — so today's verified backup restores a database nobody can read | open, and it is two minutes of the owner's time **4 Sep 2026: the obvious backup would not have worked.** Told to paste `vault.key` into a password manager the owner reported it *"looks corrupted, values cant be read at all"* — it was not corrupted, it is 296 bytes of DPAPI-wrapped binary doing its job. Worse, a byte-perfect copy is bound to one Windows account on one machine (`crypto.py:64-73`), so it would have failed on a replacement laptop: the one day it existed for. `scripts/vault_key.py --show` now exports the 32-byte key inside the wrapper as 44 characters, `--restore` rebuilds it elsewhere and refuses to overwrite, and a test carries a key to a second location and decrypts data written before the move. **Open until the owner has actually stored those characters — a tool is not a backup.** **CLOSED 4 Sep 2026 — the owner confirmed the key is in Bitwarden.** |

| **W7** | **The test suite drove the owner's desktop Outlook, and nobody noticed until he did.** `/comms/outlook` called `open_outlook_draft` unmocked (`comms_views.py:398`), which on a machine with pywin32 and classic Outlook does `Dispatch("Outlook.Application")` and `mail.Display(False)`. Five compose windows opened on his screen across two runs; four saved themselves into his Drafts. The firm: *"it opened once and i didnt know what was happening. then it opened again and i figured it out. i had to log in and stuff."* Nothing was sent — there is no `.Send()` and no `smtplib` anywhere in this codebase — and the windows, the drafts and the Deleted Items copies were cleaned up | **Fixed 4 Sep 2026.** `tests/conftest.py` forces `open_outlook_draft` to the unavailable branch for every test — the path every machine without pywin32 already takes. **This was also the cause of the split suite:** `outlook_available()` is True in `repos\SATC` and False in the other checkout, so the route took the COM branch in one and the mailto fallback in the other and the two disagreed on the same commit. Recorded as unknown for an hour before the firm's question about Outlook identified it. Verified by disabling the fixture (fails) and restoring it (passes). **The suite also went from 957s to 197s** — most of that sixteen minutes was blocking on COM |
epos\SATC` and passes in `Documents\Main\Claude\SATC_Prod_Software\SATC` — same commit `1c31330`, byte-identical `src/` and `configs/`, and both seed the demo store identically (2 requests for `SATC-001000`, neither self-employment). It fails in ISOLATION in one and passes in isolation in the other, so it is not test ordering. The two virtual environments hold different packages. **Which package, I did not establish** | open — pre-existing, not introduced today. It matters more than one test: it means a green suite here does not mean a green suite there, and the checkout that fails is the one holding the real client data |

| **W8** | **Two of the three ways an engagement ends are recorded; the third is recorded nowhere.** The letters end an engagement on delivery (`Deliverable.delivered_on`), on signature-plus-transmission (`Filing.transmitted_at` plus the signed 8879 as a `ReceivedDocument`), **or on written notice from either party — and nothing in the schema holds that date.** | `retention.engagement_ended` reads all three and returns `Undetermined` when none is on file, so the gap is visible rather than silently treated as "not ended yet". It bites hardest on **bookkeeping**, whose letter has no "concludes when" clause at all: written notice is its ONLY ending, so a bookkeeping engagement can never acquire a disposal date until this is built. Needs a date and a basis on `Engagement`, a store column and a migration — the `engagement_ref` and `parts` pattern | open |

**W1 and W2 are the same shape**: a default chosen for a developer's convenience
on a box that later took real client data. Neither was exposed to the network.
Both are the kind of thing that is free to fix now and expensive to explain later.

**What is NOT at risk:** `client-documents/`, `canon/`, `docs/` and
`satc-handoff/` had zero conflicts and shipped separately in PR #172.

All fourteen from the 3 September interview triage are closed — thirteen raised
by the review and F14 split out of F1 when its first fix turned out to be
partial.

## Closed — the client interview, raised 3 September 2026

Reproduced against the live interview engine and a running form on a temp store.
No client data was opened. The firm's decision form, with a recommendation and a
reason on every item:
**https://claude.ai/code/artifact/c5acade0-7e07-4881-8554-003377493ff7**

| # | Defect | Costs | State |
|---|---|---|---|

**Not one of the thirteen was covered by an existing test.** That is the number
worth remembering: the suite was 1,362 green and knew about none of it. It is
1,377 green now, and knows about three.

### Checked and found clean

Recorded because a survey that lists only what it found is not a survey.
`showIf` forward references (zero, audited programmatically against schema
order); dead `showIf`s (52 examined, 27 conditional, 0 dead); required-field
coverage against `registry/fields.yaml` (zero gaps); the back button's pruning
of now-invisible answers; `[CONFIRM: ]` refusal at merge; the TIN boundary
(denylisted in tests *and* refused on every draft write); draft-id path
traversal; the hard-no short-circuit; `MaterialsDeadline` correctly never asked;
and the live C-corp path.

---

## Fixed

### 4 September 2026 — the payment loop, proven with real money

| # | Proved | How |
|---|---|---|
| **P1** | A client can be given a link, pay it with a real card, and this software sees the money — on the LIVE Square account, not a sandbox | `python cli.py payments --check --production`, **7 of 7**. Link `square.link/u/Mtukztls`, order `T3yIEJw8D0j0CXjj8qwrERUF8cQZY`, $1.00 settled against location `LHW8CYHKQKH5A` (SAT-C LLP, ACTIVE, USD, `CREDIT_CARD_PROCESSING`) |

**The owner set this bar himself:** *"i can invoice myself for $1 and pay it with
a live card as our final test."* Every automated test in this repository runs
against a stand-in for the network — they prove the software behaves correctly
and cannot tell a working Square account from a closed one. This is the one
check that could not be written.

**THE ORDER READ `OPEN`, NOT `COMPLETED`, AND THAT IS WHY IT WORKED.**
`Settlement.paid` asks whether a TENDER exists — whether a card was actually
charged — and treats `COMPLETED` as sufficient but never necessary. Square's own
Checkout Complete panel reported, in one breath, *"Your test payment was
successful"*, *"Tender.id: Added to Order"*, and *"Order state: OPEN"*. Had the
code trusted the documented state, this settled invoice would have read unpaid
for ever, and `signing.may_file` would have gone on refusing to clear a return
whose bill was paid. A label can be renamed by the processor; money changing
hands cannot.

**And the owner confirmed the other end of it**, the same day: *"i got the
notification from square that i was paid $1 i trust it."* So the money left a
card, Square recorded it, this software read it, and Square told the firm it had
been paid. That is the whole loop, from two independent directions.

**The last inch is still not ours to see:** the transfer from Square's balance
into the firm's bank happens on Square's schedule, and no call from here reaches
it. Recorded as confirmed by the firm rather than measured here — which is the
honest description of it, and enough.

### 4 September 2026 — the ladder question, settled

| # | Defect | Closed by |
|---|---|---|
| **S5** | Two defensible reader ladders were argued and neither could ship while the other was open. A text-layer PDF our anchors miss: refuse to summon a model, or go on and name the parser gap? | **The firm chose to go on.** A text layer can be genuine rubbish, and refusing outright loses documents the later rungs do handle — so the ladder fails towards READING a document with the gap named, not towards refusing one. No code changed: `state.py:491` already did this. What changed is that it is now held in place |

**The skipped test was worse than no test.** `test_the_ladder_reaches_no_model_
while_a_deterministic_rung_can_still_read` had a docstring arguing the stricter
case and **no body** — it could not have failed if the ladder had done anything
at all. It is replaced by `test_a_readable_document_our_anchors_missed_still_
reaches_a_model` in `test_reader_ladder.py`, which asserts both halves: the
ladder reaches the model, AND the note still reads *"our anchors, not the
document"*.

Verified the way S15 asks for — the stricter rule was injected into
`state.py` and the suite re-run. **The new test failed, for the reason its name
gives, and the seven tests already in that file all passed**, because every one
of them disables OCR and vision and so says nothing about where the ladder
stops. Without it a revert to the stricter rule was a green merge.

### 4 September 2026 — the join the collector was waiting on

| # | Defect | Closed by |
|---|---|---|
| **S3** | **`engagement_ref`** — the join between what a client sees (`2026-0001`) and what the system keys on (`SATC-001000`) did not exist, so `collect` could file a document but never mark the request it satisfied. The firm's instruction, 31 Aug 2026: *"ADD THE FIELD"* | `Engagement.engagement_ref` (`satc/models/work.py`), a store column and migration (`satc/persistence/store.py`), and `SATCStore.client_for_ref` — a blank ref never matches, same rule as `rate_plan_key`. `collect()` takes an optional `store`, resolves a drop folder's ref, and calls the existing `reconcile_received` for any arrival good enough to trust (`Classification.may_close_a_request`). Ported from the pre-schema-port test onto `Engagement` rather than the now-gone `IntakeEngagement` — see `test_engagement_ref.py` |

**`cli.py`'s `collect` command already called `collect(..., store=store)`** —
wired ahead of the field it depended on, in the same port that deleted S2, so
the one path a person runs was silently broken (`TypeError`, unexpected
keyword). It also printed `a.awaiting`, `a.wrong_year_for` and `dr.aged` —
fields that were never built here; `awaiting`/`wrong_year_for` need S2's
bundle mechanism and a year-mismatch check that did not survive the port
either, and `dr.aged`'s retention reporting was never part of this ticket.
Trimmed back to what actually exists (`a.satisfied`) rather than adding
fields that would sit permanently unpopulated. Run for real end to end —
`satc collect --apply` against a seeded store — not just against the unit
tests: it filed the document, closed the request, and printing the closed
line matched what the code path used to be able to only claim.

### 4 September 2026 — a price edit that was silently ignored

| # | Defect | Closed by |
|---|---|---|
| **S6** | Filed as "an order-dependent test". It was a **money bug**: `catalogue._stamp` fingerprinted a config file as `(mtime_ns, size)`, so changing a rate from `450` to `495` — same length — inside one filesystem timestamp tick read as UNCHANGED, and the catalogue served the old rate | `_stamp` hashes the contents. These are hand-edited files of a few kilobytes read once per change; the heuristic it replaces was wrong precisely when the edit was a price |

**The presentation is the lesson.** It surfaced as
`test_changing_a_rate_takes_effect_without_a_restart` passing alone and failing
after a slower test shifted the timing. The obvious reading is "flaky test". The
true reading is the sentence already in that test: *"the owner would invoice at
the old rate."* A test whose failure depends on the clock is still reporting
something, and the something here was real.

The new test forces the collision with `os.utime` rather than racing for it, so
it fails for its own reason on any machine instead of when the clock obliges.

### 4 September 2026 — the page reaches the workpaper

| # | Defect | Closed by |
|---|---|---|
| **S4** | The page a value came off was READ and REPORTED and never reached the record: `SourceRef.page` was `None` on every staged field, so a workpaper citation read `Doc <id>` with no page | One argument. `state.py` did not pass `pages=result.pages` to `MapExtractor.extract` |

**Everything else was already built** — `ReadResult.pages` maps label to page,
`TextAnchorReader` anchors page by page *precisely so it can fill it*, and
`MapExtractor.extract` has always taken `pages=`. One call site did not pass it,
and that was enough to make the whole chain useless.

The cost of that gap is on the record: **$200,000 of wages lifted off page 7 of a
blank W-2 — an instructions page — was cited to the preparer identically to a
figure read off the form.** The page is the one fact that would have made those
two look different at review instead of in a measurement three weeks later.

`test_intake_carries_the_page_all_the_way_into_the_workpaper` was
`xfail(strict=True)` and **that is what caught it**: the moment the argument was
added the test XPASSed, and strict turned an XPASS into a failure. A plain skip
would have stayed quiet. Verified both ways — green with the argument, red
without it.

### 3 September 2026 — the interview stops accepting answers it cannot mean

| # | Defect | Closed by |
|---|---|---|
| **F2** | `Interview.answer` never checked a value against the question's `options`, though `coerce`'s docstring claimed it did. `federal_form="1041"` was stored, printed as the engagement letter's scope line, and classified as an *individual* engagement | `is_offered()` — one predicate now shared with `prefill_is_answerable`, which had the rule all along. The interview would refuse to *suggest* a value it would happily *store* |
| **F1** | A double-click wrote the answer onto the next question | Defanged: the stray post now hits F2's guard and is refused. The missing question id on the post is still worth carrying — reopened as **F14** rather than called done |
| **F3** | `tax_year` was free text. `99999`/`-5` made `deadlines.board()` raise and took the whole calendar down; `0` printed a return due `0001-04-17` at the top of the board with `unplaced` empty | `type: year` in the schema, `deadlines.plausible_year()` enforcing it, and `board()` degrading an impossible year to `unplaced` instead of raising |

**Two things this taught, both worth keeping:**

1. **A refusal must not repeat what was sent.** The first version of F2's error
   quoted the rejected value — helpful until somebody types their SSN into
   question one, at which point the error, the log and the JSON response all
   carry it. `test_an_unfinished_sitting_is_refused_before_it_reaches_disk`
   caught it. The message now names what *would* work.
2. **Order the refusals by which message helps most.** Once F2 landed, an SSN
   typed into question one got "that is not one of the options" instead of "the
   last four digits are enough". `tins.refuse` now runs first inside
   `Interview.answer`, which also gives the CLI door a check it never had.

### 3 September 2026 — a count is a number, and some counts cannot be zero

| # | Defect | Closed by |
|---|---|---|
| **F5** | `coerce` returned the raw string when `int()` failed and `pricing._count` read any unparseable string as absence — zero. `count_rentals` of `abc`, `2.7` or `-3` all billed identically to a correct `1`, because `form_when` bumps a sub-1 count to 1; `count_states` of `-5` produced no state line at all | `Interview.answer` refuses a non-integer answer to a `number` or `year` question. `_count`'s comment — "the interview coerces its own types, and a stray string means the count was never really asked" — was an assumption about the interview; it is now true |
| **F13** | `count_owners = 0` satisfied a required question and printed as `OwnerCount` on the business letter, because required-ness is `value in (None, "", [])` and 0 is none of those | An optional `min:` on the question, declared in the schema rather than special-cased, so the next count that cannot be zero says so itself |

**And the engine now coerces its own input.** `web.py` called `coerce` before
`answer` and `cli.py --set` did too, so every type rule held for the two callers
that remembered and for nobody else. `answer()` calls it itself now — `coerce`
is idempotent, so the doors may keep calling it. Same shape as F7, and the same
reason `intake.py`'s header gives: *"a control that lives in one front door is a
control the other silently skips."*

### 3 September 2026 — one answer, and one place that derives from it

| # | Defect | Closed by |
|---|---|---|
| **F4** | The letter's scope came from the `states` list, the fee from a separate `count_states`. Proven: one state named in the letter, $100 of extra state returns on the estimate beside it, reconciled only at close-out a season later | The counts are `derived: true` now — same mechanism `federal_schedules` already used — and `interview.counted()` reads them off the lists. A lone `"None"` counts as zero, because `localities`' help tells the preparer to type exactly that |
| **F7** | `intake.finish` did not derive `federal_schedules`; `Interview.answer` did it per keystroke and `missing_required` on a throwaway copy, so answers arriving any other way were priced without them | `iv.derive()` at the top of `intake.finish`. The workaround in `exercise.py:332` is deleted — it was the tell that this was known |

**Both fixes are the same seam.** F4 adds a second derived value, and it had to
land wherever the first one did — building that hole twice would have been
silly, so `derive()` is now the one place: `schedules.apply` plus the counts,
called by `Interview.answer`, by `missing_required`, and by `intake.finish`.

Note the direction, because `schedules.py` warns against the opposite:
deriving a *schedule* from a *count* is wrong, since a count can be blank while
the thing exists. Deriving a count from a *list* is safe — the list is the
enumeration, so its length is exact and cannot be blank-but-true.

### 3 September 2026 — a type nothing understood, a question nobody should see, and two shapes

| # | Defect | Closed by |
|---|---|---|
| **F6** | `type: integer` on two questions was a type no code in the repo handled — free-text box for a count, and invisible to the dead-condition sweep, which probes only `type: number` | Both changed to `number`, and `check_types()` now runs at every `load_schema()`. The whole class of typo is an error at load rather than a wrong input box nobody notices |
| **F8** | `extra_forms` had no `showIf`, so a 1120 was asked about home sales, HSAs, marketplace insurance and pre-59½ withdrawals | `showIf: federal_form == '1040'`. The sweep could never have found it — an unconditional question is filed under `always` and never examined |
| **F12** | `client_email` and `client_zip` were unvalidated, and a mistyped address fails silently: the signing invitation just never arrives | A `pattern` the question declares, with `pattern_says` carrying the human sentence — because a regex is not an error message |

**The test helpers had to learn the new shapes**, in two files, and that is worth
recording: `_plausible` returned `"x"` for anything textual, so every walk
stalled at the first question with a `pattern`. The fix tries stock values
against the pattern rather than mapping question ids, so the next question to
grow one does not silently stall every walk again.

### 3 September 2026 — the last four, and the register is empty

| # | Defect | Closed by |
|---|---|---|
| **F14** | `POST /interview/<sid>` carried no question id, so a resubmit applied to whatever question was current when it landed | A hidden `question` field, and a 409 when it names a question the sitting has moved past. Absent is still accepted — the JSON door predates it, and present-and-wrong is the case that matters |
| **F9** | The coverage test asserted `business-letter` for a 1120, which gets `ccorp-letter`, and passed only because it hand-wrote two answers a real 1120 sitting prunes | It drives a real sitting and takes the document from `OPENING_BY_RETURN`. A second test asserts every opening letter is covered, so `ccorp-letter` cannot go unchecked again |
| **F10** | Abandoned drafts kept a prospect's name, address and email in cleartext forever, in a folder that syncs to OneDrive | `purge_drafts()` at 90 days, the firm's number. Refusals and declines are kept deliberately; an undated draft is kept, because the failure mode of this rule is destroying a record |
| **F11** | The PRD described seven sections with red flags at six; the schema has ten with red flags second | The PRD is read back from the schema and says the schema wins, and `test_the_prd_names_the_sections_the_schema_actually_has` fails if a section is ever added silently |

**Two harnesses caught things the suite did not**, which is the whole argument
for keeping them:

- `capture.py` failed after F3. It walks to "the first `text` question with no
  claim", which used to be `tax_year` — giving that its own `type: year` moved
  the stop PAST `red_flags`, so the walk answered the hard-no question on its
  way by and photographed the review screen instead. 1,412 tests were green
  while this was broken. The hand-maintained walkthrough registry was the only
  thing that noticed (S9).
- `drive()` in `test_web.py` looped `while True` and spun forever on a missing
  answer instead of failing. It cost ten minutes of a run and looked like a
  hang. Bounded now, and it says which question it stuck on.

### The year window, and why it is not three

IRC 6511(a) caps a **refund** claim at three years from filing (or two from
payment, whichever is later) — so three is right for an amended return worth
filing. It is *not* the input rule: an **unfiled** return has no statute of
limitations, because 6501's assessment clock starts when a return is filed and
for a year nobody filed it never started. The firm does that work and the
interview asks "Any unfiled years?" because it does.

So `YEARS_BACK = 7` is a typo guard and `REFUND_YEARS = 3` sits beside it as the
separate fact, unenforced — past three the return may still be worth filing, it
just cannot produce a refund, which is the shape of a review flag rather than an
input refusal. Confirmed against irs.gov, 3 September 2026, at the firm's
instruction.
