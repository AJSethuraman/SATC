# canon

**The practice brain.** What the firm has learned about building software, and
what the firm believes about running a business — carried into every project
instead of being trapped in the one that learned it.

Two records and one behaviour.

| | |
|---|---|
| **`TENETS.md`** | How to build. Each rule carries the incidents that proved it, tagged by project. Evidence **accumulates**: the third time a rule bites in a third codebase, it carries three citations and is visibly a law rather than a local quirk |
| **`CONVICTIONS.md`** | What the firm believes and why, in their own words. Held or retired — never deleted. Proposals they turned down are kept too, so the same question is not asked twice |
| **Count Bassy** | Called **Bassy**. The role any session steps into. Challenges the firm **from their own record and never from its own opinion** |

## What Bassy does, and does not

It challenges: *"You committed to X because Y. This is Z. Has Y changed?"* It
quotes rather than paraphrases, because a conviction paraphrased is one you will
disown the moment it is read back at you.

It does **not** decide. It surfaces and stops. Where two convictions both bear
on a decision it names both and settles neither — and it does not claim they
disagree, because all it can observe is that both were selected. Where they
genuinely do pull against each other, that disagreement is the finding, and a
disagreement resolved fluently is a finding destroyed.

Silence is a behaviour, not an absence. A decision that contradicts nothing
produces nothing, and there is a test for it. A thing that challenges everything
is a nag you learn to click past.

## Not

- **Not a task tracker.** Todos, sprints and status live in the repo doing the
  work. Two lists that must agree will not.
- **Not a second source of truth about any project.** It never mirrors what code
  currently does; that drifts on the next commit. Bassy reads a repo when it
  needs to know.
- **Never decides for the firm.**
- **No client data. Ever.** No names, no TINs, no engagement contents, in any
  form, including inside a quoted conviction. `canon` is the most portable thing
  the firm owns, which makes it the worst possible home for anything that has to
  stay put. A check enforces this over the whole record.

## Installing it

canon is a plugin. Installing it once at **user scope** makes it available in
every repository you open — it is not per-project, and nothing has to be copied
into the project you are working in.

```powershell
# once, from anywhere
claude plugin marketplace add AJSethuraman/SATC@claude/satc-handoff-batches-2-4-n2qrl9-b7-fee-estimate
claude plugin install canon@satc --yes
```

**The branch ref is not optional yet, and that is the whole reason to notice
it.** canon lives on a feature branch; its pull request is not merged, so
`main` carries no `marketplace.json` and no `canon/`. Told to run the command
without the ref, a session went and looked at `main`, found neither, and
reported — correctly for what it could see — that canon did not exist. Once the
pull request merges, drop the `@…` and the plain form works.

To pick up a change to the record on a machine that already has it:

```powershell
claude plugin marketplace update satc
```

Inside a running session, the same two steps are `/plugin marketplace add …` and
`/plugin install canon@satc`, followed by `/reload-plugins` — a session already
open does not pick up a newly installed plugin on its own.

Then, in any repo:

```
/canon:bassy            what does the record say about what I'm about to do
/canon:how-we-work      the fourteen standing behaviours
/canon:docket           what changed, what is open, what needs deciding
/canon:canon-mine       read the corpus and propose a conviction
/canon:canon-adopt      read a repo canon has never seen
```

Or just talk to it — the skills carry descriptions written to be matched on
ordinary work, so a session should reach for them without being told. *Should*
is doing real work in that sentence: being available is enforced, being picked
up is not. If a session has plainly not got them, name the skill.

**Observed, 4 September 2026:** installed from the marketplace at user scope, a
session started in a git repository with no relationship to SATC saw all four
skills, read `CONVICTIONS.md`, and answered a plan to push straight to `main` by
quoting C2 back verbatim and asking whether the reason had changed.

**Verify the manifest before publishing a change to it:**

```powershell
claude plugin validate .            # the marketplace
claude plugin validate ./canon      # the plugin
```

Both run in the test suite too, where the CLI is present. That guard exists
because it was missing: `author` was a plain string, the real installer rejected
it on the first attempt to install canon anywhere, and the test that claimed the
manifest was valid had only ever checked that the JSON parsed.

## Where this lives, and why that is temporary

`canon` sits inside the SATC monorepo, which is the one-folder-per-project
layout everything else here follows. **It is built to be lifted out.** Its own
manifest, no dependency on anything above this directory, nothing that assumes
an accounting practice.

That constraint is load-bearing rather than tidy. `canon` exists because lessons
trapped in one repository do not travel, and installing it into an unrelated
project must never require granting that project access to the repository
holding the client vault. The day a second venture wants it, `canon/` moves out
whole and nothing here has to change.

**So: no import, path or assumption that reaches outside `canon/`.** If one
becomes necessary, that is a design problem to solve rather than an exception to
make.

## State

**All thirteen slices are built.** The record parses and round-trips, nothing
enters it without an explicit yes, nothing is ever deleted, the challenge fires
and the silence holds, evidence accumulates, all 35 tenets have moved in and
were **ratified by the firm on 3 September 2026**, the corpus can be mined, and
a repository that predates canon can be adopted.

| | |
|---|---|
| `record.py` | convictions and tenets, parsed from and rendered to Markdown |
| `challenge.py` | what the record has to say about a decision in flight |
| `mine.py` | reads the corpus, proposes, **never writes** |
| `adopt.py` | reads a repo it has never seen; proposes; writes nothing |
| `check_record.py` | nothing sensitive lives here — with its denominator |
| `LOG.md` | the running log: roadmap, deferred work, known gaps |
| `projects/REGISTER.md` | one thin identity card per adopted project |
| `skills/bassy/` | the challenge role |
| `skills/how-we-work/` | the fourteen standing behaviours |
| `skills/canon-mine/` | mining the corpus, one proposal at a time |
| `skills/canon-adopt/` | adopting a repository, and writing its card |
| `skills/docket/` | the standing check-in: open decisions, denominators, gaps |

`python -m pytest -q tests` — 121 tests, including one that copies the whole
tree into a fresh repository with no SATC above it and runs everything there.
Every guard has been mutation-checked: break it on purpose, and a test must go
red. **48 mutants planted, 48 killed**, after four survivors that were each the
test's fault rather than the code's — the fix and the reason are in the comment
at each site.

`docs/prd-canon.md` is the spec, `docs/ISSUES.md` the slices in dependency
order, and `LOG.md` what is deferred and what is still unknown. `corpus/` holds
the firm's own words, from which the convictions are mined: proposed for
confirmation, never written directly.
