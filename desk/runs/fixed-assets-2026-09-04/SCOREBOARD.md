# Scoreboard — fixed-assets desk — 4 September 2026

The first run in which a model answered any of these problems. Everything in
`desk/` before this was deterministic machinery; this is the measurement.

**Measured, never asserted.** Nothing here is a test and nothing here gates CI.
It is a record, in the posture `credit-suite` takes with its live pulls: the
numbers are committed, not enforced. Re-grading it never re-rolls the dice —
`--forge-replies forge.jsonl` regrades the transcript that shipped with it.

```
                    wrongly_absorbed             correct        wrong_caught           escalated
qwen3:8b (Forge)                   0                   3                  18                   0
frontier                           0                  17                   4                   0
```

`graded: qwen3:8b (Forge) 21, frontier 21` · **never summed.**
**gap (correct): 3 vs 17 — fourteen problems.**

**The baseline, beside the result.** Answering `not required to capitalize`
every time agrees with **12 of 21 conclusions (57%)**. Through the engine that
same constant answer scores **0 correct and 21 wrong_caught**, because a constant
answer cites nothing and an answer with no resolvable citation never counts as
correct. Both numbers matter and neither alone is honest: 57% is the bar on the
*conclusion*, 0 is the bar on the *scoreboard*.

**`wrongly_absorbed` is 0 on both rows, and that is stated rather than omitted.**
It is also not evidence of much — see NOT CHECKED below. `grade()` refuses a
wrong citation before it ever compares the conclusion, so this outcome is
structurally suppressed on a run where citations were the weak part.

## What the two rows actually are

| Row | How it was obtained |
|---|---|
| `qwen3:8b (Forge)` | Ollama 0.33.3, `qwen3:8b`, on this box: NVIDIA RTX 2070 SUPER, **8192 MiB VRAM**. `temperature 0`, `seed 0`, `num_ctx 8192`, `think: false`, `num_predict 512`. Every prompt and reply is in `forge.jsonl`. |
| `frontier` | Claude Opus 5, as a **fresh Claude Code subagent context** with no history of this desk, instructed to read exactly one file — `prompts.json` — and write its 21 JSON replies to `frontier-replies.json`. It reported reading nothing else. |

**Why the frontier row was not answered by the session that built this.** That
session had already seen the answer key while inspecting `PROBLEMS.md`. A row
produced by it would have measured contamination. The subagent was given the
prompts and nothing else, for the same reason the prompts withhold the passage.

**Both rows are parsed and graded by one code path.** `parse_reply` and
`scoreboard.run` do not know which brain produced a reply. A gap measured by two
different graders would not be a gap.

## The finding the four outcomes do not show

Not one of the four outcomes, and not a score — read from the record and the
engine's own comparison, never from either model's prose:

| | conclusion right | citation right | cited off the index | gave up |
|---|---|---|---|---|
| `qwen3:8b (Forge)` | **20 / 21** | 3 / 21 | 0 | 0 |
| `frontier` | **21 / 21** | 17 / 21 | 0 | 0 |

**The local model got the accounting call right 20 times out of 21 and scored 3.**
Its conclusions were 13 `not required` / 8 `must` against a true 12 / 9 — real
discrimination, not majority-guessing, and well clear of the 57% bar. What it
could not do was name *which worked example* of the regulation the fact pattern
was. It used **4 distinct citations out of the 21 it held**, one of them for 12
of its 21 answers. It was not selecting authority; it was picking a default.

The engine is right to refuse those. An answer without its own authority behind
it has not earned to be called correct, and that rule is the whole plugin. But
it means this scoreboard is currently measuring *citation retrieval* far more
than it is measuring judgment, and the two rows differ mostly on the former.

The frontier row's four misses are one shape: a **cyclic permutation** inside
§ 1.263(a)-3(j)(3) — P7 cited Example 19 (true: 14), P8 cited 20 (true: 19), P9
cited 21 (true: 20), P10 cited 14 (true: 21). Its conclusion was right on all
four. It used all 21 citations exactly once, i.e. it solved the index as a
one-to-one assignment. That is a property of *this desk having 21 passages for 21
problems*, and it will not survive contact with a real record.

## The unsupported queue

Written by `unsupported.append`, which allocates each id against the queue on
disk. One file per row, because the queue deduplicates on the refusal and ignores
the model, so a single file would have silently collapsed a refusal both brains
made identically.

| Queue | Entries this run produced | Resolved into a source | Resolved into a position |
|---|---|---|---|
| `unsupported/forge.md` | 18 | 0 | 0 |
| `unsupported/frontier.md` | 4 | 0 | 0 |

**22 entries, none resolvable, and that is the correct outcome for these 22.**
Every one failed for `citation_does_not_support`: real authority, already in the
record, that was not what the question turned on. That is neither "real authority
never loaded" (no source to add — the right passage was already held) nor "a
defensible call the rules do not settle" (the regulation settles all 21). It is
the third resolution the queue names: *leave it, its visibility is the finding.*
The finding here is not a gap in the record. It is that the desk cannot yet find
what it already holds.

## Forge status

