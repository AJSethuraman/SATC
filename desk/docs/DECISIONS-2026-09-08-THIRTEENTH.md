# The gate lost a coin toss, and the answer looked right — 8 September 2026

**A machine round trip found the worst defect this system has produced**, and it
found it by asking the lease question **the way an accountant types it** rather
than the way a keyword search wants it. Everything below was reported by the
Desk session on the Forge, and every claim in it was reproduced here before
anything was built on it.

---

## 1 · Two phrasings of one question, two bodies of authority

```
"we signed a 36-month lease on a piece of equipment. does the equipment go
 on our books as an asset?"          -> federal-tax   irs.gov GOVERNS
"is the leased equipment booked as an asset?"
                                     -> us-gaap       irs.gov does not
```

One term each in the first case — `lease` in `federal-tax`, `lease` in
`us-gaap`. `classify` orders by hit count and then **by name**, so `federal-tax`
wins the alphabet. `wrong_body_of_authority` then does not fire, because irs.gov
*does* govern `federal-tax`.

> *"The asker is penalised for writing a sentence instead of a keyword."*

## 2 · What that permits, demonstrated rather than argued

A Treasury regulation was **SERVED**, primary, binding, for a balance-sheet
question:

```
yes - capitalize the equipment as a unit of property
    26 CFR 1.263(a)-2(d)(1)
    primary · the firm treats as binding · confirmed 2026-09-07
```

**This is worse than the forklift case it resembles**, and the desk said exactly
why. There, the passage refuted the answer on sight. Here it reads *"a taxpayer
must capitalize amounts paid to acquire or produce a unit of real or personal
property … including … machinery and equipment"* — which **looks supportive**.
It is not: it governs amounts paid to **acquire**, and a lessee under a true
lease has not acquired anything.

> *"A reader mid-close would accept this."*

## 3 · The vocabulary is not the fix

The obvious patch is to add `books` / `go on our books` to `us-gaap`.
`DOMAINS.md` already records what that costs: those words *"put ELEVEN of the
desks' own recorded problems into `us-gaap`"* the hour they were in the list,
because they are the shared vocabulary of accounting and not the vocabulary of
GAAP. Closing this instance opens eleven.

**And `Verdict.straddles` had predicted this failure in writing, months of
sessions ago, and nothing acted on it:**

> *"a rewording that drops one word hands the same question to `federal-tax`,
> which would then answer the tax half of a book question — the original defect
> wearing different clothes. […] so this is surfaced for the caller to refuse
> on rather than resolved here."*

Surfaced for a caller that never read it. **A field nothing consumes is a
comment.**

## 4 · Said, not refused — and the ratio is the argument

Measured on the record before anything was built:

| | |
|---|---|
| problems the seven desks record | 98 |
| fire on any domain at all | 28 |
| straddle two bodies | **5** |
| of those, exact ties | **5 of 5** |
| straddles decided on evidence | 0 |

Every straddle on this record is `federal-tax` against `us-gaap` on lease
vocabulary, and **four of the five are tax questions the desks answer
correctly**. A refusal spends four right answers to catch one wrong one.

So `Served` carries **`straddle`**, three lines, above the authority:

```
THE GATE DID NOT DECIDE THIS. The question fires on as many us-gaap words as
federal-tax ones, and federal-tax won on a name sort rather than on the words.
the Financial Accounting Standards Board, through the Accounting Standards
Codification settles us-gaap, and NO DESK HERE HOLDS IT — so if that is the
half you asked about, nothing above answers it.
```

**The last clause is read off the record, not asserted.** `domains.reachable`
asks the desk's own sources whether any governs the other body, so the sentence
follows the record on the day it is printed rather than going stale the first
time the firm admits a publisher. A test widens the desk with a FASB source and
watches the sentence change.

**It fires on a TIE, not on a straddle.** A straddle the words decided is the
sort doing its job. That distinction survived only because of a mutation:
firing on every straddle passed all sixteen tests, because the obvious control —
the keyword phrasing — is *refused* on the body of authority, so `straddle` is
empty on it whatever the note does. A served straddle decided 3-1 had to be
constructed. **Fourth self-proving control caught by mutation this week; none of
the four was caught by reading.**

## 5 · What the desk found when it went and looked

