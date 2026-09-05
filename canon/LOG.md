# canon — running log

**Append to this file. Never start a new one.** A roadmap that lives in a
conversation dies when the container is wiped; that has already happened once to
this operation, and the corpus in `corpus/` exists because somebody noticed in
time. Deferred work, decisions about this repo, and anything a later stage needs
to know goes here, newest at the bottom, dated.

`SATC/PLAN.md` is not this repository's to write. This is where canon's own
roadmap lives.

---


## 2026-09-03 · v1 built

Slices 1–9 of thirteen, in dependency order. The record parses and round-trips,
nothing enters it without an explicit yes, nothing is ever deleted, the challenge
fires and the silence holds, evidence accumulates, all 35 tenets have moved in,
and the corpus can be mined.

Bugs found by building it, kept here because the pattern matters more than the
fixes: a `re.DOTALL` attribution that swallowed half a record; a separator
doubled on every write, twice, in two different places; `all([])` reading an
unbilled engagement as paid; a mutant that survived because an early return
guarded nothing; a matching rule written twice and disagreeing with nothing
comparing them; and a corpus header claiming 7,965 words in a file whose next
sentence promised none of the agent's.

**The firm ratified the thirty-five tenets on 3 September 2026**, after reading
them: *"i was reviewing the tenets - i am agreed with them."*

---

## 2026-09-03 · M3 roadmap, recorded

Three things are deferred deliberately, not forgotten.

**Port the skills pipeline into canon.** `grill-me → to-prd → to-issues → build`
lives in `SATC/.claude/skills/` and is the spine for new work. It is not
SATC-specific and it does not belong to one repository. Blocked on nothing but
sequence; the reason to wait is that porting a pipeline before canon has been
installed anywhere else would be porting it to one repository twice.

**The deeper mining machinery.** `mine.py` reads two Markdown corpus files.
There is more history than that — commit messages, PR bodies, the run logs, the
transcripts still sitting in other containers — and the miner has no way in to
any of it. What v1 deliberately does not do: rank, cluster, or summarise. Those
are the operations that turn "surfaced a passage" into "decided a conviction",
and any of them arriving needs the certain/guessed split held just as firmly.

**The new-project starter prompt.** What a session reads on day one of a
repository that has just adopted canon: the tenets, the standing behaviours, the
convictions that apply, and the project's identity card. Blocked on slice 13,
which is what writes the card.

---

## 2026-09-03 · Known gaps, stated rather than left to be assumed

- **The corpus is incomplete.** Transcripts from other containers — the Forge
  session, earlier archived sessions — are not in it. Any denominator the miner
  reports is a denominator over what survived, not over what was said.
- **canon has been installed nowhere but SATC.** Slice 13 adopts a repository
  that predates it; until that has run against a real one, "installs into every
  project" is a design claim and not an observation.
- **One conviction is proposed and unanswered.** C3, the website lane, drafted
  from the firm's 30 August answer. It is not on the record and must not be
  written until they say so.
- **C1 has an earlier source than the quote it carries.** On 25 August the firm
  wrote *"i want a package for college students where i'm fine operating at a
  'loss'"* — five days before C1's recorded quote and considerably sharper. The
  record never rewrites a quotation, so this is either evidence to add or a
  second conviction. The firm decides which.

---

## 2026-09-03 · Slices 10, 12 and 13 — v1 is thirteen of thirteen

**10 · The standing behaviours.** `skills/how-we-work/` — thirteen, each with a
`**Do:**` that can be checked and an `**Incident:**` behind it. `tests/
test_behaviours.py` compares the file to its own claims: thirteen numbered
without a gap, every one carrying both halves, and an incident thin enough to be
a slogan fails. The file also says plainly what a broad skill description does
*not* guarantee — the harness is not promised to load it every session, and
claiming otherwise would assert something never observed.

**12 · This log.** It exists now.

**13 · Adoption, proven on a repo with no tenets.** `adopt.py` was run against
`credit-review-os`, which has never been mined and had nothing prepared. Three
real findings, all from running it rather than reading it:

- **The reading was thinner than it looked.** `stock-helper` reported one commit,
  honestly — and nineteen were reachable from other refs, because the project had
  arrived as a squashed merge. `Reading` now reports *read of reachable* and
  names the gap in what it did not examine.
- **The certain tier is not always a signal.** 14 of 17 `credit-review-os`
  commits changed a test alongside source, because the project was built
  test-first. That is its normal case, not a finding. A tool that flags
  four-fifths of everything has told the reader nothing (S4), so the report now
  says so above half and tells the reader to read the list as history.
- **An empty tier is information.** Its fix-word tier returned zero, because
  every commit subject there is slice-shaped rather than fix-shaped. That is a
  fact about how that team writes commits, not a clean bill of health.

The card guard caught the first real card on the first attempt: both register
entries named the documents that govern them, and both read better without.

`projects/REGISTER.md` holds two cards. **Seven of the nine analytics projects
and every practice-ops project are unadopted** — that is not a backlog item
hidden in a tracker, it is the visible state of the register.

