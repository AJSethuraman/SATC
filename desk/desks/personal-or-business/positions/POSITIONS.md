# Positions — what the firm does where the rules permit a choice

**An agent proposes here. It never writes.** The pull request is the firm's yes,
and a position that entered any other way is one they will disown the moment it
is read back at them.

Each entry carries the firm's **own words**, the authority it rests on, and the
date. Where a source cannot be read by a desk at all — a licence forbidding the
content reaching a model — a position here is the desk's entire knowledge of it,
and the citation is how a reader gets to the text themselves.

**All three below are PROPOSALS. None carries a `Ratified` field and none of them
answers anything today** — `Desk.position()` returns only ratified ones, so until
the firm merges these the desk behaves exactly as it does without them.

**Read the citations before the positions.** POS1 rests on the sentence of
§ 1.262-1(b)(8) that states the *test*, deliberately not on the following
sentence that gives the sword and the uniform — and PB4 and PB5 are keyed to that
second sentence. They are split for the reason the cash desk found the hard way:
one citation admits one position, and a position written over a whole paragraph
refused that desk's own correct problems. Ratifying POS1 cannot make PB4 or PB5
unanswerable, because it does not sit on their citation.

---

## POS1 · The vendor is evidence about what was bought. It is not the test

**Citation:** 26 CFR 1.262-1(b)(8) — the test for a serviceman's equipment · **Recorded:** 2026-09-05

**Position:** ask what the item is and what the profession requires; who sold it is evidence about what was bought and never the answer

**Why:** The firm, on an agent that classified a client's J.Crew purchases as
personal — quoted in the brief that commissioned this desk, and recorded in
`engine.py` as the firm, 5 September 2026:

> *"the thing with J Crew is as a human i just google it and see it's a clothing
> company and can tacitly understand what my client was buying there. i could
> even flag it to ask the client. no matter what, its answer was wrong.
> authoritative source for 'what does a company do' is quite literally just what
> the company says it does / the rest is exactly the kind of argument i'm looking
> for our agent to be able to make through its review and challenge system"*

And on the same question in the close, 5 September 2026
(`docs/CLOSE-QUESTIONS-2026-09-05.md`, Q8):

> *"see I don't understand how distinguished and we talked about the j.crew thing
> so you know. I think knowing the client also helps not like literally knowing
> them but knowing that they're a contractor it's like I'm more willing to
> believe that they're going to shop at places that I normally wouldn't and where
> those things for work especially because of where they live"*

**THE REGULATION MAKES THIS POINT WITHOUT ANY HELP FROM US, AND THAT IS WHY THIS
IS PROPOSED AS A POSITION RATHER THAN ARGUED.** § 1.262-1(b)(8) asks whether the
item "is especially required by his profession and does not merely take the place
of articles required in civilian life". Every term in that sentence is about the
item and the profession. There is no seller in it. Then it works the test twice
and comes out both ways — the sword is allowed and the uniform is refused — and a
sword and a uniform are bought at the same kind of shop. PB4 and PB5 are that
pair, written as one purchase history at one clothing outfitter. A desk reasoning
from the vendor answers them identically and is therefore wrong on exactly one,
with no way to know which.

The firm's own reading, that a contractor might legitimately shop where the
preparer would not expect, is the same proposition from the other end: the seller
narrows what was probably bought and settles nothing.

---

## POS2 · Where the rule is clear and what was bought is not, flag it and ask

**Citation:** 26 CFR 1.262-1(a) — the general rule · **Recorded:** 2026-09-05

**Position:** flag it for attention and ask the client what was bought; do not book it to owner draws on the seller's name

**Why:** The firm, 5 September 2026 (`docs/CLOSE-QUESTIONS-2026-09-05.md`, Q7):

> *"the client had already told me that he could guarantee they were deductible
> and honestly I will believe the guy however this is a great question and I
> think that like the j.crew thing it may at least instead of being booked to
> owners drawers be flagged for attention or something"*

And, on the J.Crew case itself: *"i could even flag it to ask the client."*

This is not a new mechanism being asked for. `engine.REASONS` already carries
`facts_not_established` — "the rule is clear; what was bought is not. ASK." — and
its comment says it was added from this exact case. The position is that the desk
**uses** it here rather than reaching for a conclusion: § 1.262-1(a) refuses a
deduction for personal, living and family expenses, and on a card line carrying a
seller and an amount the desk holds the rule and does not hold the fact the rule
asks about. Booking to owner draws to make the file tidy is a conclusion wearing
a bookkeeping entry's clothes, and the firm has said twice they would rather see
the flag.

**What this position does not cover, said plainly.** Whether the offsetting entry
is an owner draw or something else is a bookkeeping question and neither
§ 1.262-1 nor § 1.162-1 contains a word about it. This desk can say a cost is not
the business's. It cannot say from this authority what the books should do about
the money that left the account.

---

## POS3 · A cleaning service is a household cost until part of the home is shown to be the place of business

**Citation:** IRS Pub. 587 (2025), "Actual Expenses" — utilities and services · **Recorded:** 2026-09-05

**Position:** treat it as the owner's household expense, and ask whether any part of the home is used regularly and exclusively for the business before treating any part of it as the business's

**Why:** THE FIRM HAS NOT SPOKEN ON THIS ONE. Q35 in
`docs/CLOSE-QUESTIONS-2026-09-05.md` is one of the twenty-three they did not
answer, so there is nothing of theirs to quote and this is a proposal in the
plainest sense: the desk's reading, waiting for their yes or their correction.

It rests on two texts that agree. Pub. 587 (2025) says expenses for services
"such as electricity, gas, trash removal, and cleaning services, are primarily
personal expenses", and that the business part becomes deductible only "if you
use part of your home for business". § 1.262-1(b)(3) says the same thing from the
primary side, listing "domestic service" among the expenses of maintaining a
household that are not deductible, and then allowing the portion "properly
attributable to" a place of business inside the house. Both stop at the same
missing fact.

**And that missing fact is not authority.** `docs/CLOSE-QUESTIONS-TRIAGE.md`
classifies Q35 as kind B, only the client has the fact — *"Nobody has said whether
one is claimed."* Adding home-office authority to this desk would not have helped;
this position is what the desk should do while the question is out.

**Why it is proposed against the publication and not the regulation.** Pub. 587 is
secondary, which is precisely where a position belongs — the interpretive text is
the thing that invites a choice. It is also the only home-office authority
reachable at all: § 280A has no final regulations, and 26 CFR 1.280A-1, 1.280A-2
and 1.280A-3 each returned 404 from the eCFR versioner on 5 September 2026.
