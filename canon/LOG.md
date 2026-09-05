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

## 4 September 2026 (night) — the third docket's five answers, and the chain reaches the filing

Five answers, all on the recommendation, all acted on. Recorded here because the
form is where an answer is given and the log is where it lives.

| decision | answer | what it caused |
|---|---|---|
| Merge PR #248 | *Merge it* | `d16e326`. Trends, charts, readable tie-out on main. |
| Download the filed XBRL | *Yes — download it*, with a question back: *"is this to tie out our api pull to that so we can prove it worked?"* | Yes. The chain now runs filing → components → ratio → workbook. Built into `--tieout --filing`, repeatable for any bank and quarter. |
| Amend L4 | *Amend L4, cite the tests* | Amended in `TEMPLATE_CONTRACT.md` with both tests cited and the half that still holds kept binding. |
| Chart workbook ships | *Ship it as an M2 slice* | Issue #252, placed after #208. |
| The red banner | *Runbook only* | A "Before you start" section in `docs/runbook-live-acceptance.md`: Mark of the Web shown and explained, the one-time unblock, the trusted-folder fix, copy-pastable. Not in `_readme`, per the answer. |

**What the filing check found, in the order it found it.** Capital One (CERT
4297) and KeyBank (CERT 17534), 2026-06-30, XBRL fetched from `cdr.ffiec.gov`
by replaying the page's own postback — to the form's *action* URL, which is a
different page from the one displayed; posting to the displayed page returns the
page, politely, with no file.

- **The filing is in dollars; the API and workbook are in thousands.** Total
  assets read 662,157,000,000 in one and 662,157,000 in the others.
- **Banks with foreign offices file consolidated lines under `RCFD`.** The
  provenance map cites `RCON` codes and annotates the 031 variant only for
  total assets. Capital One's `RCON2122` is 449.65 bn; `RCFD2122` is 457.43 bn,
  and the FDIC's figure is the consolidated one. A reviewer following the map
  literally to the facsimile would see a 7.78 bn "discrepancy" that is not one.
- **The map's parentheticals were right and my first parser threw them away.**
  `RCON2200 (+RCFN2200 031)` — deposits tie only with the 150,000 k$ of
  foreign-office deposits added. `RCON1766 (031: RCFD1763+1764)` — C&I loans
  are a different sum for an 031 filer, and it ties to the thousand.
- **Twelve "raw" fields are ratios and the charge-off flows are year-to-date.**
  The first run tied a percent to a dollar line and reported a 98 bn
  difference. Now skipped by unit, and by shape, each with its reason printed.
- **A regression of my own, caught by the tests and the live run at once:**
  treating the map's `RCON` as a fixed prefix rather than the convention sent
  every 031 line to the wrong box. Fixed; `RCON`/`RCFD` are the default
  resolved consolidated-first, and only `RCFN`/`RIAD` are instructions.

**Result:** 32 of 32 raw dollar lines tie for both banks, 0 differ, 0 absent, 5
skipped with a stated reason. `RCFD1407 + RCFD1403 = 6,822,000 = NCLNLS`;
`100 × 6,822,000 / 457,432,000 = 1.4913692089753` = the FDIC's published ratio
= the workbook. The chain is closed at the source of record for two banks.

**Opened the artifact, three times.** The chart workbook "opened with zero
dialogs" and a harness read a cell out of it. Exporting charts to PNG through
Excel and *looking* found: no axis numbers on any chart (openpyxl 3.1 hides
axes by default); the legend drawn over the data; and on the second pass, the
legend over the x-axis labels and the y-axis title over the tick numbers. Three
builds to get a chart a person could read. The harness could not have found any
of it. The peer overview is now grey context with the median in colour, plus one
small chart per bank — twelve hues were never going to be readable.

**The four unmigrated monitors, buttons pressed at last.** All day they were
"verified by file identity". Built from their own folders in a scratch copy and
driven through real Excel: all four `ran=True`, all four extracted their files.

**Tests written for the tools that had none:** `test_trend.py`, `test_chartbook.py`,
`test_filing.py` — 41 tests, 15 mutations, including the one that IS the
consolidated-first regression restored. 278 → 319 passed. 77 → 92 mutations.

**Behaviour 2, again.** "32 open pull requests" was read off a listing. A
limit-free count says 9; 65 of mine closed since noon. Recorded on the docket.

