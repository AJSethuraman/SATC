# The sixth docket — eight matters, eight answers

Published as `artifact/83e68c31` and answered between **13:09 and 13:16 UTC on
7 September 2026**. Read back at 13:20. Every quotation is verbatim from the form.

## Three ratifications, built

| | Position | |
|---|---|---|
| `capitalization/POS1` | make the de minimis election every year | **Ratify it** |
| `capitalization/POS2` | the threshold is $2,500 / $5,000 | **Ratify it** |
| `rewards/POS3` | when you cannot tell which rail a payment took, report it | **Ratify it** |

No notes on any of the three. **Twenty ratified positions, zero proposals** — the
first time the record has held none.

**What the two capitalization ratifications changed.** Until 13:09 the desk
ANSWERED safe-harbour questions straight from the regulation, never asking
whether that client had a standing rule of its own — the thing the firm objected
to when they first held these. Ratified, it refuses until somebody says. The
test that asserted the old behaviour carried a note telling its successor what to
do on this day; it now asserts the follow-up firing on the real record, with no
simulation left on that path.

**`rewards/POS3` was ratified with its wording still owed a redraft** — matter
`dec-register` below. That is a change to how it reads, never to what it says.

## `dec-courts-again` — answered, after being carried three times

> **Keep hosts closed.**

No note. The contradiction is settled: the button stands, the five court hosts
stay closed, and a court decision reaches a desk when the firm hands it over.

## `dec-parser` — **Have another go**

One timeboxed attempt at the four regulations that will not read. The acceptance
test is already published and unfakeable: a regulation cites its own paragraphs,
and a reading is right when every cited path lands. § 1.263(a)-3 lands 100 of
102; the best attempt at § 1.446-1 lands 24 of 31.

## `dec-merge-300` — **Merge it**

## `dec-register` — **Redraft them**, and the note carries two things

> *"redraft and we have to ensure our rules are followed as answers are added to
> the desk. also now that i'm thinking about it - each time we add a rule through
> the desk the entire plugin needs pushed and reloaded, right?"*

**The first half is a standing requirement, not a one-off.** Redrafting three
positions today does nothing about the fourth written next week. The repository
already has the pattern: `website/pricing.spec.py` checks published client copy
mechanically for contract-desk verbs and over-long sentences. Positions have had
no such check, which is why they drifted into the register of the thing that
generated them.

**The second half is a question, and the answer is yes.** `desk` is a plugin
(`desk/.claude-plugin/plugin.json`, listed in `.claude-plugin/marketplace.json`).
A position lives in `desks/*/positions/POSITIONS.md` inside it. A machine
consulting the desk reads the INSTALLED copy, so a ratification is not live
there until the plugin is updated — and `CLAUDE.md` already records the trap:
*"marketplace update refreshes the listing and does not install."* So the full
path is commit → push → pull → `claude plugin update desk`.

That is real friction and it is worth saying plainly: **the twenty positions
ratified in this repository are live only where somebody has run that update.**

## `dec-searcher-scope` — **Not yet**, and the note rejects the question

> *"these sites cannot be a general limit - this is too specific for the entirety
> of the desk. though, as i have said i don't know how many times, it just makes
> sense for us to basically index everything the IRS has to say from their
> website. and maybe it makes more sense to do it as questions come up, but i do
> not like these sorts of overly generic questions. there has to be a way to make
> sure the agent doesn't go to literally random places that we can't trust
> looking, however again there's simply no point in this whole forge setup if we
> only limit to certain sites - though, i do understand if the forge taking over
> the search is only for fallback. so what's going on here really"*

**The question was badly framed and the note says so correctly.** It offered
three-sites-or-anywhere as if those were the alternatives. They are not, and the
record already contains the better answer.

**Trust here has never been a list of domains.** Every source carries `Tier`
(primary / secondary / tertiary), `Access` and `May store`. A law firm's
marketing page fails not because of its domain but because it is not authority
and cannot be assigned a tier — and because it cannot be tied out against a
publisher of record. The domain whitelist was a proxy for a test the record
already performs better.

**"Index everything the IRS says" is a different project from a searcher**, and
both are legitimate. Bulk ingestion of a publisher we already trust is closer to
`add_examples.py` than to anything with a model in it.

**And the last clause is the one that matters most: *"there's simply no point in
this whole forge setup"*.** See the note below.

---

## The Forge does not exist as a session, and everything above assumed it did

Checked 7 September 2026: the account has two environments, `Personal` and
`Occam`, both `kind: anthropic_cloud`. **There is no Forge environment and no
self-hosted runner.** Every session including this one runs in a cloud container
with no access to that machine, its Chrome, or its GPU.

So the searcher design has been drawn around a machine that is not connected to
anything. That is not a detail — it is the reason `dec-searcher-scope` could not
have been answered usefully, and the firm spotted it before this session did.

