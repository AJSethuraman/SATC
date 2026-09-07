"""What a searcher finds is a pointer. What ties out is authority. They differ.

THE SNIPPET IS NEVER THE PASSAGE. A search engine hands back its own rendering of
a page — truncated, re-ordered, sometimes generated — and storing that would put
the search engine's word for what the government publishes into a record whose
entire value is that it is checkable against the government. So `check` ignores
the snippet and fetches; and where a declared source covers the citation it
fetches THAT SOURCE, so a correct quote of the CFR found on somebody's blog is
verified against eCFR and the blog never becomes its publisher.

AND CONTAINMENT ALONE IS NOT ENOUGH HERE, WHICH IS THE DIFFERENCE FROM
`proving`. The extractor stores passages as short as eight characters and is
entitled to: it took them from a known place in the document's outline, and the
outline is its warrant that the words belong to the citation. A searcher has no
outline. Words that appear four times in a document say nothing about WHICH
paragraph they came from, so the rule is uniqueness rather than length — a
measured property instead of a threshold nobody measured.

EVERY TRANSPORT HERE IS A FAKE, and one of them asserts it was never called.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import comparing                                            # noqa: E402
import proving                                              # noqa: E402
import record                                               # noqa: E402
import searching                                            # noqa: E402
from conftest import DESKS                                  # noqa: E402

ECFR = "https://www.ecfr.gov/current/title-26/section-1.263(a)-3"
BLOG = "https://tax-blog.example/what-the-regs-say"
QUOTE = ("An amount is paid to improve a unit of property if it results in a "
         "betterment to the unit of property, a restoration of the unit of "
         "property, or an adaptation to a new or different use.")


class _Page:
    def __init__(self, text):
        self.text = text
        self.at = "2026-09-07T09:00:00+00:00"


class _Transport:
    """Records what it was asked for, so a test can check WHERE it fetched."""

    def __init__(self, text=""):
        self.asked = []
        self.text = text

    def __call__(self, url):
        self.asked.append(url)
        return _Page(self.text)


def _refused():
    class R:
        reason, detail = searching.ABSENT, "not in the record"
    return R()


def _gap():
    return searching.Gap.from_refusal(_refused(), "fixed-assets", "a roof?")


def _hit(url=BLOG):
    return searching.Hit(url=url, title="What the regs say", query="roof",
                         snippet="…betterment to the unit of property…")


def _absent_citation(desk):
    """A citation under S1's prefix that this desk does not hold.

    Derived rather than typed: a hardcoded one becomes wrong the day the record
    grows to include it, and the test would then pass for the wrong reason.
    """
    prefix = desk.source("S1").citation_prefix
    for n in range(1, 500):
        c = f"{prefix}(zz)({n})"
        if desk.passage(c) is None:
            return c
    raise AssertionError("no absent citation")


@pytest.fixture
def desk():
    return record.load(DESKS / "fixed-assets")


# ── reading a candidate off a hit ─────────────────────────────────────────────

def test_a_candidate_records_what_was_quoted_and_where_it_was_pointed(desk):
    cand = searching.read(_hit(), _absent_citation(desk), QUOTE, record.RULE)
    assert cand.found_at == BLOG and cand.verdict == searching.UNCHECKED
    assert not cand.declared, "nothing is declared before it has been checked"


def test_a_candidate_may_not_elide(desk):
    """Marking an omission is a curatorial act over text already on the record.

    A quote read off a page on first sight has no reason to cut anything, and
    allowing one would let a searcher assemble a sentence the publisher does not
    have out of two the publisher does.
    """
    with pytest.raises(searching.SearchError, match=r"may not elide"):
        searching.read(_hit(), _absent_citation(desk),
                       f"An amount {comparing.ELLIPSIS} use.", record.RULE)


def test_a_candidate_must_say_whether_it_is_a_rule_or_a_worked_example(desk):
    """The same refusal `parse_passages` makes, for the same reason: an example
    read as a rule is shown to a model that is being graded on it."""
    with pytest.raises(searching.SearchError, match="kind must be"):
        searching.read(_hit(), _absent_citation(desk), QUOTE, "")


def test_a_candidate_quoting_nothing_is_refused(desk):
    with pytest.raises(searching.SearchError, match="no text at all"):
        searching.read(_hit(), _absent_citation(desk), "   ", record.RULE)


# ── where it fetches from ─────────────────────────────────────────────────────

def test_a_quote_of_a_declared_source_is_checked_against_that_source(desk):
    """THE PROPERTY THE WHOLE MODULE TURNS ON. The blog is a pointer."""
    cand = searching.read(_hit(BLOG), _absent_citation(desk), QUOTE, record.RULE)
    t = _Transport(f"prelude {QUOTE} coda")
    out = searching.check(cand, desk, t)
    assert t.asked == [ECFR], "it fetched the blog instead of the publisher"
    assert out.fetched_from == ECFR and out.found_at == BLOG
    assert out.verdict == proving.TIED and out.source_id == "S1"


def test_a_citation_no_declared_source_covers_is_read_where_it_was_found(desk):
    cand = searching.read(_hit(BLOG), "Rev. Proc. 2099-1, section 4", QUOTE,
                          record.RULE)
    t = _Transport(QUOTE)
    out = searching.check(cand, desk, t)
    assert t.asked == [BLOG] and out.source_id == "" and out.verdict == proving.TIED


def test_a_source_the_engine_may_never_read_is_never_reached_for():
    """`human_only` is the absence of a fetch, not a stricter one — so the
    component whose whole job is to reach is the one that must not."""
    licensed = record.Source(
        id="S1", title="FASB ASC", tier="primary", access="human_only",
        may_store="license_check", checked="2026-09-07",
        citation_prefix="ASC 360", url="https://asc.fasb.org/")
    d = record.Desk(name="t", sources=(licensed,))
    t = _Transport(QUOTE)
    out = searching.check(searching.read(_hit(), "ASC 360-10-35-1", QUOTE,
                                         record.RULE), d, t)
    assert t.asked == [], "it fetched a source whose licence forbids it"
    assert out.verdict == proving.COULD_NOT and "human_only" in out.note


def test_a_publisher_that_cannot_be_reached_is_not_a_publisher_that_changed(desk):
    """COULD NOT is never quietly upgraded, and never quietly demoted either."""
    def broken(url):
        raise TimeoutError("no route")

    out = searching.check(
        searching.read(_hit(), _absent_citation(desk), QUOTE, record.RULE),
        desk, broken)
    assert out.verdict == proving.COULD_NOT and "TimeoutError" in out.note


# ── the uniqueness rule ───────────────────────────────────────────────────────

def test_words_the_document_does_not_carry_differ(desk):
    out = searching.check(
        searching.read(_hit(), _absent_citation(desk), QUOTE, record.RULE),
        desk, _Transport("a document about something else entirely"))
    assert out.verdict == proving.DIFFERS and out.occurrences == 0


def test_words_the_document_carries_twice_do_not_show_which_paragraph(desk):
    """The rule the extractor does not need and the searcher does.

    Containment proves the words are in the document. It is the SECOND
    occurrence that proves containment cannot say which paragraph they are.
    """
    out = searching.check(
        searching.read(_hit(), _absent_citation(desk), QUOTE, record.RULE),
        desk, _Transport(f"(a) {QUOTE} ... (b) {QUOTE}"))
    assert out.verdict == searching.AMBIGUOUS and out.occurrences == 2
    assert searching.dispose(out, desk)[0] == searching.REFUSE


def test_a_quote_that_occurs_once_ties_out(desk):
    out = searching.check(
        searching.read(_hit(), _absent_citation(desk), QUOTE, record.RULE),
        desk, _Transport(f"lead-in {QUOTE} trailing"))
    assert out.verdict == proving.TIED and out.occurrences == 1


# ── what may become of it ─────────────────────────────────────────────────────

def _checked(desk, citation=None, doc=None, url=BLOG):
    cand = searching.read(_hit(url), citation or _absent_citation(desk), QUOTE,
                          record.RULE)
    return searching.check(cand, desk, _Transport(doc or f"x {QUOTE} y"))


def test_a_tied_out_quote_of_a_declared_source_may_be_stored(desk):
    what, why = searching.dispose(_checked(desk), desk)
    assert what == searching.STORE and why.startswith("add it.")


def test_a_tied_out_quote_of_an_undeclared_publisher_is_a_proposal(desk):
    """Not a refusal. The passage is real; whether that host is authority this
    desk relies on is the firm's to say, and they say it having seen the words."""
    cand = _checked(desk, citation="Rev. Proc. 2099-1, section 4")
    what, why = searching.dispose(cand, desk)
    assert what == searching.PROPOSE and "tax-blog.example" in why


