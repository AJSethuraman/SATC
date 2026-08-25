# Pricing and deadlines — what the firm already decided

**Status:** reconciliation, not a decision. Every number below is either read off
the firm's own workbook or derived from a statute. Nothing here has been written
into `client-documents/registry/fee-schedule.yaml` — that stays blank until the
principal confirms, because §9 of the authoring contract says an invented fee
figure is worse than a blank, and a *stale* figure is a kind of invented one.

**Source:** `Tax Estimate Generator (Original).xlsx`, supplied 25 August 2026.
Five sheets: a Microsoft Forms response table, a 46-question client
questionnaire, a 60-line fee schedule, a quote sheet, and an engagement letter.
It is set to **tax year 2023** (`Client Info and Q&A!C1`). The workbook is not
in this repository and should be — it is the only record of how the firm prices,
and it exists in one copy on one machine.

No client data is reproduced here. The workbook contains one client name and one
test respondent's email; neither appears in this document, per `CLAUDE.md`.

---

## 1. How the workbook prices

Per **form**, not per hour and not per client.

```
quoted = initial_price + (count - 1) × (initial_price × multiplier)
```

`multiplier` is 1 on all sixty lines but one, so the second copy of a form costs
the same as the first. The exception is Form 8582 (passive activity loss), at
5/40 — the second one costs $5 instead of $40.

Counts come from the questionnaire through `XLOOKUP`, so the quote is driven by
the client's own answers. Three lines are keyed off a *band*, not a count:

| Form | Rule in the workbook |
|---|---|
| Schedule E | `ROUNDUP(rentals / 3)` — one Schedule E covers **up to three rentals** |
| Schedule E p.2 | `ROUNDUP(K-1s / 4)` — one page covers **up to four K-1s** |
| Schedule C | `industries + 1099-industries` — one per line of business |

This matters: the repo's schedule prices rentals and K-1s **per unit**. The
firm prices them **per group**. Those are different quotes for the same client
and only one of them is the firm's.

## 2. What the workbook answers outright

| `fee-schedule.yaml` path | Workbook line | Amount | Implied hours at $150 |
|---|---|---:|---:|
| `base.1040` | Form 1040 | 170 | 1.13 |
| `base.1120S` | Form 1120S — S Corporation | 800 | 5.33 |
| `base.1065` | Form 1065 — Partnership | 800 | 5.33 |
| `base.1120` | Form 1120 — Corporation | 800 | 5.33 |
| `per_unit.state_return.amount` | State Return | 30 | 0.20 |
| `per_unit.schedule_c.amount` | Schedule C | 200 | 1.33 |
| `per_unit.rental.amount` | Schedule E — **per 3 rentals** | 130 | 0.87 |
| `per_unit.k1.amount` | Schedule E p.2 — **per 4 K-1s** | 20 | 0.13 |
| `bands.brokerage.*` | Schedule D 50 + Form 8949 5 | 55 flat | 0.37 |

`base_covers` is answered too, and by structure rather than opinion: **State
Return is its own line, counted from "How many states do you need to file a
return for?"** The base fee covers the federal return alone. That is
`federal_only`, on evidence.

## 3. What the workbook does not price at all

Seven gaps. Each is a real hole in a quote, not an oversight in the mapping.

1. **Local and municipal returns.** No line. The firm is in Solon, Ohio, where
   RITA, CCA, and school-district returns are routine, and the questionnaire
   never asks how many there are.
2. **Records cleanup / bookkeeping catch-up.** No line, though "Owners whose
   books have fallen behind" is one of four groups the website names as a fit.
3. **Form 8867**, the paid-preparer due-diligence checklist. Required whenever
   EIC, CTC, AOTC or head-of-household is claimed, and carrying a per-failure
   penalty under IRC §6695(g). Schedule EIC is priced at $100; the due diligence
   behind it is priced at nothing.
4. **Extensions.** No 4868, no 7004 — yet this repo has an Extension Notice
   template, so the firm files them.
5. **K-1s issued to owners.** The $800 entity return presumably covers them, but
   nothing says so, and a 6-owner S corp is not the same job as a 1-owner one.
6. **A minimum fee.** See §5 — this is the one that costs money.
7. **Form 1040X is priced identically to Form 1040** ($170). An amended return
   needs the original, the change, and the explanation. It is rarely the cheaper
   job.

## 4. Implied hours, and the firm's own 15-minute floor

At a $150 target rate and a 15-minute minimum increment, the floor for any
billable unit is **$37.50**.

**Thirty-two of the sixty lines are priced below $37.50.** Schedule A is $30.
Schedule B is $5. Form 8949 is $5. Form 8379, injured-spouse allocation, is $10.

That is not automatically wrong — these are increments inside a bundled quote,
not hourly billings, and a $5 line can be a rounding of "this adds almost
nothing". But it does mean the line items cannot be read as time. Either the
small ones are subsidised by the $170 base, or the schedule was built against a
lower effective rate than $150.

## 5. What the schedule actually pays per hour

Six realistic engagements, priced by the workbook's own rules, against $150/h.
The last column adds **0.75 h** per engagement for the work that happens on every
return regardless of size — intake, review, e-file, delivery, the two emails
chasing a missing 1099.

