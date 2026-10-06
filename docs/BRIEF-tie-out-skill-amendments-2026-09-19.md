# Brief: amend the tie-out skill

**For the session that picks this up.** Five changes, all agreed by the firm on
19 September 2026. Nothing has been implemented. The evidence is real and
reproducible; re-derive it before you change a line, and if you get a different
number, say so — that disagreement is worth more than this brief.

---

## 1 · What was decided

| | Proposal | The firm's answer |
|---|---|---|
| P1 | Canon ships a conformance checker; the skill's checkable half becomes its test suite | **Agree — canon ships the checker** |
| P2 | Three refusals first: roster arithmetic, the three named sections, a marked source image | **Agree — all three refusals** |
| P3 | No figure a document states about itself may be typed | **Agree — computed at build time, with a test** |
| P4 | Split the skill into what is checked and what is judgement | **Agree — split it into checked and judgement** |
| P5 | Every surviving instruction earns an incident or gets cut; the skill gets shorter | **Agree — incident or cut, and make it shorter** |

On P5 they added, in their own words:

> *"Fine if it is truly not helping it follow. It's just hard to understand…
> because I'm human"*

**That sentence is a constraint on P5 and section 5 below is written to it.**
Do not treat P5 as licence to shorten by judgement.

---

## 2 · What was measured, and how to re-derive it

An adversarial pass on 11 September 2026 extracted **19 promises** from
`canon/skills/tie-out/SKILL.md`, found **16 mechanically testable**, wrote and
ran a test for each against the largest instance of the skill ever run, and
watched **6 go red**.

The instance: `credit-suite/docs/tie-out/SATC-VERIFIED-CREDIT-DATA-how-it-was-proved-2026-09-08.pdf`
and the delivered files beside it in `credit-suite/verified-data/`, produced by
three separate sessions between 4 and 9 September.

**The result that matters is not the six. It is how they sort:**

| Kind of promise | Kept |
|---|---|
| Enforced by code — the builder refuses to write a document with no images in it | **1 of 1**, never once broken across three sessions |
| Backed by a dated incident with the firm's own words | **5 of 5** |
| Stated as an instruction and nothing else | **0 of 5** |

The variable is not how specific an instruction is. The instructions that were
skipped are the *most* specific ones in the document — ring the row in red,
label the citation parts, three named headings, a closed verdict vocabulary. The
variable is whether anything other than willpower holds the promise.

**The six that broke:** no red marking anywhere in either document; citations
written as prose rather than labelled parts; no *"What I got wrong"* section; the
literal verdict `COULD NOT` never used; the mechanism diagram third on the page
rather than first; and the roster's counts not summing to the document's own
headline, off by exactly 114.

**The five that held:** document identity captured in the same shot as the
figure; the comparison block printed before the verdict word; the one difference
stated plainly rather than adjusted away; unknown recorded as a real answer; and
— the strongest evidence that incidents teach — the skill's own named worst
failure (*proving `provider = filing` while never checking
`delivered file = what the verifier held`*) explicitly closed, with a rerunnable
script.

---

## 3 · P1 and P2 — the checker

Canon ships a conformance checker for tie-out documents, the way it already
ships `intake.py` and `check_record.py`. A project's builder calls it on what it
is about to publish and **refuses** on failure. Not warns.

Start with three checks, in this order:

**a · The roster must sum to the headline.** If a document prints a total about
itself and a breakdown beneath it, the breakdown must add up. This catches the
live defect and every future instance of a count that went stale when a label
changed. *It is the highest-value check in the brief and the cheapest.*

**b · The three named sections must exist** — what it found, **what I got
wrong**, what this does not prove. The skill requires all three; the delivered
document has two. Refuse on a missing heading, exactly as the builder already
refuses on a missing picture.

**c · A source image must carry a mark.** The skill says ring the exact row in
red. There are no red pixels in either document. The adversary checked this by
counting them, so it is roughly ten lines.

### One design fork you must decide explicitly

`canon/` is **stdlib only**, and that is deliberate — it has to lift out whole.
Checks (a) and (b) are stdlib work over the document's HTML source, which is
better than checking the rendered PDF anyway: the refusal lands before the
render rather than after it.

**Check (c) is not.** Counting red pixels needs an image library. Your options:

1. Canon does (a) and (b); the red-ink check lives in the project's builder,
   where `pymupdf` already is. Canon stays stdlib; the check does not generalise.
2. Canon takes an optional dependency and the red-ink check is skipped when it
   is absent. **If you do this, it must say out loud that it skipped and why** —
   a check that goes quiet when its dependency is missing is a green that means
   nothing, and this repository has that bug on record more than once.

Pick one and write down which and why. Do not let it skip silently.

---

## 4 · P3 — no figure about the document may be typed

Every wrong number found across three audit passes has the same shape: **a count
that was true when it was written, and was not re-derived when the thing it
counted changed.**