def test_a_proposal_cannot_be_turned_into_a_passage(desk):
    """The gate, in the one place a caller would try to walk around it."""
    cand = _checked(desk, citation="Rev. Proc. 2099-1, section 4")
    with pytest.raises(searching.SearchError, match="admitted"):
        searching.as_passage(cand)


def test_searching_for_something_the_desk_already_holds_reports_the_routing(desk):
    """Not a win and not a failure. The authority was there; the way to it was
    not, and that is a different repair from adding a passage."""
    held = next(p for p in desk.passages if p.source_id == "S1")
    cand = searching.check(
        searching.read(_hit(), held.citation, held.text, held.kind),
        desk, _Transport(f"lead {held.text} tail"))
    what, why = searching.dispose(cand, desk)
    assert what == searching.HELD and searching.ABSENT in why


def test_a_source_whose_words_may_not_be_copied_is_refused_even_when_it_ties():
    limited = record.Source(
        id="S1", title="A licensed treatise", tier="secondary",
        access="public_fetch", may_store="citation_only", checked="2026-09-07",
        citation_prefix="Treatise", url="https://treatise.example/x")
    d = record.Desk(name="t", sources=(limited,))
    cand = searching.check(
        searching.read(_hit(), "Treatise § 4.02", QUOTE, record.RULE),
        d, _Transport(f"a {QUOTE} b"))
    what, why = searching.dispose(cand, d)
    assert cand.verdict == proving.TIED
    assert what == searching.REFUSE and "citation_only" in why