**Still open, and none of it is mine to close:** C3 is proposed and unanswered;
C1's earlier and sharper source from 25 August is still neither evidence nor a
second conviction; and canon has been installed nowhere but SATC, so "installs
into every project" remains a design claim.

---

## 2026-09-04 · The three open items are closed

**C3 · declined.** The firm read the proposal and said it is not a conviction:
it was a call about that week's pull requests, not a standing belief. Nothing
was written to the record as a conviction — and the refusal itself is now kept.

That was not the original plan. Declining C3 exposed a gap: ids are never
reused, so C4 follows C2 and the hole at C3 is an invitation to fill it; and
the miner surfaces the same passage on every run, so the same proposal would
have come back every month. A thing that re-asks a question you have already
answered is a thing you learn to dismiss without reading — which is exactly the
nag failure the firm asked to be designed out. So `CONVICTIONS.md` now carries a
**Not convictions** section, the miner reads it, and a declined passage is
marked rather than re-proposed. It still appears in the count: quietening a
proposal must never quieten the denominator.

**C4 · recorded, 25 August 2026.** *"i want a package for college students where
i'm fine operating at a 'loss'"* — a different claim from C1. C1 is about not
charging a working student what the work is worth; C4 is a willingness to price
below cost on purpose, and it fires on the decisions a margin review makes.

**Installed elsewhere · proven.** `tests/test_installed_elsewhere.py` copies the
tree into a fresh git repository in a temporary directory, with no SATC parent
and no inherited path, and runs the record, the challenge, the guards, the
no-client-data check and the whole suite there as a subprocess. What it does
**not** prove, stated rather than implied: that a Claude Code harness elsewhere
loads the plugin. Nothing here reaches a harness.

### Four bugs, each found by doing the thing rather than reading about it

- **`adopt.py` named the project after the path it was handed**, not the git
  root. Installing into `host/vendor/canon` and adopting `..` produced a project
  called `vendor`. Nothing failed; the card would simply have carried the wrong
  name forever.
- **The confirmation retyped the entry instead of rendering it** — a second
  description of the same record in a second place with nothing comparing them
  (S31). It had already drifted: a quote ending in `a "loss"` displayed as
  `"…a "loss""`, because the display wrapped what the file does not. `ask()` is
  now the renderer, and a test parses what is shown back and compares it to the
  draft field by field.
- **`conflicts()` was a claim the code cannot make.** All it observes is that
  two convictions were selected; the report said flatly *"two things you believe
  are pulling against each other here."* The moment C4 joined C1 — which agree —
  that sentence was false. Renamed `both_bear_on`; the report says they may
  point the same way.
- **The round-trip test covered half the file.** The declined section was added
  and `test_the_committed_record_round_trips` kept passing on the convictions
  alone, which would have let every refusal be dropped on the next write with
  nothing noticing.

Two of the eight mutants in the closing pass survived the first attempt: the
malformed-declined-entry guard had never been handed a malformed entry, and the
portability test's own docstring tripped the absolute-path check it was written
to run. Both were the test's fault, not the code's.

**121 tests. 48 mutants planted across all passes, 48 killed.**

**What is still open**, and it is one thing: `projects/REGISTER.md` holds two
cards. Seven of the nine analytics projects and every practice-ops project are
unadopted.

---

## 2026-09-04 · Installed, for real, and it did not work the first time

The firm asked the obvious question — *"if I open a repo will it automatically
have canon?"* — and the honest answer at that moment was **no**. Four skills
existed under `canon/skills/`, and nothing anywhere loaded them: not
`.claude/skills/`, not an installed plugin. They were not loaded in the SATC
session that wrote them. The README's "installs itself into every project" had
never been anything but a design claim, exactly as this log said.

**What was missing was one file.** A plugin needs a marketplace to be installed
from. `SATC/.claude-plugin/marketplace.json` now lists canon, and that file
lives one level above `canon/` on purpose: the marketplace knows canon exists,
canon still reaches nothing above itself.

**And the manifest was invalid.** The first real install failed:
`author: expected object, received string`. `test_the_plugin_manifest_is_valid_
and_names_canon` had been green the whole time and had only ever checked that
the JSON parsed — a test whose *name* claimed validity while checking almost
nothing, which is the shape this repository exists to catch. There is a real
validator (`claude plugin validate`) and it now runs in the suite, alongside a
pure-Python schema check that runs even where the CLI is absent, so the test
never becomes a check that examined nothing.

**Then it was proven by doing it.** Installed at user scope; a session opened in
a temporary git repository with no relationship to SATC listed `canon:bassy`,
`canon:how-we-work`, `canon:canon-mine`, `canon:canon-adopt`; asked to challenge
a push straight to `main`, it found `CONVICTIONS.md`, quoted C2 verbatim, gave
the firm's own reason, asked whether it had changed, and proposed nothing.

