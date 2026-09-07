# Where a client's facts actually live

**This exists because a session invented a container.** On 7 September 2026 the
desks gained a reader for an "engagement file" — a Markdown file, hand-written,
kept wherever the caller liked. The firm:

> *"hold on we dont have a method for creating an engagement file - also we
> wouldn't have an engagement file so much as the occam processer (which is our
> accounting software) has workbooks for clients. taxes may have engagement
> folders and such. it shouldn't ask for what doesn't exist, or if it does it
> should have a way to rectify and understand what the process is"*

They are right. **Three real containers exist and none of them was checked
before a fourth was built.** This file is what was established afterwards, so
the next session starts from the record rather than from an assumption.

---

## The three real containers

| Container | What it is | Where | Readable from this repo? |
|---|---|---|---|
| **Occam's workbook** | one Excel workbook per client — the bookkeeping **source of record**, driven through an HTTP API | its own repository, on the Forge, over the tailnet | **No.** Separate repo, not attached |
| **The engagement folder** | one folder per engagement, ref `YYYY-NNNN`, JSON | `client-documents/engagements/`, and in OneDrive | Yes |
| **The interview** | what we were told, authoritative *until proven wrong* (`CLAUDE.md`) | `satc_system` | Yes |

---

## The three facts the desks declare, checked against those

| Fact | `Records:` on | Verdict, 7 September 2026 |
|---|---|---|
| `taxpayer` | rewards-and-information-returns | **Already recorded.** The engagement record carries `EntityType` — *"an Ohio limited liability company taxed as an S corporation"* — and `_return_type: s_corp`. The desk is asking for something the firm records under another name. This is a **mapping**, not a new field |
| `trade` | personal-or-business | **Not in the document store.** No field on the engagement record holds what the business does. Occam knows it, or the interview does — unverified, because Occam is not readable from here |
| `capitalization_rule` | capitalization-and-de-minimis | **Nowhere.** No container holds it. This is precisely `no_field_for_this_fact`, and the field-request mechanism the firm approved the same afternoon is what it is for |

---

## What the invented file got wrong beyond existing

1. **Its ref can never join.** `desk/engagements.py` accepts any alphanumeric ref
   (`alpha-2026`). The firm's ref is `YYYY-NNNN` and it is **byte-compared across
   every document**, because it is the join key the whole document set depends
   on. A desk answer keyed to the invented ref could never be tied back to the
   engagement it was about.
2. **It took the name.** `client-documents/engagements.py` is the real module.
3. **Its PII guard is for the wrong threat.** It refuses TIN-shaped *values*,
   which is right for a file somebody types. The real engagement record holds
   `ClientFullName`, `ClientAddress1`, `SignerName`. **An adapter over a real
   container must read one named fact and never the record** — a constraint that
   never came up while the container was imaginary.

---

## The simplest thing, which is what this became

The firm, an hour after the correction above:

> *"what's the simplest thing? like the desk can simply ask for info, if we
> don't have it and if we do not (and it the answer can't be tied to some data
> point) it's a hole in what we need to know"*

**That is the mechanism the engine already had, and the file was the
complication.** `engagements.py` and `tools/engagement.py` are deleted. The
caller passes what it already has; there is nothing to create.

Two states, told apart since 6 September:

| | Meaning | Fixed by |
|---|---|---|
| `context_not_on_file` | there IS somewhere to record it, and nobody has | a preparer |
| `no_field_for_this_fact` | there is **nowhere** to record it, anywhere | the firm deciding the fact exists |

`tools/holes.py` reads them out, holes first, never summed. **As of 7 September:
no holes, and five gaps** — `capitalization_rule` twice, `trade` once,
`taxpayer` twice, each named alongside the position that asked for it.

**That five was reported as a zero for several hours.** The report globbed
`unfiled/` — the queue a human files at close — and refusals land in two other
places: each desk's own `unsupported/`, written by `ask.answer` as it refuses,
and the latest run's `served.json`. It printed *"the mechanism is live and has
not fired"*, which was a claim about the mechanism made from a third of the
evidence. It now names what it read, and the run writer keeps the fact and the
position that wanted it instead of leaving them to be parsed back out of a
sentence.

**No adapter was built, and none is needed to start.** The sections below are
what an adapter would have to be true of IF one is ever wanted, kept because the
constraints were established by measurement and would otherwise be rediscovered.

---

## What has to be true of any adapter

- **It reads. It never becomes a store.** A fourth place a client fact lives is
  the thing this file exists to stop.
- **One named fact at a time**, never the record — see the PII note above.
- **The ref is the firm's ref**, so an answer can be joined to an engagement.
- **It does not guess a schema.** Occam is a separate repository. Writing an
  adapter over field names nobody confirmed would be the same error in a new
  costume, and the whole point of `desk` is that it refuses rather than guesses.

## What a refusal has to say

The firm's second sentence is the harder half: *"it shouldn't ask for what
doesn't exist, or if it does it should have a way to rectify and understand what
the process is."*

Today `context_not_on_file` says **"the file does not record this"** — a refusal
naming a container that may not exist. It should name **which** container holds
that fact and **what to do**:

- the fact belongs in Occam's workbook for this client, and it is blank there;
- the fact belongs on the engagement record, and this engagement has not been
  through the step that sets it;
- **nothing records this anywhere** — which is not `context_not_on_file` at all,
  it is `no_field_for_this_fact`, and the engine already tells those two apart.

That last distinction is why the refusal vocabulary is closed and why the two
reasons were kept separate: one is a gap in a record, the other is a gap in the
software. What is missing is the pointer, not the distinction.

---

## The finding this file was almost the wrong answer to

**`capitalization_rule` is declared and nothing implements it — and that is not
a mistake to undo, it is a decision that was recorded and never carried out.**

On the fifth docket the firm answered `dec-cap-field`: **"Add the field"**,
closing a finding they had raised themselves — *"what if this mattered only
sometimes and we never even made a field for it."* What got added was the
`Records:` line on the capitalisation desk. **The field itself was never built
anywhere**: not on the engagement record, not in the document registry, not in
`satc_system`'s intake or models — checked, 7 September evening.

So the desk now says *there is somewhere to put this and this client's file has
not got one*, and there is nowhere. Two of the close's questions refuse that way.

**A session tried to fix this by removing the declaration** so the engine would
fire `no_field_for_this_fact` and the hole would surface. That was wrong and was
reverted within minutes: the line is the firm's answer to a question they were
asked, and deleting it would erase their decision rather than surface the gap.
The tests carried the history that caught it — three of them state, in as many
words, that the refusal changed *because* the firm said add the field.

**What is actually open:** the firm decided a field should exist. Nothing built
it. That is a piece of work, not a relabelling, and it is the largest thing
standing between the capitalisation desk and answering the two questions it
refuses.

---

## Still unknown, and not to be guessed

- Occam's workbook schema, and which sheet or field holds the client's trade.
- Whether the interview records the trade, and under what name.
- Whether `EntityType` prose or `_return_type` is the right thing to hand a desk
  as `taxpayer` — the desk's position is worded against a filing status, and
  matching prose to it has not been checked.
