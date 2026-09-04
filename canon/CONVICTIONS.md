# Convictions — what the firm believes, and why

**How this file works.** Each entry carries the firm's **own words**, the reason,
the date it was recorded, where it applies, and whether it is `held` or
`retired`.

**Nothing enters without the firm's yes.** Bassy drafts an entry quoting them and
asks. A conviction paraphrased is one they will disown the moment it is read back
at them — and a challenge built on a misquote does not merely fail, it teaches
them to ignore the next one.

**Nothing is ever deleted.** A conviction that stops being true is *retired*: it
gains a date and a reason, stops firing challenges, and stays readable. What the
firm used to believe, and why they stopped, is worth as much as what they believe
now — and it means nothing already settled gets re-litigated a year later.

**The challenge is the review.** There is no renewal queue and no annual audit.
A conviction is examined at the moment it bites, which is the only moment anyone
has the context to judge it.

**`Fires on`** is what makes selection deterministic: the subjects that bring a
conviction into play. Code narrows to candidates; the judgement of whether a
candidate is really a contradiction is made in the open, by a person reading.

---

## C1 · Working students are not charged what the work is worth

**State:** held · **Recorded:** 2026-09-03 · **Applies:** SATC pricing

> *you know the reasons I wanted to charge people less if they are themselves in college and working. I just don't think it's right to fuck them over, basically.*
> — the firm, 3 September 2026

**Why:** It is a judgement about who the practice is willing to make money from, not a pricing tactic. It costs revenue on purpose.

**Fires on:** student, students, college, discount, rate, pricing, fee schedule

**A challenge looks like:** a decision that raises the student rate, removes the distinction, or prices a working student on the standard schedule. Bassy names this entry, quotes it, and asks whether the reason has changed. It does not argue the economics — that is not what this record is for.

**How it could be wrong:** if the practice cannot cover its own costs, this stops being generosity and becomes a decision to close slowly. Bassy does not raise that unprompted. If the firm raises it, the resolution becomes a new conviction recording the trade-off — because how a collision is settled says more than either side of it.

---

## C2 · Nothing reaches the live domain without the firm's hand on it

**State:** held · **Recorded:** 2026-08-28 · **Applies:** everything

> *Never push to main: it publishes to the live domain satcllp.com through Cloudflare Pages.*
> — the firm, 28 August 2026

**Why:** A push to main is a publication. There is no review step between the commit and the public site, so the branch IS the control.

**Fires on:** main, push, publish, deploy, live, production, cloudflare

**A challenge looks like:** any move that would put work on `main`, or ship to production, without the firm having said so for that specific change.

---

## C4 · Some work is priced below what it costs, on purpose

**State:** held · **Recorded:** 2026-08-25 · **Applies:** SATC pricing

> *i want a package for college students where i'm fine operating at a "loss"*
> — the firm, 25 August 2026

**Why:** A price set under what the work costs, chosen rather than mispriced. It answers the question a margin review is about to ask: this line is not meant to pull its weight.

**Fires on:** loss, margin, profitability, unprofitable, break even, package, college, student, students

**A challenge looks like:** a decision that reprices, cuts, or justifies a package on the grounds that it does not earn enough. Bassy names this entry, quotes it, and asks whether the reason has changed. C1 is the sibling belief and both usually fire together; they point the same way, which is why a pair is no longer reported as a clash.

**How it could be wrong:** if the practice cannot afford the losses it is choosing, this stops being a choice and becomes a slow decision to close. Bassy does not raise that unprompted. If the firm raises it, the resolution becomes a new conviction recording the trade-off.

---

## C5 · The rule is publication, not the word "main"

**State:** held · **Recorded:** 2026-09-04 · **Applies:** SATC repositories

> *This conviction was really meant to stop it from pushing to the website live.*
> — the firm, 4 September 2026

**Why:** C2 is recorded as applying to everything and names `main`, so a session reading it literally treats every repository's `main` as sealed. Asked directly, the firm said the control is the publish path. This is the resolution of that collision, and it is worth more than either side of it: it says what the rule protects, so a repository whose `main` publishes nothing is ordinary work, and one wired to a live site is not — whatever the branch is called.

**Fires on:** main, push, merge, publish, deploy, live, production, cloudflare, pages

**A challenge looks like:** treating a branch name as the control in either direction — refusing a merge into a `main` that publishes nothing, or pushing to a branch that does publish because it is not called `main`. The question is what the target publishes, and it is answerable by looking: CI workflows, a Pages or hosting config, a domain.

**How it could be wrong:** if a repository gains a publish path later and nobody re-checks, this reads as permission that was never given. Check the target rather than remembering this entry — which is why the challenge names looking, not recalling.

---

## C6 · One brain ties up the information, another verifies it

**State:** held · **Recorded:** 2026-09-04 · **Applies:** Occam, and any AI doing the practice's work

> *an AI should be able to run the tools and stuff and prep everything for the review... it's really supposed to be the distinction between one brain has tied up the information and one brain has verified it.*
> — the firm, 4 September 2026

**Why:** It is the reason the permission layer exists, and until now only its consequences were written down — the AI cannot close a period, cannot contact the client. Those are conclusions. This is the premise, and it decides cases the conclusions do not cover: the test is not how dangerous a tool is, but whether the act is preparation or verification. Preparation is the AI's whatever it touches; verification is a second pair of eyes by definition, and a second pair of eyes that is the same pair is not one.

**Fires on:** review, reviewer, verify, approve, sign off, close, escalate, client, staff accountant, segregation

**A challenge looks like:** giving the preparer the verifying act — letting the AI approve its own work as a reviewer, close what it prepared, or take a question to the client — or the reverse, blocking the AI from preparation because the work is sensitive. It applies to a second agent as readily as to a person: the firm's words allow the verifier to be another brain, not necessarily a human one, and two agents sharing one context are one brain.

**How it could be wrong:** if the verifying pass is never actually done, this becomes a story the practice tells itself while the AI's work goes out unchecked. The separation is only real when somebody completes the second half.

---

## Not convictions

Proposals the firm read and said no to. They are kept for two reasons. The
miner surfaces the same passages every time it runs, and a thing that re-asks a
question you have already answered is a thing you learn to dismiss without
reading. And ids are never reused, so a declined proposal leaves a gap in the
sequence — a gap with no explanation is an invitation to fill it.

### C3 · declined 2026-09-04 · decisions-in-their-words.md · 2026-08-30 01:05:21

> *You shouldn’t ever touch the website itself. That is another agents job.*

**Not a conviction because:** it was a call about that week's pull requests, not a standing belief. The lane still holds as an instruction; it is not something the firm wants challenged from. Proposed 3 September 2026, declined the next day.
