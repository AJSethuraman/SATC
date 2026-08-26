# SAT-C — Document Tenets

**Rules mined from every editing note the firm has given on client-facing
documents, 25–26 August 2026.** Read before writing or revising anything a
client receives. Each tenet carries the note it comes from, verbatim; a rule
with no quote under it does not belong here. The test each one had to pass: *if
this rule had been in force, would that note have needed writing?*

Cite as **T1**, **T7**. They govern `../04-TEMPLATES/`, the wording assembled at
render time from `client-documents/registry/fee-schedule.yaml`, and any new
document in the set. `AUTHORING-CONTRACT.md` still governs structure,
stylesheet, fields and compliance vocabulary — see **What this file replaces**
for where the two disagreed and which wins.

---

## 0 · The gap this file exists to close

The firm writes short, flat, lowercase, without ceremony. The drafts write long,
explanatory, and slightly lecturing. The gap is not politeness — it is that the
drafts keep adding a **second sentence that explains the first one**.

**How the firm writes** — all his, as instructions or as replacement copy:

> "just delete this they dont send it to us" · "can't bite if not a secret" ·
> "pick one" · "Including its statements" · "we do not need SS cards, we do
> require the numbers" · "For your safety, Pay each authority directly" · "If
> this letter states your understanding, sign below." · "If your return requires
> additional work, a new estimate will be provided in writing. Additional work
> will not be begin without your written consent to the new estimate."

No throat-clearing, no reason attached, no closing flourish. When he rewrote a
sentence he never once made it longer.

**How the drafts write** — still in the tree as of writing:

> "Each owner needs theirs before their personal return can be finished — not
> merely to file it, but to prepare it at all. That is the constraint that
> governs this whole engagement's timing."
>
> "If the records are late, the K-1s are late, and every owner's personal return
> is late behind them. One incomplete business file delays as many personal
> returns as there are owners."
>
> — `04-TEMPLATES/SATC Engagement Letter - Business Return.html:63-64`

