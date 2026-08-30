# Open threads

Every note Arjun writes into a pricing artifact lands here, verbatim, with what
happened to it. Started 25 August 2026, on the request that produced it:

> i am adding notes into the feedback im giving you and hope it ends up
> somewhere so we can work through them

**Why this file exists.** The sign-off artifacts hold *answers* — a price, a
verdict, a pick. They are a poor home for a note, because a note is usually not
an answer: it is a question, a reservation, or an idea that arrived while
answering something else. Read once and acted on, those evaporate. Written down
with a status, they get worked through.

**How to use it.** Nothing here is closed because it stopped being mentioned.
A thread leaves the list one of four ways, and the status says which:

| Status | Means |
|---|---|
| **Open** | Needs Arjun. Nobody is working on it. |
| **Answered** | A recommendation is in front of him; waiting on his call. |
| **Settled** | Decided. The decision and its date are recorded. |
| **Moved** | It turned into something else — a log entry, an issue, a document. |

Threads are numbered in the order they were raised and keep their number
forever, so `T-04` means the same thing in six months.

**Where they get asked.** Open threads are put to the firm in the interview
rounds. The live one is **round twelve**, published 26 August 2026:
<https://claude.ai/code/artifact/99d397cc-9361-4787-86dd-911b370c4807> — the
$500 package's name (T-19), whether the entity prices are published prices, and
what an amended entity return costs.

