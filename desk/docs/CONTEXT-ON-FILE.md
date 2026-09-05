# What the file already says — the input a desk did not have

**Measured, 5 September 2026.** Of the 43 questions the close produced,
**13 reach a desk that now expects a fact on file** — the client's trade, or
whose return it is. Before this, every one of those 13 arrived as a question and
nothing else, and the desk had no way to tell a general contractor from a
hairstylist.

| | |
|---|---|
| questions in the close | **43** |
| reach no desk at all (correctly — they have other owners) | 20 |
| reach a desk that now expects a fact on file | **13** |
| of those, expecting `trade` | 8 |
| of those, expecting `taxpayer` | 5 |

The 13: Q5, Q7, Q8, Q9, Q12, Q13, Q18, Q25, Q29, Q31, Q33, Q34, Q35.

## Where it came from

The firm, holding `personal-or-business/POS1` rather than ratifying it:

> *"I think that this makes sense, but I want to make sure that we understand
> each other when I say that there should be some inference in the sense that the
> Accountant should've already recorded and known what sort of business we're
> dealing with. That's something we find out during the engagement and if they're
> missing that piece of information, something was just missing from the file so
> it makes it a lot easier for me to look at a Home Depot charge from a general
> contractor and think that it's a business expense versus looking at a Home
> Depot charge from a hairstylist."*

And, holding `rewards/POS1`:

> *"this makes me think that we should probably be specifying. Hey this is the
> individual desk. This is the business desk."*

Both are the same missing input, and neither is a new desk.

## The shape

Three declarations, each in the place that owns it:

1. **The desk says what it expects.** `SUBJECTS.md` gains a `Records:` line —
   `Records: trade`. It is the desk's vocabulary, not the engine's.
2. **The position says what it cannot do without.** `POSITIONS.md` gains a
   `Needs:` line on the entries that turn on it. Two positions declare one; the
   other seventeen declare nothing and behave exactly as they did.
3. **The caller passes what it has.** `ask.consult(question, context=...)`, a
   mapping of the names the desk declared.

Unmet, the gate refuses **`context_not_on_file`** — a third kind of missing
thing. `facts_not_established` is answered by asking the client;
`document_not_requested` by obtaining a document; this one by neither, because
the fact should already be in our own engagement record. Sending it to the client
is the wrong queue, and the client is not the one who failed to write down that
they are a contractor.

**The desk is told; it never works it out.** A desk that inferred the trade from
the vendor would be running exactly the reasoning `POS1` exists to forbid — and
it would be right often enough to be trusted, which is worse.

**The brief prints the gap by name.** `trade: NOT ON FILE — do not infer it, and
do not answer from a rule that needs it`. Printing only what is on file leaves an
answerer to assume the rest was not needed.

## What the repository refused, and it was right

The first draft put `trade`, `taxpayer` and `engagement` on a dataclass in
`record.py`. `test_no_closed_vocabulary_speaks_one_trade` went red naming two of
them. Every desk shares that layer, and how much the second desk forces onto it
is the whole measurement of the split — so a fact vocabulary there would have
made every desk speak accounting, permanently, for a convenience.

The rewrite is better than the draft: `Context` carries a mapping, the words are
each desk's own, and a desk in another trade brings its own without touching a
shared file. **The guard did not slow the change down; it produced the design.**

## Two things this does NOT do, and both are the firm's to decide

**1 · A position cannot yet be a default with a per-client override.** Holding
`capitalization/POS1`, the firm: *"This is the kind of policy that gets enacted
because it makes sense and only enacted when we don't have another Answer for
instance it's possible for a particular client we have to be needed treating
differently."*

Every position today is unconditional. A per-client override needs a store keyed
by client, which is the first client-keyed data this plugin would hold — and the
plugin holds none by design.

| | |
|---|---|
| **Keep positions unconditional** | The desk stays free of client data. The override lives in the engagement record outside the desk, and the caller passes the answer in as context — which is the mechanism just built. |
| **Give positions a per-client exception table** | One place to look. It puts client-keyed data inside the plugin, and the PII rule then applies to a component that had been exempt from it. |

**Recommendation: keep positions unconditional** and express an override as a
recorded fact the caller passes, exactly like `trade`. It needs no new store, and
the desk still cannot see who the client is.

**2 · There is no "defer to the IRS when we have no position".** Holding
`rewards/POS1`: *"if we don't have an opinion and have a good reason to form one,
maybe we just use a safe Harbor Rule which, in this case would be deferring to
whatever the IRS says."*

Today a non-binding source refuses `authority_permits_choice` — the rule leaves a
choice and the firm makes it once. Their fallback would let a secondary IRS
source answer instead.

| | |
|---|---|
| **Leave it** | Nothing is served on somebody's reading of the rule. The firm keeps getting asked the same question until they answer it once, which is the complaint. |
| **Let a secondary IRS source answer where no primary rule and no position reaches** | Far fewer escalations. It also means the desk starts serving IRS guidance as though it were the rule — and on the capitalisation threshold the regulation says **$500** while the guidance says **$2,500**, so the two really do differ. |

**Recommendation: a middle one — serve it, and say what it is.** Where only a
secondary source reaches, answer from it and mark the answer as guidance rather
than rule, so the reader sees which they are relying on. That is a change to what
`Served` carries, not a hole in the gate. **Not built: it needs their yes first.**

---

# Found while checking the local-model constraint: a desk that fails completely publishes as a careful one

The firm, deferring the desk-size decision on 5 September 2026: *"their
development should still work on a local model, even if we can't technically run
it in the sense that none of the script or prompting or anything would mess it
up."* Checking that turned up two defects in the harness, neither of which needed
a model running to find.

