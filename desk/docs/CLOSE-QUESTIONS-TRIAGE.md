# What kind of question is each of the 43

**The finding, first.** Of the 43 questions a real close produced, **11 are
questions a desk can answer from citable authority.** The other 32 are not
authority questions at all — they have four other owners, and none of those
owners exists in the software yet.

That matters because `unsupported.from_question` defaults every question to
`authority_absent`. Filed that way, **32 of 43 would land in the wrong queue**,
where the resolution is "add the authority, cited" and no authority is missing.
They would sit there being counted as a gap in the record while the thing that
actually resolves them — a phone call, a document request, one decision from the
firm, or a bug fix — was never raised.

**This classification is a proposal and is argued with, not accepted.** It is one
session's reading of the firm's own words. Where a question could go two ways the
primary kind is the one whose owner has to move first, and the secondary is named.

---

## The six kinds, and where each came from

Not one of these was invented here. Each is either already in the engine's
reason set or is the firm's own phrasing from `CLOSE-QUESTIONS-2026-09-05.md`.

| Kind | What resolves it | Who owns it | Where it came from |
|---|---|---|---|
| **A · a rule settles it** | citable authority | a desk | `authority_absent`, already in `engine.REASONS` |
| **B · only the client has the fact** | asking the client | the preparer | `facts_not_established`, added from the J.Crew case |
| **C · a document settles it** | requesting it | the engagement's document list | *"there should be something telling us to get like loan statements and stuff to make sure we understand the deal"* (Q26) |
| **D · the firm decides once** | one ratified position | the firm | *"it's a good question and it has the answer in it ... to ratify on the spot if you can"* (Q4) |
| **E · a software defect** | a bug fix | this repository | *"is this an authority question or is this like the problem with the software kind of question"* (Q23) |
| **F · it changes nothing** | saying so | the desk, if it could | *"it's also useful for an agent to tell someone something doesn't matter is if that's possible"* (Q28) |

**Three of these six have nowhere to go today.** `unsupported.py` holds A and B.
C, D and F have no queue, no field and no outcome. E belongs on the issue
tracker and is not a desk matter at all.

---

## The count

| Kind | Count | Share |
|---|---:|---:|
| A · a rule settles it | 11 | 26% |
| B · only the client has the fact | 11 | 26% |
| C · a document settles it | 8 | 19% |
| D · the firm decides once | 7 | 16% |
| E · a software defect | 5 | 12% |
| F · it changes nothing | 1 | 2% |
| **Total** | **43** | |

**Read it the right way round.** 26% is not a disappointing desk. It is the
share of a real close that expert authority can take over, measured on real
questions rather than on a set we wrote — and the first honest number this
project has had. The other 74% is not desk work and never was.

**A and D together are 18 of 43 (42%)** and both end in something written down
once that never has to be decided again. That is the number worth watching.

---

## Every question, classified

`+` marks a secondary kind: the question has a second owner once the first has moved.

