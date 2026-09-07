# Scoreboard — cash-and-bank desk — 5 September 2026

The third desk scoreboard, and the first on a desk built to **escalate**. The
fixed-assets runs measured zero escalations across 58 answers and could not have
measured otherwise: every source there is binding primary authority, so
`authority_permits_choice` had nothing to fire on. This desk's only on-point
source is an IRS publication — **secondary** — so the escalation path is
reachable. #245.

**Measured, never asserted.** Nothing here is a test and nothing here gates CI.
It is a record, in the posture `credit-suite` takes with its live pulls. One run
each. Re-grading never re-rolls the dice: `--forge-replies forge.jsonl` regrades
the transcript that shipped with it.

```
                    wrongly_absorbed             correct        wrong_caught           escalated
qwen3:8b (Forge)                   0                   0                   4                   0
frontier                           0                   0                   0                   4
```

`graded: qwen3:8b (Forge) 4, frontier 4` · **never summed.**
**gap (correct): 0 vs 0.** Neither row scored a servable answer, and on this
desk neither could: see "The escalated column is not the finding" below.

- **Frontier row:** a fresh Claude Opus 5 (1M context) subagent, given
  `prompts.json` and nothing else — no repository access, no sources, no
  positions, no sight of this document or of `FORGE-RUN.md`. It answered all four
  in one pass.
- **Forge row:** `qwen3:8b` on local Ollama, `--num-ctx 8192`, `--corpus index`.
  It ran; there is no VRAM ceiling to report on this desk. The index prompt is
  about 2,600 tokens against the 8,192-token window.

---

## The escalated column is not the finding

**A problem keyed to a secondary source cannot be graded on its conclusion** —
`_check()` refuses `authority_permits_choice` before any conclusion is compared.
So the escalated total is decided by the record's tier, not by the brain, and a
desk that escalated everything without reading would score the same. The
`DIAGNOSTIC` split is the whole measurement:

|  | Forge | frontier |
|---|---|---|
| **escalated by the desk** — the brain declined on its own | **0** | **0** |
| escalated by the engine — the brain answered confidently and was stopped | 0 | 4 |
| conclusion matched (not scored; tier fires first) | 0/4 | 4/4 |
| citation matched (not scored; tier fires first) | 0/4 | 4/4 |
| gave up | 0 | 0 |

**`escalated by the desk` is 0 on both rows.** It has still never been above zero
on any desk. Not one brain has ever read the authority, seen that it did not
settle the question, and said so.

The frontier row is the sharper half of that. It got the conclusion right 4 of 4
and the citation right 4 of 4 — it read the publication correctly and reasoned
correctly from it — and it **never once noticed that its only support was an IRS
plain-language publication about an accounting convention**. It was stopped by
the record's tier, not by its own judgement. Competence and deference are
independent, and this run separates them: full competence, zero deference.

---

## The Forge row did not reach the escalation path at all

The brief for this run predicted 4/4 escalated on both rows. **It read 0/4 on the
Forge row, and the reason matters more than the number.**

qwen3:8b cited `26 CFR 1.446-1(a)(4)(i)` — the *inventory* rule, "merchandise on
hand ... shall be taken into account" — on all four problems, reasoning by
explicit "extension" to bank reconciliation. That citation resolves to **S1,
which is primary and binding**, so the tier gate never fired. The answer then
failed `grade()`'s separate relevance check and landed in `wrong_caught`.

**So the escalation guarantee is conditional on the brain citing the keyed
source.** The tier gate is keyed to the source the brain *cites*, not to the
subject of the question. A brain that miscites into the primary source escapes
the secondary-source protection entirely. "A problem keyed to a secondary source
can only grade escalated" is false as stated; it holds only for a brain that
cites the source the problem turns on.

### And those four would have been served

`grade()` and `serve()` share `_check()` deliberately — but `grade()` applies one
gate that `serve()` does not, and it is the gate that caught the Forge row:

```
passage.citation != problem.citation   ->   citation_does_not_support
```

