# The Forge run — the prompt for the session that finds out (#227)

Everything in `desk/` so far is deterministic code proving deterministic
machinery. **No model has answered a single problem.** This is the run that finds
out whether a desk can do the job, and what the local lean costs.

Paste the block below into a Claude Code session **on the Forge** — the machine
that holds the local model. It is written to stand alone: it assumes no memory of
the session that built the desk.

---

## The prompt

```text
You are running the first real scoreboard for the SATC `desk` plugin, on the
Forge. Issue #227 in AJSethuraman/SATC is the spec; read it. Everything built so
far is deterministic and no model has ever answered one of these problems, so
every number you produce is the first of its kind. Do not guess any of them.

READ FIRST, BEFORE WRITING CODE:
  - docs/LOCAL-LLM-PATTERN.md — ten rules, each paid for by a measured failure
    on this exact hardware. Rules 1, 3, 9 and 10 govern what you are about to
    build.
  - desk/scoreboard.py — read the module docstring in full. It states the
    contract you are implementing and one constraint that is easy to violate.
  - desk/engine.py — you are NOT changing this. It already verifies and grades.

WHAT TO BUILD

One thing: an adapter `ask(problem) -> Answer` and a script that runs it.

    from record import load
    from scoreboard import run, render, gap
    from engine import Answer

    desk = load("desks/fixed-assets")        # 21 problems
    forge = run(desk, ask_forge, model="qwen3:8b (Forge)")
    front = run(desk, ask_frontier, model="frontier")
    print(render([forge, front], notes=[...]))

`scoreboard.run` already handles grading, the give-up tail and the denominator.
You are writing `ask`, and the script that prints and commits the result.

WHAT THE MODEL MAY SEE — THIS IS THE PART THAT IS EASY TO GET WRONG

Give it exactly:
  - `problem.facts`
  - the desk's sources (id, title, tier, citation prefix) from SOURCES.md
  - the list of citation STRINGS the desk holds, as an index to cite from

Give it none of:
  - `problem.answer` — obviously
  - `desk.passage(problem.citation).text` — the stored authority is the same
    regulation example COMPLETE, conclusion included. `scoreboard.py` says this
    in its docstring: the leak closed in the extractor reopens the moment an
    adapter passes the passage for the problem's own citation in as context.
    Eight review rounds went into withholding those conclusions. Do not hand
    them back.
  - `problem.title` — several titles name the outcome.

A model that cannot answer without the passage is a finding, not a bug to route
around. Record it and move on.

WHAT `ask` RETURNS

    Answer(position=..., citation=..., escalated=False, reason="", working=...)

  - `position` — its conclusion, in its own words. The engine compares it to the
    known answer, normalised for case and surrounding space only.
  - `citation` — must resolve in the desk's record or the engine refuses it.
  - `escalated=True` + `reason` — when the desk declines. `reason` MUST be one of
    engine.REASONS; anything else raises. That set is closed on purpose: an open
    one becomes prose and prose cannot be counted.
  - `working` — its reasoning, verbatim. Kept for refusals; it is the evidence of
    what the record is missing.

Do not post-process the model's answer to make it parse. If it will not produce
a citation, that is `no_citation` and the engine will say so. Rule 6: policy
lives at the choke point, not in the prompt you write for it.

THE TWO ROWS

  - `qwen3:8b (Forge)` — the local model.
  - `frontier` — a frontier model. Say in the report HOW you obtained it: your
    own session acting as the adapter, or an API call, and which model.

Never sum them. `gap()` reports the distance, which is the finding: what the
local lean actually costs, measured rather than argued about.

A FORGE FAILURE IS A FLAG, NOT A GATE. The firm, 4 September 2026: "it's also
acceptable that it would not work on our current hardware, that should just be
flagged. at some point we will have enough vram, for now we are limited." If the
local model cannot run this, report it WITH THE VRAM CEILING STATED and produce
the frontier row anyway. Do not block, do not shrink the problem set to fit.

WHAT TO REPORT

`render()` already puts wrongly_absorbed first and states it at zero. It is the
only outcome that costs anything: an answer that was wrong, that the engine could
not fault, and that would have reached a client.

Fill `notes` with what was NOT checked — in its own list, never omitted. At
minimum: that 21 of 117 examples are usable and why (PROBLEMS.md counts every
exclusion), and that always answering "not required to capitalize" scores 12 of
21, 57%. THAT IS THE NUMBER A RUN HAS TO BEAT BEFORE IT HAS SHOWN ANYTHING. Print
it beside the result, not below it.

Also report the `unsupported/` queue: how many entries the run produced, and how
many resolved into a source or a position. Use `unsupported.from_refusal(...)`
and `unsupported.append(...)` — `append` allocates the id against the queue on
disk, so call it per refusal and do not pre-number them.

RULE 10 IS THE ONE THAT MATTERS MOST HERE: every number is read from engine
state, never from the model's account of what it did. `Run.counts` reads
`Result` objects. If you find yourself parsing the model's prose to decide
whether it was right, stop — that is the failure mode this whole plugin exists
to prevent.

WHAT NOT TO DO

  - Do not assert the scoreboard in a test. Do not let it gate CI. It is
    measured and committed as a record, the way credit-suite marks its live
    pulls. A non-deterministic run cannot gate a build without either flaking or
    being weakened until it proves nothing.
  - Do not change `engine.py`, `record.py` or the problem set to improve the
    numbers. If a problem looks wrong, that is a finding to report, not to edit.
    (Three rows were already removed for exactly that reason — they punished the
    better answer — so this is not hypothetical.)
  - Do not retry until it looks good. Report the first honest run, and say how
    many runs you did.

WHEN IT IS DONE

Commit the scoreboard output to the repository as a record, on a branch, with a
draft PR. Write in the PR body: both rows, the gap, the baseline beside them,
the NOT CHECKED list, the unsupported queue counts, and — if the Forge row did
not run — the VRAM ceiling and what it would take.

Then say, in one line at the end, what the numbers mean for whether this
mechanism is worth building out. That is the question the firm is actually
asking.
```

