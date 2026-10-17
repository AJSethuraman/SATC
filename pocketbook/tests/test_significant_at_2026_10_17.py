"""Significant at N%? (the firm, 17 Oct 2026): Pockets' p-value column in standard statistics wording.

The firm: "i don't like how often by chance or could be chance as much as luck at this point. or another sort of
standard term, i just think could be chance is too vague for a typical user". The layout they chose:

    Significant at 95%?
    Yes (p = 0.09%)
    Borderline (p = 4.8%)
    No (p = 23%)
    Too few losses to test
    Not losing more

It replaces How often by chance (5 Oct 2026), whose Yes pocket read "1 in X" and whose other readings were Could be
chance and Too close to call. The p-value is the same one "1 in X" was built from: the p-value that decides, after
the allowance for many tests. The heading follows How sure on Control live."""

from __future__ import annotations

import re
import shutil

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.workbook.defined_name import DefinedName

import tabs
from conftest import TEST_SHUFFLES
from pocketbook import book, choices as ch, control, engine, live, perm, results, stats, synth
from test_book import _answer


@pytest.fixture(scope="module")
def sig_book(tmp_path_factory):
    """The synthetic book, FICO by CHANNEL, judged against the rest of its band: the workbook, the engine's result,
    every call to the allowance for many tests (its raw p-values and what it gave back), and the book calculated."""
    from recalc import calculated_book
    d = tmp_path_factory.mktemp("sig")
    got: dict = {"adjust": []}
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("POCKETBOOK_MEMORY", str(d / "memory.yaml"))
        mp.setattr(perm, "SHUFFLES", TEST_SHUFFLES)
        run, adjust = engine.run, engine.adjust

        def kept(*a, **k):
            got["res"] = run(*a, **k)
            return got["res"]

        def watched(ps, how):
            out = adjust(ps, how)
            got["adjust"].append((list(ps), list(out), how))
            return out
        mp.setattr(engine, "run", kept)
        mp.setattr(engine, "adjust", watched)
        out = book.set_up(synth.write_extract(d / "src", n=8000),
                          choices=ch.Choices(run_kind=ch.BLEED, bands=("FICO",), segments=("CHANNEL",)))
        assert out.ok, out.lines
        _answer(out.book)
        ran = book.run(out.book)
        assert ran.ok, ran.lines
    return {"b": out.book, "res": got["res"], "adjust": got["adjust"], "calc": calculated_book(out.book), "dir": d}


def _with_confidence(src, out, label: str):
    """A copy of the workbook with How sure on Control set to `label` ("99%")."""
    shutil.copy(src, out)
    wb = load_workbook(out)
    for r in wb[control.SHEET].iter_rows(min_row=control.FIRST_ROW):
        if r[control.KEY_COL - 1].value == "confidence":
            r[control.CHOOSE_COL - 1].value = label
    wb.save(out)
    return out


def _head(ws) -> str:
    return ws.cell(row=tabs.header_row(ws, results.K_NUM, "#"), column=results.K_P).value


def _note_labels(ws) -> list:
    top = next(c.row for row in ws.iter_rows(max_row=40) for c in row if c.value == "How this tab works")
    return [ws.cell(row=r, column=results.K_BAND).value for r in range(top + 1, top + 12)]


# --------------------------------------------------------------------------
# the heading


def test_the_heading_follows_how_sure_on_control(sig_book, tmp_path):
    """Significant at 95%? at the Run's 95%, and Significant at 99%? once How sure reads 99%, with no Run between:
    the heading and the method note's label are live, as the tab's other live headings are."""
    ws = sig_book["calc"][results.POCKETS]
    assert _head(ws) == "Significant at 95%?"
    assert "Significant at 95%?" in _note_labels(ws)
    sure = _with_confidence(sig_book["b"], tmp_path / "99.xlsx", "99%")
    ws = tabs.calculated(sure, results.POCKETS)
    assert _head(ws) == "Significant at 99%?"
    assert "Significant at 99%?" in _note_labels(ws)
    # and the readings follow it: at 99% sure a Yes is a p-value under 1%
    yes = [x["chance"] for x in tabs.pockets(ws) if str(x["chance"]).startswith("Yes (")]
    assert yes and all(_p_of(y) < 0.01 for y in yes), yes


# --------------------------------------------------------------------------
# the three readings


def _p_of(said: str) -> float:
    """The p-value a reading prints, as a share: "Yes (p = 0.37%)" is 0.0037; "p < 0.01%" reads as 0."""
    m = re.fullmatch(r"(?:Yes|Borderline|No) \(p (?:= ([\d.]+)|< 0\.01)%\)", said)
    assert m, said
    return float(m.group(1)) / 100 if m.group(1) else 0.0