| Q | Subject | Kind | Also | Why this kind |
|---|---|---|---|---|
| 1 | vehicle: one account or four | **D** | A | The firm rejected the binary. What the chart must distinguish is their call; the rule only says what the return needs itemised. |
| 2 | vehicle used for business only | **B** | | Needs a mileage log or the client's word. No rule supplies it. |
| 3 | whose vehicle is it | **B** | C | Title, lease or loan paper settles it — but somebody has to ask first. |
| 4 | capitalisation threshold | **A** | D | The safe harbour states the limit; electing it is the firm's, once. |
| 5 | meals: book or refuse | **D** | A | Framing rejected by the firm. The rule gives the percentages; the chart is theirs. |
| 6 | is a brewery a meal | **A** | | § 274 settles entertainment outright. |
| 7 | are groceries deductible | **A** | B | The rule gives the test; what was bought is the client's fact. |
| 8 | is this clothing deductible | **A** | B | § 1.262-1(b)(8) is the test and it has no vendor in it. |
| 9 | are card rewards income | **A** | | The firm asked to be told for sure. Authority exists or it does not. |
| 10 | municipality: permit, tax or draw | **C** | | *"The town's bill settles it in one look."* |
| 11 | convenience fee implies a missing payment | **C** | E | Which account paid it is data nobody holds; that nothing noticed is separate. |
| 12 | 1099-NEC obligation | **A** | | A threshold and an exemption list, both citable. |
| 13 | is airfare business travel | **B** | | The rule needs a business purpose; no feed carries one. |
| 14 | inspection fee: job cost, permit or rebill | **B** | | The firm knew the answer from knowing the client. |
| 15 | which policies the premium covers | **C** | | The policy schedule settles it. |
| 16 | tool or fixed asset | **A** | | The same threshold as Q4, from the asset side. |
| 17 | vehicle expense and no vehicle | **B** | | The asset is somewhere; only the client says where. |
| 18 | hardware purchase as an asset | **A** | F | *"having an answer to something like the first question could immediately make all other questions basically not matter."* |
| 19 | materials held at year end | **D** | A | The firm already decided: no inventory tracking, take the safe harbour, charge for it if forced. |
| 20 | unnamed account: owner's or business's | **B** | | *"no answer beats a guess, because the guess changes equity."* |
| 21 | is the processor balance a cash account | **B** | | Turns on whether the business controls it. |
| 22 | does the client take cash | **B** | E | Unanswerable from a feed by construction — and nothing flags that. |
| 23 | card payment legs disagree | **E** | | The firm asked this exact question about this exact row. |
| 24 | one liability account per card | **B** | D | How many are actually business cards is a fact; the chart is then policy. |
| 25 | is a store-card payment a purchase | **E** | B | A rule keyed on a merchant name cannot see the difference. That is a defect. |
| 26 | is a loan hiding in the deposits | **C** | | *"there should be something telling us to get like loan statements."* |
| 27 | what proves a deposit is revenue | **D** | | The firm accepts the default and would advise clients into it. |
| 28 | processor income gross or net | **F** | | *"I'm not really sure why this matters."* Profit is right; both lines are wrong by the same amount. |
| 29 | are rewards revenue | **A** | | Q9. |
| 30 | should the engine ship an interest rule | **E** | | A missing standard rule is a product gap. |
| 31 | personal spending is a draw, not an exclusion | **A** | E | Booking it nowhere breaks the bank reconciliation; the software's own choice does that. |
| 32 | is unreceipted cash a draw | **D** | | *"under most firm policies. Is it under this firm's?"* |
| 33 | is streaming television a subscription | **A** | | § 262. |
| 34 | personal medical: draw or workers' comp | **B** | | Turns on whether it was a job-site injury. |
| 35 | is there a home office | **B** | | Nobody has said whether one is claimed. |
| 36 | what settles an unidentifiable cheque | **C** | E | The image or the register — and whether it blocks a close is separate. |
| 37 | standard evidence for deposit income | **D** | | *"the firm should pick one rather than deciding per client."* |
| 38 | marketplace order history as a standard request | **C** | | *"resolves every one of them and nobody asks for it."* |
| 39 | payments to a card we hold no statements for | **E** | C | Nothing notices. That is the defect; the statement is the remedy. |
| 40 | whose job is pairing a transfer | **E** | | The matcher's, and it did not. |
| 41 | a statement cycle that does not end at year end | **C** | E | The February statement was requested; the derivation was correctly refused. |
| 42 | transaction date or post date | **D** | A | One convention, chosen once, applied everywhere. |
| 43 | payroll sweep and the wage cost | **C** | | Without the payroll register the split cannot be made. |

---

## What this says to build, in order

1. **The 11 A-questions are the desk backlog** and four desks are being built
   against them now. That is the only part of this the desk can carry today.
2. **C has no home at all.** Eight questions resolve by asking for a document,
   and `client-documents/` already runs the engagement's document list. The
   answer *"request the loan statement"* should be an outcome a desk can return,
   not a sentence in a report nobody actions.
3. **D is seven ratifiable positions.** Five of them the firm has already
   answered in this very file, in their own words. They are proposals waiting to
   be written, not questions waiting to be asked.
4. **E is five issues** and does not belong to this project.
5. **F is one question and one missing outcome.** The engine cannot say *this
   changes nothing*, so it has to escalate instead — which sends a question that
   needed no answer to a human who then has to decide it does not matter.
