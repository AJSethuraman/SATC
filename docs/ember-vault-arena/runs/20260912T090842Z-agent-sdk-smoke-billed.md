# Smoke on the fixed billing read: the columns now hold the billed tokens — 12 September 2026

FORGE.md §2 of the 08:52Z orders, at HEAD `dcafe74c`. Eight calls, 16.2 s,
exit 0, `ANTHROPIC_API_KEY` unset. Match `ember-1-60751a62`.

```
python run.py demo --provider agent_sdk --brains brains/house --rounds 1 --seed 1
```

## The answer FORGE.md asked for

**No — not at the table's rates, and the reason is not the counts.** The
recorded `in`, `cached`, `wrote` and `out` now contain everything the cost was
priced on; the table cannot turn them into that price, for two reasons that
have nothing to do with this run:

1. **`in` merges two models.** Of dask's 3,405 input tokens, 3,403 are Haiku's
   at $1/M and 2 are Opus's at $5/M. One rate over one column is wrong however
   you pick it.
2. **The table has no cache-write rate,** and the write is 75% of the call.

Split per model, with the 1-hour write at 2× input, they reproduce the cost
within a cent. Priced the table's way they are about half. Both arithmetics
are below.

## Output, verbatim

```
Completed ember-1-60751a62
  #1 Perrin Slyke: 0 points
  #2 Ilse Corvane: 0 points
  #3 Grael Thantos: 0 points
  #4 Dask Corrigan: 0 points
  #5 Torvic Ashgard: 0 points
  #6 Fen Marrowlane: 0 points
  #7 Yarrow Dunn: 0 points
  #8 Ossa Vray: 0 points
Audit: {"valid": true, "entries": 74, "head_hash": "5ca9dc478c248aeccc4bd3352f741e9ad40657afc33dd303e384c3c8ce5beaeb"}
round agent      validity           kind          ms     in cached  wrote   out     cost  reason
    1 dask       valid              -           7516   3405   2060   3945   351  $0.0524  
    1 fen        valid              -           9578   3414   2060   3963   502  $0.0563  
    1 grael      valid              -           8031   3301   2060   3835   405  $0.0525  
    1 ilse       valid              -           9031   3325   2060   3865   446  $0.0539  
    1 ossa       valid              -           8781   3209   2060   3725   446  $0.0523  
    1 perrin     valid              -           8547   3310   2060   3843   445  $0.0536  
    1 torvic     valid              -           8625   3216   2060   3727   430  $0.0520  
    1 yarrow     valid              -           8547   3312   2060   3842   426  $0.0531  
answered by the model: 8 of 8; network: 0; panic: 0; cost recorded: $0.4261; provider/model: agent_sdk/claude-haiku-4-5-20251001+claude-opus-5
tokens: in 26492; cached 16480; cache written 30745; out 3451
```

## The arithmetic, per row and in total

**dask, split per model** (Haiku $1/$5 per M; Opus $5/$25 per M, cache read a
tenth of input, 1-hour cache write 2× input — `cache_creation` was
`ephemeral_1h_input_tokens` in the probe, `ephemeral_5m` zero):

```
Haiku  3,403 in  × $1/1M   = $0.003403
Haiku     16 out × $5/1M   = $0.000080
Opus       2 in  × $5/1M   = $0.000010
Opus   3,945 wrote × $10/1M = $0.039450
Opus   2,060 cached × $0.50/1M = $0.001030
Opus     335 out × $25/1M  = $0.008375
                             ---------
                             $0.052348   vs $0.0524 recorded — within a cent
```

(The 351 in the `out` column is the two models' outputs added: ~335 Opus plus
~16 Haiku. The split is the probe's, not this run's — this ledger stores the
sum, which is the next thing worth separating.)

**The whole run, from the totals line** (in 26,492; cached 16,480; written
30,745; out 3,451 — the `in` column is essentially all Haiku, the cached and
written columns all Opus):

```
Haiku  ~26,476 in  × $1/1M    = $0.026476
Haiku     ~128 out × $5/1M    = $0.000640
Opus       ~16 in  × $5/1M    = $0.000080
Opus    30,745 wrote × $10/1M = $0.307450
Opus    16,480 cached × $0.50/1M = $0.008240
Opus    ~3,323 out × $25/1M   = $0.083075
                                ---------
                                $0.425961   vs $0.4261 recorded
```

**Priced the table's way instead** — one model, no write rate, dask's row:
3,405 × $5/M + 2,060 × $0.5/M + 351 × $25/M = **$0.0268**, against $0.0524.
Half the call missing, all of it the cache write.

## What this run adds to the probe

- **The probe's finding holds across all eight calls, not just the one it
  replayed.** Every row now shows ~3,200–3,400 `in`, exactly 2,060 `cached`,
  and 3,725–3,963 `wrote`. The Haiku overhead and the 1-hour cache write are
  per-call constants, not a one-off.
- **The cache write is the cost.** $0.3075 of this run's $0.4261 — **72%** — is
  cache creation at the 1-hour rate. Eight contestants each write their own
  ~3,800-token entry every round and read back 2,060. On the 48-round match
  (106 calls) that is roughly $5.50 of the $7.67 recorded.
- **`provider/model` is now a compound string** —
  `claude-haiku-4-5-20251001+claude-opus-5` — which is what kills the table
  lookup, as reported in `runs/20260912T090748Z-sdk-probe-arena.md`.
- Cost per call barely moved against the old read ($0.4261 now, $0.4296 on 11
  September, $0.5821 on the first run). The fix changed what is *recorded*,
  not what is spent.

## The lever, stated plainly for the cloud

If the eight contestants shared a cached prefix instead of each writing their
own, or the write used a 5-minute TTL (1.25× input) rather than one hour (2×),
the largest line in the ledger would fall by a large fraction. This session
cannot test that — `code/arena` is the cloud's — but it is one `cache_control`
decision, and it is worth more than every other cost item combined.

## Not changed

No code edited. Key unset throughout; nothing printed or committed resembling
one. `KEY.json` not opened.