Both marked **delete**. The shape: sentence one states the fact, sentence two
says it again with more force and an abstract noun ("the constraint that
governs"). That shape is the single most-deleted thing in the review history.
His verdict on the letter carrying it — and, separately, on the delivery letter:
*"god this is full of crap, scrutinize this before coming back to me"*

---

# Part 1 — Say it once

## T1 · A fact lives in one document. A second document may name it only if the sentence carries a fact of its own.

Pointing at a clause is not content. If you delete the clause reference and
nothing is left, delete the sentence.

> "it legitimately annoys me that you can't understand that this is redundant and
> explained elsewhere, like stop repeating things for the sake of repeating. we
> want certain things to surely match, but i don't want you to keep restating
> every last thing"

Deleted on his instruction, all from the fee estimate:

- ~~"The same list as the What we will prepare section of your engagement letter."~~
- ~~"Only the work listed in the scope section of the engagement letter is included."~~
- ~~"Billing and payment terms are in the Fees and billing section of the engagement letter."~~ — *"why is this even under what the estimate assumes? delete"*
- ~~"Section 02 sets out how that works and who does what."~~ (business letter; also referenced by number, which T-contract §5 already forbids)

Still live and still failing this test:
`SATC Engagement Letter - Business Return.html:58` carries that last sentence.

See **T20** for the pointer sentences that legitimately stay.

## T2 · Never restate the heading in the items under it.

> "the section is titled 'what this estimate assumes' so why say 'this estimate
> assumes' in each bullet"

**Before:** `"{label} — this estimate assumes {assumes}, and does not include work beyond it. If {trigger}, {consequence}."`
**After:** `"{label} — {assumes}. If {trigger}, {consequence}."`
(`fee-schedule.yaml → phrases.assumption`)

Same failure on the website intake: three help lines reading "Select all that
apply" sat directly under a form that already prints "Select all that apply"
above every multi-select step. All three deleted rather than reworded.

## T3 · Two names for one list is a bug. Pick the owning document's name and use it everywhere.

> "why would you change what we will prepare to what we are doing? pick one"

The estimate's scope block was headed **What we are doing**; the engagement
letter's section is **What we will prepare**. Two names made the reader check
whether they were the same list. Now one name: the letter's, because the letter
owns scope.

## T4 · A reassurance is made once, at the point where it changes what happens next.

> "i cannot stand this ai-coded crap of 'we will tell you as soon as we see it'
> this is a tenant i will follow, maybe it belongs in some places, but straight
> up stop repeating stuff literally everywhere. particularly in writing where we
> have to update everything everywhere"

"we will tell you as soon as we see it" was on four separate phrases in the fee
schedule. It survives on exactly one — `beyond_priced`, where the client is
being told a number before the work and asked to agree it. Everywhere else it
was wallpaper, and it meant changing the promise once meant changing it in four
places.

## T5 · Do not ask for the same thing twice inside one document.

The onboarding letter's section 03 told a client with a previous accountant to
"send us your most recent filed return" when section 01's checklist had asked
for last year's return **six lines above**. Deleted.

> "we can correct by saying something does not apply, not ask for even more info
> if we think we have it all. the interview should tell us what we have to
> collect"

---

# Part 2 — Cut the sentence after the sentence

## T6 · A sentence whose only job is to intensify the sentence before it gets deleted. The first sentence already said the fact.

The clearest single rule in this file. Every one of these was marked delete:

| Kept | Deleted |
|---|---|
| "The entity return produces a Schedule K-1 for every owner." | "Each owner needs theirs before their personal return can be finished — not merely to file it, but to prepare it at all. That is the constraint that governs this whole engagement's timing." |
| "Our target for delivering the K-1s is <date>, provided the entity's records reach us complete by <date>." | "If the records are late, the K-1s are late, and every owner's personal return is late behind them. One incomplete business file delays as many personal returns as there are owners." |

Tell: the deleted sentence opens with a demonstrative pointing back — *That is…*,
*This means…*, *One … delays as many …* — or restates the same causal chain in
bigger words. Nothing in it is new.

## T7 · Delete the consequence a reader derives for free.

> "take out ' - and should not be relied on for that purpose' words like this
> are self-evident based on the words surrounding it"

> "same with the 'if a lender or investor asks…' statement. we don't need to
> explicitly say that part - it is self-evident by the first part. signing off
> on this should indicate you understand that if it isn't in this letter we
> aren't doing it. stop making things do duplicative in this nature - it is very
> much AI coded"
>
> "delete 'We will speak with your attorney, banker, or advisor only if you
> instruct us in writing.' this is self-evident"

Deleted across the set: the reliance tail (3 letters), the lender/investor
sentence (2), the attorney/banker sentence (2) — that last one duplicated the
sentence immediately before it.

## T8 · Do not narrate our own tone, our own reasoning, or our own inability.

> "also literally this is 100% what i mean by ai-coded bullshit: *If an item does
> not apply to you, tell us that rather than leaving it out — we cannot tell a
> missing document from one that does not exist, and we will keep asking.*
> this entire sentence reads like someone who can't form the subject of a
> sentence first. just tell them to let us know, in a shorter way"

**Before:** the sentence above.
**After:** tell them to say so. Nothing about what we can and cannot tell apart.

That sentence is **still live at `SATC Extension Notice.html:95`** and is the
first thing to remove there.

Also cut from the delivery letter, for the same reason: *"that is a boundary,
not a brush-off"* — the firm did not ask for that one; it was us commenting on
our own manners inside a client's letter.

## T9 · Cut the "why we want it" tail. Keep the ask.

A reason survives only when the reason changes what the reader does.

| Before | After (his) |
|---|---|
| "Pay each authority directly — never send a tax payment to us, and never to anyone who telephones claiming to be us. If you are unsure whether a request is genuine, email \<address\> and ask." | "For your safety, Pay each authority directly" |
| "If this letter states your understanding, sign and return a copy. Sign through Encyro and it comes straight back to us." | "If this letter states your understanding, sign below." |

Third case, on why we prefer one document per file: *"frankly it is not easier
for them to put things in one at a time, and we are developing software to solve
this. say we prefer one document per file, but we will leave it at that"* —
state the preference, drop the invented rationale.

Not yet swept: `SATC Engagement Letter - Bookkeeping.html:124` still carries the
long signature line.

---

# Part 3 — Say what is true, and only what is true

## T10 · Describe the process that actually happens. Ask before writing a step you have not been told.

Every one of these was a factual error dressed as polished copy:

> On *"Nothing begins until this is back with us"*: "just delete this they dont
> send it to us - it would be sent automatically via encyro and i dont care to
> say that again"
>
> "they do not send it via encyro - we collect it directly through our
> sharepoint. we will send a link to their email to upload stuff, we expect them
> to check for encyro for singing docs (this would be how the engagement letter
> gets to them). **i question how well you understand the proceses**"
>
> "we dont require login to Encyro, we just email encrypted via encyro. so just
> delete — it is waiting for you in Encyro." · "we do not need SS cards, we do
> require the numbers" · "we don't sign the return - we sign the form that
> allows us to file" *(so "We will not sign a return…" became "We will not
> prepare or file a return…")*

If you cannot name where a step happens and who does it, leave
`[CONFIRM: …]`. A confident wrong sentence costs more than a blank.

Same rule for names of real things: the IRS form is an e-file **authorization**.
British spelling on that word named a document that does not exist. American
English throughout the client-facing text, and two tests hold it.

## T11 · Do not state as certain what is only possible.

"will likely require an extension" → **"may require"**, in three templates.
The firm: *"we don't want to make statements that sound like it will definitely
happen."*

## T12 · The default is implied. Say only what departs from it.

> "standard is implied - itemized is not. so on essentials and starter, we can
> keep standard. for the higher ones just say itemized (and we would default to
> standard if it were higher, which you dont need to specify)"

---

# Part 4 — Whose side the sentence is on

## T13 · A request stays a request. Never convert an ask into a transfer of blame.

**Before** (delivery letter): *"Review the returns before you sign anything.
They are prepared from the information you gave us, and the What you are
responsible for section of your engagement letter puts their contents on you…"*

> "this is such an awfully malformed statement to make - literally makes it
> sound like we are pinning this work on them rather than asking them to review
> it as it is ultimately theirs. you can just do better."

He then deleted the softened retry too — *"just delete Please review the returns
before you sign. They are your returns, and a figure that looks wrong to you is
worth telling us about — a correction before filing is a phone call, and after
filing it is an amended return."* — and replaced it with an instruction: *"in
section 02 make the first line **Review your returns**"*.

Still live at `SATC Tax Return Delivery Letter.html:67`.

## T14 · Their choice, our limit. State what we will and will not do; do not disapprove of them.

> "instead of 'though it may not be secure and we would not advise it' we should
> just say this is at the client's discretion and we take no responsibility if
> we diverge from this"
>
> "instead of warning against emailing, say it is at their risk and we will not
> be sending them stuff that is unprotected and/or unencrypted"

**After**, his own line, and he asked for it bolded:
> "Emailing or otherwise transmitting unprotected documents are done so at your
> own risk."

Carried to four templates as *"that is your choice, and we take no
responsibility for it."*

## T15 · Do not advertise our own virtue. Say the price; behave well silently.

> "we do not need to specify we correct our own mistakes for free - we are only
> talking about how we charge for amendments. we would not re-file for free if
> someone did not give us all the info until later"

The $0 case stayed in the schedule and stopped publishing: on a public page it
reads as a marketing claim and invites an argument about whose error a given one
was. Same instinct behind *"notices and corresponds belong in a different letter
engagement or would be discussed anyway, get rid of it. **can't bite if not a
secret**"*.

---

# Part 5 — Shape

## T16 · Lead with what the reader must do, inside the first six words.

| Before | After (his) |
|---|---|
| "Your returns are ready — 2026 tax year" | "Action required: please review your 2026 tax returns" |
| "Your returns are finished." | "We have completed our work on your returns." |
| "This letter tells you what we prepared, what you need to do, and by when. Read section 02 first — nothing is filed until you act on it." | "Below is a summary of what we prepared and your next steps." |

## T17 · One ask per line. Do not run two different things into one sentence or one table cell.

> "The ID only if we have not seen it before. We need the numbers, not the cards"
> — "**this is confusing** --> put Photo ID and SSNs on their own lines to
> reduce confusion"

Same reason the package's covers list moved out of the line's detail sentence
and onto its own field on the estimate: nine clauses inside a table cell is a
paragraph nobody finishes.

## T18 · A section states the decision. It does not walk through the reasoning, the edge cases, or the mechanics.

His notes on a single letter, in one sitting:

> "take away section 03, it's too much" · "adjust section 04 to state we may
> request to contact them if it is necessary to perform our work. **shorten it a
> lot**" · "section 05 is too much and too specific. let them know it means we
> can start working and will do our best to reach out in a non-obtrusive way if
> we're missing anything" · "i want all of it to be conveyed more concisely
> **they can ask me questions if they have to**" · "this is way too much crap"

That last clause is the governing standard: a client who wants the detail will
ask. Write the decision; let the question come.

## T19 · Write in the client's vocabulary, not the spec's. No client-facing sentence past 28 words.

> "i would never expect a client to understand what an engagement letter is
> inherently. 'governs the work' come on."

The rejected sentence was transcribed off an internal brief. A requirement
written for whoever builds the thing says what the document must be *true
about*; the copy has to say it in words the reader already has.

Banned from anything a prospect reads on the site, and the right instinct
everywhere: *governs, constitutes, accompanies, pursuant, at our discretion,
deemed, shall be, herein*. Inside an engagement letter the document must name
itself, so "engagement letter" is unavoidable there — but "governs" is not.

---

# Part 6 — What must NOT be cut

Read this part before applying Parts 1–5. Over-cutting has its own cost and
several of these sentences were kept deliberately.

## T20 · A sentence that states a fact AND cites a clause as its authority is load-bearing. It stays.

The test is mechanical: **strike the clause reference. Is a fact left standing?**

| Filler — deleted | Load-bearing — kept |
|---|---|
| "The same list as the What we will prepare section of your engagement letter." | "As the *Ending this engagement* section of your engagement letter provides, either of us may end it in writing at any time." |
| "Billing and payment terms are in the Fees and billing section of the engagement letter." | "Due on presentation. Balances unpaid after thirty (30) days carry interest at the maximum rate Ohio law permits, per the *Fees and billing* section of your engagement letter." |
| "Only the work listed in the scope section of the engagement letter is included." | "As the *Fees and billing* section of your engagement letter sets out, we may suspend or withdraw if requested information is not provided." |
| "Section 02 sets out how that works and who does what." | "The *Your records, our files, and delivery* section of your engagement letter says how long we hold our copies and what happens to them; that is our retention, not yours." |

The rule as it was recorded when the invoice's note was cut: **"The pointer half
is gone and the fact after it stays."**

## T21 · Both halves of a boundary get said. Half a boundary is a promise the firm is not making.

"capped at four" alone reads as a cap the client will never exceed, and they
find out otherwise on the invoice. The firm, settling it: *"4 is a soft cap.
Then we add dollars for time."* So the phrase carries both:

> "Capped at 4 — beyond that the time is billed at $150 an hour"

Same principle kept the website consent wording untouched while everything
around it was cut: sending the form does not create an engagement, and SATC is
engaged only on a signed letter. Concision never removes the second half of a
two-part fact.

## T22 · The compliance floor is not style and is never cut for length.

None of Parts 1–5 authorizes touching any of these. If a required sentence feels
bloated, shorten it and keep the negation intact.

- **Banned assurance vocabulary** — *audit, audited, auditing, assurance,
  opinion, review engagement, attest, examination* — except in an explicit
  negation ("We do not perform audits, reviews, or any assurance engagement").
  Those negations are compliance sentences and they stay. `AUTHORING-CONTRACT §5`.
- **The credential is a person, not the firm** — "led by a licensed CPA", never
  "CPA firm". The firm: *"Stop trying to add accountancy stuff - we are not even
  trying to be accredited. The only thing I'm saying is I'm a CPA registered in
  Ohio."*
- **Client PII** — masked or last-4 only in artifacts, logs and samples; never a
  legal name or a full TIN (`CLAUDE.md`). **Drake stays the system of record** —
  no document reads as though SATC computes or files independently of it.
- **Nothing invented** — registration wording, assurance-adjacent wording, fee
  figures, statutory deadlines, anything readable as a guarantee of outcome:
  leave `[CONFIRM: …]`. *"Invented legal wording is worse than a blank. A blank
  gets filled; an invention ships."*

---

# Part 7 — Applying them

## T23 · Apply a note to every template before he reads the next one.

> "i want the feedback taken seriously and applied across templates before i
> review them … **i don't want to review a bunch of templates and have similar
> feedback on each**"

Every pattern he has flagged appeared in three or four templates. When a note
lands: grep the phrase across all ten templates *and* the registry, fix all of
them, then re-render. Known unswept instances as of writing are named in T1, T8,
T9 and T13.

## T24 · Wording is data. He must be able to change a word in one place, and no test may pin his prose.

> "particularly in writing where we have to update everything everywhere" ·
> "templates should be easily customizable to the degree possible - in the sense
> that i can easily manually update how they read" · "for editing stuff it has
> to be easy to add and take out sections as well"

Three places hold client-facing words and only three: the template HTML, the
`phrases`/labels in `fee-schedule.yaml`, and `interview.yaml`. A sentence
assembled anywhere else — in Python — is a bug, because he cannot reach it.

And a test that asserted the literal string "this estimate assumes" failed the
moment he deleted the phrase, which teaches whoever hits it to edit the test
rather than think. Tests assert the **shape** of assembled wording, never the
wording.

---

# The cutting test

Run this over a finished draft, **sentence by sentence, in this order**, before
anyone at the firm sees it. Most of it is close to a lint.

1. **Heading echo.** Does the sentence repeat three or more content words from
   the heading above it? → cut those words. (T2)
2. **Pointer test.** Delete the clause reference. Is a fact left? No → delete the
   whole sentence. Yes → keep it. (T1, T20)
3. **Cross-document grep.** Search the phrase across `04-TEMPLATES/*.html` and
   `fee-schedule.yaml`. More than one hit and not on the T22 list → keep the
   instance where the reader must act on it; delete the rest. (T1, T4)
4. **Second-sentence test.** Cover the sentence and reread the one before it. If
   only emphasis was lost, it stays deleted. (T6)
5. **Demonstrative openers.** Flag any sentence starting *That is / This means /
   This is / Which is / Not merely / One … as many … as*. Almost all are T6.
6. **Reason tail.** Find the em-dash or *because / so that / rather than* tail.
   Delete it. Restore only if the reader's next action changes. (T9)
7. **First-six-words test.** Do the first six words name the reader or what the
   reader must do? No → reorder. Never open with what we cannot tell, cannot
   do, or would not advise. (T8, T16)
8. **Two-asks test.** Does one line carry two different requests, or two
   different documents? → split onto separate lines. (T17)
9. **Vocabulary sweep.** `grep -iE 'governs|constitutes|accompanies|pursuant|at our discretion|deemed|shall be|herein'`
   plus any word naming our internal process. Replace with the client's word. (T19)
10. **Length.** No client-facing sentence over 28 words. No paragraph over three
    sentences. Length is where the wrong register hides. (T19)
11. **Certainty sweep.** `grep -iE 'will likely|typically|generally|in most cases'`
    → "may", unless the hedge is itself the fact. (T11)
12. **Default sweep.** Does the sentence name behavior that happens anyway? → cut. (T12)
13. **Blame test.** Does an ask read as putting the outcome on the client, or as
    our disapproval of their choice? → rewrite as a request, or as our own
    limit. (T13, T14)
14. **Virtue sweep.** Does anything claim we are fair, free, fast, or generous?
    → delete. (T15)
15. **Process check.** Can you name where each step happens and who does it? Any
    you cannot → `[CONFIRM: …]`, not a guess. (T10)
16. **Floor pass — do this last, after all cutting.** Re-run the assurance grep;
    confirm every explicit negation, both halves of every boundary, the
    "licensed CPA" person-form, and every `[CONFIRM:]` survived the edit. (T21, T22)
17. **Sweep the set.** Apply 1–16 to every template that shares the phrase, then
    re-render the samples. (T23)

Then run `AUTHORING-CONTRACT.md §8` — the mechanical self-check for stylesheet,
print, fields and counts. This test is about words; §8 is about the artifact.

---

# What this file replaces

`AUTHORING-CONTRACT.md` **§5 · Voice** stays in force except as below. Two of its
rules produced the drafts the firm rejected. *(Recorded here, not edited there —
that edit is a human's to make.)*

1. **"Give the reason with the rule. A rule with a reason gets followed."** —
   **superseded by T9.** This is the licence under which every deleted
   because-tail was written. Replace with: *Give the rule. Attach a reason only
   when the reason changes what the reader does. If the reader wants the reason,
   they can ask.*

2. **Both worked examples in §5's "Do" list were deleted by the firm on
   26 August.** They are now the wrong model to copy:
   - *"Nothing begins until the signed engagement letter is back with us."* → he
     cut it: *"just delete this they dont send it to us … and i dont care to say
     that again"* (T1, T10).
   - *"We cannot tell a missing document from one that does not exist."* → he
     called it *"100% what i mean by ai-coded bullshit"* (T8).

   Replace both specimens with his own copy: *"If this letter states your
   understanding, sign below."* and *"Emailing or otherwise transmitting
   unprotected documents are done so at your own risk."*

3. **§5's "Restate scope or fees in a document that isn't the one that owns
   them"** — **sharpened by T1 and T20.** As written it bans restating but
   permits pointing, and pure pointer sentences are exactly what he deleted.
   Pointing *is* restating unless the sentence carries a fact of its own.

4. **§5's "Reference other clauses by name, never by number"** — **confirmed**:
   *"delete Section 02 sets out how that works and who does what."*

5. **§6's scope-boundary table** — **unchanged.** T1 is that table applied at
   sentence level rather than at document level.

6. **§8's self-check** — **unchanged, and now runs second.** Cutting test first;
   §8 catches artifact defects, not prose defects, and every note in this file
   survived a clean §8 run.

7. **§5's compliance rules and §9's "what needs a human"** — **untouched and
   supreme.** T22 restates them so no concision tenet reads as authorizing a cut
   there.
