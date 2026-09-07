"""A regulation's worked examples are its best authority and its answer key.

THE MEASUREMENT THAT FORCED THIS, 7 September 2026. Two agents re-fetched all 34
declared sources and located every one of the 531 stored passages in the
publishers' live documents -- the record is true. But across six regulations the
desks hold 223,804 characters of worked examples and stored NONE of them, against
a whole corpus of 261,740 characters. The desks were missing more authority than
they held, from documents already fetched and already declared.

IT WAS NOT AN OVERSIGHT. `tools/extract_ecfr.py` drops them on purpose, and says
why: the first corpus stored the 21 examples it also graded on, so the record
carried its own answer key and the frontier row solved the set as a matching
puzzle rather than by reasoning (`runs/2026-09-04/SCOREBOARD.md`). That was the
right call FOR GRADING. The same exclusion runs on the answering side, where a
worked example -- the government applying its own rule to a fact pattern and
stating the outcome -- is the closest thing in the corpus to the question a
bookkeeper actually asks.

SO THE FIX IS TO MARK THEM, NOT TO CHOOSE. One store serves both: `ask.brief`
prints everything, `ask.brief_for_grading` prints no example at all.

WHY EXCLUDING THE PROBLEM'S OWN CITATION WOULD NOT HAVE DONE IT, which is the
thing that makes this a class and not a row. A problem is cited to the RULE its
analysis names, never to the example it came from. Filter on the problem's
citation and the example stating the answer is still in the brief, under a
different citation, fully readable.
"""
from __future__ import annotations

import pathlib
import re
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                   # noqa: E402
import record                                                # noqa: E402
from conftest import DESKS                                   # noqa: E402

_HAS_SOURCES = [d for d in sorted(DESKS.iterdir()) if (d / "SOURCES.md").is_file()]

#: The publisher's own marker, and the reason it is not a judgement of ours: the
#: passage text opens "Example." because the IRS wrote it that way.
_OPENS = re.compile(r"^Examples?[.\s]")
_LEADIN = re.compile(r"(following examples? (illustrate|illustrates)|"
                     r"illustrated in the following examples)", re.I)

_BLOCK = ("## C 1\n\n**Source:** S1 · **Checked:** 2026-09-04{kind}\n\n"
          "> Example. A buys a widget. A must capitalize it.\n")


def _kinds():
    for d in _HAS_SOURCES:
        for p in record.load(d).passages:
            yield d.name, p


# ── the field is recorded, never guessed ─────────────────────────────────────

def test_a_passage_that_does_not_say_which_it_is_is_refused():
    """The refusal that matters, and it is in the PARSER rather than the
    dataclass. An example silently read as a rule is exactly the leak this
    field closes, so the record may not fall back."""
    with pytest.raises(record.RecordError, match="no 'Kind' field"):
        record.parse_passages(_BLOCK.format(kind=""))


def test_a_kind_outside_the_vocabulary_is_refused():
    with pytest.raises(record.RecordError, match="Kind"):
        record.parse_passages(_BLOCK.format(kind=" · **Kind:** worked_example"))


def test_both_kinds_parse():
    for k in record.KINDS:
        got = record.parse_passages(_BLOCK.format(kind=f" · **Kind:** {k}"))
        assert got[0].kind == k


def test_every_stored_passage_declares_its_kind():
    for desk_name, p in _kinds():
        assert p.kind in record.KINDS, f"{desk_name} · {p.citation}: {p.kind!r}"


def test_the_only_thing_that_builds_a_passage_outside_a_test_is_the_parser():
    """What makes the dataclass default safe, asserted rather than assumed.

    `record.Passage.kind` defaults to RULE so a test can build a fixture without
    the field. That is only safe while the sole production construction is
    `parse_passages`, which requires it. A second caller would make the default
    the unsafe direction again, and this is what says so.
    """
    builders = []
    for path in sorted(HERE.rglob("*.py")):
        rel = path.relative_to(HERE)
        if rel.parts[0] in ("tests", "__pycache__") or rel.name == "conftest.py":
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"(?<![A-Za-z_.])Passage\(", line.split("#")[0]):
                builders.append(str(rel))
    # THE FILE, NOT THE LINE. A line number here drifts with every edit above
    # it, and a guard that has to be renumbered is one that gets deleted.
    assert builders == ["record.py"], (
        f"a Passage is built outside `parse_passages` at {builders}. The "
        f"dataclass defaults `kind` to RULE, which is the UNSAFE direction for "
        f"anything that could be an example -- give that caller an explicit kind "
        f"and update this test, or the leak reopens silently.")


