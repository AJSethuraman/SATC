# PRD: Quarterly Estimated-Tax (1040-ES) Payment Reminders

> Scope: a feature inside `satc_system`. The bar: an agent could build this with
> zero follow-up questions.

**Status:** Draft · **Owner:** Arjun Sethuraman · **Last updated:** 2026-07-04

---

## 1. Problem

Clients who owe **federal quarterly estimated taxes (Form 1040-ES)** miss
payment deadlines, which triggers IRS underpayment penalties and awkward
client conversations. Today the owner has no single place to see *which* clients
owe an estimate, *how much*, and *by when* — it lives in memory, Drake, and
scattered notes. There are four federal deadlines a year (roughly Apr 15, Jun 15,
Sep 15, Jan 15), and each is easy to let slip. Drake computes the voucher amounts
but does not chase the calendar for the owner.

## 2. Solution

An **owner-facing** worklist inside the SATC app that shows every unpaid federal
estimate coming due — sorted by due date, with overdue and due-soon flags — and
lets the owner generate a **draft** reminder email per client (never auto-sent).
SATC pre-fills a safe-harbor suggestion for each amount, which the owner confirms
or overwrites with Drake's actual 1040-ES voucher figures. **Drake stays the
computation authority; SATC tracks and reminds.**

## 3. Goals & Non-Goals

**Goals**
- One screen showing all unpaid federal estimates across clients, by due date.
- Clear overdue (red) / due-soon-within-21-days (amber) / upcoming status.
- Per-client draft reminder email in SATC voice — reviewed and sent by the owner.
- Safe-harbor pre-fill the owner can accept or override with Drake figures.
- Record a payment (mark a quarter paid) so it drops off the worklist.

**Non-Goals / Out of scope**
- **No auto-send** of any email; **no background/scheduled jobs** (the app is
  local and only runs when open).
- **No state estimates** (OH/MI/MA) in v1 — federal only.
- **No business-entity estimates** (1120-S/1065/1120) — individuals only.
- **SATC does not compute the authoritative amount** — it suggests; Drake owns
  the number.
- No payment processing, no e-file, no IRS integration.
- No importing estimate amounts directly from Drake files in v1 (owner enters/
  confirms them). *(See Open Questions.)*

## 4. User Stories

1. As the owner, I want to see every client with an unpaid federal estimate
   sorted by due date, so that I never miss a deadline.
2. As the owner, I want overdue quarters flagged red and quarters due within 21
   days flagged amber, so that I can triage at a glance.
3. As the owner, I want to flag a client as a federal estimate-payer for a tax
   year, so that SATC creates their four quarterly rows.
4. As the owner, I want each quarterly amount pre-filled with a safe-harbor
   suggestion, so that I have a sensible starting number.
5. As the owner, I want to override the pre-filled amount with Drake's actual
   1040-ES voucher figure, so that the reminder matches the system of record.
6. As the owner, I want to generate a draft reminder email for a client showing
   the amount, due date, and how to pay (IRS Direct Pay), so that I can review
   and send it myself.
7. As the owner, I want to record that a quarter was paid, so that it drops off
   the worklist and stops reminding me.
8. As the owner, I want due dates that respect weekend/holiday shifts, so that
   the dates SATC shows match the real IRS deadlines.

## 5. Requirements

1. [P0] A client can be flagged as a **federal estimate-payer for a tax year**;
   flagging creates four `estimate_payments` rows (periods Q1–Q4, jurisdiction
   `US`) for that client/year with `paid_date = None`.
2. [P0] Each quarterly amount defaults to a **safe-harbor suggestion** and is
   **editable** by the owner.
3. [P0] A **worklist view** lists all `estimate_payments` rows where
   `jurisdiction == "US"` and `paid_date is None`, sorted ascending by due date,
   each tagged **overdue** (due date < today), **due-soon** (0–21 days out), or
   **upcoming**.
4. [P0] **Recording a payment** sets `paid_date` on a row; it then leaves the
   worklist.
5. [P0] A **draft reminder email** can be generated per client/quarter, rendered
   in SATC voice with amount, due date, and IRS Direct Pay instructions, returned
   as a draft (viewable + `.eml`/Outlook), **never transmitted** — mirroring the
   existing `delivery_email` flow.
6. [P0] **Due dates** are read from `configs/crosswalk/federal/<year>.yaml`, with
   an IRS source citation, and shift to the **next business day** when the
   statutory date falls on a weekend or federal holiday.
7. [P1] Safe-harbor uses **110%** of prior-year total tax when prior-year AGI
   > $150,000 (> $75,000 MFS), otherwise **100%**, divided into four equal
   quarters (rounded per voucher convention).
8. [P1] The worklist shows, per row: client name, quarter, amount, due date,
   status, and buttons to *record payment* and *draft reminder*.
9. [P2] A per-year summary count (e.g. "3 overdue, 5 due soon") at the top.

## 6. Implementation Decisions

- **New pure-logic module `satc.estimates`** (no Flask, no I/O) holding the
  testable core:
  - `safe_harbor_quarterly(prior_year_total_tax: Decimal, prior_year_agi:
    Decimal, filing_status: str) -> Decimal` — applies the 110%/100% rule and
    divides by 4.
  - `federal_due_dates(tax_year: int, holidays) -> dict[str, date]` — maps
    `Q1..Q4` to the statutory dates from the crosswalk, applying the
    weekend/holiday → next-business-day shift.
  - `build_worklist(mart, tax_year, today, window_days=21) ->
    list[WorklistItem]` — selects unpaid `US` estimate rows, attaches due date +
    status (`overdue`/`due_soon`/`upcoming`), sorted by due date.
  - `WorklistItem` dataclass: `client_id, client_name, period, amount, due_date,
    status`.
