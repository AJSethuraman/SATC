# Adding a tax year

Roughly twenty minutes in January, once the IRS posts the final form. Do it in
this order; the tests are what stop a wrong figure shipping.

## 1 · Get the form and check what moved

```bash
cd schedule-c-pl
curl -sS -o /tmp/f1040sc.pdf https://www.irs.gov/pub/irs-pdf/f1040sc.pdf
python3 evidence/extract-form-labels.py /tmp/f1040sc.pdf \
  | grep -o ">[^<>]*</speak" | sed 's/^>//; s|</speak$||' | grep -v '^ *$' \
  > evidence/f1040sc-<YEAR>-labels.txt
diff evidence/f1040sc-2025-labels.txt evidence/f1040sc-<YEAR>-labels.txt
```

The labels come out of the accessibility text inside the official PDF, so they
are the form's words rather than anyone's transcription. **Read that diff.** In
2025 it was two lines, and those two lines were the 27a/27b swap.

If a line has moved, changed wording, or appeared, `src/lines.mjs` needs the
change and the reason belongs in a comment there.

## 2 · Write the year file

```bash
cp years/2025.mjs years/<YEAR>.mjs
```

Change, and change the citation with each one — a figure without a source fails
the tests, which is the point:

| Field | Where it comes from |
|---|---|
| `year`, `form.revision`, `form.retrieved` | the PDF you just downloaded |
| `otherExpensesLine` | `'27a'` or `'27b'` — from the diff above, never assumed |
| `standardMileage.periods` | the IRS notice for the year |
| `simplifiedHomeOffice` | the year's Schedule C instructions, line 30 |
| `mealsDeductiblePercent` | the year's Schedule C instructions, line 24b |

**If the rate changed mid-year, give it two periods.** The IRS did this for 2022
and again for 2026 (72.5 cents to June, 76 cents from July). The mileage
calculator then refuses rather than averaging, and tells the filer to split the
miles — which is correct, and much better than a confident wrong number.

## 3 · Register it

In `src/years.mjs`, one import and one entry in the `YEARS` list. Newest first.

## 4 · Prove it

```bash
npm test                 # fails on an uncited figure, a drifted label, a rate out of range
npm run build
python3 copy.spec.py
npm run walk             # then LOOK at walk/*.png — a green suite is not a look
```

Then open `walk/*-profit-and-loss.pdf` and the `.xlsx`. The suite reads them
back, but nobody has *seen* them until someone does.

## 5 · Consider dropping the oldest year

Three years is enough for the current year plus amended and late returns. A
fourth is maintenance with no reader. Dropping one is deleting a file and a line
— `tests/years.test.mjs` asserts the files on disk and the years on offer match,
so it will tell you if you do half the job.
