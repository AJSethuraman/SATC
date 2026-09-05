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
