# Tie-outs — the withholding estimator

Two figures proved against the IRS, on 6 September 2026. Each was executed end
to end; nothing here is confirmed by SATC's own software.

## Roster

```
Tied out: 29 of 30 checks
  DIFFERS      1   the 2025 standard deduction was superseded by P.L. 119-21
  TIED        29   18 printed bracket bases · 1 full computed figure ·
                   5 safe-harbour parameters · 5 safe-harbour branches
  COULD NOT    0
```

The one that differs is fixed on `main` as of the same day — see
`satc_system/configs/crosswalk/federal/2025.yaml` and its `supersedes:` block.

## The exhibits

| File | What it proves |
|---|---|
| `TIE-OUT-withholding-2026-09-06.pdf` | The federal tax on a single filer with $100,000 of wages, traced from the screen to Rev. Proc. 2024-40 — **and then one step further, to the law that superseded it.** 11 pages, every image embedded. |
| `source-irs-rp2024-40-p6-rate-schedules.jpg` | Rev. Proc. 2024-40 §2.01 Tables 3 and 4, page 6, as served by irs.gov |
| `source-irs-rp2024-40-p12-standard-deduction.jpg` | §2.15, page 12 — the amounts that were superseded |
| `source-irs-obbba-2025-standard-deduction.jpg` | irs.gov, the enacted 2025 amounts, ringed |
| `source-irs-pub505-required-annual-payment.jpg` | Pub 505, *Required Annual Payment — Line 12c*: the general rule, the higher-income substitution, **and the IRS's own worked example**, ringed |
| `audit-tape-single-100k-2025.xlsx` | The workbook the figure was read out of (cell C25) |
| `build.py` | Renders the exhibit; every image embedded as a data URI |

## The safe-harbour tie-out

Not a separate PDF: it is enforced in
`satc_system/tests/test_safe_harbour_matches_pub_505.py`, which carries every
Pub 505 figure as a literal with its citation and disagrees with the crosswalk
rather than reading from it.

**The IRS publishes an answer, not just a rule**, which is the strongest source
there is. Its example — prior-year tax $42,581, prior-year AGI $180,000,
expected tax $71,253 — gives a required annual payment of **$46,839**. Our
engine returns **$46,839.10** on the same inputs. 110% × 42,581 is exactly
46,839.10; the IRS rounded to whole dollars in its prose. Same number, two
renderings, and it is written down rather than hidden behind a `round()`.

Four mutations were run against it. The one worth naming: changing `>` to `>=`
on the $150,000 test — a single character — makes a taxpayer at exactly
$150,000 of prior-year AGI pay 110% instead of 100%. Pub 505 says *"more
than"*. That test goes red.

## What these still do not prove

The capital-gains stacking, the self-employment tax, the Additional Medicare
Tax, the Net Investment Income Tax, the per-paycheck W-4 line 4c arithmetic, and
the paystub reader. Each has a unit test; each of those tests works out its
expected answer from the same constants the engine uses.

State withholding is not modelled at all, and most SATC clients file an Ohio
return.
