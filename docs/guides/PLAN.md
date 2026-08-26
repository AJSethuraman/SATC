# Free guides — what to publish

> "i was thinking we should have documents or posts that can help clients with
> like... bringing us good records and stuff. it's generally useful advice for
> free and we can point our clients to it for our own use"
> — the firm

**Two pages. Not one, not ten.**

| File | Page title | Who reads it |
|---|---|---|
| `good-records-individuals.md` | What good records look like | Anyone with a 1040 — wages, investments, a rental, a K-1 |
| `good-records-business.md` | Good records for a business | Anyone who works for themselves or owns an entity |

`SOURCES.md` carries every factual claim in both, with the IRS or Ohio page it
came from. `tenets.spec.py` runs the mechanical half of the tenets over both
drafts; it passes, and it caught two real problems on its first run.

---

## What this is actually for

`fee-schedule.yaml` holds five assumptions. Break one and the fixed price stops
applying. `cleanup` — "the records need reconciling before the return can be
prepared" — is the one that fires most and the one the firm least wants.

A client cannot hold an assumption nobody has described to them. The schedule
says as much about cleanup itself: a client whose books need work does not know
they are in that state, because being in it is what makes it invisible from the
inside.

So these two pages are the client-facing half of the pricing model. They are
the only place a client can find out what "complete" means before it costs them
anything.

**There is also a hole in the live site.** `pricing.html` says *"These prices
assume your records arrive complete."* Nothing sits behind that sentence — no
link, no definition. The first line of the individual guide answers it outright:

> Complete means the return can be finished without coming back to you for
> something.

The spec asserts that sentence is there. If it ever goes, the link from the
price page becomes decoration.

---

## Why two

**Why not one.** For a person with a W-2, cleanup is a missing document. For a
business, cleanup is books that do not match the bank. Those are different
problems with different answers, and on one page the second one becomes a
footnote to the first. The person with two W-2s would also have to scroll past
inventory counts to reach anything of theirs.

**Why not three.** Splitting Schedule C from entities looked right and is not.
Four fifths of the advice is identical — one account, books that match, a
year-end set, mileage, contractors. Three pages would say all of that twice,
which is tenet 5 across pages. What genuinely differs for an entity is a
balance sheet, owner K-1 timing and the S corporation health insurance trap,
and that is a section, not a page.

**Why not a landlord page.** The schedule stopped treating rentals as a
package on 26 August. A landlord is a Standard client with a Schedule E beside
it. A separate page would put back a split the pricing just took out.

**The split matches one the firm already made.** Asked to merge individual and
entity pricing into one section, the answer was *"actually you have a point
they are fairly different."* The price page has two tabs for that reason. Two
guides sit on the same seam, which is also what tenet 4 asks for — two things
doing different jobs should look different.

**One page each is the ceiling.** A content library nobody opens is worth less
than one page a client actually reads. If a third is ever wanted, the evidence
for it should be a question clients keep asking that neither page answers.

---

## The organizer overlap

There is already an **Organizer Cover Letter** in `satc-handoff/04-TEMPLATES/`
and an organizer sender in `satc_system`. The decision was: **complement, and
feed. Do not restate.**

The two do different jobs.

|  | Organizer cover letter | These guides |
|---|---|---|
| Reach | Every returning client, every January | Anyone, any time, including strangers |
| Content | Their employers, their brokerage, their rental | General |
| Carries | A date to return it by | No date |
| Answers | What to send | What makes it usable |

Its own field spec is emphatic that its requested list must be built from last
year's return and **not** be a generic checklist — that is the difference
between an organizer back in two weeks and one back in April. A public generic
checklist is exactly the thing that warning is about, so neither guide is one.

**Concretely, what was dropped to stay out of its way.** An early draft had a
bullet reading *"anything that changed — marriage, a birth, a move, a new
rental, a letter from a tax office."* That is section 02 of the cover letter,
almost word for word. It came out. The guides cover two items from that list —
crypto and foreign accounts — and cover them from the other side: not *tell us
whether*, but *here is what you will need and why no form will bring it*.

**The feed, and it is one line of work.** The cover letter's closing paragraph
could carry a link to the individual guide. It has no room to explain why any
of it matters; the guide is nothing but that. **Not done here** — the templates
are the firm's and this brief said not to touch the site or the handoff set.

---

## Where each is linked from

1. **`pricing.html`** — the word *complete* in "These prices assume your records
   arrive complete" becomes a link to the individual guide. This is the live
   gap and the highest-value link of the four.
2. **`index.html`** — the *"What we'll need later"* block under Get Started.
   It already tells a visitor what is needed at signing; the guide is what is
   needed to prepare.
3. **The businesses tab** on `pricing.html` → the business guide.
4. **The organizer cover letter**, per above, when the firm wants it.

Both pages need adding to `sitemap.xml`. Neither should carry a price.

---

## What was deliberately left out

- **Every figure from the fee schedule.** No package prices, no hourly rate, no
  cleanup charge, no records sorting fee. The price page owns prices; two
  places holding the same number is how they drift.
- **The word "cleanup", and the whole idea of a surcharge.** A page that
  explains what good records are and then bills for bad ones reads as a threat.
  The pages say what a return needs and stop there.
- **Farms.** Priced in the schedule, absent from the site on purpose, absent
  here for the same reason.
- **Any position on what is deductible.** Both pages say what record a thing
  needs, never whether it can be claimed. That keeps them useful to a stranger
  without being advice to one.