**Round eleven** is answered and built:
<https://claude.ai/code/artifact/1423b12b-0f09-453a-8c46-37b16545441c>. Five of
its seven closed T-16, T-17, the foreign cap, the EIC question carried from
round ten, and the last `[CONFIRM:` in the firm settings. The two it left as
notes rather than picks became T-19 and question 2 of round twelve; T-07's
answer became T-18. Round ten
(<https://claude.ai/code/artifact/3d80533a-3a67-4525-b04b-17717d56f1c4>) is
superseded.

---

## T-01 · Pricing against automation that hasn't arrived

**Raised** 25 Aug 2026, in the note holding the K-1 line at $15.

> i think we keep it at $15 - it sounds punitive at $25 from a third party
> perspective (myself) and we should really be incorporating levels of
> automation with this sort of work when it comes to reading docs for
> requirements

**Status** Settled 25 Aug 2026 — tag the exposed lines, price today's effort.

The K-1 half is **settled at $15**, against my recommendation of $25, and the
reasoning was better than mine: $25 does read as punitive for a page of numbers
somebody else already computed.

The general half is the live question. Four lines on the sheet are pure
document reading — a K-1, a brokerage statement, a rental, a local return — and
they are the ones a reader would plausibly do first. Three ways to treat them:
price today's effort and tag the exposed lines, price the automated target now
and absorb the gap, or hold them low on purpose as positioning. My
recommendation is tagging; giving the saving away before the tool exists cannot
be undone if the tool takes two seasons.

**Blocked on** the same thing as everything else — see T-07. "The tool saved us
an hour" is uncheckable without minutes per line.

---

## T-02 · What the entity gate means for the client

**Raised** 25 Aug 2026, answering the entity balance-sheet question.

> taking this to mean $800 is a package deal when it's under the small test,
> but otherwise we start adding service fees?

**Status** Settled 25 Aug 2026 — base plus named lines on the estimate.

The reading is right. $800 is the package while the entity is under the IRS's
own small-entity test; above it, named lines are added. What is still open is
how that *prints*: base plus named lines, one combined number, or two headline
prices. Recommendation is named lines, so a client can see that the balance
sheet is the thing that costs.

---

## T-03 · Gates for definite complexity jumps

**Raised** 25 Aug 2026, agreeing the $350 balance-sheet line.

> let's do 350 - are there gates we can set for definite complexity jumps?

**Status** Settled 25 Aug 2026 — all six gates added. The individual-side
equivalent is still open.

Six proposed, each keyed on a fact a client can answer at the consultation call
rather than a complexity level they would have to rate: payroll on the books
$150, inventory $125, assets bought this year $95, the entity's first return
$250, foreign activity **hourly**, and shareholder basis (Form 7203) $75 on the
owner's 1040. Foreign is the one where a fixed price is a trap — the penalties
are per form and bear no relation to the hours.

**Still open beyond the six:** whether there are jumps on the *individual* side
that deserve the same treatment. Nobody has looked.

---

## T-04 · Gating as the general principle, not just a pricing device

**Raised** 25 Aug 2026, approving the Schedule C tier fix.

> the idea for this is gating - if it is too complex, and beyond typical
> assumptions, we have to charge hourly which is simply outside of the bounds
> of these prices. however, if they give us what we need, we assume gates are
> complexity checks - if no additional forms or whatever, then it's fairly
> simple.

**Status** Settled 25 Aug 2026 — written into `registry/fee-schedule.yaml`
as the header comment the file did not have.

This is the clearest statement anyone has written of what the whole schedule is
doing, and it is currently implicit in the code rather than stated anywhere a
person reads. Three claims worth capturing properly:

1. A gate is a **complexity check**, answered from facts, not a judgement.
2. Past the assumptions, the fixed prices **stop applying** — hourly is not a
   surcharge on the price, it is outside it.
3. The prices assume **the client gives us what we need**. That assumption is
   already written into `assumed.cleanup`, but as a fee mechanism rather than
   as the principle it actually is.

**Proposed** — write it into `client-documents/registry/fee-schedule.yaml` as
the header comment the file does not have, so the next person to touch a price
reads the rule before changing it. Not started; nobody has asked for it.

---

## T-05 · Gig drivers and small supplies

**Raised** 25 Aug 2026, in the same note.

> maybe gig drivers expense certain things like snacks and water for their cars?

**Status** Settled 25 Aug 2026 — supplies do not move the tier. Produced T-10.

Recommendation is that supplies do **not** move the tier. Standard mileage
covers the vehicle — fuel, repairs, insurance, and the depreciation built into
the rate — and has never covered anything that is not the car, so tolls,
parking, a phone and passenger supplies are deducted alongside it without
changing the work. The tier flips on actual vehicle expenses, a home office,
depreciation, inventory or payroll, because each of those is a different job.

**Carries a `[CONFIRM:`** — the deductibility wording needs checking against
current guidance before it reaches a client-facing document. irs.gov is not
reachable from the machine these notes are written on.

---

## T-06 · Keying 1099-B lots instead of summarising

**Raised** 25 Aug 2026, on the brokerage price.

> it is not that we can't enter the high level data and attach, it's that the
> process is currently me keying in everything ... this is the kind of thing
> that should be added to a log of ideas we can have to make things easier on
> filling stuff out

**Status** Moved → `docs/workflow-friction-log.md`, first entry. The price half
settled 25 Aug 2026 and **built the same day**: $45 a statement past the one
the package includes, $95 for one that has to be keyed, and `assumed.brokerage`
removed rather than reworded. What the removal cost the client's estimate is
now T-14.

It also produced the rule at the top of that log, which is worth repeating
because it decides pricing questions on its own: **where our process costs more
than the return needs, that is a cost to fix, not a cost to bill.**

What remains here is the price itself — what flips the $95 line. Round two,
question 3, recommending "the parts that cannot be summarised."

---

## T-07 · Nobody knows how long anything takes

**Raised** repeatedly, across every pricing conversation this month.

**Status** Answered 26 Aug 2026 — **both**, and it is a build rather than a
decision now. The firm, on round eleven:

> This and we need to track manual time in a good way

So: the software stamps each line as it is worked, AND there is a good way to
record the time that happens away from the software. My recommendation was the
passive half alone, for one reason — it is the only version that still exists
in April, because a log that depends on remembering stops exactly when the data
gets interesting. The firm is right that passive capture alone would miss the
phone call, the drive, and the hour spent on a return with the file closed,
which is where a lot of the real time goes.

**Not built, on purpose.** This is its own piece of work and it was not going
to be assumed into the session that answered it. What it needs before anybody
starts: where a stamp is written, whether a minute belongs to an engagement or
a line, what the manual entry costs a person in seconds (this is the whole
question — a form that takes thirty seconds will not be filled in), and whether
any of it reaches a client document. Scoped as **T-18**.

The rest of this thread, below, is why it matters and stays accurate.

Five figures would settle most of what is still argued about: the package, the
prep hours, the admin hours, whether an assumption failed, and what that cost.
Without them, "is $100 a loss on a student return", "is $200 too much for a
Schedule C" and "did automation save us anything" are all unanswerable — and
T-01 cannot be closed at all.

Also in the friction log as the second entry, because it is both a pricing
problem and a workflow one.

---

## T-08 · The allowance shape for rentals

**Raised** during the package ladder draft, never resolved.

**Status** Settled 25 Aug 2026 — three stay inside, then $45 each.

Property & Business covers up to three rentals *or* one full Schedule C, and
prices rentals beyond that at $45 each. The unresolved question is whether
three-then-meter is right at all, or whether rentals should meter from the
first with a lower base. The workbook's own rule (one Schedule E, three
rentals, $130) is where the three came from, so it is inherited rather than
chosen.

---

## T-09 · The local return price is an inference, not a source

**Raised** during the price sheet build.

**Status** Settled 25 Aug 2026 — $35 kept, and off the worry list. If the
firm ever quotes a standalone local, what it charged beats any survey.

