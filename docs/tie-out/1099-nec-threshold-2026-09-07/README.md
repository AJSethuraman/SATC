# Tie-out — the $2,000 1099-NEC threshold, 7 September 2026

**The deliverable is one file: [`TIE-OUT-1099-nec-threshold-2026-09-07.pdf`](TIE-OUT-1099-nec-threshold-2026-09-07.pdf).**
Every picture is embedded in it. Forward that, not this folder.

**Verdict: TIED. Difference 0.** All four claims in one bullet of
`satcllp.com/guides/business-records.html` section 05 agree with 26 U.S.C. § 6041
and the IRS Instructions for Forms 1099-MISC and 1099-NEC (Rev. 12/2026).

## What it found

Three things, none of which was the figure being proved:

1. **The page says "by January 31" and does not say the date moves.** It moved to
   2 February 2026 last season and moves to 1 February 2027 next season. The firm's
   own instruction at C001 says to state the moving rule; the same page states it for
   March 15 and not for January 31. **A decision for the firm — not applied here.**
2. **`SOURCES.md` justifies $2,000 with the IRS's paraphrase** ("tax years beginning
   after 2025") rather than the statute's effective-date rule ("payments made after
   Dec. 31, 2025"). Same answer today; different tests.
3. **`uscode.house.gov` is recorded as unfetchable in `website/HANDOFF.md` and it is
   not.** It was the single most useful source here.

## What is in this folder

| File | What it is |
|---|---|
| `TIE-OUT-…-2026-09-07.pdf` | **the deliverable** — self-contained, 21 pages, 13 embedded images |
| `TIE-OUT-…-2026-09-07.html` | the same document, images inlined as data URIs; what the PDF renders from |
| `exhibit.src.html` | the authored source, with `IMG:<name>` tokens instead of the images |
| `build.py` | inlines the captures and renders the PDF |
| `make-crops.py` | cuts the ringed row out of each capture and enlarges it 2.2× |
| `01-…` – `06-…` `.jpg` | the full-page captures, ringed in red where the figure sits |
| `0*-crop-*.png` | the enlargements, so the digits read without leaning in |

## Rebuild it

```
cd docs/tie-out/1099-nec-threshold-2026-09-07 && python make-crops.py && python build.py
```

Needs `pillow` and Chrome. The captures are the evidence and are not regenerated —
re-taking them would photograph today's version of a page rather than the one that
was read on 7 September 2026.

## Re-check the figure itself

The exhibit's § 11 has all six commands with the real values in them. The shortest:

```
curl -sS https://www.irs.gov/instructions/i1099mec | grep -o "at least \$2,000 in"
```

One match means the threshold still stands. **No match means the instructions have
been revised and the guide needs re-checking before the next filing season** — and
nothing in this repository watches for that. § 6041(h) indexes the figure from
calendar year 2027, rounded to the nearest $100.
