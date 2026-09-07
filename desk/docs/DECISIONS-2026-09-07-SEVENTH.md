# The seventh docket — four matters, four answers, and the goal that follows

Published as `artifact/1750afce`. Three were answered on the form at **15:49 UTC
on 7 September 2026**; the fourth was answered in conversation. Every quotation
is verbatim.

## `dec-desk-asks-for-code` — **A field, and only a field**

Answered in the conversation rather than on the form: *"i'll take your
recommendation"*, against a recommendation reading *a field, and only a field*.

The line the firm drew: a desk may cause **somewhere to write a fact** to be
built, and nothing else. A step in the close, a change to a workflow, or
anything a client reads comes to them as a matter.

Built the same hour. `Refusal` now carries the fact it turned on and the
position that asked for it; `unsupported.py` has a sixth resolution — *the rule
is clear and there is NOWHERE to write the answer → build the field, naming the
position that asked*. Proved against the real capitalisation position:
`needs_field: capitalization_rule`, `asked_by: POS1`. Four tests, and only the
`no_field_for_this_fact` refusal becomes a field request.

## `dec-admit-publishers` — **Admit eCFR only**

No note. Cornell declined, which was the recommendation: eCFR is the government
publishing its own regulation, Cornell a faithful copy that earns nothing eCFR
does not already give.

**It answered a question the desk could not answer ninety minutes earlier.**
§ 1.162-3 became S2 on fixed-assets, with both paragraphs stored and tied out.
Q18 — *does a hardware-store purchase ever become an asset?* — is served on
§ 1.162-3(c)(1)(i). Six served became seven.

## `dec-register-standing` — **Drop it — the card was the problem**

No note. Nothing was built, and that is the whole answer: no word-count rule was
invented for the positions. The docket card fix stands on its own.

## `dec-merge-305` — **Merge it**

Merged as `975c77a`, nine checks green.

---

## What the firm was looking at when they said they were confused

At about 16:30 they wrote: *"i am generally confused i have filled this docket
out"*. They had. The page had been **republished over its own answered
questions** — a new goal at the top and the same four cards below it, three
showing their answers and the fourth still showing as open, because it had been
answered in conversation and the form never heard.

The generator could not produce the sentence the docket skill asks for. Every
heading, the browser tab and the filter bar were phrased for a page with matters
on it: at zero the tab read *Docket · No Open*, the headline *No things waiting
on you*, and the bar offered *All 0 / Positions 0 / Other 0* above an empty list.

Fixed in `edea44e`. `ANSWERED` holds a matter after it is answered, with the
firm's own words and what the answer caused; `items()` refuses to build a page
carrying a key in both lists; the empty page says **Nothing is waiting on you**
and **Nothing needs deciding** in those words. Both guards mutation-checked.

## The goal, set by the firm and shaped here

*"current goal is to get this piloted through the close out"*, 7 September 2026.

**Ends when** one engagement's close questions have been put to the desks, with a
written record of every answer served, every refusal and what it asked for, and
the questions the desks never saw.

**It refuses** building more desk machinery mid-pilot; inventing a client — there
is no synthetic engagement, and with no real one this is blocked and says so
rather than producing a demonstration; and client PII reaching a desk.

### The first blocker, and it was not a client

Three desks declare a fact they need on file — `trade`, `taxpayer`,
`capitalization_rule`. `engine.serve()` takes all three. **Nothing produced
them**: the only thing carrying facts was a worked example's own `On file` line,
which is a test fixture. Five of the eighteen close answers refused with
`context_not_on_file` against a file that did not exist.

Cleared in `a601c09`. `engagements.py` reads one; `tools/engagement.py new`
prints a blank carrying every fact the desks declare, generated rather than kept
as a template; `check` prints what a file holds **and what it does not**, by name,
with the desk that will refuse without each one. The file may not live inside the
plugin and `load` refuses one that does.

**Measured:** handed a file recording the three facts, all five of those refusals
are served — 7 of 19 becomes 12. The file that proved it is a labelled stand-in
and is not a client; inventing one is what this goal refuses.

**What is left is the client.** The pilot is blocked on a real engagement, and
says so rather than producing a demonstration.