def test_nothing_is_disposed_of_on_the_strength_of_a_search_result(desk):
    cand = searching.read(_hit(), _absent_citation(desk), QUOTE, record.RULE)
    with pytest.raises(searching.SearchError, match="has not been checked"):
        searching.dispose(cand, desk)


# ── the handover, and what it refuses to carry ────────────────────────────────

def test_the_judge_is_handed_a_passage_and_nothing_about_the_search(desk):
    """A judge that could see the query or the ranking would be reading the
    searcher's confidence as evidence about the law."""
    cand = _checked(desk)
    p = searching.as_passage(cand)
    assert isinstance(p, record.Passage)
    assert (p.citation, p.source_id, p.kind) == (cand.citation, "S1", record.RULE)
    flat = repr(p)
    for leak in (cand.query, cand.found_at, _hit().snippet):
        assert leak not in flat, f"the passage carries {leak!r}"


def test_a_passage_that_did_not_tie_out_never_becomes_authority(desk):
    cand = _checked(desk, doc="an unrelated document")
    with pytest.raises(searching.SearchError, match="DIFFERS"):
        searching.as_passage(cand)


def test_the_checked_date_is_the_day_the_document_was_read(desk):
    assert _checked(desk).checked == "2026-09-07"


# ── the search as a record ────────────────────────────────────────────────────

def test_a_search_that_found_nothing_is_still_a_record(desk):
    """A gap searched and found empty and a gap nobody searched are the same
    hole in the record and call for opposite next steps."""
    s = searching.Search(gap=_gap(), queries=("roof replacement",),
                         hits=(_hit(), _hit("https://other.example/x")))
    assert s.findings == () and len(s.hits) == 2
    assert s.of(searching.STORE) == ()
