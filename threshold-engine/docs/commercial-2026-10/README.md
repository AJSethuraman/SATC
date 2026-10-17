# Evidence for COMMERCIAL-PROPOSAL.md (16 Oct 2026)

Public data only. Nothing here is the bank's.

| File | What it is |
|---|---|
| `stress_pull.py` | Pulls, from api.fdic.gov, industry sums 1991Q1–2026Q2 (the API's own aggregation) and each roster bank's rows 2005–2026, for six commercial segments. `python stress_pull.py pull.json ../../config/peers.json` (the roster is on the `threshold-engine-book` branch and on `main`) |
| `stress_stats.py` | TTM net charge-off and quarter-end nonaccrual rates, and per window the median, typical yearly move, spread of levels, worst quarter and the largest High z the history allows, using `scale.py`'s own functions. Writes `series.json`. Output: `stats-output.txt` |
| `stress_more.py` | FDIC industry against the Fed's release (FRED CSVs in `fred/`, pulled 16 Oct 2026), the big five's share of peer balances, and each bank's largest z. Output: `more-output.txt` |
| `stress_extra.py` | Past due against nonaccrual, and the count of banks whose CRE loss median since 2014 is at or below zero. Output: `extra-output.txt` |
| `research-fdic.md` | Every FDIC field probed (197), its definition and first and last dates, and the breaks visible in the data |
| `research-public.md` | The Fed release, SLOOS, SNC, FR Y-9C, macro series and paid sources, each checked against the publisher, with URLs |
| `research-sec.md` | What the 16 holding companies tag about commercial credit quality in their 2026 Q2 10-Q XBRL, and `edgar-crit-class-tracker` run against them |
| `research-breaks.md` | Definition changes, reclassifications and acquisitions since 2006, each with its primary source (Federal Register, FDIC, Fed, SEC 8-K, FDIC history) |
| `breaks-jumps.tsv` | Every bank-quarter since 2006 where a commercial category moved more than 25% (book at least $1bn on one side): 302 rows, with the merger or reporting change that explains it, or UNEXPLAINED (87) |
| `research-ffiec.md` | The FFIEC instructions quoted from the FDIC's copy (C&I and its exclusions, the >50% real estate test, NDFI, RC-L, RC-N, RI-B), the CDR bulk download and the MDRM codes not in the FDIC API, tied to KeyBank's filed report, and which form each roster bank files (17 Oct) |
| `research-crit-history.md` | How far back each of the 16 holding companies tags commercial loans by internal grade: every 10-Q and 10-K instance 2009Q1–2026Q2 (17 Oct) |
| `research-scripts/` | The research agents' scripts. Those that call SEC read the contact from the `SEC_USER_AGENT` environment variable, as SEC requires one; it is never stored |

The rates here are **as filed**: none of the tool's merger, jump or
repeated-year-to-date rules were applied, so they are indicative. Rerun on 16
Oct 2026 from these files in a clean folder: `stats-output.txt` came out the
same.
