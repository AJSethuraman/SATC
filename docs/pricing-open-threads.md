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
settled 25 Aug 2026: the $95 keys on what cannot be summarised.

It also produced the rule at the top of that log, which is worth repeating
because it decides pricing questions on its own: **where our process costs more
than the return needs, that is a cost to fix, not a cost to bill.**

What remains here is the price itself — what flips the $95 line. Round two,
question 3, recommending "the parts that cannot be summarised."

---

## T-07 · Nobody knows how long anything takes

**Raised** repeatedly, across every pricing conversation this month.

**Status** Open, and blocking more than it looks like.

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
carved out as hourly. The entity gates stay individually priced.

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
