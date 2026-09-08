"""What a person is shown does not depend on the SKILL.md a session loaded.

THE DEFECT THIS IS THE ANSWER TO, and it has bitten every Forge run. The Skill
tool served `desk:ask-desk` from a plugin cache that was three releases stale,
then four -- a file with no mention of `unchecked`, none of `passage`, and an
opening snippet that raises. A session following it correctly produces the old
output and has no way to know.

0.7.3 answered that by adding a version check and a `/reload-plugins` note TO
THAT FILE. The tester found the flaw in one sentence: *"the warning you added
lives in the file that does not load [...] Anything that depends on the loaded
SKILL.md being current cannot fix a stale SKILL.md."*

So the layout moves onto the object. `print(out)` is the whole instruction, and
every release that adds a field adds it to what a two-release-old skill prints.

WHAT `__repr__` KEEPS. The counters -- `showed`, `showed_by_source` -- exist to
falsify a model's claim that the desk held nothing. They are for the queue. The
same tester found them printed beside a sentence written for a preparer:
*"pure instrumentation next to a sentence meant for a person."*
"""
import ask
import engine

BOOKS = ('IRS Pub. 583 (12/2024), "Reconciling the checking account" '
         '— what the books are updated for')


def _served():
    return ask.answer("the bank statement shows a $10 service charge and "
                      "nothing for it is in the books", "cash-and-bank",
                      position="an entry in the books", citation=BOOKS,
                      keep=False)


def _escalation():
    return ask.answer("how do I know if a lease should be booked as an asset",
                      "fixed-assets", escalate="authority_absent",
                      working="Whether a lease puts a right-of-use asset on the "
                              "balance sheet is US GAAP under ASC 842. No desk "
                              "here holds the Codification.",
                      keep=False)


# --------------------------------------------------------------- what serves

def test_printing_a_served_answer_shows_every_field_a_reader_needs():
    out = _served()
    assert isinstance(out, engine.Served)
    shown = str(out)
    for part in (out.position, out.citation, out.tier, out.unchecked, out.passage):
        assert part and part in shown, part[:60]


def test_the_unchecked_sentence_cannot_be_left_off_by_printing():
    """The field existed in 0.7.2 and a stale skill still never printed it."""
    assert "Nobody checked" in str(_served()) or "NOBODY checked" in str(_served())


def test_the_passage_is_shown_in_full_not_truncated():
    out = _served()
    assert out.passage[-40:] in str(out)


# ------------------------------------------------------------ what refuses

def test_an_escalation_leads_with_the_working():
    """The one part written by something that read the question goes first."""
    out = _escalation()
    assert isinstance(out, engine.Refusal)
    assert str(out).startswith(out.working)


def test_the_reason_and_detail_still_reach_the_reader():
    out = _escalation()
    assert out.reason in str(out) and out.detail in str(out)


def test_the_counters_do_not_reach_the_reader():
    """`showed_by_source` is for the queue. THE CONTROL IS THE NEXT TEST."""
    out = _escalation()
    assert out.showed_by_source, "premise: this escalation carries counters"
    shown = str(out)
    assert "showed" not in shown
    assert "showed_by_source" not in shown
    assert str(out.showed) not in shown.split(out.working, 1)[-1]


def test_the_counters_are_still_on_the_repr():
    """They were not deleted -- they moved to where the log reads them."""
    out = _escalation()
    assert "showed_by_source" in repr(out)


# ----------------------------------------------- the skill's own instruction

def test_the_skill_tells_the_agent_to_print_the_object():
    """If this ever goes back to a field list, the stale-file defect returns."""
    from pathlib import Path
    skill = (Path(__file__).resolve().parent.parent
             / "skills" / "ask-desk" / "SKILL.md").read_text(encoding="utf-8")
    assert "print(out)" in skill
    assert "print(out.position)" not in skill
