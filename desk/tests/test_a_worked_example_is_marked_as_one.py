"""A regulation's worked examples are its best authority and its answer key.

THE MEASUREMENT THAT FORCED THIS, 7 September 2026. Two agents re-fetched all 34
declared sources and located every stored passage in the publishers' live
documents -- the record is true. But across six regulations the
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
sys.path.insert(0, str(HERE / "tools"))

import ask                                                   # noqa: E402
import record                                                # noqa: E402
import scoreboard_run as sr                                  # noqa: E402
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

def test_the_worked_examples_in_the_record_are_where_they_should_be():
    """DERIVED AND COMPARED, never typed.

    IT WAS FOUR AN HOUR AGO, and the four are worth remembering: IRS Pub. 587
    illustrations a person chose by hand on the desk that answers "personal or
    business" -- the question worked examples are best at. Every other desk held
    none, which was the finding that produced this change.

    Now `fixed-assets` holds all 117 of § 1.263(a)-3's examples, because the
    extractor stores them and marks them. The other five desks still hold none:
    each is built from a regulation the extractor has not been re-run over, and
    that gap is the remaining work rather than a decision.
    """
    per = {}
    for d, p in _kinds():
        if p.kind == record.EXAMPLE:
            per[d] = per.get(d, 0) + 1
    assert per == {"fixed-assets": 117, "personal-or-business": 4}, per


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


# ── the corruption the storing of examples exposed ───────────────────────────

_BROKEN_HYPHEN = re.compile(r"\w- [a-z]")


def test_no_stored_passage_has_a_word_broken_at_a_hyphen():
    """A passage broken across a wrap must rejoin to what the publisher printed.

    FOUND 7 SEPTEMBER 2026, BY DIFFING THE STORED TEXT AGAINST THE SECTION. The
    extractor wraps at 78 columns for the diff's sake, and `textwrap` breaks on
    hyphens by default; `parse_passages` rejoins lines with a space. So a wrap
    landing inside "load-carrying" stored it as "load- carrying" -- text the
    publisher never printed, in a passage that can therefore never tie out
    again, and the tie-out is the only thing that would ever have said so.

    THE EXISTING CORPUS DODGED IT ENTIRELY, which is why nothing caught it: no
    rule paragraph happened to wrap inside a hyphenated word, so the corpus tied
    out 531 of 531 with the bug fully present. Storing § 1.263(a)-3's worked
    examples hit it six times in the first run.

    A record that only breaks on some inputs is broken on all of them. This
    sweeps the whole corpus rather than the six.
    """
    broken = []
    for desk_name, p in _kinds():
        for m in _BROKEN_HYPHEN.finditer(p.text):
            broken.append(f"{desk_name} · {p.citation}: "
                          f"{p.text[max(0, m.start() - 25):m.end() + 15]!r}")
    assert not broken, (
        "a word is broken at a hyphen, so the stored text is not what the "
        "publisher printed and the passage can never tie out:\n  "
        + "\n  ".join(broken))


def test_the_extractor_wraps_without_breaking_hyphens():
    """The mechanism, beside the record. The sweep above passes on a corpus that
    was never rebuilt; this fails on the commit that reintroduces the wrap."""
    import textwrap
    text = ("A replaces the storage area of the truck with a new one rated for "
            "a load-carrying capacity fifty percent greater than before, which "
            "is a betterment.")
    rejoined = " ".join(
        l.lstrip("> ").strip() for l in
        textwrap.wrap(text, 78, initial_indent="> ", subsequent_indent="> ",
                      break_on_hyphens=False))
    assert rejoined == text, "the wrap does not round-trip"
    # AND THE DEFAULT REALLY DOES CORRUPT IT, so the argument above is load
    # bearing rather than decorative.
    with_default = " ".join(
        l.lstrip("> ").strip() for l in
        textwrap.wrap(text, 78, initial_indent="> ", subsequent_indent="> "))
    assert with_default != text and "load- carrying" in with_default


# ── what a reply is scored against must be what the prompt showed ────────────

def test_the_citation_index_is_exactly_what_the_prompt_showed():
    """A MUTATION SURVIVED WITHOUT THIS, 7 September 2026.

    `corpus_lines` withholds the worked examples from a graded prompt; three
    tests catch it if that stops. `citation_index` — the set a reply is checked
    against to score `citation_off_index` — was changed in the same commit for
    the same reason, and NOTHING failed when it was changed back.

    The damage is quiet and points the wrong way. `citation_off_index` counts
    replies citing something that was not in front of the model, which is the
    one number that detects a brain answering from RECALL of the regulation
    rather than from the brief it was handed. Counting the examples as on-index
    makes exactly those replies read as legitimate, and the detector reports
    fewer of the thing it exists to find.

    So the two are asserted as one fact rather than separately: the index a
    reply is scored against IS the set of citations the prompt showed.
    """
    for d in _HAS_SOURCES:
        desk = record.load(d)
        index = sr.citation_index(desk)
        lines = [ln.strip() for ln in sr.corpus_lines(desk, "index")]
        # COMPARED BY PREFIX, not by splitting on the separator. A citation may
        # itself contain " — " (`IRS Pub. 587 (2025), "Exclusive Use" — the den
        # the family also uses`), so splitting the line truncates the citation
        # and the test fails on a record that is correct. It did.
        assert len(lines) == len(index), (
            f"{d.name}: the prompt shows {len(lines)} lines against an index of "
            f"{len(index)}; a reply is scored against a set the model was not "
            f"shown")
        for ln in lines:
            assert any(ln.startswith(c) for c in index), (
                f"{d.name}: the prompt shows a citation the index does not "
                f"carry: {ln[:70]!r}")
        examples = {p.citation for p in desk.passages if p.kind == record.EXAMPLE}
        assert not (examples & set(sr.citation_index(desk))), (
            f"{d.name}: worked examples are on the index a reply is scored "
            f"against, so citing one the model never saw reads as on-index")


def test_that_index_still_carries_the_rules():
    """Narrowing. An empty index would satisfy the test above perfectly."""
    desk = record.load(DESKS / "fixed-assets")
    index = sr.citation_index(desk)
    rules = {p.citation for p in desk.passages if p.kind == record.RULE}
    assert set(index) == rules and len(index) == 172, len(index)
