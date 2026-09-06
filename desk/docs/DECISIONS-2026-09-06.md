# The fourth docket — thirteen matters, thirteen answers

Published as `artifact/d9339c39` on 6 September 2026 and filled in the same day.
**This file is where the firm's own words live.** `positions.py` records why:

> a conviction in `canon` keeps the quotation, because its provenance IS its
> authority. A POSITION IS CLEANED UP … and the firm's own words for it live in
> the log, where provenance belongs.

So every quotation below is verbatim from the form, and no position in
`desks/*/positions/` repeats it.

**Thirteen matters. Twelve carry a choice; one does not, deliberately** — the
court-hosts question came back with a note and no button, and it is recorded as
still open rather than read into.

---

## The four positions

| | Matter | Answer | Note they left |
|---|---|---|---|
| 1 | `rewards/POS1` — a card reward reduces what was paid | **Ratify it** | — |
| 2 | `capitalization/POS1` — make the safe-harbour election every year | **Not yet** | yes |
| 3 | `capitalization/POS2` — the threshold is $2,500 / $5,000 | **Not yet** | yes |
| 4 | `personal-or-business/POS1` — the vendor is evidence, not the test | **Not yet** | yes |

### 1 · Ratified, and against the recommendation

The docket recommended ratifying it **narrowed**, to the sentence that survives
*Anikeev*. The firm ratified it as drafted, unamended, with no note. The wording
they ratified is the wording that is served; the narrowing argument survives as
commentary on the position, not as the position.

**No score moved, and that was checked rather than assumed.** No problem on the
desk is keyed to `PLR 201027015, LAW AND ANALYSIS`; RW7 is keyed to `Ruling
request (1)`, a different passage of the same ruling.

### 2, 3 and 4 · Held, and all three for one reason

> **`capitalization/POS1`:** *"This needs to ensure that there is no already
> standing rule for that client in particular. The desk should ask that follow
> up if it is not clear, right?"*

> **`capitalization/POS2`:** *"Same as above the other safe harbor thing. This is
> inherently fine but we shouldn't ignore client level rules set with judgment
> with the desk answering broadly. This is otherwise fine"*

> **`personal-or-business/POS1`:** *"I feel as tho the desk can be helpful too.
> Like if it works this way already good but like with the safe harbor stuff it
> can ask a follow up and if the follow up has no answer we know there's a legit
> hole to fix because the accountant or firm never assigned it up front. This is
> also a way to check for bugs or defects while agents perform real work. What if
> this mattered only sometimes and we never even made a field for it"*

**What was built.** `Unless:` — a position that is the firm's default and holds
unless the file says this client is treated differently. Three answers rather
than two (`Context.standing_rule` → ABSENT / NONE / RECORDED), because "nothing
on file" and "on file, and this client is not special" are opposite facts that a
`dict.get` cannot tell apart.

**The last sentence is the one that shaped it.** `Unless:` may name a fact the
desk does not record, where `Needs:` may not — and that asymmetry is the feature.
A mechanism that can only ask about fields somebody already thought to create can
never discover the field nobody thought to create. Where there is no field, the
refusal is `no_field_for_this_fact`, and it says the gap is in what the firm
decided to write down rather than in what the client was asked.

**Answering their two questions directly.**

*"The desk should ask that follow up if it is not clear, right?"* — It does now,
and the question is a sentence rather than a code. Both capitalization positions
carry `Unless: capitalization_rule`, that desk records nothing, so the follow-up
is unanswerable by construction and lands in `unsupported/` as an `Asked:` line.

*"Like if it works this way already good"* — For `personal-or-business/POS1` it
already did. `Needs: trade` has refused rather than reasoning from the vendor
since 5 September. What it could not do was say the question out loud.

**All three are still proposals.** The mechanism they asked for exists and is
demonstrated on their own positions; ratifying is theirs.

---

## The nine other matters

### 5 · `dec-ir45-wording` — **Reword POS2**

