"""The third layer: split every pocket by another column. The firm, 25 Sep 2026:
FICO band by asset class, then "what happens when clients through the door in
those bands act and what we can gleam from their revolving debt"."""

import copy

import pytest

from origination_cube import config as cfgmod
from origination_cube import engine, stats, synth
from origination_cube.ingest import read_table


@pytest.fixture(scope="module")
def planted(tmp_path_factory):
    cfg, data = synth.write(tmp_path_factory.mktemp("split"), n=30000)
    return cfgmod.load(cfg).raw, read_table(data)


def _run(raw, table, field, how):
    r = copy.deepcopy(raw)
    r["dimensions"] = [{"name": "asset", "field": "ASSET_CLASS"}]
    r["split"] = {"field": field, "how": how}
    return engine.run(cfgmod.parse(r), table)


def test_the_planted_revolving_debt_effect_is_found(planted):
    """Within a score band and asset class, the borrower above the usual debt for
    the score goes bad 1.8x as often (synth.py). Split at each pocket's own
    median, the pooled odds ratio must find it, in every pocket, steadily."""
    res = _run(*planted, "REV_DEBT", "own_median")
    pooled = res.grids[0].split_pooled["outcome_loans"]
    assert 1.5 < pooled["odds"] < 2.2 and pooled["odds_lo"] > 1
    assert pooled["odds_p"] < 1e-6
    assert pooled["high_worse"] >= pooled["pockets"] - 1
    assert pooled["steady_p"] > 0.01                       # the plant is the same in every pocket
    assert res.grids[0].split_pooled["gco_rate"]["ratio"] > 1.4
    # found by rendering: the booked-dollar outcome printed the loan-count odds as its own
    booked = res.grids[0].split_pooled["outcome_booked"]
    assert "odds" not in booked and booked["ratio"] > 1.3


def test_a_column_with_no_effect_comes_out_near_one(planted):
    """Loan size carries no plant. Across five seeds its split gave odds of 0.90
    to 1.00 (measured 25 Sep 2026), and on this seed p = 0.018: one in twenty
    tests of nothing crosses 5% by luck, which is why the many-tests allowance
    exists. So the check is the size of the effect, not a single p."""
    res = _run(*planted, "ORIG_BAL", "own_median")
    pooled = res.grids[0].split_pooled["outcome_loans"]
    assert 0.8 < pooled["odds"] < 1.2
    planted_odds = _run(*planted, "REV_DEBT", "own_median").grids[0].split_pooled["outcome_loans"]["odds"]
    assert planted_odds > 1.5


def test_each_pocket_is_halved_at_its_own_median(planted):
    """Not the book's median: revolving debt moves with the score, so one cut
    for everyone would put nearly all of a low band in one half."""
    res = _run(*planted, "REV_DEBT", "own_median")
    g = res.grids[0]
    for (b, d), c in g.inner():
        hi, lo = g.split_cells.get((b, d, engine.HIGH)), g.split_cells.get((b, d, engine.LOW))
        if hi and lo:
            assert abs(hi.rows - lo.rows) <= 1, (b, d, hi.rows, lo.rows)


def test_every_pocket_is_the_sum_of_its_halves(planted):
    res = _run(*planted, "REV_DEBT", "own_median")
    g = res.grids[0]
    for (b, d), c in g.inner():
        parts = [p for (bb, dd, _), p in g.split_cells.items() if (bb, dd) == (b, d)]
        assert sum(p.rows for p in parts) == c.rows
    # and the tie-out itself checks it, and can fail
    k = next(iter(g.split_cells))
    g.split_cells[k].rates["gco_rate"].num += 1
    with pytest.raises(engine.TieOutError, match="split gco_rate numerator"):
        engine.tie_out(g, res.total, res.measures, res.rows)


def test_each_value_gives_one_layer_per_value(planted):
    raw, table = planted
    r = copy.deepcopy(raw)
    r["split"] = {"field": "ASSET_CLASS", "how": "each_value"}
    res = engine.run(cfgmod.parse(r), table)
    g = res.grids[0]                                       # fico x channel, one layer per asset class
    assert g.split_labels == ["1", "2", "3", "4"]
    assert not g.split_pooled                               # layers are shown, not paired


def test_the_statistics_against_known_values():
    assert stats.chi2_sf(3.841458820694124, 1) == pytest.approx(0.05, abs=1e-9)
    assert stats.chi2_sf(20, 10) == pytest.approx(0.029253, abs=1e-6)
    strata = [(20, 80, 10, 90), (40, 60, 25, 75)]
    o, lo, hi = stats.mantel_haenszel(strata, 1.959963984540054)
    # MH: sum(ad/n) / sum(bc/n) = (1800/200 + 3000/200) / (800/200 + 1500/200)
    assert o == pytest.approx((9 + 15) / (4 + 7.5))
    assert 0 < stats.cmh_p(strata) < 0.01
    steady, k = stats.steadiness_p(strata, o)
    assert k == 2 and steady > 0.5                         # both strata near OR 2


