# The website pricing brief

**For the agent working in `website/`. Written 26 August 2026, after the fee
schedule was finalised.**

This replaces the pricing sections of `docs/pricing-for-website.md`, which
predate several decisions and now disagree with the schedule in places. Where
this file and that one differ, **this one is right** — and where this file and
the YAML differ, **the YAML is right**.

---

## 0 · Read the schedule, not this table

Everything below is a snapshot for your understanding. **Do not retype any of
it.** Read it from the source:

```python
import sys; sys.path.insert(0, "client-documents")
import pricing
pub = pricing.publication()      # {"publish": [...], "from": [...], "withhold": [...]}
```

Each entry is `(path, line)`. The line carries its own `label`, `detail`,
`amount`, and — where it matters — `covers`, `starting_note`, `form_fee`.

**This is the answer to "does the site still match the schedule?"** It is not
advisory. Every priced line declares whether it may be published, a withheld
line says why, and a line with no declaration raises rather than defaulting —
because defaulting to yes publishes a price nobody cleared, and defaulting to
no silently drops one the firm meant to show.

---

## 1 · The four individual packages — publish

Cheapest to dearest. **One package per client, and the client gets the cheapest
one that covers their return.** That is the engine's own rule, not a promise
made in copy.

| Package | Price | Who it is |
|---|---:|---|
| **Simple Filer** | $100 | Wages only, standard deduction, no other income document. Children are fine here |
| **Essentials** | $200 | A straightforward return with no schedules |
| **Standard** | $325 | Schedules: itemising, investments, a gig business on standard mileage |
| **Self-Employed** | $500 | A full Schedule C — actual expenses, home office, depreciation, inventory or payroll |

**"Self-Employed" was renamed from "Business" on 26 August**, and the reason
should shape the copy around it: **this is a 1040 package.** The old name
invited a partnership or S-corp owner to buy a personal return. Do not write
anything that reinforces that reading.

**Every package includes the federal return, the first state return and the
first local return.** This sentence is load-bearing and must appear wherever a
price does — without it the extras look like double charging.

**Never publish a price without what it covers.** Each tier carries a `covers`
list; use it. Four bare numbers reproduce exactly the problem the firm set out
to fix.

**The minimum is $200 and Simple Filer is its exception**, not the entry point.
`basis.minimum` is 200 and `basis.minimum_exception` is `starter`. The firm's
own framing: *our minimum is $200, unless your return is simpler than that.* A
page that presents $100 as the starting price makes every visitor ask why they
are not getting it.

## 2 · The extras — publish

Only past what the package already covers.

| Extra | Price |
|---|---:|
| Each state return after the first | $50 |
| Each local return after the first | $35 |
| Rental schedule — Schedule E, up to three properties | $145 |
| Each rental property past those three | $45 |
| Each K-1 received beyond the package's two | $15 |
| Each K-1 issued to an owner | $40 |
| Each additional gig Schedule C | $65 |
| Each additional full Schedule C | $200 |
| Each brokerage statement after the first | $45 |
| Each brokerage statement entered by hand | $95 |
| Each foreign account | $50 |
| Any one of the six named per-form situations | $50 |
| Extension with a payment estimate | $75 |

**The extension's filing is free.** Only computing the payment is billed. A
tile reading "Extension — $75" says the opposite of the decision.

**Foreign accounts are capped at four, and the cap is SOFT.** Past four the
per-account charge stops and the time is billed at $150 an hour. The page
currently says "capped at four" and stops there, which is now half the
sentence — a promise the firm is not making. **The checker will not catch this**
because the number did not change; only the qualification did.

### The six $50 situations

Sold a home · had a debt cancelled (1099-C) · sold or spent digital assets ·
marketplace health insurance (1095-A) · paid into or out of an HSA · took money
from a retirement account before 59½.

Publish the list and "$50 each". **Do not publish the assumptions behind them**
— those belong on a client's own estimate, attached to a real engagement.

