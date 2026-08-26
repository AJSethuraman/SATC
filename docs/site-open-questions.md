# Things the site must figure out — notes, not decisions

**Whose file this is.** The website is not mine to decide. The firm said so on
26 August 2026:

> stop making website decisions. Let me handle that with the other agent. You
> can note things we must figure out for the site

So this is a list of things I found while working on the **fee schedule** that
someone building the site will hit. Every entry says what is true in
`client-documents/registry/fee-schedule.yaml` and what that leaves open. None
of them says what the page should do.

**The one rule worth repeating**, because it is the site's own and it is
right: the schedule is the source of truth, and anything unverifiable against
it does not go up. `website/pricing.spec.py` enforces that. Everything below is
a place where the schedule and the published prose currently disagree, or
where the schedule is about to move under the page.

---

## 1. The two prose-only prices are now real — RESOLVED 26 August 2026

`docs/pricing-for-website.md` §2 listed an **amended return at $250** and an
**extension with a payment estimate at $75**, and neither existed anywhere in
`fee-schedule.yaml`. The checker caught that and kept both off the page, which
was the correct outcome and is how it was found.

**Both are now in the schedule**, at those prices, on the firm's answer to
round eleven. So both are publishable where they were not before, and the
checker will verify them rather than block them.

Two details that matter if either goes up:

- The amended return is **individual only**. An amended entity return has no
  price; a page implying otherwise would quote something the firm has not set.
- The extension's **filing is free** — only computing the payment is billed.
  A tile reading "Extension — $75" says the opposite of the decision.

## 2. The foreign-account cap is SOFT, and the page says it is hard

**Changed 26 August 2026 and this one is live.** The firm confirmed four and
then qualified it:

> 4 is a soft cap. Then we add dollars for time

The schedule now carries `cap_beyond: hourly` alongside `cap_units: 4`. The
per-account charge still stops at four; the time past it does not. Every
estimate now says so on the line.

**The price page says "capped at four" and nothing else** — correct when it
went up, and now half the sentence. A visitor reads a promise the firm is not
making, which is the failure direction that costs trust rather than money.

The checker will not catch this: it compares published numbers against the
schedule, and the number is still four. It is the qualification that changed.

**Not fixed here.** What the page should say is wording a client reads, and
the site is not mine. Flagged the same day it changed.

## 2b. The cap of four itself (the original note, still true)

`per_unit.foreign_account` carries `cap_units: 4` — past four accounts the line
stops climbing. It was set on 26 August 2026 and the schedule records the
reasoning. The prose brief never mentioned it; the page published it.

Publishing it is the client-favourable reading and it matches the schedule, so
nothing is wrong. But the cap is **four days old and was chosen against a firm
instruction that did not name a number** ("a cap — nothing huge though"). A cap
is much harder to lower once it is on a public price page than while it is only
in a YAML file.

**Confirmed 26 August 2026.** Four is the firm's number. See §2 above for what
changed alongside it.

## 3. Package names are still moving, and one is disputed

All four package names are unsettled, and **"Business" specifically** is on the
open list. It is a **1040** package — $500, covering "one full Schedule C
business" on top of everything in Standard — and the name invites a
partnership or S-corp owner to think it is theirs. The entity returns are
`base.1065`, `base.1120S` and `base.1120`, and none of them is called
Business.

Rendering names from `pricing-config.js` rather than hardcoding them into
headings and anchors was the right call and it is what makes a rename cheap.
Worth keeping that property until the names are signed off.

**What is not yet settled:** whether a renamed package needs a redirect from
its old anchor, if any of these names have been shared with a real prospect.
Nobody has checked whether they have.

## 4. Three things are priced and deliberately not advertised

The schedule prices them; the page withholds them, each for a stated reason:

| Withheld | Why, per the schedule |
|---|---|
| The farm schedule ($200) | Settled 26 Aug 2026 — the firm **takes** farm work and does not **advertise** it |
| Records sorting ($175) | A floor a preparer sets, not a price — and it is a charge for the client's own untidiness |
| Every entity return figure | The page says "quoted after a conversation" instead |

These read as sound judgements to me and the checker enforces them. Recorded
because **the reasons are agents' reasons, not the firm's** — as far as I can
tell only the farm one carries a firm decision. If the firm disagrees with any
of the other two, the page and the checker both change together.

## 5. The estimate/quote distinction is load-bearing and is a wording question

An estimate that turns into a bigger invoice now refuses to go out without a
variance note — that is real, tested, and it is the strongest thing the firm
can say about its prices. How much of that guarantee the page should claim is a
wording decision, and wording that reaches a client is the firm's.

**What I can confirm for whoever writes it:** the mechanism exists, it is
enforced in `invoicing.py`, and a bill over the estimate is refused rather than
sent. What that sentence should say, I have not written.

## 6. Prices will keep moving while the open threads are open

`docs/pricing-open-threads.md`, after round eleven, has these live entries
that can still change a published number:

- **T-11** — capturing the processes themselves.
- **T-18** — the time capture, newly scoped. Nothing published depends on it
  today, but it is the thread that would eventually justify or move a price by
  effort rather than by market survey.
- **T-19** — the $500 package's name.

T-07 (nobody knows how long anything takes) was **answered** on 26 August and
became T-18. T-16 and T-17 are **closed** — see section 1.

T-15 (Property & Business against rentals) and T-14 (a priced boundary the
estimate could not state) were both **found to be already settled** on 26
August while writing this file — their status lines were stale. Mentioned
because it cuts the other way too: a thread reading "Open" here may already
have been built.

**The maintenance question the site already answered well** — *"does the page
still match the schedule?"* — is `cd website && python3 pricing.spec.py`. The
thing worth adding to somebody's checklist: run it after any change to
`fee-schedule.yaml`, not only after a change to the site. The drift will
usually start on my side.


## 7. The firm wants entity prices on the page, and they are currently withheld

Answering round eleven, on the package-name question:

> The site also needs to have tiles for actual business return prices like
> 1120S

The schedule prices all three — `1065` at $800, `1120S` and `1120` at $950 —
and the page deliberately withholds them in favour of "quoted after a
conversation" (§4 above). So this is not a gap to fill; it is a **reversal of a
decision currently in force**, and the checker enforces the current one.

**Two things have to happen in order**, and neither is a site call:

1. The firm decides the entity prices are published prices rather than
   starting points for a conversation. That is the decision §4 records as an
   agent's reasoning rather than the firm's — worth settling explicitly now
   that it is being reversed.
2. The withholding rule and its check come out together, or the page fails its
   own checker.

Worth flagging plainly: **a published entity price behaves differently from a
published individual price.** The four packages are gated on what is on the
return, so the price a visitor reads is the price they get. An entity return is
not gated that way — $950 is a base, and the balance-sheet and reconciliation
work sits on top of it. A tile saying $950 will be read as the total.

## 8. The package name may change, and the amended-return price is new

Two smaller things from the same day:

- **T-19** proposes renaming the $500 "Business" package (it is a 1040 package;
  a partnership owner could read it as theirs). Names still render from config,
  so a rename is one line — while that holds.
- **The amended return is now priced** at $250 and lives in the schedule, so it
  is publishable where it was not before. Whether it belongs on the page is a
  site call. Note it is scoped to the individual return: an amended entity
  return has no price, and a page that implies otherwise would be quoting
  something the firm has not set.
- **The extension is now priced** at $75, with the filing itself free. Same
  status: publishable, and the free/priced split is the part that would need
  saying carefully if it goes up.
