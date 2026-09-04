# Where things stand — 3 September 2026

One page. What is proven, what is waiting on the firm, what is queued.
Written because this session produced a lot and none of it was in one place.

---

## Taking payment

**Proven, against the live Square sandbox: six of the seven steps.** The token
is accepted, the location is the firm's own (it named the business back), a
payment link can be created, and the order can be read back afterwards. Run it
yourself with `python cli.py payments --check`.

**The seventh needs a card and a person, and always will.** No software can pay
itself.

**Not proven, and only one thing can prove it:** that money reaches the firm's
bank. That needs the production location id, a real $1 charge on the firm's own
card, and a look at the bank a day or two later.

### Four real defects this found

Each was invisible to a green test suite.

| | |
|---|---|
| **The money was never compared to the bill.** `settled_amount` was written onto every invoice and `grep` found no reader. A client could pay $645 against a $745 bill and the return would clear the e-file gate every engagement letter promises stays shut | fixed; a short payment now leaves the bill unsettled *by construction* |
| **A live checkout page read `SATC <<InvoiceNumber>>`** above a card field. The guard against that existed; newer code walked around it | fixed at the boundary every caller passes |
| **A charged card leaves the order reading `OPEN`**, and the code only counted `COMPLETED`. A bill the firm had been paid for would have read unpaid for ever | fixed: it asks whether a card was charged, not what the status is called |
| **The 401 message contradicted itself** — told you it was probably the other account's token, whichever account you ran against | fixed: it now asks the other account and reports what that proved |

**Blocked on:** the production location id. Set the production token in the
environment and run `python cli.py payments --check --production` — it asks
Square for the id and prints it. No link is made at that step.

---

## The app's look

Claude Design delivered four spec pages and a stylesheet
(`satc-handoff/06-APP/`). Seven decisions went to the firm; all seven answered.

**Live now:** `[CONFIRM: ]` has its own colour and means one thing — *waiting on
you*, not an error. Five state marks where there used to be three shades of
grey. Every count says what it counted. A seven-step bar showing which steps are
done, with no running count. The next deadline in the chrome. Three confirmation
pages deleted. The row is the control on the review screen.

**Cut or deferred because the software did not hold the fact:** the nine-step
bar (seven are derivable), the "4 clients due" count (the board does not count
extensions), the "built at 08:52" line (nothing records when a document was
built). *Build the fact or leave the line out.*

**Queued, in order:** the terminal's check vocabulary → the document build
record → the interview's running summary.

---

## Reading documents

A paystub reader that reads the **column heading above a number** instead of
counting dollar figures on a line. The one it replaces turned ADP's *hours*
column into $44.00 of gross pay.

Scored over 126 figures: right on 126, wrong on none; the old one wrong on 24.
**That is not an accuracy figure** — it is a corpus written to break a reader,
scored against a reader written to survive it, on layouts that are
sixteen-eighteenths invented. Accuracy on documents this firm's clients actually
send is unknown, denominator zero.

**Not delivered:** it is reachable from `satc paystub-corpus` and from tests.
The withholding screens still use the old reader.

---

## Ad-hoc documents

Looking at a document and sending one are now different acts. A preview shows a
document that *would* fail the gate — which is the most useful preview there is
— and carries a stamp on every page saying it is not the copy that goes to a
client. Sending keeps the blocking gate, the written reason and the log.

**A real bug found by ticking a box:** ticking "put the invoice in too" on the
packaging screen refused the *entire* pack — no letter, no estimate, no
onboarding letter — every time.

**The biggest hole still open:** `cli.py render` and `cli.py event` run no
pre-send gate at all. Four of the twelve client documents can ship ungated
today.

---

## The Forge

The firm's own hardware is up as of 3 September 2026, and the work is moving
onto it: **real client data lives there and the practice runs there.** The code
keeps travelling by git — GitHub is the backup and the branch/PR workflow does
not change. Claude connects over Remote Control, so the filesystem and the
network are the firm's own rather than a rented container's.

`docs/forge-first-run.md` is the survey the first session on that machine runs:
measure what the machine actually is, then the whole suite, then say plainly
what was not checked.

**One live risk, recorded rather than left as a question.** Asked what backs up
the client data, the answer was *nothing yet* — a Storage Spaces mirror and no
more. A mirror survives a failed disk; it does not survive a fire, a theft, a
ransomware run, or the wrong folder being deleted. **Git backs up the code and
nothing backs up the clients.** The firm has chosen to prove the suite runs
first, which is the right order — this is written down so the sequence is a
decision rather than an omission.

## Waiting on the firm

1. The **production Square location id** (above).
2. The **backup folder path**.
3. The **four service-line engagement letters**.
4. Three questions from the paystub work, in that agent's report: whether a
   column headed just "Amount" is always the current period; whether a stub with
   one money column should be read or refused; and whether a shape-only
   write-back from real stubs is acceptable.

## Where to look

| | |
|---|---|
| How this codebase stays honest | `docs/HOW-WE-WORK.md` |
| The tenets, each cited to a real bug | `docs/SOFTWARE-TENETS.md` |
| What is where in the repo | `docs/REPO-INVENTORY.md` |
| The redesign questions and answers | `docs/app-redesign-questions.md` |
| The app design spec | `satc-handoff/06-APP/` |
| The operating procedures (generated — never hand-edit) | `docs/OPERATING-PROCEDURES.md` |