Two things are now separated wherever they are claimed. **Available** is
enforced by the install. **Loaded without being asked** is a description
matching, which nothing guarantees — so every place that mentions it also names
the way to load the skill by hand.

123 tests.

---

## 2026-09-04 · Two things wrong with the install instruction

**The branch.** The instruction given to the firm was
`claude plugin marketplace add AJSethuraman/SATC`. Another session ran it,
looked at `main`, found no `marketplace.json` and nothing named canon, and
reported that canon does not exist. That session was right about everything it
could see: canon lives on a feature branch whose pull request is not merged.
The command needs the ref —
`claude plugin marketplace add AJSethuraman/SATC@claude/satc-handoff-batches-2-4-n2qrl9-b7-fee-estimate` —
until the branch lands, and the README now says so and says why.

**The record's address.** The first proof asked only whether it worked. It
worked: a session in an unrelated repo challenged a push to main by quoting C2
back. Asked *where it had read the record from*, it answered with a path to a
checkout that happens to exist on this machine — not the plugin's own copy. On
any machine without that checkout it would have found nothing.

Every skill that reads the record now names `${CLAUDE_PLUGIN_ROOT}` and says not
to read a copy it merely found: a working tree is a branch, a half-finished
edit, someone else's experiment. Re-proved after the fix, asking the same extra
question, and the answer is now
`/root/.claude/plugins/cache/satc/canon/1.0.0/CONVICTIONS.md`.

**And the consequence that outlives both.** The plugin directory is versioned
and replaced on update, so a conviction recorded into it is discarded the next
time canon updates. That settles an architectural question nobody had asked:
**the plugin is how the record is read everywhere; the repository is the only
place it is written.** A new conviction is a pull request against canon, and it
reaches other machines through `claude plugin marketplace update satc`. Every
record-reading skill says so now.

127 tests.

---

## 2026-09-04 · The suite runs again, and a Unix filesystem asserted on Windows

**The suite had not really been runnable.** `<temp>/pytest-of-<user>` on this
machine is locked against its own owner — `icacls` cannot read it, and granting
yourself access is refused — so every test taking `tmp_path` errored at *setup*.
That is 34 of them, reported as errors in tests that never ran, which reads as
broken code rather than a broken directory. The firm chose the in-repository fix
over an elevated command.

`conftest.py` now chooses a scratch root and carries why both obvious choices
are wrong:

- **Not inside the tree.** Tried first, and it made canon's own no-client-data
  check walk the fixtures the fix had just written and report that the record
  carried a taxpayer identifier, an employer identifier and a private key. It
  carried none of them.
- **Short.** Windows refuses paths past ~260 characters and names neither length
  nor the tool that failed: the observed symptom was `git init` exiting 128
  under a deep pytest path. The root has a length budget, asserted by a test.

An operator who sets `PYTEST_DEBUG_TEMPROOT` themselves still wins.

**And a failure that had been sitting in this repository.**
`test_installed_elsewhere` isolated its subprocess with a hardcoded `PATH` of
`/usr/bin:/bin` — a Unix filesystem asserted by a test that also runs on
Windows. Every test using that helper passed except the one that shells out to
`git`, which failed with `WinError 2` and named neither PATH nor git.
`shutil.which` asks the platform instead. A claim in the docstring, a different
behaviour in the value, and nothing comparing them — inside canon.

**Mutation table.** Seven planted, seven killed, after one survivor worth more
than the six kills: `test_a_root_the_operator_chose_is_left_alone` handed
`choose_root` a *long* directory, so deleting the operator check left the
*length* check to return `None` anyway and the test stayed green. It was passing
for a reason unrelated to what it tested. Rewritten to use a short directory and
to assert first that the directory would otherwise be accepted.

**What went wrong in the doing of it, which belongs here more than the fix
does.** The first commit of this work silently contained three of the five files
it was supposed to. The `PATH` fix and this log entry were written, verified by a
green suite, and then not committed — and both were reported to the firm as
landed. It surfaced only because a rebase onto a moved `main` showed the branch
carrying three files instead of five. Nothing in the process compared what was
claimed against what was staged, which is the one sentence at the top of
`how-we-work` happening to the session writing the guards. **`git show --stat`
before saying a thing is committed.**

93 passed and 34 errors → **138 passed, 0 failed**, with nothing set by hand.
The README's "121 tests / 48 mutants" was stale by six tests before this work
started; corrected to 138 / 55.

Version left at 1.3.0: nothing a session reads changed.

---
## 2026-09-04 · C6 retired within a day, and four entries in its place

**A conviction misfired, and that is the entry worth reading.** C6 was recorded
on 4 September as applying to *"Occam, and any AI doing the practice's work"*.
Hours later Bassy pointed it at a scheduled, deterministic data-disposal engine
and asked whether the firm had abandoned the separation of duties. The firm:
*"this is really specific to Occam, maybe overstated... in this case, i think it
is being misinterpreted."*

The record was wrong, not the firm. C6 is **retired** — text kept, state flipped,
reason recorded — and four entries take its place:

