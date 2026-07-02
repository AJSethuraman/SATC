# Bank Counterparty & Peer Monitor (v1)

A self-contained, macro-enabled Excel workbook (`Bank_Peer_Monitor.xlsm`) for
**credit-risk review of BANKS**: your hand-picked peer/counterparty list IS
the watchlist, keyed by FDIC CERT and pulled from the **FDIC BankFind API --
public domain, KEYLESS (no API key, no account)**. Fourth template in the
series; built to `TEMPLATE_CONTRACT.md`.

## The inversion that defines this template

Rows are **banks**, not series types. `[SERIES]` in `_config` is a
bank-agnostic 15-metric dictionary; `[PEERS]` is the flexible bank list:

```
[PEERS]   slot | cert | name | group | active     (group: peer/counterparty/self)
```

- **Add a bank**: fill a free slot row, re-run the runner. **No rebuild.**
  Find CERTs from PowerShell: `python runner.py --lookup "Frost Bank"`.
- **Remove a bank**: `active=FALSE` (or clear the row) -- the slot blanks on
  the next run (stateless clearing).
- **Capacity** is a build knob (`make_workbook.py --peer-slots N`, default
  40). Over capacity the runner **refuses with the exact rebuild command** --
  it never truncates.
- Raw anchors depend only on the **slot**; bank identity flows into every tab
  **by formula** from the `[PEERS]` cells -- a swap re-labels and re-points
  everything on recalc.

## The lanes (credit-risk framing)

| Tab | Metrics | Authority / caveat |
|-----|---------|--------------------|
| `Dashboard_AssetQuality` | Noncurrent %, quarterly NCO, 30-89 PD (computed), ALLL/loans, coverage, **Texas ratio (VARIANT)** | Texas 50/100 bands (Cassidy/RBC; StL Fed 2025); QBP Q1'26 NCO 0.59% |
| `Dashboard_Capital_Earnings` | T1 leverage, total RBC (blank for CBLR electors -- null != 0), equity/assets, ROAQ, NIM, efficiency | PCA well-cap; **CBLR floor 8% eff 7/1/2026**; QBP Q1'26 ROA 1.26%, NIM 3.31% |
| `Dashboard_Funding_Concentration` | Loans/deposits, brokered % (FDI Act sec 29 salience), CRE concentration | 2006 interagency 300% screen -- **PROXY denominator** EQ+LNATRES until the tier-1 dollar field is verified |
| `Watchlist` | Bank \| CERT \| Group \| Texas \| ALERT/WATCH flag counts \| Rank \| Status | Ranked by (ALERT count, Texas) desc, by formula; REFUSED rendered for blank/malformed CERTs |

Per-cell threshold coloring is **direction-aware** (below-is-bad metrics get
inverted heat), every column has a **peer-MEDIAN row**, and every raw field
lands in `Raw_FDIC` as the audit trail.

## Staleness is a first-class failure

Merged-away banks keep returning their final REPDTE **with no error**. Each
run compares every bank's latest REPDTE to the peer-set max: laggards are
STALE -- excluded from digest alert counts and annotated "possible
merger/closure" (the `/institutions` roster call surfaces ACTIVE/ENDEFYMD
directly). Known v1 divergence, documented in `_readme`: the **Excel median
rows still include stale banks** (Excel can't see runtime staleness); the
digest medians exclude them.

## Quick start (dev)

```bash
pip install pandas openpyxl
python3 make_workbook.py             # build the .xlsm (--peer-slots N)
python3 -m pytest tests/ -q          # 14 tests, headless/offline
python3 email_sim.py                 # acceptance: ranked table + staleness + vintage
python3 make_bundle.py               # the transmission artifact (below)
```

## Delivery to a locked-down machine

Send **`build_fdic_monitor.py`** (one pure-ASCII file). On the target
machine, from PowerShell:

```powershell
python -m pip install pandas openpyxl
python build_fdic_monitor.py
```

It locally builds the demo-populated `.xlsm` (macro embedded), a fallback
`.xlsx` + `macro.bas` (if Excel rejects the embedded project: open the
fallback, paste the macro via Alt+F11, save as `.xlsm`), `runner.py`, and
`requirements.txt`. Live refresh is **keyless**:
`python runner.py -w Bank_Peer_Monitor.xlsm` -- no env var, nothing to
configure. `control_center.py` (repo root) discovers and drives this template
automatically.

## Honest limits (v1)

- CAMELS ratings are confidential; problem-bank NAMES are never public.
- Holding-company (Y-9C) data is out -- this monitors the **bank (CERT)** level.
- Uninsured-deposit share and unrealized HTM/AOCI losses (the 2023-failure
  metrics) are **v1.1 priorities** -- field ids unverified, never silently
  approximated.
- Seeded CERTs: 628/3511/639 are verified; all others are illustrative --
  verify with `--lookup` before a live run. Demo stress banks are FICTION
  assigned by a hash.

Provenance: `COVERAGE_RESEARCH_FDIC.md` (verified API research) ->
`BUILD_SPEC_FDIC.md` (binding spec) -> this build. Decisions and verification
in `BUILD_NOTES.md`.
