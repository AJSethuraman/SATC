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

Slice 1 of thirteen — the tracer bullet. One tenet, one conviction, and the
challenge that reads them. Deliberately one of everything: the point is to prove
the plugin loads, the record parses, the challenge fires and the silence holds,
*before* thirty-five of anything is moved.

`docs/prd-canon.md` is the spec. `docs/ISSUES.md` is the remaining work in
dependency order. `corpus/` holds the firm's own words, from which the
convictions are mined — proposed for confirmation, never written directly.
