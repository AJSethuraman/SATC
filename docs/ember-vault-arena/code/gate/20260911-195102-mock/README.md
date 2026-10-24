# Gate run 20260911-195102-mock

- provider: **mock** (model: deterministic-ruleset-policy-0.2)
- brains: /home/user/SATC/docs/ember-vault-arena/code/brains/house (8 loaded), all on build **scout**
- seeds: [101, 102, 103], rounds per seed: 6
- calls: 142, answered by the model: 142 of 142 (a mock answers everything and proves nothing about brains)
- cost recorded: $0.00 (from the call ledger)

Hand `transcripts/` and `brains/` to two readers who wrote none of the brains. Each fills in `ANSWER_SHEET.md` and saves a JSON answer file. Then:

```
python3 tools/score_gate.py gate/20260911-195102-mock reader_a.json reader_b.json
```

Do not open `KEY.json` until both sheets are in.
