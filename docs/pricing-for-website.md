# Pricing, for the website

**Audience: the agent working in `website/`.** This is the single source for
what SATC charges. It exists so the website work does not need to read the
pricing conversation, the fee schedule, or this repo's Python.

Everything below was signed off by the firm across four review rounds on
25 August 2026. The decision record is `docs/pricing-open-threads.md`; the
machine-readable source of truth is
`client-documents/registry/fee-schedule.yaml`. **If those and this file ever
disagree, the YAML wins** — it is what actually prices a client's estimate, and
a website that contradicts the estimate is worse than a website with no prices.

---

## 0 · Before anything else

- **`website/` deploys to the live domain on push to `main`.** Never push to
  `main`. Branch, open a draft PR, let a human merge.
- **`website/site-config.js` is hands-off** unless the firm says otherwise in
  that session. If pricing needs config, put it in a new file and say why.
- **The site carries no pricing today.** This is an addition to a public site,
  not an edit to existing copy — so the question of *whether* prices go public
  at all is the firm's, not the agent's. Do not publish prices without an
  explicit instruction naming this file.

---

## 1 · The four individual packages

One package per client. The client is in the **first** package whose test they
meet, reading down this list — the tests are written most specific first.

| Package | Price | Who it is |
|---|---|---|
| **Starter** | **$100** | Wages only. No other income document arrived, nobody is claimed as a dependent, standard deduction. A tuition form for a credit you claim for yourself is fine here. |
| **Property & Business** | **$500** | You have rentals, a farm, or a business running on actual expenses. |
| **Standard** | **$325** | You have schedules, but nothing that scales — itemising, investments, a gig business on the standard mileage rate. |
| **Essentials** | **$200** | A straightforward return with no schedules. |

Read as a ladder for a reader, that is Starter $100 → Essentials $200 →
Standard $325 → Property & Business $500. The order above is the *matching*
order, not the display order; **display them cheapest to dearest**.

**Every package includes the federal return, the first state return and the
first local return.** This sentence is load-bearing and must appear wherever a
price does — without it, the per-extra prices below look like double charging.

### What each covers

**Starter** — Federal 1040, first state, first local. One or two W-2s. A
1098-T education credit claimed for yourself.

**Essentials** — Federal 1040, first state, first local. Wages, interest and
dividends. The standard deduction.

**Standard** — everything in Essentials, plus itemised deductions, one
brokerage statement, up to two K-1s, and a gig Schedule C on standard mileage.

**Property & Business** — everything in Standard, plus **either** up to three
rental properties **or** one full Schedule C. Not both. K-1s are not part of
this allowance; they meter from Standard upward.

---

## 2 · What costs extra

Only past what the package already covers.

| Extra | Price |
|---|---|
| Each state return after the first | $50 |
| Each local return after the first | $35 |
| Each rental beyond the package's three | $45 |
| Each K-1 beyond the package's two | $15 |
| Each additional gig Schedule C | $65 |
| Each additional full Schedule C | $200 |
| Each foreign account | $50 |
| Earned income credit, with the required due diligence | $150 |
| Amended return | $250 |
| Extension with a payment estimate | $75 |

**Business returns** (1120-S, 1065, 1120) are **not priced on the website
yet** — the firm has not set those figures. Say "quoted after a
conversation", never a number.

---

## 3 · What is hourly, and why to say so

**$150 an hour**, billed to the quarter hour with a fifteen-minute minimum.

Three things are hourly because nobody can size them before seeing the work:
records that need reconciling before a return can be prepared, responding to a
notice, and anything to do with a foreign company.

The framing the firm settled on, and the one to use: **past the assumptions,
the fixed price stops applying.** Hourly is what happens *instead of* the fixed
price — it is not a surcharge added on top of it. Every estimate states its
assumptions in advance, in the client's own copy, before any work happens.

---

## 4 · Wording rules

- **An estimate is not a quote.** Anything the site produces or shows is an
  estimate of the work involved and may change if complexities appear that were
  not apparent. The engagement letter governs; the estimate accompanies it.
- **Never publish a price without what it includes.** A number alone invites
  the client to price-check a line they do not understand.
- **State the assumptions wherever a price appears**, at least in short form:
  records arrive complete, and one brokerage statement is included.
- **Do not invent legal, regulatory or assurance wording.** If a sentence would
  make a promise about compliance, accuracy or outcomes, leave a
  `[CONFIRM: ...]` and ask.
- **Minimum engagement is $100** — the Starter package is the floor. There is
  no separate minimum fee.

---

## 5 · What must NOT reach the website

All of this exists in the repo and none of it is public-facing:

- The firm's own workbook figures, and any comparison to them.
- Which numbers were the firm's and which were a recommendation — the
  "yours / my judgment / new line" tagging on the internal price sheet.
- The hourly cost basis behind any price ("$50 is twenty minutes at the
  standard rate").
- Market comparisons to other firms or to consumer tax software.
- Anything in `docs/pricing-open-threads.md`.
- Any value still carrying a `[CONFIRM:` — those are unanswered questions, not
  prices.

---

## 6 · What is not final

Publish knowing this. The **four package prices and the per-extra prices above
are signed and stable.** These are not:

- **A flat $50 per additional form** — signed by the firm, not yet built, and
  not yet in the table above. It will cover a handful of named situations (a
  home sale, cancelled debt, digital assets, marketplace insurance, an HSA, an
  early retirement withdrawal) at one price each. Leave room for it.
- **Brokerage** — signed at $45 for each statement after the first and $95 for
  one that has to be entered by hand, and not yet built.
- **A gig Schedule C inside Property & Business.** The package covers
  "everything in Standard", which includes a gig Schedule C, *and* an
  either/or that is about Schedule Cs. Those two clauses collide and the firm
  has not resolved it. Today such a client pays $65 for that Schedule C. Do
  not write website copy that promises either reading.

---

## 7 · The decision this file cannot make

Where pricing goes is the firm's call, and the two options are meaningfully
different:

**A public price page.** Anyone can read it. Sets expectations before the first
call and filters out prospects who were never going to pay $500 — and commits
the firm publicly to numbers that are two weeks old.

**An indicative estimate at the end of the intake.** The prospect answers the
questions they are already being asked and sees the package their answers put
them in. This is what the pricing engine already does, so the two would agree
by construction rather than by anyone remembering to update both. It also shows
a number only to someone who has already told you enough for it to be roughly
right.

Nothing on the site should be built until the firm has chosen. Ask.
