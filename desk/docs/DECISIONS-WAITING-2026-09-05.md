# Seven decisions the close is waiting on

These are the **kind D** questions from `CLOSE-QUESTIONS-TRIAGE.md`: the ones no
authority settles, because the rules permit a choice and the firm has to make it
once. They are not questions to be researched. They are decisions.

**Two of the seven the firm has already answered** in their own words while
reading the close questions, and those are written below as position text ready
to be proposed. **Five are genuinely open.** Each of those carries both outcomes
and what it costs to be wrong, because a decision handed over without its
downside is one somebody makes twice.

Nothing here is written into any desk. A position is proposed by pull request and
ratified by the firm; that is the only route.

---

## Already answered — these are proposals waiting to be placed

### Q19 · Do we track inventory for a trades client?

**The firm, 5 September 2026:**

> *"I think materials at year end isn't what we want to do here like so for
> bookkeeping I don't really want to keep track of an inventory and I would charge
> them if we had to because that's more complicated and like I I kind of base it
> off the tax code anyway I guess this is another safe harbor moment for me like
> you don't have to defer to safe harbor but if there's no reason not to I feel
> like you might as well in general"*

**The position that follows:** materials bought for jobs are expensed as
purchased. Inventory is tracked only where the tax code requires it, and where it
is required the engagement is priced for it.

**What is still needed before this can be written:** the citation. The position
rests on a small-taxpayer exception in the code rather than on a preference, and
that paragraph has to be fetched and stored before a position can point at it.
The capitalisation desk being built now is where it would live.

### Q27 · What proves a deposit is revenue?

**The firm, 5 September 2026:**

> *"yeah I kind of agree with this because like why else would you deposit money
> into an account and the simplest thing to do is to just deposit all your money
> into your business account and call it revenue and that's what I would advise
> my clients to do"*

**The position that follows:** a deposit into a business account is revenue
unless something identifies it otherwise. The firm advises clients into the
practice that makes this true.

**What is still needed:** this is a bookkeeping convention, not a tax rule, and
the literature that states it is GAAP — which is `human_only` by licence. So this
is the same shape as the cash desk's POS1: **the position is the desk's entire
knowledge of the rule**, written in the firm's words, with a citation only so a
reader can go and look. That is exactly what `positions/` is for and it is not a
weakness.

---

## Open — five decisions, with both outcomes

### Q1 · How many vehicle accounts should a trades client have?

The firm rejected the question as posed:

> *"we shouldn't be like is it one or four we should be like OK how many accounts
> should it be what other reasons could there be for that like I'm assuming we
> want to know the reasoning so I had to give us the reasoning as well"*

**What it turns on:** whether a client may switch between the standard mileage
rate and actual expenses. The actual-expense method needs fuel, repairs, tyres,
servicing and registration itemised, and a blended total cannot be taken apart
afterwards.

| | |
|---|---|
| **One blended account** | Simplest chart, matches what clients already have. Costs a rebuild at return time, every year, for any client who might use actual expenses. |
| **Split** | More accounts on every trades client forever. Makes the switch free and the return preparable from the books as they stand. |

**Recommendation: split.** The cost of splitting is paid once at setup; the cost
of blending is paid every year by whoever prepares the return. But the number and
the names are the firm's — a recommendation to split is not a chart.

### Q5 · What distinctions must the meals accounts carry?

Framing rejected here too:

> *"Book them or refuse them is too narrow of a question to me this is more like
> the first question in the sense that it is how many accounts do we need to
> account for what the client does and how do we find that out"*

**What it turns on:** the same cost is 100%, 50% or 0% deductible depending on
what it was, and a single Meals account throws that away.

**Held.** The meals desk being built now should come back with the actual
categories the regulation makes, and the chart question is answered against that
rather than against a guess. **This is the one decision here that should wait.**

### Q32 · Is unreceipted cash a draw?

> *"Cash withdrawn with no receipt is an owner draw under most firm policies. Is
> it under this firm's?"* — the closing agent. The firm has not said.

| | |
|---|---|
| **Yes, always a draw** | Unambiguous, closes every one of them, never wrong in a way that costs the client a deduction they can substantiate — because they cannot. |
| **Held pending the client** | Recovers real deductions where the client does have receipts they have not sent. Leaves rows open and blocks closes. |

**Recommendation: a draw, with the client told what it would take to change it.**
Neither costs anything that cannot be corrected, and only one of them closes.

### Q37 · What is the standard evidence for deposit income?

> *"the firm should pick one rather than deciding per client."*

The candidates: the bank's own deposit detail, the invoicing system, or a list
from the client. **Recommendation: the bank's deposit detail as the default**,
because it is the one document the firm can obtain without the client doing
anything — and the one that exists whether or not they invoice.

**What it costs:** deposit detail does not carry a payer on a mobile cheque
deposit, which is Q27's problem restated. The default has to be paired with what
happens when it comes back blank.

### Q42 · Transaction date or post date?

The book runs on transaction date; card statements close on post date. They
disagree at every period boundary by whatever is in transit.

