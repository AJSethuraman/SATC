# The close-out pilot — 43 questions put to the desks

**8 September 2026 · desk 0.17.0 · `runs/asked-2026-09-08/`**

**This is NOT the firm's end condition, and an earlier version of this line said
it was.** The firm's words are *"get this piloted through the close out"*; the
clause below — *one close's questions put to the desks, with a written record of
every answer served, every refusal and what it asked for, and the questions the
desks never saw* — was **written by a session** in
`DECISIONS-2026-09-07-SEVENTH.md:67`, which labelled it honestly as *"the goal,
set by the firm **and shaped here**"*. This document dropped the caveat and
re-attributed the shaping to the firm; a docket then published it as *"the
firm's goal, set on 7 September 2026"* under a heading saying silence approves
it. When the firm later answered *"The pilot is still the goal"*, they were
confirming a definition they never wrote.

**The firm's actual V1 bar**, verbatim, `desk/relay.py:5-9`:

> *"the final check for this for V1 will be to have Forge - Occam install the
> new plugin we are designing and run a close from start to finish on Sarcia
> Services [...] this implies that the skill is able to call for questions and
> receive back answers from Forge - Desk"*

**By that bar this run does not count and the goal is not met.** What follows is
a paper exercise run in a cloud container on 43 archived questions. Its findings
are real; its status is not a pilot. Corrected 8 September 2026 after Count Bassy
traced the substitution through three files.

**No engagement facts were loaded before the run, on purpose.** The firm, on
the docket the same morning:

> *"the pilot needs to ensure we have these things. that is part of the
> pilot. why would we use stand-ins? the entire point of this pilot is for us
> to test whether the desk asks for the info and whether the principal gives
> it back and if they can. if they cannot, then that would be the type of
> thing that stands out as "this is a missing field we need"."*

So a refusal here is not a failure of the run. It is the run's output.

---

## The denominators

| | |
|---|---:|
| questions the close produced | 43 |
| put to a desk | **11** |
| never put to a desk | **32** |
| briefs written (a question may reach more than one desk) | 21 |
| the engine would serve | **7** |
| the engine would refuse | **14** |

**The 11 are not a shortfall of routing — all 11 that should reach a desk
did.** The other 32 are not authority questions at all. `CLOSE-QUESTIONS-
TRIAGE.md` sorts them into five other kinds, and this run is the first thing
to put a number on what that costs.

| Kind | What resolves it | Count | Where it can go today |
|---|---|---:|---|
| **A** a rule settles it | citable authority | 11 | a desk — this run |
| **B** only the client has the fact | asking the client | 11 | `unsupported.py` |
| **C** a document settles it | requesting it | 8 | `unsupported.py` |
| **D** the firm decides once | one ratified position | 7 | **nowhere** |
| **E** a software defect | a bug fix | 5 | the issue tracker |
| **F** it changes nothing | saying so | 1 | **nowhere** |

**Eight of the 43 have nowhere in the software to go at all** — the seven the
firm has to decide once, and the one whose answer is that it does not matter.
That is the largest single gap this pilot found, and it is not in a desk.

---

## What the desks served — 7 of 21

Whether each conclusion is RIGHT is the firm's to say. The engine only says
it may leave the desk: the citation resolves, it binds or carries the firm's
word, and its source is declared to answer this subject.

### Q6 · Is a brewery a meal? — `meals-and-entertainment`

> a charge at a bar, brewery or taproom is a food or beverage expense at 50 percent unless the record shows the drink was provided at or during an entertainment activity, in which case it follows the entertainment. Where the record shows neither, the line is held for the client to answer and is not booked to owner's draws on the strength of the vendor's name.

**Cited** `26 CFR 1.274-11(b)(1)(i)` · tier **primary**

### Q7 · Are groceries ever deductible? — `meals-and-entertainment`