$35 is the weakest number on the sheet. No survey breaks out an Ohio municipal
return and neither RITA nor CCA publishes preparer fees, so it is reasoned:
lighter than a state return, but residency, the workplace credit and
withholding by city are real work. It should be checked against what other Ohio
preparers actually charge before it is treated as fixed.

---

---

## T-10 · Free literature that helps people arrive prepared

**Raised** 25 Aug 2026, agreeing that supplies do not move the gig tier.

> Let's do this and make it a priority to produce literature we can give for
> free/on the website to drive traffic to help people be prepared for their
> accountants

**Status** Answered 25 Aug 2026 — hand-write two, then generate the rest from
the registry once the format is proven. First two: the gig driver and the
first-time landlord. Drafts pending.

It arrived on the gig-supplies answer for a reason. The recommendation there
included writing down once, for clients, that passenger snacks and water are
supplies and the driver's own lunch is not — and the observation that a client
told once stops asking every year. Arjun's note generalises that: if telling a
client something once saves the question every year, the telling is worth
producing deliberately, and putting it on the website turns it into traffic
rather than an email.

**What it plausibly is.** Short, specific, per-situation sheets — the gig
driver, the first rental, the new S corp, the student — each saying what to
bring and what counts. Not a blog. The test is whether a real client can act on
it before their appointment.

**Why it is more than marketing.** Every one of these sheets is the same
content as a document-request list, and the pipeline in `client-documents/`
already builds those from the interview registry. A public sheet and a client's
personalised request list could come off one source, which is the difference
between writing them once and maintaining two copies that drift.

**Not started.** Needs scoping before anything is written — which situations,
how many, and whether they generate from the registry or are hand-written.

---

## T-11 · Capturing the processes themselves, not just the frictions

**Raised** 25 Aug 2026, on the automation question.

> the most important thing is to track the need for processes and workflows as
> these will be very important to get right

**Status** Open — new.

Distinct from the friction log, and the distinction matters. The friction log
records where the current way of working *hurts*. This is about writing down
what the way of working *is* — the steps of a return, from the consultation
call through to delivery — because that is the thing automation will be pointed
at, and an undocumented process cannot be automated, only re-invented.

It is also the missing half of T-07. Minutes per line say how long something
takes; a written process says what the something is. Neither is much use alone.

**Not started, and deliberately not scoped here** — this is large enough that
guessing at its shape would waste the effort.

---

## T-12 · Bookkeeping is parked, on purpose

**Raised** 25 Aug 2026, as the answer that was a note instead of an answer.

> this just needs its own workstream and we will get there when we get there -
> for now we have cleanup in tax prep

**Status** Parked — deliberately, with a reason, which is different from blank.

Bookkeeping is the only service in the repo with a signed engagement letter and
no fee anywhere. Four shapes were put up — monthly tiers, hourly, a hybrid, or
leave it. None was chosen, and the note explains why: it is a workstream, not a
line on a tax price sheet, and until it is sold deliberately the records-cleanup
hourly line inside tax prep does the job.

**What holds it in the meantime.** `assumed.cleanup` — every engagement assumes
records arrive complete and reconciled, and work past that assumption is billed
hourly at the standard rate. That covers the tax-prep case honestly. It does not
cover a client who wants their books kept, which is the workstream.

---

## T-13 · One per-form price, gated by complexity

**Raised** 25 Aug 2026, on the individual-return gates.

> i have been doing this stuff with a client for awhile and just charge per
> account - nothing huge though. let's just try to make it simple and come up
> with a per form amount and gate with complexity

**Status** Settled 25 Aug 2026 — $50 a form, gated by the assumption behind
each. Foreign accounts at $50 each, with a foreign *company* (Form 5471 or 8865)
carved out as hourly. The entity gates stay individually priced. **Built the
same day**, as `per_form:` in the fee schedule and an `extra_forms` question in
the interview; each ticked form prints its own assumption on the estimate, and
the ones nobody is filing print nothing.

Two things at once, and the second is the larger.

**The correction.** Five individual gates were proposed at five bespoke prices.
That is over-engineered for what those situations are, and on foreign accounts
it ignored that the firm already does the work and already charges per account —
which is why that was the one gate left unmarked.

**The idea.** One flat per-form amount, with the assumption behind each form
acting as the gate: hold the assumption, pay the flat price; break it, the meter
runs. That is claim 2 of T-04 applied to a whole category rather than to one
line, and it turns the sheet from a price list into a rule plus exceptions.

**The price is the firm's, not mine.** $50, against my recommendation of $75.
Twenty minutes at the standard rate rather than half an hour — and it has one
downstream consequence worth recording, because it was argued the other way: at
$75 the extension line would simply have BECOME the per-form price. At $50 it
stays a named exception, because computing a payment from an incomplete file is
not a twenty-minute job.

