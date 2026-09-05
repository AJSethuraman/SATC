---
name: tie-out
description: Prove one figure is right by exhibiting the whole chain that produced it, ending at a source you do not control — the call that was made, what the software did with it, the independent authority, and the two numbers side by side. Written so a skeptic can rerun it by hand and land on the same number. Use when the firm cannot explain how a number is derived, wants a sample of one, wants to prove a figure to an auditor or a client, or asks how do we know this is right.
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

## The five links

Each one recorded, in order, in `docs/TIE-OUT-<figure>-<date>.md`.

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

**5 · The comparison.** Both numbers side by side and the difference. Zero, or
explained line by line.

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

## What not to do

- **Do not pick the easy number.** Pick the one whose derivation you cannot
  currently explain. A tie-out of a figure everybody already trusts proves
  nothing and costs the same.
- **Do not tie out to your own fixture, cache, or a copy you control.** That is
  the mirror, and it is the commonest way this goes wrong.
- **Do not stop at the match.** Record what you had to *know* to make the right
  call — which endpoint, which period convention, which sign. That knowledge is
  the reusable half, and it is invisible once the number agrees.

**Incident:** on 5 September 2026 an agent proposed a new conviction and numbered
it **C13**. On `main`, C13 was a proposal the firm had already *declined* — and
canon never reuses an id, so the entry would have overwritten a refusal and the
miner would have re-proposed the declined thing on every run. The agent was not
careless. It read a real record, checked it, and quoted it. It read the copy
installed on that machine, which was three versions stale, while five other
copies of the record existed locally in four different states. The authority —
`origin/main` — was one command away and was never asked. **A figure taken from a
copy you control is not tied out; it is echoed.**
