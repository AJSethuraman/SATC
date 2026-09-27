"""One comparison decides the verdict, the dollars and materiality, and profit reads literally (the firm,
26 Sep 2026).

"That works": the dollars were measured against the whole book's rate while the reading followed Control's
"judged against", and materiality was applied to the book's dollars. So a pocket in a high-loss band could
clear materiality against the book while being in line with its neighbours. Now the setting picks one of
two dollar figures, over the rest of the book and over the rest of its band, for the reading, materiality and
the ranking. Since Option A (the firm, 26 Sep 2026: "i think this makes most seense") the book's figure is
over the rest of the book, the same rest its gap and test are taken against; the dollars over the whole book
stay only as the tie-out, which adds to zero (OC-4).

"yes I prefer it to be literal": profit and contribution say their gap, "short of its band by 0.80 points
($16,000)", instead of "keeps less".

The book: two score bands of three channels, 400 loans of $1,000 each. The low band goes bad at about 10%,
the high band at 1%. Low / A is 42 bad of 400: in line with its band, far over the book. High / C is 16 bad
of 400: four times its band, under the book."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from recalc import calculated
from conftest import cube, row, table
from pocketbook import book, cli, engine, house, live, results
import tabs

BANDS = [{"name": "score", "field": "SCORE", "edges": [650]}]
LINE = 5_000                              # the materiality line, in GCO dollars


def _bench(compare_to: str, **more) -> dict:
    return {"min_units": 30, "min_events": 5, "worse_at": 1.25, "better_at": 0.8, "confidence": 0.95, "power": 0.8,
            "compare_to": compare_to, "many_tests": "none", "materiality": LINE, "shuffles": 500, **more}


def _rows():
    out, i = [], 0
    for score, chan, bad in ((600, "A", 42), (600, "B", 40), (600, "C", 40), (700, "A", 4), (700, "B", 4),
                             (700, "C", 16)):
        for j in range(400):
            flag = int(j < bad)
            out.append(row(i, score, chan, 1000, flag, 1000 * flag, 50 - 1000 * flag))
            i += 1
    return out


def _run(compare_to: str, **more):
    return engine.run(cube(bands=BANDS, benchmark=_bench(compare_to, **more)), table(_rows()))


def _gco(res, band: int, chan: str):
    g = res.grids[0]
    return g.cell(g.band_labels[band], chan).rates["gco_rate"]


def test_by_hand():
    """The dollar figures, worked out by hand. Over the rest of the book (Option A): 42,000 less 104 / 2,000 of
    $400,000. Over its band: 42,000 less 80 / 800 of $400,000 (the rest of its band, as vs_band is taken).
    Over the whole book, the tie-out only: 42,000 less 146 / 2,400 of $400,000."""
    res = _run("peers")
    low_a, high_c = _gco(res, 0, "A"), _gco(res, 1, "C")
    assert low_a.excess_rest == pytest.approx(42_000 - 104 / 2000 * 400_000)     # 21,200
    assert low_a.excess_band == pytest.approx(42_000 - 0.10 * 400_000)           # 2,000
    assert high_c.excess_rest == pytest.approx(16_000 - 130 / 2000 * 400_000)    # -10,000
    assert high_c.excess_band == pytest.approx(16_000 - 8 / 800 * 400_000)       # 12,000
    assert low_a.excess == pytest.approx(42_000 - 146 / 2400 * 400_000)          # 17,667: the tie-out's
    # both figures are there whatever the setting: only which one decides changes
    other = _gco(_run("topline"), 0, "A")
    assert (other.excess_rest, other.excess_band) == pytest.approx((low_a.excess_rest, low_a.excess_band))


def test_the_tie_out_still_adds_to_zero_over_the_whole_book():
    """OC-4's excess over the whole book stays as Check's tie-out: across a grid it adds to zero, and the Run
    checks it (the tie-out raises otherwise). The dollars that decide are the rest of the book's."""
    res = _run("topline")
    inner = [c.rates["gco_rate"] for _, c in res.grids[0].inner()]
    assert sum(s.excess for s in inner) == pytest.approx(0, abs=1e-6)
    assert all(s.dollars == s.excess_rest != s.excess for s in inner)
    assert res.tie_outs > 0


