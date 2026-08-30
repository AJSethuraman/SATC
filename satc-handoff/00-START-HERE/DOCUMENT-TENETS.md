# SAT-C — Document Tenets

**Mined from every editing note the firm has given on client-facing documents,
and from the commit diffs those notes produced, 25–26 August 2026.** Read before writing or
revising anything a client receives. Every tenet carries its evidence — a verbatim note, a
real diff, or both; a rule with nothing under it does not belong here. The test each had to
pass: *if this rule had been in force, would that note have needed writing?*

Cite as **T1**, **T7**. Governs `../04-TEMPLATES/`, the wording assembled at render time from
`client-documents/registry/fee-schedule.yaml`, and any new document in the set.
`AUTHORING-CONTRACT.md` still governs structure, stylesheet, fields and compliance vocabulary
— see **What this file replaces**.

---

## 0 · The gap this file exists to close

The firm writes short, flat, lowercase, without ceremony. The drafts write long, explanatory,
slightly lecturing. The gap is not politeness — it is that the drafts keep adding a **second
sentence that explains the first one**.

**How he writes** — all his, as instructions or as replacement copy:

> "just delete this they dont send it to us" · "can't bite if not a secret" · "pick one" ·
> "Including its statements" · "we do not need SS cards, we do require the numbers" · "For
> your safety, Pay each authority directly" · "If this letter states your understanding, sign
> below." · "If your return requires additional work, a new estimate will be provided in
> writing. Additional work will not be begin without your written consent to the new
> estimate."

No throat-clearing, no reason attached, no closing flourish. When he rewrote a sentence he
never once made it longer.

**How the drafts write** — both still in the tree:

> "Each owner needs theirs before their personal return can be finished — not merely to file
> it, but to prepare it at all. That is the constraint that governs this whole engagement's
> timing."
>
> "If the records are late, the K-1s are late, and every owner's personal return is late
> behind them. One incomplete business file delays as many personal returns as there are
> owners."
>
> — `04-TEMPLATES/SATC Engagement Letter - Business Return.html:63-64`

Both marked **delete**. Sentence one states the fact; sentence two says it again with more
force and an abstract noun ("the constraint that governs"). That shape is the single
most-deleted thing in the review history. His verdict on the letter carrying it, and
separately on the delivery letter: *"god this is full of crap, scrutinize this before coming
back to me"*.

### The positive model — what has never been objected to

Found by diffing every template against its first commit. These have survived four rounds
untouched — the house voice working:

> "We will confirm in writing once each return has been transmitted and accepted. If you do
> not get that confirmation from us, assume nothing has been filed and call." · "Mail each
> return separately, to the address on that return. Federal, state and local go to different
> places, and a return sent to the wrong authority is not late — it is unfiled." · "Signing
> the authorization is not the same as paying." · "Estimated payments are not optional for
> everyone. Where they apply, missing one carries an underpayment charge even if the return
> itself is filed and paid on time."

The surviving shape: **an instruction or a fact, then a second sentence carrying a NEW fact —
an exception, a failure mode, a deadline.** Never an amplification, never a reason of ours,
never a comment on our own tone. These do contain because-shaped clauses; the difference is
that the consequence belongs to the reader and changes what they do. That is the whole
carve-out in T9.

---

# Part 1 — Say it once

## T1 · A fact lives in one document. A second document may name it only if the sentence carries a fact of its own.

> "it legitimately annoys me that you can't understand that this is redundant and explained
> elsewhere, like stop repeating things for the sake of repeating. we want certain things to
> surely match, but i don't want you to keep restating every last thing"

Deleted on his instruction, all from the fee estimate (`8a2562f`):

- ~~"The same list as the What we will prepare section of your engagement letter."~~
- ~~"Only the work listed in the scope section of the engagement letter is included."~~
- ~~"Billing and payment terms are in the Fees and billing section of the engagement letter."~~ — *"why is this even under what the estimate assumes? delete"*
- ~~"Section 02 sets out how that works and who does what."~~ (business letter; referenced by number too)

**How the first of those got there:** it was *added* one round earlier by `bbd1930`, fixing a
different note — "either it needs to list what we are doing in one place, or needs to be
comparable in both". The fix reproduced the list, then captioned the copy. A fix that adds a
sentence explaining the fix is the failure mode (T25). Still live:
`SATC Engagement Letter - Business Return.html:58`. See **T21** for pointer sentences that
legitimately stay.

