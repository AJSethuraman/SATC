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

## Still unknown, and not to be guessed

- Occam's workbook schema, and which sheet or field holds the client's trade.
- Whether the interview records the trade, and under what name.
- Whether `EntityType` prose or `_return_type` is the right thing to hand a desk
  as `taxpayer` — the desk's position is worded against a filing status, and
  matching prose to it has not been checked.
