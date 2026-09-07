# Which body of authority governs a question — 7 September 2026, evening

**Found by the firm, testing the thing rather than reading about it.** They asked
four questions of the installed desks. Three answered or refused correctly. The
fourth found a defect nobody building it would have found.

> *how do i know if a lease should be booked as an asset*

Every desk refused `authority_absent` — 89 provisions from three sources put
against the question, none reaching it. So the searcher ran, and came back with
**four passages off irs.gov that tied out**: re-fetched from the publisher,
matched character for character, one occurrence each. It recommended admitting
them.

Every check passed. All four are about the **tax** question — whether a lease is
deducted as rent or capitalised as a conditional sale. The firm asked the **book**
question, which is US GAAP. The firm:

> *"you don't check the IRS website for coding tips"*

**Nothing in the machinery could tell.** A desk knew its subjects and its sources
and never knew which **body of authority** it spoke for, so a competent search in
the wrong universe was indistinguishable from a competent search in the right
one. And `authority_absent` told the reader *"we do not have the rule yet, go and
find it"* when the truthful refusal was *"this is not a tax question."*

---

## What was built, and why it is one file

`DOMAINS.md` at the desk root, with `domains.py` reading it. **Not a line on each
desk**, because the firm named the thing to avoid:

> *"i'm trying to avoid a million desk creations which means i always don't want
> to have to personally find every possible source"*

**Tier is a property of the publisher, not a finding about a source.** The body
with authority over a domain publishing its own text is primary; that body
explaining itself is secondary; everyone else is tertiary however good they are.
Written once, applied by the engine — so a host nobody has seen before gets a
tier without an interview. That is what replaces admitting sources one at a time.

The firm still decides two things, and neither is a source list: which domains
the practice answers in, and what the firm does where the authority permits a
choice.

**It refuses rather than defaults, in both directions.** A question matching no
domain classifies to `None` rather than to a guess. A host in no domain's list is
**tertiary everywhere** — it can help you find the authority and can never be the
authority.

---

## The straddle, which is the half that was easy to get wrong

A lease genuinely **is** taxed and **is** booked. `classify` orders by how many
words fired, and on the firm's question `us-gaap` beat `federal-tax` **2–1** — a
weak signal doing a strong job. Reword the question, drop one word, and the same
question goes to the tax desk and gets the tax half answered confidently: the
original defect wearing different clothes.

So a straddle is **surfaced, not resolved**. And the refusal now says where the
passage *would* have been competent, because those four IRS passages are sound
law on the tax half — refusing them flat throws that away and reports a searched
question as nothing-found, which is a second wrong answer.

---

## Two defects the work found in itself

**A wrapped field was silently truncated.** `**Body:**` wraps in the real map and
the first parser read to the end of its first *line*, so the refusal printed *"the
Financial Accounting Standards Board, through the Accounting"* — naming a body
that does not exist. Only in prose a person reads, which is why nothing failed.

**A test proved itself.** The end-to-end test passed an empty `proposals` list
and asserted nothing was proposed — true of any code, gate or no gate, and it
stayed green when the gate was mutated out. It now feeds a real proposal through
with the fetch replaced so the tie-out **succeeds**, so what refuses it is the
domain and not a failed fetch; and a second test removes the classification and
requires the same input to be PROPOSED, so it cannot pass for the wrong reason.

---

## What this does not do yet

**The lookup ladder is still not walked.** `record.ACCESS` has been
`public_fetch → headless_browser → signed_in_browser → human_only` since the
beginning; all 36 declared sources sit on rung one and nothing performs a
headless or signed-in fetch. The firm's design — *"a claude code session that can
look stuff up... you don't need to store stuff if you look it up, you can look it
up again"* — is the next piece, and it is what makes a licensed primary like ASC
answerable at all.

**Storage was the wrong axis, and this was recorded wrong before it was recorded
right.** A session argued that FASB being unstorable made GAAP unreachable. The
firm: *"storage does not matter if we can search for it in the browser... if you
are allowed to store, all the better."* Reading and keeping are different
questions; `DOMAINS.md` settles that ASC **governs**, and `access`/`may_store` on
a source settle what may be done with it.