## T2 · Never restate the heading in the items under it.

> "the section is titled 'what this estimate assumes' so why say 'this estimate assumes' in
> each bullet"

- **Before:** `"{label} — this estimate assumes {assumes}, {where}. If {trigger}, {consequence}."`
- **After:** `"{label} — {assumes}. If {trigger}, {consequence}."`

(`fee-schedule.yaml → phrases.assumption`, `8a2562f`)

Same failure on the website intake: three help lines reading "Select all that apply" under a
form that already prints "Select all that apply" above every multi-select step. All three
deleted rather than reworded.

## T3 · Two names for one list is a bug. Use the owning document's name.

> "why would you change what we will prepare to what we are doing? pick one"

The estimate's scope block was headed **What we are doing**; the letter's section is **What we
will prepare**. Two names make the reader check whether they are the same list. Now one: the
letter's, because the letter owns scope. `bbd1930` also deleted the phrase variant
`includes_only`, which said what `includes` said.

## T4 · A reassurance is made once, at the point where it changes what happens next.

> "i cannot stand this ai-coded crap of 'we will tell you as soon as we see it' this is a
> tenant i will follow, maybe it belongs in some places, but straight up stop repeating stuff
> literally everywhere. particularly in writing where we have to update everything everywhere"

The diff: that clause sat on four phrases in `fee-schedule.yaml` (`beyond_hourly`,
`beyond_priced`, `capped_soft`, `capped_soft_only`) and left all four in `2a41777`. It
survives once, in substance, on the priced boundary — where the client is told a number before
the work and asked to agree it. Elsewhere it was wallpaper, and it meant changing one promise
in four places. Also cut on his instruction: ~~"and we will keep that to one message rather
than a run of them"~~. A promise about how considerate we intend to be is not a usable fact.

## T5 · Do not ask for the same thing twice inside one document.

The onboarding letter's section 03 told a client with a previous accountant to "send us your
most recent filed return" when section 01's checklist had asked for last year's return **six
lines above**. Deleted in `b815cd2`.

> "we can correct by saying something does not apply, not ask for even more info if we think
> we have it all. the interview should tell us what we have to collect"

---

# Part 2 — Cut the sentence after the sentence

## T6 · A sentence whose only job is to intensify the sentence before it gets deleted. The first sentence already said the fact.

The clearest single rule in this file. All marked delete:

| Kept | Deleted |
|---|---|
| "The entity return produces a Schedule K-1 for every owner." | "Each owner needs theirs before their personal return can be finished — not merely to file it, but to prepare it at all. That is the constraint that governs this whole engagement's timing." |
| "Our target for delivering the K-1s is \<date\>, provided the entity's records reach us complete by \<date\>." | "If the records are late, the K-1s are late, and every owner's personal return is late behind them. One incomplete business file delays as many personal returns as there are owners." |

Same shape at clause scale (`5faa4c7`): "Questions about what we prepared are part of the work
**and always will be**." → tail gone. Tell: the deleted sentence opens with a demonstrative
pointing back — *That is…*, *This means…*, *One … as many … as* — or restates the same causal
chain in bigger words. Nothing is new.

## T7 · Delete the consequence a reader derives for free.

> "take out ' - and should not be relied on for that purpose' words like this are self-evident
> based on the words surrounding it"
>
> "same with the 'if a lender or investor asks…' statement. we don't need to explicitly say
> that part - it is self-evident by the first part. signing off on this should indicate you
> understand that if it isn't in this letter we aren't doing it. stop making things do
> duplicative in this nature - it is very much AI coded"
>
> "delete 'We will speak with your attorney, banker, or advisor only if you instruct us in
> writing.' this is self-evident"

Deleted across the set in `2a41777`: the reliance tail (3 letters), the lender/investor
sentence (2), the attorney/banker sentence (2) — that last one duplicated the sentence
immediately before it.

## T8 · Do not narrate our own tone, our own reasoning, or our own inability.

> "also literally this is 100% what i mean by ai-coded bullshit: *If an item does not apply to
> you, tell us that rather than leaving it out — we cannot tell a missing document from one
> that does not exist, and we will keep asking.* this entire sentence reads like someone who
> can't form the subject of a sentence first. just tell them to let us know, in a shorter way"

**After** (`353a2d8`): "If something on this list does not apply to you, just tell us."

