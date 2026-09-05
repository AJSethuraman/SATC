---
name: tie-out
description: Prove one figure is right by exhibiting the whole chain that produced it, ending at a source you do not control — the call that was made, what the software did with it, the independent authority, and the two numbers side by side. Delivers one self-contained document with the pictures embedded, opening on a diagram of how the dots connect, and closing on what running it found. Written so a skeptic can rerun it by hand and land on the same number, and reporting COULD NOT as a real verdict only after the obstacle has been attacked once. Use when the firm cannot explain how a number is derived, wants a sample of one, wants to prove a figure to an auditor or a client, needs to decide whether to trust a feed or a signal built on somebody else's numbers, or asks how do we know this is right.
---

# Tie out one number

Take **one figure** and prove it, by showing every link between the call that
produced it and a source you do not control. Not a hundred figures spot-checked.
One, traced completely, written so somebody who doubts you can follow it and land
on the same number.

The sample of one is the point, not a limitation. Coverage is a different job.

## The rule everything else serves

**A number confirmed only by your own system is confirmed by nothing.**

Before anything else, ask of your source: **could this disagree with me?** If the
answer is no, it is not a source. It is a mirror.

| Not a source | A source |
|---|---|
| another report from the same system | a bank or card statement |
| a figure recomputed by the same code | an IRS publication or form instruction |
| a fixture somebody wrote | a filed return, a vendor invoice |
| a total that balances by construction | a regulator's or agency's published series |
| the number as it looked yesterday | a third party's confirmation |

**Worked failure.** A period posted with no opening balances reported
`TB debit 33,655.83 = TB credit 33,655.83` and `Balance sheet: Balanced`, on
books where the operating checking account was in **credit** and the card
liability in **debit**. Every green on the screen was true. The poster only ever
accepts balanced journals, so debits equalling credits is an identity — it cannot
come back red. The tie-out that would have caught it in one line was never run:
compare `1110 Operating Checking` to the closing balance on the bank statement.
The bank can disagree with you. Your own totals cannot.

## What comes out is one document, not a note and a folder

**The deliverable is a single self-contained file a person can open, read and
forward** — one PDF, or one published page, with every image **embedded in it**
rather than referenced by a path into a folder beside it. The Markdown is the
source it renders from. It is not the thing you hand over.

A note plus a directory of loose images is correct and unusable. Every picture in
it is a link that resolves only on the machine that wrote it, so the reader gets
prose about numbers they cannot see. Nobody forwards that to an auditor.

**Incident:** on 5 September 2026 the firm was handed exactly that — a tie-out
that had been run properly, filed as a Markdown note with six files beside it.
*"i assumed that you understood the final product of tie out and walk would
basically be a PDF that shows how everything tied out? and explains it and makes
it easy to follow? Is that not?"* And, on what the document has to do: *"A sample
of one and a walk through or a… procedure document should literally, like,
visually and verbally easily show you how all the dots connect. How to use the
system? How it works. How it tied out."* Nothing had been left out of the note.
It was the shape that was wrong.

Render it, and keep it beside its evidence:

```
chrome.exe --headless=new --no-pdf-header-footer --print-to-pdf=docs/tie-out/<figure>-<date>/TIE-OUT-<figure>-<date>.pdf file:///<absolute path to the html>
```

Then **open the rendered file and look at every page.** Behaviour 11 applies to
your own output: an exhibit whose images failed to embed is indistinguishable
from one whose images embedded, until somebody opens it — and the first person to
open it should not be the auditor.

### What the document carries, in this order

**1 · A picture of the mechanism, before any prose.** Draw the same fact
travelling **two roads**: the production path — the authority's feed, into the
raw block, into the cell a person reads — and the check — the authority's own
document, the filed lines, divided by hand — meeting at **difference 0**. Label
every arrow with what happens along it (`one request`, `= X164/AM164*100`,
`RC-N 5.a ÷ RC-C 6.a`), and say underneath which road touches a document you do
not control, because that is the road that makes this evidence rather than a
second opinion from the same source. **A reader should see how the dots connect
before reading a word.**