@pytest.mark.parametrize("word, gap, p, border, said", [
    (engine.WORSE, 1.6, 0.0009, None, "Yes (p = 0.09%)"),
    (engine.WORSE, 1.6, 0.0037, None, "Yes (p = 0.37%)"),
    (engine.WORSE, 1.6, 0.048, "0.048", "Borderline (p = 4.8%)"),
    (engine.UNSURE_WORSE, 1.6, 0.052, "0.052", "Borderline (p = 5.2%)"),
    (engine.UNSURE_WORSE, 1.6, 0.23, None, "No (p = 23%)"),
    (engine.WORSE, 1.6, 0.00004, None, "Yes (p < 0.01%)"),
])
def test_yes_borderline_and_no_carry_the_p_value(word, gap, p, border, said):
    assert live.sig_said(word, gap, p, border, False, bar=0.05) == said


def test_the_tab_prints_only_the_new_readings_and_never_the_old(sig_book):
    """Every row on Pockets, for every measure, reads Yes, Borderline or No with a p-value, or one of the reasons
    kept from How often by chance. Nothing a reader sees says 1 in X, Could be chance, Too close to call or How often
    by chance."""
    kept = {live.FEW_LOSSES, live.FEW_LOANS, live.NO_REST, live.UNDER_WORSE, live.UNDER_PROFIT, live.NOT_MORE}
    seen = set()
    for measure in [results.plain(m) for m in results.rates(sig_book["res"])]:
        ws = tabs.calculated(tabs.choose(sig_book["b"], sig_book["dir"] / f"m-{len(seen)}-{measure[:3]}.xlsx",
                                         results.POCKETS, measure=measure), results.POCKETS)
        for x in tabs.pockets(ws):
            said = str(x["chance"])
            if said in kept:
                seen.add(said)
                continue
            word = said.split(" (p ")[0]
            assert word in (live.SIG_YES, live.SIG_BORDER, live.SIG_NO), said
            assert 0 <= _p_of(said) <= 1
            seen.add(word)
            # Yes is a p-value under the bar and No one at or over it; Borderline may be either side
            if word == live.SIG_YES:
                assert x["worse"] == "Yes" and _p_of(said) < 0.05, x
            elif word == live.SIG_NO:
                assert _p_of(said) >= 0.05, x
    assert {live.SIG_YES, live.SIG_NO} <= seen, seen
    wb = sig_book["calc"]
    text = " ".join(str(c.value) for ws in wb.worksheets if ws.sheet_state == "visible" for row in ws.iter_rows()
                    for c in row if isinstance(c.value, str))
    for gone in ("How often by chance", "Could be chance", "Too close to call", "Rarer than 1 in"):
        assert gone not in text, gone
    assert not re.search(r"\b1 in [\d,]+\b", " ".join(str(c.value) for row in wb[results.POCKETS].iter_rows()
                                                      for c in row if isinstance(c.value, str)))


# --------------------------------------------------------------------------
# the p format


@pytest.mark.parametrize("p, bar, said", [
    (0.0009, 0.05, "p = 0.09%"), (0.0037, 0.05, "p = 0.37%"), (0.048, 0.05, "p = 4.8%"), (0.23, 0.05, "p = 23%"),
    (0.0001, 0.05, "p = 0.01%"), (0.0000999, 0.05, "p < 0.01%"), (0.0, 0.05, "p < 0.01%"),
    (0.00995, 0.05, "p = 1.0%"), (0.0996, 0.05, "p = 10%"), (1.0, 0.05, "p = 100%"),
    # a p-value that would round onto the bar it is under, or over, takes one more decimal
    (0.0498, 0.05, "p = 4.98%"), (0.0503, 0.05, "p = 5.03%"), (0.05, 0.05, "p = 5.0%"),
    (0.0099, 0.01, "p = 0.99%"), (0.00999, 0.01, "p = 0.999%"), (0.0101, 0.01, "p = 1.01%"),
])
def test_the_p_value_is_a_percentage_at_the_firms_precision(p, bar, said):
    assert live.p_words(p, bar) == said


