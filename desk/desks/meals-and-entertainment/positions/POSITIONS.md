# Positions — what the firm does where the rules permit a choice

**An agent proposes here. It never writes.** The pull request is the firm's yes,
and a position that entered any other way is one they will disown the moment it
is read back at them.

Each entry carries the firm's **own words**, the authority it rests on, and the
date. Where a source cannot be read by a desk at all — a licence forbidding the
content reaching a model — a position here is the desk's entire knowledge of it,
and the citation is how a reader gets to the text themselves.

**Every entry below is a PROPOSAL.** None carries a `Ratified` field, so none of
them is served: `Desk.position()` returns only ratified ones, and until the firm
merges this file these four are worth exactly what a suggestion is worth.

**None of them is cited to a paragraph a problem is keyed to**, and that is
deliberate. A ratified position outranks the stored passage on the same citation,
so ratifying one that sat on M3's or M11's paragraph would silently re-answer
those rows from the position instead of from the regulation.

---

## POS1 · How many food-and-drink accounts the chart has to carry

**Citation:** 26 CFR 1.274-12(c)(1) · **Recorded:** 2026-09-05

**Position:** three accounts at least, split by the answer and not by the vendor: food or beverages at 50 percent, food or beverages at 100 percent under a named exception, and entertainment at nothing. A charge goes to the 100 percent account only where the record names which exception in § 1.274-12(c)(2) is being claimed. A single "Meals and Entertainment" account is refused, because the two halves of its name now have different answers.

**Why:** The question this answers was put as a binary and the firm rejected the framing. In their own words, 5 September 2026, on Q5: *"I think that Book them or refuse them is too narrow of a question to me this is more like the first question in the sense that it is how many accounts do we need to account for what the client does and how do we find that out and what do we need to know anyway maybe these are the kinds of questions that we should be aware of or the agent should be like OK these are good follow-ups to a question like this and these are similar follow-ups to the question just before because whether or not it is deductible to a certain point also largely depends on who it was with when it was et cetera if it was travel it's almost definitely deductible as long as we trust the expense"*

And on Q6, 5 September 2026: *"I'm just going to say the same thing as above like with the meals question you know entertainment slash meals they're very subjective in these natures so it makes more sense to maybe have some sort of like client rule but it also makes sense just generally speaking for the agent to ask a question that then provokes questions like OK well how many accounts may we need anyway"*

The regulation is what makes three the floor rather than a preference. § 1.274-12(a)(2) caps a food or beverage expense at 50 percent; § 1.274-12(c)(1), the citation above, says the cap does not apply at all to an expense described in (c)(2) and that those are deductible to the extent chapter 1 allows; and § 1.274-11(a) disallows entertainment outright. Three answers, so at least three places to put a charge — and a chart with fewer cannot record which one was reached.

**What this position does not settle**, said plainly because it is the part the firm asked about: *how we find that out*. The chart being right is necessary and not sufficient; nothing in a bank feed says who was at the meal or why.

**Ratified:** the firm, 5 September 2026 — ratified on the docket, and marked as a general test worth trying on other accounts: split the chart by the answer the rules give, not by the vendor's name.

---

## POS2 · A brewery or taproom charge is neither automatically entertainment nor automatically a meal

**Citation:** 26 CFR 1.274-11(b)(1)(i) · **Recorded:** 2026-09-05

**Position:** a charge at a bar, brewery or taproom is a food or beverage expense at 50 percent unless the record shows the drink was provided at or during an entertainment activity, in which case it follows the entertainment. Where the record shows neither, the line is held for the client to answer and is not booked to owner's draws on the strength of the vendor's name.

**Why:** The firm's words, 5 September 2026, on Q6: *"I'm just going to say the same thing as above like with the meals question you know entertainment slash meals they're very subjective in these natures so it makes more sense to maybe have some sort of like client rule but it also makes sense just generally speaking for the agent to ask a question that then provokes questions like OK well how many accounts may we need anyway"*