## 1 · `Leak` was a plain exception, so four desks scored as careful ones

`forge_adapter` builds the prompt inside `ask()`, and `scoreboard.run` catches
anything `ask` raises and records it as an escalation with reason
`model_gave_up` — which is rule 9 working exactly as designed, for the failure it
was written for. `Leak` is not that failure. It is ours: the harness refusing to
build a prompt because the stored authority carries the answer.

**Reproduced with no model running at all**, on the rewards desk:

```
problems: 19
recorded as the model giving up: 19
outcomes: {'ESCALATED': 19}
```

**Escalation is a success on this scoreboard.** A desk whose every single prompt
the harness refused to build would have published as a perfectly careful one.

| desk | problems the harness cannot prompt |
|---|---|
| rewards-and-information-returns | **19 of 19** |
| meals-and-entertainment | 6 of 16 |
| vehicle-expense | 5 of 15 |
| personal-or-business | 4 of 12 |
| | **34 of 98** |

**Nothing published was wrong, and that is luck rather than a control.** Both
Forge runs were on `fixed-assets` and `cash-and-bank`, the two desks that do not
leak. `Leak` is now a `HarnessError`, which `scoreboard.run` re-raises — the
class was already there, written on this same file after the identical bug turned
sixteen refusals into give-ups.

**The 34 leaks are a separate, real finding and are NOT fixed here.** They mean
the stored authority for those desks carries the conclusions its own problems
turn on. That is a corpus question, and quietly loosening the leak check to get a
number would be the worst available move.

## 2 · The full-text prompt could never have run on the box it was written for

`ollama()`'s docstring has said since it was written that a request over the
window *"does not error — it silently drops the front of the prompt"*, and the
front of this prompt is the instruction to cite. Nothing checked it.

An 8,192-token window leaves **7,616** for a prompt once 512 is reserved for the
reply and a little for overhead — and the reply comes *out* of the window, which
the sizing did not account for either.

| desk | `--corpus index` | `--corpus text` |
|---|---|---|
| capitalization-and-de-minimis | 4,020 | **8,978** |
| cash-and-bank | 3,460 | **15,367** |
| fixed-assets | 6,171 | leaks before it can be measured |

**The index shape fits all seven desks. The full-text shape fits none**, and it
was reachable from the command line. `check_fits` now runs at the API choke
point — LOCAL-LLM-PATTERN rule 6, the same reason the citation rule lives in
`engine.serve` rather than in a prompt — and raises `PromptTooLong`, naming the
estimate, the room, and the three things that would fix it.

The token figures are **estimates and are called that everywhere**: there is no
tokeniser here, so the ratio is deliberately pessimistic (3.2 characters to the
token, where English prose is nearer 4) because under-counting is the one
direction that would let a prompt be cut anyway.

## The 34 leaks, diagnosed — two causes, and only one of them is the record's fault

Not one number: **two separate defects that happen to share a symptom.**

### 19 of them are three stored passages, all on one desk

A single worked example in the corpus is a **desk-wide outage**, because the leak
check sweeps every problem for every prompt. Three passages therefore cost all
nineteen scores on `rewards-and-information-returns`.

| passage | what it is | what it costs |
|---|---|---|
| `IRS Pub. 525 (2025), "Cash rebates"` | the rule **and** Example 36 in one passage — and Example 36 *is* problem RW2 | the rule stands alone; trimming at `Example 36.` leaves it verbatim |
| `26 CFR 1.6041-1(a)(1)(v), Example 1` | an example end to end; the citation says so | it is problems IR4's fact pattern |
| `26 CFR 1.6041-1(a)(1)(v), Example 2` | the same | IR5's |

**The obvious fix is not free, which is why it is recorded rather than made.**
Both regulation examples name the paragraph they apply — *"Under paragraph
(a)(1)(iv) of this section, A, as payor, is not required to file"* — and the desk
already holds `§ 1.6041-1(a)(1)(iv)` as a rule. So IR4 and IR5 should cite the
rule and the examples should leave the corpus. **But the firm ratified POS2 on
that same paragraph this morning.** A ratified position is served verbatim and
`_check` refuses an answer that restates it, so the moment those problems cite
it, their own recorded answers refuse as `contradicts_ratified_position` unless
the two wordings are reconciled:

> **POS2, the firm's:** *no Form 1099-NEC for a payment settled by card or
> through a third party payment network; track the rest against $2,000 per payee
> per calendar year*
>
> **IR4 and IR5, the regulation's:** *the payor is not required to file an
> information return under section 6041*

They say the same thing in different words, and the engine is exact on purpose —
that exactness is what stops a model handing back the firm's position with the
conclusion reversed. **Reconciling them is the firm's wording to choose, not
mine**, so nothing was changed.

### 15 of them are the leak check being too strict, and the record is fine

`'not deductible' appears in the prompt outside the list of admissible
conclusions` — on 15 problems across meals, personal-or-business and vehicle.

But § 1.274-11(a) *does* say entertainment is not deductible. **That is the rule
stating its own outcome, which is what a rule is for.** A model that reads it and
concludes "not deductible" has reasoned correctly from authority; that is the
desk working, not the answer key leaking.

The check cannot tell those apart today, and it should not simply be relaxed: an
admissible conclusion appearing verbatim does let a model pattern-match without
reading. **Proposed, not done:** distinguish the conclusion appearing *inside a
quoted passage* — where it is the rule's own words — from it appearing anywhere
else in the prompt, which is where a leak would actually live.

**Nothing here loosens a check to obtain a number.** The three passages and the
fifteen strict refusals are recorded in `tests/test_corpus_is_rules.py`, which
goes red if a fourth appears and equally red when one is fixed and left on the
list.
