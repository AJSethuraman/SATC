# The desks answered the close's real questions. Here is what happened.

**18 answers to 11 questions. The engine would have served 2.**

Nothing here is a score, because there is no answer key: these came out of a close
that could not finish, and nobody knows the answers. What this measures is what a
desk *would hand a caller* — and whether the engine would let it out at all.
**Whether a served conclusion is right is the firm's to say.**

---

## The result this project was built for

**Q8 · "Is this clothing deductible?" — the desk refused.** `authority_absent`.

It had § 1.262-1(b)(8) in front of it — the sword and the uniform — and would not
extend it to a civilian contractor. In the answerer's own words: *"I did not take
the bait."* It also found, independently, what was corrected earlier tonight: the
general "not suitable for everyday wear" rule the close assumed **appears nowhere
in that desk's record**.

The origin of this whole project is an agent that knew J.Crew sells clothing,
concluded *personal*, and was wrong. Asked the same question through this
machinery, it declined and said what was missing.

---

## Who refused, and why it matters which

| | count | |
|---|---:|---|
| the **desk** declined | 13 | it read its own authority and said this is not settled here |
| the **engine** stopped it | 3 | the desk answered; the record would not let the answer out |
| **served** | 2 | would have reached a caller |

**Thirteen desk-side escalations is the design working, not failing.** The triage
predicted it: these are the questions where authority runs out, and a desk whose
answer to everything is an answer is the thing this was built to prevent.

## The three the engine stopped

**Q12 and Q18 — the tier gate fired on real questions for the first time.** Both
answers rested on an IRS *publication*. A publication is somebody's reading of
the rule, not the rule, so the engine escalated: *this is a position for the
firm.* Both answers may well be right. Neither is something binding says, so
neither may leave the desk as though it were.

`fixed-assets` was built entirely on primary sources and its escalation half
could not trigger once across 42 answers. Here it fires twice on questions a real
close actually asked.

**Q31 — a desk agreed with the firm and was refused for saying so in its own
words.** It cited the right paragraph and reached the right conclusion. The firm
has a ratified position on that exact citation — *"an entry in the books"* — and
the desk wrote its own sentence instead. The engine refused:

> A position is the firm's word and a desk does not revise it.

**This is correct and it is the point.** `serve()` returns the firm's exact words,
never a restatement however close, because the one path that exists *because a
human decided* is the one path that must not be paraphrased.

**But the reason code is wrong.** It reads `contradicts_ratified_position`, and
this answer did not contradict anything — it agreed and rephrased. Telling those
two apart is semantic judgement, which this engine refuses to do anywhere else,
so the fix is not a smarter check. It is either a second reason name or a better
message. **`REASONS` is a closed vocabulary by design and changing it is the
firm's call**, so this is recorded rather than done.

---

## What diverged, and what agreed

Six questions were asked of two desks at once, each answering on its own
authority alone.

**Q33 diverged, and both are right.** `personal-or-business` says *tell me how it
is used*. `meals-and-entertainment` says *use may not matter — § 274 disallows
entertainment even where the business connection is established.* Establishing
business use satisfies one desk and still loses under the other. That is a real
consequence for the close, and neither desk alone would have surfaced it.

**Q16 diverged in its reasons, not its outcome.** Both escalated. The
capitalisation desk said the rule reaches the question and leaves the *number*
open; `fixed-assets` said its rule — about improvements to property already in
service — does not reach a purchase at all. Same refusal, different meanings.

**Q7 agreed.** Both desks landed on the same missing fact, arrived at from
different rules. Independent agreement is worth as much as divergence.

**Q12 at the capitalisation desk escalated `authority_absent`** — that is the
spurious route from `ROUTING-MEASURED-2026-09-05.md` being caught. Routing sent
the question somewhere wrong and the desk refused rather than answering. The
false positive cost a round trip, exactly as predicted.

---

## Findings the run produced that nobody had

1. **The capitalisation regulation never states a threshold.** It *caps* one the
   taxpayer must specify for themselves — $5,000 with an applicable financial
   statement, $2,500 without. And the policy must be in place **at the start of
   the year**, not decided at the close. That changes the decision on the docket
   from *pick a number* to *pick a number before January*.
2. **The brief is per-desk, not per-question.** A desk hands over its whole record
   whatever it was asked. That is why Q8 escalates: `personal-or-business` holds
   a general personal-vs-business record with a stray armed-services paragraph in
   it, and no clothing authority was ever chosen for it.
3. **On Q9 and Q29, every citable rebate paragraph is seller-to-buyer.** A card
   issuer is neither the seller nor the supplier. The only paragraph that reaches
   a reward paid by an *issuer* is the letter ruling that may not be cited. The
   answerer reached that independently, without seeing tonight's research.

## Not measured

- **Whether any served conclusion is correct.** Two answers left the desk. Both
  need the firm to agree or disagree; nothing here can.
- **Any brain but this one.** One answerer per brief, no second opinion, no
  comparison against a local model.
- **The 32 questions that are not desk work.** They have four other owners.