**Not done, stated:** FRED has no chart workbook (#252). The trend tool trends
FDIC only. The provenance tab still cites bare `RCON` codes — the tool now
compensates, but the tab a reviewer reads has not been corrected; that is a
golden change and wants its own decision.

## 2026-09-04 (evening) — the 670 that nobody believed

**The firm looked at the Capital One stage chart and said:** *"hard for me to
believe the 670 here is right."* It was right and it was wrong. `NTCONOTQ`
5,300 k$ charged off against an `LNCONOTH` book of 3,173 k$ at 2022-12-31,
× 400 = 670.41% annualised — the engine's arithmetic, the FDIC's raw cells,
tied to the thousand. The book was $3–7M for three years before it grew to
$8.6B in 2025. A ratio on a near-empty book is arithmetic, not information,
and the chart drew it faithfully.

**What changed.** `tools/trend.py` now carries a materiality floor:
`MATERIALITY_FLOOR_K = 100_000` (thousands, so $100M). Every loan-class
ratio (card, auto, other consumer, C&I, each real-estate class) is blanked
for a quarter where the bank's book in that class is under the floor. Totals
and capital ratios are never blanked. On the example monitor that is **625
bank-metric-quarter values** blanked out of the panel (BNY Mellon 192,
Morgan Stanley 156 — no card or auto book at all; Capital One 88; Goldman
80; Citi 69; KeyBank 40). Capital One's other-consumer stage chart now
starts at 25Q2, the first quarter the book cleared $100M; the stage sheet
says how many values are blank and why, and the About sheet explains what a
blank means ("too small to read", not "no data").

**Checked:** 331 passed, 20 skipped (full suite, 176 s) — the 20 are being
read, see the docket; parity 2/2; conformance 3 notes, all the known M2
single-sourcing items; the three new mutations (`trend-no-materiality-floor`,
`trend-materiality-blanks-nothing`, `chartbook-about-forgets-the-blanks`)
killed; full 95-mutation sweep running as this is written. Opened the
artifact: Capital One, KeyBank and the peer NCO chart exported through Excel
and looked at.

**Not decided by me, filed:** #258 — the FDIC's own published `NTCONOTQR`
(0.0044) does not match the value derived from its raw cells (670.41), and I
could not reproduce the FDIC's definition (YTD ÷ average balance gave 1.22).
#259 — a bank with no book in a class reads "OK" on the dashboard rather than
N/A. Both are output/golden changes; the firm's call. The $100M floor itself
is a judgement and is on the docket as a decision, not reported as settled.

## 2026-09-05 — the 670 docket, answered

Read back from the docket store at 01:05–01:09 UTC.

- **D1, the $100M floor — no pick.** *"hold on - it's just odd because that
  calc was all of a sudden really high and inconsistent with the others - it
  reads like an abnormality. make me believe you recognized the cause."* The
  floor is not accepted on the strength of a threshold; the cause of the spike
  has to be shown first. Investigating: the raw series either side of
  2022-12-31, and the FDIC's own definition of the ratio.
- **D2, #258 FDIC's published rate vs our derivation — "Investigate first."**
  *"if we use different data sources how do we either make sure it's still
  useful or separate it into views that can't be contaminated? like i think
  FDIC makes more sense if we can't reproduce … we can have multiple sources of
  data that have diff numbers and mean diff things. if a ratio is calculated
  using certain numbers, they will always be different."* Lean: use the FDIC's
  figure if ours cannot be made to reproduce it, and never put the two in one
  view. And: *"it would help if everything was said in more plain terms - i
  have no idea what LNCONOTH means without really thinking about it."*
- **D3, #259 — "Change to N/A."**
- **D4, the 20 dead skips — "Delete them."**
- **D5, provenance tab — "Fix the tab."** *"general thing - i dont know what
  RCON2200 means without looking it up so lets start making things have plain
  definitions in addition to the code."*

**Standing instruction from D2 and D5, applied from here on:** every code a
person reads — MDRM, FDIC field, metric id — carries its plain meaning beside
it, in chart titles, the provenance tab, the tie-out and dockets. The plain
description is not a substitute for the code (behaviour 15: show the jargon
and say what it means); it sits next to it.

**Candidate conviction, not yet entered:** *numbers from different sources
that mean different things never share a column* — from D2's note. To be
drafted in their words and taken to bassy; nothing enters the record without a
yes.

## 2026-09-05 — the cause of the 670, and the four decided items built

**D1 — the cause, from the FDIC's own records, not from a threshold.** Capital
One Bank (USA), N.A. (CERT 33954) merged into Capital One, N.A. (CERT 4297)
on 3 October 2022 — FDIC `/history`, change code 223 "Merger - Without
Assistance", acquiring CERT 4297. The spike sits in that quarter. The
mechanism, proved on the card book to the dollar: the FDIC builds a quarter's
charge-off flow as the merged bank's December year-to-date **minus both
banks' September year-to-date** (card: 2,926,715 − 140,331 − 1,767,237 =
1,019,147 = the published `NTCRCDQ`). For other consumer loans the acquired
bank had reported **no** other-consumer book and **no** other-consumer
charge-offs, yet the merged year-end total was $6.3M against the survivor's
$1.0M through September and a $0.3M-a-quarter run rate. The extra $5.3M is
the acquired bank's activity landing in a category it never used in its own
filings, divided by the survivor's $3.2M residual book. A merger artefact,
not a credit event. Which loans exactly cannot be read from public filings;
that is stated, not guessed.

