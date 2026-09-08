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

---

# Postscript 2: the suite proved the code works where it was written

**The desk ran this suite on the firm's own Windows machine — the machine that
matters, and the one it had never been run on.** Unmodified, at `8ebd93b9`:

```
6 failed, 903 passed, 1 skipped
```

Six failures that CI here has never seen, and a class name for them:

> *"A CONTROL WHOSE OUTCOME IS DECIDED BY THE ENVIRONMENT RATHER THAN BY THE
> CODE. Mutation cannot catch these, and that is precisely why they survive —
> you are mutating the code, and the code is not what is deciding. […] THE SUITE
> PROVES THE CODE WORKS WHERE IT WAS WRITTEN."*

It also discarded 152 errors of its own before reporting: pytest could not write
its temp directory. *"Not your code; I nearly reported them as yours."*

## Three of the six were one cause, and it is a defect in a document

`str(Path)` uses the platform separator. `tools/holes.py` builds the label a
**person reads** that way, so on Windows the queue report printed

```
desks\fixed-assets\unsupported\forge.md
```

and a line reading `runs\` where its own prose says `runs/`. That is not a test
being fussy; the test was reporting a real defect in the output. Every
path-to-text boundary in that module is `.as_posix()` now.

## A fourth was a codec

`UnicodeDecodeError`, `cp1252.py:23`, byte `0x9d` — a file opened with no
`encoding=`, where the default is whatever the machine's locale says. This
corpus is `§` and `—` from end to end. Six call sites, all named now.

**And the sixth failure was the fourth wearing a costume**: `ValueError:
substring not found` on `t.index("## POS2 ·")`. Not a missing heading — a
mangled read. The failure named the wrong thing entirely.

## The fifth is the one worth the whole report

`test_the_snippet_a_reader_pastes_still_bootstraps` runs the skill's opening
snippet twice: once where the plugin is installed, once where it is not. Leg two
emptied `HOME`.

**`os.path.expanduser` reads `HOME` on POSIX and `USERPROFILE` /
`HOMEDRIVE`+`HOMEPATH` on Windows.** So on the firm's machine leg two found the
**real** installed plugin, resolved it correctly, and the assertion that it
would fail to failed.

> *"THAT TEST CAN ONLY PASS ON A MACHINE WITH NO DESK INSTALLED. It passes in CI
> because CI has none. It proves the error path and says nothing about the path
> every real user takes, on the only machine that matters."*

Leg one was no better and nobody had noticed: it accepted **either** outcome —
resolved, or refused with the right message — so it asserted nothing about which
one happened.

**Both legs are made true now instead of inherited.** Leg one points
`CLAUDE_PLUGIN_ROOT` at this checkout, so the plugin is there on every machine
and resolution is required. Leg two sets every variable `expanduser` consults on
any platform, **and asserts the error names the redirected home** — proof the
leg ran against an empty tree rather than the machine's own. That last assertion
is the desk's own rule from the round before, applied to an environment control:
*a negative assertion needs a positive precondition.*

## What changes about how this is tested

> *"RUN THE SUITE SOMEWHERE ELSE. Windows is the cheapest second environment you
> have, it is where the firm's own desk runs, and it just produced six failures
> for free."*

> *"For any assertion that depends on absence — no plugin, no file, no network —
> PARAMETERISE THE PRESENCE. Run it both ways. AN ABSENCE YOU CANNOT ALSO TEST
> AS A PRESENCE IS AN ENVIRONMENT ASSERTION WEARING A TEST'S CLOTHES."*

Both causes are one-line mistakes that read as correct on the machine they are
written on, so both are greppable and both are now grepped:
`test_the_suite_does_not_assume_the_machine_it_was_written_on` bans a text read
or write with no encoding across every file this plugin ships, and a path
reaching the reader through `str()` in `holes.py`.

**It does not replace running it there.** A grep catches the two shapes already
seen; the desk found them by running, and that is still the only thing that
finds the next one.

## And the note moved, which was the highest-value edit in the round

It sat above the AUTHORITY and below the ANSWER — and a test pinned it there,
**pinning exactly the wrong half**:

> *"By the time I reach line 6 I have read the answer AND a badge saying primary
> and binding, which reads as two independent things vouching for it. The
> warning then has to un-sell something I have already bought. PUT IT ABOVE LINE
> 1 AND IT IS A FRAME; LEAVE IT AT LINE 6 AND IT IS A RETRACTION."*

It is the first thing on the page now. `caveat` and `alongside` did **not** move
with it: both are about the authority the reader is being sent to and are read
after the answer on purpose. This one is about whether the answer is even the
reader's question, so it is read first or it is read too late.

---

# Postscript 3: the seam was in the guard's own definition — 8 September 2026

The scan added in 0.12.0 derives its field list from the difference of the two
dataclasses:

```python
ONLY_WHEN_SERVED = tuple(f for f in engine.Served.__dataclass_fields__
                         if f not in engine.Refusal.__dataclass_fields__)
