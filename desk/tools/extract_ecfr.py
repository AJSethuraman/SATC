"""Turn a section of the eCFR into a desk's problem set and stored authority.

WHY THIS IS A SCRIPT AND NOT PART OF THE ENGINE. This is the one place a live
fetch belongs: building the record. Once built, the engine grades against stored
text and never reaches out, which is what keeps CI deterministic and offline.

WHAT IT REFUSES TO DO. It does not invent a conclusion. An example whose outcome
is not stated in terms this desk can score is left out and counted, because a
problem set that quietly drops what it could not parse reports a denominator
that means nothing -- and that is the first tenet in `docs/SOFTWARE-TENETS.md`,
which exists because a proof artifact once declared 190 documents fine when
every one of them was unreadable.

Run:  python tools/extract_ecfr.py <reg.xml> <desk-dir>
"""
from __future__ import annotations

import re
import sys
import textwrap
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

#: HOW THE REGULATION ACTUALLY STATES A CONCLUSION, read off the corpus rather
#: than guessed at. Across § 1.263(a)-3's 117 examples, 112 sentences open with a
#: conclusion connective, and every scorable outcome in them is one of four
#: framings: "must capitalize" (22), "not required to be capitalized" (13), "not
#: required to capitalize" (8), "must be capitalized" (7). Two answers, four
#: spellings. An earlier version knew only the first and third, which is how an
#: example concluding "must be capitalized" was recorded as NOT required to.
CLASSIFY = (
    ("must capitalize", re.compile(r"\bmust capitaliz\w*", re.I)),
    ("must capitalize", re.compile(r"\bmust be capitaliz\w*", re.I)),
    ("not required to capitalize", re.compile(r"\bnot required to capitaliz\w*", re.I)),
    ("not required to capitalize", re.compile(r"\bnot required to be capitaliz\w*", re.I)),
)

#: A conclusion is announced, not merely stated. Requiring the connective is what
#: separates the paragraph that DECIDES from the ones that recite the rule or the
#: taxpayer's own prior treatment -- both of which use the same verbs.
CONNECTIVE = re.compile(
    r"^\(?[ivx]*\)?\s*(?:Therefore|Accordingly|Thus|As a result|Consequently)\b", re.I)

#: WHAT COUNTS AS DISCLOSING THE ANSWER: the words themselves, anywhere in the
#: fact pattern. Not a list of framings -- a TOTAL ban on the two stems this desk
#: reasons about.
#:
#: Three rounds of review were spent widening a list of phrasings, and each round
#: found another the last had missed: first "must be capitalized", then
#: "capitalize these amounts", then the affirmative "is required to capitalize"
#: sitting in three fact patterns after the leak had twice been called fixed. A
#: rule that must enumerate how English can say a thing will always be one
#: phrasing behind, and every gap in it is a silently inflated score.
#:
#: So the rule stops enumerating. A fact pattern may not contain "capitaliz" or
#: "deduct" in ANY form, conclusive or incidental. It costs examples whose facts
#: merely mention the words in passing -- 31 usable became 24 -- and it cannot
#: have a gap, because there is no vocabulary left to be incomplete. The cost
#: bought something too: the surviving set is 12 and 12, so a constant answer
#: scores 50% rather than 58%.
DISCLOSES = re.compile(r"capitaliz|deduct", re.I)

#: An example that leans on one not shown cannot be answered from what the desk
#: is given. Three spellings, because the regulation uses each -- a filter
#: written for only the first missed a real case on this script's first run, and
#: one written for the first two missed "The facts are the same as in Example 30"
#: on the third.
DEPENDENT = re.compile(
    r"same facts as(?: in)? Example|Assume the same facts|the facts are the same as", re.I)

#: A sentence boundary, kept crude on purpose. Its correctness is NOT what makes
#: the split safe: whatever it does, `DISCLOSES` re-checks what survives.
_SENTENCE = re.compile(r"(?<=\.)\s+(?=[A-Z(])")


def conclusions_in(text: str) -> set:
    """Every DISTINCT answer this text states. Zero, one, or -- fatally -- two."""
    return {a for a, rx in CLASSIFY if rx.search(text)}


