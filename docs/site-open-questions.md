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

## 1. Two prices in the prose brief do not exist in the schedule

`docs/pricing-for-website.md` §2 lists an **amended return at $250** and an
**extension with a payment estimate at $75**. Neither is anywhere in
`fee-schedule.yaml` — not a base, not a per-unit line, not one of the eight
per-form situations.

The checker already caught this and kept both off the page, which is the
correct outcome. Recorded here because the fix is not a site fix: it is
**T-16** and **T-17** in `docs/pricing-open-threads.md`, both open, both
waiting on the firm. If they get priced, they become publishable; if they get
struck, §2 of the prose brief is what changes.

**What the site should not do meanwhile:** infer either number from the prose.

## 2. The foreign-account cap of four is now public

`per_unit.foreign_account` carries `cap_units: 4` — past four accounts the line
stops climbing. It was set on 26 August 2026 and the schedule records the
reasoning. The prose brief never mentioned it; the page published it.

Publishing it is the client-favourable reading and it matches the schedule, so
nothing is wrong. But the cap is **four days old and was chosen against a firm
instruction that did not name a number** ("a cap — nothing huge though"). A cap
is much harder to lower once it is on a public price page than while it is only
in a YAML file.

**Flagged so the firm confirms the number, not so the page changes.** It is
question 4 of pricing round eleven.

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

`docs/pricing-open-threads.md` has four live entries that can change a
published number:

- **T-07** — nobody knows how long anything takes. Blocks the automation
  argument and any defence of a price by effort.
- **T-11** — capturing the processes themselves.
- **T-16 / T-17** — the two in section 1 above.

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
