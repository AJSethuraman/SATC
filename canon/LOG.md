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
