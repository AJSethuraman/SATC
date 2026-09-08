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

### Correction, one hour later: three sections were refusing, not six

The paragraph above and the commit that carried it (`ae9323d`) say "six sections
that would not read at all now read". **Three did.** § 1.162-3, § 1.162-4 and
§ 1.263(a)-1 were already reading before any of this; the three that were
refusing and now read are § 1.446-1, § 1.274-5T and § 1.274-12. Every one of the
nine tested lands every path it cites, which is the part that was true.

**And two of the eleven regulations these desks rely on still refuse**, which the
docket card claimed otherwise until this correction. Both are diagnosed:

- **§ 1.274-5** opens `(a)-(b) [Reserved]` — the same span as § 1.274-5T's
  `(k) and (l)`, written with a dash. It also writes `(2)(i) and (ii) [Reserved]`,
  a span continuing the deepest label of a multi-label chain, which the new rule
  only reads when the chain is one label long. Expanding a true range needs the
  alphabet, which is not known until `placements` has chosen a depth — so the
  honest fix is to defer the expansion into `placements` rather than widen the
  regex.
- **§ 1.62-2** has broken markup in the government's own XML:
  `<I>Returning amounts in excess of expenses—(</I>1<I>) In general.</I>` puts
  the em-dash and the opening parenthesis inside the italics and the numeral
  outside. The run-in reader looks for an italic run closed by an em-dash and
  finds neither shape.

Found by checking a claim I had already written into a task, which is the only
reason it was caught before the firm read it.

### And then the last two, an hour after that: all eleven read

Seven causes in total, not the three prototyped and not the five reported above.

- **§ 1.62-2's cause is in the file, not the regulation.** The XML reads
  `<I>Returning amounts in excess of expenses—(</I>1<I>) In general.</I>` —
  the em-dash and the opening parenthesis inside the italics, the numeral
  outside — where every other run-in in the CFR writes
  `<I>Substantiation</I>—(1) <I>In general.</I>`. The same sentence, typeset two
  ways. The repair moves fences and never text: strip the italics from either
  side and the string is identical, and the label comes out plain, which is what
  (f)(1) is. A stray tag cost the vehicle desk every example it might have had.
- **§ 1.274-5 writes a reserved span three ways** — `(a)-(b)` on its opening
  line, `(2)(i) and (ii)` continuing the deepest label of a chain rather than
  the leading one, and true ranges `(3)-(7)` and `(1) through (3)`.

  The range is the interesting one. Expanding it looked like it needed the
  depth, and the depth is not known where labels are read. It does not: a range
  names two labels, and where exactly one alphabet holds both of them in that
  order, the run between them is the same whatever depth the pair turns out to
  sit at. `(3)-(7)` is 4, 5, 6, 7 in the only alphabet with a 3 and a 7. Where
  two alphabets qualify — `(i) through (v)` is five roman numerals or fourteen
  letters — it returns nothing and the section fails to read, loudly.

| section | paragraphs | self-citations landed |
|---|---|---|
| § 1.263(a)-3 | 172 | 76 of 76 (100 of 102 over the whole file, unchanged) |
| § 1.274-5T | 123 | 24 of 24 |
| § 1.274-12 | 96 | 28 of 28 |
| § 1.274-5 | 92 | 24 of 25 |
| § 1.446-1 | 77 | 30 of 30 |
| § 1.280F-6 | 70 | 22 of 22 |
| § 1.263(a)-1 | 68 | 24 of 24 |
| § 1.162-3 | 64 | 28 of 28 |
| § 1.62-2 | 49 | 21 of 21 |
| § 1.274-11 | 15 | 5 of 5 |
| § 1.162-2 | 8 | 0 of 0 |

§ 1.274-5's one dead reference is the regulation's own: its (b) is reserved to
§ 1.274-5T, so it names a (b)(2) it does not contain. That is the residue
§ 1.263(a)-3 has two of, not a reading that is partly wrong.

**Fifteen mutations tried across the seven rules; fourteen failed the suite.**
The fifteenth — dropping the trailing word boundary from the span pattern —
broke nothing, and the comment now says so rather than claiming it is load
bearing. The anchor does that work, the same finding `_RUN_IN` already records
about its full stop.

---

## Seventh docket published: `artifact/1750afce`

Three matters, all new — nothing from the sixth docket is carried, because all
eight were answered and asking an answered question again is the fault the card
rebuild exists to stop. `dec-courts-again` came off the page for that reason: it
was answered "Keep hosts closed" with no note, which settles it.

1. `dec-admit-publishers` — eCFR and Cornell's LII for § 1.162-3, from the
   searcher's first real run. Recommendation: admit eCFR only.
2. `dec-register-standing` — whether the standing check on how positions are
   worded is still wanted, given the firm's correction that the complaint was
   about how a position is EXPLAINED. Recommendation: drop it.
3. `dec-merge-305` — merge the pull request. Recommendation: merge.

