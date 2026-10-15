# Economic conditions tool

A separate tool from the loss thresholds. It reads public economic series and
says where each stands against its own history, for the firm and the consumer
and commercial teams. It looks only at conditions outside management's
control. Nothing from KeyBank's books goes in.

The series are the "ready to rate" group in
[`reports/Macro risk indicators for lending.md`](reports/Macro%20risk%20indicators%20for%20lending.md),
chosen by the firm on 15 Oct 2026.

## What works now (slice 1 of 3)

- **The catalog: 85 series, 83 of them rated.** Two more are inputs to
  derived readings (income per person, the 10-year Treasury). The catalog
  lives in `src/threshold_engine/macro/catalog.py`. Each entry gives the
  publisher, id, frequency, first observation, licence and known breaks, and
  the report section that put it on the list. Every id was checked on FRED or
  at the publisher on 15 Oct 2026.
- **The pull: no API key.** It downloads every series into a folder named
  for the day and never overwrites an earlier one, so every rating can name
  the release it used. A shared file is fetched once. A failure is recorded
  and the rest still pull.
- **Gaps stay gaps.** FRED's "." and BLS's dash or blank are read as
  missing, never as zero. October 2025 is missing in every BLS household
  series and in CPI. November 2025 is also missing for motor vehicle
  insurance.

Run from `threshold-engine/`:

```
python -m threshold_engine.macro list
python -m threshold_engine.macro pull --cache work/macro-cache
python -m threshold_engine.macro show --cache work/macro-cache unemployment
```

The first live pull, on 15 Oct 2026, read 85 of 85 series in 31 seconds.

## Not read yet, and why

- **NY Fed recession probability.** It is published only as an old-format
  Excel file, which needs a reader the tool does not have. The 10-year minus
  3-month spread it is built from is read.
- **NY Fed flows into delinquency.** Its reuse terms are not confirmed.
- **FHFA mortgage delinquency by state.** Not wired in yet; the national and
  loan-type figures are.

## Still to build

- **Slice 2, the ratings.** Each series gets a rating from 1 to 5 for where
  it sits in its own history. Labour series and others that matter by how
  fast they worsen also get a rating for their change. Every setting is
  required, and the tool refuses without it:
  - the cut-offs for each rating;
  - the history window;
  - the change horizon;
  - the direction of stress for the nine series the research leaves open.
- **Slice 3, the workbook.** A summary of every rating, with what drove it,
  the history window and the data release, and one sheet per series.
