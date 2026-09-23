"""Off-source answers need a reader even on a desk that never asked for one.

THE FIRM CHOSE THIS, 8 September 2026, on the docket: *"Leave it demoted, add
the judgment requirement."* It followed Forge-Desk measuring that the judge does
NOT by itself refuse what the source map used to block — a reader who quotes the
paragraph correctly and judges wrongly still serves.

WHAT `off_source` MARKS. An answer whose citation came from a source the desk
does not declare for this subject. Until `7be95ff` that was refused outright.
It is served now, with a warning, because the map measured 10 false refusals in
98 on short phrasings. The one thing that must not ALSO be optional on that
class is that somebody read the paragraph.

**IT CHANGES NOTHING TODAY AND THAT IS WORTH SAYING.** All seven desks already
declare `Judged: required`, so today the new condition is never the one that
fires. This is a guard against the next desk built without it — the case where a
narrow declaration and no second reader would combine silently. A test that only
exercised the current desks would prove nothing, so this constructs a desk that
does not require a judge.

AND IT DOES NOT CLOSE MISJUDGMENT. Nothing here pretends otherwise: a careless
yes still serves, with the warning. It closes OMISSION on the class where
omission is least affordable.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import ask
import engine
import record

CORPUS = Path(__file__).resolve().parents[1] / "corpus"
CORPUS = Path(__file__).resolve().parents[1] / "corpus"

#: The measured case.
#: THE ORIGINAL FIXTURE WAS FIXED OUT FROM UNDER THIS TEST, 8 September 2026,
#: and that is the right outcome. It used Q16 on `capitalization-and-de-minimis`
#: citing 1.162-3(c)(1)(iv); the firm then approved widening `tool`/`asset` to
#: also be answered from S2, so that citation is now ON-source and the case is
#: gone. Repointed at `vehicle-expense` VE1, where "car" is answered from S4 and
#: 1.280F-6 -- the listed-property rule, squarely on point for a car -- sits in
#: S1. Six of that desk's problems are off-source on their own citation.
QUESTION = "An inspector who uses her own car for a construction job"
OFF_SOURCE = "26 CFR 1.280F-6(a)(2)(ii)"
POSITION = "listed property, and the substantiation rules apply"


def _desk_not_requiring_a_judge(tmp_path):
    """A real desk with its `Judged: required` declaration removed."""
    dst = tmp_path / "corpus"
    shutil.copytree(CORPUS, dst)
    p = dst / "SUBJECTS.md"
    text = p.read_text(encoding="utf-8")
    assert "**Judged:** required" in text, "the fixture's premise moved"
    p.write_text(text.replace("**Judged:** required", ""), encoding="utf-8")
    desk = record.load(dst)
    assert not desk.needs_a_judge, "the fixture did not actually opt out"
    return desk


def test_off_source_is_refused_unjudged_even_where_the_desk_did_not_ask(tmp_path):
    desk = _desk_not_requiring_a_judge(tmp_path)
    out = ask.answer(QUESTION,  position=POSITION,
                     citation=OFF_SOURCE, corpus=tmp_path / "corpus", keep=False)
    assert isinstance(out, engine.Refusal), (
        "an off-source answer was served with nobody having read the paragraph")
    assert out.reason == "not_judged"
    assert "does not declare" in out.detail, (
        "the refusal must say WHY this answer needed a reader, or a caller "
        "cannot tell it from the desk-wide rule")


def test_an_on_source_answer_on_that_desk_is_untouched(tmp_path):
    """The new condition must not become a desk-wide requirement by the back
    door — that would be reinstating the thing the firm just removed."""
    desk = _desk_not_requiring_a_judge(tmp_path)
    # CHOSEN BY THE PROPERTY, NOT BY NAME. This picked VE7, which was on-source
    # for `vehicle-expense`. One corpus moves answers in BOTH directions — the
    # union of `answered_from` puts some citations on-source that were not, and
    # changes which subjects a source is declared for, so VE7 is now OFF-source
    # and the test was asserting the opposite of its own subject. What it is
    # about is an on-source answer, so that is what is searched for.
    served = [p for p in desk.problems
              if not isinstance(
                  ask.answer(p.title, position=p.answer, citation=p.citation,
                             corpus=tmp_path / "corpus", keep=False),
                  engine.Refusal)]
    assert served, (
        "no answer in the corpus is on-source and servable without a judge, so "
        "the demotion this test guards has nothing left to be true of — that is "
        "a finding about the record, not a reason to weaken the assertion")
    pr = served[0]
    out = ask.answer(pr.title,  position=pr.answer,
                     citation=pr.citation, corpus=tmp_path / "corpus", keep=False)
    if isinstance(out, engine.Refusal):
        assert out.reason != "not_judged", (
            "this desk opted out of judgments and this answer is on-source; "
            "requiring one here is the demotion undone")
