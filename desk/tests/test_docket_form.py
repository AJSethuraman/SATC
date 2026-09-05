"""The docket must not state a number the record does not hold.

The failure this guards against is specific and was found in review: the page
announced twenty-two matters and seventeen positions in fixed text, so the first
ratification -- the whole point of the page -- would have left it lying about how
many decisions remained, in the headline, the filter buttons and the preface at
once. Every figure is now derived, and these tests are what keeps it that way:
they read the RENDERED page and compare it with the record, so a number typed
back into the template fails here rather than in front of the firm.
"""
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402
from tools import docket_form as df                         # noqa: E402


@pytest.fixture(scope="module")
def page():
    return df.render()


@pytest.fixture(scope="module")
def counted():
    return df._counted()


@pytest.fixture(scope="module")
def independent():
    """The same figures, counted from the record and the module -- NOT from
    `_counted`. Read off the thing under test, these tests moved with any bug in
    it and proved only that the page agreed with itself: two mutations survived
    that way, including the hard-coded preface count this file exists to stop."""
    proposed, ratified = 0, 0
    for d in sorted((HERE / "desks").iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        for q in record.load(d).positions:
            if q.proposed:
                proposed += 1
            else:
                ratified += 1
    return {"pos": proposed, "ratified": ratified, "dec": len(df.OTHERS),
            "n": proposed + len(df.OTHERS)}


def test_every_total_on_the_page_is_the_number_of_rows_on_it(page, counted, independent):
    assert (counted["n"], counted["pos"], counted["dec"]) == (
        independent["n"], independent["pos"], independent["dec"]), \
        "the generator's own count disagrees with the record"
    n, pos, dec = independent["n"], independent["pos"], independent["dec"]
    assert n == pos + dec, "a row is neither a position nor a decision"
    assert ">%s things waiting on you<" % df._word(n).capitalize() in page
    assert ">0 of %d answered<" % n in page
    assert ">All %d<" % n in page
    assert ">Positions %d<" % pos in page
    assert ">Other %d<" % dec in page


def test_the_preface_counts_what_the_cards_actually_are(page, counted, independent):
    """It hard-coded "Five of these nine" on the second docket and this caught it
    on the run that wrote it -- the same drift the filter labels had."""
    n, pos, dec = independent["n"], independent["pos"], independent["dec"]
    assert "%s of these %s did not exist" % (
        df._word(dec).capitalize(), df._word(n)) in page
    assert "%s are positions you held; %s are decisions" % (
        df._word(pos).capitalize(), df._word(dec)) in page
    assert sum(r.get("shape") == "rule" for r in counted["rows"]) == counted["rules"]
    assert counted["rules"] + counted["concl"] == pos


def test_how_many_are_answerable_is_read_off_the_notes(page, counted, independent):
    """Not typed. A position this docket says to hold back is identified by its
    own recommendation, so ratifying one moves the sentence without an edit."""
    waiting, answerable = counted["waiting"], counted["answerable"]
    pos = independent["pos"]
    assert waiting + answerable == pos
    held_back = sum(1 for r in df.items()
                    if "Do not ratify" in (r.get("note") or {}).get("rec", ""))
    assert waiting == held_back, "the held-back count is not read off the notes"
    said = ("All but %s of the %s you held now answerable" % (
        df._word(waiting), df._word(pos))) if waiting else (
        "Every one of the %s you held now answerable" % df._word(pos))
    assert said in page


def test_the_ratified_over_proposed_figure_is_read_from_the_desks(page, independent):
    assert "<b>%d / %d</b>" % (independent["ratified"], independent["pos"]) in page


def test_no_card_shows_a_position_its_desk_does_not_hold(counted):
    for row in counted["rows"]:
        if row["kind"] != "position":
            continue
        desk = record.load(HERE / "desks" / row["group"])
        held = [q for q in desk.positions if q.proposed and q.id == row["tag"].split(" · ")[1]]
        assert held, "%s is on the page and not in the record" % row["key"]
        assert held[0].position == row["position"]
        assert held[0].citation == row["citation"]


def test_every_row_has_somewhere_to_put_an_answer(counted):
    for row in counted["rows"]:
        assert row["picks"], "%s has no answer to give" % row["key"]
        assert "Not yet" in row["picks"], \
            "%s cannot be deferred, so silence would have to stand for it" % row["key"]
