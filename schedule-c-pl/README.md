# Schedule C profit and loss

A free, no-signup tool that turns a sole trader's income and expenses into a
profit and loss statement and a Schedule C worksheet, as a PDF and a spreadsheet.
Everything happens in the browser. There is no server and no analytics, and the
build refuses to produce a page that would talk to one.

Lives at **`satcllp.com/tools/schedule-c-profit-and-loss/`**.

There is a second page beside it: **`satcllp.com/guides/schedule-c-line-by-line/`**,
a plain-English walk through the form written from the questions a real user had
with the screen in front of them. Same rules — one file, no network, no analytics.

- **`DECISIONS.md`** — why it is built this way, what was refused, and where the
  plan is wrong. Read that first (§7 is the guide page).
- **`YEAR-UPDATE.md`** — the January job.

## Layout

```
src/          the tool, as plain ES modules the browser could load unbundled
years/        one file per tax year: line 27a/27b, the mileage rate, its source
evidence/     Schedule C labels extracted from the official IRS PDFs, per year
guide/        the line-by-line guide: copy.mjs is the prose, build-guide.mjs renders it
tests/        the suite, plus walk.mjs which drives a real browser
build.mjs     generates website/tools/schedule-c-profit-and-loss/index.html
copy.spec.py  the client-facing register rules, run against the built page
```

The source lives here and the page is **generated** into `website/`, because
satcllp.com is served by Cloudflare Pages copying `website/` — and the tests,
fixtures and evidence should not sit on a public web server. The same shape as
`pricing-config.js`, and checked the same way: regenerate, fail on any drift.

## Verifying a change

```bash
cd schedule-c-pl
npm install                # fast-check, pdfjs-dist, playwright — dev only
npm test                   # 141 tests
npm run build              # writes both pages into website/
python3 copy.spec.py       # 24 checks on what a client reads
npm run walk               # drives the built page in a real browser, offline
```

`npm run check` rebuilds and fails if either committed page is not what the
source produces today. That is the one to run in CI.

The suite is worth a word, because a green suite that proves nothing is the
failure mode this repo keeps writing tenets about:

| Where | What it actually proves |
|---|---|
| `lines.test.mjs` | Every money line's wording matches the IRS PDF for that year — 52 of 55 word-for-word, 3 reworded and named. Mutation-tested three ways. |
| `engine.test.mjs` | The arithmetic, plus loss cases, empty and partial input, contradictions, and the year-to-year line swap. |
| `property.test.mjs` | 19 invariants over ~800 random returns each. It found a real `-0` bug. |
| `pdf.test.mjs` | Every figure the screen shows is in the PDF — read back by **pdf.js**, not by our own writer. |
| `xlsx.test.mjs` | Same for the spreadsheet, via **openpyxl**, including evaluating each SUM formula against the cells it names. |
| `build.test.mjs` | The shipped file makes no requests, carries no tracker, and is one file. |
| `walk.mjs` | A person fills the form in, offline, and the downloaded files hold what the screen held. 62 checks. |
| `guide.test.mjs` | The guide's line numbers are looked up per year, not typed: 27a for 2023–24, 27b for 2025, and the shipped page carries the right one. |
| `copy.spec.py` | No contract-desk verbs, no sentence over 25 words, no unexplained term of art, no promise that cannot be kept. |

`FC_RUNS=5000 npm test` runs the property tests harder.

## The things most likely to go wrong

1. **27a and 27b swap between years.** 2023 and 2024 put other expenses on 27a;
   2025 puts them on 27b. It is a per-year parameter, never a constant.
2. **Blank is not zero.** A line nobody filled in must print nothing. Several
   tests exist only to hold that line.
3. **Money is integer cents.** No float anywhere in the engine. Whole-dollar
   mode follows the 1040 rule — add the cents, round the total once.
4. **Nothing may reach the network.** The build refuses; two tests re-check the
   shipped bytes; the browser walk blocks and records every attempt.