> groceries bought on a business card are food or beverages under § 1.274-12(b)(1) and are 50 percent at most, and 100 percent only where the record names the § 1.274-12(c)(2) exception relied on. Where nothing in the record establishes that the taxpayer or an employee was present and that the food went to the taxpayer or a business associate, the line is flagged for the client and is not booked either way.

**Cited** `26 CFR 1.274-12(a)(1)` · tier **primary**

### Q16 · Where is the line between a tool and a fixed asset? — `fixed-assets`

> The default is capitalisation: an amount paid to acquire a unit of property must be capitalised unless it falls under materials and supplies or the de minimis safe harbour election.

**Cited** `26 CFR 1.263(a)-2(d)(1)` · tier **primary**

### Q18 · Does a hardware-store purchase ever become an asset? — `fixed-assets`

> Yes — where the purchase is a unit of property rather than a consumable, it must be capitalised, and the supplier's name has no bearing on that.

**Cited** `26 CFR 1.263(a)-2(d)(1)` · tier **primary**

### Q29 · Are rewards revenue at all? — `rewards-and-information-returns`

> No — a rebate on something you bought is not income; it reduces what the thing cost.

**Cited** `IRS Pub. 525 (2025), "Cash rebates"` · tier **secondary**

### Q31 · Personal spending on a business card is not excluded — it is a draw — `cash-and-bank`

> an entry in the books

**Cited** `IRS Pub. 583 (12/2024), "Reconciling the checking account" — what the books are updated for` · tier **secondary**

### Q31 · Personal spending on a business card is not excluded — it is a draw — `personal-or-business`

> flag it for attention and ask the client what was bought; do not book it to owner draws on the seller's name

**Cited** `26 CFR 1.262-1(a) — the general rule` · tier **primary**

---

## Every refusal, and what it asked for — 14 of 21

Grouped by who has to move next, because that is the only thing a queue can
be worked from.

### `context_not_on_file` — 2

**The engagement file is empty — the principal has to record a fact.** This is the case the firm predicted. The desk is not asking the client anything; it is saying the engagement record has no answer on a fact it was built to consult. **The named fact is the missing field.**

**Q4 · What is the capitalisation threshold?** — `capitalization-and-de-minimis`

- **Fact the engagement must record:** `capitalization_rule`
- **Why:** 'IRS Tangible Property Final Regulations, "What is the de minimis safe harbor election?"' is the firm's default position (POS2), which holds unless this client is treated differently on 'capitalization_rule'. Nothing on file says either way, and a default applied without looking is not a default

**Q9 · Are card rewards income?** — `rewards-and-information-returns`

- **Fact the engagement must record:** `taxpayer`
- **Why:** 'PLR 201027015, LAW AND ANALYSIS' is answered by the firm's position POS1, which cannot be applied without taxpayer on file. That is the engagement's to record, not the client's to be asked

### `facts_not_established` — 6

**The rule is clear and a fact about the client is not — ask the client.** The authority settles the question the moment somebody answers the question in the `ask` column. Each one names the fact and what would settle it.

**Q7 · Are groceries ever deductible?** — `personal-or-business`

- **Asked:** Who consumed these groceries and where? Household food for the owner's family is personal under 1.262-1(a). Food bought to feed a crew at a job site is a business expense — and if it is, say whether it was provided at the site, because that changes the percentage as well as the answer.
- **Why:** escalated by the desk

**Q8 · Is this clothing deductible?** — `personal-or-business`

- **Asked:** What garment was bought, and does the trade require it as protective or specialised gear that would not be worn in ordinary life? Steel-toed boots or flame-resistant coveralls meet the test; jeans and t-shirts from the same receipt do not. The firm's ratified position on this citation is to ask what the item is — who sold it is evidence about what was bought, not the answer.
- **Why:** escalated by the desk

**Q18 · Does a hardware-store purchase ever become an asset?** — `capitalization-and-de-minimis`

