"""The record refuses to be half-read.

Every test here has a mutation twin: it changes the record so the check must go
red, and asserts that it does. Seven of this operation's check bugs produced
false passes, and a check that has only ever passed is not evidence.
"""
from __future__ import annotations

import sys

import pytest

import record
from record import RecordError
from conftest import DESKS, ROOT


# ── it loads at all ───────────────────────────────────────────────────────────

def test_fixed_assets_desk_loads(fixed_assets):
    assert fixed_assets.name == "fixed-assets"
    assert fixed_assets.sources, "a desk with no authority cannot answer anything"
    assert fixed_assets.problems, "a desk that cannot be scored is a claim"


def test_every_problem_cites_authority_the_desk_actually_holds(fixed_assets):
    """The scoreboard is worthless if its own answers cite nothing."""
    for p in fixed_assets.problems:
        assert fixed_assets.passage(p.citation) is not None, (
            f"problem {p.id} cites {p.citation!r}, which is not in extracted/"
        )


def test_a_problems_authority_is_a_rule_and_its_conclusion_is_the_examples(
        fixed_assets):
    """Two halves, and they used to be one assertion.

    This test asserted that every problem's stored passage STATED the problem's
    conclusion -- which was true, because the passage was the worked example
    itself, and that identity is the defect #244 removed: an authority corpus
    that is its own answer key. Now the passage backing a problem is the rule
    its analysis names, and it must NOT state the outcome for these facts; the
    conclusion is still the regulation's, read from the example on a rebuild.

    Matched through the classifier's spellings rather than against the answer
    string, because `answer` is a canonical LABEL covering four framings: the
    regulation writes "not required to be capitalized" where the label reads
    "not required to capitalize". Asserting the label literally passed only while
    the classifier knew two spellings, and it was that same two-spelling reading
    that recorded a wrong answer for § 1.263(a)-3(l)(3) Example 4.

    Over every problem, not `problems[0]` -- regenerating the set has already
    moved a different example into that slot once.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    import extract_ecfr as ex
    xml = ROOT / "tools" / "fixtures" / "1.263a-3.xml"
    _, kept, _, _, _ = ex.build(xml, DESKS / "fixed-assets", checked="2026-09-04")
    example_of = {e["facts"]: e for e, _ in kept}
    assert fixed_assets.problems, "no problems; this would pass vacuously"
    for p in fixed_assets.problems:
        passage = fixed_assets.passage(p.citation)
        assert passage is not None, f"problem {p.id} has no stored authority"
        spellings = [rx for answer, rx in ex.CLASSIFY if answer == p.answer]
        assert spellings, f"{p.answer!r} is not an answer the classifier states"
        announces = [s for s in ex._SENTENCE.split(passage.text)
                     if ex.CONNECTIVE.search(s.strip()) and ex.conclusions_in(s)]
        assert not announces, (
            f"problem {p.id}'s authority {p.citation} announces a conclusion: "
            f"it is a worked example, not a rule")
        example = example_of[p.facts]["text"]
        assert any(rx.search(example) for rx in spellings), (
            f"problem {p.id} claims {p.answer!r}, and its example says no such "
            f"thing — one of the two is wrong"
        )


# ── it raises rather than defaulting ──────────────────────────────────────────

BASE = """## S1 · A source

**Tier:** primary · **Access:** public_fetch · **May store:** full_text · **Checked:** 2026-09-04

