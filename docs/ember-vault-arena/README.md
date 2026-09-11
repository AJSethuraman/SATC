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

## What is built (11 September 2026, overnight)

M0 and M1 are done and M2's harness is built; the gate itself has not been
run on a model. Suite: **89 tests** (July's 62 plus 27 new), all green here.

| Piece | Where | Proven by |
|---|---|---|
| Output contract `agent-action-1.0` and brain manifest v1 | `code/arena/models.py`, pinned in `code/schemas/` | `tests/test_contract.py` (pinned == generated) |
| Brain template and loader, refusals naming the section | `code/brains/TEMPLATE.md`, `code/arena/brains.py` | loader tests; the eight house brains load |
| Private note round-trip, say/whisper/silent routing, `give`, panic vs network with one transport retry, call ledger | `code/arena/engine.py`, `rules.py`, `storage.py`, `memory.py` | seams 1, 3, 4; three mutation cuts went red |
| Adapters: `agent_sdk` (subscription) and `anthropic` (API key), lazily imported | `code/arena/providers.py` | seam 4 through fakes; no credential in any export |
| Gate harness and scorer | `code/tools/gate.py`, `code/tools/score_gate.py` | one mock run, artifacts opened |
| Eight house brains to the template | `code/brains/house/` | loaded; each build used twice |

## The morning checklist (the firm)

1. **Check the subscription route works at all** from the machine that is
   logged into Claude Code:
   ```bash
   cd docs/ember-vault-arena/code
   python3 -m pip install claude-agent-sdk
   python3 run.py demo --provider agent_sdk --brains brains/house --rounds 1 --seed 1
   ```
   Eight calls, one round. The ledger line per decision says `validity`,
   `error_kind`, `latency_ms`, `cost_usd`. If every decision is
   `network_fallback`, read `fallback_reason` in the replay before anything else.
2. **Run the gate** on the house brains:
   ```bash
   python3 tools/gate.py --provider agent_sdk --brains brains/house --seeds 3 --rounds 6 --build scout
   ```
   Under a hundred and fifty calls. It prints where the pack went.
3. **Hand the pack to two readers** who wrote none of the brains. They fill
   `ANSWER_SHEET.md` and save `reader_a.json`, `reader_b.json`. Then:
   ```bash
   python3 tools/score_gate.py gate/<run> reader_a.json reader_b.json
   ```
   PASS means both readers got six of eight or better. Nothing in M3 starts
   before this has been read.
4. **If the subscription route refuses**, the same commands with
   `--provider anthropic` and `ANTHROPIC_API_KEY` set use the Messages API at
   roughly four to twelve dollars for a full match; a gate run is under a
   dollar.

## Next step

Read `PRD.md` §9. M0 is done by this folder existing. M1 is the two provider
adapters and the brain template. **M2 is the gate, and nothing in M3–M5 starts
until it has been run and read.**
