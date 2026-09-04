# canon

**The practice brain.** What the firm has learned about building software, and
what the firm believes about running a business — carried into every project
instead of being trapped in the one that learned it.

Two records and one behaviour.

| | |
|---|---|
| **`TENETS.md`** | How to build. Each rule carries the incidents that proved it, tagged by project. Evidence **accumulates**: the third time a rule bites in a third codebase, it carries three citations and is visibly a law rather than a local quirk |
| **`CONVICTIONS.md`** | What the firm believes and why, in their own words. Held or retired — never deleted |
| **Count Bassy** | Called **Bassy**. The role any session steps into. Challenges the firm **from their own record and never from its own opinion** |

## What Bassy does, and does not

It challenges: *"You committed to X because Y. This is Z. Has Y changed?"* It
quotes rather than paraphrases, because a conviction paraphrased is one you will
disown the moment it is read back at you.

It does **not** decide. It surfaces and stops. Where two convictions collide it
names both and resolves neither — the disagreement is the finding, and a
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
| `skills/how-we-work/` | the thirteen standing behaviours |
| `skills/canon-mine/` | mining the corpus, one proposal at a time |
| `skills/canon-adopt/` | adopting a repository, and writing its card |

`python -m pytest -q tests` — 102 tests. Every guard has been mutation-checked:
break it on purpose, and a test must go red. **37 mutants planted, 37 killed**,
after two survivors that were both the test's fault rather than the code's — the
fix and the reason are in the comment at each site.

`docs/prd-canon.md` is the spec, `docs/ISSUES.md` the slices in dependency
order, and `LOG.md` what is deferred and what is still unknown. `corpus/` holds
the firm's own words, from which the convictions are mined: proposed for
confirmation, never written directly.
