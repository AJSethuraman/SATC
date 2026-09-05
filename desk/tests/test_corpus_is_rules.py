"""The corpus is the rules. The worked examples are the questions.

`check_no_leak` has always said this and enforced it at prompt-build time, which
is too late to be seen: the failure surfaced as an escalation on a scoreboard,
and escalation reads as a success. This puts the same fact in the suite, where a
corpus edit that reintroduces it goes red on the commit that makes it.

THREE PASSAGES CARRY A WORKED EXAMPLE TODAY, all on one desk, and any one of them
poisons ALL nineteen of its problems -- the check sweeps every problem for every
prompt. They are listed rather than fixed because the fix is not free, and what
it costs is written up in `docs/CONTEXT-ON-FILE.md`.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import record                                               # noqa: E402
import scoreboard_run as sr                                 # noqa: E402
from conftest import DESKS                                  # noqa: E402

#: `(desk, problem, passage)` — every worked example currently stored as
#: authority. Each is a real defect and each is here so that a FOURTH fails this
#: test on the commit that adds it, rather than surfacing as a desk that scores
#: nineteen careful escalations without a model ever running.
#:
#: Removing one from this set is what fixing it looks like. The test goes red
#: either way, which is the point: the number may only move deliberately.
KNOWN = {
    # FIXED 5 September 2026, and left here as a comment rather than an entry:
    # Pub. 525's passage held the rule AND Example 36, and Example 36 IS problem
    # RW2. Trimmed at the publication's own "Example 36." boundary. The rule --
    # a cash rebate "isn't income, but you must reduce your basis by the amount
    # of the rebate" -- stands alone, verbatim, and still answers RW2.
    # These two are examples end to end -- the citation says so. Each names the
    # paragraph it applies ("Under paragraph (a)(1)(iv) of this section"), and
    # the desk already holds (a)(1)(iv) as a rule. So the obvious fix is to point
    # IR4 and IR5 at the rule and drop the examples from the corpus.
    #
    # IT IS NOT FREE, WHICH IS WHY IT IS NOT DONE HERE. The firm ratified POS2 on
    # 5 September 2026, and POS2 rests on that same (a)(1)(iv). A ratified
    # position is returned verbatim and `_check` refuses an answer that restates
    # it -- so once these problems cite it, their own recorded answers refuse as
    # `contradicts_ratified_position` unless the wordings are reconciled.
    ("rewards-and-information-returns", "IR4",
     "26 CFR 1.6041-1(a)(1)(v), Example 1"),
    ("rewards-and-information-returns", "IR5",
     "26 CFR 1.6041-1(a)(1)(v), Example 2"),
}


def _stored_examples():
    found = set()
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for problem in desk.problems:
            probe = sr._bare(max(sr._SENTENCES.split(problem.facts), key=len))
            for passage in desk.passages:
                if probe in sr._bare(passage.text):
                    found.add((desk.name, problem.id, passage.citation))
    return found


def test_no_new_worked_example_enters_the_corpus():
    found = _stored_examples()
    new = found - KNOWN
    assert not new, (
        f"stored authority now carries {sorted(new)}. A worked example in the "
        f"corpus carries its own conclusion into every prompt on that desk, and "
        f"the desk then scores an escalation for every problem without a model "
        f"ever running — which this scoreboard reports as a success."
    )


def test_a_fixed_one_is_removed_from_the_list():
    found = _stored_examples()
    fixed = KNOWN - found
    assert not fixed, (
        f"{sorted(fixed)} no longer carries a worked example. Good — delete it "
        f"from KNOWN so the list keeps meaning what it says."
    )


def test_one_of_these_takes_the_whole_desk_down():
    """Not one problem: all of them. The check sweeps every problem for every
    prompt, so a single stored example is a desk-wide outage — which is why
    three defects cost nineteen scores."""
    desks = {d for d, _, _ in KNOWN}
    assert len(desks) == 1, "the arithmetic below is written for one desk"
    desk = record.load(DESKS / next(iter(desks)))
    blocked = 0
    for problem in desk.problems:
        try:
            sr.build_prompt(problem, desk, shape="index")
        except sr.Leak:
            blocked += 1
    assert blocked == len(desk.problems), (
        f"{blocked} of {len(desk.problems)} blocked; this test records that it "
        f"is all of them")
