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


def test_every_total_on_the_page_is_the_number_of_rows_on_it(page, counted):
    n, pos, dec = counted["n"], counted["pos"], counted["dec"]
    assert n == pos + dec, "a row is neither a position nor a decision"
    assert ">%s things waiting on you<" % df._word(n).capitalize() in page
    assert ">0 of %d answered<" % n in page
    assert ">All %d<" % n in page
    assert ">Positions %d<" % pos in page
    assert ">Other %d<" % dec in page


def test_the_preface_counts_what_the_cards_actually_are(page, counted):
    rules, pos = counted["rules"], counted["pos"]
    assert "%s of the %s are not conclusions" % (
        df._word(rules).capitalize(), df._word(pos)) in page
    # And the figure is a count of the cards, not a sentence someone wrote.
    assert sum(r.get("shape") == "rule" for r in counted["rows"]) == rules
    assert rules + counted["concl"] == pos


def test_the_retraction_is_stated_from_the_measurement(page, counted):
    blind, turns = counted["blind"], counted["turns"]
    assert blind + turns == counted["pos"]
    if turns == 0:
        assert "<b>Not one of them</b> sits on a citation" in page
        assert "That is wrong for all %s of them" % df._word(blind) in page
    else:
        assert "Only <b>%s</b> of them sits" % df._word(turns) in page


def test_the_ratified_over_proposed_figure_is_read_from_the_desks(page, counted):
    ratified = sum(len([q for q in record.load(d).positions if not q.proposed])
                   for d in sorted((HERE / "desks").iterdir())
                   if (d / "SOURCES.md").is_file())
    assert counted["ratified"] == ratified
    assert "<b>%d / %d</b>" % (ratified, counted["pos"]) in page


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