- **Asked:** Can you get the itemised receipt for this purchase, not just the card total? The de minimis limit is per invoice or per item as substantiated by the invoice, so a $900 hardware-store charge could be one tool that is capitalised or thirty consumables that are expensed, and the bank line cannot tell them apart.
- **Why:** escalated by the desk

**Q18 · Does a hardware-store purchase ever become an asset?** — `cash-and-bank`

- **Asked:** Request the itemised receipt or supplier statement for this charge. Until the line detail is in the file the books cannot show what was bought, and the classification cannot be made from the bank feed alone.
- **Why:** escalated by the desk

**Q18 · Does a hardware-store purchase ever become an asset?** — `personal-or-business`

- **Asked:** Which job or property did this purchase go to? Materials for a client job or for business premises are the business's; materials for the owner's own home are personal under 1.262-1(a), whatever card paid for them.
- **Why:** escalated by the desk

**Q33 · Is streaming television ever a business subscription?** — `meals-and-entertainment`

- **Asked:** Where does this subscription play — a client waiting area or shop floor, or the owner's household devices? A screen running in a waiting room is a cost of the premises; the same service on a home television is personal.
- **Why:** escalated by the desk

### `wrong_body_of_authority` — 3

**The question reached a desk that does not hold its law.** Routing sent one question to two desks and only one of them holds the governing rule. The refusal is correct and cheap; it also says routing is broader than the record.

**Q4 · What is the capitalisation threshold?** — `fixed-assets`

- **Asked:** Put the threshold question to the capitalisation-and-de-minimis desk, which holds 1.263(a)-1(f). This desk can say whether a given item is a unit of property, not what the expensing ceiling is.
- **Why:** escalated by the desk

**Q9 · Are card rewards income?** — `fixed-assets`

- **Asked:** Put this to the rewards-and-information-returns desk, which holds section 61, the rebate rulings and Pub. 525.
- **Why:** escalated by the desk

**Q12 · Do payments to individuals create a 1099-NEC obligation?** — `capitalization-and-de-minimis`

- **Asked:** Put this to the rewards-and-information-returns desk, which holds sections 6041, 6041A and 6050W and the 1099-MISC/NEC instructions.
- **Why:** escalated by the desk

### `citation_does_not_support` — 3

**The desk holds the paragraph and its own record forbids citing it here.** Not a missing source. The desk's `SUBJECTS.md` declares which source answers which subject, and in these three the answer's paragraph sits in a source not declared for that subject. **These are the three findings below.**

**Q12 · Do payments to individuals create a 1099-NEC obligation?** — `rewards-and-information-returns`

- **Why:** the question is about 1099-nec, which this desk answers from S11; '26 USC 6041(a)' comes from S2. A citation from a source the desk does not use for this subject is not this question's authority, however real it is

**Q16 · Where is the line between a tool and a fixed asset?** — `capitalization-and-de-minimis`

- **Why:** the question is about tool, asset, fixed asset, which this desk answers from S1; '26 CFR 1.162-3(c)(1)(iv)' comes from S2. A citation from a source the desk does not use for this subject is not this question's authority, however real it is

**Q33 · Is streaming television ever a business subscription?** — `personal-or-business`

- **Why:** the question is about subscription, streaming, which this desk answers from S1; '26 CFR 1.162-1(a) — what a business expense is' comes from S2. A citation from a source the desk does not use for this subject is not this question's authority, however real it is

---

## The three findings

### 1. A desk could not agree with the firm in its own words

Four answers came back `contradicts_ratified_position` **while agreeing with
the position they cited**. Q6 and Q7 on `meals-and-entertainment`, Q31 on
`cash-and-bank` and on `personal-or-business`.

`engine._same` compares a submitted conclusion to the firm's word by exact
string equality, and that is deliberate and right:

> *A looser comparison here would quietly turn wrong answers into right ones,
> which is the one direction this code must never fail in.*

