# Ten years of bank data, every value beside the page it was filed on

**5 September 2026.** Twelve banks, forty quarters, 68 fields each — **32,640
values**. Every one that was compared against a line on a Call Report appears in
one of these exhibits with a **photograph of that line**, taken from the
regulator's own copy of the filing.

**28,667 tied. 0 differed.**

## Why photographs

The firm's reason, in their words:

> i want the screenshot method used for those quarters ... like it's the only
> way i feel like i have been able to trust this sort of audit.

A software comparison proves the code agrees with a file it downloaded. It does
not let a person put a finger on the number. These do.

Each shot carries **the filing's own page header** — the bank's legal name, the
form (FFIEC 031 or 041), and the report date — directly above the row. So *same
entity, same period* is read off the picture rather than taken on trust, which
is exactly the assumption that is true right up until it is not.

## The unit is the bank-year

One document per bank per calendar year: **132 of them**, because 2016 and 2026
are partial. A bank is forty quarters and roughly 2,700 photographs, and nobody
opens that. A year is four filings, which is what somebody actually checks in a
sitting.

Every exhibit is **self-contained** — each image is embedded in the PDF, not
linked to a folder beside it — so it survives being forwarded to an auditor who
does not have this machine.

## What is in git, and what is not

The 132 exhibits total **664 MB**, which does not belong in a repository. What
is committed:

| File | What it is |
|---|---|
| `manifest.csv` | one row per exhibit: bank, year, values, ties, photographs, size |
| `TIE-OUT-17534-KeyBank-NA-2025.pdf` | one specimen, so the shape is visible without rebuilding |
| `.gitignore` | keeps the other 131 out |

Rebuild all of them in about six minutes:

```
python tools/tieout/build_deep_bank_exhibits.py
```

One at a time, if that is all you want:

```
python tools/tieout/build_deep_bank_exhibits.py 17534 2025
```

Both need the strips, which are cut from 480 facsimile PDFs. In order, from the
repository root:

```
python tools/tieout/fetch_all_facsimile_pdfs.py
python tools/tieout/deep_bank_strips.py
python tools/tieout/build_deep_bank_exhibits.py
```

## How to check a value yourself

1. Open the exhibit for the bank and year.
2. Find the field. The block shows **ours** (read out of
   `verified-data/bank-values.csv`, the file the firm opens) and **filed** (read
   off the bank's Call Report), with the difference between them.
3. Beneath them is the page. The eight-character code — an **MDRM code**, the
   Federal Reserve's permanent name for one line on the form — is in the shot,
   with the number beside it.
4. To go past the picture, open the `cdr.ffiec.gov` link under the quarter
   heading and search the page for that code. It is the regulator's own copy.

## What running it found

**`LNLSGR` cited a line the FDIC does not use.** Nine of 480 bank-quarters came
back as differences, always exactly one thousand dollars, on a balance of two
hundred billion, across three unrelated banks in six unrelated quarters. The
bank files that total twice — RC-C Part I line 12 as one rounded figure, and
RC 4.a + 4.b as two separately rounded halves. The FDIC publishes the sum of the
halves in all 480; line 12 agrees with it in 471. The values were right the
whole time. The citation was wrong, which is invisible until somebody follows
it — which is what a tie-out is.

**960 codes were not found on their filing**, out of 49,066 looked for. They are
recorded in each exhibit as not found rather than omitted, because a missing
strip and a strip nobody looked for are indistinguishable in a finished
document.

## What these do not prove

- **That the bank was right.** A value can match its filing to the dollar and
  the filing can still be wrong. This proves faithful copying and nothing past
  it.
- **Anything shaded grey is a value of exactly zero** — a category where that
  bank has no exposure. It ties, and it is the weakest form of agreement there
  is. There are 5,385 of them, and 5,348 were checked against an explicitly
  filed zero.
- **Ratios the FDIC computes have no line to photograph**, so they carry no
  picture. The lines they are computed from do.
- **Nothing here was checked by a second person.**