- **C7 · The context follows the role, and the reviewer carries the preparer's
  work.** The rewrite is much better than what it replaces, and it came from the
  firm rather than from a session tidying its own mistake: the division is not
  headcount, it is *information*. The reviewer answers for what the preparer did;
  their output is a **question back to the preparer**, not a correction; and the
  preparer must be able to send up what is *"beyond their paygrade"*.
- **C8 · A deterministic engine is not a brain, and does not need a second one.**
  The line C6 could not draw, settled by the misfire that exposed it.
- **C9 · The simplest answer is likely the best.** The practice's software is
  named after it and it was not on record.
- **C10 · An agent runs on the Forge if it can, and is built to its role.**

**The new entries were run before being believed.** `challenge.gate` was called
with a decision written for each one, and C9 **did not fire on the exact case its
own challenge note describes** — "add a second backup script beside the existing
one" returned silence, because `touches` matches whole words by design and
"duplicating" is not "duplicate". Inflections added, re-run, fires. C9 also now
says in its own text that the selector under-fires here: it matches a decision's
*subject*, and this entry is about a decision's *shape*. Better to record the
limit than to let the entry claim a reach it does not have.

**A pre-existing false positive, reported and not touched.** `bump the version
number in package.json` fires **C4**, whose `Fires on` includes `package`;
whole-word matching still sees `package` in `package.json`. It is the firm's
conviction and theirs to change, so it is written down here rather than fixed
quietly.

Convictions are read from the plugin cache, which keys on version, so this is
**1.4.0** — without the bump `claude plugin update` pulls nothing.

