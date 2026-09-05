# Dayboard — canon adoption and mining, 5 September 2026

**Everything in this folder is a PROPOSAL. Nothing here has entered the record.**
`canon/CONVICTIONS.md`, `canon/TENETS.md` and `canon/projects/REGISTER.md` were
read and not modified. Each item waits on an explicit yes, one at a time.

Dayboard is `AJSethuraman/Dayboard` — a separate private repository, not a folder
in this monorepo. It is a household calendar and organiser for a wall-mounted
kitchen tablet. It is here only because the record it would join lives in
`canon/`, which lives here.

## The three files

| File | What it is |
|---|---|
| `adopt-proposal.md` | Six candidate tenets read from Dayboard's own 55 commits, each citing a real SHA; six pieces of evidence for tenets canon already holds; and a draft identity card for `canon/projects/REGISTER.md`. |
| `mine-proposal.md` | The mining run, which proposed **nothing** — see below. |
| `docket-2026-09-05.html` | Source of the docket published for the firm to answer. It carries the twelve open decisions, both outcomes each, and a recommendation on each. |

The published docket is at
`https://claude.ai/code/artifact/baded882-3979-473c-affc-965158989b3f`.
Answers are stored against it under the `decisions` collection, one document per
decision, and must be read back with the Artifact tool's `read_db` — this
session could not register a wake subscription on it, so nothing arrives on its
own.

## Two findings that outlived the run

**`canon/adopt.py` cannot see a JavaScript test.** Its `_TEST_PATH` pattern
matches `_test.ext` and `.spec.ext` but not `.test.ts`, which is what Vitest and
Jest use. Against Dayboard it saw 4 of 15 test files — and one of those four is a
helper, not a test — so the tier that exists to be judgement-free reported 4
commits where the real figure is 18. This is canon's defect, not Dayboard's, and
it will misread every JS/TS repository canon is pointed at. It is decision D-9 on
the docket.

**There is nothing of the firm's own words in Dayboard to mine.** Of the 62
commits git attributes to `iamtrispec@gmail.com`, 56 were committed by agent
tooling running under that git config and carry an empty body; the remaining 6
are GitHub web-UI merges whose bodies are the agent's pull-request text. `git
blame` attributes 22 README lines to the owner: 21 blank lines and one code
fence. Even the GitHub issue comments posted from the owner's account close with
a Claude Code footer. Canon's marker pass over 253 prose passages and all 95
commits returned 79 hits, all of them agent-authored.

So the mining run proposed zero convictions, deliberately. A conviction is a
quotation, and what was available here would have been an agent's sentence filed
under the owner's name in the file they are later challenged from. Whether
Dayboard should start capturing the owner's words at all is decision D-11.

## What was not checked

- The board was never opened, deployed or driven in a browser. No claim rests on
  the product working — only on its tests passing and its source saying what it
  says.
- Dayboard has no `LOG.md`, so the docket was built from git, the test run and
  GitHub rather than from a running log.
- The six tenet citations in `adopt-proposal.md` were verified as commits, not
  each re-read diff by diff.
- Roughly 1.2 MB of code diffs went unread; the commit messages were read in full.

## The baseline, measured 5 September 2026

`npm run verify` in `/home/user/dayboard` — lint, typecheck, unit tests, build,
worker tests — exits 0. **213 unit tests and 10 worker tests pass; none skip.**
`main` was last moved on 26 August (`666602b`), and the repository has no open
pull requests and no open issues.