## 3 · Amendments — publish, and it is three prices

Settled 26 August. What decides the price is **whose work it is**:

| The situation | What it costs |
|---|---|
| **We got it wrong** | **Nothing** |
| **We filed it; information arrived later** | **$50** |
| **It was prepared somewhere else** | **$50 on top of the return's own fee** |

There is no single amendment number to print. The honest short form:

> Correcting our own mistake is free. Amending a return we filed is $50.
> Amending a return prepared elsewhere is $50 on top of the return's own fee.

The first line is worth its space — it is the strongest thing on the page and
it costs the firm almost nothing to say.

**No separate entity amendment price**, and that is deliberate. What makes an
entity amendment bigger is reissuing a K-1 to every owner, and that is already
$40 each.

## 4 · Entity returns — **from** prices only

| Return | From |
|---|---:|
| Form 1065 — partnership | $800 |
| Form 1120-S — S corporation | $950 |
| Form 1120 — C corporation | $950 |

**Each must display its own `starting_note` list.** Read it from
`base.<form>.starting_note`; the notes sit beside the amount in the schedule
precisely so the two cannot drift apart.

**"From" is doing real work and must not be dropped.** The four individual
packages are *gated* on what is on the return, so the price a visitor reads is
the price they get. An entity base is a floor, with the balance sheet, the
reconciliation and the owner K-1s priced on top. **A bare $950 will be read as
a total.** `publish: from` marks this, and a test asserts the packages are
*not* from-prices, so the two kinds must not be styled the same.

## 5 · Hourly

**$150 an hour**, billed to the quarter hour with a fifteen-minute minimum.

Five things are hourly because nobody can size them beforehand: records that
need reconciling, **responding to a notice**, anything to do with a foreign
company, officer compensation, and time past the foreign-account cap.

The framing the firm settled on: **past the assumptions, the fixed price stops
applying.** Hourly happens *instead of* the fixed price, not on top of it.

## 6 · Do NOT publish

`pricing.publication()["withhold"]` is the authority. Today:

| Withheld | Why |
|---|---|
| Farm schedule ($200) | The firm **takes** farm work and does not **advertise** it. A published price is a solicitation |
| Records sorting ($175) | A floor a preparer sets, and a charge for the client's own untidiness reads very differently in public than in a conversation |

Each carries `publish_reason` in the schedule. If a draft mentions farms, take
it out.

**Also never public:** the firm's workbook figures; which numbers were the
firm's and which were a recommendation; the hourly cost basis behind any price;
market comparisons; anything in `docs/pricing-open-threads.md`.

## 7 · Wording rules

- **An estimate is not a quote.** The engagement letter governs.
- **Every price on the page must match the schedule on the day it is
  published.** A number on satcllp.com is a commitment, and the estimate a
  client gets later has to agree with it.
- **Do not invent legal, regulatory or assurance wording.** Leave a
  `[CONFIRM: ...]` and ask.
- **Build the package names as data, not markup.** They render from
  `pricing-config.js` today and that is what makes a rename one line. One of
  the four has already changed once.

## 8 · Deploy

- `website/` deploys to the live domain on push to `main`. **Never push to
  `main`.** Branch, draft PR, human merges.
- **`website/site-config.js` is hands-off.**
- Run `cd website && python3 pricing.spec.py` after any change — **including a
  change to the fee schedule.** Three of the four corrections above originated
  on the pricing side, not the site side.

## 9 · Still open — do not get ahead of these

- **How much the page claims about the estimate-to-invoice guarantee.** A bill
  over the estimate refuses without a variance note. That is real and tested;
  what the page *says* about it is a sentence a client reads, so it is the
  firm's to write.
- **Whether records sorting stays withheld.** The reason above is an agent's,
  not the firm's. The entity prices sat withheld on the same footing for two
  days before the firm reversed it.
- **Whether any package name has already gone to a real prospect.** If one has,
  a rename is a content migration rather than a config change.
