"""A new column made from two others (NEXT-GOAL 3.9), what an amount is over
(3.10) and what it measures (3.11), and the synthetic book that plants a ratio
effect to test them end to end.

A new column is one column divided by another on each loan. It is made before
anything reads the extract, so it can be a band or split the pockets like any
number column. A zero or blank bottom gives a blank value, never a zero and
never infinity, and each is counted by why. Periods that disagree are warned
about on Check and never stop the run."""

from bisect import bisect_right
from datetime import date

import pytest

from conftest import cube, row, table
from origination_cube import config as cfgmod
from origination_cube import engine, synth

RATIO = [{"name": "SCORE_TO_BAL", "top": "SCORE", "bottom": "BAL"}]
BAND = [{"name": "ratio", "field": "SCORE_TO_BAL", "edges": [3]}]


def test_a_new_column_is_one_column_over_another_and_can_be_cut(book):
    res = engine.run(cube(derived=RATIO, bands=BAND), table(book))
    made = {r["ID"]: r["SCORE_TO_BAL"] for r in res.table.rows}
    assert made == {"L1": 6.0, "L2": 6.0, "L3": 3.5, "L4": 3.5, "L5": 1.5, "L6": 0.7}
    g = res.grids[0]
    assert g.band == "ratio" and g.band_labels == ["0 - 2", "3 - 6"]
    assert g.cell("3 - 6", "A").rates["loans"].units == 3 and g.cell("0 - 2", "B").rates["loans"].units == 2
    assert res.derived[0].made == 6 and not res.derived[0].blank
    assert res.table.columns[-1] == "SCORE_TO_BAL" and "SCORE_TO_BAL" not in book[0]   # the extract is untouched


def test_a_zero_or_blank_bottom_gives_a_blank_value_counted_by_why(book):
    book[1]["BAL"] = 0
    book[2]["BAL"] = ""
    book[3]["SCORE"] = "n/a"
    res = engine.run(cube(derived=RATIO, bands=BAND), table(book))
    made = {r["ID"]: r["SCORE_TO_BAL"] for r in res.table.rows}
    assert made["L2"] is None and made["L3"] is None and made["L4"] is None
    assert dict(res.derived[0].blank) == {"BAL is zero": 1, "BAL blank": 1, "SCORE blank": 1}
    assert res.derived[0].made == 3
    # the blanks are their own row in the grid, counted, never read as a zero
    assert res.grids[0].cell(engine.BLANK_LABEL, engine.ALL).rows == 3


def test_a_missing_rule_on_the_bottom_applies_to_the_new_column(book):
    res = engine.run(cube(derived=RATIO, missing={"BAL": {"values": [100]}}, bands=BAND), table(book))
    assert dict(res.derived[0].blank) == {"BAL missing by rule": 2}


def test_a_new_column_can_use_one_made_before_it(book):
    two = RATIO + [{"name": "PER_POINT", "top": "SCORE_TO_BAL", "bottom": "SCORE"}]
    res = engine.run(cube(derived=two), table(book))
    assert res.table.rows[0]["PER_POINT"] == pytest.approx(6.0 / 600)


def test_a_new_column_made_from_an_outcome_is_not_cut_by(book):
    """GCO over the booked amount, cut into bands, puts every loan with GCO in the top band: cutting by it
    cuts the book by its own outcome, as cutting by GCO would."""
    gco = [{"name": "GCO_TO_BAL", "top": "GCO", "bottom": "BAL"},
           {"name": "AGAIN", "top": "GCO_TO_BAL", "bottom": "SCORE"}]
    bands = [{"name": "score", "field": "SCORE", "edges": [650]}, {"name": "g", "field": "GCO_TO_BAL", "edges": [0.3]},
             {"name": "a", "field": "AGAIN", "edges": [0.001]}]
    res = engine.run(cube(derived=gco, bands=bands), table(book))
    assert [g.band for g in res.grids] == ["score"]
    assert any("`GCO_TO_BAL` is not cut by: it is made from `GCO`, the top of a rate" in w for w in res.warnings)
    assert any("`AGAIN` is not cut by: it is made from `GCO`" in w for w in res.warnings)
    with pytest.raises(engine.DataRefused, match="splitting by it would split the book by its own outcome"):
        engine.run(cube(derived=gco, split={"field": "GCO_TO_BAL", "how": "own_median"}), table(book))


def test_a_new_column_named_like_a_column_of_the_extract_is_refused(book):
    with pytest.raises(engine.DataRefused, match="`SCORE` has the name of a column the extract already has"):
        engine.run(cube(derived=[{"name": "SCORE", "top": "GCO", "bottom": "BAL"}]), table(book))
    with pytest.raises(engine.ColumnsMissing, match="SALES` \\(used by new column SCORE_TO_SALES\\)"):
        engine.run(cube(derived=[{"name": "SCORE_TO_SALES", "top": "SCORE", "bottom": "SALES"}]), table(book))


