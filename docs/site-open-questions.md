# The site: what to change, and what is still open

**Read this first.** As of 26 August 2026 this file has two halves, because
the firm's instruction changed during the day.

It started as notes only — *"stop making website decisions. Let me handle that
with the other agent. You can note things we must figure out for the site."*
Then, once round twelve was answered:

> answers saved - we can instruct updates to the website before it is live

So **Part A below is instructions**: firm decisions, already in the fee
schedule, that the page must reflect before it goes live. They are not
suggestions and they are not mine — each one names the decision behind it.

**Part B is still notes**: things nobody has decided, where the page should
not get ahead of the firm.

Neither half is me editing the site. `website/` is the other agent's, and
`website/site-config.js` is nobody's without sign-off.

---

# Part A — changes to make before the page goes live

Every item here is a firm decision recorded in
`client-documents/registry/fee-schedule.yaml`. If the page and the schedule
disagree, the schedule is right — that is §4 of the pricing brief and the
site's own checker enforces it.

## A1. The $500 package is now "Self-Employed", not "Business"

Settled 26 August, round twelve. It renders from `pricing-config.js`, so this
is the one-line change that the config indirection was built for.

The reason matters for the copy around it: **it is a 1040 package.** The old
name invited a partnership or S-corp owner to buy a personal return. Anything
on the page that reinforces that reading should go with the name.

## A2. The foreign-account cap is SOFT and the page says it is hard

The page says **"capped at four"**. That was correct when it shipped and it is
now half the sentence. The schedule carries `cap_beyond: hourly`: the
per-account charge stops at four, the time past it does not.

The estimate now says both. The page says one. A visitor reads a promise the
firm is not making — the direction that costs trust rather than money.

**The checker will not catch this.** It compares published numbers against the
schedule and the number is still four; it is the qualification that changed.

The schedule's own sentence, for reference rather than to copy verbatim —
page wording is the firm's:

> capped at 4 — beyond that the additional time is billed at $150 an hour as
> it is worked, and we will tell you as soon as we see it

## A3. Entity prices go up as **from** prices, with their notes

Reversed 26 August, round twelve: *"definitely a from price - prevents people
from wasting my time squeezing value but it should also be fairly clear that
these are starting points and maybe some very light notes indicating what
'starting' means."*

So the three entity returns may now be published, **as from prices only**:

| Return | From |
|---|---|
| Form 1065 — partnership | $800 |
| Form 1120-S — S corporation | $950 |
| Form 1120 — C corporation | $950 |

**Each number must carry its `starting_note` list**, which is in the schedule
beside the amount precisely so the two cannot drift apart. Read them from
`base.<form>.starting_note` rather than retyping them. Today they are: a
balance sheet where one is required; inventory where the business carries any;
each owner's K-1 after the first two (1065 and 1120-S only); returns in more
than one state.

**The distinction that makes this safe.** The four 1040 packages are *gated* on
what is on the return, so the price a visitor reads is the price they get — a
flat price, honestly. An entity base is not gated that way. A bare $950 on a
tile is read as a total, and it is a floor. The schedule marks this explicitly:
`publish: from` on the entity bases, and a test asserts the packages are **not**
from-prices, so the two cannot be shown the same way by accident.

## A4. Two newly-priced items are now publishable

Both were in the prose brief with no home in the schedule until 26 August, so
the checker correctly kept them off. They are real now:

- **Amended return — the package price plus $50**, every form. Not a flat
  number, so the page cannot print one: an amended Essentials return is $250
  and an amended 1120-S is $1,000. "Amendments are priced at $50 on top of the
  return's own fee" is the honest one-liner.
- **Extension with a payment estimate — $75.** **Filing an extension is
  free** — only computing the payment is billed. A tile reading
  "Extension — $75" says the opposite of the decision.

Whether either belongs on the page is still a site call. The constraint is
that if they go up, they go up with those qualifications.

