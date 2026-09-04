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

**State:** retired · **Recorded:** 2026-09-04 · **Applies:** Occam, and any AI doing the practice's work

> *an AI should be able to run the tools and stuff and prep everything for the review... it's really supposed to be the distinction between one brain has tied up the information and one brain has verified it.*
> — the firm, 4 September 2026

**Why:** It is the reason the permission layer exists, and until now only its consequences were written down — the AI cannot close a period, cannot contact the client. Those are conclusions. This is the premise, and it decides cases the conclusions do not cover: the test is not how dangerous a tool is, but whether the act is preparation or verification. Preparation is the AI's whatever it touches; verification is a second pair of eyes by definition, and a second pair of eyes that is the same pair is not one.

**Fires on:** review, reviewer, verify, approve, sign off, close, escalate, client, staff accountant, segregation

**A challenge looks like:** giving the preparer the verifying act — letting the AI approve its own work as a reviewer, close what it prepared, or take a question to the client — or the reverse, blocking the AI from preparation because the work is sensitive. It applies to a second agent as readily as to a person: the firm's words allow the verifier to be another brain, not necessarily a human one, and two agents sharing one context are one brain.

**How it could be wrong:** if the verifying pass is never actually done, this becomes a story the practice tells itself while the AI's work goes out unchecked. The separation is only real when somebody completes the second half.

**Retired:** 2026-09-04

**Retired because:** It read as governing any automated act, including deterministic code, and misfired within a day of being recorded: Bassy pointed it at a scheduled disposal engine and asked whether the firm had abandoned the separation of duties. The firm: "this is really specific to Occam, maybe overstated... in this case, i think it is being misinterpreted." What it was reaching for is C7, which applies more widely but to divisions of work rather than to machinery. Where the line falls is C8.

---

## C7 · The context follows the role, and the reviewer carries the preparer's work

**State:** held · **Recorded:** 2026-09-04 · **Applies:** everything — any division of work between people or agents

> *generally speaking, i would want to have the appropriate context for a job... the reviewer is responsible, ultimately though, for what goes to the next level. they take responsibility for the bull shit that the accountant did - and they must know how to identify something to challenge, and manifest that into a question for the accountant to critically determine if it was the correct call.*
> — the firm, 4 September 2026

**Why:** This is what C6 was reaching for and stated too thinly as "two brains". The division is not headcount, it is **information**: the preparer knows the data that compiled the work more intimately, because that is their responsibility; the reviewer holds a different responsibility, for what goes up. Three things follow that a "second pair of eyes" framing loses. The reviewer answers for what the preparer did, so review is not advisory. The reviewer's output is a question back to the preparer, not a correction — the preparer is the one who decides whether the call was right. And the route runs both ways: the preparer must be able to send up what is, in the firm's words, "beyond their paygrade".

**Fires on:** agent, agents, reviewer, accountant, preparer, role, roles, context, responsibility, escalate, sign off, segregation

**A challenge looks like:** giving two roles the same context and calling the second one a review; a reviewer that silently corrects rather than asking; a design with no route for the preparer to escalate a decision above their authority; or a preparer handed context that belongs to the reviewer.

**How it could be wrong:** a reviewer starved of context cannot identify anything to challenge. "The context follows the role" can be used to keep the reviewer thin, and a reviewer who cannot see enough to ask a question is a rubber stamp wearing the title. The test is whether they could actually find the thing worth questioning.

---

## C8 · A deterministic engine is not a brain, and does not need a second one

**State:** held · **Recorded:** 2026-09-04 · **Applies:** the practice's software

> *this is meant to be an automated engine, which is deterministic. AI, in my view, assists in testing those engines by ensuring it can work in the real world*
> — the firm, 4 September 2026

**Why:** It draws the line C6 could not, and it was settled the moment C6 was misapplied: a challenge fired at a scheduled disposal engine on the grounds that one brain was both preparing and verifying. An engine applying a rule is not a brain making a judgement, so the separation has nothing to say about it. It also says what AI is *for* here — proving the engine survives contact with the real world, which is testing, not deciding.

**Fires on:** deterministic, engine, automated, automation, unattended, schedule, disposal, destroy, judgement

**A challenge looks like:** demanding human sign-off on every run of a deterministic process because its effects are serious, or the reverse — calling something an engine when a model is making the call. The test is whether a rule is being applied or a judgement is being made.

**How it could be wrong:** "deterministic" can be claimed for a process whose inputs are judgements. An engine fed a date somebody guessed is only as deterministic as the guess, and this entry would wave it through.

---

## C9 · The simplest answer is likely the best

**State:** held · **Recorded:** 2026-09-04 · **Applies:** everything

> *we are believes in occam's razor - the simplest answer is likely the best. at least that's how i paraphrase it.*
> — the firm, 4 September 2026

**Why:** The practice's software is named after it, and it was not on record. It is what the firm reached for when asked whether one configurable process should handle disposal rather than several — and it is the reason to prefer one script, one log and one schedule over a second mechanism beside the first.

**Fires on:** simple, simpler, simplest, complex, complicated, consolidate, duplicate, duplicates, duplicating, duplicated, duplication, redundant, rewrite, razor, second system, two systems

**A challenge looks like:** a design that adds a mechanism beside an existing one rather than extending it, or a configuration flag added because two cases were not reconciled. It is not an argument against necessary complexity — it asks whether the complexity was chosen. **The selector under-fires here, and that is worth knowing:** this entry is about the *shape* of a decision, while `Fires on` matches its *subject*. It catches a discussion that uses the vocabulary of simplicity; it will not catch "add a second script beside the first" unless somebody names it as duplication. Raise it by hand when a design adds rather than extends.

**How it could be wrong:** simplest is not fewest parts. Collapsing two things that genuinely differ into one — a backup rotation and a legal disposal, say — is the failure this entry could be used to justify, and C8 is the check on it.

---

## C10 · An agent runs on the Forge if it can, and is built to its role

**State:** held · **Recorded:** 2026-09-04 · **Applies:** agents, plugins and skills the practice builds

> *when we make an agent (in plugins or whatever), it would be preferable we can figure out how to make it work on ollama (though i know some stuff is hard to do on a limited model provided by the Forge) and it should really align with its role.*
> — the firm, 4 September 2026

**Why:** Two commitments in one sentence, and the firm named the cost of the first itself. **Preferably local:** an agent that only works against a frontier model is one the practice cannot run on its own hardware, and the Forge exists precisely so the work does not have to leave. **Built to its role:** an agent is made for a job — its tools, its context and what it refuses should follow from that job rather than from a title. C7 is why the second half matters; this is where it lands when something is actually being built.

**Fires on:** agent, agents, plugin, skill, ollama, local model, forge, role

**A challenge looks like:** an agent designed against a frontier model when the same job could be shaped to fit the Forge; or an agent given a role name whose tools and context do not match it.

**How it could be wrong:** forcing everything onto an 8B model produces an agent that does its job badly, and a bad agent that runs locally is worse than a good one that does not. The 8 GB ceiling on this box is real. This is a lean, not a rule, and the firm said so in the same breath.

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