**2 · The five links**, each with its evidence in the page — the call and its
real response, the formula verbatim, the source photographed and marked, the two
numbers adjacent.

**3 · The roster** with its denominator, if more than one figure was checked.

**4 · How to run it yourself** — numbered steps, each copy-pastable, **with the
real values already in it**, so the reader reproduces the whole thing without
you. Not `<your-cert>`; the cert. Behaviour 15 is the rule, and this is the
section where a document stops being a claim and becomes a tool.

**5 · What it found**, **6 · What I got wrong**, and **7 · What this does not
prove** — each a section of its own, not a footnote. The last two are what make
the first believable.

## The five links

Each one recorded, in order, in the exhibit source `docs/TIE-OUT-<figure>-<date>.md`,
and each one visible in the document that renders from it.

**1 · The figure.** Exactly which number, and where a reader sees it — the
screen, the report line, the field. Quote it as displayed, to the cent.

**2 · The call.** The exact request that produced it, **copy-pastable, with the
real parameters in it** — not a description of a call. A reader who cannot rerun
it has been given an assertion, not evidence.

**3 · The derivation.** What happened between the call and the figure, stated so
a person could redo it by hand: which rows, which filter, which dates, what was
summed, what was excluded and why. **"Then the system computes it" is not a
derivation** — it is the exact gap this document exists to close.

**4 · The independent source.** Named, dated, and obtainable by the reader:
which statement, which publication, which series, as at what date. Say how they
get it themselves. A source only you can see is not independent of you.

**Capture it. Do not summarise it.** Screenshot the page, the statement, the
filing — with the figure visible in the shot — and file it beside the exhibit:

```
docs/tie-out/<figure>-<date>/source-fdic-total-assets.png
```

Then **locate the figure on it**, precisely enough that a reader can put their
finger on the same one: which table, which row, which column, which label, as at
which date, in what units and at what scale. *"The FDIC reports 12.4%"* is not
locating a figure. *"Table 3, row `Total assets`, column `2026-Q2`, in thousands,
as filed 2026-08-15"* is.

This is the link that catches you. Writing *"the source agrees"* is something you
can do while believing it. Pasting the image and pointing at the cell is not —
either the number is there or it is not, and you find out at the moment you look
rather than at the moment somebody else does.

**Mark it, and enlarge it.** A photograph of a dense regulatory page with a
sentence pointing at a row is still a puzzle the reader has to solve. In the
document: ring the exact row **in red**, and put a **zoomed crop of that row
directly beneath it**, large enough to read the digits without leaning in. Beside
them, break the citation into its parts — schedule, page, line, column, code,
units — each shown as its own label rather than buried in a sentence. The reader
should be able to check you in one glance, which is the only kind of checking
that actually gets done.

**The identity of the document goes in the same shot as the number.** The
entity's name, the form or statement type, and the period, printed in the header
of every page you capture. Three of the four sameness checks below are then read
off the picture instead of taken on trust — and "same entity, same date" is
exactly the kind of thing that is true right up until it is not.

**Read every figure twice where a second rendering of the same source exists** —
the rendered page and the machine-readable filing, the PDF statement and the
CSV, the printed table and the published series. Two readings of one document is
not the mirror; it is one document read twice.

**Incident:** on 5 September 2026 a tie-out read the values off photographed
filing pages **and** off the same filing's XBRL — the machine-readable copy the
regulator publishes alongside the rendered pages. Every figure agreed except one:
a home-equity balance read off the image as `2,929,670`, where the XBRL said
`2,929,570`. The filing was not ambiguous, the software was not wrong, and the
error was a digit misread off a small picture by the person writing the exhibit.
It did not touch the figure being proved, and it is in the delivered document
anyway. **A tie-out that hides its own misreads is worth nothing**, and one that
never had a second reading would not have known.

**5 · The comparison.** Put the two numbers adjacent, digit for digit, **before**
writing any verdict:

```
ours    (GET /api/v1/institutions/12345/summary → total_assets)   4,182,663
source  (FDIC BankFind, Table 3, 2026-Q2, $000s, filed 08/15)     4,182,663
diff                                                                      0
```