- **Data model:** reuse the existing `EstimatePayment` / `estimate_payments`
  table as-is (`payment_id, client_id, tax_year, jurisdiction, period, amount,
  paid_date, provenance`). `paid_date is None` == still owed. **No schema
  migration** expected. Due date is *derived* (not stored) from `period` +
  `tax_year` via `satc.estimates.federal_due_dates`.
- **Crosswalk addition:** add an `estimated_tax` block to
  `configs/crosswalk/federal/<year>.yaml` — the four statutory dates and the
  safe-harbor thresholds/percentages, each with an IRS citation, following the
  existing `parameters:` + `citation:` convention.
- **Flask blueprint `estimates_bp`** registered in `satc.app.server.create_app`
  alongside `intake_bp`/`workflow_bp`/`withholding_bp`, following the
  `intake_views.py` blueprint pattern. Routes (behavioral, not final paths):
  - `GET /estimates` — the worklist.
  - `POST /estimates/enroll` — flag a client/year as an estimate-payer (creates
    the four rows with safe-harbor defaults).
  - `POST /estimates/<payment_id>/amount` — edit an amount (Drake override).
  - `POST /estimates/<payment_id>/paid` — record payment (set `paid_date`).
  - `GET  /estimates/<payment_id>/email` — render the draft reminder (+ `.eml`).
- **Email rendering** reuses the comms/template approach in `configs/comms/`
  (add an `estimate_reminder.txt` template with merge fields) and the existing
  draft/`.eml` mechanism — no SMTP, no send path.
- **Prior-year tax lookup:** safe-harbor reads prior-year total tax and AGI from
  the mart's prior-year 1040 `ReturnRecord.line_items` by line code. *(Exact line
  codes to confirm — see Open Questions.)*

## 7. Testing Decisions

- **Primary seam: `satc.estimates` pure functions**, tested in
  `tests/test_estimates.py`. A good test proves:
  - safe-harbor math (100% vs 110% threshold, MFS $75k, quarter rounding) against
    hand-worked examples;
  - `federal_due_dates` shifts weekend/holiday dates to the next business day and
    matches known IRS dates for a couple of tax years;
  - `build_worklist` selects only unpaid `US` rows, computes `overdue`/`due_soon`/
    `upcoming` correctly around the 21-day boundary, and sorts by due date.
- **Secondary seam: Flask routes** via the app test client, mirroring
  `tests/test_app_intake_flow.py`: enrolling creates four rows; recording payment
  removes a row from the worklist; the draft-email route returns the amount + due
  date and **does not send**.
- Expected values come from **independent hand calculations / cited IRS dates**,
  not by re-running the code's own formula.

### Data handling (PII / financials)

- **Real client names** appear in the owner-facing worklist and in the draft
  email (which is addressed to that client) — appropriate, matches
  `delivery_email`.
- **Masked/last-4 identifiers only** in any log line, exported artifact, or
  doc/comms repository entry — per the codebase's hard no-PII-in-artifacts rule;
  the build's validation tests must still pass.
- **Amounts are financial, not PII** — never masked.
- Fixtures use **synthetic** clients only — no real taxpayer data.

## 8. Success Metrics

- The owner can, in one screen, see 100% of unpaid federal estimates with correct
  due dates and statuses.
- Zero auto-sent emails (every reminder is a reviewed draft).
- No estimate math disagreement with Drake after the owner confirms amounts.

## 9. Milestones / Rollout

- **M1 (MVP):** `satc.estimates` module + crosswalk `estimated_tax` block +
  worklist view + enroll/edit/record-paid + draft email, federal/individual only,
  with tests at both seams.

## 10. Risks & Open Questions

- **Open question:** the exact `line_code`(s) in the mart's 1040 `LineItem` facts
  that represent **prior-year total tax** and **AGI** for safe-harbor. Confirm
  against `configs/line_sheets/` before implementing the lookup; if unavailable
  for a client, fall back to owner-entered amounts (skip the pre-fill).
- **Open question:** whether to seed amounts from a Drake file later (deferred;
  v1 is owner-entered/confirmed).
- **Risk:** federal holiday calendar (e.g. Emancipation Day shifting Apr 15)
  affects due dates — encode the holidays used and cite them.
- **Risk:** safe-harbor is a *suggestion only*; the UI must make clear the owner
  must confirm against Drake, so SATC is never mistaken for the authority.

## 11. Done Criteria

- [ ] `satc.estimates` module implements safe-harbor, due-date derivation, and
      worklist selection; `tests/test_estimates.py` passes.
- [ ] `estimated_tax` block added to the federal crosswalk with IRS citations.
- [ ] `estimates_bp` registered; worklist, enroll, edit-amount, record-paid, and
      draft-email routes work; route tests pass (mirroring intake-flow tests).
- [ ] Draft reminder renders amount/due date/pay instructions and **never sends**.
- [ ] No real PII in logs/exports; masked-artifact validation still passes.
- [ ] Verified by running the app on synthetic estimate-payer clients: worklist
      shows correct statuses and a draft email renders.