**And a `Next` block, which is new to the page and new to canon.** canon 1.13.0
landed on `main` this morning with behaviour 19 — *name the goal, report the
distance, then stop* — and its docket skill asks for the goal to sit above the
decisions as **the one item silence approves**. The goal: get the three thin
desks holding the worked examples their own regulations contain. Distance: 0 of
3 desks.

**Two matters came off the page to get there.** "Add the 34 examples" and "read
the 29 written as prose" were drafted as decisions. They are not decisions —
they are the work. Behaviour 19: *"do not manufacture the next decision.
Behaviour 13 says decisions go to the human; it does not say produce some."*

**The docket was built on the old skill.** The plugin here was still on canon
1.12.0 — nine releases behind — so `/canon:docket` loaded the version without
behaviour 19 or the `Next` block. The firm caught it. `claude plugin marketplace
update satc` refreshes the listing and installs nothing; `claude plugin update
canon@satc` is the command that installs, and it is the trap canon's own log
already describes.

**Measured for this docket, and one of the numbers is a finding.** The eleven
sections yield **72** worked examples the extractor can see and **29** it cannot:
§ 1.274-11, § 1.274-12 and § 1.274-5 write an example as an ordinary numbered
paragraph rather than in a tagged block, so those sections read perfectly and
return nothing. All 29 are on the meals desk — the desk that appeared to gain
almost nothing today. It was not thin; it was unreadable in a second way nobody
had counted.

---

## Eighth docket, same page: `artifact/1750afce`

**The three matters are unchanged and unanswered** — read back from the page's
own store, which returned zero documents. Republished onto the same page rather
than opening a new one: a second page asking the same three questions cannot see
the first one's answers.

**The last goal is met and a new one is named.** All three thin desks hold every
worked example their regulations carry.

> **Next:** answer the close's own 18 questions from the desks and put every
> answer through the production path. **0 of 18 answered.**

Shaped to refuse, per behaviour 20:

- **It refuses the scoreboard.** Worked examples are withheld from anything
  being graded by three separate mechanisms, so a graded score *cannot* move
  when examples are added. Asking for one would be measuring nothing.
- **It refuses saying an answer is right.** These 18 have no answer key — that
  is why they were asked. The desk proposes; the firm disposes.

**A finding from routing them:** the vehicle desk gained 12 worked examples today
and **not one of the 18 questions reaches it.** Either the close never raised a
vehicle question or the routing does not fire on one; those are different
problems and this does not yet say which.

**And a candidate goal killed by measuring it.** "Run the searcher over the
recorded failures" looked obvious. The queue holds 22 failures, all of them
`citation_does_not_support`, and **none is `authority_absent`** — the only reason
that opens a gap. The searcher has no recorded work to do. Measured before
proposing rather than after starting.

### What I got wrong, and it is in the goal I wrote

The seventh docket's Next promised the examples would go in *"with the
before-and-after scores on the page"*. **Those scores cannot exist.** Scoring
withholds worked examples by construction, so adding 63 of them cannot move a
score. I wrote a measurement into a goal without checking the measurement was
possible, and repeated it in a commit message. Behaviour 20 asks a goal to be
shaped so it can refuse; this one asked for something the system refuses on
purpose.

---

## The Next is met: 18 of 18 answered, and one defect found twice

`runs/asked-2026-09-07/served.json`. **6 the engine would serve, 12 it would
refuse.** Nothing here is a score — whether a served conclusion is right is the
firm's to say.

| refusal | n | what it is |
|---|---|---|
| `context_not_on_file` | 5 | the follow-up the firm ratified, firing |
| `authority_absent` | 4 | the question reached a desk that does not hold it |
| `citation_does_not_support` | 2 | **the defect** |
| `facts_not_established` | 1 | the rule is clear; a fact about the client is not |

**Eleven of the twelve refusals are the desk working.** Five are the follow-up
the firm held two positions for and then ratified on the sixth docket, now firing
on real questions rather than on fixtures: Q4 and Q16 will not apply the firm's
$2,500 default without knowing whether this client is treated differently on
`capitalization_rule`; Q8 will not apply the J.Crew rule without `trade` on file;
Q9 and Q29 will not apply the rewards position without `taxpayer`. Four are a
question reaching the wrong desk, and **three of those four also reached the
right desk, which answered**.

### The defect, and it appeared twice on two different desks

Both times the desk held exactly the right authority and the per-subject
narrowing refused it.

**Q18, cash-and-bank.** § 1.446-1(a)(4)(ii) says it in the regulation's own
words — *"expenditures made during the year shall be properly classified as
between capital and expense… plant and equipment, which have a useful life
extending substantially beyond the taxable year, shall be charged to a capital
account"*. Refused:

> the question is about **bank**, which this desk answers from S2;
> `26 CFR 1.446-1(a)(4)(ii)` comes from S1

The only subject the question matched is "bank", from the close's own phrase
*"a bank feed has none"* — an incidental word, not what the question is about.

**Q12, rewards-and-information-returns.** The firm's own ratified position on
§ 1.6050W-1(c)(3). Refused:

> the question is about **peer-to-peer, 1099-nec**, which this desk answers from
> S11, S3; `26 CFR 1.6050W-1(c)(3)` comes from S6