**The defect was that the brief never said so.** An answerer told a position
is "binding" restates it. Re-serving the identical run with those four
positions copied verbatim and nothing else changed took it from **3 served to
7** — a third of everything the desks tried to answer was measuring a missing
instruction rather than the desks.

Fixed in `tools/ask_the_desks.py`: the brief now tells the answerer to copy a
position exactly into `position` and keep its own words in `working`. Both
runs are kept — `served-run1-paraphrased.json` and `served.json` — because the
difference between them is the finding.

**And the fix has a cost that only shows on reading the output.** Q31 on
`cash-and-bank` now serves, and what it serves in full is:

> an entry in the books

That is the firm's ratified position and it is correct, but as the whole of
what a desk hands a preparer it is not an answer — it is a fragment that
assumed the question was still on the page next to it. Exact reproduction
makes every ratified position load-bearing as *prose*, not just as a
conclusion. Nothing is broken; four words are doing a sentence's work.

**A question for the firm, not a change:** should a position that reads as a
fragment be rewritten as a sentence that stands alone, or should the served
answer carry the position *and* the desk's own restatement in `working`
alongside it? The second needs no rewriting of the record. Neither is applied.

### 2. Three subject-to-source declarations are narrower than their own desk

Each of these desks holds the paragraph that answers the question and refuses
to cite it, because `SUBJECTS.md` maps that subject to a different source.

| Question | Desk | Cited | Declared |
|---|---|---|---|
| Q16 where is the line between a tool and a fixed asset | `capitalization-and-de-minimis` | § 1.162-3(c)(1)(iv), the $200 line (S2) | `tool`/`asset` answered from S1 only |
| Q12 do payments to individuals create a 1099-NEC | `rewards-and-information-returns` | 26 USC 6041(a), the statute (S2) | `1099-nec` answered from S11 only |
| Q33 is streaming ever a business subscription | `personal-or-business` | § 1.162-1(a), what a business expense is (S2) | `subscription`/`streaming` answered from S1 only |

**Q16 contradicts its own desk's prose.** `capitalization-and-de-minimis/
SUBJECTS.md` says the desk answers *does this purchase get expensed at all*
from *"§ 1.263(a)-1(f) and § 1.162-3"* — but `tool` and `asset` are declared
on S1 alone, so the materials-and-supplies limit in S2 is unreachable for a
question asked in the close's own words.

**Proposed, not applied.** Each is one word added to one declaration line, and
the record is the firm's. They are on the docket.

### 3. Two published sources disagree with each other, and the desks hold both

Found by answering, not by reading:

- **The de minimis ceiling.** § 1.263(a)-1(f)(1)(ii)(D) still reads **$500**.
  Notice 2015-82 raised it to **$2,500**, and the only passage in the record
  carrying that is the IRS page — a *secondary* source. A desk answering this
  from primary authority alone gives a number that is ten years stale.
- **The information-return threshold.** 26 USC 6041(a) reads **$2,000** for
  tax years beginning after 2025; § 1.6041-1(a)(1)(i)(A) still reads **$600**.
  Both are primary. The statute is the later word.

Neither is a bug. Both are cases where *primary and binding* is not enough on
its own to pick the right paragraph, and a preparer relying on the regulation
would be wrong twice.

---

## What is waiting on the firm

1. **The two facts the desks asked the engagement to record** — `capitalization_rule` (Q4) and `taxpayer` (Q9). Neither is the client's to answer; both are the engagement's.
2. **The three subject-line widenings** in finding 2 — proposed above, not applied.
3. **The eight questions with nowhere to go** — the seven the firm decides once
   (kind D) and the one whose answer is that it does not matter (kind F).

## How to re-run this

```
cd desk
python tools/ask_the_desks.py                                   # write the briefs
python tools/ask_the_desks.py --serve runs/asked-<date>/answers.json
```

The run directory is dated by the day the desks were asked. The corpus keeps
its own date — the questions were asked by the close on 5 September.
