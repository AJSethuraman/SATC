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