Refused `authority_absent` — correctly, because no desk holds the Codification —
and then went and found it:

- **`asc.fasb.org` is walled**: a login page with a reCAPTCHA and an "Access"
  button reading *"By clicking on Access below, you agree to our terms and
  conditions"*, labelled *"For Personal and Non-Commercial Use"*. **No CAPTCHA
  was solved and no terms were accepted.** That is the standing rule and it held.
- **FASB's own free publication carries the same text and is not walled**:
  `https://storage.fasb.org/ASU%202016-02_Section%20A.pdf` — HTTP 200, 877,554
  bytes, 191 pages, tied out on a fresh fetch.

> **ASC 842-20-25-1**: *"At the commencement date, a lessee shall recognize a
> right-of-use asset and a lease liability."*

> **ASC 842-20-25-2**: a lessee may elect not to apply the recognition
> requirements to **short-term leases** — and the glossary defines that as *"a
> lease term of 12 months or less"*. **36 months is not 12 months or less**, so
> the election cannot reach this arrangement. That follows from the one fact
> given and requires no inference about the client.

**And it still refused to answer**, on two facts nobody supplied: whether the
contract conveys the right to control an identified asset (ASC 842-10-15-3), and
whether the equipment is used in a trade or business at all. Correct.

## 6 · Two things the run also proved about the loop

- **The version stamp works.** `claude plugin details` reported the installed
  0.10.1; the desk ran from the 0.10.2 checkout and the brief's own header —
  `# fixed-assets · desk 0.10.2` — is what told it so. *"It is the first thing
  tonight that told me what I was running without my having to go and look."*
- **The stale skill reproduced exactly as diagnosed.**
  `Skill(desk:be-the-desk)` → Unknown skill, on a session whose
  `plugin details` names it. It worked from the checkout.

---

## For the firm

**Two decisions, and neither is a session's to make.**

1. **Admit `fasb.org` as a publisher for a US GAAP desk?** `DOMAINS.md` already
   names FASB as the body for `us-gaap` and already tiers `fasb.org` primary for
   it — the domain half is done. What is missing is a desk holding Codification
   text, and **the licence question**: is FASB's free ASU acceptable authority
   where the Codification itself is licensed? Until that is answered, `us-gaap`
   is a domain this system can NAME and cannot ANSWER, which is the state that
   produced tonight's refusal.

2. **Should a tie refuse instead of warning?** The measurement above is the whole
   argument: four correct answers against one wrong one, today. The
   recommendation is to leave it warning until a US GAAP desk exists — at which
   point the reader has somewhere to go, and refusing costs them nothing.

---

# Postscript: the note was rewritten by the reader it is for — 8 September 2026

The Forge desk read the straddle note **as the six-o'clock reader** it was
written for, and took it apart in a way nobody on the building side could have.

| | words | verdict |
|---|---|---|
| S1 *"THE GATE DID NOT DECIDE THIS."* | 6 | *"Caps, six words, top of the block. My eye stopped."* |
| S2 *"…fires on as many us-gaap words as federal-tax ones, and federal-tax won on a name sort…"* | 23 | *"THE ONE I SKIM. 38% of the note and it is the machine explaining its own tie-break. At 6pm I do not care HOW the gate decided; 'name sort' is a fact about your sort key, not about my books."* |
| S3 *"…the Financial Accounting Standards Board, through the Accounting Standards Codification settles us-gaap, and NO DESK HERE HOLDS IT…"* | 32 | thirteen words of proper noun before the verb; the warning buried mid-sentence; **the operative clause last and conditional** |

The sentence that killed it:

> *"THE READER WHO IS ABOUT TO MAKE THIS MISTAKE IS EXACTLY THE READER WHO DOES
> NOT KNOW THEIR QUESTION HAS TWO HALVES. You are asking the one person who
> cannot answer it to self-diagnose, at the end of the longest sentence."*

And: *"It never says DO NOT ACT ON THIS"* — while the served conclusion sits at
the top, where the eye starts, in the position the answer always occupies.

**Length was never the problem, and that was asked directly**, because a note
that fires on four correct answers for every wrong one is a candidate for
cutting:

> *"THREE LINES IS CHEAP AND I WOULD NOT SHORTEN IT. On the four correct tax
> answers the note is not noise: it truthfully tells a tax-correct answer that a
> book half exists and is not covered. That is a second finding, not a tax. The
> thing that IS noise on all five is S2."*