**D2 — the FDIC's definition, reproduced.** The FDIC's `NTCONOTQR` is
quarterly other-consumer net charge-offs × 4 **over average total assets**
(this and the prior quarter-end), merger-adjusted: it reproduces the
published figure exactly in 8 of 8 non-merger quarters, and in the merger
quarter once the acquired bank's $127.6B of September assets are added to the
prior-quarter base (implied 486.36B = (391.81 + 127.60 + 453.31) / 2). Our
`NTCONOTQR` divides by the class book. Same code, different ratio. #258 is
therefore a naming collision, not a data mismatch, and the fix is a decision:
rename ours so it cannot be mistaken for theirs.

**Built, on the firm's answers:** D3 (#259) — a ratio on a book that does
not exist reads `N/A`: guarded direct metrics in the engine registry,
`metric_status` in the digest, the value cell and the Watchlist helper in the
workbook; FDIC demo golden re-banked after it detected 3,366 cells. D4 — the
twenty legacy-runner tests deleted with their scaffolding; the suite now
reports 0 skipped. D5 — the provenance tab's seventeen bare RCON rows carry
the code that tied live for an 031 filer (JPMorgan, CERT 17534, 2026-06-30);
a "what it is" column renders every row's plain meaning; 23 raw dollar fields
got plain descriptions; chart titles say the words and the code.

**A recovery, recorded.** At 21:30 another session auto-stashed this
checkout's working tree for a scoreboard run and switched the branch. Seventeen
files of uncommitted work and one untracked test went into `stash@{0}`. All of
it was recovered into a separate worktree (`C:\Users\ajish\SATC-cs`) and
verified there; three files touched in the shared tree after the reset were
put back. One shared checkout between two live sessions is the defect; the
worktree is the fix from here on.

## 2026-09-05 (later) — the two answers built, and a third thing found

**D1 answered "merger flag only" — so the floor came out.** The firm took the
cause over the threshold, and they were right to: a $100M floor hid the 670 by
luck of the book size. On a $500M book the same $5.3M draws a plausible 4.3%
that nobody questions. `tools/trend.py` now blanks quarterly-flow rates for a
quarter that spans a merger, from the FDIC's own record, and nothing else:
balances and 30-89 / 90+ / nonaccrual rates are correct as at the date and are
left alone.

New `sources/fdic/mergers.py` reads the FDIC history endpoint (one request for
the whole peer set, `ACQ_CERT:(...)`), keeps six acquisition change codes as an
allowlist, discards the four known non-acquisition codes by name, and
**reports** anything else rather than dropping it. A truncated page is refused:
a merger nobody sees is a quarter nobody marks. The record lands on a new
`_mergers` tab — contract §2 amended the same day to name it — written by the
runner on every run, and read back by the tool, so nothing infers a merger
from the shape of the numbers. Three answers, drawn apart: records, "asked and
none found", and "never asked" (the demo provider, honestly).

Six real mergers sit in the sixteen-quarter window for these twelve banks:
Citibank 2022Q3, **Capital One 2022Q4 (the 670)**, JPMorgan and US Bank
2023Q2, **Capital One 2025Q2 (Discover)**, PNC 2026Q2. Both discontinuities in
the chart the firm questioned are mergers.

**D2 answered "rename ours" — and the reason turned out to be worse than
stated.** The FDIC publishes nineteen of the twenty class ratios we compute,
under exactly our names, over **average total assets** where ours are over the
loan class. Ours are now `<numerator>_BOOK`. While checking that, the same
question was put to the fifteen class rates we *land* directly: they are the
FDIC's, so they are over total assets too — sitting on the loan-book dashboard
beside ours, under thresholds calibrated for book rates. `P3CRCDR` watches at
2.5% where the number it watches is 0.86% of assets, so eight early-warning
flags have been effectively dead. Filed as #268 with two options and a
recommendation; not changed, because it moves shipped numbers.

**A stale claim, corrected.** `series_seed.py` said these were computed
because "the R-twin name would exceed the 8-char field limit (unverified)".
The twins exist and are published. The note now says what is true.

**Checked:** 366 passed, 0 skipped. Parity 2/2 after re-banking the FDIC demo
golden (158 cells: the ids on `_config` and `_provenance`, 20 Watchlist
headers, the new tab; no dashboard value moved, flag counts unchanged).
Conformance clean but for the four known single-sourcing notes. Mutation sweep
run after all of it.