**The boundary worth being deliberate about.** The rule fits individual forms,
which genuinely have one document behind them. It does not fit the entity gates:
Schedules L, M-1 and M-2 are three schedules and a book-to-tax reconciliation,
not a form. Pricing those per form would misprice the exact engagements where
mispricing hurts most.

---

## T-14 · A priced boundary the estimate cannot state

**Raised** 25 Aug 2026, building the brokerage lines.

**Status** Settled 26 Aug 2026 — the vocabulary was widened and the firm asked
for it. `assumed.brokerage_keying` now carries `beyond: priced` with
`beyond_price_from: brokerage_keyed`, so the estimate reads the number off the
line that charges it rather than repeating it. `phrases.beyond_priced` is the
sentence. **This status line said "Open" until 26 August 2026, a day after the
work shipped** — worth noting, because a register nobody closes out is a
register people stop reading.

Brokerage moved off the hourly list and onto the counted one — $45 a
statement, $95 for one that has to be keyed. `assumed.brokerage` came off in
the same change, because an assumption *and* a price for the same overrun is
worse than either alone: the client reads "included", then gets an invoice
line, and afterwards nobody can say which one was operative.

**What came off with it.** The old assumption printed on every estimate and
warned, before the work, that unusual brokerage activity would cost more. The
new lines only appear once somebody has answered how many statements need
keying — and that is usually unanswerable when the estimate is written,
because nobody knows until the statement arrives. So the common case is now:
estimate goes out silent, $95 appears on the invoice.

A review flag covers the firm's side (the interview raises it at file review).
It does nothing for the client's side.

**What it would take.** `assumed:` states a boundary and its consequence, and
the consequence vocabulary is deliberately one word wide — `hourly`, with
`requote` refused on purpose because the firm ruled out stopping the job to
renegotiate. A boundary whose consequence is *a price already on the sheet* is
a third thing, and it is arguably the best of the three: the client is told
the number before the work rather than the rate.

Adding it means extending that vocabulary — something like `beyond: priced`
naming the per-unit line that prices the overrun, so the sentence reads "...
that statement is billed at $95, which you will see as a line before you pay"
instead of "... at $150 an hour". That is a small change to
`pricing.assumptions()` and a one-line addition to the schedule.

**Not done, on purpose.** The `beyond:` vocabulary is narrow because the firm
narrowed it, and widening it is a policy decision wearing a config key's
clothes. Recommendation: do it. But the firm decides.

---

## T-15 · Property & Business never pays for itself on rentals

**Raised** 25 Aug 2026, by building the check the firm asked for:

> something should be able to pretty simply determine its cheaper tier or
> combination of pricing to get them to the cheapest thing they need to do

**Status** Settled 26 Aug 2026 — dissolved rather than decided, by making
rentals a **form**. Verified 26 Aug: `per_unit.rental` is priced
`form_fee: 145` covering three, then $45 each, and **no tier carries a rental
allowance any more** — `standard` allows brokerages and K-1s, `business`
allows one standard-mileage Schedule C, and neither mentions rentals. So the
$175 step no longer buys a landlord anything they could fail to spend: it buys
one full Schedule C, which is what the name is about. The arithmetic below is
kept because it is why the shape changed, but it no longer describes the
sheet.

**This status line said "Open" until 26 August 2026**, as T-14's did. Two of
four live threads were already settled and still reading as open — see the note
on T-14.

**The arithmetic.** Property & Business is $500 against Standard's $325 — a
$175 step — and what it buys a landlord is a three-rental allowance worth
3 × $45 = **$135**. The allowance is worth less than the step, at every count:

| Rentals | Property & Business | Standard + metered rentals | Client loses |
|---:|---:|---:|---:|
| 1 | $500 | $370 | $130 |
| 2 | $500 | $415 | $85 |
| 3 | $500 | $460 | $40 |
| 4 | $545 | $505 | $40 |
| 7 | $680 | $640 | $40 |

It never crosses. The package only earns its price on a **full Schedule C**,
where the allowance is worth $200 against the same $175 step — $500 versus
$525, by $25.

**Who it bites, and the sentence that makes it worth fixing.** Only a client
who also holds Standard's gate, which means a landlord who *itemises*. A
landlord who does not itemise is not eligible for Standard and has no cheaper
option. So today: **the client with more going on pays less.** A landlord with
a Schedule A pays $370; the same landlord without one pays $500.

**Four ways out, and they are not equivalent.**

1. **Drop Property & Business** to $460 or below. Makes the ladder consistent
   and costs the firm on every landlord.
2. **Widen the rental allowance** to five, worth $225 against the $175 step.
   Keeps the price and makes the package genuinely better value.
3. **Raise the per-rental price** so three of them are worth more than $175 —
   $60 each. Changes what a fourth rental costs everyone.
