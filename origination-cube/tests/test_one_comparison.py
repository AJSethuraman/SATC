"""One comparison decides the verdict, the dollars and materiality, and profit reads literally (the firm,
26 Sep 2026).

"That works": the dollars were measured against the whole book's rate while the reading followed Control's
"judged against", and materiality was applied to the book's dollars. So a pocket in a high-loss band could
clear materiality against the book while being in line with its neighbours. Now the setting picks one of
two dollar figures, over the book and over its band, for the reading, materiality and the ranking, and
the other stays on the row for reference.

"yes I prefer it to be literal": profit and contribution say their gap, "short of its band by 0.80 points
($16,000)", instead of "keeps less".

The book: two score bands of three channels, 400 loans of $1,000 each. The low band goes bad at about 10%,
the high band at 1%. Low / A is 42 bad of 400: in line with its band, far over the book. High / C is 16 bad
of 400: four times its band, under the book."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from conftest import cube, row, table
from origination_cube import book, cli, engine

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
    """The two dollar figures, worked out by hand. Over the book: 42,000 less 42,000 x 146 / 2,400 of $400,000.
    Over its band: 42,000 less 80 / 800 of $400,000 (the rest of its band, as vs_band is taken)."""
    res = _run("peers")
    low_a, high_c = _gco(res, 0, "A"), _gco(res, 1, "C")
    assert low_a.excess == pytest.approx(42_000 - 146 / 2400 * 400_000)          # 17,667
    assert low_a.excess_band == pytest.approx(42_000 - 0.10 * 400_000)           # 2,000
    assert high_c.excess == pytest.approx(16_000 - 146 / 2400 * 400_000)         # -8,333
    assert high_c.excess_band == pytest.approx(16_000 - 8 / 800 * 400_000)       # 12,000
    # both figures are there whatever the setting: only which one decides changes
    other = _gco(_run("topline"), 0, "A")
    assert (other.excess, other.excess_band) == pytest.approx((low_a.excess, low_a.excess_band))


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
    assert low_a.dollars == low_a.excess >= LINE and low_a.material is True
    assert not high_c.by_band and high_c.flag in (engine.BETTER, engine.UNSURE_BETTER)       # not worse
    assert high_c.dollars == high_c.excess < 0 and high_c.material is False
    assert high_c.excess_band >= LINE                                            # still worked out, for reference


def _sheet(res, write):
    ws = Workbook().active
    write(ws, res)
    return ws


def _bleeds(res) -> list[dict]:
    ws = _sheet(res, book._bleeds)
    heads = [c.value for c in ws[4]]
    return [dict(zip(heads, (c.value for c in r))) for r in ws.iter_rows(min_row=5) if r[1].value]


@pytest.mark.parametrize("compare_to, first, other", [("peers", "Excess over its band", "Excess over the book"),
                                                      ("topline", "Excess over the book", "Excess over its band")])
def test_where_it_bleeds_ranks_by_the_deciding_dollars_and_shows_the_other(compare_to, first, other):
    res = _run(compare_to)
    rows = [x for x in _bleeds(res) if x["Measure"] == "GCO per booked dollar"]
    heads = list(rows[0])
    assert heads.index(first) + 1 == heads.index(other)                           # the deciding one first
    firsts = [x[first] for x in rows]
    assert firsts == sorted(firsts, reverse=True) and all(v > 0 for v in firsts)
    got = {(x["Band"], x["Segment"]): x for x in rows}
    lo, hi = res.grids[0].band_labels
    if compare_to == "peers":
        a = got[(lo, "A")]
        assert a[first] == pytest.approx(2_000) and a[other] == pytest.approx(17_667, abs=1)
        assert a["Material"] == "below the line" and a[f"Flag (vs the rest of its band)"] == engine.IN_LINE
        c = got[(hi, "C")]
        assert c["Material"] == "yes" and c["Flag (vs the rest of its band)"] == engine.WORSE
        assert rows[0]["Segment"] == "C" and rows[0]["Band"] == hi                  # the biggest over its band
    else:
        assert (hi, "C") not in got                                               # under the book: not bleeding
        a = got[(lo, "A")]
        assert a["Material"] == "yes" and a[other] == pytest.approx(2_000)


def test_losses_vs_revenue_dollars_are_the_engines_and_the_other_is_beside_them():
    """Before, this tab worked out its own dollars against the rest of the book; now it shows the engine's,
    so it can't disagree with Where it bleeds or materiality."""
    for compare_to in ("peers", "topline"):
        res = _run(compare_to)
        ws = _sheet(res, book._losses_vs_revenue)
        g0 = book.LVR_G
        first, other = ((("Over its band ($)", "Over the book ($)") if compare_to == "peers"
                         else ("Over the book ($)", "Over its band ($)")))
        assert [ws.cell(row=6, column=g0 + 4).value, ws.cell(row=6, column=g0 + 5).value] == [first, other]
        rows = {(ws.cell(row=r, column=2).value, ws.cell(row=r, column=3).value): r for r in range(7, 13)}
        lo, hi = res.grids[0].band_labels
        s = _gco(res, 0, "A")
        r = rows[(lo, "A")]
        want = (s.excess_band, s.excess) if compare_to == "peers" else (s.excess, s.excess_band)
        assert (ws.cell(row=r, column=g0 + 4).value, ws.cell(row=r, column=g0 + 5).value) == pytest.approx(want)
        # profit's dollars are over, so a shortfall is negative: the engine's shortfall, turned round
        p = res.grids[0].cell(lo, "A").rates["ranr_rate"]
        assert ws.cell(row=r, column=book.LVR_R + 4).value == pytest.approx(-p.dollars)


