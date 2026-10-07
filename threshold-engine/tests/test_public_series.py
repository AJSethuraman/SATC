"""The engine on the four public consumer charge-off series.

These pin what the engine finds in real history, without being given the
answers reached by hand in the design proposal. Where it disagrees with the
hand analysis, the disagreement is the finding and the test records it.

Sources are in each file's header: Federal Reserve charge-off rates for cards
and mortgage, and an aggregate of every FDIC filer for home equity and other
consumer, each a trailing-twelve-month rate in percent.
"""
import statistics

import pytest

from conftest import NCO, load, settings
from threshold_engine import Refused, run

CARDS = load("cards_nco_ttm.csv")
MORTGAGE = load("mortgage_nco_ttm.csv")
HOME_EQUITY = load("home_equity_nco_ttm.csv")
OTHER_AS_FILED = load("other_consumer_as_filed_nco_ttm.csv")


def complete_peaks(r):
    return [round(e.peak, 2) for e in r.episodes if e.complete]


def test_cards_2008_is_an_outlier_and_is_excluded():
    r = run(NCO, settings(), CARDS)
    assert complete_peaks(r) == [6.6, 10.43]
    assert r.outlier["excluded"]
    assert r.outlier["run"] == ("2009-04-01", "2011-04-01", 9)
    # Matches the hand analysis in the proposal, to the third decimal.
    assert [round(b, 3) for b in r.bounds] == [3.796, 4.498, 5.199, 5.901]


def test_cards_1990s_cycles_never_returned_to_normal():
    # 1996 to 2006 is one stretch above the 3.98% normal: the 1998 and 2002
    # peaks are one episode under this rule, not two.
    r = run(NCO, settings(), CARDS)
    first = r.episodes[0]
    assert (first.start, first.peak_date, first.end) == (
        "1996-04-01", "2002-07-01", "2006-10-01")


@pytest.mark.parametrize("series, prior_peak", [(MORTGAGE, 0.24),
                                                (HOME_EQUITY, 0.24)])
def test_without_materiality_mortgage_and_home_equity_look_like_cards(series, prior_peak):
    # The finding the hand analysis hid: one complete episode before 2008, as
    # cards has. A uniform rule therefore excludes 2008 here too, leaving a
    # scale on a quarter of a percent.
    r = run(NCO, settings(), series)
    assert complete_peaks(r)[0] == prior_peak and len(complete_peaks(r)) == 2
    assert r.outlier["excluded"]
    assert r.bounds[-1] < 0.3


@pytest.mark.parametrize("series", [MORTGAGE, HOME_EQUITY])
def test_materiality_is_what_keeps_2008_for_mortgage_and_home_equity(series):
    # At a stated materiality of 0.5%, the 2002 rise is not stress, 2008 is the
    # only episode, and it stays. The level is the bank's to set; 0.5 here is a
    # test value, not a recommendation.
    r = run(NCO, settings(materiality=0.5), series)
    assert len(complete_peaks(r)) == 1
    assert not r.outlier["excluded"]
    assert r.bounds[-1] > 1.5


def test_mortgage_and_home_equity_are_a_1_today():
    for s in (MORTGAGE, HOME_EQUITY):
        assert run(NCO, settings(materiality=0.5), s).latest_score == 1


def test_other_consumer_after_the_2011_break_holds_no_cycle_and_is_refused():
    # The Call Report split auto out of other consumer in 2011. Read only from
    # the break onward, the series has no complete episode.
    r = run(NCO, settings(window=("2011-03-31", "2026-06-30")), OTHER_AS_FILED)
    assert isinstance(r, Refused) and r.code == "no_episode"


def test_an_independent_recomputation_of_the_cards_bounds():
    # Recomputed here from the file with the standard library alone: median of
    # the retained quarters, worst retained quarter, three equal steps to 75%.
    excluded = {p.date for p in CARDS if "2009-04-01" <= p.date <= "2011-04-01"}
    kept = [p.value for p in CARDS if p.date not in excluded]
    normal, worst = statistics.median(kept), max(kept)
    step = 0.75 * (worst - normal) / 3
    expect = [normal + i * step for i in range(4)]
    assert run(NCO, settings(), CARDS).bounds == pytest.approx(expect)
