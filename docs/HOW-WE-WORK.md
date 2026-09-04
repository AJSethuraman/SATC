# How this codebase keeps itself honest

Written for an agent joining a project that wants the same discipline. Nothing
here is theory — every rule exists because something specific went wrong, and
the rule is written down next to the thing it protects.

## The one sentence

**A claim in one place, the behaviour in another, and nothing comparing them.**

That is the shape of nearly every real bug found here. Not typos, not crashes —
a document that says the software does X while the software does Y, with no
mechanism that would ever notice. Everything below is a way of closing that gap.

## 1. Tenets are not principles, they are case law

There is a file of thirty-five tenets. **Every one is cited to a real bug in
this repository.** Not "prefer composition" — but:

> *A proof artifact once declared 190 documents fine when every one of them
> was unreadable.* → **Never claim something works without opening the artifact.**

Rules with a body count get followed. Rules that sound wise get skimmed.

When a new class of mistake appears, it becomes a numbered tenet with the
incident attached. When an agent writes a commit message, it names the tenet it
broke or upheld. The list is a shared memory, not a style guide.

**Do this:** keep one file. Each entry = the rule, then the incident, in the
firm's/user's own words where possible. Add to it when something bites.

## 2. Every check reports its denominator

A green check that examined nothing looks exactly like a green check that
examined everything. So nothing here reports a result without reporting what it
looked at:

    6 of 7 checked.
    1 of 7 figures read, 6 refused — from 6 rows under 0 labelled tables
      across 1 page (6 figures seen)
    22 screens, 97 controls, photographed

And where a check examined nothing, it says so **in words** rather than showing
a zero: *"nothing to look at — no clause was cited"* is a different fact from
*"0 problems found"*, and only one of them means what a reader takes it to mean.

## 3. Check the checker, by mutation

A test that passes proves nothing until you have seen it fail for the right
reason. So: after writing a guard, **break the guard on purpose and confirm a
test goes red.** Every meaningful change here ends with a mutation table:

| mutation | result |
|---|---|
| short payment settles anyway | DIED |
| reads the order total, not the tenders | DIED |
| never asks the other account | DIED |
| a broken collaborator takes the page down | **SURVIVED** |

**A survivor is the finding.** In this session survivors caught, among others:

- A test asserting what a message *said* while a mutant made a wasted network
  call and stayed quiet — the test never checked whether the call happened.
- A guard tested with a fixture that could not exercise it: the "broken file"
  case was already swallowed one layer down, so deleting the guard changed
  nothing and the test stayed green.
- Four mutants that lived because the test transport raised a hand-made error
  instead of one built the way production builds it. **The fixture proved the
  code agreed with itself.**

If you cannot kill a mutant, either the guard is decoration — say so in the
code — or the test is too weak. Both are worth knowing. Report survivors; never
quietly drop them.

## 4. Prevent, don't detect

Given a choice between a report that says something went wrong and a
construction that makes it impossible, take the construction.

- A short payment does not "get flagged" — it leaves the settled-date unwritten,
  so the downstream gate that reads settled bills **stays shut by construction**.
  Nobody has to read anything.
- An unfilled `<<Placeholder>>` is refused **at the boundary every caller
  passes**, not in the two functions that happen to build the string. One of
  those two was written later, walked around the guard, and put
  `SATC <<InvoiceNumber>>` on a live checkout page above a card field.

**Corollary:** when a rule is stated in a second place, go and read the first.
Nearly every "we already handle that" bug is a sibling that was never re-read.

## 5. Allow one state; never exclude the ones you expect

Code decided a payment had arrived by checking `state == "COMPLETED"`. A real
charged card came back `OPEN`. A bill that *had* been paid would have read
unpaid forever.

The fix was not a better guess at the vocabulary — the comment had already
guessed wrong twice from documentation. The fix was to stop trusting a label and
ask whether money changed hands.

But note *why* nothing worse happened: the guard **allowed** one state rather
than **excluding** the ones it expected. Written the other way round, an
unanticipated `DRAFT` would have read as paid and settled a bill nobody paid.

**Allowlists fail closed. Denylists fail open.**

## 6. Unknown is a third answer

"Cannot tell" must never collapse into "no" — or into "yes". A signature census
that cannot read the templates returns `None`, and the screen draws it
differently from both. A diagnosis that could not reach the second server says
nothing rather than reporting a refusal.

**Two silences are not an answer.**

## 7. Earn the claim, or don't make it

An error message named one cause as "the commonest". Run it against server A:
*"it's probably a B credential."* Run the same credential against B: *"it's
probably an A credential."* Both cannot be true, and between them they had
already ruled out what each was asserting.