**The desk refused the firm's own ratified position** because the question's
matching words are registered to different sources.

This is the mirror of the defect `fixed-assets/SUBJECTS.md` already records:
there the subjects were the regulation's vocabulary while the questions were the
situation's. Here a situation word matched and the subject it named was the wrong
one. **Not worked around** — the check is not loosened to produce a served
answer.

### The 63 worked examples were in front of me for all 18 and I cited none

Measured rather than assumed, and it is the deflating half of today. Every brief
carried its desk's full authority, examples included. All 18 answers rest on a
rule or on the firm's own words. These questions ask *which rule applies* and
*which fact is missing* — they are not fact patterns to be matched against a
worked example. That does not make the examples worthless; it says what they are
for is the question a bookkeeper asks about a specific entry, and none of these
18 is that.

### And a routing finding from before any of them were answered

The vehicle desk gained 12 worked examples today and **not one of the 18
questions reaches it.** Either the close never raised a vehicle question or the
routing does not fire on one; this does not say which.

---

## The seventh docket's three answers, and what each caused

Read back from `artifact/1750afce`, answered 15:49 UTC on 7 September 2026. All
three took the recommendation; none carried a note.

### `dec-admit-publishers` — **Admit eCFR only**

Cornell's LII declined, which is the narrower of the two and the right one: it is
a faithful copy and not the publisher. **Both** stored paragraphs were therefore
re-read from eCFR and tied out there before being stored — including
§ 1.162-3(c)(2), which the searcher first found at Cornell.

`fixed-assets` now declares **S2 · § 1.162-3**, holding exactly the two
paragraphs the searcher proposed. Admitting a publisher is not importing a
section, and the rest of § 1.162-3 has not been asked for.

**The subject moved with it, and that is the substance of the change.**
`materials and supplies` was registered to S1 — to § 1.263(a)-3, which uses the
phrase only to say what a thing is NOT, its examples citing § 1.162-3(c)(1)(i) by
name for the definition. Left there, the desk would have declared a source it
could never serve on the one question it answers: `engine.serve` refuses a
citation from a source the desk does not use for THIS subject. **That is the
defect the answering run found twice this afternoon**, and building it in on
purpose an hour later would have been remarkable.

**And the subject list under-fired on its first real test.** With `materials and
supplies` and `material or supply` declared, a question worded the way
§ 1.263(a)-3's own examples word it — *"are not materials or supplies under
§ 1.162-3(c)(1)(i)"* — served with `checked_subject=False`: allowed out with the
subject gate never run. `materials or supplies` is declared now. The form the
regulation writes is the form a preparer will write.

### `dec-register-standing` — **Drop it — the card was the problem**

Nothing further is built. The docket-card fix stands: the recommendation leads,
and a card cannot offer a pick its own recommendation argues against.

### `dec-merge-305` — **Merge it**

### Four guards fired on the second source, and one of them was hiding

Adding a second source to a desk that had held one since it was built exposed
three tests that had quietly conflated *the desk* with *§ 1.263(a)-3*: the
verbatim-marking check, the `PROBLEMS.md` denominator, and the citation index.
The first two are the section's own arithmetic and are now scoped to S1; the
index is the desk's and correctly grew to 174.

**The fourth was a test written twice, identically.** Both copies had the same
name, so the first was shadowed and had never run — surfaced only because adding
a source made one of them fail. Its assertion was `calls == sorted(set(calls))`,
which required alphabetical order as well as one-call-per-source; true for free
with one source, false with two, and never the property the test's own name
claimed. The duplicate is removed and the survivor asserts what it says.

---

## `dec-desk-asks-for-code` — **the recommendation, taken**

> *"i'll take your recommendation"* — 7 September 2026.

**A field, and only a field.** Built the same hour.

`unsupported.py` had five resolutions and none of them changed the software. It
has six now, and the sixth is the only one that does:

> The rule is clear and there is NOWHERE to write the answer → **build the
> field**, naming the position that asked.

**It arrives carrying its chain, which was the condition.** `Refusal` gained
`fact` and `by_position` as FIELDS rather than prose in `detail`, and
`Unsupported` gained `needs_field` and `asked_by`. A desk asks for a field
because a position it holds names a fact — so approving the field approves that
position's reach, and a chain parsed back out of a sentence is not a chain
anybody can check.

**Only `no_field_for_this_fact` becomes a request.** `context_not_on_file` names
a fact too and means the opposite: the field exists and this engagement did not
fill it in. Copying it across would file a request to build something already
built, and the queue's largest category would start asking for software.

Proved end to end against the real position rather than a fixture — the
capitalisation desk's POS1 with its field removed produces
`needs_field: capitalization_rule`, `asked_by: POS1`.

**Four mutations, and one survived until a test was written for it.** Deleting
`fact=fact` from the `client_rule_governs` branch broke nothing: the field was
assigned and nothing read it, which is the shape of a safeguard everyone
believes in that does nothing — the same finding this record made about a
different check five days ago. All three `Unless:` refusals now have to name
their fact, and all three sites fail the suite when they stop.