def test_judged_against_its_band_the_band_decides_the_flag_the_dollars_and_materiality():
    """In line with its neighbours: not flagged, not material, small dollars over its band, while its large
    dollars over the book are still there to see. The pocket four times its band is flagged and material."""
    res = _run("peers")
    low_a, high_c = _gco(res, 0, "A"), _gco(res, 1, "C")
    assert low_a.by_band and low_a.flag == engine.IN_LINE
    assert low_a.dollars == low_a.excess_band < LINE < low_a.excess
    assert low_a.material is False
    assert high_c.by_band and high_c.flag == engine.WORSE
    assert high_c.dollars == high_c.excess_band >= LINE and high_c.material is True


def test_judged_against_the_book_the_reverse():
    res = _run("topline")
    low_a, high_c = _gco(res, 0, "A"), _gco(res, 1, "C")
    assert not low_a.by_band and low_a.flag == engine.WORSE
    assert low_a.dollars == low_a.excess_rest >= LINE and low_a.material is True        # Option A
    assert not high_c.by_band and high_c.flag in (engine.BETTER, engine.UNSURE_BETTER)       # not worse
    assert high_c.dollars == high_c.excess_rest < 0 and high_c.material is False
    assert high_c.excess_band >= LINE                                            # still worked out, for reference


def _tab(res, tab: str, **picks):
    """One result tab for this run, its dropdowns set, calculated: its verdicts and dollars are formulas (OC-40).
    The tab as written rides along as .formulas."""
    wb = Workbook()
    results.write(wb, res, "now")
    for label, value in picks.items():
        tabs.dropdown(wb[tab], label).value = value
    ws = calculated(wb[tab])
    ws.formulas = wb[tab]
    return ws


@pytest.mark.parametrize("compare_to, rest", [("peers", "Rest of band"), ("topline", "Rest of book")])
def test_pockets_ranks_by_the_deciding_dollars(compare_to, rest):
    """Worse pockets first by the dollars that decide, then the rest by theirs, then those losing more only
    against the other comparison (so a change of Judged against finds them). The other comparison's figure is
    no longer beside each row (the redesign's columns); it stays on _pockets and the command line."""
    res = _run(compare_to)
    ws = _tab(res, results.POCKETS, measure="Charge-offs")
    rows = tabs.pockets(ws)
    head = tabs.header_row(ws, results.K_NUM, "#")
    assert ws.cell(row=head, column=results.K_REST).value == rest
    got = {(x["band"], x["seg"]): x for x in rows}
    lo, hi = (f"SCORE {x}" for x in res.grids[0].band_labels)
    worse = [x["excess"] for x in rows if x["worse"] == "Yes"]
    rest_ = [x["excess"] for x in rows if x["worse"] != "Yes"]
    assert [x["worse"] == "Yes" for x in rows] == sorted((x["worse"] == "Yes" for x in rows), reverse=True)
    assert worse == sorted(worse, reverse=True) and all(v > 0 for v in worse)
    positive = [v for v in rest_ if v > 0]
    assert rest_[:len(positive)] == sorted(positive, reverse=True)          # losing more now, then the others
    if compare_to == "peers":
        a = got[(lo, "A")]
        assert a["excess"] == pytest.approx(2_000) and (a["worse"], a["material"]) == ("No", "No")
        c = got[(hi, "C")]
        assert (c["worse"], c["material"]) == ("Yes", "Yes") and rows[0] is c        # the biggest over its band
    else:
        a = got[(lo, "A")]
        assert a["excess"] == pytest.approx(21_200) and a["material"] == "Yes"
        c = got[(hi, "C")]                         # under the rest of the book, over its band: last, not worse
        assert c["excess"] == pytest.approx(-10_000) and c["worse"] == "No" and rows[-1] is c