> **CORRECTED 27 Aug 2026.** This said the flagged sentence was *"still live at
> `SATC Extension Notice.html:95`"*. It is not, and was not when the claim was written:
> that line already carried the corrected form. Measured against all twelve templates
> while building the linter.

Three more, deleted in the diffs and never replaced:

- ~~"That is a boundary, not a brush-off."~~ — commenting on our own manners.
- ~~"Every amount and date above comes from the returns themselves."~~ — vouching for our own
  arithmetic inside the client's letter.
- ~~"A file that arrives complete and reconciled moves faster and, because our estimate
  assumes it, usually costs what we quoted."~~ — explaining our economics to the person paying
  them.

## T9 · Cut the "why we want it" tail. Keep the ask.

A reason survives only when the consequence belongs to the reader and changes what they do
(see the positive model in §0).

| Before | After |
|---|---|
| "Pay each authority directly — never send a tax payment to us, and never to anyone who telephones claiming to be us. If you are unsure whether a request is genuine, email \<address\> and ask." | "For your safety, Pay each authority directly" *(his)* |
| "If this letter states your understanding, sign and return a copy. Sign through Encyro and it comes straight back to us." | "If this letter states your understanding, sign below." *(his)* |
| "Ask before you guess — a five-minute question now is cheaper than a correction later." | "Ask us early rather than guessing." |
| "Responding to a notice is a separate engagement, but reading one and telling you what it actually says costs nothing." | "Reading one and telling you what it actually says costs nothing." |

And on why we prefer one document per file: *"frankly it is not easier for them to put things
in one at a time, and we are developing software to solve this. say we prefer one document per
file, but we will leave it at that"* — state the preference, drop the invented rationale. Not
yet swept: `SATC Engagement Letter - Bookkeeping.html:124` still carries the long signature
line.

---

# Part 3 — Say what is true, and only what is true

## T10 · Describe the process that actually happens. Ask before writing a step you have not been told.

Every one of these was a factual error dressed as polished copy:

> On *"Nothing begins until this is back with us"*: "just delete this they dont send it to us
> - it would be sent automatically via encyro and i dont care to say that again"
>
> "they do not send it via encyro - we collect it directly through our sharepoint. we will
> send a link to their email to upload stuff, we expect them to check for encyro for singing
> docs (this would be how the engagement letter gets to them). **i question how well you
> understand the proceses**"
>
> "we dont require login to Encyro, we just email encrypted via encyro. so just delete — it is
> waiting for you in Encyro." · "we do not need SS cards, we do require the numbers" · "we
> don't sign the return - we sign the form that allows us to file" *(so "We will not sign a
> return…" became "We will not prepare or file a return…")*

If you cannot name where a step happens and who does it, leave `[CONFIRM: …]`. A confident
wrong sentence costs more than a blank. Same for the names of real things: the IRS form is an
e-file **authorization**, and British spelling on that word named a document that does not
exist (`b815cd2`). American English throughout client-facing text; two tests hold it.

## T11 · Do not state as certain what is only possible.

"will likely require an extension" → **"may require"**, in three templates (`2a41777`). The
firm: *"we don't want to make statements that sound like it will definitely happen."*

## T12 · The default is implied. Say only what departs from it.

> "standard is implied - itemized is not. so on essentials and starter, we can keep standard.
> for the higher ones just say itemized (and we would default to standard if it were higher,
> which you dont need to specify)"

## T13 · A document must never state two things that cannot both be true.

The same note caught a real bug. `covers:` inherits down the package ladder, so a Standard
estimate printed **"The standard deduction"** and **"Itemized deductions"** one after the
other. A return takes one or the other. The estimate said something impossible, and buried the
one line explaining why the package costs more (`a107e69`). Read a *rendered* document: this
was invisible in the source and obvious on the page.

---

# Part 4 — Whose side the sentence is on

## T14 · A request stays a request. Never convert an ask into a transfer of blame.

**Before** (delivery letter): *"Review the returns before you sign anything. They are
prepared from the information you gave us, and the What you are responsible for section of
your engagement letter puts their contents on you…"*

> "this is such an awfully malformed statement to make - literally makes it sound like we are
> pinning this work on them rather than asking them to review it as it is ultimately theirs.
> you can just do better."