| Quote | Prep hours at $150 | Effective rate with admin | Engagement |
|---:|---:|---:|---|
| $200 | 1.33 | **$96/h** | W-2 only, one state, standard deduction |
| $290 | 1.93 | **$108/h** | W-2, itemized, one brokerage account, one state |
| $405 | 2.70 | **$117/h** | Landlord, two rentals, depreciation, one state |
| $535 | 3.57 | **$124/h** | Sole proprietor, one Schedule C, home office, one state |
| $830 | 5.53 | **$132/h** | S corporation, one state |
| $860 | 5.73 | **$133/h** | Partnership, two states |

**The schedule approaches the target as the return gets bigger and misses it
worst on the simplest work.** Every engagement carries the same fixed overhead;
only the large ones earn enough to absorb it.

Sensitivity, because the honest answer depends on times only the principal
knows:

| A bare 1040 + one state, at $200 | | An entity return at $800 | |
|---|---:|---|---:|
| 1.0 h | $200/h | 5 h | $160/h |
| 1.5 h | $133/h | 6 h | $133/h |
| 2.0 h | $100/h | 8 h | $100/h |
| 2.5 h | $80/h | 10 h | $80/h |
| 3.0 h | $67/h | 12 h | $67/h |

**Recommendation:** the highest-leverage change is not to any individual line —
it is a **minimum engagement fee**. At $150/h, the simplest return that takes two
hours end to end is a $300 job. A $300 floor pulls the bottom row of that table
up to target and leaves all fifty-nine other prices untouched. Setting one number
fixes the case the schedule gets most wrong.

The second change, if there is appetite for one, is the **local return line** —
in this county it is not an edge case.

## 6. Deadlines

The firm settings ask for a **materials deadline** per return type: the date a
client's documents must be in hand. That is a firm policy, but it hangs off a
statutory filing date, so the filing dates come first.

`_season` in this repo means the **tax year**, not the filing year — the sample
engagement letter is dated February 2027 and prepares "your 2026 income tax
returns". So `materials_deadlines["2026"]` governs returns filed in **calendar
2027**.

**Statutory filing dates for tax year 2026**, from IRC §6072 (15th day of the
third month for partnerships and S corporations, of the fourth month for
individuals and C corporations) and §7503 (a due date falling on a Saturday,
Sunday or legal holiday moves to the next business day):

| Return | Due | Weekday | §7503 shift |
|---|---|---|---|
| Form 1065, Form 1120-S | **15 March 2027** | Monday | none |
| Form 1040, Form 1120 | **15 April 2027** | Thursday | none |
| Extended 1065 / 1120-S | 15 September 2027 | Wednesday | none |
| Extended 1040 / 1120 | 15 October 2027 | Friday | none |

None of the four shift. DC Emancipation Day falls on Friday 16 April 2027 —
*after* the individual due date, so it does not move it. (In years where it
falls on the 15th, or on a weekend adjacent to it, the individual deadline moves
to the 18th; 2027 is not such a year.)

**Proposed rule for the materials deadline** — one rule to approve instead of
four dates to invent: *the statutory filing date minus four weeks, moved back to
the nearest Monday.*

| Setting | Filing date | Materials deadline under the rule |
|---|---|---|
| `s_corp_1120s` | 15 Mar 2027 | **Monday 15 February 2027** |
| `partnership_1065` | 15 Mar 2027 | **Monday 15 February 2027** |
| `individual_1040` | 15 Apr 2027 | **Monday 15 March 2027** |
| `c_corp_1120` | 15 Apr 2027 | **Monday 15 March 2027** |

Four weeks is a proposal, not a fact. Three weeks is defensible and more
aggressive; six is common for entity work. The rule is what matters, because it
regenerates every January without anyone having to remember four dates.

## 7. What else the workbook settles

- **The firm's legal name.** The client-facing quote sheet reads *"Sethuraman
  Accounting Tax and Consulting LLP"* — no commas, no ampersand. This is a
  **fourth** spelling, distinct from the three already in the repo. Four
  variants across the firm's own documents; only one is on the Ohio filing.
- **Record retention: seven years.** The engagement letter states records and
  work papers are kept for up to seven years and then destroyed. The repo's
  templates say nothing about retention.
- **Payment terms: net thirty, interest thereafter.** "Invoices are due and
  payable upon presentation of the Final Invoice. All accounts not paid within
  thirty (30) days are subject to interest charges to the extent permitted by
  state law." That is a *term*, not a *method* — `payment_instruction` still
  needs the method and the processor.
- **A contradiction to resolve.** The engagement letter says the fee "is based on
  the time required at standard billing rates plus out-of-pocket expenses". The
  fee schedule is per form, and the invoice template deliberately shows no rates.
  Both cannot describe the same engagement. Either the letter's sentence changes,
  or the schedule is a *time estimate expressed as prices* and the letter is
  right.
- **The questionnaire is 46 questions and already in production.** It gates
  properly — rental income before rental count, self-employment before industry
  count — and drives form selection through the same lookups that drive price.
  It is the closest thing the firm has to a specified interview, and it belongs
  in `client-documents/registry/interview.yaml` rather than in a spreadsheet.

---

## Open, and genuinely a human's call

1. Is $150 the target rate, or the current average to be moved off?
2. Are the 2023 prices still the 2026 prices?
3. Minimum engagement fee — yes or no, and how much?
4. Per-group or per-unit for rentals and K-1s: does the firm's rule change, or
   does the repo's schedule change to match it?
5. The seven unpriced items in §3.
6. Four weeks, or another lead time, for materials.
7. Which of the four spellings is on the Ohio filing.
