# PRD: Verification is the gate

**Status:** Draft · **Owner:** Sethuraman Accounting, Tax & Consulting · **Last updated:** 2026-09-08

---

## 1. Problem

**A desk can only answer what somebody already stored, and that is the wrong
limit.** The engine refuses any citation absent from the desk's record:

```python
backing = desk.authority_for(answer.citation)
if backing is None:
    return Refusal("authority_absent", "... is not in this desk's record")
```

and the brief says it to every answerer: *"Answer ONLY from what follows. A
citation to anything not printed here is refused by the engine, however real it
is."*

The consequence is that the seven desks are a ceiling. A doer agent running a
month's books asks about a lease, a payroll deposit, a state filing — anything
outside the stored corpus — and gets `authority_absent`. The searcher can go and
find the rule, and then **everything stops at the firm**, because a source has to
be admitted before any desk may cite it. A question that a competent person could
settle in four minutes with a browser waits on the owner instead.

The firm, 8 September 2026, having explained it more than once:

> *"we want the best to be able to answer anything and not be limited to
> literally specific things … the entire point is to have a headless machine and
> the agent to tie out things to make sure it's all correct."*

> *"Yes verification is the gate. Who cares if we can store it outside of it just
> being quicker the next time. Store if possible sure but this isn't a limit."*

**Why now:** the pieces are all built and pointed the wrong way. `proving.py`
compares our text against a publisher's, `domains.py` says which publisher can
settle which question, and `record.ACCESS` has declared a `headless_browser`
rung since the beginning that nothing has ever walked. The firm authorised the
browser on 8 September.

## 2. Solution

**A desk answers anything it can prove.** When the record holds the authority it
answers from the record, unchanged. When it does not, the agent goes and gets the
authority, the desk fetches the publisher's own page with a real browser, and it
serves the answer **only if the words are on that page right now** — citing the
live document, with the URL, the timestamp, the digest of the bytes, and how much
of the passage was found.

Storage stops being the gate and becomes a cache: worth having so the next
question is faster, never a precondition for answering. `record.MAY_STORE`
already has `citation_only` for exactly this — cite it, keep nothing.

One check does not move: **the publisher must be competent to settle the
question.** `domains.governs` is what caught a Treasury regulation being served,
primary and binding, for a balance-sheet question on 8 September. Proving that
irs.gov really says something is not evidence that irs.gov gets to say it.

## 3. Goals & Non-Goals

**Goals**

- A doer agent can ask a desk a question in a subject no desk holds and get a
  cited, verified answer rather than `authority_absent`.
- Every served answer that did not come from the record carries a proof a
  skeptic can re-run by hand: URL, fetch time, sha256, bytes, matched characters.
- Nothing is served on unproved text. `DIFFERS` and `COULD NOT` never become a
  served answer on an unstored citation.
- The firm is reached only for the two things that are genuinely theirs: a wall
  we may not cross, and a question no authority anywhere settles.
- Storing what was found is opportunistic and permitted-by-default-never.

**Non-Goals / Out of scope**

- **Anything touching a ledger.** No transactions, no trial balance, no
  statements, no month-end pipeline. The doer agent runs the books in whatever it
  runs them in; that is not this system's business. Stated because two earlier
  passes at this drifted straight into it.
- **Removing `domains.governs`.** Subject breadth is the goal; publisher
  competence is not negotiable.
- **Crossing a licence wall.** A reCAPTCHA, a terms click or a sign-in stays a
  wall. `access: human_only` still means the engine never reaches.
- **Growing `DOMAINS.md` to cover every body of authority.** Needed, phased,
  tracked separately — see Milestones. v1 ships with the two bodies that exist.
- **Making the desks decide what a client's facts are.** Unchanged: facts are
  told to the desk or the desk asks.
- **Auto-admitting a publisher into a desk's `SOURCES.md`.** The firm admits
  sources. What changes is that an answer no longer waits on that.

## 4. User Stories

1. As a **doer agent** running a client's books, I want to ask a desk a question
   about a subject no desk was built for, so that I get an answer instead of a
   dead end.
2. As a **doer agent**, I want the answer to carry a citation I can open, so that
   I can put it in front of the owner without either of us taking it on trust.
3. As a **doer agent**, I want to be told plainly when the answer came from a
   live fetch rather than the record, so that I know which of the two I am
   holding.
4. As a **desk**, I want to fetch a publisher's page with a real browser, so that
   a site which bounces plain clients does not read as "the authority moved".
5. As a **desk**, I want to refuse when the words are not on the page I fetched,
   so that a plausible citation cannot become an answer.
6. As a **desk**, I want to refuse when I could not reach the publisher at all,
   rather than serving unproved text, so that "unknown" never silently upgrades.
7. As a **desk**, I want to keep refusing a publisher that does not govern the
   question, so that verifying the wrong body of authority does not launder it.
8. As **the firm**, I want to be asked only about walls and genuine gaps, so that
   my queue is decisions rather than lookups.
