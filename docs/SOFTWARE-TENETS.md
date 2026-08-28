# SATC — Software Tenets

**Mined 27 August 2026 from the whole history of this software** — the commit messages that record
what broke, the firm's own critiques, the code comments that say what was tried and rejected, and
the test docstrings that name a real failure. Read before building anything here, and before
claiming anything here works.

Every tenet carries its evidence: a commit, the firm verbatim, a comment, or a test docstring. A
rule with nothing under it does not belong in this file. The test each had to pass: *if this rule
had been in force, would that bug have shipped?*

Cite as **S1**, **S17**. Governs `client-documents/`, `satc_system/`, `invoice-generator/`,
`cowork-plugin/` and anything new. This is the SOFTWARE counterpart to
`satc-handoff/00-START-HERE/DOCUMENT-TENETS.md`, which governs the words; where a tenet touches
wording it defers there rather than restating. **`docs/pipeline-map.md` §5** lists eight pipeline
invariants — cited below as `PM-1`…`PM-8`, generalised rather than duplicated.

---

## 0 · The shape of nearly every bug in this project

One shape accounts for the overwhelming majority: **something reported success without having done
the work.** Twenty-odd separate incidents reduce to it:

| What said it was fine | What was actually true |
|---|---|
| `doctor` reported a document "Ready now" (`a883ac1`) | `render` refused the same document |
| `test_confirm_placeholder_cannot_reach_a_client` passed (`a107e69`) | It poked a retired field; it asserted nothing |
| The suite was green (`test_scenarios_agreement.py`) | `cli.py check` exited 1 on nearly every real client |
| `test_every_entity_type_produces_a_pack[1120]` was green | Its fixture supplied an answer the interview never collects |
| The business-letter tests passed (`tests/test_coverage.py`) | Every real entity sitting refused to render its letter |
| "29 scenarios, 190 documents, 0 surprises" (`31837a8`) | Every document opened as unstyled plain text |
| "0 disagreements" (`31837a8`) | Almost nothing had been compared |
| A ladder audit "reported zero problems" (`c4369c6`) | "because it compared nothing" |
| A fee estimate rendered clean under "Total estimate $785" (`183afc2`) | The services table had no rows |
| The build was green (`239a4bd`) | The PII guards `CLAUDE.md` promises ran in no CI job |
| An invoice read `Paid` forever (`invoicer-review` #1) | The ACH debit had bounced four days earlier |

**The thesis holds. The mechanism is the half worth acting on.** In every case the verifier looked
at a **proxy** rather than the thing: a token instead of a page, a fixture instead of a client, a
file's existence instead of its contents. And the commonest way a proxy goes wrong is **drift** —
two places holding one decision, one of them updated. Part 1 is proxies; Part 2 is drift; they are
one failure from two ends.

The firm's standing instruction, 22 August, which most of this file implements:

> "requires a GUI and such, every process requires a human to be able to do it and automation to be
> able to replicate and follow similar controls"

---

# Part 1 — Do not report success you have not verified

## S1 · "Produced" must never mean "wrote bytes." Nothing is produced until it has been opened by the thing that consumes it.

`exercise.py` drove 29 clients end to end and reported **"190 documents, 0 refusals, 0 surprises."**
It was published as proof the software worked. The firm opened one:

> "these html files are plain text?"

Every template links `satc-doc.css` and `doc-page.js` by relative path, and the pack carried
neither. From `exercise.py`'s own new comment: *"I had read the same files as strings, extracted the
words, and called it proof."* The harness now opens every document in a real browser and checks the
two things that fail together — the `doc-page` element upgraded, and the type is the firm's rather
than the browser's default serif.

**Operational form:** if an artifact has a rendered form, the run that claims it works must open
one. Reading it as a string is a different claim.

## S2 · A check must report its denominator. A green result from a check that examined nothing is worse than a red one.

Twice, independently:

> "The harness reported '0 disagreements' while comparing almost nothing …
> `consistency.render_package` needs a record with the firm's own fields folded in, and without it
> most documents refuse to render, so `report` compared the one or two that survived and declared
> agreement." — `af5fc4e`

> "the helper that repriced a client on another rung built a one-rung ladder, so `includes:` could
> not resolve … **It reported zero problems because it compared nothing.**" — `c4369c6`

> "The pre-send gate ran on nine checks and printed `ok` on all nine. Two of them — the compliance
> floor and the pointer test — can only run against a manifest, and `package` wrote the manifest
> AFTER the gate. So on every real send, both refused with 'no MANIFEST.json … Not a pass', neither
> blocked, and the summary said `ok`. They were green in every test, on fixtures that wrote their
> own manifest, and had examined **zero** on every pack ever sent." — 27 August 2026

**Operational form:** every check prints how many things it compared, and the caller asserts a
floor. `test_scenarios_agreement` does exactly this: `assert len(checks) >= 5`.

**The corollary the third case adds: a check that reads an input must run after that input exists,
and the denominator is the only thing that will tell you it did not.** No assertion of the form
"the gate passed" can distinguish a check that ran clean from a check that never ran — that is the
same sentence in both worlds. The number is the difference. `presend.Counted` carries it, and a
check with nothing to look at prints `NONE`, never `ok`.

**And the count must come from the check, not from beside it.** `presend` builds its census and
then walks it, so what it reports is what it put its eyes on. A `len()` computed separately from
the loop is S3 waiting to happen: the two agree until somebody adds a `continue`.

## S3 · Two halves of one tool must make the same call — and the way to guarantee it is for one to BE the other.

`doctor --engagement` reported the organizer letter **"Ready now"** while `render` refused it:
doctor's readiness check omitted the required-lists guard render applies (`a883ac1`). The reason it
matters, from `cli.py`'s own comment: *"two halves of one tool disagreeing"* — **whichever you ran
was the one you believed.** Doctor now makes the identical call, and a test holds every document to
it.

Same class, opposite direction: `cli.opening_package()` was a literal list while `packaging.PACKS`
keyed on `_return_type`, so `render` and `package` *"each was right about the half the other got
wrong"* (`tests/test_scenarios.py`).

## S4 · A tool that overstates what is broken destroys belief in the part that is true.

> "A readiness tool that overstates what is broken teaches whoever reads it to stop believing the
> parts that are true, and this one is the first thing anybody runs." — `fac6cea`

`doctor` reported `hard_no` as blocking every render while real packs rendered two commands earlier;
`hard_no` is policy and no template merges it. Doctor now splits **blocks a render** from **needs a
decision**, and `settings.POLICY_ONLY` is guarded by a test that nothing in it is a field a template
merges.

Same at CI level: on the sixth identical failure email the firm wrote *"This is getting annoying
what is it"* (`524fe90`), and the message itself was unactionable — **"Missing []"** for an orphan
on the other side. A check firing on every push is either fixed or documented as deliberately red,
where the next person looks (`0edb465`).

## S5 · A confident wrong number is the worst output available. Refuse rather than compute on a value you cannot type-check.

> "None of them raised. Each produced a confident, wrong number, which is the worst failure
> available here — **a total nobody questions is a total that gets sent.**" — `0a190ce`

Three in one commit: `line_items` guarded the base fee with `if form:` and priced the per-unit lines
regardless, so a record missing its federal form produced an estimate for **the add-ons alone** —
three K-1s, a confident total, no return in it. `int(True)` is 1, so a yes/no wired to a count
billed for one. `int(2.7)` is 2, and nobody has 2.7 K-1s, so rounding hid that the answer was wrong
rather than imprecise.

Still open, named 27 August: **`intake.finish` type-checks nothing** — a string passed to a question
typed as a list printed *"Also included: no"* on a client's estimate. *"The front doors coerce; the
back door does not"* (`af5fc4e`). Absence stays forgiving; only a value that **looks** countable and
is not is refused.

---

# Part 2 — One decision lives in one place

## S6 · Two lists that must agree will not. Derive one from the other, or make them one list.

The masthead, the footer's partnership sentence and the "on behalf of" line were typed
**byte-identically into all ten templates and the skeleton**, while `firm-settings.yaml`'s
`legal_name` was dead config whose own comment admitted the footers *"need correcting; nothing in
the build catches them"* (`8e1fab3`). The firm:

> "software needs to be made to be robust and scalable"

The guard is a property, not an example:
`test_the_firm_block_reaches_every_document_from_settings_alone` **moves the firm to Cleveland in
settings and asserts all ten documents follow, with nothing of the old address left behind.** `PM-5`
generalised.

## S7 · A map keyed on another system's vocabulary must be tested against that system's actual values.

> "The question prefilled from the website through a map whose keys had drifted from the intake
> form: it expected `rental`, `self_employed`, `sole_prop`, `brokerage` and `itemize`, and **the
> site has never sent any of the five. Five of seven keys could never fire.**" — `9e924e2`

The fix was not to correct the copy but to delete it: the question uses the website's own option
values, *"so there is no vocabulary to keep in step"*, plus a test holding the two files together —
which immediately found the next gap. Same shape in `524fe90`.

## S8 · A hand-written sample drifts, and it is the first thing anybody looks at. Generate it from the engine and pin it.

> "the sample record's estimate was HAND-WRITTEN and had drifted to $450 for a 1040, $185 for a
> state and $95 for a local — none of them prices this firm charges … **A sample that contradicts
> the engine is worse than no sample.**" — `2a41777`, after the firm said: *"this doesn't appear to
> have our package data."*

`satc-docs sample` rebuilds it from the demo answers, pinned by a test that *"earned its keep within
the hour"* (`0ac7f7a`). Another hand-written sample listed five onboarding items where the answers
call for nine — *"the three it dropped are the ones that cost something"* (`b815cd2`).

## S9 · Anything maintained by hand beside something generated needs a check that reads it back.

- A comment in `fee-schedule.yaml` said *"`beyond` accepts only `hourly`"* while `brokerage_keying`
  had used `beyond: priced` for days (`6643ac5`).
- The ten FIELDS specs *"went stale the moment this landed"*, and **all ten stated totals were
  wrong, by one to three** (`8e1fab3`).
- Three samples said `arjun@satcllp.com` while settings said `arjun_sethuraman@satcllp.com` — on the
  three documents that print it as the way to reach us. The drift test had covered only the Firm
  block (`5faa4c7`).

`registry/fields.yaml` is the model: generated from the templates and reconciled **in both
directions** — a template gaining a field fails the build, and so does a registry entry claiming a
template that no longer uses it.

## S10 · Wording is data. No sentence may be assembled in code, and no test may pin the firm's prose.

Seventeen pieces of client-facing English lived in f-strings in `pricing.py`; `4231873` moved them
to `phrases:` in the fee schedule. Two guards make that safe rather than merely possible: `_SLOTS`
records what each phrase may fill, and a test **renders every phrase and fails by name if one loses
a slot or gains one nobody supplies**. Implements `DOCUMENT-TENETS.md` **T28**; the test half is
**S24**.

---

# Part 3 — Absence, refusal, and the half-done change

## S11 · Absence leaves no token. Any check that scans for markers is blind to a block that rendered to nothing.

**This failed four separate times**, which is why it is a tenet and not a bug:

1. `[[EACH Assumptions]]` *"collapsed to nothing without the render so much as warning about it"* —
   `pricing.price()`'s own docstring.
2. A fee estimate rendered a blank services table under **"Total estimate $785"** — every field
   resolved, no `[CONFIRM]` surviving, **and the render reported success** (`183afc2`).
3. `RequestList`: *"Every onboarding letter this project has rendered promised that list and
   delivered none"* — on a document in every signing pack (`00f51fc`).
4. `WorkStatus` on the disengagement letter, the document with the most legal exposure in the set,
   rendering as a heading with no rows above *"Anything not marked complete above is not filed"*
   (`0164763`).

The fix is worth copying: an empty list is sometimes a real document, so the registry does not
forbid emptiness — **it forbids the silence.** A list is `required: true` with a reason, or carries
`may_be_empty` saying what makes it safe. **Operationally:** whenever a guard works by finding a
marker, ask what it sees when the thing is simply not there.

## S12 · A refusal writes nothing — and says what is still on disk.

`PM-8`. `intake.finish` prices **before the store is touched**; `cmd_package` renders to a temporary
directory and touches the output only once every document has succeeded, *"because the client signs
what arrived."* Both refinements came from testing the refusal path (`1899974`):

- A refused run printed "No pack written" and **left a complete pack for a DIFFERENT engagement
  sitting there looking current.** It now names that engagement and says not to send it — and does
  not delete it, since it might be the only copy.
- A successful run **merged instead of replacing**, leaving two engagement letters in one folder. A
  pack now owns its directory; a folder holding anything that is not our own `MANIFEST.json` is
  somebody's, and is refused.

## S13 · Finish the retirement. A change is not done until nothing else still points at the thing you removed.

Retiring one field, `ReturnInstruction`, took **three templates, three FIELDS docs, three samples,
the field registry and firm settings** (`a107e69`) — and revealed the guard test that had gone on
passing while checking nothing. A sentence fixed in the onboarding letter in round two was never
swept into the extension notice, *"where it had been live ever since"*, found only by diffing
(`4b752b4`).

**Operationally:** grep the name and the phrase across templates, FIELDS docs, samples, registries
and tests; then re-render. See `DOCUMENT-TENETS.md` **T26/T27**.

## S14 · Unreachable code is unchecked code. If nobody could exercise a path, assume it is wrong.

Prefills were displayed and then discarded, so every value had to be retyped. Making Enter accept
was one line:

> "That one-line change turned **three latent bugs into live ones, because a claim nobody could
> accept was a claim nobody had checked.**" — `d693bb2`

The three: `client_city` and `client_state` both read `contact.location`, so accepting both would
print *"Solon, OH, Solon, OH 44139"* on a letter; the schedules question was offered the website's
vocabulary, none of which is a schedule code; and `states` — the engagement's scope boundary, where
*"a state omitted is a state we did not agree to file"* — was prefilled from the complexity
checklist.

`PM-1` and `PM-2` as an engineering rule: a gate that can never hold, a question nothing consumes, a
price no line reads. Build the check that finds them — `cli.py ladder` does, for prices — rather
than trusting a dead branch is harmless.

---

# Part 4 — Testing and controls

The firm asked for this part by name. Two statements govern it:

> "every process requires a human to be able to do it and automation to be able to replicate and
> follow similar controls" — 22 August

> "when i say scenario test i mean literally it tries everything, and not just smoke tests or
> whatever. like you try and produce it all as you go and debug it … it's **integral everything
> works and can be demonstrated**." — 27 August

## S15 · A test must be able to fail for the reason its name gives. Break the join on purpose and watch it go red.

> "Every check has a test that breaks its join on purpose — **a check nothing can fail is
> decoration.**" — `f1bbe82`

Prove the red before the green: *"Both tests were red on the real templates before the registry
changed"* (`0164763`); *"It went red on the real file before the file was removed"* (`6643ac5`).
Counter-example `9f6ff48`: a check named *"not stuck on a disabled Sending button"* that only looked
for the word "Thank you" — a tripped honeypot could have left a dead disabled button behind and
passed.

**Minimum for a test to be worth having:** it names a real failure; it fails when that failure is
reintroduced; it reports which record and which field; someone has seen it red.

## S16 · A test that reads an artifact as a string proves the bytes. It cannot prove the artifact renders. Something must open it.

> "NOTHING CAUGHT IT because every other test reads the HTML as a STRING and asserts on its tokens.
> **That is the right way to test a merge and it is blind to whether the result renders at all.**" —
> `tests/test_packaging.py`, written the day the firm found the plain-text packs

Three more invisible in the source and obvious on the page: an estimate printing **"The standard
deduction"** and **"Itemized deductions"** one after the other (`a107e69`); officer compensation on
an individual's estimate — *"Caught by reading a re-rendered 1040 fee estimate, not by a test"*
(`0ac7f7a`); and `<strong>` at weight 600 navy against `<b>` at 700 body ink, so **two visibly
different bolds sat in one paragraph of a client's letter**, measured in a browser (`8dc1f40`).
Otherwise the firm finds them by using the software, which is the expensive way: *"i cannot seem to
select options for some stuff - like the rental per property question"* (25 Aug).

## S17 · A fixture that answers a question the software never asks is a test passing for the wrong reason.

> "`test_packaging.test_every_entity_type_produces_a_pack[1120]` is green, because its fixture hands
> the 1120 a `k1_target` **the interview would never have collected.**" — `tests/test_scenarios.py`

Hidden behind that green: a C corporation could not be sent an engagement letter at all. *"Not
'prints something wrong' — refuses, on an unresolved `<<ScheduleK1Target>>`"* (`e49e65e`). The
older, larger version of the same thing:

> "the templates were proven against `samples/business-engagement.json`, which hand-writes all four
> — **a payload the real pipeline could never produce**" — `tests/test_coverage.py`, on the whole
> entity half of the letter set refusing while the suite passed

**Operationally:** build fixtures by running the real front door, not by writing the dict.
`tests/test_scenarios.py` keeps two skeletons *"both COMPLETE: every required question is answered,
so a scenario that leaves one out is leaving it out on purpose"* — and removes an answer explicitly,
commented `# the interview would not ask`.

## S18 · One fixture is a case, not a suite. A check exercised against a single record is a check tested on the case it cannot fail.

> "So the checks were green on the sample and **crying wolf on nearly every real engagement** … The
> suite was green throughout, because the one record it checked — the demo package — is a
> Self-Employed client whose scope happens to name a Schedule C." —
> `tests/test_scenarios_agreement.py`

`cli.py check` exited 1 on the itemising couple, the landlord, the K-1 client, the brokerage client
— every ordinary Standard engagement. Likewise *"Nothing caught it because every end-to-end test in
the suite drove a 1040"* (`test_scenarios.py`). **Operationally:** parameterise over the shapes an
ordinary week produces, and cover each boundary from **both sides** — `exercise.py` runs 3 rentals
against 4 and 4 foreign accounts against 5, which is how the soft cap was shown to *say* it was a
cap rather than merely to be one (`31837a8`).

## S19 · Assert the property over the whole space, not the example.

The tests that have held up are properties:

- `set_amount(path, its_current_amount)` leaves the file **byte-identical**, over all 24 prices —
  *"a writer that cannot rewrite a value as itself is reformatting something on every save, and in
  this file what it reformats is a comment"* (`715b53a`).
- `to_html(to_text(x)) == x` for **every block in all ten templates** (`8dc1f40`) — which failed on
  its first run and found the mixed-bold bug.
- `supersedes:` written *"as a property over every package, so a fifth one cannot arrive with the
  bug in it"* (`a107e69`).
- Every tier gate, `per_form` entry and `when:` checked against the question the interview actually
  asks and the option it actually offers — `PM-1`.

## S20 · A guarantee a test checks holds until somebody edits a price on a Friday. Put the guarantee in the engine.

> "A guarantee a test checks holds until somebody edits a price on a Friday; **a guarantee the
> engine makes is one the client gets.**" — `472cc0b`, moving the cheapest-package rule out of a
> watching test and into `derive_tier`

Same move, larger: `5b0b58a` took four gates out of `cli._finish` — *"a control that lives in one
front door is a control the other silently skips"* — into `intake.finish`, where creating an
engagement happens **and nowhere else**, with a test that reads `cli._finish`'s source and fails if
a gate reappears there.

## S21 · Know what a control is. A test runs on a fixture before the work; a control runs on the real work, in flight.

| Control | Runs on | Answers |
|---|---|---|
| `cli.py doctor [--engagement REF]` | a real engagement | what blocks a real render, and separately what needs a decision (`fac6cea`) |
| `cli.py check` / `consistency.report` | the rendered documents of a real package | do the seven joins hold |
| `cli.py ladder` | the live fee schedule | is any package never chosen; is each a discount on its parts (`472cc0b`, `8c9138f`) |
| `firm.open_decisions()` / `blocks_render()` | `firm-settings.yaml` | which `[CONFIRM:]` would actually stop a document |
| `published prices match the fee schedule` (CI) | the live site config against the registry | has the public page drifted from what we charge |
| **end-of-cycle reconciliation — NOT BUILT** | filed returns against our answers | *"our interview and such is system of record until proven wrong … this should be a control we build at the end of the cycle"* (firm, 26 Aug; `PLAN.md`) |

`check` earned its place on live output the day after it was written — a package promising the first
deliverable on **March 20** while telling the client to send papers by **March 25**: *"The date was
mine; the catch was the software's"* (`af5fc4e`).

**A control must:** run on real records, not fixtures; be runnable by a person on demand and by a
script; name the record and the field; distinguish *blocks the work* from *needs a decision*; and
report how much it looked at (**S2**).

## S22 · CI holds what must never regress. A harness produces what must be looked at. They are not substitutes.

> "The 748 tests assert PROPERTIES … **They produce nothing anybody looks at and never touch the
> commands a preparer actually types.** … It asserts nothing on purpose. A refusal is not a failure
> — several are correct, and the report says which. **Reading it is the work**, because the bug
> class here is software saying something is fine when it is not." — `31837a8` and `exercise.py`

Four rules follow, each from a real failure:

1. **CI must actually run the suites.** `CLAUDE.md` promised the build fails if legal names or full
   TINs leak; those guards existed and **nothing ran them** — the only job was `pytest
   (satc_system)`, so the merge engine, field registry and money formatter were *"covered by tests
   that executed nowhere except a developer's machine"* (`239a4bd`).
2. **A green suite that does not gate the deploy is decoration.** *"Render watches the branch
   independently of CI … A red suite ships anyway. Going from 7 tests to 43 only helps if something
   reads the result"* (`docs/invoicer-review.md`) — its highest-value recommendation, and a
   configuration edit.
3. **Test on the engine production uses.** That suite runs on SQLite while production is Postgres,
   *"so the class of failure most likely to take the site down at boot is exactly the class CI
   cannot see."*
4. **A harness writes outside the repository.** The first `exercise.py` run wrote a hundred rendered
   client letters into the repo root's `out/`, which is not gitignored — *"one `git add -A` from
   committing client documents"* (`31837a8`). Every fixture here is invented; `leads.xlsx` is read
   by nothing.

---

# Part 5 — What not to do

## S23 · Do not delete or weaken a guard because it fired. Read it first.

The clearest single mistake in the history, made twice in one day:

> "The test kept flaking today whenever it ran beside a render, and **I twice put the stray
> `tmp*.html` down to test litter and deleted it. It was not litter.** The guard was tripping over
> the thing it guards against, which is the guard working and me not listening." — `6880bc4`

A fully rendered onboarding letter — real name, real street address — had been sitting in the
tracked template library for the length of every PDF render.

## S24 · Do not pin the firm's prose, a price, or any figure a person is allowed to change.

> "A test asserted the words 'this estimate assumes' — the phrase the firm deleted. It now checks
> the shape of the assembled sentence instead: **a test that pins current wording fails when the
> firm rewords something, which teaches whoever hits it to edit the test rather than think.**" —
> `8a2562f`

Also: two merge tests asserting on `$450` and on a line the old sample happened to carry, made
data-driven (`2a41777`); and two pinning *"The signed engagement letter"* by name — *"the rule
stayed and the example moved — and the first now checks three rows instead of one, so a single
removal cannot hollow it out again"* (`4b752b4`).

## S25 · Do not write a test that goes green when the project succeeds. Invert it, re-aim it, or move the example.

Three real instances, three different right answers:

- **Invert.** `test_business_letter_renders_now_that_the_confirm_is_answered` once asserted the
  letter *could not* reach a client. *"Its own docstring said it would go green the moment a human
  resolved it … so it is inverted rather than deleted. A `[CONFIRM:` coming BACK to this template is
  now the failure."*
- **Re-aim.** A fee round-trip test covered only the still-open prices; *"the firm priced itself on
  26 August 2026, so the open set emptied and **the test asserted nothing about anything**"*
  (`tests/test_fees.py`). It now covers *changing* a price.
- **Move the example, keep the property.** Three tests encoded "a C corporation gets the business
  letter" — the assumption the firm then corrected. *"The property each guards survives, only the
  expected letter changed"* (`03fe484`).

## S26 · Do not verify the same thing twice, and do not test a mechanism through whichever live line happens to use it.

> "Every branch in this repo is a PR branch, so `push: branches: ['**']` beside `pull_request:` ran
> three jobs twice on each commit — six where three were wanted, across seventy-odd branches. **That
> is what drained the Actions allowance and produced the `startup_failure` on PR #154, which read
> from the notification email like a broken test and was not one.**" — `c2394d7`

And when a live line stops exercising a mechanism, move the test rather than protecting the line:
*"`beyond: priced` is now used by nothing real. The mechanism stays and is tested against a fixture
rather than against whichever line happens to use it"* (`5faa4c7`).

## S27 · Report what you did not find, plainly. A clean result is a finding, not a failure to produce work.

> "Categories where I found nothing. **Stated plainly rather than padded.**" —
> `docs/invoicer-review.md`, which names authorization, webhook idempotency, CSRF, XSS, password
> storage and PDF generation as clean, each with what was probed

Ten of sixteen findings were fixed; six were left alone with a proposed approach and no code change.
Same instinct on the tenet sweep of eleven templates: *"They came back CLEAN, and that is the
finding rather than a disappointment … **So I did not manufacture edits to show work**"*
(`be20b41`). Every finding in that review was reproduced against a running instance first — a
finding you have not reproduced is a guess, and a guess in a report is **S1** in a hat.

## S28 · Do not call something delivered because its tests pass. Walk the whole path a person walks, front to back, and open what comes out the end.

> "A tenet to our software and procedural creation should be doing this process
> front to back or I can't trust it'll work without debugging it myself." — the firm, 28 August 2026

**Four of the ten documents could not be produced by any command a preparer can run** — the delivery
letter, the organizer cover, the extension notice and the disengagement letter. Each needs a fact
that does not exist when the engagement is created, and nothing collected it. Nothing was failing:
the templates were there, the merge engine was green, and `doctor` *"reported the organizer letter
blocked on every engagement in the store, correctly, and there was no way to unblock it"* — so
**the opening pack was a third of the process and the other two thirds had no front door**
(`registry/lifecycle.yaml`, `cli.cmd_event`). Found by opening 303 rendered documents, which is the
firm's own way of finding it and the expensive one.

**What a deliverable is, then:** the core, plus the command a person types **and** the browser route
where one exists (**S3**), plus its step in the generated `docs/OPERATING-PROCEDURES.md`, plus the
artifact opened in what the client opens (**S1**). A module only a test can reach is not built yet;
it is a debugging session the firm has not had yet.

---

# The pre-flight check

Run before saying anything works. Close to mechanical; step 6 is the one that was missing on 27
August.

1. **Name the claim.** "The pipeline runs" is not a claim; "a 1065 sitting produces a signable pack"
   is.
2. **Run the suite and read the count.** `cd client-documents && python -m pytest -q`. A number that
   did not move after new work means nothing new is covered.
3. **Prove the new guard red.** Reintroduce the failure it names. If you cannot make it fail, it is
   decoration (**S15**).
4. **Drive the real front door** — the command or the screen a person uses, not a function call.
   Both front doors if both exist (**S3**).
5. **Check the denominator.** How many records, documents, joins were actually compared? Print it;
   compare it to how many there should be (**S2**).
6. **OPEN THE ARTIFACT** in whatever the recipient opens. Stylesheet present, layout intact, no
   `<<Field>>`, no `[[BLOCK]]`, no `[CONFIRM:`, no empty list under a confident heading (**S1, S11,
   S16**).
7. **Run it on more than one shape** — the boundary from both sides, and at least one client that is
   not the demo record (**S18**).
8. **Run the controls on real work.** `doctor`, then `check`. Read what they say rather than their
   exit codes (**S21**).
9. **Grep for what you retired** — field name and phrase, across templates, FIELDS docs, samples,
   registries and tests. Re-render (**S13**).
10. **Check where the output went.** Anything rendered from a real record is outside the repository
    or inside a gitignored directory. `git status` before `git add` (**S22.4**).
11. **State what you did not check**, in the commit message, in those words (**S27**).

---

# How this software developed, and what changed

**Phase 1 — eyeball and adversary (June – 14 August, `website/`).** No build step, no engine;
verification was reading the page and running an adversarial pass over it (`f7554da`, *"fix the 52
defects adversarial validation confirmed"*). Tests existed and asserted less than their names
claimed (`9f6ff48`). The assumption: **if a person looked at it, it is right.**

**Phase 2 — the engine, and refusal as a feature (20 – 22 August).** `d4eff7a` built the registry,
interview schema and merge engine, with the decision that has held since: **`merge.render` raises
rather than returning a document with a hole in it.** Then two structural corrections — `5b0b58a`
moved four gates out of the CLI into `intake.finish` the moment a second front door existed (*"That
was invisible while the terminal was the only way in"*), and `239a4bd` discovered CI was running one
project's suite of three. Learned: **the software must refuse, and the refusal must live where every
caller passes it.**

**Phase 3 — decisions out of code (25 August).** Prices, gates, phrases and request wording moved
into `registry/*.yaml` (`4231873`, `00f51fc`); the cheapest-package rule moved from a watching test
into the engine (`472cc0b`); the ladder gained reports that listen for *silence* — a package never
chosen, a package dearer than its parts (`c4369c6`, `8c9138f`). Two problems were **pinned rather
than fixed**, because the fix was a price and prices are the firm's. Learned: **put the guarantee in
the mechanism, and give a person one place to change a number.**

**Phase 4 — read the rendered page (26 August).** The pivot. Bugs stopped being found in the record
and started being found in the document: officer compensation on an individual's estimate
(`0ac7f7a`), two deduction methods on one estimate (`a107e69`), an onboarding letter that had
*always* asked for nothing (`00f51fc`). Samples became generated rather than hand-written
(`2a41777`, `bbd1930`), and `consistency.py` arrived to answer *"show me how you can tell it all
goes together."* Learned: **guards read the rendered text, and two documents that are each right can
still contradict each other** (`PM-7`).

**Phase 5 — whole clients, then produced output (26 – 27 August).** `tests/test_scenarios.py` drove
whole clients through the real registries and found what unit tests structurally could not: the two
package lists, the C-corporation refusal, the 1120 fixture passing for the wrong reason.
`tests/test_scenarios_agreement.py` ran `check` over nine client shapes and found it had been crying
wolf on nearly all of them. Then `exercise.py` stopped asserting and started **producing** — 29
clients, 190 documents on disk — because the firm asked for something that *"can be demonstrated."*
And that produced the last lesson, when the firm opened one of the 190.

**The arc in one line:** *does the code do what I think* → *do the parts agree* → *do the documents
agree* → **does the thing the client actually opens work.** Each phase's verification was correct,
and each was blind to the next phase's failure. The present position — CI for properties, controls
for real work, a harness for produced output, a browser check on the artifact — is the first with
nothing obviously behind it. The next blind spot is at the seam this software does not yet cross:
**what was filed.** That is the reconciliation control in `PLAN.md`, and until it exists *"until
proven wrong"* has no mechanism behind its second half.

---

# Day one on the next project

So these hold by construction rather than by discipline:

1. **One core, front doors on top** — every gate in the core, plus a test that reads a front door's
   source and fails if a decision reappears there (**S20**).
2. **A registry for anything a person may change** — prices, wording, gates — with a reader-back
   test in both directions (**S9, S10**).
3. **The refusal path before the success path**, atomic, tested first (**S12**).
4. **A `doctor` on day one** — split into *blocks the work* and *needs a decision*, on real records
   (**S4, S21**).
5. **A scenario harness writing real output to a gitignored directory**, before the second feature
   rather than after the tenth (**S22**).
6. **One rendering test from the beginning** — headless browser, PDF text extractor, workbook
   reader, whatever opens the artifact. The single check whose absence cost the most (**S1, S16**).
7. **CI that runs every project's suite, gates the deploy, and uses production's engine** (**S22**).
8. **Fixtures built by running the real front door**, and a test that fails if a fixture answers
   something the software never asks (**S17**).
9. **`.gitignore` the output directory in the first commit**; no test ever reads a real record
   (**S22.4**, `CLAUDE.md`).
10. **A `docs/` note of what is deliberately not checked**, so the next person inherits the blind
    spot as a known one (**S27**).
