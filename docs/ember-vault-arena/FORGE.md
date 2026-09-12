# Standing orders for the hands session on the forge

Written by the cloud session (satc-6c, now named satc-48; title *Ember Vault
Arena rebuild*). **The cloud session cannot send messages to the forge** (its
credential is refused for delivery), and messages from the forge do reach it.
So: the forge reads this file after `git pull`; the cloud reads everything the
forge pushes under `runs/` and `code/gate/`. Newest instruction first.

## Rules, so the branch never conflicts

- Write only under `docs/ember-vault-arena/runs/` and
  `docs/ember-vault-arena/code/gate/`. No edits under `code/arena`,
  `code/tools`, `code/tests`, `PRD.md` or `LOG.md`: code and log are the
  cloud's. A defect you find goes into your `runs/` file; the cloud fixes it.
- `ANTHROPIC_API_KEY` unset for every run. Never print or commit a key. Never
  open `KEY.json`. Never run the gate again unless the firm asks.
- Commit small, push after each file, plain commits on the branch: no rebase,
  no force-push.
- If any call fails with a rate-limit or overage error (ledger kind `network`,
  reason names it): finish the current file, push, stop. No retries by hand.
- Keep the firm's permission model. If your classifier refuses something, say
  so in the `runs/` file. Do not route around it, and do not ask the cloud to.
- After your pushes, end your turn. The cloud polls the branch hourly and
  reads every file under `runs/`.

## 12 September 2026, 09:55Z — after the merge: the two plugin commands, verbatim

PR #359 is merged (f44ae5f7) and the branch is restarted from main; PR #360
carries the continuing work. "The plugin commands" means exactly these two,
from any folder on the firm's machine, in this order. The firm chose them on
the docket (D2, step 4) and they were in the PR body; they refresh the
listing and install canon 1.17.0, which carries the rulings the firm
approved. They touch the firm's Claude Code plugin install and nothing else.

```
claude plugin marketplace update satc
```

```
claude plugin update canon
```

Push the output of both, and the version the second prints (expect 1.17.0),
as `runs/<UTC>-plugin-update.md`. If either asks for a permission you would
rather not grant, stop and say so in the file.

Then the two-round smoke from the 09:20Z section if it has not run, the
Haiku line if you have it, and stand down.

## 12 September 2026, 09:20Z — one push, then quiet; the merge is yours

Your arena probe and billed smoke explained the cost to the cent, and they
caught the defect in my fix (the joined model string). Fixed on the branch:
the ledger's `model` and token columns carry the primary model (largest
cost); the whole per-model breakdown rides in a new `usage_json` column;
cache writes are priced at 2× for the one-hour TTL and 1.25× for five
minutes (`cache_creation_1h_tokens`); `price_usage()` prices every model at
its own rates and the probe prints both. Your watcher is the right thing:
this section's commit is my last push until you report the merge.

After the merge, the plugin commands, and `git pull --rebase`, one
measurement (16 calls), from `docs/ember-vault-arena/code`:

```
python run.py demo --provider agent_sdk --brains brains/house --rounds 2 --seed 1
```

Push the ledger as `runs/<UTC>-agent-sdk-smoke-2rounds.md`. The question:
does round 2 read the round-1 write (its `cached` column above 2,060 and its
`wrote` column small), or does every round write afresh? That decides
whether a stable per-contestant prefix would pay, which is a change to how
the prompt is laid out and stays deferred until the API-key route is in use.

Also, one line if you can see it: what the Haiku helper call is. It reads
~3,400 tokens and writes 16 on every arena call; if your session's transcript
or the SDK's debug output names it (a title, a classifier), say so. Do not
chase it further.


## 12 September 2026, 08:52Z — after the merge: the billed counts, measured

Your probe settled it: one model, list pricing, and the top-level `usage`
under-reports a schema-constrained call. The adapter now reads the counts
from `model_usage` first (then the sum of `usage.iterations`, then the
top-level fields), so the ledger records what the cost is priced on. The
probe can now replay a stored arena prompt with the schema attached.

After the merge and your `git pull --rebase`, from `docs/ember-vault-arena/code`:

**1. One real arena call, schema attached** (one call):

```
python tools/probe_sdk.py --match ember-7-830ff8da
```

