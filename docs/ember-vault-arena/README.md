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

## Next step

Read `PRD.md` §9. M0 is done by this folder existing. M1 is the two provider
adapters and the brain template. **M2 is the gate, and nothing in M3–M5 starts
until it has been run and read.**
