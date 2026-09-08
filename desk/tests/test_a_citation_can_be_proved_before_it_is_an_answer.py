"""The core proves a passage; the record half only finds one to prove.

A PREFACTOR, AND THIS FILE IS WHAT MAKES IT ONE. `prove` took a `Served` and
resolved its citation out of a desk's record -- which is precisely what a
CANDIDATE citation does not have. Nothing about fetching a page and comparing
what came back needs a record, and the two were only married because there had
been one caller.

WHY THE SPLIT IS TESTED RATHER THAN TRUSTED. A wrapper that quietly grew its own
copy of the comparison would pass every test in the suite: same inputs, same
verdicts, two implementations drifting apart until one of them was fixed and the
other was not. So one test here asserts DELEGATION -- that `prove` goes THROUGH
`prove_passage` -- and it is the only test in this file that would survive the
logic being inlined. That is the mutation #341 names.

NO NEW BEHAVIOUR IS CLAIMED HERE. The verdicts, the landed-host check and the
never-upgrade rule are proved in `test_an_answer_can_prove_itself.py` and
`test_a_bounce_is_not_the_text_moving.py`, both unchanged and both still passing
at the same count. This file proves the seam, not the semantics.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import engine                                               # noqa: E402
import proving                                              # noqa: E402
import record                                               # noqa: E402
from conftest import DESKS                                  # noqa: E402

DESK = "fixed-assets"


class _Page:
    def __init__(self, text, url=""):
        self.text = text
        self.body = text.encode("utf-8")
        self.url = url
        self.at = "2026-09-08T12:00:00+00:00"
        self.nbytes = len(self.body)


def _desk():
    return record.load(DESKS / DESK)


def _passage(desk):
    for p in desk.passages:
        if desk.position(p.citation) is None:
            return p
    raise AssertionError("no passage on this desk is backed by a source")


def _source(desk, passage):
    kind, _obj, source = desk.authority_for(passage.citation)
    assert kind != "position" and source is not None
    return source


# ── the core needs no record, and no answer ──────────────────────────────────

def test_a_passage_ties_out_with_no_desk_and_no_served_answer():
    """The whole point of the prefactor, stated as the shortest call there is."""
    desk = _desk()
    p = _passage(desk)
    proof = proving.prove_passage(
        p.citation, p.text, _source(desk, p),
        lambda s, c: _Page("preamble " + p.text + " and more"))
    assert proof.verdict == proving.TIED and proof.held
    assert proof.citation == p.citation
    assert proof.matched_chars > 0
    assert len(proof.sha256) == 64


def test_the_core_says_DIFFERS_when_the_words_are_not_there():
    """THE PAGE MUST NAME THE CITATION, or this is not a rewrite — it is a
    document we cannot show is the right one, and that is COULD NOT (#344)."""
    desk = _desk()
    p = _passage(desk)
    proof = proving.prove_passage(
        p.citation, p.text, _source(desk, p),
        lambda s, c: _Page(f"{p.citation} says something else entirely now"))
    assert proof.verdict == proving.DIFFERS
    assert proof.matched_chars == 0


def test_a_document_that_does_not_name_the_citation_is_COULD_NOT():
    """FOUND ON THE FORGE, 8 September 2026. eCFR served a real headless
    browser an HTTP 200 "Request Access" page from the CORRECT host with no
    redirect — and `prove` called it DIFFERS, which withdrew the answer and
    told a human to retire a citation that had not moved."""
    desk = _desk()
    p = _passage(desk)
    proof = proving.prove_passage(
        p.citation, p.text, _source(desk, p),
        lambda s, c: _Page("Request Access. Due to aggressive automated "
                           "scraping, programmatic access is limited."))
    assert proof.verdict == proving.COULD_NOT
    assert "does not mention" in proof.note


def test_the_core_says_COULD_NOT_when_the_transport_raises():
    """Never DIFFERS. A network that is down says nothing about the text."""
    desk = _desk()
    p = _passage(desk)

    def dead(source, citation):
        raise OSError("no route to host")

    proof = proving.prove_passage(p.citation, p.text, _source(desk, p), dead)
    assert proof.verdict == proving.COULD_NOT
    assert not proof.held
    assert "no route to host" in proof.note


def test_the_landed_host_check_survives_the_split():
    """A redirect to another host is COULD NOT, not DIFFERS -- in the core."""
    desk = _desk()
    p = _passage(desk)
    proof = proving.prove_passage(
        p.citation, p.text, _source(desk, p),
        lambda s, c: _Page(p.text, url="https://interstitial.example/blocked"))
    assert proof.verdict == proving.COULD_NOT
    assert "landed on" in proof.note


def test_a_passage_the_core_is_handed_need_not_be_the_one_on_the_desk():
    """The candidate path's shape: words that no desk holds, proved anyway.

    #343 builds a source in memory for a citation the record has never seen.
    Nothing in the core may assume the passage came out of `desk.passages`, and
    this is the test that says so before that slice is written.
    """
    desk = _desk()
    p = _passage(desk)
    invented = "a sentence that is in no desk's record anywhere"
    proof = proving.prove_passage(
        p.citation, invented, _source(desk, p),
        lambda s, c: _Page("before " + invented + " after"))
    assert proof.verdict == proving.TIED
    assert proof.matched_chars == len(invented)


# ── the wrapper delegates, and that is the load-bearing assertion ────────────

def test_prove_goes_through_the_core_rather_than_repeating_it(monkeypatch):
    """THE MUTATION #341 NAMES: inline the comparison and this goes red.

    Every other test in the suite passes either way. This one fails the moment
    `prove` stops delegating, which is the only moment a second copy of the
    comparison can start to drift.
    """
    desk = _desk()
    p = _passage(desk)
    seen = {}

    def spy(citation, passage, source, transport):
        seen.update(citation=citation, passage=passage, source=source)
        return proving.Proof(proving.TIED, citation, note="from the spy")

    monkeypatch.setattr(proving, "prove_passage", spy)
    served = engine.Served(position="x", citation=p.citation,
                           tier="primary", checked=p.checked)
    proof = proving.prove(served, desk, lambda s, c: _Page(p.text))

    assert proof.note == "from the spy", "prove did not go through the core"
    assert seen["citation"] == p.citation
    assert seen["passage"] == p.text, "the core was not handed the stored words"
    assert seen["source"] is not None


def test_the_two_record_outcomes_never_reach_the_core(monkeypatch):
    """A position has no publisher, and the wrapper must not fetch to say so.

    Positive precondition first: the desk really does hold a position, so a
    green here is the check working rather than the fixture being empty.
    """
    # A DIFFERENT DESK, deliberately: `fixed-assets` holds no ratified position,
    # so a test written against it would assert nothing and pass.
    desk = record.load(DESKS / "capitalization-and-de-minimis")
    positions = desk.positions
    assert positions, "this desk holds no ratified position to test with"

    def never(*a, **k):
        raise AssertionError("the core was reached for a ratified position")

    monkeypatch.setattr(proving, "prove_passage", never)
    citation = positions[0].citation
    assert desk.position(citation) is not None
    served = engine.Served(position="x", citation=citation,
                           tier="primary", checked="2026-09-08")
    proof = proving.prove(served, desk, lambda s, c: _Page("anything"))
    assert proof.verdict == proving.COULD_NOT
    assert "no publisher" in proof.note


# ── the identifier rules, pinned because the fixtures do not exercise them ──
#
# TWO MUTATIONS SURVIVED THE FIRST VERSION OF THIS FILE and both were the same
# fault: every fixture above puts the citation in the page EXACTLY AS CITED, so
# the two rules that make the check work on a real document were never run. A
# guard whose helper can be broken without a test going red is a guard nobody
# can rely on.


def test_a_page_naming_the_SECTION_matches_a_citation_to_a_subparagraph():
    """THE CASE THAT ACTUALLY HAPPENS, and no fixture above reaches it.

    A desk cites the subparagraph it relies on — `1.263(a)-2(d)(1)`. The page
    that carries it is headed with the SECTION, `1.263(a)-2`, and contains the
    full path nowhere. Without trimming trailing groups, the genuine document
    matches nothing, every real page looks like an interstitial, and DIFFERS
    becomes unreachable — the guard swallowing the thing it exists to protect.
    """
    marks = proving.identifiers("26 CFR 1.263(a)-2(d)(1)")
    assert "1.263(a)-2" in marks, marks
    assert "1.263(a)-2(d)(1)" in marks, "the citation as written must survive too"
    page = "Sec. 1.263(a)-2 Amounts paid to acquire or produce tangible property."
    assert proving.about_this_citation("26 CFR 1.263(a)-2(d)(1)", page)


def test_only_TRAILING_groups_come_off():
    """Removing `(a)` from the middle would leave `1.263-2`, a different rule."""
    assert "1.263-2" not in proving.identifiers("26 CFR 1.263(a)-2(d)(1)")


def test_nothing_shorter_than_three_characters_is_an_identifier():
    """A bare `2` is in every document ever written. A one-character token
    would make `about_this_citation` true of anything and the guard would never
    fire — which is mutation M3, and it survived until this test existed."""
    for mark in proving.identifiers("26 CFR 1.263(a)-2(d)(1)"):
        assert len(mark) >= 3, mark
    assert proving.identifiers("A 1") == (), "a bare digit is not an identifier"
    # AND THE INTERSTITIAL STAYS UNMATCHED, which is the consequence that
    # matters: a loose rule makes the refusal page look like the regulation.
    assert not proving.about_this_citation(
        "26 CFR 1.263(a)-2(d)(1)",
        "Request Access. Due to aggressive automated scraping of "
        "FederalRegister.gov and eCFR.gov, programmatic access is limited.")


def test_a_bare_year_is_not_an_identifier():
    """`IRS Pub. 583 (12/2024)` yields `2024`, which appears in a great many
    documents that are not that publication — including, plausibly, the
    publisher's own refusal page. `583` is the identifier and it survives."""
    marks = proving.identifiers('IRS Pub. 583 (12/2024), "Reconciling"')
    assert "583" in marks and "2024" not in marks, marks


def test_a_publishers_name_is_not_evidence_and_the_measurement_says_so():
    """THE MEASUREMENT FROM THE FORGE, kept as a test. A check on the
    publisher's own name would have passed the interstitial: `eCFR` is in it."""
    interstitial = ("Request Access. Due to aggressive automated scraping of "
                    "FederalRegister.gov and eCFR.gov, programmatic access to "
                    "these sites is limited to our developer APIs.")
    assert "eCFR" in interstitial, "the fixture is not the one that was measured"
    assert not proving.about_this_citation("26 CFR 1.263(a)-2(d)(1)", interstitial)
