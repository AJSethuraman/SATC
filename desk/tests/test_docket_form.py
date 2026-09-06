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


#: The nine matters the SECOND docket carried, taken from the page published on
#: 5 September 2026 (artifact d1372697) rather than from this module. It is the
#: only independent record of what was already open -- without it, "which matters
#: are new" is a flag this file reads back out of the same list that sets it, and
#: a mutation that unmarks one survives because both sides move together. Two did.
SECOND_DOCKET = {
    "dec-ir45-wording", "dec-override", "dec-guidance", "dec-courts-again",
    "dec-merge-275",
}


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
    n = independent["n"]
    fresh, from_tieout = counted["fresh"], counted["from_tieout"]
    assert "%s of these %s are new since the last docket" % (
        df._word(fresh).capitalize(), df._word(n)) in page
    assert "%s of them out of the tie-out" % df._word(from_tieout) in page
    # AND THE TWO ARE NOT THE SAME NUMBER, which is what the sentence got wrong:
    # it read "four ... came out of the tie-out" when three did and the fourth
    # came from a CI failure that night.
    assert from_tieout <= fresh
    # AGAINST THE PREVIOUS DOCKET, not against this module's own flag.
    keys = {r["key"] for r in df.OTHERS}
    assert SECOND_DOCKET <= keys, (
        f"matters carried over have been renamed or dropped: "
        f"{sorted(SECOND_DOCKET - keys)}. A docket that renames a matter loses "
        f"the answer already given for it.")
    assert fresh == len(keys - SECOND_DOCKET), (
        f"the page says {fresh} matters are new; the ones absent from the second "
        f"docket are {sorted(keys - SECOND_DOCKET)}")
    assert from_tieout == sum(1 for r in df.OTHERS
                              if r.get("new") and r["group"] == "From the tie-out")
    assert sum(r.get("shape") == "rule" for r in counted["rows"]) == counted["rules"]
    assert counted["rules"] + counted["concl"] == independent["pos"]


def test_how_many_are_answerable_is_read_off_the_notes(page, counted, independent):
    """Not typed. A position this docket says to hold back is identified by its
    own recommendation, so ratifying one moves the sentence without an edit."""
    waiting, answerable = counted["waiting"], counted["answerable"]
    pos = independent["pos"]
    assert waiting + answerable == pos
    held_back = sum(1 for r in df.items()
                    if "Do not ratify" in (r.get("note") or {}).get("rec", ""))
    assert waiting == held_back, "the held-back count is not read off the notes"
    said = ("All but %s of the %s positions you held are answerable" % (
        df._word(waiting), df._word(pos))) if waiting else (
        "Every one of the %s positions you held are answerable" % df._word(pos))
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
def test_the_browser_tab_carries_the_same_count_as_the_page(page, independent):
    """The <title> read "Docket · Nine Open" on a page whose headline said
    thirteen, and it shipped: the tab is the artifact's name in the gallery, and
    every test above reads the BODY. A figure is a figure wherever it is
    printed."""
    n = independent["n"]
    assert "<title>Docket \u00b7 %s Open</title>" % df._word(n).capitalize() in page
