# Scoreboard — fixed-assets desk — second run, the rules as authority (#244)

Ran 2026-09-04, the same calendar day as the first run. It is **not** in
`runs/2026-09-04/` because that directory is the first run's measured record and
this one must not overwrite it. Two runs, one day — not two days.

**Measured, never asserted.** Nothing here is a test and nothing here gates CI.
It is a record, in the posture `credit-suite` takes with its live pulls. Re-grading
never re-rolls the dice: `--forge-replies forge.jsonl` regrades the transcript that
shipped with it.

**One run. No run was discarded, and nothing was re-run to improve a number.**

```
                    wrongly_absorbed             correct        wrong_caught           escalated
qwen3:8b (Forge)                   0                   1                  15                   0
frontier                           0                   4                  12                   0
```

`graded: qwen3:8b (Forge) 16, frontier 16` · **never summed.**
**gap (correct): 1 vs 4 — three problems.**

## The baselines, beside the result and not below it

| Baseline | Score |
|---|---|
| Answering `not required to capitalize` every time | **10 of 16 conclusions (62%)** |
| Citing `26 CFR 1.263(a)-3(j)` every time | **7 of 16 citations (43%)** |
| Either constant, put through the engine | **0 correct** — a constant answer cites nothing |

Both print automatically from the record. They are the bar, and **neither row
clears the citation bar**: the Forge matched 1 of 16 citations and the frontier 4
of 16, against 7 for always saying `(j)`.

## How to read the citation number — read this beside it

Seven of the 16 problems key to `(j)` and five to `(l)`, because that is the
paragraph the regulation's own conclusion names. So the citation score measures
**whether the desk picked the governing family and the paragraph the regulation
names** — a real practitioner call — and **not** fine-grained retrieval. A reader
given a bare `4/16` will take it for the second thing. It is not.

## The finding this run exists to produce

`DIAGNOSTIC — not one of the four outcomes, and not a score:`

| Row | conclusion | citation exact | within governing rule, not it | off index | gave up |
|---|---|---|---|---|---|
| `qwen3:8b (Forge)` | 11/16 | 1/16 | **0** | 0 | 0 |
| `frontier` | 14/16 | 4/16 | **12** | 0 | 0 |

**The frontier row's 4 exact and 12 contained sum to 16.** Every one of its
citations was either the keyed paragraph or a paragraph beneath it. It picked the
governing rule in **all sixteen** problems and named the exact paragraph the
regulation's conclusion names in four. The engine refuses the other twelve as
`citation_does_not_support`, and that is correct — see below.

**The Forge row is degenerate on the citation, and the containment column is what
proves it.** It used three distinct citations for sixteen problems — `(d)(1)`
eleven times, `(i)(3)(i)` four, one other — and **not one** landed inside the
governing rule's subtree. It is not retrieving a finer path; it is anchoring on
the section's general rule. Its conclusion score of 11/16 sits one problem above
the 10/16 constant baseline, which by this run's own n=16 caveat is not a
difference anyone may read.

## Containment is reported and never scored

The firm considered loosening the engine to accept a contained citation and
**declined**. `_check()` is shared by `serve()` and `grade()` deliberately, so
anything forgiving a near-miss on the scoreboard hands one to a client. Two tests
hold that line — `test_a_near_miss_is_not_treated_as_a_match` and
`test_a_finer_path_under_the_governing_rule_is_counted_apart`. **Neither was
touched and nothing was implemented to accept containment.**

It is also not a metric in waiting: containment admits 14 of 172 paths under `(j)`
and exactly 1 under `(k)(1)(vi)`, so scoring by it would grade seven problems
fourteen times more leniently than one, for no reason but how verbosely the
regulation phrased its conclusion.

## What the two rows actually are

| Row | How it was obtained |
|---|---|
| `qwen3:8b (Forge)` | Ollama 0.33.3, `qwen3:8b`, on this box: NVIDIA RTX 2070 SUPER, **8192 MiB VRAM**. `temperature 0`, `seed 0`, `num_ctx 8192`, `think: false`, `num_predict 512`. Every prompt and reply is in `forge.jsonl`. |
| `frontier` | Claude Opus 5, as a **fresh Claude Code subagent context** with no history of this desk or repository, instructed to read exactly one file — a copy of `prompts.json` in an isolated scratch directory — and write 16 JSON replies. It was explicitly forbidden to touch `SATC/` at all, and reported reading nothing else. |

**Why the frontier row was not answered by the session that ran the first
scoreboard.** That session read `PROBLEMS.md` while building the adapter, so it
has seen the answer key. A row produced by it would measure contamination. This
session also read `PROBLEMS.md` — to verify the denominator and the exclusions —
and for exactly that reason did not answer a single problem itself.

**Both rows are parsed and graded by one code path.** `parse_reply` and
`scoreboard.run` do not know which brain produced a reply, and nothing was
repaired on the way back: no citation was mapped onto the index, no conclusion
onto an admissible phrase.

## The Forge ran. The ceiling is real and it is close.

**A Forge failure would have been a flag, not a gate — but there was no failure.**
qwen3:8b loaded fully into VRAM at `num_ctx 8192`: **6.19 GB resident of 8192 MiB,
leaving 292 MiB free.** All 16 prompts (17,845–19,679 characters, ~4,600 tokens
median, 4,919 max) fitted the window. 16 exchanges, 0 transport errors, 0 give-ups,
every reply parsed as JSON.

What does *not* fit is `--corpus text` (~17,000 tokens). This run used
`--corpus index` for that reason, and the record prints which shape was shown. A
row answered under the other shape is a different run, not a better one.

## `wrongly_absorbed` is 0 on both rows, and it is stated rather than omitted

It is also not evidence of much. `grade()` refuses a wrong citation **before** it
compares the conclusion, so on a run where the citation is the weak part this
outcome is structurally suppressed. The frontier row had 14 correct conclusions
and only 4 could ever have reached this column. Zero here means the trap was not
sprung, not that it cannot be.

## Unsupported queue

| Row | Entries this run produced | File before → after |
|---|---|---|
| `qwen3:8b (Forge)` | 15 | `forge.md` 18 → 33 |
| `frontier` | 12 | `frontier.md` 4 → 16 |

Every refusal was new; the queue deduplicated none of them. None has yet resolved
into a source or a position — this run produced the queue, it did not work it.

## NOT CHECKED

See `NOT-CHECKED.txt`, which ships in this directory and is reproduced in full in
`SCOREBOARD.txt`. It is 17 items and it is not optional reading.