# ── what is marked, in the record we actually hold ───────────────────────────

def test_the_worked_examples_in_the_record_are_the_four_that_are_there():
    """DERIVED AND COMPARED, never typed. Four, all on `personal-or-business`,
    all IRS Pub. 587 illustrations a person chose by hand -- on the desk that
    answers "personal or business", which is the question worked examples are
    best at. Every other desk holds none, which is the finding."""
    marked = {(d, p.citation) for d, p in _kinds() if p.kind == record.EXAMPLE}
    assert len(marked) == 4, sorted(marked)
    assert {d for d, _ in marked} == {"personal-or-business"}
    assert all("Pub. 587" in c for _, c in marked)


def test_a_lead_in_is_a_rule_and_not_an_example():
    """The distinction that was got wrong once, in this session. Eleven
    fixed-assets passages open "Examples." and are the regulation ANNOUNCING
    examples it then gives -- "The following examples illustrate the rules of
    this paragraph (c)". That sentence is rule text. What follows it is not
    stored at all, which is the gap this whole change is about."""
    leadins = [(d, p) for d, p in _kinds() if _LEADIN.search(p.text[:220])]
    assert len(leadins) == 12, f"{len(leadins)} lead-ins, not 12"
    for d, p in leadins:
        assert p.kind == record.RULE, (
            f"{d} · {p.citation} announces examples and is marked as one. A "
            f"lead-in withheld from grading costs the brief a real rule.")


def test_no_passage_opening_example_is_filed_as_a_rule_unless_it_is_a_lead_in():
    """The marking, checked against the publisher's own marker rather than
    against the list that produced it. A passage whose text opens "Example."
    and does not announce anything is a worked example, whatever we typed."""
    wrong = [f"{d} · {p.citation}" for d, p in _kinds()
             if _OPENS.match(p.text.strip()) and not _LEADIN.search(p.text[:220])
             and p.kind != record.EXAMPLE]
    assert not wrong, f"marked rule, but opens as a worked example: {wrong}"


# ── the two briefs ───────────────────────────────────────────────────────────

def test_the_grading_brief_carries_no_worked_example_from_any_desk():
    """The leak, closed at the choke point. Swept over every desk, because
    `check_no_leak`'s lesson is that one stored example is a desk-wide
    outage rather than a problem-shaped one."""
    for d in _HAS_SOURCES:
        desk = record.load(d)
        text = ask.brief_for_grading("anything", desk)
        for p in desk.passages:
            if p.kind == record.EXAMPLE:
                assert p.text[:80] not in text, (
                    f"{d.name}: the grading brief carries {p.citation!r}, which "
                    f"is a worked example and may be a problem's own answer")


def test_the_answering_brief_does_carry_them():
    """NARROWING, and without it the test above passes on an empty brief.
    The whole point is that the answering side keeps what grading gives up."""
    desk = record.load(DESKS / "personal-or-business")
    full = ask.brief("is the greenhouse deductible?", desk)
    grading = ask.brief_for_grading("is the greenhouse deductible?", desk)
    examples = [p for p in desk.passages if p.kind == record.EXAMPLE]
    assert examples, "this desk holds no example; the test proves nothing"
    for p in examples:
        assert p.text[:80] in full, f"{p.citation} is missing from the brief"
        assert p.text[:80] not in grading
    assert len(full) > len(grading), "the two briefs are the same text"


def test_the_grading_brief_keeps_every_rule():
    """Narrowing the other way. Withholding examples must not cost the brief a
    single rule -- a grading brief that quietly lost authority would depress
    the score and read as the model getting worse."""
    for d in _HAS_SOURCES:
        desk = record.load(d)
        text = ask.brief_for_grading("anything", desk)
        missing = [p.citation for p in desk.passages
                   if p.kind == record.RULE and p.text[:80] not in text]
        assert not missing, f"{d.name}: the grading brief dropped rules {missing}"