def test_paid_cost_kept_dollars_are_the_engines():
    """Before, this tab worked out its own dollars against the rest of the book; it shows the engine's, so it
    can't disagree with Pockets or materiality."""
    for compare_to, times in (("peers", "× band"), ("topline", "× book")):
        res = _run(compare_to)
        ws = _tab(res, results.PCK)
        head = tabs.header_row(ws, results.C_TOG, "Together")
        assert ws.cell(row=head, column=results.C_COST).value == times
        rows = {(x["band"], x["seg"]): x for x in tabs.pck(ws)}
        lo, hi = res.grids[0].band_labels
        s = _gco(res, 0, "A")
        assert rows[(lo, "A")]["cost_d"] == pytest.approx(s.dollars)
        assert s.dollars == pytest.approx(s.excess_band if compare_to == "peers" else s.excess_rest)
        # profit's dollars are over, so a shortfall is negative: the engine's shortfall, turned round
        p = res.grids[0].cell(lo, "A").rates["ranr_rate"]
        assert rows[(lo, "A")]["kept_d"] == pytest.approx(-p.dollars)


def test_a_pocket_alone_in_its_band_has_no_dollars_over_it_and_is_ranked_by_the_books():
    rows = [row(i, 800, "A", 1000, int(i < 20), 1000 * int(i < 20), 50) for i in range(100)] + _rows()
    res = engine.run(cube(bands=[{"name": "score", "field": "SCORE", "edges": [650, 750]}],
                          benchmark=_bench("peers")), table(rows))
    g = res.grids[0]
    s = g.cell(g.band_labels[-1], "A").rates["gco_rate"]
    assert s.alone and not s.by_band and s.excess_band is None and s.dollars == s.excess_rest > LINE and s.material
    rows = tabs.pockets(_tab(res, results.POCKETS, measure="Charge-offs"))
    got = [x for x in rows if x["band"] == f"SCORE {g.band_labels[-1]}"]
    assert got and got[0]["excess"] == pytest.approx(s.excess_rest) and got[0]["material"] == "Yes"


def test_check_says_which_comparison_decides():
    for compare_to, opens in (("peers", "The rest of its band decides"), ("topline", "The rest of the book decides")):
        res = _run(compare_to)
        wb = Workbook()
        book._record(wb, res, Path("loans.csv"))
        ws = calculated(wb["Record"])
        check = tabs.record(ws)
        said = check["Decides each pocket"]
        assert said.startswith(opens) and "flag, its dollars and whether it is material" in said
        assert ("alone in its band is compared with the rest of the book" in said) == (compare_to == "peers")


def test_the_command_line_ranks_by_the_deciding_dollars():
    out = cli.report(_run("peers"))
    gco = out[out.index("Grid score x chan - gco_rate"):]
    gco = gco[gco.index("Where it bleeds"):gco.index("Materiality evidence")]
    assert "excess GCO over the rest of its band's rate" in gco
    # four times its band, under the book: listed, material, with the book's figure beside it
    assert "650 - 700 / C: 12,000, 400 loans\n      for reference, against the book: -10,000" in gco
    # in line with its band, far over the book: below the line, by its band's dollars
    assert "below the materiality line: 1 pocket, 2,000 together" in gco


# --------------------------------------------------------------------------
# The literal wording


PTS = engine.ProfitLine("points", 0.0025)
TEST = engine.ProfitLine("test")