4. **Tighten Standard's gate** to exclude E1 and F, so a landlord is never
   eligible for Standard. This makes the check pass and fixes nothing: the
   allowance is still worth less than the step, and any client who can read
   both prices can still see it.

Recommendation: **2**. It is the only one that answers the actual complaint —
the package should be worth what it costs — without moving a price the firm has
already signed, and it makes Property & Business mean something to a landlord
rather than being where the software files them.

**The check is now permanent.** `test_the_ladder_always_puts_a_client_on_their
_cheapest_package` prices every client shape on every rung they are eligible
for and fails if a cheaper one existed. This exception is pinned by name and by
amount, so it can shrink but not grow, and a future price change that breaks the
ladder somewhere else fails immediately.

## Settled

| # | Thread | Decision | Date |
|---|---|---|---|
| — | K-1s inside Standard | Two, then a meter | 25 Aug 2026 |
| — | Each K-1 past the allowance | $15 | 25 Aug 2026 |
| — | Entity return at $800 | Applies under the IRS small-entity test | 25 Aug 2026 |
| — | Balance sheet when required | $350 | 25 Aug 2026 |
| — | An entity's second state | $150, separate from the $50 individual line | 25 Aug 2026 |
| — | Additional Schedule C | $65 gig / $200 full, on the existing fact test | 25 Aug 2026 |
| — | Brokerage | Counted at $45 + $95, off the hourly list | 25 Aug 2026 |
| — | The orphaned Schedule C tier | Folded into `standard`; regression test added | 25 Aug 2026 |
| — | Gig supplies and the Schedule C tier | Supplies do not move it | 25 Aug 2026 |
| — | How the entity gate prints | Base plus named lines | 25 Aug 2026 |
| — | What flips the $95 brokerage line | What cannot be summarised | 25 Aug 2026 |
| — | Lines exposed to automation | Price today's effort, tag them | 25 Aug 2026 |
| — | Six entity complexity gates | All six added as proposed | 25 Aug 2026 |
| — | The rentals allowance | Three inside, then $45 | 25 Aug 2026 |
| — | The local return price | $35, kept | 25 Aug 2026 |
| — | The gating rule | Written into the fee schedule header | 25 Aug 2026 |
| — | The pricing write-up | Retired; the sheet carries the reasoning | 25 Aug 2026 |
| — | The per-form price | $50, gated by each form's assumption | 25 Aug 2026 |
| — | Foreign accounts | $50 each; a foreign company stays hourly | 25 Aug 2026 |
| — | How far the rule goes | Individual forms only; entity gates stay named | 25 Aug 2026 |
| — | What a package covers | Prints on the estimate; `includes:` is followed, not printed | 25 Aug 2026 |
| — | Counted lines the package paid for | Labelled "after the first" / "after the N included" | 25 Aug 2026 |
| — | Rentals outnumbering local returns | Flagged for a human; never derived | 25 Aug 2026 |
| — | The gig Schedule C in Property & Business | Included; the either/or is rentals vs a FULL Schedule C | 25 Aug 2026 |
| — | Where pricing goes | A public price page, for transparency | 25 Aug 2026 |

---

## T-16 · Amended returns are priced in prose and nowhere in the schedule

**Raised** 26 Aug 2026, checking what the price page could publish.

**Status** Settled 26 Aug 2026, then **reshaped by T-20 the same day** — an
amendment is now **+$50 on whatever the return is**, not a flat $250. Read T-20
for the current shape; what follows is why the price existed at all. The firm's
answer to round eleven took the figure that had been sitting in the prose and
put it in the schedule, where the estimate can quote it and the invoice can
bill it.

Built as `base.1040.amended`, beside `tiers` rather than among them: the four
packages describe an original return prepared from scratch and no rung of them
describes redoing one. Checked before tier selection so it cannot lose a
cheapest-eligible comparison to a package it is not competing with. It is a
base, so everything on the return is still counted on top.

**One thing is deliberately still open:** the amended ENTITY return. Different
work, no price set, and the interview does not ask about it rather than
inviting an answer nothing can price.

`docs/pricing-for-website.md` §2 lists **Amended return — $250**. It is not in
`registry/fee-schedule.yaml`: not a `base`, not a `per_unit` line, not one of
the eight `per_form` situations. Grep the schedule for "amend" and there is no
hit at all.

The schedule is the source of truth — that is §4's own rule, and the site's
checker enforces it, so the $250 correctly did not reach the price page. But
the consequence runs further than the website: **the estimate cannot quote an
amended return and the invoice cannot bill one.** There is no line to put it
on. Today the work would be typed in by hand, which is the exact thing the
counted schedule exists to stop.

Two ways it is a real number and one way it is not:

- It is the firm's price and the YAML simply missed it → add it and the whole
  pipeline picks it up.