- **What an S corporation owner pays themselves.** It sits outside the
  engagement in the schedule. Left silent, and flagged — see `SOURCES.md`.
- **Turnaround, review times, and anything about who does the work.** Tenet 6.
- **A retention table in the business guide.** It lives on the individual page
  and is referred to, not repeated.

---

## What needs a human before this goes up

Six `[CONFIRM:` markers, listed in full at the foot of `SOURCES.md`. The two
that block publication:

- **Every IRS citation was located through search, not read.** `irs.gov`,
  `tax.ohio.gov` and `ritaohio.com` are blocked by this container's network.
  Good enough to draft against; not good enough to publish a CPA firm's name
  over. Each link needs opening once against the claim beside it.
- **Whether these pages carry a line saying they are general.** Nothing was
  invented, because inventing assurance wording is against the repo's own rule.
  If one is wanted, the sentence has to be the firm's.

The other four are decisions, not risks: the IRA form's deadline, how far the
Ohio city claim reaches, whether to name the upload route, and where the pages
live.

---

# The third guide — entity choice

> "we should definitely let people know about s corp pay - i think an important
> topic is actually people thinking of being an s corp and not understanding
> what that means. heck even a page on what and why an LLC to some extent some
> people need"
> — the firm

| File | Page title | Who reads it |
|---|---|---|
| `entity-choice.md` | What people mean by "S corp" | Someone told by a friend, a podcast or a bookkeeper that they should be an S corp |

`SOURCES-entity-choice.md` carries its claims separately from `SOURCES.md`,
because that file is titled for the records guides and the two sets share no
subject. `tenets.spec.py` now runs over three drafts, and its cross-page check
runs over every pair rather than the original one.

## Where it sits

The records guides answer *what does a return need from me*. This one answers a
question asked earlier than that, and by someone who is not a client yet. It is
the only one of the three whose reader is deciding something rather than
gathering something.

It is also the one closest to the price page. `pricing.html` prices
partnerships, S corporations and C corporations on the Businesses tab and
assumes the visitor knows which they are. Some of them do not, and the ones who
do not are the ones about to buy the wrong thing.

## The confusion it exists to fix

Three separate ideas, routinely collapsed into one:

1. An LLC is a state filing. It settles ownership and liability.
2. How a business is taxed is a different question with its own defaults.
3. "S corp" is an election. An LLC can make it and stay an LLC.

So "should I be an LLC or an S corp?" does not parse, and saying why is the
most useful paragraph on the page. That sentence is the reason this is one page
and not two. The firm floated a separate page on what and why an LLC; splitting
them would put the two ideas on two pages and lose the only thing worth saying,
which is that they are not the same idea.

## Why it is not four pages

Same argument as the records split, running the other way. There the two
subjects were genuinely different and had to separate. Here the two subjects
*look* different to a reader and are the same subject, so they have to stay
together. One page each remains the ceiling.

## The section it was written for

**05 · Reasonable compensation.** Everything before it is setup and everything
after it is consequence. People elect for the self-employment tax saving and
meet the wage requirement afterwards, and `assumed.officer_compensation` in
`fee-schedule.yaml` puts setting or reviewing that figure outside the flat
engagement. The guide explains what the number is and why it is not optional,
and names none.

That closes a gap the second guide left open. `good-records-business.md` says
nothing about what an owner pays themselves and flags the silence, on the
grounds that an S corp owner searching the phrase is exactly who would find the
page. This page is where that reader lands instead.

## The honest half

A page that lists only reasons to elect is marketing, so section 07 is the
cases where the answer is no: profit too small for a reasonable wage to leave
anything, one owner who wants one return, a business raising outside money that
cannot have an ineligible shareholder or a second class of stock, a company
holding rentals that had no self-employment tax to save, and losses funded by
company borrowing that gives a shareholder nothing to deduct against. Section
08 says the election is hard to undo.

## What was deliberately left out

- **Every figure that resets each year** — the self-employment rate, the Social
  Security wage cap, the late-filing penalty per owner, the Ohio filing fee.
  The page describes each mechanism instead, so nothing on it goes stale on
  1 January.
- **Any number an owner should pay themselves**, and any method for reaching
  one.
- **Prices, including ours.** Same rule as the other two.
- **C corporations.** On the Businesses tab, off this page. It exists to
  separate two things a reader has already tangled.
- **Late-election relief.** A reader who has missed the deadline needs a
  person, and naming relief makes the deadline read as soft.
- **State pass-through entity elections.** A page's worth of material on their
  own; half of it would be worse than none.
- **The S corporation health insurance rule.** It is in the business guide.
- **A named upload route.** Per the firm: no reason to name it on the site.

## What is new against the other two

**It carries a not-advice line.** Open item 4 in `SOURCES.md` left that
question for the firm and the firm has since answered it — a short, plain,
generic one, kept out of contract-desk register. The sentence written is *"This
is general information, not advice about a particular business."* Two things
follow. The wording is not the firm's, so it is flagged. And if it stays, the
other two guides should carry the same sentence word for word, because two
things doing the same job have to look identical.

## What needs a human before this goes up

Seven `[CONFIRM:` markers, listed in full at the foot of
`SOURCES-entity-choice.md`, three of them in the draft itself. The one that
blocks publication is the same one that blocks the other two, and it is worse
here: **no primary page was opened.** `irs.gov`, `tax.ohio.gov`, `ecfr.gov`,
`law.cornell.edu` and `ohiosos.gov` are all blocked from this container. The
records guides describe what a document is and when it arrives. This one
describes an election that takes five years to unwind.
