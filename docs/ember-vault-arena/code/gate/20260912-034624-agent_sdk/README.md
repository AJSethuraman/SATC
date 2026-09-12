# Gate run 20260912-034624-agent_sdk

- provider: **agent_sdk** (model: opus)
- brains: brains/house (8 loaded), all on build **scout**
- seeds: [101, 102, 103], rounds per seed: 6
- calls: 136, answered by the model: 136 of 136
- cost recorded: $8.55 (from the call ledger)

Hand `transcripts/` and `brains/` to two readers who wrote none of the brains. Each fills in `ANSWER_SHEET.md` and saves a JSON answer file. Then:

```
python3 tools/score_gate.py gate/20260912-034624-agent_sdk reader_a.json reader_b.json
```

Do not open `KEY.json` until both sheets are in.
