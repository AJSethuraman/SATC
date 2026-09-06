# Raising an invoice, and getting paid — walked 6 September 2026

One job, done through the screens in a real Chromium against
`claude/invoice-generator-snfbjk` at `445eee1`, on a fresh database.

| File | What it is | Who it is for |
|---|---|---|
| `PROCEDURE.html` | The whole procedure as **one self-contained file** — twenty steps, every screenshot embedded, opening with the route. Forward it to somebody with no checkout and it works. | Whoever does the job |
| `PROCEDURE-invoice-and-get-paid-2026-09-06.pdf` | The same document printed. 21 pages. | Whoever wants it on paper |
| `step-*.webp` | The screenshots, in order. The control for each step is ringed; where the figures are small they are enlarged underneath. | Rebuilding the document |
| `emailed-invoice-DRAFT.pdf` | The PDF that actually arrived in the client's inbox, kept because of what is stamped on it. | Defect 1 |

**The defects are written up separately**, in `../../WALKTHROUGH-DEFECTS.md`. That
split is deliberate: merging them hands the person being trained a list of things
that are broken, and hands the person fixing them a list of clicks.

## Doing it again

The procedure is the script. Walk it after a change and every step either matches its
picture or does not — a step that no longer matches is either a defect or an
out-of-date instruction, and finding out which is the job. The harness that produced
this run is under `out/walk/` (untracked): `route.py` records the steps and rings the
controls, `client.py` captures what the client receives, and `sink.py` is a local
SMTP server so the run can reach the send step.

The exploratory pass came first and is where the defects were found; this recording
followed the same route so the pictures are of the route as walked, not as
remembered.
