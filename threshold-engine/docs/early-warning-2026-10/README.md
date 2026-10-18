# Early warning signals for consumer credit (16–18 October 2026)

The analyst asked whether FICO should be a rated dimension of the consumer
book. The question widened to every public signal that might come before
card and mortgage losses, and ended with four measures built into Book 1 and
the rest set aside, each with the chart that decided it.

**`EVIDENCE.html`** (and `EVIDENCE.pdf`) is the one document: the decision
table first, then the evidence for what was kept (A), for what was set aside
(B), the kept measures as they sit in the book (C), and the data, scripts
and what was not checked (D). Every chart is drawn by the scripts in
`record/` from the data beside them.

## What was kept

| Measure | Built into the book as |
|---|---|
| 30+ to charge-off, card and other consumer (industry, peer group, KeyBank) | rated by level; `peers/flows.py` |
| Gap to peers and gap to industry on 30+ to charge-off | rated by level, no floor at zero (the book's `floor_off`) |
| Share of card accounts paying only the minimum (large banks, Philadelphia Fed) | rated by level; `peers/large_banks.py` |
| Mortgage rated on nonaccrual | the existing measure; the analyst weights it later |

Shown beside the ratings, not rated: card origination quality and banks
easing standards (2 to 3 years ahead of card losses), and other consumer
30–89 as a confirming signal for mortgage 90+.

## What was set aside

Refreshed FICO (it moves with 30–89 days past due); card balances under 660
as a rating (kept as a peer comparison); purchase volume by score; mortgage
origination terms and current LTV (economic data, Book 2); the roll steps on
their own (watch only). Section B draws each.

## Rerun

From `threshold-engine`, after the book is built (the Call Report measures
read its series files):

```
python docs/early-warning-2026-10/record/evidence.py
```

`record/README.md`-level notes are at the top of each script. The derived
data under `record/data/` (`rolls/`, `peerfico/peers.json`, `nmdb/`,
`keyhist/`) can be rebuilt with the scripts named in section D; the raw SEC
facts (14 MB) and FHFA zips (21 MB) are not kept in the repository.