def split_conclusion(text: str):
    """Split an example into its fact pattern and the conclusion it announces.

    Returns `(facts, conclusion, answer)`, or `(None, None, why)` naming the
    reason this example cannot become a problem. Nothing is ever guessed and
    nothing is ever dropped without a reason a reader can count.

    WHY THIS EXISTS, AND WHAT IT NEARLY COST. `build` wrote each example's
    COMPLETE text into `Facts`, and an example was kept precisely BECAUSE that
    text stated a conclusion -- so every problem handed to a model contained its
    own answer, in the regulation's own words. A model had only to copy the
    sentence back, both scoreboard rows would have read near-perfect, and the gap
    between the local brain and the frontier one -- the single finding this
    harness exists to produce -- would have been noise between two ceilings.

    WHY MORE THAN ONE CONCLUSION IS A REFUSAL AND NOT A CHOICE. § 1.263(a)-3(l)(3)
    Example 4 concludes that a cleanup is not an adaptation AND that the regrading
    must be capitalized. Reading only two spellings, an earlier version saw one
    phrase, recorded "not required to capitalize", and would have scored the right
    answer as WRONGLY ABSORBED -- manufacturing the one number that costs
    something. An example stating two outcomes has no single answer to score, so
    it is not a problem, and saying so is the only honest move available.
    """
    facts, held, found = [], [], set()
    for sentence in _SENTENCE.split(text.strip()):
        answers = conclusions_in(sentence)
        if answers and CONNECTIVE.search(sentence.strip()):
            held.append(sentence)
            found |= answers
        else:
            facts.append(sentence)
    if not found:
        return None, None, "states no conclusion this desk can score"
    if len(found) > 1:
        return None, None, "states more than one conclusion"
    kept = " ".join(facts).strip()
    if not kept or DISCLOSES.search(kept):
        return None, None, "conclusion cannot be separated from the facts"
    return kept, " ".join(held).strip(), found.pop()


PROBLEMS_HEAD = """# Problems — the denominator

Every problem is a worked example from Treas. Reg. § {section}, carrying the
conclusion the regulation itself states. **The answers are not ours**, and that is
the point: a score against answers we wrote measures agreement, not correctness.

Generated by `tools/extract_ecfr.py` from the section's own XML, so the facts are
verbatim by construction rather than retyped. Do not hand-edit.

**The conclusion is withheld from the facts.** Every sentence in which the
regulation announces its outcome is stripped out and kept only under `Answer`, so
a problem cannot be solved by reading it back. Written the other way -- the whole
example into `Facts` -- a model needed only to copy the phrase that had decided
the answer, and both rows of the scoreboard would have read near-perfect while
measuring reading comprehension.

**An example that states two outcomes is not a problem.** § 1.263(a)-3(l)(3)
Example 4 holds that a cleanup is not an adaptation and that the regrading must be
capitalized. Reading only some of the regulation's spellings, an earlier version
saw one of them and recorded the opposite answer -- which would have scored a
correct response as `wrongly_absorbed`, manufacturing the one number that costs
something. Anything that cannot be reduced to a single scorable conclusion is left
out and counted below.

## The count, and every exclusion

| | |
|---|---|
| Examples in the section | **{found}** |
| Usable as problems | **{kept}** |
| Left out | **{dropped}** |

| Left out | Because |
|---|---|
{reasons}

## What a model gets for free

| Answer | Problems |
|---|---|
{spread}

**Always answering the most common one scores {baseline}.** That is the number any
run has to beat before it has shown anything, and it is printed here because a
scoreboard whose baseline is unstated reads as skill when it may be arithmetic.

**Nothing is dropped silently.** An example that leans on one not shown cannot be
answered from what the desk is given, and one whose outcome is not stated in
capitalisation terms cannot be scored without inventing a conclusion — which is
the single thing this whole plugin exists to prevent.

---

"""

EXTRACTED_HEAD = """# Extracted authority — Treas. Reg. § 1.263(a)-3

Public-domain text under 17 U.S.C. § 105, stored in full because `SOURCES.md`
records S1 as `may_store: full_text`. Every passage is checkable against eCFR at
the URL recorded there.

**An agent may write this file.** Every line is verifiable against a public
source, which is why it is separate from `positions/` — that store holds what the
firm decided, and there an agent only proposes.

Generated by `tools/extract_ecfr.py`; do not hand-edit.

---

"""


