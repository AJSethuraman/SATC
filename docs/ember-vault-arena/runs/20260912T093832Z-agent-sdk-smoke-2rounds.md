# Two rounds: does round 2 read round 1's cache write? — 12 September 2026

FORGE.md §1 of the 09:20Z orders, run after the merge. HEAD `c7559f7a`
(= the merged tip; PR #359 merged as `f44ae5f7` at 09:37:03Z). 16 calls,
35.0 s, exit 0, `ANTHROPIC_API_KEY` unset. Match `ember-1-893d938f`.

```
python run.py demo --provider agent_sdk --brains brains/house --rounds 2 --seed 1
```

## The answer: no. Every round writes afresh and reuses nothing.

`cached` is **exactly 2,060 on all sixteen calls** — identical in round 2 to
round 1 — while `wrote` *rises* in round 2 rather than collapsing:

| | round 1 `wrote` | round 2 `wrote` |
|---|---|---|
| dask | 3,944 | 4,347 |
| fen | 3,964 | 4,415 |
| grael | 3,835 | 3,914 |
| ilse | 3,866 | 4,118 |
| ossa | 3,725 | 3,655 |
| perrin | 3,842 | 4,353 |
| torvic | 3,731 | 3,719 |
| yarrow | 3,842 | 4,370 |

If round 2 were reading round 1's entry, `cached` would climb past 2,060 and
`wrote` would fall to near nothing. Neither happens. Round 2 pays the full
premium write again, on a slightly larger prompt (one round of history added).

**The 2,060 is a constant, and it is not the arena's prompt.** It is identical
across every call, every round, every match measured today — the one-round
smoke, the 48-round match, and this. A per-contestant prefix that varies by
brain cannot produce a fixed number. Whatever is being cached and re-read is
the same 2,060 tokens for all eight contestants; the arena's own ~3,800-token
prompt is what gets written fresh each time and never read back.

**So a stable per-contestant prefix would pay, and by a lot** — that is the
change FORGE.md says stays deferred until the API-key route is in use. As
things stand the arena writes ~3,900 tokens at 2× input rate on *every single
call* and reads back 2,060 that it did not write. On this run that is 63,640
tokens written against 32,960 read.

## Output, verbatim

```
Completed ember-1-893d938f
  #1 Yarrow Dunn: 1 points
  #2 Grael Thantos: 1 points
  #3 Perrin Slyke: 0 points
  #4 Ilse Corvane: 0 points
  #5 Dask Corrigan: 0 points
  #6 Torvic Ashgard: 0 points
  #7 Fen Marrowlane: 0 points
  #8 Ossa Vray: 0 points
Audit: {"valid": true, "entries": 143, "head_hash": "eb4ef43e69e63ced4cc831da080ddec0261bb9fbf43204f1e5da685cb552ef15"}
round agent      validity           kind          ms     in cached  wrote   out     cost  reason
    1 dask       valid              -           7047      2   2060   3944   325  $0.0521  
    1 fen        valid              -           9313      2   2060   3964   451  $0.0554  
    1 grael      valid              -          10266      2   2060   3835   442  $0.0538  
    1 ilse       valid              -          11391      2   2060   3866   571  $0.0574  
    1 ossa       valid              -          10656      2   2060   3725   519  $0.0545  
    1 perrin     valid              -          11438      2   2060   3842   573  $0.0572  
    1 torvic     valid              -           8985      2   2060   3731   398  $0.0516  
    1 yarrow     valid              -          11031      2   2060   3842   564  $0.0569  
    2 dask       valid              -           9531      2   2060   4347   509  $0.0610  
    2 fen        valid              -          11485      2   2060   4415   596  $0.0640  
    2 grael      valid              -           7047      2   2060   3914   378  $0.0530  
    2 ilse       valid              -           8891      2   2060   4118   477  $0.0578  
    2 ossa       valid              -           9969      2   2060   3655   489  $0.0531  
    2 perrin     valid              -           9360      2   2060   4353   497  $0.0608  
    2 torvic     valid              -           7844      2   2060   3719   440  $0.0525  
    2 yarrow     valid              -           9516      2   2060   4370   489  $0.0608  
answered by the model: 16 of 16; network: 0; panic: 0; cost recorded: $0.9019; provider/model: agent_sdk/claude-opus-5
tokens: in 32; cached 32960; cache written 63640; out 7718
```

## Your two fixes both hold

**The compound model string is gone.** The summary line reads
`agent_sdk/claude-opus-5` — the primary model by cost, as intended, not
`claude-haiku-4-5-20251001+claude-opus-5`.

**`usage_json` captures what the model column no longer shows.** Read back from
`data/arena.db` for this match:

```
round 1 dask:  in=2 cached=2060 out=325 cost=$0.052093 model=claude-opus-5
  claude-haiku-4-5-20251001: in=3403 out=17  cost=0.003488
  claude-opus-5:             in=2    out=325 write=3944 cost=0.048605
round 1 fen:   cost=$0.055432
  claude-haiku-4-5-20251001: in=3412 out=13  cost=0.003477
  claude-opus-5:             in=2    out=451 write=3964 cost=0.051955
round 1 grael: cost=$0.053809
  claude-haiku-4-5-20251001: in=3299 out=14  cost=0.003369
  claude-opus-5:             in=2    out=442 write=3835 cost=0.050440
```

$0.048605 + $0.003488 = **$0.052093**, the recorded cost exactly. Every row
reconciles again.

**One consequence worth stating plainly:** a reader of the ledger *alone* still
cannot reproduce a row's cost, because the visible columns are now Opus-only
while `cost` covers both models — dask's Opus tokens price at $0.0486 against
$0.0521 shown, and the missing $0.0035 is Haiku, visible only in `usage_json`.
That is a reasonable trade (the column would otherwise be a compound string),
but if the ledger is ever the artifact someone audits, the totals line should
probably carry a "+ helper model $X" term.

## Incidental

- `in` is 2 on every row and `in 32` in the totals, because the Opus input is
  genuinely 2 uncached tokens; Haiku's 3,403 lives in `usage_json` now.
- Cost rose round 1 → round 2 on six of eight contestants, tracking the larger
  prompt: $0.9019 for 16 calls against $0.4261 for 8 earlier today.
- Two contestants scored a point in two rounds; nothing else resolved that
  fast, as expected for a truncated match.
- Audit chain valid, 143 entries.

## Not changed

No code edited. Key unset throughout. `KEY.json` not opened.
