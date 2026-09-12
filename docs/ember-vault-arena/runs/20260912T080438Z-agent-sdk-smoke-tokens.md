# Run: smoke test re-run on the fixed adapter — 12 September 2026

Run by the forge session `ajish-5a` after satc-6c's token-field fix, because
satc-6c's 11 September log entry names this as the forge's next job: re-run the
smoke test for real token counts. Same command the firm approved before. No
code was edited.

## Result

**answered by the model: 8 of 8**, 16.6 s wall clock, exit code 0, at HEAD
`c00f98e0` (includes `1c1fcc73`, the `usage` fix).

**The fix works — and the ledger still under-reports input by three orders of
magnitude.** `in` shows 2; the real prompt is about 2,062 tokens, 2,060 of them
cache reads, stored in the database and never printed.

## Command

From `docs/ember-vault-arena/code`, `ANTHROPIC_API_KEY` confirmed unset
(`ANTHROPIC_API_KEY set: False`):

```
python run.py demo --provider agent_sdk --brains brains/house --rounds 1 --seed 1
```

Start 2026-09-12T08:04:21Z, end 2026-09-12T08:04:38Z.

Full output, verbatim:

```
Completed ember-1-b6b428e5
  #1 Perrin Slyke: 0 points
  #2 Ilse Corvane: 0 points
  #3 Grael Thantos: 0 points
  #4 Dask Corrigan: 0 points
  #5 Torvic Ashgard: 0 points
  #6 Fen Marrowlane: 0 points
  #7 Yarrow Dunn: 0 points
  #8 Ossa Vray: 0 points
Audit: {"valid": true, "entries": 75, "head_hash": "bbf6375c33b094c1aee111b7f36bf5728dde366195b8b9cb6e989f7245dccb60"}
round agent      validity           kind          ms     in   out     cost  reason
    1 dask       valid              -           7844      2   341  $0.0525  
    1 fen        valid              -           8594      2   484  $0.0563  
    1 grael      valid              -           8953      2   441  $0.0538  
    1 ilse       valid              -           8750      2   433  $0.0539  
    1 ossa       valid              -           8281      2   416  $0.0520  
    1 perrin     valid              -           9062      2   501  $0.0554  
    1 torvic     valid              -           8219      2   404  $0.0518  
    1 yarrow     valid              -           8750      2   446  $0.0540  
answered by the model: 8 of 8; network: 0; panic: 0; cost recorded: $0.4296; provider/model: agent_sdk/opus
Run `python run.py serve` to watch the replay.
```

## What the database holds, which the ledger does not print

`data/arena.db`, table `decisions`, the eight rows of this match (the two rows
below them are from the 11 September run, before the fix — 0 tokens against a
real cost, the defect satc-6c fixed):

```
{'input_tokens': 2, 'output_tokens': 446, 'cached_tokens': 2060, 'cost_usd': 0.053975, 'cost_source': 'sdk_estimate'}
{'input_tokens': 2, 'output_tokens': 404, 'cached_tokens': 2060, 'cost_usd': 0.051759, 'cost_source': 'sdk_estimate'}
{'input_tokens': 2, 'output_tokens': 501, 'cached_tokens': 2060, 'cost_usd': 0.055373, 'cost_source': 'sdk_estimate'}
{'input_tokens': 2, 'output_tokens': 416, 'cached_tokens': 2060, 'cost_usd': 0.051992, 'cost_source': 'sdk_estimate'}
{'input_tokens': 2, 'output_tokens': 433, 'cached_tokens': 2060, 'cost_usd': 0.053923, 'cost_source': 'sdk_estimate'}
{'input_tokens': 2, 'output_tokens': 441, 'cached_tokens': 2060, 'cost_usd': 0.053784, 'cost_source': 'sdk_estimate'}
{'input_tokens': 2, 'output_tokens': 484, 'cached_tokens': 2060, 'cost_usd': 0.056262, 'cost_source': 'sdk_estimate'}
{'input_tokens': 2, 'output_tokens': 341, 'cached_tokens': 2060, 'cost_usd': 0.052498, 'cost_source': 'sdk_estimate'}
{'input_tokens': 0, 'output_tokens': 0, 'cached_tokens': 0, 'cost_usd': 0.073755, 'cost_source': 'sdk_estimate'}
{'input_tokens': 0, 'output_tokens': 0, 'cached_tokens': 0, 'cost_usd': 0.071404, 'cost_source': 'sdk_estimate'}
```

`cached_tokens` is 2,060 on every call — the prompt is identical across the
eight contestants but for the brain, and the SDK is serving it from cache.

**Where it goes missing:** `arena/cli.py:61` prints `d['input_tokens']` in the
`in` column and nothing else. `cached_tokens` is stored by
`arena/providers.py:977` and never rendered. So a reader of the ledger sees
`in 2` for a ~2,062-token prompt. This is not the old defect returning — the
number is now real, it is just the wrong one to show alone. Suggested (not
done, no code edited): print cached as its own column, or as `2 (+2060 cached)`.

The adapter reads `input_tokens`, `output_tokens` and `cache_read_input_tokens`.
It does **not** read `cache_creation_input_tokens`, which the comment at
`providers.py:968-972` names as a field the SDK sends. On this run that cost
nothing visible — cache reads dominate — but the first call of a cold session
is the one that pays to create the cache, and it is currently unrecorded.

