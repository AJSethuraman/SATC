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

---

# Answered — the second docket, 5 September 2026, 11:39–11:45 UTC

Returned at `claude.ai/code/artifact/2baf0b4f`. Their words are quoted exactly.

| | Matter | Answer |
|---|---|---|
| D1 | Three finished pull requests unmerged | **Drive all three** |
| D2 | Four website pull requests since August | **Something else** — they are taking it |
| D3 | Three scoreboard drafts | **Keep them as history** |
| D4 | Seventeen positions still proposals | **Walk me through them one at a time** |
| D5 | Anikeev | *answered by handing over the opinion itself* |
| D6 | The conviction | **No** |

## D6 · Declined, and the reason is worth more than the entry would have been

> *"No, this isn't a particular conviction. I'm trying to write out. This is just
> point of fact."*

**It does not go in `CONVICTIONS.md`, and that is correct.** They are drawing a
line the record did not have: between a **conviction** — something they believe,
which could turn out to be wrong, and which Bassy is meant to challenge them
from — and a **point of fact** about what the firm is. *"We don't provide
assurance services"* is not a belief about accounting. It is a description of the
business, true whether or not anybody agrees with it.

**The distinction is load-bearing for the desk anyway.** What a desk may treat as
evidence still turns on it: the threshold is *what we must ask to know it's
right*, not *what would survive an audit*, because an audit is not the product.
That belongs somewhere — but somewhere for facts about the practice, not in a
file whose whole discipline is that every line is a belief the firm chose to hold.

**Recorded as declined. Nothing was written to the record.**

## D2 · Theirs, with one observation left for them

> *"Confused because pricing is already live on the site. In any case this isn't
> your problem I'll look and come back maybe"*

Their confusion is worth keeping: **if the published prices are already live,
then #158 and #160 may describe work that reached the site another way**, which
would make them stale rather than pending. Not checked here — `website/` belongs
to another agent and this session does not touch it.

## D5 · Answered by handing over the opinion

They did not tick a box. They pasted the full text of *Anikeev v. Commissioner*,
T.C. Memo. 2021-23 — the case no host reachable from this environment would
serve. **The wall was real and a person walked through it in the time it takes to
paste.** Digested separately; what it changes is recorded with the rewards
position.

---

# The docket of 5 September 2026 — twenty-two answered

Read back out of the page's own store (artifact `8df0c974`, collection
`decisions`) rather than out of a conversation, on 5 September 2026. **All
twenty-two were answered.** Thirteen positions were ratified, eleven unamended
and two with an edit; four were held; five decisions were made.

## What the answers changed in the record

| | before | after |
|---|---|---|
| positions ratified | 2 | **15** |
| positions proposed | 17 | **4** |

**No scored problem moved, and that was checked rather than assumed.** Not one
of the thirteen newly ratified positions sits on a citation any of its own
desk's problems turn on — measured after ratifying, per desk. `test_guards.py`
now proves it the hard way: for such a desk it grades escalate-everything with
the positions and again with `positions=()` and requires the two scores to be
identical. So the claim "these change what the desk says when it cannot answer,
not what it scores" is now a test rather than a sentence.

## The wording rule they gave while ratifying

> *"I want to ensure that where when you say my words, they're not the direct
> quotes I do like the convictions and stuff, including direct quotes, so we can
> kind of remember where they came from but positions that the agent finds to
> argue from should be cleaned up"*

And, on the airfare position:

> *"I don't want our desk to have this much like of my thought behind it so much
> as I'm giving you my perspective and how I hope things can work."*

**So: a conviction keeps the quote; a position is cleaned up.** Every `Ratified:`
line written from this docket is prose, not transcription. Their words stay here,
in the log, where the provenance belongs. Recorded in `positions.py` so the next
session writing a position reads it before writing one.

## The two ratified with an edit

**`vehicle-expense/POS4` — the reviewer has to be told.**

> *"But things like this, when there could be a subjective component should
> probably be marked for the reviewer to make sure there is a question to be
> asked or something"*

The position now ends *"and mark the line for the reviewer so the question is put
to the client rather than left implicit"*.

**`vehicle-expense/POS5` — do the work, then confirm; do not just hold.**

> *"No, I'd rather do the work because it's not difficult for the AI to process
> it or for tools to process it or whatever and then for us to confirm with the
> client ... I would prefer to do the work correctly and confirm then have to go
> back and fix it if we were supposed to do it"*

Holding the line was the drafted answer and they rejected it. The position now
assembles what the file shows, puts the ownership question to the client, and
sets the treatment on their answer.

## The four they held, and what each is waiting for