Two fixes, because they were two problems:
1. The generic path **stopped choosing** — it lists the causes and picks none,
   because from one refusal it genuinely cannot know.
2. The diagnostic path **went and found out** — one extra read-only request to
   the other server, and now it reports what that proved.

The observation was one request away and nothing went and made it. **If you can
check, check. If you can't, say you can't.**

## 8. Documentation is generated from the software, or it rots

The operating-procedures document is **generated** and must not be hand-edited.
It parses every command it prints through the real argument parser — so a
procedure naming a flag that does not exist cannot be published.

The screenshot walkthrough goes further: a script drives a real browser, walks
every screen, photographs it, and writes down **every control it can see**. A
registry answers for each control. The build **refuses** when:

- a screen was never reached (nothing said about it is checked),
- a control has no answer (the reader meets a button the document never mentions),
- the registry explains a control that is no longer there (it tells them to
  press something that is gone).

That third check fired three times today on pages the firm chose to delete, and
once on a button that had become hover-revealed. Each refusal was correct.

**A document that describes software is a claim about the software. Generate it,
or test it against reality.**

## 9. The register a reader is in is not the register you wrote the spec in

Requirements are written to argue a case. Copy is written to be read. Sentences
were being transcribed straight from specification into things clients read —
*"the engagement letter governs the work"* — which the firm rejected flatly:
*"i would never expect a client to understand what an engagement letter is."*

So: **never transcribe a spec.** Write what the requirement protects, then
delete the requirement's wording. No term a first-time reader would look up. No
contract-desk verbs. Cut any sentence whose only job is to protect us. **Length
is the tell** — past ~25 words it was written to be complete, not to be read.

A linter enforces the mechanical half over published copy. The same bar applies
to screen labels, which are copy: a separate check fails the build if any
browser-facing string names a filename, a code identifier, or a terminal
command. It was written after the user sent a screenshot asking *"why would that
be in our software? what software says stuff like that to its user?"*

## 10. Where a fact is missing, refuse — visibly

Nothing is invented to fill a gap. A missing fact becomes a literal
`[CONFIRM: what the firm does if an extension is refused]`, and the document
**refuses to ship** rather than going out with a placeholder. Those are counted
and reported as *waiting on a person*, never as failures.

This matters more than it sounds: three separate items in one redesign were cut
or deferred because the design assumed data the software did not hold — a
nine-step progress bar when seven were derivable, a client count from a board
that did not count the relevant dates, a "built at 08:52" line with no build
record behind it. **Build the fact, or leave the line out. Never draw the line
and hope.**

## 11. Front to back, or it is not delivered

A feature reachable only from tests is not delivered. Every change is walked
from where a person actually starts — the front door, not the function.

And: **open the artifact.** The single most productive act in this session was
the user opening a payment page in a browser and photographing it. It said
`SATC <<InvoiceNumber>>` above a card field. Sixty-plus tests passed at the
time, and not one of them opened the page.

## 12. Reviews: be hard, and report what you did not check

Every report separates:

- what was **proven**, and by what,
- what was **assumed**,
- what was **not checked at all**, said plainly.

A corpus scored 126/126 and the report leads with: *"126/126 is not an accuracy
figure. It is a corpus written to break a reader, scored against a reader
written to survive it, on layouts that are sixteen-eighteenths invented.
Accuracy on real documents is unknown, denominator zero."*

That sentence is worth more than the score.

**Never take another agent's report at face value** — including your own. Two
reports in this session were confidently wrong in ways a single check would have
caught, and the check took one command.

## 13. Decisions go to the human, as answerable questions

Anything that changes behaviour, states a new fact, or deletes something a person
uses is not an agent's call. Those get written up as: **what is being asked, what
happens either way, and a recommendation** — in language the person can answer in
one line, without scrolling back.

And when they push back, take it seriously. Asked whether to delete a page of
green checks, the answer came back as a question: *"is it meant to be a call to
read it all or a call to ensure anything it flags is resolved?"* That question
was better than the recommendation, and it changed the design.

## The line that governs everything

> **Change anything a test can prove; change nothing a client reads or pays.**

---

### If you take four things

1. **Cite your rules to real incidents.** A rule with a body count gets followed.
2. **Break your own guards and watch a test go red.** A survivor is a finding,
   and the commonest cause of a survivor is a fixture that agrees with the code.
3. **Report the denominator, always.** A check that examined nothing must not
   look like a check that passed.
4. **Open the artifact.** Tests prove the code agrees with itself. Only looking
   proves it agrees with reality.
