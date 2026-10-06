# Ledger reprint on the new columns — 12 September 2026

FORGE.md §1 of the 08:50Z orders. No model calls: this reprints the stored
smoke match `ember-1-b6b428e5` at HEAD `4b11aadc` (the merge of the cloud's
`4593ccbc` into the forge's full-match commit).

```
python run.py ledger ember-1-b6b428e5
```

Output, verbatim:

```
round agent      validity           kind          ms     in cached  wrote   out     cost  reason
    1 dask       valid              -           7844      2   2060      0   341  $0.0525  
    1 fen        valid              -           8594      2   2060      0   484  $0.0563  
    1 grael      valid              -           8953      2   2060      0   441  $0.0538  
    1 ilse       valid              -           8750      2   2060      0   433  $0.0539  
    1 ossa       valid              -           8281      2   2060      0   416  $0.0520  
    1 perrin     valid              -           9062      2   2060      0   501  $0.0554  
    1 torvic     valid              -           8219      2   2060      0   404  $0.0518  
    1 yarrow     valid              -           8750      2   2060      0   446  $0.0540  
answered by the model: 8 of 8; network: 0; panic: 0; cost recorded: $0.4296; provider/model: agent_sdk/opus
tokens: in 16; cached 16480; cache written 0; out 3466
```

**It shows `cached 2060` on every line, as predicted.** The fix works: the
cached column is rendered, the new `wrote` column is there, and the totals line
is new. The old rows migrated on open without incident — these eight rows were
written before the column existed.

`wrote 0` on every line is the migration showing, not a measurement: these
decisions were recorded before `cache_creation_input_tokens` was captured, so
the column is empty for them rather than zero-by-observation. The first run
made *after* the fix will be the one that says whether cache creation is ever
non-zero on this route.

Nothing else changed in the stored match: same eight calls, same latencies,
same per-call costs, same total $0.4296.

**But the totals line makes the cost problem easier to see, not smaller.**
16 input tokens, 16,480 cached, 3,466 out, priced at the repo's own list rates
($5/M in, $25/M out, cache reads at a tenth) comes to:

```
(16 × 5 + 16,480 × 0.5 + 3,466 × 25) / 1,000,000 = $0.0952
```

against `$0.4296` recorded. The probe run in
`runs/20260912T083032Z-sdk-probe.md` is what explains the gap; read that one.