9. As **the firm**, I want anything stored from a live find to be permitted
   explicitly rather than by default, so that a licence is never crossed by
   accident.
10. As **the firm**, I want to see, for any answer, whether it rested on stored
    text or a live proof and when that proof was taken, so that I can tell a
    fresh answer from an old one.
11. As a **reviewer**, I want the proof to be re-runnable by hand from what the
    answer carries, so that I do not have to trust this system's own word for
    itself.
12. As a **maintainer**, I want the live path to be unreachable without an
    explicitly passed transport, so that the offline suite cannot start making
    network calls by accident.

## 5. Implementation Decisions

### Where the gate moves

`engine._check` keeps its order and gains one branch. Today an absent citation is
terminal. It becomes a *candidate*: the answer may still be served if a proof
comes back `TIED`. The refusal `authority_absent` survives unchanged for the case
where no proof was offered — which is every existing caller and the whole suite.

**The order does not change, and each stage may add a refusal and never remove
one.** The live path sits where `prove` already sits, and inherits that property:

```
citation present in record?  -> yes: today's path, unchanged
                             -> no : candidate path, only if a transport was given
domain competence (domains.governs)   ALWAYS, both paths
tie-out (proving.prove)               required on the candidate path
judge (judging.read)                  unchanged, still opt-in
```

### The candidate source

`proving.prove` calls `transport(source, citation)` and needs a `record.Source`.
An unadmitted publisher has none, so one is **built in memory** from the found
URL rather than the transport signature changing:

- `tier` — from `domains.tier_for(url, domain)`. An unknown host is `TERTIARY`
  and therefore not binding, which is already the right answer.
- `access` — `headless_browser`. The rung the firm authorised.
- `may_store` — `license_check`, the record's own default, which stores nothing.
- `checked` — the fetch date, because that is when anybody last confirmed it.

This reuses `Source.binding` and `Source.readable` untouched. A candidate whose
host resolves `human_only` in the record is refused before any fetch.

### The transport

A new module supplies a **real headless browser** transport, returning the
existing `fetch.Response` — `status`, `body`, `headers`, `url` (where we landed
after redirects), `egress_blocked`. Nothing else in the system learns a new shape.

`Response.url` is load-bearing and already exists for this reason: `proving`
compares the landed host against the asked host and reports `COULD NOT` on a
mismatch, because ecfr.gov bounces non-browser clients to an interstitial that
returns **HTTP 200**. The browser is what stops that happening at all; the host
check stays as the guard for when it does.

**The user agent is a real browser because it is one.** The firm's answer to the
8 September decision, and the reason: a claim to be Chrome is a false statement
to a publisher whose text we cite as authority in client work.

### What the answer carries

`Served.proof` already exists and already carries everything a re-run needs. The
rendering gains one line, above the citation, for the case where the record held
nothing: **the answer rests on a document fetched at a stated moment, not on this
record.** Freshness is a strength here and the reader should see which they have.

`Served.__str__` is the place, because a skill can go stale and what it tells you
to print cannot.

### Storage

After a `TIED` proof, storing the passage is attempted only when the resolved
source says `may_store: full_text`. There is no such source for a candidate by
construction, so **v1 stores nothing** and the answer is `citation_only` in
effect. The hook exists so that admitting a publisher later turns caching on
without touching the engine.

### What does not change

- `domains.classify` / `governs` / `tier_for` — untouched.
- `judging` — untouched and still opt-in.
- Ratified positions — untouched. The firm's own word is not fetched from
  anybody.
- The refusal vocabulary. No new reason: a candidate that fails its tie-out is
  `authority_has_moved` if the text is absent from the page, and
  `authority_absent` if there was no proof to offer.

### The tie-out is the exhibit, and it is always reported

**Corrected 8 September, by the firm, after I had it backwards.** I treated the
tie-out as a check the engine runs *after* deciding to serve, and then declared
it broken for not establishing whether a rule was current. It never claimed to.

> *"Tie out isn't meant to pass old rules specifically. It's meant to be used to
> prove how a suggestion is correct prior to using it. Like it is handed in with
> the suggestion so the judge can actually assess it."*

> *"It should state what happened when trying to tie it out. I need info to make
> decisions down the line."*

So the tie-out is **evidence submitted with a proposal**, not a gate the engine
applies to a finished answer. Three consequences, and they reshape the pipeline:

**1. The proposer produces it.** Proposing a conclusion means handing in what
backs it: the document fetched, the URL, the moment, the digest, the span that
matched. An answer and its exhibit arrive together.

**2. The judge assesses the pair, reading the fetched document.** `judging.read`
today checks the judge's quoted words against OUR STORED PASSAGE. With an exhibit
in hand it should read the authority that was actually fetched — the thing the
suggestion rests on — not our copy of it.

**3. The attempt is always stated, whatever it produced.** Not only when it
succeeds, and not only when it blocks. `TIED`, `DIFFERS` and `COULD NOT` are all
findings, and the reason is explicit: *"I need info to make decisions down the
line."* A publisher that keeps failing to tie out is a decision waiting to be
made, and it can only be made if the failures accumulate somewhere readable
rather than vanishing into one answer nobody kept.