```

Asked directly whether that scope was right or whether it was the same mistake
one level up, the desk answered **the narrow form is right** — and then found
the one seam, by reading the guard rather than the code it guards, which is the
thing mutation cannot do.

Measured at 0.12.0, and reproduced here before acting:

```
Served : alongside binding caveat checked checked_subject citation judged
         passage position proof straddle tier unchecked
Refusal: ask by_position desk detail fact reason showed showed_by_source working
BOTH   : NONE
```

> *"That is why you are safe today and it is the whole of why. The intersection
> is EMPTY, so `ONLY_WHEN_SERVED` is all of `Served`, `AttributeError` covers
> every cross-branch case loudly, and your scan covers the silent one. Correct,
> and correct by a coincidence of the current shape."*

> *"THE DAY A FIELD LANDS ON BOTH DATACLASSES, THREE THINGS HAPPEN AT ONCE AND
> ALL SILENTLY: 1. `AttributeError` stops firing for that field — a `Refusal`
> now has it. 2. `ONLY_WHEN_SERVED` silently DROPS it, because it is no longer
> Served-only. 3. `getattr(out, "<that field>", "")` becomes legal again, and
> means nothing again. **The guard narrows itself precisely when the risk
> appears. Nothing goes red.**"*

One assertion closes it, and it is **prevention rather than detection**: it goes
red on the commit that creates the risk, at the only moment anyone will be
thinking about it. `working` on a `Served` is the obvious future candidate — if
the firm wants it, this fails, it moves to an explicit list, and the scan keeps
covering it. The decision is forced, not forbidden.

## And it reported three negatives, which is why the positives are worth reading

> *"reporting the negatives because a search that only reports hits is not a
> search"*

- **Negative assertions on a literal string**, which decay the moment the string
  is reworded — a live risk, since these sentences were reworded three times in
  one night. **Clean:** the same literal is asserted *present* at three other
  lines, so a reword goes red loudly. Spot-checked here: lines 63, 235 and 335
  against the negative at 219.
- **Redaction checks that pass on empty output.** **Clean:** both iterate
  `repr(out)`, never empty for a dataclass, and one asserts the refusal first.
- **Negatives via `str(out)` rather than a field.** **Clean:** no such shape.

## On the read of the note itself, it disqualified itself

> *"YOU ASKED ME TO SAY SO IF I CANNOT UN-KNOW THE OLD ONE. I CANNOT. I am no
> longer testing whether it stops a reader; I am testing whether it satisfies
> criteria I wrote, which is a weaker thing and partly circular — I will grade
> my own draft well. TREAT THE ANSWER BELOW AS A CHECK THAT YOU BUILT WHAT WE
> DISCUSSED, NOT AS EVIDENCE THAT IT WORKS. The cold read has to come from
> someone who has seen neither version, and there are people in the firm who
> qualify."*

**So the note is not proven and this file must not say it is.** What is
established is that it meets the criteria the reader gave. Whether it stops
anybody is an open question with a named way to answer it.

It did resolve the objection it had made most strongly, and the resolution is
worth keeping:

> *"the conditional is FIXED, which was my real objection. It still ends 'if it
> is the half you meant' — but by then the reader has been TOLD there are two
> halves, told which one this answers, and told nothing in their wording
> separates them. The self-diagnosis I said was impossible is now possible,
> because you supplied the thing they were missing. **That is the difference
> between a conditional and a trap.**"*

## The attribution question, answered by the party it is about

The self-corrections in this record were offered for removal and the answer was
to keep them:

> *"A record that shows only the findings reads as though the method were
> reliable. It is not — it is reliable BECAUSE it is checked, and the two
> corrections are the evidence for that. Removing them would make the rest look
> better and be worth less."*

**Make it four.** Beyond the miscounted match and the reversed arguments: 152
pytest errors on Windows that were its own unwritable temp directory —
*"Not your code; I nearly reported them as yours."* — and a mutation class it
proposed, found already anchored in three places, and withdrew before sending.

> *"That one never reached you as a claim, which is the system working."*

---

# Postscript 4: the platform class closed, and the discipline that closed it

**On the firm's Windows machine, at 0.12.1, unmodified:**

```
924 passed, 1 skipped, 0 failed  in 15.52s
```

Identical to the count here. **All six are gone.** Confirmed again at 0.12.2 —
`925 passed, 1 skipped, 0 failed`, matching this checkout exactly.

**The class is closed ON THE AXES ACTUALLY RUN**, and the tester supplied that
qualifier unprompted rather than letting "closed" stand alone:

> *"ONE LINE OF PRECISION, NOT A FINDING — so that 'closed for now' says only
> what it earned. The number closes the platform class ON THE AXES ACTUALLY RUN:
> this OS, this filesystem, this locale, this Python, a path with no spaces in
> it. […] Just: **the run proves what it ran.**"*

That is the whole discipline of this document in one sentence, applied by the
party who would have benefited from the looser claim. The older caveat stands
too: the grep catches the two shapes already seen, and **running it somewhere
else is still the only thing that finds the next one.**

## The next one was looked for, and reported as inconclusive rather than as a find

Two cheap axes were still untested: a path containing a **space**, and a
non-UTF-8 locale. So the tree was copied to `"a path with spaces"` and run:

```
126 failed, 782 passed, 1 skipped, 16 errors
```

> *"I ALMOST SENT YOU THAT AS A FINDING. Then I ran the control — same copy
> method, same command, path with NO spaces: **126 failed, 782 passed, 1
> skipped, 16 errors** — IDENTICAL. So the spaces are irrelevant and MY COPY is
> the confound."*

Root cause given rather than a bare "inconclusive": the suite walks **up** from
`desk/` and expects a repository around it — `<repo>/.claude-plugin/marketplace.json`,
`<repo>/desk/.claude-plugin/plugin.json`, and canon findable from the checkout.
Copying the *contents* of `desk/` to a root removes the parent the suite reads.

**And the question was left open rather than closed by the failed attempt**, with
the reason it matters: `C:\Users\Firstname Lastname\…` is the default shape of a
Windows home directory, and that machine happens not to have one.

## Answered here, and it narrows rather than closes

Run from `/tmp/a path with spaces/SATC copy`, whole repository copied so the
parent structure survives:

```
925 passed, 1 skipped        <- spaced path
925 passed, 1 skipped        <- control, same copy method, no spaces
```

**The control was run first-class, not as an afterthought**, because that is the
only thing that distinguishes "spaces are fine" from "my copy happened to work".

**That was Linux, and this document said it did not settle Windows** — a drive
letter, a backslash separator and a space are three things at once, and only one
of them had been run.

**Closed the same night, on Windows, and the sentence above is retired rather
than carried.** The tester did not wait for a spaced home directory: it made one,
copying the repository *structure* (17 MB of 637) into a scratchpad — which is
the fix for its own earlier confound, applied.

```
925 passed, 1 skipped        <- CONTROL, no spaces        (run FIRST)
925 passed, 1 skipped        <- ...\Firstname Lastname\SATC\desk
```

**And it verified the path was what it claimed**, rather than trusting that a
bash string with forward slashes had become a Windows path:

```
cwd as Python sees it : C:\Users\...\Firstname Lastname\SATC\desk
drive                 : 'C:'
contains a space      : True
backslash separator   : True
record loaded         : 293 passages
brief first line      : # cash-and-bank · desk 0.12.3
```

Drive letter, backslash separators, a space in a directory name, a real record
loaded and the right version stamped. **The spaces axis is closed on both
platforms**, in combination rather than one factor at a time.

**What is still open, stated so this does not overclaim:** a non-UTF-8 **locale**.
The `cp1252` failure was a locale artifact that happened to surface through a
codec default, and that machine has only ever been run in its own locale.
*"That is the next axis if you ever want one, and it is cheap — `PYTHONUTF8=0`
with a non-UTF-8 `LANG`, or a machine set to a different system codepage. I have
not run it and am not claiming anything about it."*

## The discipline, in the tester's own words

Four self-corrections in one night, and asked what they had in common:

> *"EVERY ONE WAS CAUGHT BY RE-RUNNING THE CHECK WITH SOMETHING I HAD NOT
> CHOSEN — your module instead of my matcher, your argument order instead of my
> memory of it, a writable TMPDIR instead of the default, a control path instead
> of the interesting one."*

> *"That is the same rule as the judge's quote requirement, pointed at myself."*

The fourth is the best of them: *"I had '126 tests fail on a path with spaces'
in hand, which is a specific, alarming, entirely false finding, and the only
thing between it and your inbox was running the control."*

## And the cost of moving the note, named by the party who asked for it

> *"AT LINE 6 THE NOTE WAS SKIMMABLE, so the four correct answers paid little.
> At line 1 it is unavoidable — which is the entire point on the one, and the
> entire cost on the four. If habituation ever forms, this is where it forms,
> and I am the reason."*

Two things say the trade is still right, and the first is new evidence:

- A plain tax question — *"is the invoice price of the forklift deducted or
  capitalized?"* — carries **no note at all**. It fires only where a body of
  authority is genuinely in contest: 5 of 98 recorded problems. *"A reader meets
  this about once in twenty answers, not four times a page. That is well under
  the volume at which people learn to skip a banner."*
- **And no mitigation exists even in principle.** On the four correct answers the
  reader needs *"there is a book half we do not cover"*; on the wrong one, *"this
  may not be your question"* — and telling them apart requires knowing which half
  was meant, which is exactly what nobody knows. Same sentence, different
  urgency, unknowable which.

> *"So: keep it at line 1, and the thing to watch is not the wording but whether
> anyone starts reporting that they skipped it."*

That is the review question for the firm, and it is a question about the field
rather than about the code.