126 passed, 1 failed (the `/usr/bin:/bin` PATH bug that PR #198 fixes), with the
temp-root workaround this branch still needs because #198 has not merged.

## 4 September 2026 — credit-suite M1, and two bugs the bar could not see

M1 merged to main as `577ca35` (PR #184, 29 commits). Nine issues closed:
#164–#170, #180, #181. One engine, six monitors, both spine monitors at
cell-for-cell parity — 22,836 FDIC cells and 21,975 FRED cells, formulas
recomputed rather than compared as text.

**Four decisions, answered on a docket form rather than in chat.** All four took
the recommendation, and the form is the reason they are recorded here at all
rather than living in a conversation nobody can find again.

| decision | answer | what it caused |
|---|---|---|
| Turn the Excel VBA setting back off | *Done — turned it off* | Verified: `AccessVBOM` is absent again, back to its shipped default. |
| Merge the branch | *Merge it* | `577ca35`. #164 needed closing by hand — its commit said `(#164)`, a reference, not a closing keyword. |
| Stop 26 series being flagged stale forever | *Fix it — per-publisher lag* | PR #204. Live stale count 38 → 1. |
| Five dead series | *Check for successors, drop the rest* | PR #204. Five retired, reasons in `series_seed.RETIRED`. |

**The two defects, and why neither was visible.** Both were in shipped product
and both were invisible to a suite that was green the whole time.

*The ExtractFiles button had never worked, in any monitor, in any workbook ever
shipped.* The VBA compressor emitted MS-OVBA literals only, which cannot be
legal past one chunk: the header carries the chunk size in 12 bits, capping a
chunk at 4098 bytes, while every non-final chunk must decompress to exactly
4096 — and 4096 literals need 4096 + 512 flag bytes. Any module over ~3.6 KB was
unrepresentable. Both shipped macros are over it. `olevba` decodes the broken
output without complaint, which is exactly why the offline bar stayed green, and
real Excel refuses it.

Eight hypotheses died before one held, each overturned by the next experiment,
and two experiments were void by construction. What ended it was not more
thinking: the firm enabled the Trust Center setting, Excel authored a project
itself, and bisecting *down* from that working file found it in three steps.
**A known-good artefact beat eight rounds of reasoning about a broken one.**

*Eleven of eighteen FRED metro series were pulling ids FRED does not publish.*
FHFA publishes those metros at division level; the seed derived every id from
the CBSA code. A live pull 404'd eleven times while the whole offline bar was
green.

**What this says about the bar.** Three separate times the checking machinery
was the thing at fault: `check_parity` crashed while *printing* a diff, the
first real break it ever had to describe; `mutation_check` could silently skip
an equal-length mutation through stale bytecode, in both directions, so every
mutation count quoted before this week was worth less than claimed; and the same
harness could not run at all on a fresh Windows clone. Each was found by using
it, not by reading it.

The suite went 234 → 278 passing and 63 → 77 mutations killed, and credit-suite
got its first CI job — until 4 September its entire verification bar ran only on
the machine that built it.

**Still open:** whether `DEXRSA` (Case-Shiller Detroit, one month behind its
nineteen peers) is a permanent stop or a one-off delay. One observation cannot
say, and the flag now surfaces it instead of burying it in 38.

## 4 September 2026 (later) — the second docket, and M2 scoped

Four more answers, all on the recommendation, all acted on.

| decision | answer | what it caused |
|---|---|---|
| Merge PR #204 | *Merge it* | `8b1f810`. The stale flag now means something and five dead series are gone. |
| Close #176 | *Close it — post the evidence* | Closed with the run output, after re-running canon's suite here: 138 passed on Windows, the thing the issue called impossible. |
| Detroit still flagged | *Leave flagged, re-check next release* | Issue #207, with the date (29 Sep, the last Tuesday) and the three outcomes and what each means. |
| Start M2 | *Scope into issues first* | Issues #208–#214. |

**Two decisions were only possible because someone checked rather than assumed.**
#176 was fixed by another session and left open; it closed on a suite run here,
not on reading their commit. And Detroit looked like a sixth dead series until
FRED's own metadata showed it had been refreshed on 27 August within two minutes
of Chicago's — alive and maintained, just missing one month. Retiring it would
have been a plausible, checkable, wrong decision.

**M2, seven slices, dependency-ordered.** Goldens for all four monitors first,
because nothing may move before there is a record to move it against — that is
the single thing that made M1 safe. Then macro (reuses the proven FRED provider
and kills the duplicate, closing #178), bureau (whose data source is genuinely
unestablished and is named as an open question rather than assumed), CFPB (a
scraping provider, where an empty result must fail loudly), EDGAR (two-stage
fetch and a CIK dialect — and the slice explicitly checks whether the engine
diff is zero, because the PRD's own success criterion says it should be).
Then provenance across all six, then conformance turning from reporting to
failing.

**Why the last slice matters.** On the morning of 4 September the ExtractFiles
fix had to be applied by hand to five separate copies of the same file. Nothing
currently stops someone copying a module back in — it is the easiest thing in
the world to do, it always works, and it is invisible until a fix lands in one
copy and not the other. Slice 6 makes that fail the build instead.

**Standing:** #175 untouched. #207 waits on the September release. 278 tests,
77 mutations, both spine monitors at parity, six of six checks green.

## 1.5.0 — three behaviours a fourteen-hour session paid for

**16 · A skipped check is not a passed one.** Five tests skipped in a full suite
while passing alone — they borrowed a staged record the earlier 1,600 tests had
consumed. The same day, ten tests in another project skipped for want of a
harness nobody had run, so the checkout holding the firm's real client data
reported *1,424 passed, 12 skipped* and looked healthy while the working copy
reported 1,434 and 2. Same commit. The gap was ten checks that quietly did not
happen.

**17 · Clean up what your run touched.** A test suite drove the owner's desktop
Outlook — five compose windows across two runs, four of which saved themselves
into his Drafts. He noticed before the session did. Nothing was sent, and fixing
it made the suite five times faster: most of sixteen minutes had been spent
blocking on a desktop application.

**18 · Prepare it; do not prescribe it.** The firm was told to run a command
still sitting in an unmerged pull request, from a checkout parked on another
branch, with a Python that could not import its own libraries. All three were
checkable from that machine.

**Two sharpened rather than added.** Behaviour 2 gains the count that was
reported as 12, then 14, then 20 in one day and was 38 — each figure a row limit
read back as a total. Behaviour 3 gains the harder half: in that session **five
findings were the instrument, not the code**, and every one would have had
somebody repair something that was never wrong. It also now names two shapes
that hide from mutation testing — a branch that runs in one ordering and not the
other, and an exclusion list that outlives the guard it was written around.

**Checked before believed.** Three mutations against canon's own tests: a
behaviour stripped of its incident, one reduced to an observation with no
`**Do:**`, and a stated count that disagrees with the content. Each fails the
test that names it. 138 passed.

Convictions are read from the plugin cache, which keys on version, so this is
**1.5.0** — without the bump `claude plugin update` pulls nothing.

---
## 2026-09-04 · C11, and the bump that was made and still did not arrive

**The conviction.** C11 was recorded from the firm's own words:

> *i am a firm believer in the simplest answer being doing the work upfront and
> testing to ensure it works when you know you will eventually do it anyway.
> that's what makes AI so useful as a tool, it wildly changes my view of
> complexity*

It refines C9 rather than repeating it. C9 is *one mechanism, not two beside each
other*; C11 is about **when** — that the work you know is coming is cheapest done
now, and that AI changes the arithmetic of what "too complex for now" means. It
fires on `defer`, `simplest`, `scale` and `hardcode`, and it is the conviction to
raise whenever a session proposes a stub it intends to replace.

**What actually went wrong, which is the entry worth reading.** C11 was merged to
`main` in a commit that touched five files and neither manifest. Nothing failed.
The entry above this one, written the same day, ends: *"Convictions are read from
the plugin cache, which keys on version, so this is 1.5.0 — without the bump
`claude plugin update` pulls nothing."*

**That session knew the rule, bumped `plugin.json`, and the record still did not
arrive** — because the number the cache keys on is the one in the MARKETPLACE
entry, one level up, and that stayed at 1.4.0. So for most of a day the installed
copy stopped at C10 while the repository had eleven, and no test in a 138-test
suite could tell: the only version check asserted the string matched semver.

A rule stated correctly in a log, followed, and still missed — because it was
followed at the wrong file. Knowing a rule is not a mechanism.

**Three checks, each proved able to fail:**

| | |
|---|---|
| the marketplace and the manifest must agree on the version | mutated back to 1.4.0 → red |
| the record's digest must match the version that claims it | a conviction appended with no release → red |
| a count stated in a manifest must be a count somebody made | the marketplace said *fifteen* standing behaviours; there are eighteen → red |

`canon/release.py` writes `RELEASED.json` — a hash over `CONVICTIONS.md`,
`TENETS.md` and the two skills a session actually reads. **It cannot force a
bump, and it does not claim to.** What it does is make the omission loud: change
the record and the suite goes red until the digest is rewritten, and the line you
rewrite sits beside the version number, so *"should this be 1.6.0?"* lands in a
diff somebody is reading.

Also recorded to `PLAN.md` this session: the expert-desks decision, the Forge as
a flag rather than a gate, and D4 — the paid Codification licence — put on the
backburner by the firm: *"backburner the paid cert, we will test the process and
see what we learn."* ASC stays `human_only`; the fixed-assets desk proves the
mechanism on federal authority, which is public, binding and free, before anyone
spends money to widen it.

141 passed. Version stays at **1.5.0** — the record did not change here; what
changed is that the version now travels.

## 4 September 2026 (evening) — trends, charts, a readable tie-out, and a lesson re-tested

Written while working, not at the close. Session moved to Fable 5.1 mid-afternoon
by the firm's choice; canon 1.6.0 loaded, and behaviours 16–18 were applied to
this session before the docket was built rather than after.

**Built, in PR #248 (draft, CI 7/7 green):**

- `tools/trend.py` — the history was already in the workbook. `Raw_FDIC` holds
  16 quarters × 12 banks × 68 fields back to 2022-Q3, and every dashboard read one
  column. Change over 4q/8q, run length, divergence from the peer median move.
  Lights no flags; thresholds stay in `_config`.
- `tools/chartbook.py` — a second workbook with 18 native Excel line charts, no
  macros, so it opens with no Mark-of-the-Web banner. FDIC only.
- `--tieout` rewritten to a block per metric: what it is, how built, where on the
  form, the code, the verification state in words. All 53 metrics described; the
  codes kept, because stripping them makes the number unsearchable.

**A carried lesson tested rather than inherited.** L4 forbids native charts on
two grounds. The corruption ground did not reproduce in Excel 16.0 — a library
chart opened with zero dialogs, bare and inside the real `.xlsm` with its macro
still running. The refresh ground still holds and is the binding one. Amendment
is on the docket, not made.

**What an auditor asked for, and got most of.** *"i want to see the validation
process work, and believe it."* Capital One (CERT 4297, 2026-06-30), pulled with
raw `urllib` and no monitor code: RCON1407 + RCON1403 = 6,822,000 = NCLNLS as
reported; 100 × 6,822,000 / 457,432,000 = 1.4913692089753 = the FDIC's published
ratio = the workbook. The one ratio that does not tie (NTLNLSQR, 1.1% off) is
explained by RC-K average loans, as the provenance note already said. The filed
Call Report was opened at `cdr.ffiec.gov` and its cover confirmed — bank, quarter,
form 031 — but the viewer would not surface the line item. **The chain reaches
the FDIC's API, not the filing.** Closing it needs the XBRL download, which
needs the firm's permission; it is decision 2 on the docket.

**Behaviour 2, caught in the act.** This session reported "32 open pull requests"
off a listing. A limit-free count says 9, with 65 of mine closed since noon (35
merged) — main took 75 commits in an afternoon. Whether 32 was ever right cannot
be told from here. Recorded on the docket as wrong, not absorbed.

**Behaviour 16, applied.** The 20 skips are all the legacy-runner differential
tests. What is therefore unproven: that the engine still matches an
implementation that no longer exists. That proof now rests on the parity
goldens — a different proof — and the docket says so instead of calling the
skips inert.

**Behaviour 17, applied.** Cleared before the docket: a data export left at the
repo root, two scratch files in `/tmp`, a Chrome tab, and stray Excel processes
(none found). `credit-suite/example-output/` is now ignored so `git add -A`
cannot sweep two live workbooks into a commit.

**Not tested, stated.** `trend.py` and `chartbook.py` carry no tests. They are
hand-verified against raw cells and the workbook's own recalculated formulas,
and they write nothing into the monitor. That is below this project's bar, and
the docket says so beside the recommendation to merge.

**Docket published**, five decisions: merge #248; permission to download the
XBRL; amend L4; ship the chart workbook as an M2 slice; document the red banner
in `_readme`. Answers to be written here when given.

---

## 5 September 2026 — two sessions wrote to the record at once, and it broke in two ways

`main` was red for about an hour and every open pull request was stuck behind it
— 253, 254 and 257, two of them not this session's. Four failing tests, two
causes, neither of them the four tests' own fault.

**A silent partial read, in the place canon's own log already names.** `_field`
took the first line of a field and nothing else. The C11 decline recorded the
night before carries a ten-line `Not a conviction because:`; **nine lines were
dropped by every read**, and the record still parsed. Nothing downstream could
tell — an empty field and a field that was never fully read look identical to
every caller — and the only check that could notice is the round trip, which
compares the committed file against a re-render of the parse. It noticed.

This is the same defect the entry of 4 September records one field over: *"a
single-line reader on a value that had grown, parsing 5 of 24 subjects and
reporting success."* Fixed there, in `desk/record.py`, whose comment names canon
as where it was first found. Not fixed here, because nothing had wrapped yet.

**Two sessions, two ideas, one id.** `61b04c9` recorded C11 as a conviction the
firm holds. `ae23978`, an hour later, recorded a different C11 as a proposal they
declined. Both merged. The record whose own rule is that ids are never reused
held one number against two ideas, and *"what did we decide about C11"* became a
question with two answers. The declined entry — the later claimant — is now C13.

**The test that should have caught it was the reason it wasn't caught.**

```python
assert [d.cid for d in declined] == ["C3"]
```

A literal like that fails on the second declined entry whatever it is called, so
it reads as a tripwire for exactly this. It is not one. Whoever adds an entry
updates the literal, the suite goes green, and the collision is untouched — which
is what happened. It now asserts the RULE, over whatever the record holds:

```python
twice = sorted({i for i in ids if ids.count(i) > 1})
assert not twice
```

**It needs no editing when the record grows, and cannot be satisfied by editing
it.** That is the difference between a check and a note.

**Two things the fix taught, which were not in the brief.**

*Prose wraps; structure does not.* Making `_field` multi-line for everything was
over-broad and broke a passing test immediately: `Fires on` is a comma list this
module writes on one line, and read as prose it swallowed `Proposal.ask()`'s own
closing question as two subjects the conviction fires on. A run-on read of a
structured field does not lose data, **it invents it**. Wrapping is now opt-in,
and only a field whose value is a sentence takes it.

*A rendered entry has to be closed.* `ask()` printed the entry and then asked the
firm to confirm it, with nothing between. A field's value runs to the next field
or a rule, so prose appended straight after an entry is structurally part of its
last field. `ask()` now ends the entry with `---`, which also does the thing it
looks like it does.

Eight mutations, all red. Two survived a first attempt and both were the test's
fault rather than the code's: one asserted `_field`'s default in isolation and
left the real call site in `parse_convictions` free to pass `prose=True` with the
suite still green — **the helper proved and its caller not, for the fourth time
in this repository** — and one "empty reason" fixture was not actually empty.

168 passed. **1.7.0 → 1.7.1**, both manifests, because the record changed and the
plugin cache keys on the marketplace number.

### What the firm answered on the 5 September docket

Published as a form rather than as prose, per the docket skill; answers read back
out of it with `read_db`.

| | Answered |
|---|---|
| Fix the canon record, and on which branch | **Yes — new branch.** This entry is that work. |
| Which subject the second desk covers (#245) | **Cash and bank reconciliation** — the firm's own example, and a firm convention rather than a citable rule, which is the shape that makes escalation fire. |
| May a desk's question leave the network | **Yes — de-identified only.** In their words: *"sure build that in and de-identify, i still want it measured against real so we can see how much is able to be saved and automated"* |
| Should a near-miss citation stop being filed as a refusal | **Yes — record the near miss.** |

**Open against that third answer:** *measured against real* has two readings —
against real client work, to see what proportion a desk can take over; or the
de-identified input against the real one, to see what de-identification costs in
accuracy. They are not the same measurement. Asked rather than assumed.

**Not proposed as a conviction, yet.** *"i still want it measured against real"*
may be a standing belief about evidence rather than a scoping call on this
project. It is noted here so it is not lost, and it is not in `CONVICTIONS.md`,
because nothing enters that file without an explicit yes.

---

## 5 September 2026 (later) — what the docket's answers caused, and one correction

The four answers are in the entry above. What they turned into:

| Answered | Landed as |
|---|---|
| Fix canon on a new branch | #260, merged. `main` was red for roughly an hour and a half and had #253, #254 and #257 stacked behind it; 168 pass on `main` again. |
| Cash and bank reconciliation | `desk/desks/cash-and-bank` — 47 passages, 4 problems, the first desk built through `factory.emit` rather than by hand. |
| De-identified only | Noted; nothing built yet. |
| Record the near miss | `Unsupported.falls_under`, and the run prints `n filed, m of them citing a finer path inside a rule the desk holds`. |

**Two clarifications the firm gave after the form was filled in**, recorded here
because an answer that lives only in a conversation has to be asked again.

*On measuring against real.* The written answer read two ways — against real
client work, or de-identified input against real input. The firm: **"Against real
work. Run the desk on actual engagement questions, de-identified, and measure
what share of them it can take over. That measures the labour saved."** And on
the other reading: *"other is cool but let's not overcomplicate at this point."*

*On which body of law the cash desk belongs to, which is the correction.* The
desk was built on tax sources — § 1.446-1 and IRS Publication 583 — because those
are what this environment can reach. The firm:

> there is a difference between tax and something like GAAP. i account like an
> accountant, even in cash basis though we would record what happened. cash in
> and cash out. cash balance doesn't change for tax purposes. i feel like i'm
> going crazy here having to explain this. it's not just bull shit i'm making up

They are right, and the session was wrong about which body of law the question
lives in. Bank reconciliation is bookkeeping: the books record the transaction
when it happened, the bank records it when it processed it, and the difference is
timing. It holds on cash basis too — cash basis governs when income and expense
are RECOGNISED, not whether a check that was written was written.

**The mistake was a streetlight search**, and it has a name now: the sources
reached first were the ones that answered, not the ones that govern. Recorded in
`factory.QUESTIONS` Q3 and in the desk-factory skill so the next desk does not
repeat it, along with the two facts that came out of chasing it — eCFR serves
EVERY CFR title, so accounting and banking authority is reachable too; and
reachable is not a reason to store, because SEC Regulation S-X came back clean
and mentions reconciliation, outstanding checks and deposits in transit exactly
zero times, so it was left out.

**What the correction did NOT change is the desk.** The literature that states
the convention is FASB ASC, which is `human_only` by licence — no network policy
reaches it, and neither would the Forge. So the desk holds the firm's words
instead, as `positions/POS1`, unratified. That is not a workaround; it is the
case the two-store split was written for, and this is the first time it has been
the actual answer rather than an illustration.

**Standing and unrecorded:** the tax-against-GAAP stance above looks like a
conviction rather than a decision — it would hold next year, it carries a reason
about principle, and the firm has now had to explain it more than once, which is
the exact cost `CONVICTIONS.md` exists to remove. It is drafted and put to them
as a proposal. **Nothing enters that file without an explicit yes**, so it is
named here and not there.

---

## 5 September 2026 — C14, and the qualification that came with the yes

The tax-against-GAAP stance was proposed as a conviction and confirmed. **C14 ·
Tax treatment does not move the books; the books record what happened.**

It was proposed because the firm had explained it more than once in one evening —
*"i feel like i'm going crazy here having to explain this. it's not just bull
shit i'm making up"* — and removing that cost is the whole reason this file
exists. A session had just built a desk on the wrong body of law for want of it.

**The qualification is the part worth recording separately**, because it names a
failure mode this record could otherwise create. The firm, confirming:

> that is a conviction but it does not mean i want to avoid looking stuff up
> about it

So it went into `How it could be wrong` rather than being noted and lost. **A
conviction that ends research is worse than none** — it turns a belief into a
reason not to read, which is the opposite of what a record of reasons is for.
Bassy challenges *from* the record; it does not get to close a question with it.

`1.7.1 → 1.8.0`, both manifests: the record gained an entry, and convictions are
read from a plugin cache that keys on the marketplace number.

---

## 5 September 2026 — the deliverable was the thing that was wrong

`tie-out` and `walk` both told a session what to prove and neither told it what
to hand over. A tie-out ran end to end — five links executed, the source
photographed, the roster with its denominator — and was filed as a Markdown note
with six loose files beside it. Nothing was missing and it could not be given to
anybody. The firm:

> i assumed that you understood the final product of tie out and walk would
> basically be a PDF that shows how everything tied out? and explains it and
> makes it easy to follow? Is that not?

and, on what the document has to do:

> A sample of one and a walk through or a… procedure document should literally,
> like, visually and verbally easily show you how all the dots connect. How to
> use the system? How it works. How it tied out.

Both skills now say the deliverable is **one self-contained file with every
image embedded**, rendered from the Markdown rather than being it, opening on a
picture of the mechanism — for `tie-out`, the same fact travelling two roads and
meeting at difference 0; for `walk`, the route through the screens.

Three other things the reworked exhibit did that the skill had not asked for,
now asked for: the source page **marked and enlarged** rather than merely
captured, with the entity, form and period in the same shot as the number; every
figure **read twice** where a second rendering of the same source exists — which
caught a digit misread on the day; and **what running it found** as a section of
its own, because that tie-out turned up three lines citing codes from the wrong
version of a regulatory form, right values behind a citation that pointed at a
line that does not exist.

And the one that changes a verdict: **a `COULD NOT` is a hypothesis about the
source and gets attacked once.** Five of them were recorded with true obstacles
named. Pushed, all five closed on one pass. Naming an obstacle is not testing
it, and the skill had been accepting the name.

Four new tests pin the shape (175 → 179 passing). `1.10.0 → 1.11.0`, both manifests:
skill text is installed behaviour, and an installed session reads whatever the
marketplace's number fetches.
