# Tenets — how to build

**How this file works.** Each tenet is a rule, then the incidents that proved
it. Evidence **appends**; it is never rewritten. Every entry names the project,
the date, and a citation you can go and read — a commit, a quotation, a comment,
or a test docstring.

**A rule with nothing under it does not belong in this file.** The test each one
had to pass: *if this rule had been in force, would that bug have shipped?*

Identifiers match `SATC/docs/SOFTWARE-TENETS.md` — `S31` here is `S31` there —
so every citation already written across that repository still resolves after
the rest are migrated.

**Evidence count is reported, not implied.** A tenet carrying one incident is a
local observation. One carrying three, from three projects, is a law. The
difference should be visible without reading.

---

## S31 · A claim and the behaviour it describes are two things. Build the third: something that compares them.

**Evidence: 2** *(SATC ×2)*

### SATC · 2026-09-02 · `payments.py`, and the grep that found nothing

`deactivate()` was written with a comment naming it the one guard against this
feature taking the wrong amount: *"a link outliving its figure is the one way
this feature takes the wrong amount. Re-price an engagement from $645 to $745
and the old link will still cheerfully collect $645."*

Nothing ever compared the two numbers. `record_settlement` wrote
`settled_amount` onto every invoice and `grep -rn settled_amount` returned
exactly one line — the write. A client could pay $645 against a $745 bill, the
bill would be marked settled, and the e-file gate that every engagement letter
promises stays shut until the invoice is paid would open.

Twenty-four tests covered that module. None of them compared the claim to the
behaviour, because nothing in the code did either.

### SATC · 2026-09-03 · a refusal message that contradicted itself

A 401 handler named a token from the other account as *"the commonest cause"*.
Run against Sandbox it said the token was probably a Production one; the same
token against Production said it was probably a Sandbox one. Both cannot be
true, and between them the two runs had already ruled out the thing each was
asserting.

The message stated a hypothesis it had never checked. The fix was not a better
hypothesis — it was to go and make the observation, which was one read-only
request away and which nothing had gone to make.

---

## The rest

Thirty-four more are waiting in `SATC/docs/SOFTWARE-TENETS.md`, already curated
and already carrying their evidence. They come across in slice 8, **after** the
format has been proved by this one — because migrating thirty-five entries into
a shape nothing has exercised is how you end up rewriting the shape with
thirty-five entries in it.