**Citation prefix:** 26 CFR 1.263(a)-3
"""


def test_a_good_source_block_parses():
    """The control. Without it, every test below could pass for the wrong reason."""
    assert record.parse_sources(BASE)[0].tier == "primary"


@pytest.mark.parametrize("find,replace,expect", [
    ("**Tier:** primary", "**Tier:** important", "tier"),
    ("**Access:** public_fetch", "**Access:** curl", "access"),
    ("**May store:** full_text", "**May store:** sure", "may_store"),
    ("**Checked:** 2026-09-04", "**Checked:** last tuesday", "checked"),
])
def test_a_value_outside_the_vocabulary_is_an_error(find, replace, expect):
    with pytest.raises(record.RecordError, match=expect):
        record.parse_sources(BASE.replace(find, replace))


@pytest.mark.parametrize("line,label", [
    ("**Citation prefix:** 26 CFR 1.263(a)-3\n", "Citation prefix"),
])
def test_a_missing_required_field_is_an_error(line, label):
    with pytest.raises(record.RecordError, match=label):
        record.parse_sources(BASE.replace(line, ""))


def test_an_empty_record_is_an_error_not_an_empty_desk():
    with pytest.raises(record.RecordError, match="no sources"):
        record.parse_sources("# nothing here\n")
    with pytest.raises(record.RecordError, match="no problems"):
        record.parse_problems("# nothing here\n")


def test_a_passage_citing_an_unrecorded_source_is_an_error(tmp_path):
    """Authority with no recorded source cannot be verified, so it is refused."""
    d = tmp_path / "orphan"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(BASE, encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** c\n\n**Answer:** a\n\n**Facts:** f\n",
        encoding="utf-8")
    (d / "extracted" / "x.md").write_text(
        "## 26 CFR 1.263(a)-3(k)(7) Example 3\n\n"
        "**Source:** S9 · **Checked:** 2026-09-04\n\n> text\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="S9"):
        record.load(d)


def test_a_missing_desk_is_an_error(tmp_path):
    with pytest.raises(record.RecordError, match="no desk"):
        record.load(tmp_path / "nope")


def test_a_desk_without_problems_is_an_error(tmp_path):
    """A desk that cannot be scored is a claim, so it does not load."""
    d = tmp_path / "unscored"
    d.mkdir()
    (d / "SOURCES.md").write_text(BASE, encoding="utf-8")
    with pytest.raises(record.RecordError, match="PROBLEMS"):
        record.load(d)


# ── the vocabulary is closed on purpose ───────────────────────────────────────

def test_human_only_is_a_recognised_access_value():
    """FASB ASC needs it: a source the engine may cite and must never read."""
    assert "human_only" in record.ACCESS


def test_license_check_stores_nothing_by_being_the_strictest_default():
    assert record.MAY_STORE[-1] == "license_check"


def test_only_primary_authority_is_binding():
    """Tier 2 or 3 alone is somebody's reading, which is a position for the firm."""
    src = record.parse_sources(BASE)[0]
    assert src.binding
    for tier in ("secondary", "tertiary"):
        weaker = record.parse_sources(BASE.replace("primary", tier))[0]
        assert not weaker.binding


def test_human_only_sources_are_not_readable():
    src = record.parse_sources(BASE.replace("public_fetch", "human_only"))[0]
    assert not src.readable, "human_only is the absence of a fetch, not a stricter one"