- It is a stale figure from the prose brief that nobody has re-decided → the
  fix is to strike it from §2, not to publish it.
- **SATC does not take amended returns as standalone work** → say so, and the
  prose line is the thing that is wrong.

**Recommendation:** it is a `base`, not a per-unit line — an amended return is
a whole engagement with its own scope, not an add-on to another return. But the
price is the firm's and I have not assumed one.

---

## T-17 · The firm can send an extension notice and cannot bill for it

**Raised** 26 Aug 2026, same check as T-16, and the sharper of the two.

**Status** Settled 26 Aug 2026 — **$75, its own named line, and filing an
extension is free.** Only computing the payment is billed.

Not in `per_form`, which is what this thread argued for and what the schedule's
own comment already said. Counted rather than a yes/no, because a state that
will not honour the federal extension is a second computation and not the same
one filed twice. Preparer-facing and normally blank when the estimate goes out,
since an extension happens in season.

The Extension Notice still carries no fee, and a test now checks that — the
temptation when closing this was to fix the gap at the letter, which would have
broken the letter to fix the invoice.

`docs/pricing-for-website.md` §2 lists **Extension with a payment estimate —
$75**. Like the amended return, it is absent from `fee-schedule.yaml`.

What makes this one worse is that the rest of the machinery is already built
around it:

- **The Extension Notice is one of the ten templates** and it renders for real
  today — it is not blocked on anything.
- That template **deliberately carries no fee**. Its FIELDS spec says so in as
  many words: *"No fee. The invoice owns it. An extension notice that also asks
  for money reads as a bill and gets filed as one — and this is the letter that
  most needs reading."* That is a good decision.
- The invoice it hands the money to **has no line for an extension**.

So the fee was handed from the notice to the invoice, and the invoice never
received it. Each document is individually right and the pair drops the charge
on the floor. It is the same shape as the six bugs found on 26 August: nothing
errors, nothing is flagged, and the work is simply never billed.

There is also a live argument in the schedule about the number. The `per_form`
header comment records that **$50 is the firm's number against a
recommendation of $75**, and that at $75 the extension line *would simply have
become* the per-form price — it stays a named exception at $50 precisely
because *"computing a payment from an incomplete file is not a twenty-minute
job."* That reasoning was written about the extension specifically. The $75 in
the prose is the number that argument produced and then nobody carried across.

**Recommendation:** price it, and as its own named line rather than inside
`per_form` — the schedule's own comment already explains why it does not fit
there. Whether it is $75, or $50 to match the per-form price, or something else
is the firm's call. Filing an extension without a payment estimate may well be
free; the priced thing is the estimate.


---

## T-18 · The time capture, scoped

**Raised** 26 Aug 2026, out of T-07's answer. **Status** Open — a build nobody
has started, deliberately not begun in the session that scoped it.

Two halves, and the second is the one that usually fails:

1. **Passive.** The software stamps each line as it is worked. No discipline
   required, which is why it survives a busy season.
2. **Manual.** The time that happens away from the software — a call, a drive,
   an hour with the file closed. The firm asked for this explicitly and it is
   the half that carries most of the answer to "what does this actually cost".

**What has to be decided before any of it is written**

- **Where a stamp lives.** An engagement, or a line on the estimate? Per line
  is what would settle the pricing arguments; per engagement is what somebody
  will actually keep.
- **What manual entry costs the person doing it.** This is the whole question.
  A form that takes thirty seconds does not get filled in, and a log with gaps
  is worse than no log because it reads as complete.
- **Whether any of it reaches a client.** Today nothing does — every fee is a
  price, not an hourly total, apart from the explicit hourly lines. If captured
  time starts appearing on an invoice that is a different product and a
  different conversation.
- **What question it is meant to answer first.** "Which lines are underwater"
  is answerable with far less data than "what did this client cost". Building
  for the second and getting the first is the usual outcome.

**Why it blocks other things.** Every argument about whether a price is right
ends here. T-01's automation half could not be settled without it, the sorting
fee is a floor rather than a price because of it, and every fee on the sheet is
currently defended by somebody else's market survey rather than by the firm's
own minutes.


---

## T-19 · What the $500 package should be called

**Raised** 26 Aug 2026, answering round eleven. The firm did not pick, and
asked for options:

> Maybe we rename but I need ideas to do. The site also needs to have tiles for
> actual business return prices like 1120S. What makes more sense than business?

**Status** Settled 26 Aug 2026 — **Self-Employed.** "self-employed seems
reasonable". The label changed; the tier key stays `business`, because it is
internal and renaming it would be churn no reader benefits from.

