# Arena probe with the schema attached: the cost, explained to the cent — 12 September 2026

FORGE.md §1 of the 08:52Z orders, at HEAD `dcafe74c`. One call, 6.6 s, exit 0,
`ANTHROPIC_API_KEY` unset.

**Sequencing note:** FORGE.md says "after the merge and your `git pull
--rebase`". The merge has not happened yet — PR #359 is green but its tip keeps
moving, and the firm's standing instruction is to merge when the branch is
quiet. The code this needs was already on the branch, and the measurement does
not depend on the merge, so it was run now rather than held. (Also, per the
branch rules, the pull was a fast-forward, not a rebase.)

```
python tools/probe_sdk.py --match ember-7-830ff8da
```

## The two answers FORGE.md asked for

**`iterations` has exactly one entry.** Not a multi-iteration call.

**The first two prices do not both agree with the third — one does, exactly,
and the other no longer produces a price at all.**

- sum of `model_usage` `costUSD` = **$0.052523**
- `total_cost_usd` = **$0.052523** — identical, to the cent
- the repo's rate table = **no price**: it printed
  `no rates for claude-haiku-4-5-20251001+claude-opus-5`

## Output, verbatim

```
asked for model: opus | effort: low
replaying the prompt of round 1 / dask from ember-7-830ff8da
schema attached: True | prompt characters: 10800
latency_ms: 6360
subtype: "success"
is_error: false
num_turns: 2
duration_ms: 4429
duration_api_ms: 5069
stop_reason: "tool_use"
total_cost_usd: 0.052523
usage: {"input_tokens": 2, "cache_creation_input_tokens": 3945, "cache_read_input_tokens": 2060, "output_tokens": 342, "output_tokens_details": {"thinking_tokens": 0}, "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0}, "service_tier": "standard", "cache_creation": {"ephemeral_1h_input_tokens": 3945, "ephemeral_5m_input_tokens": 0}, "inference_geo": "not_available", "iterations": [{"input_tokens": 2, "output_tokens": 342, "cache_read_input_tokens": 2060, "cache_creation_input_tokens": 3945, "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 3945}, "type": "message"}], "speed": "standard"}
model_usage: {"claude-haiku-4-5-20251001": {"inputTokens": 3403, "outputTokens": 16, "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0, "webSearchRequests": 0, "costUSD": 0.003483, "contextWindow": 200000, "maxOutputTokens": 32000, "thinkingTokens": 0, "canonicalModel": "claude-haiku-4-5", "provider": "firstParty", "costBasis": "list"}, "claude-opus-5": {"inputTokens": 2, "outputTokens": 342, "cacheReadInputTokens": 2060, "cacheCreationInputTokens": 3945, "webSearchRequests": 0, "costUSD": 0.04904, "contextWindow": 1000000, "maxOutputTokens": 64000, "thinkingTokens": 0, "canonicalModel": "claude-opus-5", "provider": "firstParty", "costBasis": "list"}}
errors: null
result characters: 416 | structured_output: True
ledger would record: in 3405, cached 2060, wrote 3945, out 358, model claude-haiku-4-5-20251001+claude-opus-5
at the repo's rate table: no rates for claude-haiku-4-5-20251001+claude-opus-5 | sum of model_usage costUSD: $0.052523 | total_cost_usd: 0.052523
```

## Where the missing money was — two things, both now measured

The 5.5× gap reported in `runs/20260912T083032Z-sdk-probe.md` was not one
effect. It is two, and together they reconcile exactly.

**1. A second model is billed on every arena call.** `model_usage` has two
keys. Alongside Opus there is `claude-haiku-4-5-20251001`: 3,403 input, 16
output, `costUSD` $0.003483. Checked against Haiku 4.5 list rates ($1/M in,
$5/M out):

```
3,403 × $1/1M  = $0.003403
   16 × $5/1M  = $0.000080
                 ---------
                 $0.003483   ← matches its costUSD exactly
```

That is the CLI's own internal work, not the arena's prompt — the arena
compiles one prompt and sends it to one model. It is ~6.6% of this call's cost.
It is also most of what I mis-attributed earlier to "~8,600 uncached input
tokens in the arena prompt": 3,403 of those tokens are Haiku's, not the
contestant's.

**2. The rest is cache *writes*, at the one-hour rate.** `cache_creation` is
`{"ephemeral_1h_input_tokens": 3945, "ephemeral_5m_input_tokens": 0}`. A
one-hour cache write is billed at **2× base input**, not the 1.25× of a
five-minute write. On Opus ($5/M in, $25/M out, cache read a tenth):

```
    2 × $5/1M      = $0.000010   uncached input
3,945 × $10/1M     = $0.039450   cache WRITE at the 1h rate (2× input)
2,060 × $0.50/1M   = $0.001030   cache read
  342 × $25/1M     = $0.008550   output
                     ---------
                     $0.049040   ← matches Opus's costUSD exactly
```

And $0.049040 + $0.003483 = **$0.052523** = `total_cost_usd`. The cost is now
explained to the cent, with nothing left over.

**The single largest line is the cache write: $0.0395 of $0.0525, 75% of the
call.** Every contestant call writes a fresh 3,945-token 1-hour cache entry and
reads back only 2,060. If each of the eight contestants writes its own cache
every round, the arena is paying the premium write rate continuously and
recovering a fraction of it on reads. Whether that is avoidable — a shared
prefix across contestants, a 5-minute TTL at 1.25× instead of 1h at 2×, or
`cache_control` left off entirely — is a question for the cloud, whose code
this is. It is the biggest single lever on cost in the whole ledger.

## A defect the fix introduced

The adapter now records the model as the **concatenation** of every key in
`model_usage`: `claude-haiku-4-5-20251001+claude-opus-5`. The rate table is
keyed by single model id, so it can never match that string. The probe's own
output says so: `no rates for claude-haiku-4-5-20251001+claude-opus-5`. Before
the fix the table missed because the alias `opus` wasn't a key; now it misses
because the key is a compound. The table-priced cross-check is therefore dead
for every `agent_sdk` row, which is the only route in use.

Not fixed here — `code/arena` is the cloud's. Suggestions, in the order I'd
take them: price each `model_usage` entry against its own rates and sum;
record the models as a list rather than a joined string; add
`claude-haiku-4-5` and a cache-write rate (2× input for 1h, 1.25× for 5m) to
`RATES`, since without a write rate the table cannot reproduce 75% of a call's
cost even with the right model key.

## Not changed

No code edited. Key unset, nothing printed or committed resembling one.
`KEY.json` not opened.