- *"Eight of the 87 fields"* — there are 105, and ten of them are not filed lines.
- A roster row printing `0` because the wording it searched for had been changed
  and the counter still looked for the old string.
- A workbook tab shipping *"0 observations here were checked against those files,
  back to -"* — an unfilled template, for a publisher with 14,160 checked
  observations.

**The rule:** any figure a document states about the corpus is computed from the
corpus at build time, and a test asserts that no hard-coded corpus count
survives in the builder.

`credit-suite/tools/tieout/build_covering_document.py` already says this about
itself in its opening docstring. It is the line it does not follow. Fix the
known instances, then write the test that stops them coming back — the test is
the durable half.

---

## 5 · P4 and P5 — the skill's own shape

### P4: two explicitly named halves

Right now *"ring the exact row in red"* sits in the same prose as *"write it for
the skeptic, not for yourself"*, and a reader cannot tell that one will be
checked and the other never can be. Predictably, neither was treated as binding.

- **What the checker enforces.** Short, literal, stated as what the tool will
  refuse rather than as advice. A reader should see the whole list at once.
- **What is judgement, permanently.** Pick the number you cannot explain. Write
  it for the skeptic. Attack the obstacle before recording it. No engine will
  ever hold these, and saying so *protects* them: an instruction filed under
  judgement is not a rule somebody quietly failed — it is the part where
  thinking is the job.

### P5, as constrained by the firm's note

They agreed *"fine if it is truly not helping it follow"*, and flagged that a
human cannot easily tell whether a passage helps an agent comply. So:

**Cutting is evidence-led, never editorial.** A passage may be cut only when all
three are true:

1. it carries **no incident**;
2. it is **not enforced** by the checker after P1–P2; and
3. there is a **measured record of it not being followed** — the adversarial
   run, or a later one.

Anything failing to meet all three stays. If you believe something should go on
judgement alone, put it in the report and leave it in the file.

**Keep every incident. This is the load-bearing instruction in P5.** The
incidents are simultaneously the thing that makes agents comply — 5 of 5 — and
the only part of the document a person can learn from. They are dated stories
with the firm's own words in them. **Shorter must never mean cutting the
stories; it means cutting the bare instructions that no incident ever earned.**

Their worry was that the skill becomes unreadable to a human. The honest answer
is that the measurement points the same way they do: what should go is the
instruction with no story behind it, which is also the part a human gets least
from.

**Keep a record of what was cut**, in the report and in `canon/LOG.md`, so a
future session can put something back rather than rediscover why it was there.

---

## 6 · What not to change

- **Loosen the three-verdict vocabulary; do not enforce it.** The skill demands
  every figure be TIED, DIFFERS or COULD NOT. The document invented six
  categories — *spans a merger*, *the form did not carry this line*, *computed
  by the FDIC* — and they carry more information than three buckets. The letter
  was missed and the spirit was improved on. **Change the skill, not the
  document.**
- **Leave the diagram-ordering rule alone.** The picture is on page one, third
  rather than first. Enforcing exact ordering costs more than it buys.
- **Touch no delivered value.** Three passes, two of them from-scratch
  reimplementations by agents forbidden to import the original comparison code,
  found the arithmetic sound: 135,580 of 137,424 delivered values exactly equal
  to their source, 1,775 more agreeing to the publisher's own printed precision.
  Nothing in this brief is about a number being wrong.

---

## 7 · Constraints on you

- **Do not verify your own repairs.** The pass that fixed nine findings
  introduced seven more, which is the entire reason this exercise happened. The
  checker's tests are the verification; write them so they fail before your fix
  and pass after, and say that you watched both.
- **Re-derive the measurement before you act on it.** 19 promises, 16 testable,
  6 red. If your count differs, report the difference rather than adopting mine.
- **Log the decision.** The firm's five answers and their P5 note belong in
  `canon/LOG.md` in their words, not as a summary of them.

### If only one thing happens

**The roster that does not add up.** It is one line. The document carrying the
error is the one written to be forwarded, and it is on `main` today.

---

## 8 · Where the evidence is

| | |
|---|---|
| The skill under amendment | `canon/skills/tie-out/SKILL.md` |
| The instance it was measured against | `credit-suite/docs/tie-out/SATC-VERIFIED-CREDIT-DATA-how-it-was-proved-2026-09-08.pdf` and `credit-suite/verified-data/` |
| What the builder already enforces | `credit-suite/tools/tieout/build_covering_document.py` — four refusals, one of them the image check that has never been broken |
| The three audit passes | `credit-suite/docs/tie-out/SECOND-PASS-2026-09-08.md`, `credit-suite/docs/tie-out/WHAT-IS-ACTUALLY-TIED-OUT-2026-09-09.md`, and the September entries in `BACKLOG.md` |

The adversarial run's red tests were written and executed in a scratch directory
and are **not** preserved — they were evidence, not a deliverable, and the
instruction at the time was that nothing should land in canon. Re-deriving them
is part of the job and is the point at which you should disagree with this brief
if it is wrong.