def test_the_p_format_formula_matches_python_in_a_spreadsheet(tmp_path):
    """p_words_formula, calculated by LibreOffice, against p_words, at two bars."""
    from recalc import recalc
    ps = [0.0009, 0.0037, 0.048, 0.23, 0.0001, 0.0000999, 0.0, 0.00995, 0.0996, 1.0, 0.0498, 0.0503, 0.05, 0.0099,
          0.012345, 0.000151, 0.4567, 0.00999, 0.0101]
    for bar in (0.05, 0.01):
        wb = Workbook()
        ws = wb.active
        ws["D1"] = bar
        wb.defined_names[live.BAR] = DefinedName(live.BAR, attr_text=f"'{ws.title}'!$D$1")
        for i, p in enumerate(ps, start=1):
            ws.cell(row=i, column=1, value=p)
            ws.cell(row=i, column=2, value="=" + live.p_words_formula(f"A{i}"))
        path = tmp_path / f"p-{bar}.xlsx"
        wb.save(path)
        got = recalc(path, tmp_path / f"out-{bar}")
        calc = got.active
        for i, p in enumerate(ps, start=1):
            assert calc.cell(row=i, column=2).value == live.p_words(p, bar), (p, bar)


# --------------------------------------------------------------------------
# the same p-value "1 in X" was built from, tied by hand


def _bh(raw: list) -> list:
    """Benjamini-Hochberg by hand: each p-value x m / its rank, then the smallest from it upward, capped at 1."""
    tested = sorted((p, i) for i, p in enumerate(raw) if p is not None)
    m = len(tested)
    out: list = [None] * len(raw)
    running = 1.0
    for rank in range(m, 0, -1):
        p, i = tested[rank - 1]
        running = min(running, p * m / rank)
        out[i] = running
    return out


def test_a_yes_pocket_prints_the_p_value_that_decides_tied_by_hand(sig_book):
    """One Yes pocket on Bad loans, tied end to end: its p-value worked out here from its own counts (the pooled
    two-proportion z test against the rest of its band), the allowance worked out here over its grid's p-values,
    and the two side by side with the engine's, with _pockets' p-value that decides (what "1 in X" was built from)
    and with what Pockets prints."""
    res, calc = sig_book["res"], sig_book["calc"]
    assert res.config.benchmark.many_tests == "bh" and res.config.benchmark.compare_to == "peers"
    g = next(x for x in res.grids)
    # the Yes pocket with the largest p-value, so the figure printed is a percentage rather than "p < 0.01%"
    yes = [(c.rates["outcome_loans"].p_band, bl, dl, c, c.rates["outcome_loans"]) for (bl, dl), c in g.inner()
           if c.rates["outcome_loans"].flag == engine.WORSE and c.rates["outcome_loans"].by_band
           and c.rates["outcome_loans"].units >= res.config.benchmark.min_units]
    assert yes, "no Yes pocket on Bad loans"
    pick = max(yes, key=lambda x: x[0])[1:]
    bl, dl, c, s = pick
    band = g.cells[(bl, engine.ALL)].rates["outcome_loans"]
    raw = stats.two_prop_z(s.num, s.units, band.num - s.num, band.units - s.units)[1]
    same = lambda r: r is not None and abs(r - raw) <= 1e-12 * raw                 # noqa: E731
    call = next(x for x in sig_book["adjust"] if any(same(r) for r in x[0]) and x[1][[same(r) for r in x[0]].index(
        True)] == pytest.approx(s.p_band, rel=1e-12))
    i = [same(r) for r in call[0]].index(True)
    by_hand = _bh(call[0])[i]
    assert by_hand == pytest.approx(s.p_band, rel=1e-12) and by_hand >= raw
    # _pockets' p-value that decides, the cell the old "1 in X" read, is the same number
    pk = calc[live.POCKETS]
    row = next(r for r in range(live.P_FIRST, pk.max_row + 1)
               if (pk.cell(row=r, column=live.P_KIND).value, pk.cell(row=r, column=live.P_BAND).value,
                   pk.cell(row=r, column=live.P_SEG).value, pk.cell(row=r, column=live.P_MEASURE).value)
               == ("grids", bl, dl, "outcome_loans") and pk.cell(row=r, column=live.P_GRID).value.startswith("FICO"))
    assert pk.cell(row=row, column=live.P_P).value == pytest.approx(by_hand, rel=1e-12)
    want = f"Yes ({live.p_words(by_hand, 0.05)})"
    assert pk.cell(row=row, column=live.P_SIG).value == want
    # and Pockets prints it on that pocket's row
    ws = tabs.calculated(tabs.choose(sig_book["b"], sig_book["dir"] / "bad.xlsx", results.POCKETS,
                                     measure="Bad loans"), results.POCKETS)
    names = {b.name: b.field for b in res.config.bands}
    rows = [x for x in tabs.pockets(ws) if x["band"] == f"{names[g.band]} {bl}" and str(dl) in str(x["seg"])]
    assert [x["chance"] for x in rows] == [want], rows
