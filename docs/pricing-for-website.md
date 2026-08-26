# Pricing, for the website

> **Provenance note, added on filing this into the repo (26 Aug 2026).** This
> document arrived as an upload and is reproduced below unedited. It is filed
> here so the repo carries the brief the website work is supposed to read,
> rather than it living only in one conversation.
>
> **Both files it names exist on unmerged branches, not on `main`.**
>
> - `client-documents/registry/fee-schedule.yaml` — built in **PR #151**, along
>   with `pricing.py` and its tests. Its figures match this document: the four
>   packages at 100/200/325/500, the per-unit extras, the entity bases at
>   800/950/950 and $150/hr billed to the quarter hour. It annotates each number
>   with the argument behind it and it references this document by name.
> - `docs/pricing-open-threads.md` — the decision record, built in **PR #143**.
>
> So §0's "the YAML wins" is live guidance, but only once #151 merges. Until
> then `main` has no fee schedule at all, and anything reading one will not find
> it. Check #151 before building against this document.

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

## 0.5 · If you publish only one thing

The firm's own steer: the page **does not need to list every line**. It needs
the packages.

**The minimum honest page** is four things, and it is genuinely enough:

1. **The four packages, cheapest to dearest, with what each covers.** §1.
2. **The sentence that makes the prices readable:** every package includes the
   federal return, the first state return and the first local return. Without
   it the extras below look like double charging.
3. **One line saying extras exist**, without necessarily itemising them —
   "additional states, rentals, K-1s and business schedules are priced
   separately, and your estimate lists them before you commit."
4. **The estimate/quote distinction.** §4. An estimate is not a quote.

Everything in §2 is available to publish and none of it is *required*. A page
that lists every line reads as a menu; a page that lists four packages and
says extras are itemised on the estimate reads as a firm. That is a judgement
for whoever writes the copy, and either is honest.

**One line NOT to publish, even though it is on the sheet:** the records
sorting fee. It is a real charge and it is set by the preparer when they see
what arrived, so a website number would be a floor presented as a price — and
it is a charge for the client's own untidiness, which reads very differently
on a public page than it does in a conversation. Say nothing; the estimate
says it when it applies.

**What must NOT be trimmed to make the page shorter:** what each package
covers. A price with no scope is the thing the firm set out to fix — "it is
hard to know what you will pay upfront on most tax sites" — and four bare
numbers reproduce exactly that problem.

---

## 1 · The four individual packages

One package per client, and the client gets **the cheapest one that covers
their return**. That is the engine's own rule, not a promise made in copy —
among the packages a client qualifies for, it quotes the lowest total.

| Package | Price | Who it is |
|---|---|---|
| **Simple Filer** | **$100** | Wages only, standard deduction, and no other income document arrived. A tuition form for a credit you claim for yourself is fine here, and so are children. |
| **Essentials** | **$200** | A straightforward return with no schedules. |
| **Standard** | **$325** | You have schedules — itemising, investments, rentals, a farm, a gig business on the standard mileage rate. |
| **Business** | **$500** | You run a business on actual expenses, a home office, depreciation, inventory or payroll. |

That is also the display order: **cheapest to dearest**.

> **Three of the four names are now settled**, on the firm's own rule that the
> simplest answer is usually right. Only the cheapest rung was renamed —
> *Starter* became **Simple Filer**, because "Starter" reads as the bottom of a
> ladder and invites every new client to ask why they are not in it, where the
> firm wants it to read as an exception below the minimum. **"Business" is
> still provisional**; it replaced "Property & Business" when rentals stopped
> being a package. Build the names as data rather than markup anyway — one
> more rename is cheap that way and expensive otherwise.

**Every package includes the federal return, the first state return and the
first local return.** This sentence is load-bearing and must appear wherever a
price does — without it, the per-extra prices below look like double charging.

### What each covers

**Simple Filer** — Federal 1040, first state, first local. One or two W-2s. A
1098-T education credit claimed for yourself. Children are fine here: a
dependent by itself does not move a return out of this package.

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
| Sorting paperwork that arrives unsorted | from $175 |
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

**Business returns — publish these as STARTING prices**, which is the firm's
own instruction and is the honest framing:

| Entity return | Starting at |
|---|---:|
| Partnership (Form 1065) | **from $800** |
| S corporation (Form 1120-S) | **from $950** |
| C corporation (Form 1120) | **from $950** |

"From" is doing real work in that table and must not be dropped. An entity
return varies more than an individual one — a balance sheet, the number of
owners, whether the books arrive reconciled — so a bare number would be a
promise the estimate then has to break. Every one of those variables is priced
separately and appears on the client's own estimate before they commit.

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
- **The firm's stated minimum is $200**, and Simple Filer at $100 is the
  exception to it, not the entry point. That is the firm's own framing and it
  is worth writing copy to: *our minimum is $200, unless your return is
  simpler than that.* A page that presents $100 as the starting price makes
  every visitor ask why they are not getting it. There is no separate minimum
  fee on top of either.

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
- **Farm work is taken but NOT advertised.** Settled 26 August 2026. The
  Schedule F is priced at $200 and prepared when a client has one; the website
  says nothing about it. That is deliberate rather than an omission — a
  published price is a solicitation, and the firm does not want to solicit farm
  returns. **Do not add it to the page**, and if a draft mentions farms, take
  it out.
- **The hourly rate is soft.** $150 is the firm's own estimate of its average,
  described as "at least for now". The NSA survey puts the market at $149.52
  for Schedule E work, so it is safe to publish. It is not safe to build copy
  that treats it as a fixed, permanent figure.
- **The estimate says less than it used to about brokerage.** A client whose
  1099-B needs keying by hand now meets the $95 as a priced boundary in the
  estimate's assumptions rather than as an hourly warning. The $95 is real and
  correct to publish; it is worth knowing about if you are writing copy that
  promises no surprises.

**What changed late on 26 August, after the first correction.** *Starter*
became *Simple Filer*. A dependent no longer moves a client out of the cheapest
package — the market charges nothing for a dependent, and the work it creates
is the earned income credit due diligence, which is its own $65 line. A records
sorting charge exists at a $175 minimum and is deliberately not for the page.

**What changed earlier on 26 August, in case this file is read against older copy.**
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