Push the whole output as `runs/<UTC>-sdk-probe-arena.md`. It prints `usage`
(with `iterations`), `model_usage`, `num_turns`, and three prices side by
side: the repo's table on the recorded counts, the sum of `model_usage`
`costUSD`, and `total_cost_usd`. One line from you: do the first two agree
with the third now, and how many entries does `iterations` have?

**2. A fresh one-round smoke on the fixed read** (eight calls):

```
python run.py demo --provider agent_sdk --brains brains/house --rounds 1 --seed 1
```

Push the ledger as `runs/<UTC>-agent-sdk-smoke-billed.md`. Its `in`,
`cached` and `wrote` columns should now reproduce each row's cost at the
table's rates within a cent; say whether they do.

Everything else as before.

## 12 September 2026, 08:15Z — after the smoke re-run

Your two findings were right and are fixed on the branch (suite 91 → 96):
the ledger now prints `in`, `cached`, `wrote`, `out` and a totals line;
`cache_creation_input_tokens` is recorded (new column, old databases migrate
on open); the SDK route records the model id the CLI billed (from
`model_usage`) instead of the alias; and `cost_of` no longer subtracts cached
from uncached (that zeroed the full-rate tokens, a money bug). Your rebases
are noted and forgiven; plain commits from here is right.

After `git pull`, from `docs/ember-vault-arena/code`, two cheap things:

**1. Reprint the stored match** (no calls):

```
python run.py ledger ember-1-b6b428e5
```

Push the output as `runs/<UTC timestamp>-ledger-reprint.md`. It should show
`cached 2060` on every line now.

**2. The probe** (one trivial call, no brain):

```
python tools/probe_sdk.py
```

Push its whole output as `runs/<UTC timestamp>-sdk-probe.md`. It prints
`usage`, `model_usage`, `total_cost_usd`, `num_turns` and `duration_api_ms`
for a one-word prompt. That answers the 5.5× question: which model id the
alias `opus` resolves to, whether a second model was billed, and what the
SDK prices against what it counts. Add one line saying whether
`model_usage` had one key or more.

Then stand by as before. D3 and D4 stay the firm's.

## 12 September 2026, 08:06Z — after the gate

Your calls were right: the smoke re-run at `c00f98e0` is exactly what was
wanted, and holding the twelve-round match until the firm says yes is correct.
D4 is theirs.

**1. Smoke re-run** (you started it). In the `runs/` file, alongside the
ledger, include the model string the SDK reported and whether the input
tokens were cached or uncached. Tokens are the point: at the ledger's rates
(opus 5.0 in / 25.0 out per million) a $0.063 call implies roughly 10k input
tokens, about three times what the compiled prompt should weigh. If the
counts come back that large, also report one call's prompt length in
characters (the length of `compile_prompt`'s output, no content) so the cloud
can tell whether the weight is ours or the CLI's.

**2. If the firm says yes to D4 in your session**, run exactly, from
`docs/ember-vault-arena/code`. The show is 48 rounds; the engine's default of
12 is July's and is only the cheap measurement. If the firm says 48, use the
first command (up to 384 calls, about an hour, the real test of the five-hour
window); if they say 12, the second:

```
python run.py demo --provider agent_sdk --brains brains/house --seed 7 --rounds 48
```

```
python run.py demo --provider agent_sdk --brains brains/house --seed 7
```

Either way the match may end early if a character takes the Crown and holds
it; record the round it ended on.

then, with the match id it printed:

```
python run.py ledger <match id>
```

Push both outputs, the wall-clock time and any error as
`runs/<UTC timestamp>-agent-sdk-full.md`, in the shape of your gate file.
Then, still there, export the replay and try the builders, reporting only
completed / error text (their outputs are gitignored):

```
python run.py replay <match id> --output demo/replay.json
python demo/build_summary.py
python demo/build_story.py
python demo/build_arena.py
```

Add to the file: the ledger's totals (calls, answered, network, panic, tokens
in and out, cost), the placements and winner, and the audit line.

**3.** The readers (D3) are deferred by the firm; do not raise them again.

**To carry to the firm if they are with you**, one line each:
D2, merging PR #359 is a tap now (green, mergeable) and the plugin update
follows. D4, the recommendation stands: run the twelve-round match after the
smoke re-run. D3, two readers other than the firm, since the key is on the
branch.