He deleted the softened retry too — *"just delete Please review the returns before you sign.
They are your returns, and a figure that looks wrong to you is worth telling us about…"* — and
replaced it with an instruction: *"in section 02 make the first line **Review your
returns**"*.

> **CORRECTED 27 Aug 2026.** This said the sentence was *"still live at
> `SATC Tax Return Delivery Letter.html:67`"*. That line is an `[[END EACH]]` marker;
> section 02 opens with his own "Review your returns". The claim was already stale.

**Not a ban on assigning responsibility.** "You chose to file on paper, so filing these
returns is your responsibility, not ours" has survived every round untouched. The objection is
to bolting a liability clause onto a *request*.

## T15 · Their choice, our limit. State what we will and will not do; do not disapprove of them.

> "instead of 'though it may not be secure and we would not advise it' we should just say this
> is at the client's discretion and we take no responsibility if we diverge from this"
>
> "instead of warning against emailing, say it is at their risk and we will not be sending
> them stuff that is unprotected and/or unencrypted"

**After**, his own line, bolded at his request: *"Emailing or otherwise transmitting
unprotected documents are done so at your own risk."* Carried to four templates as *"that is
your choice, and we take no responsibility for it."*

## T16 · Do not advertise our own virtue. Say the price; behave well silently.

> "we do not need to specify we correct our own mistakes for free - we are only talking about
> how we charge for amendments. we would not re-file for free if someone did not give us all
> the info until later"

The $0 case stayed in the schedule and stopped publishing: on a public page it reads as a
marketing claim and invites an argument about whose error a given one was. Same instinct
behind *"notices and corresponds belong in a different letter engagement or would be discussed
anyway, get rid of it. **can't bite if not a secret**"* — and behind the delivery letter's own
version of it, third row of the T9 table.

---

# Part 5 — Shape

## T17 · Lead with what the reader must do, inside the first six words.

| Before | After (his) |
|---|---|
| "Your returns are ready — 2026 tax year" | "Action required: please review your 2026 tax returns" |
| "Your returns are finished." | "We have completed our work on your returns." |
| "This letter tells you what we prepared, what you need to do, and by when. Read section 02 first — nothing is filed until you act on it." | "Below is a summary of what we prepared and your next steps." |

## T18 · One ask per line. Do not run two different things into one sentence or one table cell.

> "The ID only if we have not seen it before. We need the numbers, not the cards" — "**this is
> confusing** --> put Photo ID and SSNs on their own lines to reduce confusion"

Same reason `includes` moved out of the detail sentence onto its own field on the estimate
(`bbd1930`): nine clauses inside a table cell is a paragraph nobody finishes.

## T19 · A section states the decision. It does not walk through the reasoning, the edge cases, or the mechanics.

> "take away section 03, it's too much" · "adjust section 04 to state we may request to
> contact them if it is necessary to perform our work. **shorten it a lot**" · "section 05 is
> too much and too specific. let them know it means we can start working and will do our best
> to reach out in a non-obtrusive way if we're missing anything" · "i want all of it to be
> conveyed more concisely **they can ask me questions if they have to**" · "this is way too
> much crap"

The diff shows the cost: the onboarding letter went from six sections to five, losing "Access
we may ask for" outright and collapsing "What happens once we have everything" from a
four-item list plus a paragraph into two sentences. **"they can ask me questions if they have
to"** is the governing standard. Write the decision; let the question come.

## T20 · Write in the client's vocabulary, not the spec's. No client-facing sentence past 28 words.

> "i would never expect a client to understand what an engagement letter is inherently.
> 'governs the work' come on."

The rejected sentence had been transcribed off an internal brief. A requirement written for
whoever builds the thing says what the document must be *true about*; the copy has to say it
in words the reader already has. Banned from anything a prospect reads on the site, and the
right instinct everywhere: *governs, constitutes, accompanies, pursuant, at our discretion,
deemed, shall be, herein*.

> **[CONFIRM: `accompanies` — your call.]** It is on this list and it is **live in five
> templates**, in copy you have approved four times: *"the estimate accompanying this
> letter"*, *"Accompanies our engagement letter"*. The linter ships **without** it, because
> a check that fires on approved copy on its first run gets muted and takes the other six
> words with it. Either the word comes off this list or those five sentences change — four
> rounds of review say the former, but it is your list. An engagement letter must name itself; "governs" is still not
needed.

---

# Part 6 — What must NOT be cut