@pytest.mark.parametrize("word, gap, dollars, against, line, p, want", [
    (engine.WORSE, -0.008, 16_000, "its band", PTS, 0.001, "short of its band by 0.80 points ($16,000)"),
    (engine.BETTER, 0.04, -150_000, "the book", PTS, 0.001, "ahead of the book by 4.00 points ($150,000)"),
    (engine.IN_LINE, -0.0012, 1_200, "its band", PTS, 0.001, "within 0.25 points of its band (-0.12)"),
    (engine.IN_LINE, -0.008, 16_000, "its band", TEST, 0.3, "-0.80 points against its band, not significant"),
    (engine.UNSURE_WORSE, -0.008, 16_000, "its band", PTS, 0.3,
     "short of its band by 0.80 points ($16,000) (not significant)"),
    (engine.UNSURE_BETTER, 0.008, -16_000, "the book", PTS, 0.3,
     "ahead of the book by 0.80 points ($16,000) (not significant)"),
    (engine.IN_LINE, 0.0012, -1_200, "the book", engine.ProfitLine("dollars", 5_000), 0.001,
     "within $5,000 of the book (+0.12 points)"),
    (engine.FEW, -0.01, 10, "its band", PTS, None, engine.FEW),
])
def test_the_profit_reading_says_the_gap(word, gap, dollars, against, line, p, want):
    assert engine.literal(word, gap, dollars, against, line, p) == want


def test_the_reading_names_the_comparison_that_decides_it():
    """Its gap and its dollars are the same comparison's: the band's under the band, the book's otherwise."""
    for compare_to, against in (("peers", "its band"), ("topline", "the book")):
        res = _run(compare_to, revenue_line=0.25)
        s = res.grids[0].cell(res.grids[0].band_labels[1], "C").rates["ranr_rate"]
        words = engine.said(s, engine.profit_line(res.config.benchmark))
        gap = s.vs_band if compare_to == "peers" else s.vs_rest
        assert words.startswith(f"{'short of' if gap < 0 else 'ahead of'} {against} by {abs(gap) * 100:.2f} points")
        assert f"(${abs(s.dollars):,.0f})" in words


def test_no_verdict_word_is_left_on_the_profit_side():
    """The literal wording is the reading of record on _pockets (and the command line); the tabs show the gap
    and its dollars in columns, and Worse? says whether it counts."""
    res = _run("peers", revenue_line=0.25)
    wb = Workbook()
    results.write(wb, res, "now")
    v = calculated(wb[results.POCKETS]).parent
    reads = [r[live.P_SAID - 1].value for r in v[live.POCKETS].iter_rows(min_row=live.P_FIRST)
             if r[live.P_MEASURE - 1].value in ("ranr_rate", "contribution_rate")]
    assert reads and all(isinstance(x, str) for x in reads)
    for x in reads:
        assert not any(w in x for w in ("keeps", "pays", "about the same")), x
        assert x.startswith(("short of ", "ahead of ", "within ", "too few")), x
    for x in tabs.pck(v[results.PCK]):
        assert all(isinstance(x[k], (int, float)) for k in ("paid", "paid_d", "kept", "kept_d")), x


def test_a_real_shortfall_is_pink_and_an_unsure_one_canvas():
    """Worse? is Yes on a shortfall past the line with a p-value under the bar, and pink with crimson words;
    Not sure is CANVAS (the redesign's Global rule 9)."""
    res = _run("peers", revenue_line=0.25)
    ws = _tab(res, results.POCKETS, measure="Kept after losses")
    rows = tabs.pockets(ws)
    assert any(x["worse"] == "Yes" and x["gap"] < 0 for x in rows)
    rules = [(r.formula[0], r.dxf) for rng in ws.formulas.conditional_formatting
             if str(rng.sqref).startswith(results.col(results.K_WORSE)) for r in rng.rules]
    yes = next(d for f, d in rules if f.endswith(f'="{live.YES}")'))
    assert yes.fill.fgColor.rgb.endswith(house.ALERT_FG) and yes.font.color.rgb.endswith(house.CRIMSON) and yes.font.b
    unsure = next(d for f, d in rules if f.endswith(f'="{live.NOT_SURE}")'))
    assert unsure.fill.fgColor.rgb.endswith(house.CANVAS)

