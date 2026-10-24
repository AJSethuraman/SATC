---
name: satc-withholding
description: >
  Project a household's full-year federal withholding and recommend a W-4
  line-4c adjustment, using the SATC desktop app's local API. Use when the user
  says estimate my withholding, am I withholding enough, will I owe or get a
  refund, do a paycheck checkup, fix my W-4, or pastes a paystub and asks what
  to do about it.
argument-hint: "[paste a paystub, or describe each job's pay & withholding]"
---

# SATC — withholding checkup

Drive SATC's withholding estimator through its local API to tell a household
whether they're on track for the year and, if not, exactly what to put on **W-4
line 4c**. Everything here is **stateless compute** — these tools read figures
and calculate; they write no ledger and touch no stored client record. There is
no irreversible action to confirm here. Your job is to be accurate and
transparent about the figures and assumptions.

## Before you start
The SATC app must be **running** on this machine (its window open). The tools
talk to it at `http://127.0.0.1:5050` by default; if the app printed a different
port on startup, set `SATC_BASE_URL` in the MCP config to match. If a tool
reports it can't reach the app, stop and tell the user to start it
(`SATC_PORT=5050 satc-app`) rather than guessing.

## Steps

1. **Read first.** Call `satc_withholding_meta` for the accepted filing
   statuses, pay frequencies, default tax year, and field guide. Don't guess
   these — assemble the payload to match.

2. **Get each job's figures.** A household estimate is one `jobs[]` entry per
   job (taxpayer + spouse, or a second job). For each you need: **whose job it
   is** (`owner`: `you` or `spouse`), pay frequency, gross pay per period,
   pre-tax retirement per period, federal tax withheld per period, and the
   year-to-date figures (taxable wages + federal tax withheld) from the latest
   stub. On a joint return, ask whose each job is -- it decides whose Social
   Security wage base it uses, and a business owner's self-employment tax can be
   off by thousands if a spouse's salary is counted against it.
   - If the user pastes a paystub, call `satc_read_paystub` on the text, then
     **show them the labeled figures and call out anything in `uncertain`** —
     confirm those before relying on them.
   - Otherwise ask for the numbers plainly. Never invent values to fill a gap.

3. **Confirm filing status and tax year.** Default the year to the meta's
   `default_tax_year` unless the user says otherwise.

4. **Estimate.** Call `satc_estimate_withholding` with the assembled payload
   (`filing_status`, `tax_year`, `jobs[]`, plus optional `other_income`,
   `deductions`, `prior_year_tax`). If it raises an error, **surface the message
   verbatim** and fix the input — don't retry blindly.

5. **Report** in plain language, numbers not raw dicts:
   - Projected **total tax** vs. projected **withholding**, and the resulting
     **balance** — a refund or an amount owed.
   - The recommended **additional per-paycheck withholding (W-4 line 4c)** and
     how many pay periods that assumes remain.
   - The result's `headline` first, then every `checks` entry with level
     `act`, then the `assumptions` list as returned — the estimator records
     what it filled in itself, so report those rather than inventing your own.
   - Any `notes` the estimator returned.
   - A year that is not on file comes back as an error. Do not retry with a
     different year; say which year is missing.

## Honesty rules
- Show parsed paystub figures before trusting them; never silently accept a
  field the reader flagged as `uncertain`.
- If a tool returns an error or an obviously impossible result, say so and where
  — don't paper over it or "average it out."
- Nothing is stored by this checkup. If the user wants the result saved to a
  client record, that's the app's job and out of scope here.
