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

## 12 September 2026, 08:20Z — after the gate

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
`docs/ember-vault-arena/code`:

```
python run.py demo --provider agent_sdk --brains brains/house --seed 7
```

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

**3. If the firm answers D3 (the two readers) in your session**, write the
names into the same `runs/` file, not into `LOG.md`; the cloud logs it.

**To carry to the firm if they are with you**, one line each:
D2, merging PR #359 is a tap now (green, mergeable) and the plugin update
follows. D4, the recommendation stands: run the twelve-round match after the
smoke re-run. D3, two readers other than the firm, since the key is on the
branch.
