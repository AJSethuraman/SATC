# What a mid-year withholding review should cost

**Written 7 September 2026**, because the firm answered the fee question with
*"Not yet — market research is preferable."* This is that research.

It turned up something bigger than the fee it was asked about, so that is first.

---

## The finding that was not the question

**SATC's hourly rate is about 18% below what its own region charged in 2021,
before adjusting for a single year of inflation since.**

The authoritative source for this is the **National Society of Accountants
Income and Fees Survey** — a survey of what accounting practices actually
charge, broken out by census district, which is the closest thing the
profession has to a published price list. Ohio sits in **East North Central**
(Ohio, Indiana, Illinois, Michigan, Wisconsin).

| Service | E.N. Central, 2020–21 | Same, in 2026 dollars | National, 2020–21 | In 2026 dollars |
|---|---|---|---|---|
| Federal/state tax return work | $148.15 | **$182.57** | $179.71 | $221.46 |
| Estate / tax services | $153.84 | $189.58 | $174.29 | $214.78 |
| Financial planning | $150.87 | $185.92 | $170.43 | $210.02 |

*Source: NSA 2020–2021 Income and Fees of Accountants and Tax Preparers in
Public Practice, "NATIONAL: Client Services — Average Hourly Fees", Census
District rows. Converted using cumulative CPI-U inflation of **23.23%** from
2021 to 2026.*

**SATC's `basis.rate` in `fee-schedule.yaml` is $150.00.**

That is **$32.57 an hour below regional par**, and the coincidence is worth
naming: $150 is almost exactly the *2021* regional average of $148.15. The rate
looks like it was set against a correct benchmark and then never moved.

**What this is not.** It is not an argument that the rate is wrong — a firm can
price below its region deliberately, and this one may be doing so. It is that
the rate currently prices five years of inflation at zero, and nothing in the
repository records that as a decision. **This is the firm's call and it is not
on the withholding review's critical path** — but pricing one new service
against an hourly rate that is 18% stale would bake the gap into the new thing
too.

---

## The question that was asked

### What the market charges for the nearest comparable thing

There is **no established market price for a "withholding review"**, and that is
itself a finding. The IRS calls this a **Paycheck Checkup** — its own name for
checking whether the tax coming out of your pay matches what you will owe — and
publishes it as a free self-service tool. No firm found in this search sells a
withholding review as a named standalone product.

What the market does sell, and at what price:

| What it is | Typical price | How close it is |
|---|---|---|
| A single tax planning session (quarterly or mid-year) | **$200–$500** | **Closest comparable.** Same length, same season, same kind of output |
| Year-end planning: review, projections, strategy | $500–$2,000 | Broader; several hours and a written plan |
| Ongoing advisory package, per year | $3,000–$12,000 | A different product entirely — a relationship, not a session |
| Standalone project work (entity restructuring, cost segregation) | $2,500–$15,000+ | Not comparable |

So the honest read: this sits at **the bottom of the single-session band**,
because it is narrower than a full planning session — one question, answered
with a number and a workpaper.

### Where it lands inside SATC's own schedule

A price has to make sense next to the prices beside it, and these are the ones
it will sit among:

| Existing line | Price |
|---|---|
| Hourly basis rate | $150 |
| Records sorting | $175 |
| Extension estimate | $75 |
| 1040 — essentials tier | $200 |
| 1040 — standard tier | $325 |
| Schedule C — standard | $200 |

| If the review takes | At $150/hr | At regional par ($182.57) |
|---|---|---|
| 1 hour | $150 | $183 |
| 1.25 hours | $188 | $228 |
| 1.5 hours | $225 | $274 |
| 2 hours | $300 | $365 |

---

## The recommendation

### **$225, flat.**

Four reasons, in the order they matter:

1. **It is inside the market band and at the bottom of it.** $200–$500 is what a
   single planning session goes for; $225 is the entry of that range, which is
   where a new service with no track record belongs.
2. **It is 1.5 hours at the current rate** — an honest estimate of a first one,
   and the same shape as records sorting, which the schedule already prices at
   *"a bit over an hour"*.
3. **It sits correctly against records sorting at $175.** It has to be more:
   records sorting produces a tidy file, this produces a number the client
   writes on a form and a workpaper citing the law behind every line of it.
4. **It survives the rate correction.** If the hourly rate later moves to
   regional par, $225 becomes 1.25 hours rather than 1.5 — still defensible,
   so the fee does not need revisiting the moment the rate does.

**Against $175**, which was the earlier recommendation and was made without any
of this: it is below the market band entirely, and it prices a workpaper the
same as a filing cabinet.

### What it should say it includes

Not written as client copy — that is the firm's — but as the scope the number is
priced against:

1. One paystub read, for one household.
2. A projection to year end, with every figure checked against an IRS document.
3. **The W-4 line 4c figure** — the box on the tax form marked *Extra
   withholding*, the amount an employer takes out of each remaining paycheck on
   top of the normal calculation.
4. A printable workpaper with the law cited beside each line.
5. Sold June–August, when the year has enough data and there is still time to act.

---

## What this research does not prove

* **The NSA survey is 2020–21.** It is the most recent full study published, and
  everything above adjusts it by CPI rather than by anything the profession
  itself measured. Fee inflation and general inflation are not the same series.
* **The market comparables are secondary sources** — pricing guides and firm
  websites, not a survey. They agree with each other, which is weak evidence,
  not strong.
* **No local competitor was priced.** Nothing here says what the firm across town
  charges, and that is the number that actually binds. If any of them publish a
  fee schedule, that is a better source than everything above.
* **Nobody has been asked to pay it.** The strongest possible research is
  offering it to three existing clients and seeing who says yes.