**The Forge row ran.** It was not blocked by the VRAM ceiling and nothing was
shrunk to fit. The prompt is ~1,070 tokens at its largest — one fact pattern, one
source line, 21 citation strings — inside the 8,192-token window that 8 GB of
VRAM allows (rule 1). 21 problems answered, 0 give-ups, **56 seconds** wall clock
for the whole row (18:04:04 to 18:05:00, from the transcript's own timestamps).

The ceiling still costs something and it is recorded here rather than argued
about: thinking was **disabled** so the reasoning would not eat the window it had
to answer from. What `qwen3:8b` scores with thinking on, on this box, is unknown.

## NOT CHECKED

Reproduced verbatim from `NOT-CHECKED.txt`, which is the file `render()` was
handed. See `SCOREBOARD.txt` for the generated output in full.

1. 21 of the section's 117 worked examples are usable as problems; `PROBLEMS.md`
   counts every one of the 96 exclusions. This scoreboard says nothing about the
   other 96.
2. The citation index handed to both brains holds exactly 21 strings for exactly
   21 problems, one each. That is a bijection, and a brain that notices it can
   solve the citation as an assignment puzzle rather than by knowing the law. The
   frontier row used all 21 exactly once; on a real desk holding hundreds of
   passages no such structure exists, so its 17 correct is an upper bound and not
   a forecast.
3. Both brains were told the desk's two admissible conclusions, derived from the
   record. That was deliberate: the engine compares conclusions exactly, so an
   unconstrained phrasing would score `wrongly_absorbed` for punctuation. It
   discloses that the answer space is binary. Nothing measured here shows what
   either brain does when the space is open.
4. `wrongly_absorbed` is 0 on both rows, and it was never seriously tested.
   `grade()` refuses a wrong citation BEFORE comparing the conclusion, so a wrong
   conclusion only lands in `wrongly_absorbed` if the citation happened to be
   right. The Forge row's single wrong conclusion (P10) also cited the wrong
   example; the frontier row had no wrong conclusion at all. Zero here means the
   trap was not sprung, not that it cannot be.
5. Neither row is a measure of legal reasoning held apart from memory. Treas.
   Reg. § 1.263(a)-3 and its examples are public and old enough to be in both
   models' training data. Nothing here separates recall of these specific
   examples from reasoning about the facts.
6. One run each, at temperature 0 and seed 0. Run-to-run variance was not
   measured, and the give-up tail rule 9 describes (roughly 1 run in 6 to 9) did
   not appear in a sample of one — `gave_up` was 0 on both rows, which is a
   sample size, not a finding.
7. The local model was run with thinking disabled to keep the prompt and the
   answer inside the 8,192-token window. What `qwen3:8b` scores with thinking on,
   and whether it fits, was not measured.
8. Escalation is untested from both sides. Neither brain escalated once, so the
   escalation path was exercised by no real answer, and nothing here shows
   whether either can tell "the authority does not settle this" from "I do not
   know".
9. Every problem on this desk rests on one primary federal source. The
   secondary-and-tertiary path (`authority_permits_choice`), the `human_only`
   path, and the ratified-position path were not exercised at all: this desk
   records no positions and holds no non-primary source.
10. `serve()` was not exercised. The scoreboard calls `grade()`; nothing in this
    run went through the production path that hands an answer to a caller.
11. Freshness was not checked. Verification read stored text, as designed;
    whether the stored text still matches eCFR is the staleness check's job and
    was not run here.
12. The unsupported queue deduplicates on the refusal (question, conclusion,
    citation, reason) and ignores the model field, so the two rows are kept in
    separate files. A single shared queue would have silently collapsed a refusal
    both brains made identically.

## How many runs

**One scoring run per brain, and it is the one reported.** The local model was
called 21 times, once per problem, and every call is in `forge.jsonl`. Before it,
one throwaway transport check (`{"ok": true, "n": 7}`) confirmed Ollama answered
with thinking off; it touched no problem. The plumbing — queue, diagnostic,
render — was proved on a scratch copy of the desk with stub replies, which was
deleted. Nothing was re-run to improve a number.

## What is in this directory

| File | |
|---|---|
| `SCOREBOARD.md` | this record |
| `SCOREBOARD.txt` | the generated output, as `render()` produced it |
| `outcomes.json` | **engine state**: every `Result`, its outcome and reason, per row |
| `prompts.json` | the 21 prompts, exactly as both brains received them |
| `forge.jsonl` | every prompt and reply from `qwen3:8b`, verbatim |
| `frontier-replies.json` | the frontier replies, verbatim |
| `frontier.jsonl` · `forge-regraded.jsonl` | the replay transcripts. Regenerated by the command below and not committed: they are `prompts.json` and the replies restated, and a record should not ship the same evidence three times. |
| `NOT-CHECKED.txt` | the list handed to `render(notes=...)` |

## Reproducing the grading

```
cd desk
python tools/scoreboard_run.py \
  --forge-replies    desks/fixed-assets/runs/2026-09-04/forge.jsonl \
  --frontier-replies desks/fixed-assets/runs/2026-09-04/frontier-replies.json \
  --notes            desks/fixed-assets/runs/2026-09-04/NOT-CHECKED.txt \
  --out              desks/fixed-assets/runs/2026-09-04
```

Drop `--forge-replies` to call the local model again. That is a new run and a new
record, not a correction to this one.
