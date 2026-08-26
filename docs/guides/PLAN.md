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