> *"How would this work in the process of answering questions from the agents to
> the desk? Interesting"*

**The answer to that question, plainly.** When an agent asks the desk about a
payment settled by card, the engine resolves the citation and finds POS2 — and a
ratified position OUTRANKS the stored regulation on the same citation. So what
comes back is the firm's own sentence, verbatim, not the model's restatement of
it. If the model's conclusion disagrees, the answer is refused as
`contradicts_ratified_position`. **The position is both the answer and the
check**, which is why its wording had to be the regulation's own sentence before
the regulation's own worked examples could be pointed at it.

The $2,000 rule moved to **POS3**, on `§ 1.6050W-1(c)(3)` — the rule it actually
turns on — and is a **proposal**, because the words are theirs and the citation
is not. It is matter 1 on the next docket.

**"Second sentence" could not be honoured literally.** A two-sentence position
and a one-sentence answer key cannot both be exact. The option they chose said
what it was for — the desk stops refusing itself and the scores come back — and
that is what was delivered: **0 of 19 promptable → 19 of 19.**

### 6 · `dec-prove` — **Build it**

Built as `proving.py`. Off by default, and off means off: it takes a transport
rather than a flag, so nothing reaches the network by accident.

### 7 · `dec-6041-sources` — **Split into four**

Done, and every URL verified live. The § 6041 page carries none of the other
three — longest matching prefix three characters.

### 8 · `dec-583-quotation` — **Mark the omission**

Done, with `[...]`, and the mark is checked rather than excused: every segment
must appear in the live document in order.

### 9 · `dec-cd-fix` — **Add the line**

Merged as [#296](https://github.com/AJSethuraman/SATC/pull/296). `main` is green.
The client-documents job ran 8m13s and passed, against 36s to a collection error
before it.

### 10 · `dec-override` — **Keep unconditional**

**Nothing to build, and that is the answer.** Positions stay unconditional; an
override arrives as a recorded fact the caller passes in — the same mechanism as
the client's trade. The desk still holds no client data and the PII rule still
does not reach it.

This is what made matters 2–4 buildable at all: `Unless:` does not put a
per-client exception table inside the plugin, it asks the caller whether the file
holds one.

### 11 · `dec-guidance` — **Serve it, marked**

Where no rule and no position reaches, guidance answers with `binding=False` and
a caveat naming the tier. Escalations across all seven desks: **24 → 6**, and
every one of the six is a desk that holds the rule.

**A correction to the docket's own wording.** Its recommendation said this
"changes what a served answer carries, not what the gate lets through". The
second half is loose — it does change what the gate lets through. What it does
not change is the citation requirement: nothing uncited is served either way.

### 12 · `dec-merge-275` — **Merge it**

### 13 · `dec-courts-again` — **no choice recorded, and it stays open**

> *"I'll do this when home. Also look into Lexis nexis. A lawyer said this is how
> they research precedent"*

**Nothing was read into the silence.** The matter asked which half of a
contradiction they meant — the button they pressed last time (keep the five court
hosts closed) or the words they wrote beside it (open everything we can use).
This time there is a note and no button, which is not an answer to that question,
and recording one would be inventing it.

**Carried forward, unchanged, plus one thing to look at:** LexisNexis. Worth
noting that it is a different shape from every source this record holds — a
licensed commercial database, so `access` and `may_store` would both need
deciding before a single passage could be stored, and the `human_only` path
(where a position IS the desk's entire knowledge of a source) may be the only
lawful one. That is research, not a decision, and it is on the next docket as
such.

---

## What is still open after all thirteen

1. **POS3** on the rewards desk — the $2,000 rule on its new citation. Proposed.
2. **The three held positions** — now answerable, still theirs to ratify.
3. **`dec-courts-again`** — carried, with LexisNexis added to it.
4. **`capitalization_rule` as a field** — the follow-up mechanism can now ask the
   question and the record has nowhere to put the answer. That is the finding
   working, and closing it is a decision about what the firm records.