**The problem, stated precisely.** "Business" is a **1040** package: $500,
covering one full Schedule C on top of everything in Standard. The entity
returns are `base.1065` ($800), `base.1120S` ($950) and `base.1120` ($950), and
none of them is called Business. So a partnership or S-corp owner reading four
package names picks the one with their word in it and buys a personal return.
That is a mistake the client makes and the firm has to unwind.

**What the package actually is.** Not "a business" — a person who works for
themselves and files it on their own return. That is what the name has to say.

| Candidate | Why | Against |
|---|---|---|
| **Self-Employed** | Says exactly who it is for, and nobody with an S-corp thinks it means them. The plainest available answer | Slightly clinical; it is the IRS's word rather than a person's |
| **Sole Proprietor** | Precise, and precision is the whole problem here | A term some clients will not recognise as describing them |
| **Schedule C** | Unambiguous to anyone who has filed one | Names a form rather than a person; the other three names do not |
| **Freelancer** | Warmest, and true for a large share of who buys it | Wrong for a contractor with employees, who is exactly the full-Schedule-C client this tier is priced for |

**My reading, though the name is the firm's.** *Self-Employed* — it is the
only one that is both plain and correct for the whole range the tier covers,
and it reads as a description of the client rather than a label for a product.
*Freelancer* is the tempting one and it is the one that misdescribes the
expensive half of the tier.

**Why now rather than later.** The price page renders package names from
config rather than hardcoding them into headings and anchors, deliberately,
because all four names were unsettled. While that holds, a rename is one line.
Once a name is in a heading, an anchor, and a link somebody has sent a
prospect, it is a content migration.

**Nobody has checked whether any of the four names has already gone to a real
prospect.** If one has, this stops being free.

