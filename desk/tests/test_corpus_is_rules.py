"""No worked example reaches a graded prompt UNMARKED.

THIS FILE SAID "the corpus is the rules" UNTIL 7 SEPTEMBER 2026, and the corpus
is no longer only the rules -- deliberately. The desks were measured holding
223,804 characters of worked examples they did not store, against a whole corpus
of 261,740: they were missing more authority than they held, from documents
already fetched and already declared. A worked example is the government
applying its own rule to a fact pattern and stating the outcome, which is the
closest thing in the record to the question a bookkeeper actually asks.

WHAT DID NOT CHANGE IS WHY THIS FILE EXISTS. An example the graded brain can see
carries its own conclusion into every prompt on that desk. So the examples are
stored and MARKED, `Passage.kind` says which is which, and three readers withhold
them: `corpus_lines` (what the prompt shows), `citation_index` (what a reply is
scored against) and `ask.brief_for_grading`.

THE DEFECT IS THEREFORE A DIFFERENT SHAPE NOW, and this file tests for the new
one: a passage that carries a problem's fact pattern and is filed as a RULE. That
passage reaches the prompt, carries the answer, and nothing marks it. A marked
example doing the same thing is the design working.

`check_no_leak` has always said this and enforced it at prompt-build time, which
is too late to be seen: the failure surfaced as an escalation on a scoreboard,
and escalation reads as a success. This puts the same fact in the suite, where a
corpus edit that reintroduces it goes red on the commit that makes it.

NO PASSAGE CARRIES A WORKED EXAMPLE TODAY, and the set below is empty for the
first time. It was three, then two, then none: Pub. 525's Example 36 came out on
5 September 2026 and the two § 1.6041-1(a)(1)(v) examples on the 6th, once the
firm reworded POS2 so the rule they name could carry their problems.

THE SET IS KEPT, EMPTY, RATHER THAN DELETED WITH THE TESTS. An empty list that a
new entry breaks is a guard; a deleted file is a defect nobody will find again.
The desk-wide arithmetic is what makes it worth the lines -- ONE stored example
blocked all nineteen problems on its desk, and a blocked problem is recorded as
an escalation, which this scoreboard reports as a SUCCESS. That is a silent
outage wearing the costume of a careful desk.
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
#: EMPTY, and `set()` rather than `{}` -- an empty brace literal is a DICT,
#: and `found - KNOWN` then raises TypeError instead of measuring anything.
#: Both tests went red on the commit that emptied it, which is the right
#: failure and is why the set is spelled out.
KNOWN: set = set()
# EMPTY, and each line below is a fix rather than a deletion.
#
# Pub. 525's passage held the rule AND Example 36, and Example 36 IS problem
# RW2. Trimmed 5 September 2026 at the publication's own "Example 36."
# boundary. The rule -- a cash rebate "isn't income, but you must reduce your
# basis by the amount of the rebate" -- stands alone, verbatim, and still
# answers RW2.
#
# § 1.6041-1(a)(1)(v) Examples 1 and 2 ARE problems IR4 and IR5, end to end.
# Removed from the corpus 6 September 2026 and the problems pointed at the
# rule each example names, "(a)(1)(iv)". THE COST WAS NOT THE REMOVAL, and
# this is why it waited a day: the firm had ratified POS2 on that same
# (a)(1)(iv), a ratified position outranks the stored regulation and is
# served verbatim, so both problems would have refused as
# `contradicts_ratified_position` -- the desk refusing the regulation for
# disagreeing with the firm's summary of it. The firm reworded POS2 to the
# paragraph's own sentence and its second rule moved to POS3, on the
# paragraph that rule actually turns on.


def _stored_examples():
    found = set()
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for problem in desk.problems:
            probe = sr._bare(max(sr._SENTENCES.split(problem.facts), key=len))
            for passage in desk.passages:
                # MARKED EXAMPLES ARE EXPECTED and are not the defect: they
                # are withheld from the prompt by kind. `fixed-assets` stores
                # all 117 of its section's examples, 16 of which ARE its
                # problems. Counting those would make this guard fire forever
                # on the desks that are correct, which is how a guard dies.
                if passage.kind != record.RULE:
                    continue
                if probe in sr._bare(passage.text):
                    found.add((desk.name, problem.id, passage.citation))
    return found


def test_no_new_worked_example_enters_the_corpus():
    found = _stored_examples()
    new = found - KNOWN
    assert not new, (
        f"stored authority now carries {sorted(new)} as a RULE. It is a worked "
        f"example -- it holds a problem's own fact pattern -- so it reaches the "
        f"prompt with its conclusion in it, and the desk scores an escalation "
        f"for every problem without a model ever running, which this scoreboard "
        f"reports as a success. Mark it `Kind: example` and it is withheld."
    )


def test_a_fixed_one_is_removed_from_the_list():
    found = _stored_examples()
    fixed = KNOWN - found
    assert not fixed, (
        f"{sorted(fixed)} no longer carries a worked example. Good — delete it "
        f"from KNOWN so the list keeps meaning what it says."
    )


def test_every_problem_on_every_desk_can_actually_be_prompted():
    """The measurement, not the promise. ONE stored worked example is a
    desk-wide outage, not one bad problem -- the leak check sweeps every problem
    for every prompt -- so this asserts the whole population rather than a
    sample. Measured 6 September 2026: 19 of 19 on the rewards desk, where it
    had been 0 of 19."""
    blocked = []
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for problem in desk.problems:
            try:
                sr.build_prompt(problem, desk, shape="index")
            except sr.Leak as exc:
                blocked.append(f"{desk.name}/{problem.id}: {exc}")
    assert not blocked, (
        "these problems cannot be prompted at all, and each is recorded as an "
        "escalation — which this scoreboard reports as a success:\n  "
        + "\n  ".join(blocked))
