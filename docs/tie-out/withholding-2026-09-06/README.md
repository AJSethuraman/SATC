# Tie-outs — the withholding estimator

Two figures proved against the IRS, on 6 September 2026. Each was executed end
to end; nothing here is confirmed by SATC's own software.

## Roster

```
Tied out: 60 of 63 checks
  DIFFERS      3   the 2025 standard deduction, superseded by P.L. 119-21
                   the $400 floor on Schedule SE, absent from the engine
                   the 15% and 20% capital-gains rates, uncited literals in code
  TIED        60   18 printed bracket bases · 1 full computed figure ·
                   5 safe-harbour parameters · 5 safe-harbour branches ·
                   5 Schedule SE constants · 8 SE computation cases ·
                   8 capital-gains breakpoints · 8 stacking cases · 2 rate checks
  COULD NOT    0
```

**Both differences are fixed on `main` the day they were found.** Neither was
findable from inside: in each case the engine's own tests work out their expected
answers from the same constants the engine reads, so the code and the tests
agreed with each other while both were wrong about the form.

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

## The Schedule SE tie-out

Enforced in `satc_system/tests/test_se_tax_matches_schedule_se.py`, which carries
every figure as a literal with its **line number on the form**.

The engine had every rate and the wage base right, and implemented lines 7
through 13 exactly — including the part most likely to be wrong, where wages
already taxed for social security eat into the room under the cap. **It did not
have line 4c**: *"Combine lines 4a and 4b. If less than $400, stop; you don't
owe self-employment tax."* On net earnings of $400 it charged $56.52.

The floor is tested **after** the 92.35% step, which is what line 4c does and is
easy to get backwards: net earnings of $430 are above $400 and still owe nothing,
because line 4a brings them to $397.10.

**One thing here is inferred, not quoted.** Form 8959 line 8 reads *"your
self-employment income from Schedule SE (Form 1040), Part I, line 6"* — a line
you never reach when 4c stops you — so the Additional Medicare Tax sees nothing
either. Form 8959's instructions do not address the "Schedule SE was not
required" case. Marked as an inference in the code and the test.

## The capital-gains tie-out

Two authorities, because the answer needs both: **Rev. Proc. 2024-40 §2.03** for
the breakpoints ($48,350 and $533,400 for a single filer), and the **Qualified
Dividends and Capital Gain Tax Worksheet** from the Form 1040 instructions for
the METHOD. The test writes that worksheet out longhand by its own line numbers,
so it is a genuinely different route to the number than the engine's seven lines
— and a test asserts it never becomes a call into the engine.

The stacking was right in all eight cases. **The rates were not cited**: `0.15`
and `0.20` were bare literals in `engine.py`, the only tax constants in the
estimator with no citation and no date, in a file whose whole discipline is that
a reader can check every figure against the law. They are in the dated table now.

**A mutant survived this one, and that was the most useful thing in it.**
Replacing `fifteen_start = max(ordinary_ti, zero_top)` with plain `ordinary_ti`
left all twenty-three tests passing. The difference only shows when ordinary
income is *below* the 0% breakpoint **and** the gain is large enough to reach
20% — a client who sells a rental or a business in a low-wage year. On $36,000 of
wages and a $600,000 gain the answer moves by **$1,405.00**. The guard was right
the whole time; the tests were too weak to say so, and now there are twenty-five.

## What these still do not prove

The Additional Medicare Tax's own thresholds, the Net Investment Income Tax, the
per-paycheck W-4 line 4c arithmetic, and the paystub reader. Each has a unit test; each of those tests works out its expected answer
from the same constants the engine uses.

State withholding is not modelled at all, and most SATC clients file an Ohio
return.