## The cost figure does not agree with the token counts

Using this repo's own rate table (`providers.py:788`, `claude-opus-5` at
$5/M in and $25/M out, cache reads at a tenth of input) and its own formula
(`cost_of`, line 816), the dask call — 2 in, 341 out, 2,060 cached — works out
at:

```
(0 uncached × $5 + 2,060 × $5 × 0.1 + 341 × $25) / 1,000,000 = $0.0096
```

The SDK reported **$0.0525** for that call, about 5.5× the arithmetic. Across
the run: $0.4296 reported against roughly $0.08 by the table. Not diagnosed
here — candidates are a different rate card inside the SDK, cache *creation*
being billed on the first call and amortised into each result, or per-session
overhead. It matters because the PRD's $0.02–0.03 per call is being judged
against the reported figure: **by the token counts the run is cheaper than the
PRD assumed; by the SDK's own number it is dearer.** Both are in this file so
the next reader can pick.

Also worth noting: the same eight-call run cost $0.5821 on 11 September and
$0.4296 today. The SDK's estimate is not stable run to run.

## Unchanged from the earlier runs

- No API key set anywhere; nothing printed, nothing committed.
- Eight calls ran concurrently (7.8–9.1 s each, 16.6 s wall clock).
- All eight scored 0 points in a single round, as before.
- Match id `ember-1-b6b428e5`; `python run.py ledger ember-1-b6b428e5`
  reprints the table. `data/` stays out of source control.

## Addendum — answering FORGE.md's questions on this run

Added after reading `FORGE.md` (08:20Z orders). Three things were asked: the
model string the SDK reported, whether the input tokens were cached or
uncached, and — if the counts came back near 10k — one call's prompt length in
characters.

**The model string is `opus`.** Not a versioned id. `provider` is `agent_sdk`
and `effort` is `low`, both as recorded in `decisions`. Worth knowing for any
cross-check: `AnthropicProvider.RATES` (`providers.py:788`) is keyed
`claude-opus-5`, so a rate lookup by the string these rows actually carry finds
nothing and must map the alias first. It does not affect this run's figures —
the `agent_sdk` path takes `total_cost_usd` from the SDK and never consults
`RATES` — but it would silently skip a cost cross-check written against these rows.

**Cached, almost entirely.** Per call: 2 uncached input tokens, 2,060 cache
reads, 341–501 output. Identical 2,060 on all eight calls. The adapter does not
read `cache_creation_input_tokens`, so whatever built that cache is unrecorded.

**The counts did not come back near 10k — they came back below the prompt's own
weight, which is the more interesting answer.** Prompt sizes for the eight
calls of `ember-1-b6b428e5`, measured as the length of the stored `prompt_json`
(no content reproduced):

```
agent    prompt_json   message text   system part   in   cached   out   output chars
yarrow      11,752        10,538          2,867      2    2,060   446       661
torvic      11,503        10,337          2,867      2    2,060   404       593
perrin      11,730        10,516          2,867      2    2,060   501       680
ossa        11,478        10,296          2,867      2    2,060   416       605
ilse        11,795        10,581          2,867      2    2,060   433       675
grael       11,743        10,525          2,867      2    2,060   441       573
fen         12,053        10,803          2,867      2    2,060   484       769
dask        12,044        10,798          2,867      2    2,060   341       407
```

At the usual ~4 characters per token, ~11.7k characters of compiled prompt is
roughly **2,900–3,000 tokens**. The SDK reports **2,062** input tokens in total
(2 + 2,060). So the reported input is *smaller* than the prompt the arena
compiled, not three times larger.

What that rules in and out, stated as far as the evidence goes and no further:

- **The weight is not the CLI's wrapper.** The hypothesis behind the question
  was that a $0.063 call implies ~10k input tokens and therefore something
  outside the arena's prompt was being sent. Nothing of that size appears in
  the counts.
- **The cost is not explained by token volume at all.** 2,062 cached-in and
  ~440 out, priced by this repo's own table and formula, is ~$0.0096. The SDK
  says $0.0525. The gap is in the SDK's accounting, not in prompt weight.
- **The counts and the prompt do not reconcile either**, being ~30% short of
  the compiled prompt's estimated weight. Either the SDK reports only part of
  what it sent, or the characters-per-token ratio is well off for this content
  (JSON with many short keys runs denser than prose). Not resolved here; it
  needs a token count from a tokenizer, which this session did not run.

The prompt is the arena's own: a 2,867-character system part identical across
all eight calls, plus ~7.5k characters that differ per contestant.

## A rule I broke before I had read it

`FORGE.md` says plain commits, no rebase. I rebased three times — `d539d35f`
onto `07632a9a`, then onto `d8b5bb1b`, then `ec6b7a70` onto `e7cd42ce` — each
time replaying only my own not-yet-pushed commit onto the cloud's tip, never
rewriting anything already on the remote and never force-pushing. The last of
those happened after `FORGE.md` was pushed and before I pulled it. From here:
plain commits, and a merge rather than a rebase if the branch has moved.
