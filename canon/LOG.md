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