The verdict is **read off that block**, never written ahead of it. A verdict
written first is a conclusion looking for evidence.

Before you may write `TIED`, four things must be the same, and each is a real way
a number that looks right is wrong:

- **the same entity** — the same institution, client, account, ticker
- **the same date or period** — an as-of that differs by a quarter matches nothing
- **the same basis** — gross or net, accrual or cash, consolidated or standalone,
  restated or as-originally-filed
- **the same units and scale** — thousands against units is the failure that
  looks closest to correct

If any of the four is not the same, the verdict is `DIFFERS` or `COULD NOT`, not
`TIED` with a note.

## A difference is a finding, not a failure

If they do not match, you have found something, and that is a better outcome
than a match. **Never plug it.** Never round to close it. Never adjust the call
until it agrees — that is fitting the evidence to the answer, and it is the one
way this document can do harm rather than nothing.

Write the difference down, say which side you believe and why, and if you cannot
tell, **say that**. Unknown is a third answer.

## Write it for the skeptic, not for yourself

An auditor does not accept your instructions as evidence. They read your
documentation, form their own view of what they would need to do, do it, and see
whether they arrive where you said. That is a much higher bar than "here is how I
did it", and it is the bar.

So: every step reproducible by hand, every term shown and then explained, and
nothing that only makes sense to somebody who already knows the system. If a step
cannot be followed without asking you a question, the document is not finished.

The exhibit is also a template. Done properly, the firm should be able to take it
and tie out the next figure without you.

## Every link is executed, never described

**A tie-out you did not run is not a tie-out.** It is a plausible document, which
is worse than no document, because it is indistinguishable from a real one at a
glance and it is the thing somebody will point at later.

So, without exception:

- **Make the call.** Paste the real response, or the part of it that carries the
  figure. Not a description of what it would return.
- **Go and get the source.** Open it. Read the number off it. If it is a page,
  say what the page said and when you fetched it.
- **Do the comparison in the document**, with both numbers visible, so a reader
  is checking your arithmetic rather than your word.

If you describe a step instead of doing it, **say that in the step**, in those
words. A document where four links were executed and one was assumed is useful.
A document where that is not marked is a liability.

## "Could not" is a verdict, not a gap

Every figure gets exactly one of three, and the third is not a failure:

| Verdict | Meaning |
|---|---|
| **TIED** | executed end to end, and the numbers agree |
| **DIFFERS** | executed end to end, and they do not — with the difference stated |
| **COULD NOT** | no independent source was reached, **and here is precisely why** |

`COULD NOT` must name its obstacle, because that is the whole value of it:

- no independent source appears to exist for this figure
- a source exists but is paywalled, gated, or behind a login the run has no access to
- the source publishes on a different basis — a different date, definition, unit or period — and reconciling them is a piece of work nobody has done
- the API does not expose the field the source publishes, so there is nothing to compare
- **I do not know where the authority for this number is** — which is a real answer and the most useful one to hear early

An agent that reports `COULD NOT` honestly on nine figures out of ten has done
more for the firm than one that reports ten green. The first is a map of where
the trust runs out. The second is a document that has to be re-verified by hand,
which is the work it was supposed to remove.

**Never convert a `COULD NOT` into a `TIED` by lowering the bar.** Reaching for a
second copy of your own data because the real source was hard to get is the
mirror again, wearing a hat.

### A `COULD NOT` is a hypothesis about the source, and it gets attacked once

An obstacle you can name is not an obstacle you have tested. So before you record
one: **name the obstacle, ask what it would take to get past it, and try that.**
Then write down the verdict you actually reached. One pass — this is not a
mandate to grind; it is a rule against the first plausible reason to stop.

**Incident:** on 5 September 2026 a roster reported 48 of 53 lines tied and five
`COULD NOT`, each with its obstacle named, which is what this skill asks for. The
two capital ratios: *"the regulator publishes these as percentages; there is no
single filed line to compare a percentage with."* The three quarterly charge-off
flows: *"the filing reports charge-offs year-to-date, so a quarter is a
difference of two filings, not a line in one."* Both statements were true. Both
were wrong as verdicts. Pushed on them, all five closed on one pass: the filing
publishes those two ratios itself, as percentages, on its own Schedule RC-R, so
they compare directly; and the three flows tie **to the dollar** by subtracting
one filing's year-to-date figure from the next one's — the subtraction the
obstacle had just finished describing. Nothing about the source had changed. The
obstacle had been described instead of tested, and "different basis" had been
allowed to mean "unreachable" when it meant "one arithmetic step away".