def test_halves_under_the_minimum_are_not_compared_or_counted(planted):
    """The third walk, defect 4: two halves of 27 loans were tested under a 30-loan floor."""
    raw, table = planted
    r = copy.deepcopy(raw)
    r["benchmark"]["min_units"] = 400
    r["dimensions"] = [{"name": "asset", "field": "ASSET_CLASS"}]
    r["split"] = {"field": "REV_DEBT", "how": "own_median"}
    res = engine.run(cfgmod.parse(r), table)
    g = res.grids[0]
    for got in g.split_compare.values():
        idx, p, nh, nl = got["outcome_loans"]
        if nh < 400 or nl < 400:
            assert idx is None and p is None
    tested = sum(1 for got in g.split_compare.values() if got["outcome_loans"][0] is not None)
    assert g.split_pooled["outcome_loans"]["pockets"] == tested


def test_the_split_says_how_closely_it_moves_with_each_band(planted):
    res = _run(*planted, "REV_DEBT", "own_median")
    assert res.split_moves_with["FICO"] < -0.3                 # debt runs higher as the score falls
    assert res.three_way and all(" / " in g.dimension for g in res.three_way)


def test_the_split_luck_figures_carry_the_allowance(planted):
    """Asked on 25 Sep 2026: every "Luck alone" figure is after the allowance for
    many tests, the split's included."""
    raw, table = planted
    r = copy.deepcopy(raw)
    r["dimensions"] = [{"name": "asset", "field": "ASSET_CLASS"}]
    r["split"] = {"field": "REV_DEBT", "how": "own_median"}
    r["benchmark"]["many_tests"] = "none"
    plain = engine.run(cfgmod.parse(r), table).grids[0].split_compare
    r["benchmark"]["many_tests"] = "bonferroni"
    held = engine.run(cfgmod.parse(r), table).grids[0].split_compare
    tested = [k for k in plain if plain[k]["outcome_loans"][1] is not None]
    assert tested
    for k in tested:
        assert held[k]["outcome_loans"][1] == pytest.approx(min(1.0, plain[k]["outcome_loans"][1] * len(tested)))


def test_statistics_md_a5_to_a8_through_the_split():
    """statistics.md's two pockets, run through the engine's split: pocket A,
    high half 8 bad of 100 and low half 4 of 100; pocket B, 20 of 200 and 12 of
    200. A7: actual against expected with the low half's rate is 28 / 16 = 1.75
    (the pooled rate would give 28 / 22 = 1.27). A5: odds 1.829. A6: CMH with no
    continuity correction, p 0.060, now shown beside the odds. A8: p 0.81."""
    from conftest import cube, row, table
    rows, i = [], 0
    for chan, n, high_bad, low_bad in (("A", 200, 8, 4), ("B", 400, 20, 12)):
        for k in range(1, n + 1):                        # DEBT 1..n: the high half is above the median
            high = k > n // 2
            bad = (k - n // 2 <= high_bad) if high else (k <= low_bad)
            r = row(i, 600, chan, 100, int(bad), 50 if bad else 0, 10)
            r["DEBT"] = k
            rows.append(r)
            i += 1
    bench = {"min_units": 2, "min_events": 1, "worse_at": 1.25, "better_at": 0.8, "confidence": 0.95,
             "power": 0.8, "compare_to": "peers", "many_tests": "none", "materiality": "none"}
    res = engine.run(cube(split={"field": "DEBT", "how": "own_median"}, benchmark=bench), table(rows))
    g = res.grids[0]
    pooled = g.split_pooled["outcome_loans"]
    assert pooled["pockets"] == 2 and pooled["ratio"] == pytest.approx(28 / 16) and round(pooled["ratio"], 2) == 1.75
    assert round(pooled["odds"], 3) == 1.829
    assert round(pooled["odds_p"], 3) == 0.060
    assert round(pooled["steady_p"], 2) == 0.81
    # each pocket's halves by A1, pooled
    idx, p, nh, nl = g.split_compare[("600 - 649", "A")]["outcome_loans"]
    assert (nh, nl) == (100, 100) and idx == pytest.approx(2.0)
    assert p == pytest.approx(stats.two_prop_z(8, 100, 4, 100)[1], rel=1e-12)
    # a dollar rate's split test is the within-pocket shuffle (B2)
    gco = g.split_pooled["gco_rate"]
    assert gco["shuffles"] == 2_000 and 0 < gco["ratio_p"] <= 1 and gco["ratio_p"] == (gco["ratio_hits"] + 1) / 2_001