def examples(xml_path: Path):
    """Walk the section in document order, tagging each example with its paragraph."""
    root = ET.parse(xml_path).getroot()
    para = sub = None
    n = 0
    for child in root:
        text = "".join(child.itertext()).strip()
        if child.tag == "P":
            m = re.match(r"^\((\d+)\) Examples?\..*?paragraph \(([a-z])\)", text)
            if m:
                sub, para, n = m.group(1), m.group(2), 0
        elif child.tag == "EXAMPLE" and para:
            n += 1
            head = "".join(child.find("HED").itertext()).strip()
            # EVERY child except the heading, not just PSPACE. An example's
            # later paragraphs are <P> SIBLINGS of <PSPACE>, not children of it,
            # and 24 of the section's examples have them. Collecting only
            # PSPACE dropped the (ii) paragraph -- which is usually where the
            # conclusion lives -- so ten examples reached `classify` with their
            # fact pattern intact and their answer missing, and were counted as
            # stating no conclusion. Silent truncation again, and this time it
            # shrank the denominator rather than breaking anything visible.
            body = " ".join(
                " ".join("".join(kid.itertext()).split())
                for kid in child if kid.tag != "HED"
            )
            yield {
                "para": para, "sub": sub, "n": n,
                "title": head.split(". ", 1)[-1] if ". " in head else head,
                "text": body,
            }


def build(xml_path: Path, desk_dir: Path, *, section="1.263(a)-3",
          source_id="S1", today=None):
    today = today or date.today().isoformat()
    all_ex = list(examples(xml_path))
    kept, dropped = [], []
    for e in all_ex:
        if DEPENDENT.search(e["text"]):
            dropped.append((e, "depends on an example not shown"))
            continue
        facts, _, verdict = split_conclusion(e["text"])
        if facts is None:
            dropped.append((e, verdict))          # `verdict` is the reason
        else:
            kept.append(({**e, "facts": facts, "answer": verdict}, None))

    wrap = lambda t: "\n".join(textwrap.wrap(t, 78, initial_indent="> ",
                                             subsequent_indent="> "))
    cite = lambda e: f"26 CFR {section}({e['para']})({e['sub']}) Example {e['n']}"

    problems = [
        f"## P{i} · {e['title']}\n\n"
        f"**Citation:** {cite(e)}\n\n"
        f"**Answer:** {e['answer']}\n\n"
        f"**Facts:** {e['facts']}\n"
        for i, (e, _) in enumerate(kept, 1)
    ]
    passages = [
        f"## {cite(e)}\n\n"
        f"**Source:** {source_id} · **Checked:** {today}\n\n"
        f"{wrap(e['text'])}\n"
        for e, _ in kept
    ]
    return all_ex, kept, dropped, problems, passages


def counts(all_ex, kept, dropped):
    """The denominator, and the reason for every exclusion."""
    reasons = {}
    for _, why in dropped:
        reasons[why] = reasons.get(why, 0) + 1
    spread = {}
    for e, _ in kept:
        spread[e["answer"]] = spread.get(e["answer"], 0) + 1
    return {"found": len(all_ex), "kept": len(kept), "dropped": len(dropped),
            "reasons": reasons, "spread": spread}


def write(desk_dir: Path, problems, passages, c, *, section="1.263(a)-3") -> None:
    """Write what `build` produced. Separate so `build` stays pure and testable.

    The documented command computed both collections and then printed counts
    without writing either, so `desk_dir` was accepted and ignored and the
    "reproducible regeneration" path regenerated nothing. A command that exits
    0 having done nothing is worse than one that fails.
    """
    desk_dir = Path(desk_dir)
    reasons = "\n".join(f"| {n} | {why} |" for why, n in sorted(c["reasons"].items()))
    spread = "\n".join(f"| {a} | {n} |" for a, n in sorted(c["spread"].items()))
    top = max(c["spread"].values()) if c["spread"] else 0
    baseline = f"{top} of {c['kept']} ({top * 100 // c['kept']}%)" if c["kept"] else "nothing"
    (desk_dir / "PROBLEMS.md").write_text(
        PROBLEMS_HEAD.format(section=section, found=c["found"], kept=c["kept"],
                             dropped=c["dropped"], reasons=reasons,
                             spread=spread, baseline=baseline)
        + "\n---\n\n".join(problems), encoding="utf-8")
    extracted = desk_dir / "extracted"
    extracted.mkdir(exist_ok=True)
    (extracted / f"treas-reg-{section.replace('.', '-').replace('(', '').replace(')', '')}.md"
     ).write_text(EXTRACTED_HEAD + "\n---\n\n".join(passages), encoding="utf-8")


if __name__ == "__main__":                                  # pragma: no cover
    xml_path, desk_dir = Path(sys.argv[1]), Path(sys.argv[2])
    all_ex, kept, dropped, problems, passages = build(xml_path, desk_dir)
    c = counts(all_ex, kept, dropped)
    write(desk_dir, problems, passages, c)
    print(f"found {c['found']} examples; kept {c['kept']}; left out {c['dropped']}")
    for why, n in sorted(c["reasons"].items()):
        print(f"  {n:>3}  {why}")
    print(f"wrote {len(problems)} problems and {len(passages)} passages to {desk_dir}")
