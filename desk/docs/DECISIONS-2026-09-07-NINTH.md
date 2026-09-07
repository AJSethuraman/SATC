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

---

## The trap the Forge found, and why 0.7.0 did not catch it

**The firm sent the plugin to a session on the Forge to be tested as a user,
and it came back with the thing nobody building it had found.**

Asked *"how do i know if a lease should be booked as an asset"*, the tester
played an agent reaching for the nearest paragraph and proposed an answer citing
**IRS Pub. 463 (2025), "Leasing a Car"**. It was **SERVED**, `checked_subject:
True`. The entire cited passage:

> *"If you lease a car, truck, or van that you use in your business, you can use
> the standard mileage rate or actual expenses to figure your deductible
> expense. This section explains how to figure actual expenses for a leased car,
> truck, or van."*

Two sentences about figuring a deduction. Nothing about the balance sheet,
nothing about recognition. The question is a US GAAP recognition question and
the engine served a confident *"no"* the paragraph does not contain — and
directionally the **expensive** error: expense the lease, omit the right-of-use
asset and the lease liability.

**Every check passed and every one was right to.** The citation resolves; `lease`
genuinely is a declared subject of that source on that desk. What nothing asked
is whether a federal-tax publisher can settle a US GAAP question at all.

**0.7.0 had the map and pointed it at the wrong door.** The domain gate guarded
`searching.dispose` — where a passage may be STORED — and left `engine.serve`
alone, where a passage is handed to a person. So the same map that refused four
irs.gov proposals for this question would still serve one. It is now checked in
`serve`, below the position branch and above the tier logic.

**Two things the tester was right about that this does NOT fix**, recorded
because the next session will otherwise think it did:

- *"A domain guard fixes the lease case specifically and leaves the general hole
  open: nobody checks that the paragraph supports the conclusion."* True. That
  is the judge, and it is still not built.
- **Ratified positions are doing the safety work.** Five citations of 151 on
  that desk carry one, and the tester's first trap was caught only because it
  happened to hit one of the five.

---

## What the gate broke on its first run, and the measurement that found it

**It refused ELEVEN of the desks' own recorded problems** — every bank
reconciliation on the cash desk, four de minimis problems, one rewards problem.
Cause: `books`, `book`, `financial statement`, `financial statements` and
`accrual` were listed as US GAAP vocabulary. **They are the ordinary words of the
work**, and *applicable financial statement* is a defined term of
§ 1.263(a)-1(f), which is a Treasury regulation. A domain that claims them
swallows every bookkeeping question in the practice.

The list now holds terms of art and recognition phrases: `booked as an asset` is
in it and `booked` is not. That alone cleared all eleven, and the lease question
still classifies `us-gaap` 2–1.

**A ratified position was never at risk, and this was checked rather than
assumed.** The cash desk exists *because* the governing authority is unreachable
— FASB is `human_only`, so the firm ratified a position citing the IRS
publication that describes the same timing. A gate that refused that would be
the engine overruling the firm on their own answer. `serve` takes the position
branch first, so it does not; a test now pins it, and no exemption was written,
because code guarding a case that cannot arise is worse than none.

## Also from that report, not yet acted on

- **`binding: True` printed beside `tier: secondary`.** The field means *the firm
  ratified this*, not *this is binding authority* — and an accountant reading it
  next to an IRS publication will read the second. The word is wrong.
- **A brief is ~318 KB across three desks** (fixed-assets alone 242,596
  characters, 293 passages) against a stated design target of an 8,192-token
  local model.
- **`showed_by_source` leaks instrumentation** into a refusal somebody reads
  mid-close.
- **`python3` is not on PATH on the Forge**; the documented `holes.py` command
  fails there and works as `python`.
- **FASB's free Basic View is labelled "For Personal and Non-Commercial Use"**,
  behind a reCAPTCHA and a terms click. That is a licence question for the firm,
  not a wall to route around, and the tester correctly stopped at it.

---

## What the asking agent actually gets back — 0.7.2

**The firm's question: "how does it respond to the original agent?"** The Forge
tester read dataclasses. An agent does not. So the round trip was run as an
agent runs it — `consult`, read the brief, propose, `answer` — and printed.

**The architecture, said plainly, because it explains every trap in the
report:** `consult` hands over the authority, **the agent writes the answer and
picks the citation**, and `serve` checks that the citation resolves, that the
source is declared for that subject, and now that the domain matches. *Nothing
checks the reasoning.* So *"the desk says X"* is really *"an agent said X and the
engine did not stop it."*

**And every field that came back read like verification while being a property
of the source.** `tier` is the regulation's standing. `binding` says the firm
declared that source as authority that binds — **not that this answer binds**.
`checked_subject` is word overlap. `checked` is when the PASSAGE was last
confirmed. The tester: *"Served carries no field for 'did anyone check that this
paragraph says this?'"*

**The skill already said so, and that was not enough.** `ask-desk` carries the
sentence *"what it does not verify is that the conclusion follows"* — in prose,
at the top, read once by the agent and gone by the time an answer is rendered
onward to a person. **A warning that does not travel with the thing it warns
about is a warning nobody reads.**

So a served answer now carries `unchecked` and `passage`, computed in `serve`
rather than passed, and the skill requires an agent to print both. The tester's
sharpest trap now renders as:

> **deducted, not capitalized** — 26 CFR 1.263(a)-2(d)(1) · primary
> NOBODY CHECKED THAT THIS PARAGRAPH SAYS THIS …
> *"a taxpayer must capitalize amounts paid to acquire or produce a unit of
> real or personal property"*