def test_a_pocket_alone_in_its_band_has_no_dollars_over_it_and_is_ranked_by_the_books():
    rows = [row(i, 800, "A", 1000, int(i < 20), 1000 * int(i < 20), 50) for i in range(100)] + _rows()
    res = engine.run(cube(bands=[{"name": "score", "field": "SCORE", "edges": [650, 750]}],
                          benchmark=_bench("peers")), table(rows))
    g = res.grids[0]
    s = g.cell(g.band_labels[-1], "A").rates["gco_rate"]
    assert s.alone and not s.by_band and s.excess_band is None and s.dollars == s.excess > LINE and s.material
    got = [x for x in _bleeds(res) if x["Measure"] == "GCO per booked dollar" and x["Band"] == g.band_labels[-1]]
    assert got and got[0]["Excess over its band"] is None and got[0]["Excess over the book"] == pytest.approx(s.excess)


def test_check_says_which_comparison_decides():
    for compare_to, opens in (("peers", "The rest of its band decides"), ("topline", "The rest of the book decides")):
        res = _run(compare_to)
        ws = _sheet(res, lambda ws, r: book._check(ws, r, Path("loans.csv")))
        check = {r[1].value: r[2].value for r in ws.iter_rows(min_row=4)}
        said = check["Decides each pocket"]
        assert said.startswith(opens) and "flag, its dollars and whether it is material" in said
        assert ("alone in its band is compared with the book" in said) == (compare_to == "peers")


def test_the_command_line_ranks_by_the_deciding_dollars():
    out = cli.report(_run("peers"))
    gco = out[out.index("Grid score x chan - gco_rate"):]
    gco = gco[gco.index("Where it bleeds"):gco.index("Materiality evidence")]
    assert "excess GCO over the rest of its band's rate" in gco
    # four times its band, under the book: listed, material, with the book's figure beside it
    assert "650 - 700 / C: 12,000, 400 loans\n      for reference, against the book: -8,333" in gco
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
    res = _run("peers", revenue_line=0.25)
    ws = _sheet(res, book._losses_vs_revenue)
    reads = [ws.cell(row=r, column=c).value for r in range(7, 13) for c in (book.LVR_C + 3, book.LVR_R + 3)]
    assert reads and all(isinstance(x, str) for x in reads)
    for x in reads:
        assert not any(w in x for w in ("keeps", "pays", "about the same")), x
        assert x.startswith(("short of ", "ahead of ", "within ", "too few")), x
    # the loss side keeps its words
    losses = [ws.cell(row=r, column=book.LVR_G + 3).value for r in range(7, 13)]
    assert all(x.startswith(("losing more", "losing less", "about the same", "too few")) for x in losses), losses


def test_a_literal_shortfall_is_red_and_an_unsure_one_amber():
    """Where it bleeds shades by the flag's words. Profit's flag is literal now, so "short of" is worse,
    and one ending "(not significant)" is amber, as "worse, not significant" is."""
    res = _run("peers", revenue_line=0.25)
    ws = _sheet(res, book._bleeds)
    heads = [c.value for c in ws[4]]
    flag = heads.index("Flag (vs the rest of its band)") + 1
    assert book._col(flag) == "R"                                  # the column the rules read
    short = [ws.cell(row=r, column=flag).value for r in range(5, ws.max_row + 1)
             if str(ws.cell(row=r, column=flag).value).startswith("short of its band by ")]
    assert short
    rules = {r.dxf.fill.fgColor.rgb[-6:]: r.formula[0] for rng in ws.conditional_formatting for r in rng.rules}
    assert rules[book.WORSE_FILL] == ('OR($R5="worse",AND(LEFT($R5,8)="short of",'
                                      'NOT(RIGHT($R5,17)="(not significant)")))')
    assert rules[book.LUCK_FILL] == ('OR($R5="worse, not significant",AND(LEFT($R5,8)="short of",'
                                     'RIGHT($R5,17)="(not significant)"))')