def test_a_position_whose_citation_matches_no_source_is_refused_at_load(tmp_path):
    """It loaded clean and raised EngineError the first time anybody asked that
    exact question -- a record that reads as valid and detonates on use."""
    d = tmp_path / "typo"
    (d / "positions").mkdir(parents=True)
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        "## S1 · A source\n\n**Tier:** tertiary · **Access:** human_only · "
        "**May store:** license_check · **Checked:** 2026-09-04\n\n"
        "**Citation prefix:** ASC\n", encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** ASC 360\n\n**Answer:** must capitalize\n\n"
        "**Facts:** f\n", encoding="utf-8")
    (d / "positions" / "POSITIONS.md").write_text(
        "## POS1 · A position with a mistyped citation\n\n"
        "**Citation:** ACS 360-10 · **Recorded:** 2026-09-04\n\n"
        "**Position:** must capitalize\n\n"
        "**Ratified:** the firm, 4 September 2026\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="matches 0 recorded sources"):
        record.load(d)


def test_a_date_that_is_not_a_day_on_the_calendar_is_refused(tmp_path):
    """`2026-02-31` matched the shape regex, loaded clean, and then crashed
    `staleness.check` at `date.fromisoformat`. This parser's promise is that a
    malformed record fails while being READ; stopping at the digit layout keeps
    half of it."""
    with pytest.raises(record.RecordError, match="not a day on the calendar"):
        record.parse_sources(BASE.replace("2026-09-04", "2026-02-31"))
    # And a real leap day still loads, so the check is not just "reject 31".
    assert record.parse_sources(BASE.replace("2026-09-04", "2024-02-29"))


def test_the_same_source_id_defined_twice_is_refused(tmp_path):
    """A set hid the duplicate and `Desk.source()` takes the first match, so a
    passage's tier, access policy and storage permission changed by REORDERING
    two blocks -- with every test green, because the id was "known" either way."""
    d = tmp_path / "dup"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(
        BASE + "\n" + BASE.replace("**Tier:** primary", "**Tier:** tertiary"),
        encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** 26 CFR 1.263(a)-3(a)\n\n"
        "**Answer:** must capitalize\n\n**Facts:** f\n", encoding="utf-8")
    (d / "extracted" / "a.md").write_text(
        "## 26 CFR 1.263(a)-3(a)\n\n**Source:** S1 · **Checked:** 2026-09-04\n\n"
        "> text\n", encoding="utf-8")
    with pytest.raises(record.RecordError, match="more than once"):
        record.load(d)


def test_the_same_citation_stored_twice_is_refused(tmp_path):
    """Two extracted files defining one citation both load and `Desk.passage()`
    takes the first. Files are read sorted, so RENAMING one changes the source,
    tier and checked date behind an answer -- and a tier change can turn a served
    answer into `authority_permits_choice` with nothing in the diff to show it."""
    d = tmp_path / "twice"
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(BASE, encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** 26 CFR 1.263(a)-3(a)\n\n"
        "**Answer:** must capitalize\n\n**Facts:** f\n", encoding="utf-8")
    body = ("## 26 CFR 1.263(a)-3(a)\n\n**Source:** S1 · "
            "**Checked:** 2026-09-04\n\n> text\n")
    (d / "extracted" / "a.md").write_text(body, encoding="utf-8")
    (d / "extracted" / "b.md").write_text(body, encoding="utf-8")
    with pytest.raises(record.RecordError, match="stored more than once"):
        record.load(d)


def test_two_ratified_positions_on_one_citation_are_refused(tmp_path):
    """`position()` takes the first match, so a FILENAME decided which
    conclusion the desk served as the firm's. Proposals may collide freely --
    competing proposals are what a pull request is for."""
    d = tmp_path / "two-positions"
    (d / "positions").mkdir(parents=True)
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(BASE, encoding="utf-8")
    (d / "PROBLEMS.md").write_text(
        "## P1 · x\n\n**Citation:** 26 CFR 1.263(a)-3(a)\n\n"
        "**Answer:** must capitalize\n\n**Facts:** f\n", encoding="utf-8")
    entry = ("## POS{n} · Reading {n}\n\n"
             "**Citation:** 26 CFR 1.263(a)-3(a) · **Recorded:** 2026-09-04\n\n"
             "**Position:** {p}\n\n**Ratified:** the firm, 4 September 2026\n")
    (d / "positions" / "a.md").write_text(
        entry.format(n=1, p="must capitalize"), encoding="utf-8")
    (d / "positions" / "b.md").write_text(
        entry.format(n=2, p="not required to capitalize"), encoding="utf-8")
    with pytest.raises(record.RecordError, match="two ratified positions"):
        record.load(d)

    # A ratified one beside a PROPOSAL is not a collision: only one answers.
    (d / "positions" / "b.md").write_text(
        entry.format(n=2, p="not required to capitalize")
        .replace("**Ratified:** the firm, 4 September 2026\n", ""),
        encoding="utf-8")
    assert record.load(d).position("26 CFR 1.263(a)-3(a)").position == "must capitalize"


# ── the one containment rule ─────────────────────────────────────────────────

def test_containment_stops_at_a_label_boundary():
    """A continuation that is not a label is not a child.

    `26 CFR 1.263(a)-30` begins with every character of `26 CFR 1.263(a)-3` and
    is a DIFFERENT SECTION, not a paragraph inside it. A plain prefix test calls
    it contained; requiring the remainder to open a label is what makes it not.
    A desk holding two sections with a shared stem is all it takes for this to
    matter, and the queue asks this question about citations a model produced.
    """
    assert not record.under("26 CFR 1.263(a)-30", "26 CFR 1.263(a)-3")
    assert not record.under("26 CFR 1.263(a)-3T(j)", "26 CFR 1.263(a)-3")
    assert record.under("26 CFR 1.263(a)-3(j)", "26 CFR 1.263(a)-3")


def test_a_sibling_numbered_ten_is_not_beneath_the_one_numbered_one():
    """`(j)(10)` starts with the characters of `(j)(1)`. The closing bracket in
    the ancestor is what separates them — asserted rather than assumed, because
    it is the reason a prefix comparison is safe here at all."""
    assert record.under("26 CFR 1.263(a)-3(j)(1)(iii)", "26 CFR 1.263(a)-3(j)(1)")
    assert not record.under("26 CFR 1.263(a)-3(j)(10)", "26 CFR 1.263(a)-3(j)(1)")
    assert record.under("26 CFR 1.263(a)-3(j)(10)", "26 CFR 1.263(a)-3(j)")


def test_containment_does_not_cross_sections():
    """The copy this replaced compared only the parenthesised labels, so the
    identical labels of two different sections read as contained. A desk holding
    two sources is all it takes."""
    assert not record.under("26 CFR 1.999(a)-3(j)(1)", "26 CFR 1.263(a)-3(j)")


def test_a_citation_is_not_beneath_itself():
    """Strict, because "the desk cited exactly what it holds" is a different
    fact from "the desk cited a finer point inside it", and only the second is
    a near miss."""
    assert not record.under("26 CFR 1.263(a)-3(j)", "26 CFR 1.263(a)-3(j)")


def test_nothing_is_beneath_an_empty_citation():
    """An answer that offered no citation must not be filed as having reached
    the right rule by a finer path."""
    assert not record.under("", "26 CFR 1.263(a)-3(j)")
    assert not record.under("26 CFR 1.263(a)-3(j)(1)", "")


# ── the second boundary rule, and why it is not `under` ──────────────────────

@pytest.mark.parametrize("citation,prefix,expected", [
    # THE COLLISION THAT PRODUCED THIS. A desk holding a regulation and its
    # temporary counterpart is an ordinary pairing, and every temporary paragraph
    # resolved to BOTH sources, so `load()` refused the desk outright.
    ("26 CFR 1.274-5T(b)(2)", "26 CFR 1.274-5", False),
    ("26 CFR 1.274-5T(b)(2)", "26 CFR 1.274-5T", True),
    ("26 CFR 1.274-5(c)(1)", "26 CFR 1.274-5", True),
    # the same collision without the letter, and without the punctuation
    ("26 CFR 1.274-11(a)", "26 CFR 1.274-1", False),
    ("26 CFR 1.4461", "26 CFR 1.446", False),
    ("26 CFR 1.446-1(a)(4)", "26 CFR 1.446-1", True),
    # a publication continues with a comma, not a label -- which is why this is
    # NOT `under`, whose remainder must open with "("
    ('IRS Pub. 583 (12/2024), "Reconciling the checking account"',
     "IRS Pub. 583 (12/2024)", True),
    # and a citation may be the prefix exactly
    ("IRS Pub. 463 (2025)", "IRS Pub. 463 (2025)", True),
    ("", "26 CFR 1.446", False),
    ("26 CFR 1.446", "", False),
])
def test_a_citation_belongs_to_a_source_only_at_a_boundary(citation, prefix, expected):
    assert record.from_source(citation, prefix) is expected


def test_from_source_is_not_under_and_the_difference_is_load_bearing():
    """`under` asks whether one paragraph sits INSIDE another, so its remainder
    must open a label. A source prefix is answered against whole citations that
    continue with a comma, or do not continue at all. Collapsing the two would
    resolve no publication citation to its own source."""
    pub = 'IRS Pub. 583 (12/2024), "Reconciling the checking account"'
    assert record.from_source(pub, "IRS Pub. 583 (12/2024)")
    assert not record.under(pub, "IRS Pub. 583 (12/2024)")
    assert record.from_source("IRS Pub. 463 (2025)", "IRS Pub. 463 (2025)")
    assert not record.under("IRS Pub. 463 (2025)", "IRS Pub. 463 (2025)")


# ── a subject may not be a bare number, and the separator is why ─────────────

def _subjects(terms: str) -> str:
    return (f"## demo · A desk\n\n**Answered from S1:** {terms}\n")


@pytest.mark.parametrize("terms,offender", [
    # THE ONE THAT PRODUCED THIS. The list is comma-separated and a written
    # figure carries a comma, so `$2,500` arrives already split -- and the figure
    # the firm actually asked about became a subject no question could match,
    # while `500` became a token firing on any question mentioning any $500.
    ("$2,500, threshold", "500"),
    ("$5,000, ceiling", "000"),
    # a bare section number is a whole word under canon's rule, so one desk
    # declaring `463` fired on every question containing it
    ("463, travel", "463"),
    ("threshold, 263", "263"),
    ("cash, 446", "446"),
    # a figure is a bad subject WITH its dollar sign too: whole-word matching
    # will not reach "$2,500" written the way anybody writes it
    ("$2500, ceiling", "$2500"),
])
def test_a_bare_number_is_refused_as_a_subject(terms, offender):
    with pytest.raises(RecordError, match="bare number"):
        record.parse_subjects(_subjects(terms), "demo")


@pytest.mark.parametrize("term", ["threshold", "1.263(a)-1", "263(a)",
                                  "notice 2015-82", "162-3", "form 3115"])
def test_a_qualified_citation_is_still_a_subject(term):
    """The guard is exact and so may block — but it must not eat a real subject.
    `263(a)` and `1.263(a)-1` are not bare numbers and neither is `$2500`."""
    reg = record.parse_subjects(_subjects(f"{term}, threshold"), "demo")
    assert term in reg.fires_on


def test_no_shipped_desk_declares_a_subject_this_short_or_this_numeric():
    """Written as a guard over the real record rather than only over a fixture:
    four of six desks were declaring one when this was added."""
    from pathlib import Path
    for d in sorted((Path(__file__).resolve().parents[1] / "desks").iterdir()):
        if not (d / "SUBJECTS.md").is_file():
            continue
        desk = record.load(d)          # raises if any term is degenerate
        assert all(len(t) >= 3 for t in desk.fires_on), d.name