That check needs the answer key. **Production does not have one.** Verified
directly against the engine on this desk's CB1, with the Forge's own answer:

```
GRADE -> WRONG_CAUGHT, citation_does_not_support
SERVE -> Served(position='a reconciling item',
                citation='26 CFR 1.446-1(a)(4)(i)',
                tier='primary', checked='2026-09-05')
```

An accounting conclusion resting on an inventory rule **leaves the desk, stamped
`primary`**, and the caller is told the authority is binding. Nothing in the
scoreboard's `wrong_caught` column tells you this: on the Forge row, `wrong_caught
4` means "caught by the answer key", not "would have been refused".

**This makes `wrongly_absorbed = 0` weaker than it looks.** That outcome is
defined as an answer that was wrong, that the engine could not fault, and that
would have reached a client. By that definition the Forge row scored **four**,
and they are recorded as `wrong_caught` only because the grader held a key the
production path never sees. Reported, not edited — `FORGE-RUN.md` is explicit
that a problem found here is a finding, not something to fix in `engine.py`.

---

## Baselines, beside the result and not below it

- A desk that **escalates every question without reading anything** scores
  **4 of 4 escalated and 4 of 4 escalated-by-desk** — the ceiling on both counts,
  reached by refusing to think. Both rows scored 0 on the second. This run can
  show a desk is **not reckless**; it cannot show it is **good**.
- Answering `a reconciling item, no entry in the books` every time agrees with
  **2 of 4 conclusions (50%)**, and through the engine scores **0 correct**,
  because a constant answer cites nothing.
- Citing `IRS Pub. 583 (12/2024), "Reconciling the checking account"` every time
  matches **4 of 4 citations (100%)** — there are four problems and one keyed
  passage, so the citation column here is not a retrieval measurement at all.

## POS1 was UNRATIFIED at the time of this run

Read from engine state, not from prose: `Desk.position("POS1")` returns `None`.
The entry in `positions/POSITIONS.md` carries no `Ratified` field, so the desk
held **no ratified position** and every problem escalated by construction. When
POS1 is ratified, three of the four problems have a servable answer,
always-escalating scores zero, and the same run measures something else entirely.

## The desk's two stored sources are tax sources for an accounting question

S1 is Treasury Regulation 1.446-1; S2 is IRS Publication 583. The subject —
which side of a bank reconciliation an item belongs on — is an **accounting**
convention. The literature that governs is FASB ASC, which is `human_only` by
licence, and every other accounting-side source (fasab.gov,
tfm.fiscal.treasury.gov, ffiec.gov, pcaobus.org, gao.gov) is refused by this
environment's network policy. The two stored sources are what can be **reached**,
not what governs. That gap is why POS1 exists, and this run does not close it.

## The unsupported queue

| | filed | finer path inside a rule the desk holds | reaching outside it |
|---|---|---|---|
| qwen3:8b (Forge) | 4 | 4 | 0 |
| frontier | 4 | 0 | 4 |

Nothing is subtracted: every entry is filed, refused, and never served. The two
rows split in opposite directions — the Forge's four are all near misses inside
S1, which is consistent with it never leaving the primary source; the frontier's
four all reach outside the record, which is the correct shape for this desk,
whose governing literature it does not hold.

## Denominator and comparability

**4.** Not 16, not 21. Nothing here is comparable to either fixed-assets run on
any axis. One changed answer moves every rate by 25 points. `AUTHORITY SHOWN: 47
stored paragraphs as 'index', for 4 problems.`

## NOT CHECKED

See `NOT-CHECKED.txt`, committed beside this file and reproduced in
`SCOREBOARD.txt`. It is part of the record, not an appendix to it.

---

**What the split means.** A desk that escalates everything and a desk that knows
when it is out of authority are indistinguishable on this scoreboard, and the one
number that could have told them apart — escalated by the desk — is zero on both
rows, so this run shows the mechanism is not reckless and shows nothing about
whether it is good.