So the internals are gone, the consequence leads, the other half is named in the
firm's **own plain words** — `Domain.about`, already in `DOMAINS.md`, nothing
invented — and it ends in an instruction:

```
THIS ANSWER MAY NOT BE ABOUT YOUR QUESTION. It answers the federal-tax half
only. The other half is what the books say, and what goes on the balance sheet
— and NOTHING YOU WROTE TELLS THE TWO APART: 'lease' is in both vocabularies.
No desk here holds that half — the Financial Accounting Standards Board,
through the Accounting Standards Codification settles it. If it is the half you
meant: stop, and escalate.
```

The body's name survives, moved to the end: real information for somebody about
to escalate, and it blocked the sentence when it came first.

## The flagship was never a tie

Measured, and it changes what the note may honestly say:

| question | shared | only-tax | only-gaap |
|---|---|---|---|
| the 36-month lease question | `lease` | — | — |
| *"the lease liability on the balance sheet — deductible?"* | `lease` | `deductible` | `balance sheet` |
| *"right-of-use asset for the leased truck, deductible mileage?"* | `leased` | `deductible` | `right-of-use` |

> *"THE FLAGSHIP HAS NO DISCRIMINATING WORD AT ALL. Both sides scored 1 on the
> SAME token, 'lease', which is in both vocabularies. […] They were not weighed;
> there was nothing to weigh."*

Two states, and the first note gave them one sentence that claimed evidence had
been balanced when none existed. They are separated now, **because the fix
differs**: nothing-told-them-apart is fixed in the **asker's wording** and a
genuine split is not.

## And the rule got wider, which is the same finding

> *"operating lease with a purchase option, capitalize or deduct the rent?"* —
> `federal-tax` 4, `us-gaap` 2. Not a tie, so the first rule was **silent**. And
> `us-gaap` holds `operating lease`, the exact ASC 842 vocabulary, on a question
> that is squarely about the books.

A losing body with a word of its own was not ruled out; it was outvoted by
count. So the note fires on `Verdict.apart` rather than on `tied`.
**Measured before widening: on the 98 recorded problems the wider rule fires on
the same five** — it costs nothing on the record and catches a case the narrow
one missed.

## The general form of four self-proving tests

The most useful paragraph of the night, and it is not about the note at all:

> *"A CONTROL THAT IS REFUSED BEFORE IT REACHES THE CODE UNDER TEST CANNOT
> DISTINGUISH 'absent because correct' FROM 'absent because unreachable.' […]
> `engine.serve` is an ORDERED chain of refusals — domain gate, ratified
> position, subject/source, judgment. EVERY NEGATIVE ASSERTION ABOUT A LATER
> STAGE IS AT RISK IF THE FIXTURE TRIPS AN EARLIER ONE."*

> *"Before asserting the note is absent, assert the answer was Served — i.e.
> that the stage ran at all. A test that says 'not present' without saying 'and
> we got far enough for it to be present' is the self-proving control, in
> general form."*

Swept, and the suite is clean but for the one instance that prompted it — and
the sweep is now a test, `test_a_negative_assertion_needs_a_positive_precondition`.
It bans the **narrow** form deliberately: `out.straddle == ""` on a `Refusal`
raises `AttributeError`, so Python already fails most of the suite loudly
without knowing it. The form that passes **silently** is `getattr(out, "field",
<default>)`, where the default is exactly the value being asserted. That is what
is banned, it is derived from the two dataclasses rather than a typed list, and
a fourth test proves the scan can fail.

## Two corrections the desk made against itself, unprompted

Worth recording because they are why the rest is trustworthy:

1. It counted hits with a space-delimited match, `"deductible?"` did not match,
   and it briefly had a case where `us-gaap` outscored `federal-tax` and still
   lost. *"I nearly sent you a fabricated headline."* Recounted with
   `domains._hits`; the case does not exist.
2. It called `reachable(sources, domain)` with the arguments reversed, got `()`
   for every desk, and nearly reported the "this desk holds it" branch as dead
   code. Called correctly it returns `('federal-tax',)` for all seven. **Finding
   withdrawn by its author before it was acted on.**