**`capitalization/POS1` — the safe-harbour election.** Held as a default, not a
rule: *"This is the kind of policy that gets enacted because it makes sense and
only enacted when we don't have another Answer for instance it's possible for a
particular client we have to be needed treating differently."* **What it needs:**
a way for a position to be the firm's default and still be overridden for a named
client. The record has no such shape today — every position is unconditional.

**`capitalization/POS2` — the threshold.** Held on a question, and the desk
already holds the answer: *"I feel like I need to understand why would a
confidently said $500 like where did this number come from?"*

- **§ 1.263(a)-1(f)(1)(ii)(D)** is where the $500 comes from. It is the number in
  the regulation, and it was never amended.
- The same sentence delegates: *"or other amount as identified in published
  guidance in the Federal Register or in the Internal Revenue Bulletin"*.
- **Notice 2015-82** is that guidance. Per the IRS's own page, held in this
  desk's `S3.md`: it *"increased the de minimis safe harbor threshold from $500
  to $2500 per invoice or item for taxpayers without applicable financial
  statements"*, effective for tax years beginning on or after 1 January 2016, and
  $5,000 where there is an applicable financial statement.

So the regulation is not stale and the $2,500 is not a number somebody
remembered — it is the amount the regulation points at. **The desk could have
answered this; nobody asked it.**

**`personal-or-business/POS1` — the vendor is not the test.** Held on a real gap:

> *"there should be some inference in the sense that the Accountant should've
> already recorded and known what sort of business we're dealing with ... it makes
> it a lot easier for me to look at a Home Depot charge from a general contractor
> and think that it's a business expense versus looking at a Home Depot charge
> from a hairstylist"*

**What it needs:** the client's trade as an input the desk actually receives.
`ask.consult` takes a question and nothing else today, so the desk cannot know
whether it is looking at a contractor or a hairstylist. This is a hole in the
front door, not in the position.

**`rewards/POS1` — card rewards.** Held, and it asks for two things:

> *"generally speaking I've always seen that credit card rewards are not taxable
> for a person and this makes me think that we should probably be specifying. Hey
> this is the individual desk. This is the business desk. Also, how do we get the
> desk to understand that like sometimes the correct answer may be deduced because
> if we don't have an opinion and have a good reason to form one, maybe we just
> use a safe Harbor Rule which, in this case would be deferring to whatever the
> IRS says"*

**What it needs:** (1) a desk to know which return it is answering for —
individual or business; *Anikeev* is a personal return and nothing in the record
says so structurally. (2) A stated fallback: where the firm has no position and
no reason to form one, follow the IRS's own published position. That is a rule
about how to answer, and it does not exist in `engine.REASONS` today.

## The five decisions

**Q32 · unreceipted cash — `Always a draw`.** No qualification given.

**Q42 · dates — `Transaction date`.** No qualification given.

**Q37 · what proves a deposit is revenue — `Bank deposit detail`**, and the
qualification matters more than the choice:

> *"we are not their invoicing system at least right now and the desk needs to
> probably understand what kind of engagement that the accountant is doing ... yeah
> I'm just gonna assume everything is revenue unless you tell me otherwise I'll
> try to ask follow up questions to make sure that they are definitely revenue
> like hey is everything from this particular vendor revenue? Is this check
> revenue? But yeah, dude, I'm not doing three-way matching unless we're being
> paid for it or something"*

So the policy is: **deposits are revenue unless something says otherwise**, with
targeted follow-ups by payer or by item — and the depth of verification is a
function of the engagement, which the desk does not currently know either. That
is the same missing input as `personal-or-business/POS1`.

**Desk size — `Not yet`.** Not a refusal, a deferral with a constraint:

> *"For now, I'm fine. Developing these to work on Claude and then we can figure
> it out with a local model. I would hope that, however their development should
> still work on a local model, even if we can't technically run it in the sense
> that none of the script or prompting or anything would mess it up"*

**The constraint is the finding:** nothing built now may depend on a large model
to be *correct* — only to be *fast*. Routing is already a word comparison and the
gate is already code, so both survive a swap. The briefs are what would not.

**Court opinions — `Keep them closed`, and the note pulls the other way:**

> *"I want to open everything we can use. We should just kind of determine what
> good sources are out there cause like there's no reason for them not to use
> this court case I don't want to be the one to answer it. The only reason we are
> talking so much now is because I can't trust the answers"*

**Recorded as answered and flagged as contradictory rather than resolved by me.**
The button says keep the hosts closed; the words say open what we can and stop
making the firm the source of last resort. Taken as: the choice stands for the
five blocked hosts, and the real ask is a wider set of *reachable* authority.
Put back to them rather than decided here.
