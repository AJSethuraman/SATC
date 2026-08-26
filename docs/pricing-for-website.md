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

One package per client, and the client gets **the cheapest one that covers
their return**. That is the engine's own rule, not a promise made in copy —
among the packages a client qualifies for, it quotes the lowest total.

| Package | Price | Who it is |
|---|---|---|
| **Starter** | **$100** | Wages only. No other income document arrived, nobody is claimed as a dependent, standard deduction. A tuition form for a credit you claim for yourself is fine here. |
| **Essentials** | **$200** | A straightforward return with no schedules. |
| **Standard** | **$325** | You have schedules — itemising, investments, rentals, a farm, a gig business on the standard mileage rate. |
| **Business** | **$500** | You run a business on actual expenses, a home office, depreciation, inventory or payroll. |

That is also the display order: **cheapest to dearest**.

> **The package names are not final.** The firm is reworking all four to sound
> more like the firm. Do not build copy, headings or URLs that assume these
> exact words. "Business" in particular is a placeholder — it replaced
> "Property & Business" on 26 August when rentals stopped being a package.

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

**Business** — everything in Standard, plus one full Schedule C: a business
on actual expenses, a home office, depreciation, inventory or employees.

**Rentals and farms are no longer a package.** This is the change that matters
most for the site, made 26 August 2026. A Schedule E is priced as a form the
way the rest of the market prices it — so a landlord is a **Standard** client
with a Schedule E beside it, not a client pushed up a rung. A landlord pays
the same whether or not they itemise, which was not true before.

---

## 2 · What costs extra

Only past what the package already covers.

| Extra | Price |
|---|---|
| Each state return after the first | $50 |
| Each local return after the first | $35 |
| Rental schedule — the Schedule E, covering up to three properties | $145 |
| Each rental property past those three | $45 |
| Farm schedule — the Schedule F | $200 |
| Each K-1 beyond the package's two | $15 |
| Each additional gig Schedule C | $65 |
| Each additional full Schedule C | $200 |
| Each brokerage statement after the first | $45 |
| Each brokerage statement that has to be entered by hand | $95 |
| Each foreign account | $50 |
| Any one of the named per-form situations (see below) | $50 |
| Earned income credit, with the required due diligence | $65 |
| Amended return | $250 |
| Extension with a payment estimate | $75 |

### The $50 per-form situations

One price, whichever it is. All six are things that *happened*, so a reader
can tell in a second whether one applies to them:

- sold a home
- had a debt cancelled or forgiven (a 1099-C arrived)
- sold, exchanged or spent digital assets
- had health insurance through the marketplace (a 1095-A arrived)
- paid into or out of an HSA
- took money out of a retirement account before 59½

Each carries an assumption — the ordinary version of that situation is $50,
and the unusual version is hourly. **Do not spell the assumptions out on the
site**; they belong on the client's own estimate, where they are attached to
a real engagement. On the site, "$50 each" plus the list above is the whole
story.

**Business returns** are priced now — **$800** for a partnership (1065),
**$950** for an S corporation (1120-S), **$950** for a corporation (1120).
They were the last blanks on the sheet and they were set on 26 August 2026.

One caveat that must survive into any copy: an entity return that has to file
a **balance sheet** is more work than one that does not, and that is charged
separately rather than being absorbed into the base. Do not write copy that
implies the base is the whole price for an entity.

The paragraph this replaces said business returns were **not priced
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
- **Every price on the page must match `fee-schedule.yaml` on the day it is
  published.** This is not a general good practice, it is the specific cost of
  the firm choosing a public page: a number on satcllp.com is a commitment,
  and the estimate a client gets later has to agree with it. Anything you
  cannot verify against the YAML does not go up.
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

Publish knowing this. **Every price in this file is now set, built and in
`fee-schedule.yaml`** — the schedule carries no unpriced items at all, for the
first time. The entity bases were the last three and they were set on
26 August 2026.

What remains genuinely unsettled:

- **The package names.** All four are being reworked to sound more like the
  firm. This is the single biggest risk to website work: names end up in
  headings, anchors, URLs and image alt text, and renaming them later is a
  content migration rather than a find-and-replace. **Build the page so the
  names are data, not markup.**
- **Whether the firm takes farm work at all.** The Schedule F is priced at
  $200 so the software does not give the work away while the question is open,
  but the firm has said it is unsure it wants to do it. **Do not advertise
  farm returns** until that is settled — a published price is a solicitation.
- **The hourly rate is soft.** $150 is the firm's own estimate of its average,
  described as "at least for now". The NSA survey puts the market at $149.52
  for Schedule E work, so it is safe to publish. It is not safe to build copy
  that treats it as a fixed, permanent figure.
- **The estimate says less than it used to about brokerage.** A client whose
  1099-B needs keying by hand now meets the $95 as a priced boundary in the
  estimate's assumptions rather than as an hourly warning. The $95 is real and
  correct to publish; it is worth knowing about if you are writing copy that
  promises no surprises.

**What changed on 26 August, in case this file is read against older copy.**
Rentals and farms left the package ladder and became priced forms. Property &
Business became Business. The earned income credit dropped from $150 to $65 to
match the market. The three entity bases were set and split. If any draft copy
says a landlord is a $500 client, it predates all of this and is wrong.

---

## 7 · Where pricing goes — decided

**The firm chose a public price page**, on 25 August 2026, in these words:

> i plan to operate transparently and find it personally frustrating it is
> hard to know what you will pay upfront on most tax sites

This was against the recommendation in the previous version of this file,
which argued for showing the number at the end of the intake instead. The
recommendation was about risk; the decision is about positioning, and
positioning is the firm's call. Build the page.

**What the decision costs, and what to do about each.** A public number is a
commitment in a way an estimate at the end of an intake is not, so three
things that were merely advisable become requirements:

1. **The page cannot show a price that is not in the YAML.** Not a rounded
   one, not a "from", not a placeholder. §4's last rule is the operative one.
2. **The entity returns say "quoted after a conversation".** A visitor
   reading four confident individual prices will expect a fifth. Give them
   the sentence, not a gap they fill in themselves.
3. **The page needs a way to be re-checked when prices move.** Whatever shape
   it takes, someone has to be able to answer "does the site still match the
   schedule?" in under a minute. A single page that names its source beats
   prices sprinkled through the copy.

**The intake estimate is not cancelled by this — it is the second half.** The
price page sets the expectation; the intake tells a specific person which
package their own answers put them in. The engine that does the second one
already exists, and the two agree by construction because both read the same
YAML. Build the page first; that is what was asked for.

---

## 8 · If you need something this file does not have

Ask the firm, or ask the agent working in `client-documents/`. Do not read the
price out of the Python and do not infer one from a comparable firm. Every
number here was argued about for a reason, and a number that appears on the
website without going through that argument is a number nobody decided.