@pytest.mark.parametrize("entry, says", [
    ({"name": "X", "top": "GCO"}, "needs `bottom:`"),
    ({"name": "X", "top": "GCO", "bottom": "GCO"}, "over itself is 1 on every loan"),
    ({"name": "GCO", "top": "GCO", "bottom": "BAL"}, "the name `GCO` is taken"),
    ({"name": "X", "top": "GCO", "bottom": "BAL", "over": 12}, "unknown key `over`"),
])
def test_a_new_column_the_file_gets_wrong_is_refused(entry, says):
    with pytest.raises(cfgmod.ConfigError, match=says):
        cube(derived=[entry])


def _columns(**extra):
    base = {"ID": "key", "BAL": "booked", "BAD": "outcome", "GCO": "gco", "RANR": "ranr", "SCORE": "fico",
            "CHAN": "category"}
    base.update(extra)
    return dict(columns=base, columns_confirmed=True, key=None, booked=None, outcome=None, gco=None, ranr=None)


def test_periods_that_disagree_warn_and_never_stop(book):
    for r in book:
        r["INC"], r["SAL"] = 1200, 100
    res = engine.run(cube(derived=[{"name": "INC_TO_SAL", "top": "INC", "bottom": "SAL"}],
                          **_columns(INC={"means": "amount", "period": "per_year"},
                                     SAL={"means": "amount", "period": "per_month"})), table(book))
    assert res.table.rows[0]["INC_TO_SAL"] == 12.0                     # never rescaled: which is right is ours
    assert any("INC_TO_SAL divides `INC` (per year) by `SAL` (per month): they aren't over the same period, so "
               "it reads 12 times a like-for-like ratio" in w for w in res.warnings)
    res = engine.run(cube(derived=[{"name": "INC_TO_SAL", "top": "INC", "bottom": "SAL"}],
                          **_columns(INC={"means": "amount", "period": "per_year"},
                                     SAL={"means": "amount", "period": "per_year"})), table(book))
    assert not any("same period" in w for w in res.warnings)


def test_a_period_is_for_an_amount_and_a_definition_is_kept():
    with pytest.raises(cfgmod.ConfigError, match="a period is for an amount; `CHAN` means category"):
        cube(**_columns(CHAN={"means": "category", "period": "per_year"}))
    with pytest.raises(cfgmod.ConfigError, match="period must be one of per_year, per_month, one_time"):
        cube(**_columns(INC={"means": "amount", "period": "yearly"}))
    c = cube(**_columns(INC={"means": "amount", "period": "per_year",
                             "definition": "household   income, trailing twelve"}))
    assert c.periods == {"INC": "per_year"} and c.definitions == {"INC": "household income, trailing twelve"}


# --------------------------------------------------------------------------
# The synthetic book


@pytest.fixture(scope="module")
def dated_book():
    return synth.make_rows(40000, 7, dated=True)


def test_the_dated_book_keeps_every_other_plant_loan_for_loan(dated_book):
    plain = synth.make_rows(40000, 7)
    assert all(a[k] == b[k] for a, b in zip(dated_book, plain) for k in synth.COLUMNS)


def test_the_dated_book_has_an_outcome_date_on_bad_loans_only(dated_book):
    as_of = date.fromisoformat(synth.AS_OF)
    months = []
    for r in dated_book:
        made = date.fromisoformat(r["ORIG_DATE"])
        assert made <= as_of
        if r["BAD_FLAG"] == 1:
            went = date.fromisoformat(r["BAD_DATE"])
            assert made <= went <= as_of
            months.append(engine.months_between(made, went))
        else:
            assert r["BAD_DATE"] == ""
    months.sort()
    assert 6 <= months[len(months) // 2] <= 12 and months[-1] >= 36          # a realistic spread, with a tail
    assert sum(r["SALES"] == 0 for r in dated_book) == 40 and sum(r["SALES"] == "" for r in dated_book) == 40


def test_the_dated_book_plants_the_ratio_effect(dated_book):
    """bad odds x3 above 2.0 and x2 below 0.1, against the middle (docs/scout-vs-measure.py)."""
    edges = [0.1, 0.25, 0.5, 1.0, 2.0]
    loans, bad = [0] * 6, [0] * 6
    for r in dated_book:
        if r["BAD_FLAG"] in (0, 1) and r["SALES"] not in ("", 0):
            g = bisect_right(edges, r["INCOME"] / r["SALES"])
            loans[g] += 1
            bad[g] += r["BAD_FLAG"]
    odds = [b / (n - b) for b, n in zip(bad, loans)]
    ref = odds[2]
    assert 1.6 <= odds[0] / ref <= 2.8
    assert 2.3 <= odds[5] / ref <= 3.7
    assert all(0.8 <= odds[k] / ref <= 1.25 for k in (1, 3, 4))