## A5. Re-run the checker after schedule changes, not only after page changes

`cd website && python3 pricing.spec.py`. Worth adding to somebody's checklist:
the drift will usually start on the pricing side, which is where three of the
four items above came from.

---

# Part B — still open, do not get ahead of these

Nothing here has been decided. The page should not imply an answer to any of
it.

## B1. ~~The amended entity return~~ — CLOSED 26 August 2026

Settled: an amendment is **+$50 on whatever the return is**, every form. So an
amended 1120-S is $1,000 and an amended Essentials return is $250. It is
publishable (`amendment.publish: "yes"`), and the individual/entity split that
made this a gap is gone.

## B2. Two things stay priced and unadvertised, on reasoning nobody has signed

| Withheld | The stated reason |
|---|---|
| The farm schedule ($200) | The firm **takes** farm work and does not **advertise** it — settled 26 Aug, a real firm decision |
| Records sorting ($175) | A floor a preparer sets, not a price, and it is a charge for the client's own untidiness |

The farm one carries a firm decision. **The records-sorting one is an agent's
reasoning**, and it reads as sound to me, which is not the same as being the
firm's. Worth settling explicitly rather than inheriting — the entity
withholding rule was in exactly this position until round twelve reversed it.

## B3. How much the page claims about the estimate-to-invoice guarantee

An estimate that turns into a bigger invoice now refuses to go out without a
variance note. That is real, tested and enforced in `invoicing.py` — a bill
over the estimate is refused rather than sent.

It is the strongest thing the firm can say about its prices. **How much of it
the page should claim is wording a client reads**, so it is the firm's
sentence, not mine and not the site's. I can confirm the mechanism; I have not
written the claim.

## B4. Prices can still move while these threads are open

In `docs/pricing-open-threads.md`:

- **T-11** — capturing the processes themselves.
- **T-18** — the time capture, scoped and not started. Nothing published
  depends on it, but it is the thread that would eventually justify or move a
  price by effort rather than by market survey.

Everything else on that list is closed as of 26 August. The schedule now has
**no unpriced item and no unanswered decision** — `doctor` reports clean, and
a test holds it that way.

## B5. Nobody has checked whether a package name has already reached a prospect

Raised when "Business" was renamed and still unanswered. If one of the four
names has gone out to a real person, a rename stops being free and becomes a
migration. Cheap to find out, and only the firm can.

## B6. Two facts the interview asks about that the intake form cannot express

Found 26 August 2026 while rebuilding the interview to ask about a client's
year rather than about schedules.

**The good news first: the two now share a vocabulary.** `individual_complexity`
on the intake form and `return_features` in the interview ask the same question
in the same words with the same option values, so a website answer prefills
directly. Until today it did not: the interview translated through a map whose
keys had drifted — it expected `rental`, `self_employed`, `sole_prop`,
`brokerage` and `itemize`, and the site has never sent any of the five. **A
prospect who ticked "Rental property" prefilled nothing.** Only `k1` and
`investments` ever matched. A test now holds the two lists together.

**The gap that is left** is two options the interview offers and the site does
not ask about:

| Interview option | What it means | On the site? |
|---|---|---|
| `farm` — "Farming" | Schedule F, and Schedule SE with it | No |
| `itemizing` — "Mortgage interest, large medical costs or significant charitable giving" | Schedule A | No |

Both change the price. A farm is a priced form; itemising is what separates the
**Essentials** package from **Standard**. A prospect with either gets a quote
built without knowing about them, and the preparer finds out on the call.

**This is the site's call, not mine.** Adding two options to
`individual_complexity` would close it; so would deciding that these are
genuinely call-only facts and the estimate is expected to move. Either is
defensible — what is not defensible is nobody knowing the gap is there.

The interview does not force it closed from its side: the test asserts that
every value the *site* sends is one the interview understands, and treats the
reverse as a note.