**What this does NOT change:** whether a verdict blocks. `DIFFERS` still
withdraws — serving text the publisher has changed, with our own record as the
only witness, is the thing the proof exists to stop. `COULD NOT` still serves a
STORED answer and says so, because refusing there would make a client's answer
depend on a government website being up. On the CANDIDATE path `COULD NOT`
refuses, because there is nothing else holding the answer up — and **the refusal
states what happened when trying**, which is the point.

**And staleness moves to where judgment belongs.** A reader holding
`ASU 2016-02` can say "this is the text as issued in 2016 and I cannot tell you
it is still the rule" — with their name against it. That is reading, not a
mechanical check, and this engine's line has always been that it checks what is
exactly checkable and a reader assesses what needs reading. An earlier draft of
this PRD put currency in the engine as a declared field on a source; that was the
wrong side of the line.

### Client data

Unchanged and absolute. The doer describes the transaction in words; no client
name, TIN or figure crosses to a desk or into a fetch. `relay.ask` already
refuses an envelope containing a TIN.

## 6. Testing Decisions

**Primary seam — `ask.answer(...)`.** The front door, and already the seam
`prove` is tested at (`tests/test_an_answer_can_prove_itself.py`). A test passes
a fake transport returning a canned document and asserts the outcome. Everything
worth proving is observable there: served-with-live-proof, refused on `DIFFERS`,
refused on `COULD NOT`, refused on the wrong body of authority, and the control
that an unstored citation with **no** transport still refuses exactly as it does
today.

What a good test proves here:

- An answer cited to a document no desk holds is **served** when the fake
  transport returns a page containing the passage — and the `Proof` carries the
  URL, the digest and the matched length.
- The same answer is **refused** when the page does not contain it.
- The same answer is **refused** when the transport raises.
- A candidate from a host `domains` says does not govern the question is refused
  **before** any fetch is attempted — assert the transport was never called.
- With no transport, behaviour is byte-identical to today. This is the control
  that stops the change becoming a hole.

**Second seam — the browser transport, and it cannot be reached from the first.**
`conftest.py` replaces the socket layer for every test, autouse, with a test
proving the guard itself can fail. A real browser needs a real socket. So the
transport gets a contract test against a local fixture, and **the real thing is
proven by a live run on the Forge, recorded in the decision record** — the firm's
answer on 8 September.

This is stated as a limit rather than hidden: *"the suite proves the code works
where it was written."* Every negative assertion about the live path gets a
positive precondition — assert the answer was `Served` before asserting a field
on it is absent (`test_a_negative_assertion_needs_a_positive_precondition`).

**Mutation is required, not optional.** At minimum: make the tie-out always pass;
make `governs` always true; make `COULD NOT` serve; skip the host-match check.
Each must turn a test red.

## 7. Done Criteria

1. A question in a subject no desk holds returns a served, cited answer through
   `ask.answer(...)` with a live `Proof`, in the offline suite, via a fake
   transport.
2. All five refusal paths above are red under mutation.
3. With no transport passed, the full existing suite is unchanged — same count,
   same behaviour.
4. **A live run on the Forge**, against a real publisher, through the real
   headless browser, recorded in a dated decision record with the URL, the
   timestamp and the digest.
5. `docs/` states plainly what CI covers and what only the live run covers.

## 8. Milestones

- **v1 — the gate moves.** Candidate path, browser transport, live run recorded.
- **Next — grow `DOMAINS.md`.** Two bodies exist (federal tax, US GAAP). Payroll,
  state, and information-return questions have no governing body named, so they
  refuse for the right reason and still refuse. Mostly research plus the firm's
  yes; phased deliberately so it does not block v1. `[LOG]`
- **Later — caching.** Turning `may_store: full_text` on for admitted publishers
  so a proved passage is kept and the next question is faster. Explicitly *not*
  a limit on answering. `[LOG]`

## 9. Open Questions

**None.** Both questions this PRD opened were answered on the docket and are
recorded below rather than left hanging.

- **FASB's free ASU is admitted.** *"Admit the free ASU."* The firm also asked
  why FASB publishes two things — the Codification is living, an ASU is frozen at
  issue — and my first answer turned that into a currency check inside the
  engine. The firm corrected it: the tie-out is the exhibit handed in with a
  suggestion, and whether a frozen document is still the rule is a judgment a
  reader makes with their name against it. See *The tie-out is the exhibit, and
  it is always reported* above. Nothing here waits on the firm.
- **The judge looks at everything.** *"The judge can look at it all I guess?"* —
  all seven desks, not `fixed-assets` first. The cost stands and is stated so
  nobody rediscovers it: a second model call on every served answer, and the
  check is worth nothing unless the second reader is genuinely second — one
  session playing both parts produces something that looks like a check and is
  not. `judging.read` already raises when the answerer judges itself, which is
  the load-bearing part.