The regulation cuts both ways here and that is why this is a position rather than a lookup. § 1.274-11(b)(1)(i), the citation above, names *"entertaining at bars"* in its own list of what entertainment means. But § 1.274-11(b)(1)(ii) says the term entertainment *"does not include food or beverages unless the food or beverages are provided at or during an entertainment activity."* A beer bought at a bar is a beverage; the bar becomes entertainment when there is an entertainment activity for it to be provided at or during. The vendor's merchant category does not decide which of those happened, and the closing agent's rule — breweries to owner's draws — decides it by the name over the door.

**Ratified:** the firm, 5 September 2026 — ratified on the docket, unamended.

---

## POS3 · A supermarket charge is held, not booked, until the record says which exception is claimed

**Citation:** 26 CFR 1.274-12(a)(1) · **Recorded:** 2026-09-05

**Position:** groceries bought on a business card are food or beverages under § 1.274-12(b)(1) and are 50 percent at most, and 100 percent only where the record names the § 1.274-12(c)(2) exception relied on. Where nothing in the record establishes that the taxpayer or an employee was present and that the food went to the taxpayer or a business associate, the line is flagged for the client and is not booked either way.

**Why:** The firm's words, 5 September 2026, on Q7: *"the client had already told me that he could guarantee they were deductible and honestly I will believe the guy however this is a great question and I think that like the j.crew thing it may at least instead of being booked to owners drawers be flagged for attention or something"*

**THE PART THIS DESK CANNOT HOLD, AND WILL NOT PRETEND TO.** The firm's actual basis for the answer is that the client told them and they believe the client. Nothing in this record can carry that. A desk answers from `SOURCES.md` and `positions/`, and there is no third store for *what the client said*, *what the client is*, or *what experience suggests* — the three registers the firm names across Q7, Q8 and Q20, the last of which they explicitly say must not be trusted blindly. So this position deliberately stops at *flag it*, which is the half of the firm's own answer the record can actually implement. Building the other half is not a wording change here; it is a new kind of evidence the engine has no shape for, and it is written into the report rather than modelled.

The regulation is only the floor. § 1.274-12(a)(1), the citation above, allows nothing at all unless the expense is not lavish, the taxpayer or an employee was present, and the food went to the taxpayer or a business associate. A supermarket receipt establishes none of those three on its own.

**Ratified:** the firm, 5 September 2026 — ratified on the docket, unamended.

---

## POS4 · Airfare is not booked to Travel from a feed alone

**Citation:** 26 CFR 1.162-2(a) · **Recorded:** 2026-09-05

**Position:** an airline charge is held until the business reason for the trip is recorded. Booking it to Travel with the purpose still missing records a conclusion the file does not support, and the four elements § 1.274-5T(b)(2) requires — amount, time, place, business purpose — are cheap to get in the week of the trip and expensive to reconstruct in March.

**Why:** **THE FIRM HAS SAID NOTHING ON THIS.** Q13 is one of the twenty-three in `docs/CLOSE-QUESTIONS-2026-09-05.md` that carries no response, so unlike POS1 through POS3 there are no words of theirs to quote and this proposal is the agent's alone. It is recorded here rather than acted on for exactly that reason.

What the authority says, and it is unusually blunt. § 1.162-2(a), the citation above: *"If the trip is undertaken for other than business purposes, the travel fares and expenses incident to travel are personal expenses."* And § 1.274-5T(a), on the substantiation the fare needs regardless: the requirement *"supersedes the doctrine found in Cohan v. Commissioner"*, and § 274(d) *"contemplates that no deduction or credit shall be allowed a taxpayer on the basis of such approximations or unsupported testimony of the taxpayer."* An estimate at return time is not a fallback the regulation leaves open.

The closing agent's call — booked to Travel pending a stated purpose — puts a number on a line the record cannot yet support. The difference between that and holding it is which way the file reads if nobody ever comes back to it.

**Ratified:** the firm, 5 September 2026 — ratified on the docket, with the preference that the desk ask and follow up rather than assume, and on the understanding that keeping the record is the client's job unless the firm is engaged to do it.