**The second half of the note is a website question**, not this one — see
`docs/site-open-questions.md`. Publishing entity prices would reverse a
decision currently in force (they are withheld in favour of "quoted after a
conversation"), so it is a firm decision with a site consequence rather than a
site decision.


---

## T-20 · Is an amended return a flat price, or a base plus an adder?

**Raised** 26 Aug 2026, by the firm, answering round twelve's question about
amended ENTITY returns — and the answer reaches further than the question did:

> this should assume that it is an "Essentials" package plus the work for
> amendment and reviewing the old return. the $50 premium at that point turns
> into more of an adder - right? does this make sense?

**Status** Settled 26 Aug 2026 — **an amendment is +$50 on whatever the return
is.** The firm:

> let's just make an amendment cost an extra $50 and go from there. i want the
> business, and the value is $50 for amending as opposed to doing the primary
> file.

Built as a top-level `amendment:` adder gated on `return_basis`, replacing the
flat $250 base that bypassed the ladder. It applies to **every form**, which is
what finally gives an amended entity return a price:

| The return | Original | Amended |
|---|---:|---:|
| Simple Filer | $100 | **$150** |
| Essentials | $200 | **$250** |
| Standard | $325 | **$375** |
| Self-Employed | $500 | **$550** |
| Form 1065 | $800 | **$850** |
| Form 1120-S / 1120 | $950 | **$1,000** |

Essentials + $50 still lands on $250, which is where that number came from.

**The firm overrode my recommendation and said why**, which is worth keeping:
I argued for capping the adder at the original fee, because $550 to amend a
$500 return invites an argument. The firm wants the work and priced it
deliberately cheap — the $50 is what amending is worth *over* preparing the
return, and the reconciliation to the return as filed is real work on top of
preparing it. Positioning, not arithmetic, and positioning is theirs.

**B1 in `docs/site-open-questions.md` is closed by this too** — the amended
entity return now has a price and may be published.

**Yes, the arithmetic makes sense, and it is where the $250 came from.**
Essentials is $200. The amended return is $250. So $250 *is* Essentials plus a
$50 amendment adder, exactly as described. Nobody designed it that way; it
falls out.

**And the structural instinct is better than what is built.** Today the
amendment is a flat $250 that bypasses the package ladder. That means amending
a Self-Employed return — a full Schedule C, originally $500 — also costs $250.
Amending a complex return is plainly more work than amending a simple one, and
a flat price cannot see the difference. Base-plus-adder can.

**But the anchor overshoots at the top, and this is the part worth deciding
with your eyes open.** If the base is the package the return actually is:

| The return | Original | Amended, base + $50 |
|---|---|---:|
| Essentials | $200 | **$250** |
| Standard | $325 | **$375** |
| Self-Employed | $500 | **$550** |
| Form 1120-S | $950 | **$1,000** |

The bottom row is the problem in miniature: **$550 to amend a return that cost
$500 to prepare.** An amendment is a review, a change and a refiling — real
work, and not more work than preparing the thing from nothing. A shape that
charges more to amend than to originate will be argued with, and the client
will be right.

**Three ways out, and I have not picked for you.**

1. **A share of the base plus the adder** — say half the package price plus
   $50. Scales with complexity, never exceeds the original.
2. **Base plus adder, capped at the original fee.** Keeps the arithmetic you
   described and puts a ceiling on it.
3. **Flat by tier**: one amendment price for the two simple packages, another
   for the two complex ones, a quote for entities. Cruder, and nobody argues
   with it.

**And the $50 is doing a lot of work at the top.** Reviewing a filed 1120-S,
reconciling what changed and reissuing every K-1 is not a $50 job. Whatever
shape wins, the adder probably is not one number across a 1040 and an 1120.

**Recommendation:** option 2. It preserves the reasoning you arrived at
independently — which is a good sign the reasoning is right — and fixes the
one case where it produces a number you would not want to defend.


---

## T-21 · An amendment is priced by whose work it is

**Raised** 26 Aug 2026, by the firm, reading the flat +$50 back:

> if we legit made a mistake i wouldn't even charge to fix it for $50. but yes
> for someone else's return we add $50

**Status** Settled 26 Aug 2026 — three cases, keyed on fault and origin rather
than on what the return looks like.

| The situation | What it costs |
|---|---|
| **We got it wrong** | **Nothing.** And the line prints at $0.00 rather than vanishing |
| **We filed it; something arrived later** | **$50**, and no package charge |
| **It was prepared somewhere else** | **$50 on top of the return's own fee** |

**What this fixed.** The flat adder charged *package + $50* in every case,
which is right for a stranger's return and hard to defend for one SATC filed
last month — it quoted $850 to amend a 1065 we had prepared ourselves. Two
different jobs were wearing one name: understanding a return before changing
it, and changing one we already hold.

`reprices` is the switch, and it is false for both of our own cases: the
estimate is the amendment line and nothing else. No package, no schedules, no
states. We hold all of it, and charging again charges twice for one job.

**The $0 line prints.** A client told in writing that fixing our error costs
nothing has been told something; a line that quietly fails to appear has not.

**No reason answered means no price.** $0 and $1,050 are both live answers, so
an unanswered reason carries the question to the line and the estimate refuses
— the same convention every other unanswered tier uses.

**On entity amendments, asked in the same breath.** There is no separate entity
price and there should not be. What actually makes an entity amendment bigger
is reissuing a K-1 to every owner, and `owner_k1` already prices that per owner
— so the cost scales on the number of owners, which is the thing that varies,
rather than on the word "entity". Verified: a 1065 with five partners amended
from elsewhere prices at **$970**, of which $120 is the three K-1s past the two
the base covers.

> **Superseded figure, kept because the reasoning above rests on it.** This
> paragraph originally recorded $1,050, "of which $200 is the five K-1s". That
> was read back off the engine at a time when the engine billed every K-1 from
> the first — while `starting_note`, on the website, said "each partner's K-1
> after the first two". The firm settled it on 28 August 2026: *"Base should
> carry a 2 k1 allowance."* The engine now matches the published note and the
> figure moved by $80.
>
> **And the question it raised is answered.** The argument here is that an
> entity amendment costs more because every owner's K-1 is reissued — so under
> the allowance, a two-owner amendment bills **nothing** for reissuing two
> K-1s: $800 + $50, with the reissue work free. That was raised as an open
> question the same day, because the allowance had been decided about the
> base, which is a from-price for an original return, and an amendment is not
> one. **The firm, 28 August 2026: "This can flow through."**
>
> So it flows. The two-partner amendment is $850, the five-partner is $970,
> and the K-1 line starts at the third owner whether the return is original or
> amended. No code changed to close this — the allowance already flowed and
> the question was whether to stop it. Pinned at both counts in
> `test_an_entity_amendment_follows_the_same_three_cases`, so a later change
> that quietly reintroduces a charge for the first two has to move a number
> somebody can see.

**One thing NOT settled and not assumed.** Whether amending a partnership
return is procedurally the same kind of filing as amending a 1040. If it is
not, that is a scope question before it is a pricing one. Nobody has checked,
and it is not an agent's to assert.

---

## T-22 — the bookkeeping estimate has no scope block

Opened 26 August 2026, alongside the firm's ask that the estimate and the
engagement letter be comparable.

The fee estimate now repeats the engagement letter's four scope lines —
`FederalReturns`, `StateReturns`, `LocalReturns`, `AdditionalForms` — from the
same fields on the same record, and `ReturnScope` gates the block.

**A bookkeeping engagement's scope is a different shape.** Its letter carries
`ScopeItems`, a list, not four lines. So the flag is off there and the block
drops rather than printing four blanks, which is the right behaviour today
because there is no bookkeeping interview and no bookkeeping estimate.

**What it needs when that changes:** a second branch on the estimate that
repeats `ScopeItems` the way the block repeats the four lines. Not a decision
for the firm — a build note, recorded so it is not rediscovered.
