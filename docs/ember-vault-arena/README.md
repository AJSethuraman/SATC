# Ember Vault Arena (staged)

Eight player-written brains on one themed adventure, streamed live. The model
decides, deterministic code adjudicates.

**This folder is staged for migration** to its own private repository,
`ember-vault-arena`, which a session cannot create (GitHub App: 403). It lifts
out whole. It is not SATC practice-ops code and the practice's convictions apply
to it only by explicit ruling — see *Rulings by project* in `canon/CONVICTIONS.md`.

| File | What it is |
|---|---|
| `PRD.md` | The v1 spec. Sole authority; supersedes everything under `code/docs/`. |
| `LOG.md` | The running log: decisions, roadmap, deferred items, what is open. |
| `code/` | July 2026 engine, staged verbatim from commit `7252fa98` minus five generated demo outputs. Start here; do not start from a blank page. |

## Run July's tests

```bash
cd docs/ember-vault-arena/code
python3 -m unittest discover -s tests
```

62 tests, about 17 s, Python 3.11, standard library only. Ran green here on
11 September 2026.

## Regenerate the July demo outputs

The five generated files (`demo/summary.json`, `demo/seed_scan.json`,
`demo/viewer.html`, `demo/story.html`, `demo/arena.html`) were dropped from the
staging copy. `code/demo/build_summary.py`, `build_viewer.py`, `build_story.py`,
`build_arena.py` and `scan_seeds.py` rebuild them from a match in the database
(`python3 run.py demo --seed 52`, then the builders).

## What is built (12 September 2026, after PR #359)

M0 and M1 are done. M2's harness is built and **has run on the model**: the
gate pack `code/gate/20260912-034624-agent_sdk` exists (136 of 136 calls
answered) and is **unscored**, because the firm has deferred naming the two
readers. By the PRD's own line, nothing from M3 on starts until the gate has
been read. Suite: **101 tests**, all green here and in CI.

| Piece | Where | Proven by |
|---|---|---|
| Output contract `agent-action-1.0` and brain manifest v1 | `code/arena/models.py`, pinned in `code/schemas/` | `tests/test_contract.py` (pinned == generated) |
| Brain template and loader, refusals naming the section | `code/brains/TEMPLATE.md`, `code/arena/brains.py` | loader tests; the eight house brains load |
| Private note round-trip, say/whisper/silent routing, `give`, panic vs network with one transport retry | `code/arena/engine.py`, `rules.py`, `storage.py`, `memory.py` | seams 1, 3, 4; three mutation cuts went red |
| The call ledger: uncached, cached, written (by TTL) and output tokens, the billed model, the per-model breakdown, cost priced three ways | `code/arena/cli.py`, `providers.py`, `storage.py` | `tests/test_ledger.py`; the forge's probe numbers reconcile to the cent |
| Adapters: `agent_sdk` (subscription) and `anthropic` (API key), lazily imported | `code/arena/providers.py` | seam 4 through fakes shaped to the real SDK messages; no credential in any export |
| Gate harness and scorer; the key written beside the pack, off the branch | `code/tools/gate.py`, `code/tools/score_gate.py` | `tests/test_gate.py`: no house name or id reaches a reader |
| SDK probe: one call, raw accounting, a stored arena prompt replayed with the schema | `code/tools/probe_sdk.py` | run on the forge, `runs/*sdk-probe*.md` |
| Eight house brains to the template | `code/brains/house/` | loaded; each build used twice |
| Golden replay, verified without a model on every PR | `code/tests/golden/seed52.json` | `tests/test_golden.py`; CI matrix |

## What has run on the firm's machine (`runs/`)

All on the subscription route, no API key set, through the hands session
described in `FORGE.md`:

- Smoke tests, one round, 8 of 8 answered, three times (11 Sep; 12 Sep on
  the token fix; 12 Sep on the billing fix).
- **The gate**, three seeds × six rounds, 136 of 136, 5 min 58 s.
- **A full match**, `--rounds 48`, 106 of 106, 4 min 56 s, **won at round 16**
  by Crown extraction; `--rounds` is a ceiling.
- Two probes that explain a contestant call's cost to the cent: about 75% is
  a one-hour cache write of the whole prompt at 2× input, about 7% a Haiku
  helper call the CLI makes on its own. $0.05–0.10 a call at API rates;
  nothing charged on the subscription.

## What waits on the firm (the docket)

- **The two blind readers**, deferred. Until they exist the gate is unscored
  and M3 is shut; or the firm changes the PRD's rule.
- **M4's first design decision:** a match can end at round 16 on July's
  world; the show promises about an hour. A larger world, or a rule that an
  extraction does not end the match.
- The private repository `ember-vault-arena` (a session cannot create it).
- Who the eight players are.

## Run the tests

```bash
cd docs/ember-vault-arena/code
python3 -m pytest -q
```

101 tests, about 17 s, Python 3.11+, standard library only.

## Next step

Read `PRD.md` §9 and the newest entries in `LOG.md`. The hands session's
orders are in `FORGE.md`. Nothing in M3–M5 starts until the gate has been
read, or the firm rules otherwise.
