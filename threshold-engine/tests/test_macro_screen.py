"""Leads found's screen: the Dashboard's lead test in Python, over every economic series against every bank series.
Its statistics are held to published values here; that it gives what the Dashboard's formulas give for the same pair
was checked in LibreOffice (LOG.md, 24 Oct 2026)."""
import random

import pytest

from threshold_engine.macro import screen as SC

LEADS, STARTS, P, MIN_PAIRS = [-24, -12, 0, 6, 12, 24], 4, 0.05, 6


def test_tdist_is_excels_two_tailed_with_its_degrees_of_freedom_cut_to_a_whole_number():
    # Student's t at the 5% two-tailed point: 2.228139 on 10 degrees of freedom, 2.262157 on 9 (any t table).
    assert SC.tdist2(2.228139, 10) == pytest.approx(0.05, abs=1e-6)
    assert SC.tdist2(2.262157, 9) == pytest.approx(0.05, abs=1e-6)
    assert SC.tdist2(2.262157, 9.9) == SC.tdist2(2.262157, 9)          # TDIST truncates, as Excel does
    assert SC.tdist2(0, 5) == pytest.approx(1.0) and SC.tdist2(3.0, 0.5) is None


def test_pearson_gives_none_where_correl_gives_an_error():
    assert SC.pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert SC.pearson([1, 2, 3], [5, 5, 5]) is None and SC.pearson([1], [2]) is None


def _quarterly(seed, years=40, start=2000 * 12):
    rnd = random.Random(seed)
    level, out = 0.0, {}
    for i in range(years * 4):
        level = 0.6 * level + rnd.gauss(0, 1)
        out[start + 3 * i] = level
    return out


def test_a_series_that_follows_another_by_a_year_holds_at_twelve_months_and_nowhere_else_strongly():
    first = _quarterly(1)
    second = {m + 12: v for m, v in first.items()}                        # the same changes a year later
    rows, level = SC.lead_test(first, second, LEADS, STARTS, P, MIN_PAIRS)
    best = SC.strongest(rows)
    assert best["lead"] == 12 and best["holds"] and SC.verdict(best) == "holds"
    assert level == pytest.approx(P / sum(r["tested"] for r in rows))
    assert all(min(r["ns"]) >= MIN_PAIRS for r in rows if r["tested"])


def test_two_unrelated_series_hold_nowhere():
    rows, _ = SC.lead_test(_quarterly(2), _quarterly(3), LEADS, STARTS, P, MIN_PAIRS)
    assert not any(r["holds"] for r in rows)


def test_the_lead_spoken_of_is_one_that_holds_before_a_stronger_one_that_misses():
    rows = [{"lead": 6, "tested": True, "avg": 0.74, "holds": False, "same_sign": True, "holds_in": 3},
            {"lead": 12, "tested": True, "avg": 0.71, "holds": True, "same_sign": True, "holds_in": 4},
            {"lead": 0, "tested": False, "avg": None, "holds": False, "same_sign": False, "holds_in": None}]
    assert SC.strongest(rows)["lead"] == 12
    rows[1]["holds"] = False
    assert SC.strongest(rows)["lead"] == 6 and SC.verdict(SC.strongest(rows)) == "near miss"


def test_a_near_miss_needs_the_same_sign_everywhere_and_one_pass_at_least():
    row = {"holds": False, "same_sign": True, "holds_in": 2}
    assert SC.verdict(row) == "near miss"
    assert SC.verdict(dict(row, holds_in=0)) is None                     # the firm: "Only 1 of 4 or more"
    assert SC.verdict(dict(row, same_sign=False)) is None and SC.verdict(None) is None


def test_a_lead_without_a_p_at_every_starting_point_is_not_tested():
    # Two series that each run on strongly from year to year leave too few effective pairs on a short span.
    rnd = random.Random(4)
    slow = {}
    level = 0.0
    for i in range(7 * 4):
        level = 0.97 * level + rnd.gauss(0, 0.05) + 0.2
        slow[2000 * 12 + 3 * i] = level
    other = {m: v * 1.1 + rnd.gauss(0, 0.01) for m, v in slow.items()}
    rows, _ = SC.lead_test(slow, other, [0], STARTS, P, MIN_PAIRS)
    assert min(rows[0]["ns"]) >= MIN_PAIRS and None in rows[0]["ps"] and not rows[0]["tested"]


def test_screen_tries_every_economic_series_against_every_bank_series():
    series = {"a": _quarterly(5), "b": _quarterly(6), "bank 1": _quarterly(7)}
    series["bank 2"] = {m + 12: v for m, v in series["a"].items()}
    settings = {"compare_leads": LEADS, "compare_starts": STARTS, "compare_p": P, "compare_min_pairs": MIN_PAIRS}
    found, tried = SC.screen(series, ["a", "b"], ["bank 1", "bank 2"], settings)
    assert tried == 4
    assert [(x["economic"], x["bank"], x["verdict"], x["row"]["lead"]) for x in found if x["verdict"] == "holds"] \
        == [("a", "bank 2", "holds", 12)]
    chance = SC.by_chance(series, ["a", "b"], ["bank 1", "bank 2"], settings)
    assert set(chance) == set(SC.SHIFTS) | {"reverse"}
    assert all(v == {"holds": 0, "near miss": v["near miss"]} for v in chance.values())


def test_a_bank_series_is_moved_out_of_line_keeping_every_reading_and_its_calendar_month_when_shifted():
    x = _quarterly(8, years=10)
    for how in SC.SHIFTS:
        moved = SC.scrambled(x, how)
        assert sorted(moved.values()) == sorted(x.values()) and {m % 12 for m in moved} == {m % 12 for m in x}
        assert all(moved.get(m) != x[m] for m in list(x)[:5])
    mirrored = SC.scrambled(x, "reverse")
    lo, hi = min(x), max(x)
    assert mirrored[lo] == x[hi] and mirrored[hi] == x[lo]