**Recommendation: transaction date, always.** The closing agent's own note says
the acceptable direction is the book ahead of the statement, which is what
transaction date produces. **Confirm rather than assume** — this is stated from
one close, not from a rule.

---

## And one that is not a decision but a conviction

Said three separate times, on Q4, Q18 and Q19:

> *"this is another safe harbor moment for me like you don't have to defer to
> safe harbor but if there's no reason not to I feel like you might as well in
> general"*

That is broader than any of these seven — it is a rule about how the firm
approaches every election in the code. It belongs in `canon/CONVICTIONS.md` and
**not one word of it goes there without an explicit yes**, which is the whole
discipline of that file.

---

# Answered — the firm, 5 September 2026

All nine returned on the docket at `claude.ai/code/artifact/b3bbfa5b`. Their words
are quoted exactly; what each caused is recorded beside it.

| | Matter | Answer |
|---|---|---|
| M1 | Merge #264 | **Merge it** |
| M2 | Vehicle accounts | **Split it** |
| M3 | Meals accounts | **Three accounts** |
| M4 | Unreceipted cash | **Always a draw** — *"draw and client confirm"* |
| M5 | Deposit income evidence | **Bank deposit detail** — and a conviction, below |
| M6 | Transaction or post date | **Transaction date** |
| M7 | Card rewards | **"I'll read it first"** |
| M8 | Per-citation subject mapping | **Build and measure it** |
| M9 | Document requests | **Wire it up properly** — *"but not direct to client"* |

## What each one caused

**M1 · Merged**, as `9a976ce`. It ratifies POS1 and POS2 on the cash desk and
closes #266. `main` had moved twice under us and the merge conflicted; resolved
by taking the other session's `release.py` fix, keeping both log entries, and
re-releasing canon at **1.12.0** over the union — because two sessions had each
cut 1.11.0 on the same afternoon, which is the second time in one day that a
version described a record it did not contain.

**M2 · Split.** The chart is theirs and the split is decided. **What goes in each
account is now desk work**, because Publication 463 names the categories itself:
depreciation, lease payments, registration fees, licenses, insurance, repairs,
gas, garage rent, tires, oil, tolls, parking fees. The firm's own reasoning for
splitting, which is better than the one this file first offered:

> *"hopefully if i split it into more accounts the agent is then smart enough to
> ask what goes where which an authority should be able to help with"*

Splitting turns one unanswerable question into twelve answerable ones. **And the
publication splits parking against itself** — business parking deducts, parking
at your own place of work is a nondeductible commuting expense. Same merchant,
two answers, and the deciding fact is where he parked: `facts_not_established`,
not an authority gap.

**M3 · Three.** 50% under § 1.274-12(a)(2), 100% under a named § 1.274-12(c)
exception, 0% for entertainment under § 1.274-11(a). Held on the last docket
until the meals desk reported what the regulation actually makes; it made three.

**M4 · A draw, and the client is told.** *"draw and client confirm"* — so the
draw is booked and the client is asked what would change it, rather than the row
being held open.

**M5 · The bank's deposit detail**, plus the reasoning that matters more than
the answer. See the conviction below.

**M6 · Transaction date.** The books say when the money was spent. The timing
difference at each year end is the ordinary kind, explained on the reconciliation.

**M7 · Held, correctly.** *Anikeev v. Commissioner*, T.C. Memo. 2021-23 is the
only place the rewards answer has been tested, and no host carrying court
opinions is reachable from this environment. **POS1 on the rewards desk stays a
proposal until the firm has read it.** Nothing else on that desk is blocked.

**M8 · Build and measure it.** The last known way the engine can serve a
confidently wrong answer. To be built the same way the shape it replaces was
chosen: build, run against every desk, count the right answers it wrongly
refuses, and only let it block at zero.

**M9 · Wire it properly — and route it to the firm, not the client.**

> *"but not direct to client - things would be wired to go to me as the last
> resort right now"*

That is a constraint on the design, not a detail of it. A desk that concludes
*request the loan statement* raises it to the preparer, who decides whether to
ask the client. Nothing reaches a client without a person in between.

---

## A conviction, proposed and NOT recorded

M5's note is not an answer about deposits. It is a statement about what the firm
is, and it bears on far more than the matter it was written under:

> *"and if we use their csv - i assume it's real, my clients are not trying to
> pay tax on money to look like they make more and we don't provide assurance
> services. we record things and ask what we must to know it's right"*

**Why it matters beyond M5.** It settles what a desk may treat as evidence.
`facts_not_established` was added because a rule can be clear while a fact is
missing — and this says how that fact is allowed to arrive. The client's own
statement is evidence. The threshold is *what we must ask to know it is right*,
not *what would survive an audit*, because the firm does not sell assurance.

It also resolves, in one line, a question three desks escalated tonight and one
the firm already answered by instinct on the groceries — *"the client had already
told me that he could guarantee they were deductible and honestly I will believe
the guy."*

**It is not in `CONVICTIONS.md` and will not be until the firm says yes to
recording it as one.** They wrote the words under a different question; that is
not the same as ratifying them as a standing rule.
