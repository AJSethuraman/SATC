# Prompt for Claude Design

Paste this along with the four attached files.

---

I need help with the layout and look of a pricing page. Four files attached:

- `pricing-individuals.html` — the page as it opens
- `pricing-businesses.html` — the same page with the other tab showing
- `home.html` — our existing home page, for the shell, nav, type scale and palette
- `README.md` — the constraints

**Who we are.** SAT-C LLP, a small accounting and tax firm in Ohio. The site is
deliberately plain: IBM Plex throughout, navy and a cool off-white, oxblood for
anything you click, gold only as hairlines and rules. `home.html` is the look I
want this page to belong to.

**What the page is for.** Most tax firms make you book a call to find out what
you'll pay. We publish our numbers instead, and that transparency is the whole
point of the page. A visitor should be able to find their own situation and see
a real price in a few seconds.

**Two audiences behind a switch.** Individuals get four packages. Businesses get
three entity returns. They are priced on different principles and that
difference has to stay visible — see the README, it is the one thing I care most
about not losing.

**What I want from you.** Make it look considered. The current version was built
to be correct, not finished — the cards, the grouped rows and the tab strip are
all first-pass. Specifically:

- The four cards are uneven; the shortest has two bullets and the tallest has
  five, and it shows.
- The extras table is a long list of rows and gets monotonous.
- The switch is a plain segmented control and does not look like it belongs to
  the rest of the site.
- The whole page is one column of stacked sections; I suspect it wants more
  structure than that.
- Phone layout has had almost no attention.

**Constraints, in the README.** Read it before proposing anything — eight items,
each a decision already made, and they are enforced by a test that runs in CI so
breaking one fails the build.

**Please do not rewrite the copy.** Several sentences are exact wording arrived
at over a lot of rounds. If a layout needs different words, say so and I will
get them changed rather than you changing them.

**Give it back as HTML I can diff** — keep the existing `id` and `class` names
where you reasonably can. The live page fills `#tiers`, `#entities`, `#extras`,
`#sits`, `#hourlyApplies` and a few others from a config file at load, so those
hooks need to survive even though the attached files have the content baked in.
Package names in particular are data, not markup, on the real page.