## More than one figure: report the roster

A feed, a dashboard or a signal set is not one number, and the firm's question is
not "is this figure right" but **"how much of this can I trust, and where does it
stop."** So one exhibit per figure, and above them a roster — which is the
deliverable the decision actually gets made from:

```
Tied out: 14 of 22 figures
  TIED        14
  DIFFERS      2   competitor headcount, revenue-per-seat  (see exhibits 7, 11)
  COULD NOT    6   4 no public source · 1 paywalled · 1 different basis
```

**Report the denominator** — 14 of 22, never "14 figures tied out". And put
`DIFFERS` and `COULD NOT` above `TIED`, because the fourteen that agree are not
what anybody needs to read.

## What it found is the return on running it, and it gets its own section

**Say prominently what changed because you ran this.** Not in a closing line —
its own heading, in the document, with the before and after. A tie-out that
proves a number and reports nothing else reads like ceremony; a tie-out that
names the defect it turned up is the argument for doing the next one.

**Incident:** on 5 September 2026 a tie-out of one dashboard figure came back
`TIED`, difference zero. The roster behind it found three past-due lines whose
provenance map cited codes from **the wrong version of the form** — the short
Call Report, filed by banks with no foreign offices, on a bank that files the
long one. The landed values were correct to the dollar; the citation pointed at
a line that does not exist on the form that bank files. No test could catch it,
because the numbers were right and the tests check numbers. Only going to the
filing did. **Right value, wrong citation, is invisible until somebody follows
the citation** — which is what this skill is.

## What not to do

- **Do not pick the easy number.** Pick the one whose derivation you cannot
  currently explain. A tie-out of a figure everybody already trusts proves
  nothing and costs the same.
- **Do not tie out to your own fixture, cache, or a copy you control.** That is
  the mirror, and it is the commonest way this goes wrong.
- **Do not stop at the match.** Record what you had to *know* to make the right
  call — which endpoint, which period convention, which sign. That knowledge is
  the reusable half, and it is invisible once the number agrees.
- **Do not write a link you did not execute** without marking it as assumed. The
  only thing worse than a missing tie-out is a convincing one nobody ran.
- **Do not write "the source agrees" without the image and the location.** That
  sentence is the one that can be typed while assuming, which is why it is the
  one this skill does not accept on its own.
- **Do not pad the roster with the easy figures** to lift the ratio. A roster of
  cheap wins reports a number that is true and a picture that is false.
- **Do not hand over the source instead of the document.** The Markdown and the
  folder of captures are what you rendered from. What the firm asked for is the
  one file they can forward without explaining how to open it.

**Incident:** the firm, 5 September 2026, on why the source has to be captured
rather than described: *"they would catch themselves and say, oh, shit. It
doesn't actually tie out. I've been lying this whole time because there was a
number there. I just assumed, yeah, of course, it's good. But now that I'm
looking at the screen, taking a screenshot and circling this and saying, look,
it's right here. I can see plainly it doesn't match."* The first draft of this
skill asked for the source to be **named and quoted**, which is a step that can
be completed truthfully by somebody who glanced at a page and found *a* number.
Nothing in it required looking.

**Incident:** on 5 September 2026 an agent proposed a new conviction and numbered
it **C13**. On `main`, C13 was a proposal the firm had already *declined* — and
canon never reuses an id, so the entry would have overwritten a refusal and the
miner would have re-proposed the declined thing on every run. The agent was not
careless. It read a real record, checked it, and quoted it. It read the copy
installed on that machine, which was three versions stale, while five other
copies of the record existed locally in four different states. The authority —
`origin/main` — was one command away and was never asked. **A figure taken from a
copy you control is not tied out; it is echoed.**