**It refutes itself on sight.** It still serves — the domain guard cannot reach
a tax question cited to a tax regulation — but a person can now do in one glance
the check that was previously a lookup nobody performed.

**`binding` was NOT renamed.** Ten call sites to fix a reading problem is the
wrong tool; the sentence beside it says what it means instead.

---

## Two defects the round trip found that no test would have

Both from printing it for a person rather than asserting on it.

1. **"Read the passage" with no passage.** A ratified position has no passage
   text — it carries the firm's words in `.position` — so the cash desk served a
   disclaimer pointing at an empty string, **which is worse than no disclaimer
   because it looks discharged**. On a `human_only` source the firm's words are
   the desk's entire knowledge of the authority, so they are both the right
   thing to show and the only thing there is.
2. **"Nobody checked" was a lie on the safest answers.** A position-backed
   answer HAS been checked — the firm ratified that conclusion for that
   citation, and `_check` refuses any restatement, so the served words are
   theirs. There is no gap between conclusion and authority to warn about.
   **A disclaimer that cries wolf on the safe cases teaches a reader to skip it
   on the dangerous ones.** Two sentences now, and what is left unchecked on a
   ratified answer is stated and narrower: whether the firm's position fits
   these particular facts.

## What is still true and unfixed

**This is presentation, not protection.** 4 of 5 aimed traps still serve on the
largest desk. The judge — a second model handed only the paragraph and the
conclusion — is the fix, and it is not built. What changed is that the answer no
longer *looks* checked when it is not.

---

## The Forge closed a set of books on 0.7.2 — 0.7.3 is what it found

**The firm, on my saying 0.7.2 was verified:** *"stop assuming it works until you
test it with a forge prompt. it has to receive and give it back."* Correct. Every
"verified" that evening meant *I called `ask.answer` in my own container and read
the object back*. That proves a function returns. It does not prove a session
receives a question, loads the skill, routes it, and hands a person something
usable.

So a Forge session was asked to **do the work** rather than test it — close a set
of books, ask three questions, write what it would put in front of the
accountant. It reported that **the round trip works**, and that the two fields
0.7.2 added do the job:

> *"A reader who has never opened the CFR sees 'deducted, not capitalized'
> sitting three lines above 'must capitalize… include the invoice price.' The
> answer refutes itself on sight."*

And its honest limit, which is the right way to hold it: *"it worked here because
the contradiction is in the passage's first clause… It converts 'impossible to
catch' into 'catchable if you read', which is the correct trade, not a solved
problem."*

**Four defects, none of which a test would have found, and two of which I had
introduced within the hour.**

### 1 · `passage` echoed the answer on a ratified position — my own fix from an hour earlier

`serve` resolves through `authority_for`, which on a ratified citation returns
the **Position** — and a Position has no `.text`. My fix for the empty field fell
back to `.position`, so it printed:

```
an entry in the books            <- position
> an entry in the books          <- "the words it rests on"
```

The tester: *"the whole argument for `passage` is 'so the reader can check the
conclusion against the words it rests on' — and here the words it rests on are
the Pub. 583 text, which is not shown. **The one case where the reader is told a
human already decided is the case where the underlying authority becomes
invisible.**"* The text was reachable the entire time: `desk.passage()` on the
same citation carries 2,683 characters of it. Source text wins now; the firm's
words remain the fallback only for a citation-only `human_only` source.

### 2 · An escalation handed back instrumentation and withheld the reasoning

`Refusal` carried `showed_by_source={'S1': 63, 'S2': 40, …}` and **not** the
agent's `working` — the reasoning `ask-desk` insists is written in full. It went
only to the queue.

> *"So the one answer where the agent has the most to say hands the caller the
> least, and I had to write the accountant's paragraph from my own memory rather
> than from anything the desk returned. Meanwhile `showed_by_source` — pure
> instrumentation — does come back. That is exactly backwards for a human
> reader."*

Carried now, set once where every refusal passes through so a later one cannot
drop it.

### 3 · The skill's documented first line does not run

`sys.path.insert(0, os.environ["CLAUDE_PLUGIN_ROOT"])` raises `KeyError` in a
plain shell — the variable is set when a skill is *invoked*, not otherwise. That
is line one of first use. A test now **executes** the published snippet with the
variable stripped, because a snippet that only looks right is what shipped.

### 4 · The Skill tool served a SKILL.md three releases stale

`desk:ask-desk` resolved to the 0.4.0 cache — a file with no mention of
`unchecked` or `passage`. **An agent following it exactly would have produced the
pre-0.7.2 output and never known.** The tester only printed the fields because it
went and read the 0.7.2 file directly.

**This one is not fully fixed and should not be recorded as if it were.** The
skill now tells the reader how to check which version they loaded and to
`/reload-plugins` before trusting it. That is a warning, not a guarantee — the
resolution happens in the harness, not here.

### And one reversal, recorded rather than quietly applied

A test written that afternoon *required* the `unchecked` sentence to inventory
three checks, reasoning that a bare disclaimer trains a reader to skip it. The
Forge, after handing three of them to an accountant: *"at the fortieth of a
close, the eye slides off the capitals… the middle inventory of what was checked
is the part I would actually cut."* They did the work; they win. One clause still
names what was checked, so it is not bare — and the tier and source were printed
beside the citation anyway, so the inventory said it twice.