---

## Built, 7 September 2026: the searcher, and the docket card that asked twice

**The whitelist died on one question.** *"how would you know you need to access a
site not on the whitelist before being asked?"* You cannot ask permission for a
site you do not yet know you need, so an allow-list makes discovery the one thing
the discovery tool cannot do. `searching.py` looks anywhere; the gate is on the
record, not on the reaching. `desk/runs/2026-09-07/SEARCH.md` is the first real
run: § 1.162-3 found through a live search, two passages tied out at eCFR and
Cornell, both held back as source proposals because neither publisher is declared
on `fixed-assets`.

**And a second complaint the same day, which was not about positions at all.**
*"i have no clue why you will even ask me things on the docket like 'should i
ratify this' when your last thing is a recommendation saying 'i wouldn't activate
this, it is missing a field'."*

I had been measuring the wrong thing — word counts and sentence shapes in the
POSITIONS. The dribble is the CARD. Two faults, both now structural rather than
stylistic:

- The recommendation sat last, under four labelled blocks, so the reader
  assembled the point before reaching it. It now leads, directly under the title,
  and the supporting blocks are one click away.
- The picks were a constant that never read the recommendation, so the fifth
  docket offered **Ratify it** first on two cards whose own recommendation said
  do not ratify. A recommendation now names its pick, that pick is offered first,
  and a card recommending something it does not offer raises `DocketError` at
  build time. The preface's held-back count reads the same field instead of
  matching the phrase "Do not ratify" in prose.

**Two cards were asking settled questions and are gone**: the search-scope card
(you answered it) and the merge card for #300 (it merged). Replaced by the two
decisions that are actually open — admitting eCFR and Cornell for § 1.162-3, and
merging #305.

---

## `dec-parser` built, 7 September 2026: all six sections read

The pass mark was the firm's and it was unfakeable: a regulation names its own
paragraphs, and a reading is right when every one of them lands. The best
prototype found **24 of the 31** § 1.446-1 cites, and I said that was not good
enough to ship — three quarters is not the ordinary residue of dead
cross-references, it is a reading that is partly wrong.

**It now finds all thirty**, and every one of the six sections lands every path
it cites. § 1.263(a)-3, the section that already worked, reads identically: 172
paragraphs, 0 underdetermined, the same two dead references.

| section | paragraphs | self-citations landed |
|---|---|---|
| § 1.263(a)-3 | 172 | 76 of 76 (100 of 102 over the whole file, unchanged) |
| § 1.446-1 | 77 | 30 of 30 |
| § 1.274-5T | 123 | 24 of 24 |
| § 1.274-12 | 96 | 28 of 28 |
| § 1.162-3 | 64 | 28 of 28 |
| § 1.263(a)-1 | 68 | 24 of 24 |

**Five causes, not the three I had found.** The two I described to the firm were
real and insufficient, exactly as the docket said.

1. `ALPHABETS` had no italic-lowercase alphabet at all.
2. A depth admitted one alphabet. § 1.446-1 needs the fourth to admit plain
   capitals **or** italic lowercase, chosen per branch — `(c)(1)(ii)(A)` and
   `(c)(1)(iv)(a)` in one section.
3. **A label sitting directly on another with no heading between them.**
   `(2)(i) Except as otherwise…` and `(ii) (a) A change in…` are each one
   element opening two paragraphs, and the chain only continued through a
   run-in heading.
4. **A span reserved in one element.** § 1.274-5T's `(k) and (l) [Reserved]`
   leaves the outline standing at (k), so the `(m)` that follows — the last
   element of 105 — is not its successor and the section had no reading at all.
5. **An element with no label.** § 1.274-12 writes `(B) Example.` in one
   element and the example itself in the next, unnumbered. This reader raised
   on that, correctly at the time; it now continues the paragraph above, and
   still raises before the first label, where there is nothing to continue.

**And one defect the work surfaced that was not about the outline.**
`cited_paths` read `paragraph (c)(1)(iii), (iv), or (v)` as citing paragraphs
called `(iv)` and `(v)`. Not only a miscount: `governing()` picks the citation an
example is filed under out of that set, so a bare `(v)` was a candidate rule on
any section whose examples live under (v) — the same class of defect as the four
examples once filed under the wrong paragraph. An enumerated item is now resolved
against its head, as a sibling or a child depending on which level its alphabet
belongs to.

Resolving them against `ALPHABETS` rather than the plain hierarchy immediately
produced a `(g)(2)(i)(j)` that no section has, out of "paragraphs (g)(2)(i) and
(j)" — a citation is plain text and says nothing about face. The acceptance bar
caught it by going from 102 to 103.

**Eight mutations, all caught.** Nothing here has been added to a desk: the
reading is a separate change from what any desk is scored on.