Read this part before applying Parts 1–5. Over-cutting has its own cost.

## T21 · A sentence that states a fact AND cites a clause as its authority is load-bearing. It stays.

Strike the clause reference. **Is a fact left standing?**

| Filler — deleted | Load-bearing — kept |
|---|---|
| "The same list as the What we will prepare section of your engagement letter." | "As the *Ending this engagement* section of your engagement letter provides, either of us may end it in writing at any time." |
| "Billing and payment terms are in the Fees and billing section of the engagement letter." | "Due on presentation. Balances unpaid after thirty (30) days carry interest at the maximum rate Ohio law permits, per the *Fees and billing* section of your engagement letter." |
| "Only the work listed in the scope section of the engagement letter is included." | "As the *Fees and billing* section of your engagement letter sets out, we may suspend or withdraw if requested information is not provided." |
| "Section 02 sets out how that works and who does what." | "The *Your records, our files, and delivery* section of your engagement letter says how long we hold our copies and what happens to them; that is our retention, not yours." |

The rule as recorded when the invoice's note was cut: **"The pointer half is gone and the fact
after it stays."** The delivery letter's `.ref` block has said it since day one and no round
has touched it: *"No restated scope. The engagement letter owns it. This letter points at two
of its clauses by name and restates neither."*

## T22 · Both halves of a boundary get said. Half a boundary is a promise the firm is not making.

"capped at four" alone reads as a cap the client will never exceed, and they find out
otherwise on the invoice. The firm: *"4 is a soft cap. Then we add dollars for time."* So the
phrase carries both:

> "Capped at 4 — beyond that the time is billed at $150 an hour"

What the `capped_soft` diff shows: the shortening pass in `2a41777` removed the promise tail
and left both halves of the boundary intact. That is the line. The same principle kept the
website consent wording untouched while everything around it was cut.

## T23 · The compliance floor is not style and is never cut for length.

Nothing in Parts 1–5 authorizes touching any of this. If a required sentence feels bloated,
shorten it and keep the negation intact. The assurance-negation paragraphs in the three
engagement letters have passed every round unchanged — correct and deliberate.