---

## Why the prompt is shaped this way

**The window is the first constraint, not the last.** Rule 1: 8 GB VRAM is an
8,192-token context, and loading every tool schema (~11k tokens) silently
truncates the model's own instructions — it then "ignores" rules it never
received. The adapter hands the model one fact pattern and a citation index, and
nothing else, for that reason as much as for the leak.

**The leak is the thing most likely to be undone here.** The problem set went
34 → 21 across eight review rounds, mostly to stop the facts disclosing their own
answer. All of that is undone by one line in an adapter that passes
`desk.passage(problem.citation)` as helpful context.

**The baseline is printed beside the result because 57% is beatable by not
reading.** A scoreboard whose baseline is unstated reads as skill when it may be
arithmetic.

---

## The second run — the rules as authority (#244)

The first run's citation number was uninterpretable: the desk's whole authority
corpus was its own answer key, 21 worked examples for 21 problems, and the
frontier row solved the citation as an assignment puzzle
(`runs/2026-09-04/SCOREBOARD.md`, NOT CHECKED 2). #244 changed the record, not
the engine: the stored authority is now every paragraph of the section outside
its examples (172 of them), and a problem's expected citation is the rule its
own withheld analysis names. Sixteen problems; the other five of the 21 are
excluded **by name** in `PROBLEMS.md` because their analysis names two rules
that neither contains.

**Run it on the Forge, into a directory of its own.** Never into
`runs/2026-09-04/`; that is a measured record and the two runs are comparable
only with the change between them stated.

**The default `--out` is `runs/<today>/`, and both runs happened on 4 September
2026** — so the command below, run without an explicit `--out`, would have
written the second scoreboard over the first. The session running it noticed and
passed `--out` by hand. `run_dir` now refuses a directory that already holds a
run, on an explicit `--out` as well as the default: a scoreboard is measured and
the brain that produced it is not deterministic, so it cannot be regenerated.
Two runs on one day is not two days, and the record says which it is.

```
cd desk
python tools/scoreboard_run.py --corpus index --dump-prompts desks/fixed-assets/runs/<today>/prompts.json
```

Hand `prompts.json` to a fresh frontier context that has seen nothing else, as
before, then:

```
python tools/scoreboard_run.py \
  --corpus index \
  --frontier-replies desks/fixed-assets/runs/<today>/frontier-replies.json \
  --notes            desks/fixed-assets/runs/<today>/NOT-CHECKED.txt \
  --out              desks/fixed-assets/runs/<today>
```

`--corpus index` shows each citation with the first sentence of its paragraph
(about 4,100 tokens, inside the 8,192-token window). `--corpus text` shows every
paragraph in full (about 17,000 tokens) and does not fit the Forge; a row
answered under it is a different run. The record prints which shape was shown.

What to put in `NOT-CHECKED.txt`, at minimum: the denominator is 16 and not 21,
so the rows are not comparable to 4 September on the conclusion either; the
citation baseline is 7 of 16 (always citing `(j)`); and the engine matches a
citation exactly, so a desk citing `(j)(1)(iii)` where the key is `(j)` is
refused as `citation_does_not_support` — a limitation of the key, stated in
`PROBLEMS.md`, not a finding about the brain.

**How to read the citation number, and say it beside the number.** The
`DIAGNOSTIC` line now reports `within the governing rule but not it` alongside
the exact match: a desk that answered `(j)(1)(iii)` where the key is `(j)`
reached the right rule by a finer path. It is counted apart and added to no
total, on purpose — containment admits 14 of 172 paths under `(j)` and exactly 1
under `(k)(1)(vi)`, so scoring by it would grade seven problems fourteen times
more leniently than one for no reason but how verbosely the regulation phrased
its conclusion.

So the citation score measures **whether the desk picked the governing family
and the paragraph the regulation names** — a real practitioner call — and not
fine-grained retrieval. Write that sentence next to it. A reader given `9/16`
with no gloss will take it for the second thing.

The firm considered loosening the engine to accept containment and declined:
`_check()` is shared by `serve()` and `grade()` deliberately, so anything that
forgives a near-miss on the scoreboard also hands one to a client.