- **Banned assurance vocabulary** — *audit, audited, auditing, assurance, opinion, review
  engagement, attest, examination* — except in an explicit negation ("We do not perform
  audits, reviews, or any assurance engagement"). Those negations are compliance sentences and
  they stay. `AUTHORING-CONTRACT §5`.
- **The credential is a person, not the firm** — "led by a licensed CPA", never "CPA firm".
  The firm: *"Stop trying to add accountancy stuff - we are not even trying to be accredited.
  The only thing I'm saying is I'm a CPA registered in Ohio."*
- **Client PII** — masked or last-4 only in artifacts, logs and samples; never a legal name or
  a full TIN (`CLAUDE.md`). **Drake stays the system of record** — no document reads as though
  SATC computes or files independently of it.
- **Nothing invented** — registration wording, assurance-adjacent wording, fee figures,
  statutory deadlines, anything readable as a guarantee of outcome: leave `[CONFIRM: …]`.
  *"Invented legal wording is worse than a blank. A blank gets filled; an invention ships."*

---

# Part 7 — Revising, which is where most of the damage happened

## T24 · A sentence flagged twice gets deleted, not reworded a third time.

The most expensive pattern in the whole history, and it is only visible in the diffs. **How
Encyro got explained three times:**

| Round | Sentence |
|---|---|
| v1 | "We use Encyro for everything containing your personal or financial information. You will receive an invitation at \<email\>; the link works without an account…" |
| v2 `353a2d8` | "Documents for signature come through Encyro, to the same address. That is where the engagement letter is now, and where your finished returns will be delivered." |
| v3 `5faa4c7` | "Anything for signature comes to you by email, encrypted through Encyro, at the same address. That is how the engagement letter reached you, and how your finished returns will be delivered." |
| v4 | "delte *That is how the engagement letter reached you, and how your finished returns will be delivered.*" — deleted |

Each pass reworded the explanation instead of asking whether one was needed. The commit that
settled it is titled *"Encyro stops being explained three times"*. Same story on the tax
letter's section 06 fee clause — edited in five separate commits — and on the delivery
letter's review paragraph, rewritten in round three and deleted in round four.

**Operational form:** before rewording a sentence a second time, delete it and read the
paragraph without it. If the paragraph still works, that is the edit.

## T25 · Do not answer a decision by adding prose to a document that already honours it.

> "i do not know why you re-worded it, it was fine and already explained this principal"

He had ruled that mid-job re-quoting should be avoided. The response widened the tax letter's
fee clause to spell out the assumptions mechanism (`324e0cc`) — and it was reverted whole
(`3c3032a`): *"restated something the letter already covered and added length to the paragraph
a client is most likely to read closely."* The ruling was already honoured, in the estimate's
own assumptions block. The sign-off register now carries: *"Section 06 fee clause was
rewritten 25 Aug and reverted at the firm's instruction. Do not rewrite it again."*

Ask first: **which document owns this, and does it already say it?** A ruling usually needs a
config change or nothing, not a paragraph.

## T26 · Finish the cut. A deletion is not done until nothing dangles and nothing else still points at it.

Cutting has its own failure mode, and it bit twice:

- Dropping "this estimate assumes" from the assumption phrase left **"and does not include
  work beyond it"** dangling with nothing before it — which is how anyone noticed the clause
  was meaningless on every line. It printed on every bullet, immediately before a sentence
  saying exactly what happens beyond it.
- Retiring the `ReturnInstruction` field took **three templates, three FIELDS docs, three
  samples, the field registry and firm settings** (`a107e69`). Left half-done, a template
  merges a field nothing supplies.
- And it revealed a test passing for the wrong reason: the placeholder guard poked
  `ReturnInstruction`, so once no template merged it the test checked nothing and stayed green.

After any cut: re-read the surrounding sentence whole, grep the phrase and the field name
across templates, FIELDS docs, samples and the registry, and **re-render** — T13's
contradiction was only visible on the page.

## T27 · Apply a note to every template before he reads the next one.

> "i want the feedback taken seriously and applied across templates before i review them … **i
> don't want to review a bunch of templates and have similar feedback on each**"

Every pattern he has flagged appeared in three or four templates. When a note lands: grep the
phrase across all ten templates *and* the registry, fix all of them, then re-render. Unswept
instances as of writing: **none**.

> **CORRECTED 27 Aug 2026.** This read "T1, T8, T9, T14". Three of the four were already
> swept when it was written — the claims were never re-measured. The fourth, **T9**, was
> real: `SATC Engagement Letter - Bookkeeping.html:124` still carried
> *"Sign through Encyro and it comes straight back to us."* a full day after that sentence
> was replaced in every other letter, and this file said so in writing the whole time.
>
> **A note in a document saying a thing is still wrong is not a control.** All nineteen
> deleted sentences now live in `client-documents/registry/retired.yaml`, and the pre-send
> gate refuses any document that carries one. That is what closed T9, and it is what stops
> the next one needing a note.

## T28 · Wording is data. He must be able to change a word in one place, and no test may pin his prose.

> "particularly in writing where we have to update everything everywhere" · "templates should
> be easily customizable to the degree possible - in the sense that i can easily manually
> update how they read" · "for editing stuff it has to be easy to add and take out sections as
> well"

Three places hold client-facing words and only three: the template HTML, the
`phrases`/labels in `fee-schedule.yaml`, and `interview.yaml`. A sentence
assembled anywhere else — in Python — is a bug, because he cannot reach it.

A test asserting the literal string "this estimate assumes" failed the moment he deleted the
phrase, which teaches whoever hits it to edit the test rather than think. Tests assert the
**shape** of assembled wording, never the wording. And write new wording in the current
register: `capped_soft` was born in round eleven already carrying the promise tail that round
three had to strip from four phrases at once.

---

# The cutting test

Run over a finished draft, **sentence by sentence, in this order**, before anyone at the firm
sees it. Most of it is close to a lint.

1. **Heading echo.** Sentence repeats three or more content words from the
   heading above it → cut them. (T2)
2. **Pointer test.** Delete the clause reference. Fact left? No → delete the
   sentence. Yes → keep it. (T1, T21)
3. **Cross-document grep.** Search the phrase across `04-TEMPLATES/*.html` and
   `fee-schedule.yaml`. More than one hit and not on the T23 list → keep the
   instance where the reader must act on it; delete the rest. (T1, T4)
4. **Second-sentence test.** Cover it and reread the one before. Only emphasis
   lost → stays deleted. Carries a NEW fact — exception, failure mode, deadline
   → keep. (T6, §0)
5. **Demonstrative openers.** Flag *That is / This means / This is / Which is /
   Not merely / One … as many … as*. Almost all are T6.
6. **Reason tail.** Find the em-dash or *because / so that / rather than* tail
   and delete it. Restore only if the consequence is the reader's. (T9)
7. **First-six-words test.** Do they name the reader or what the reader must do?
   No → reorder. Never open with what we cannot tell or would not advise. (T8, T17)
8. **Two-asks test.** One line carrying two requests or two documents → split. (T18)
9. **Vocabulary sweep.** `grep -iE 'governs|constitutes|accompanies|pursuant|at our discretion|deemed|shall be|herein'`
   plus any word naming our internal process. (T20)
10. **Length.** No client-facing sentence over 28 words; no paragraph over three
    sentences. Length is where the wrong register hides. (T20)
11. **Certainty.** `grep -iE 'will likely|typically|generally|in most cases'` →
    "may", unless the hedge is the fact. (T11)
12. **Default.** Names behavior that happens anyway → cut. (T12)
13. **Blame.** Does an ask read as putting the outcome on the client, or as
    disapproval of their choice? → rewrite as a request or as our own limit.
    Responsibility that genuinely moved may be stated plainly. (T14, T15)
14. **Virtue.** Anything claiming we are fair, free, fast or generous, or
    describing our own tone or arithmetic → delete. (T8, T16)
15. **Process.** Can you name where each step happens and who does it? No →
    `[CONFIRM: …]`, not a guess. (T10)
16. **Revision check.** `git log -p --follow` the file. Being edited a second
    time → try deleting it. *Added* by a fix for another note → prime suspect.
    (T24, T25)
17. **Finish the cut.** Re-read every edited sentence whole. Grep the deleted
    phrase and any retired field across templates, FIELDS docs, samples and the
    registry. Check no test asserted the words you changed. (T26, T28)
18. **Floor pass.** Re-run the assurance grep; confirm every explicit negation,
    both halves of every boundary, the "licensed CPA" person-form and every
    `[CONFIRM:]` survived. (T22, T23)
19. **Render and read it** — on the page, not in the source. T13's contradiction
    and the officer-compensation line on an individual's estimate were both
    invisible in the template.
20. **Sweep the set.** Apply 1–19 to every template sharing the phrase, then
    re-render the samples. (T27)

Then run `AUTHORING-CONTRACT.md §8` — the mechanical check for stylesheet, print, fields and
counts. This test is about words; §8 is about the artifact.

---

# What this file replaces

`AUTHORING-CONTRACT.md` **§5 · Voice** stays in force except as below. Two of its
rules produced the drafts the firm rejected. *(Recorded here, not edited there — that edit is
a human's to make.)*

1. **"Give the reason with the rule. A rule with a reason gets followed."** —
   **superseded by T9.** This is the licence under which every deleted
   because-tail was written. Replace with: *Give the rule. Attach a reason only
   when the consequence is the reader's and changes what they do.*

2. **Both worked examples in §5's "Do" list were deleted by the firm on 26
   August**, so they are now the wrong model to copy. *"Nothing begins until the
   signed engagement letter is back with us."* → *"just delete this they dont
   send it to us … and i dont care to say that again"* (T1, T10). *"We cannot
   tell a missing document from one that does not exist."* → *"100% what i mean
   by ai-coded bullshit"* (T8). Replace both with his own copy — *"If this letter
   states your understanding, sign below."* — or with any sentence from the
   positive model in §0, all of which have survived four rounds untouched.

3. **§5's "Restate scope or fees in a document that isn't the one that owns
   them"** — **sharpened by T1 and T21.** As written it bans restating but
   permits pointing, and pure pointer sentences are exactly what he deleted.
   Pointing *is* restating unless the sentence carries a fact of its own.

4. **§5's "Reference other clauses by name, never by number"** — **confirmed**:
   *"delete Section 02 sets out how that works and who does what."*

5. **§6's scope-boundary table** — **unchanged.** T1 is that table applied at
   sentence level rather than at document level.

6. **§8's self-check** — **unchanged, and now runs second.** Cutting test first.
   §8 has no step that renders a document and reads it; step 19 above is that
   step, and it is where two live bugs were found.

7. **§5's compliance rules and §9's "what needs a human"** — **untouched and
   supreme.** T23 restates them so no concision tenet reads as authorizing a cut
   there.
