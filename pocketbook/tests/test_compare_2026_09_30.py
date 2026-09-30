"""Two filters, and the Compare chart (the firm, 30 Sep 2026).

- Two Filter by columns: "independently and in conjunction with each other" (ORIG_YEAR = 2023 and SYS_FLAG = Y).
  Grids and Summary offer both dropdowns; vs the book stays against the whole book.
- "can we make it so they can be visually compared in a graph? Like if we used origination date as a filter it would
  essentially be vintage years", and then: "if we are proving things exist across categories it should not be
  vintage analysis only so let's make sure that is the case and how would we show that say vintage analysis mixed
  with like underwriter/system approved?" A line chart, chosen over bars.

Every figure the tab shows is worked out again here from the loan file with the csv module alone: the tests that
tie out read the calculated workbook with openpyxl and import nothing from pocketbook.
"""

import csv
import math
import random
import shutil
from pathlib import Path

import pytest
from openpyxl import load_workbook
from openpyxl.utils import range_boundaries

from pocketbook import book, choices as ch, synth
from test_book import _answer

KEY_FILE = "loans.csv"
YEARS = ("2022", "2023", "2024")
FLAGS = ("N", "Y", "(blank)")
CHANNELS = ("Branch", "Broker", "Online")
ONLY_YEAR = f"Only loans where {ch.ORIG_YEAR} is"
AND_FLAG = "and SYS_FLAG is"


def _file(d: Path, n: int) -> Path:
    """The synthetic book with an origination date (2022 to 2024; every 151st loan has none) and SYS_FLAG, the
    system-approved flag (Y or N; every 97th loan blank, so its loans are few in every pocket)."""
    from datetime import date, timedelta
    src = synth.write_extract(d / "src", n=n)
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    rng = random.Random(930)
    for i, r in enumerate(rows):
        made = date(2022, 1, 1) + timedelta(days=rng.randint(0, 1094))
        r["ORIG_DATE"] = "" if i % 151 == 5 else made.isoformat()
        r["SYS_FLAG"] = "" if i % 97 == 0 else rng.choice("YN")
    out = d / KEY_FILE
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return out


def _book(d: Path, n: int, filt: str, filt2: str):
    from pocketbook import perm
    from test_book import at
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("POCKETBOOK_MEMORY", str(d / "memory.yaml"))
        mp.setattr(perm, "SHUFFLES", 100)
        x = _file(d, n)
        out = book.set_up(x, choices=ch.Choices(run_kind=ch.BLEED, bands=("FICO",), segments=("CHANNEL",),
                                                filter=filt, filter2=filt2, outcome="BAD_FLAG"))
        _answer(out.book)
        wb = load_workbook(out.book)
        wb["Columns"][at(wb, "FICO", book.C_EDGES)] = "620; 680; 740"     # whole scores: labels say the loans
        wb.save(out.book)
        ran = book.run(out.book)
        assert ran.ok, ran.lines
    return out.book, x, ran


def _calc(b: Path, out: Path, tab: str, **picks) -> Path:
    """A calculated copy with a tab's dropdowns set (LibreOffice), for the tie-outs to read with openpyxl alone."""
    import tabs
    from recalc import recalc_file
    return recalc_file(tabs.choose(b, out, tab, **picks), out.parent / f"rc-{out.stem}")


@pytest.fixture(scope="module")
def vintage(tmp_path_factory):
    """Filter 1 ORIG_YEAR, Filter 2 SYS_FLAG; Compare with Origination year across the bottom, and FICO with the
    lines by year and one panel for each SYS_FLAG value."""
    d = tmp_path_factory.mktemp("vintage_sys")
    b, x, ran = _book(d, 5000, ch.ORIG_YEAR, "SYS_FLAG")
    return {"book": b, "csv": x, "ran": ran,
            "across_year": _calc(b, d / "year.xlsx", "Compare", **{"Across the bottom": "Origination year"}),
            "fico_panels": _calc(b, d / "fico.xlsx", "Compare", **{"Across the bottom": "FICO",
                                                                    "Measure": "Charge-offs"})}


@pytest.fixture(scope="module")
def channels(tmp_path_factory):
    """Filter 1 CHANNEL (a segment too), Filter 2 SYS_FLAG: FICO across, lines by CHANNEL, panels by SYS_FLAG. Not
    vintage at all (the firm: "it should not be vintage analysis only")."""
    d = tmp_path_factory.mktemp("channel_sys")
    b, x, ran = _book(d, 6000, "CHANNEL", "SYS_FLAG")
    return {"book": b, "csv": x, "ran": ran,
            "calc": _calc(b, d / "fico.xlsx", "Compare", **{"Across the bottom": "FICO", "Measure": "Bad loans"})}


# ---- worked out from the loan file, with nothing from pocketbook


def _rows(x) -> list[dict]:
    return list(csv.DictReader(open(x, encoding="utf-8")))


def _year(r) -> str:
    return r["ORIG_DATE"][:4] if r["ORIG_DATE"] else "(no date)"


def _flag(r) -> str:
    return r["SYS_FLAG"] or "(blank)"


def _fico_of(rows):
    """Each loan's FICO band, on the edges typed on Columns (620; 680; 740) and labelled as the Run labels them:
    the lowest band from the smallest score read, the top band to the largest."""
    read = [float(r["FICO"]) for r in rows if r["FICO"] != "" and float(r["FICO"]) > -1000]
    lo, hi, edges = min(read), max(read), (620, 680, 740)

    def band(r) -> str:
        if r["FICO"] == "":
            return "(blank)"
        v = float(r["FICO"])
        if v < -1000:
            return "(marked missing)"
        if v < edges[0]:
            return f"{lo:.0f} - {edges[0] - 1}"
        for a, z in zip(edges, edges[1:]):
            if a <= v < z:
                return f"{a} - {z - 1}"
        return f"{edges[-1]} - {hi:.0f}"
    return band


def _bad(rows):
    """Bad loans %: the loans marked 1 over the loans whose outcome reads 0 or 1."""
    read = [r["BAD_FLAG"] for r in rows if r["BAD_FLAG"] in ("0", "1")]
    return read.count("1") / len(read) if read else None


def _gco(rows):
    """Charge-offs: charged-off dollars over the booked dollars of the loans with both amounts."""
    def f(v):
        try:
            return float(v)
        except ValueError:
            return None
    both = [(f(r["GCO_AMT"]), f(r["ORIG_BAL"])) for r in rows]
    both = [(g, b) for g, b in both if g is not None and b is not None]
    den = sum(b for _, b in both)
    return sum(g for g, _ in both) / den if den else None


def _tables(path) -> dict:
    """Compare's tables as calculated: {panel heading: {row label: {line: (rate, loans)}}}."""
    ws = load_workbook(path, data_only=True)["Compare"]
    out = {}
    for r in range(1, ws.max_row):
        if ws.cell(row=r + 1, column=3).value == "Rate" and ws.cell(row=r, column=2).value:
            names = {c: ws.cell(row=r, column=c).value for c in range(3, ws.max_column + 1, 2)
                     if ws.cell(row=r, column=c).value}
            rows, rr = {}, r + 2
            while ws.cell(row=rr, column=2).value not in (None, ""):
                rows[ws.cell(row=rr, column=2).value] = {n: (ws.cell(row=rr, column=c).value,
                                                             ws.cell(row=rr, column=c + 1).value)
                                                         for c, n in names.items()}
                rr += 1
            out[ws.cell(row=r, column=2).value] = rows
    return out


def _fewest(path) -> int:
    """Fewest loans in a pocket, as the tab's method note says it."""
    ws = load_workbook(path, data_only=True)["Compare"]
    for row in ws.iter_rows(max_row=20):
        for c in row:
            if isinstance(c.value, str) and "Fewest loans in a pocket" in c.value and "fewer loans than the " in c.value:
                return int(c.value.split("fewer loans than the ")[1].split(" ")[0].replace(",", ""))
    raise KeyError("Fewest loans in a pocket")


def _series(written, calc) -> list[list[list]]:
    """Each chart's series as drawn, in order: [chart][series] = the y values LibreOffice calculated (#N/A as
    None). The lines come first (the whole book, then one per line slot), then one label per place across, then the
    scale's two points."""
    cw = load_workbook(calc, data_only=True)["Compare"]
    out = []
    for chart in load_workbook(written)["Compare"]._charts:
        got = []
        for s in chart.series:
            ref = s.yVal.numRef.f.split("!")[1].replace("$", "")
            c0, r0, c1, r1 = range_boundaries(ref if ":" in ref else f"{ref}:{ref}")
            vals = [cw.cell(row=r, column=c0).value for r in range(r0, r1 + 1)]
            got.append([None if v in ("#N/A", None, "") else v for v in vals])
        out.append(got)
    return out


def _close(a, b) -> bool:
    if b is None:
        return a in (None, "", "#N/A")
    return isinstance(a, (int, float)) and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


# ---- the tie-outs


def test_compare_vintage_by_system_approved_every_point_is_the_loan_files(vintage):
    """Origination year across the bottom, one line per SYS_FLAG value: each point's bad-loan rate and loans from the
    CSV; the whole book line is every loan of the year. SYS_FLAG's blanks are too few in every year, so that line
    is in the table and left off the chart."""
    rows = _rows(vintage["csv"])
    few = _fewest(vintage["across_year"])
    tables = _tables(vintage["across_year"])
    assert list(tables) == ["All loans"]                                     # a filter across: one chart
    shown = tables["All loans"]
    assert list(shown) == list(YEARS)                                        # (no date) isn't a place across
    for y in YEARS:
        mine = [r for r in rows if _year(r) == y]
        rate, n = shown[y]["Whole book"]
        assert n == len(mine) and _close(rate, _bad(mine)), y
        for flag in FLAGS:
            pick = [r for r in mine if _flag(r) == flag]
            rate, n = shown[y][flag]
            assert n == len(pick) and _close(rate, _bad(pick)), (y, flag)
    drawn = _series(vintage["book"], vintage["across_year"])[0]
    lines = {"Whole book": drawn[0], **{f: drawn[1 + k] for k, f in enumerate(FLAGS)}}
    thin = 0
    for name, ys in lines.items():
        for i, y in enumerate(YEARS):
            mine = [r for r in rows if _year(r) == y and (name == "Whole book" or _flag(r) == name)]
            if len(mine) < few:
                assert ys[i] is None, (name, y)                              # left off the line, not plotted
                thin += 1
            else:
                assert _close(ys[i], _bad(mine)), (name, y)
    assert thin == len(YEARS)                                                 # the blanks' line, every year


def test_compare_fico_lines_by_year_panels_by_system_approved_one_scale(vintage):
    """FICO across, lines by year, one panel per SYS_FLAG value: each panel's points are that flag's loans of that
    year in that band, charge-offs over booked; every panel carries the same two scale points, the smallest and
    largest value drawn in any panel."""
    rows = _rows(vintage["csv"])
    _fico = _fico_of(rows)
    few = _fewest(vintage["fico_panels"])
    tables = _tables(vintage["fico_panels"])
    assert list(tables) == [f"SYS_FLAG is {f}" for f in FLAGS]
    drawn = _series(vintage["book"], vintage["fico_panels"])
    everything = []
    for p, flag in enumerate(FLAGS):
        shown = tables[f"SYS_FLAG is {flag}"]
        labels = list(shown)
        assert len(labels) == 4 and all(" - " in x for x in labels)
        for i, lab in enumerate(labels):
            for k, y in enumerate(YEARS + ("(no date)",)):
                pick = [r for r in rows if _year(r) == y and _flag(r) == flag and _fico(r) == lab]
                plotted = drawn[p][1 + k][i]
                if y not in shown[lab]:                     # no loan of the panel has that year: no line, no column
                    assert not [r for r in rows if _year(r) == y and _flag(r) == flag] and plotted is None
                    continue
                rate, n = shown[lab][y]
                assert n == len(pick) and _close(rate, _gco(pick)), (flag, lab, y)
                if len(pick) < few:
                    assert plotted is None, (flag, lab, y)
                else:
                    assert _close(plotted, _gco(pick)), (flag, lab, y)
                    everything.append(_gco(pick))
            whole = [r for r in rows if _fico(r) == lab]                       # the whole book's dashed line
            assert _close(drawn[p][0][i], _gco(whole)) and shown[lab]["Whole book"][1] == len(whole)
            everything.append(_gco(whole))
    scale = [chart[-1][:2] for chart in drawn]
    want = [min(everything), max(everything)]
    assert len(drawn) == 4 and not any(v for s in drawn[3][:-1] for v in s)  # a fourth slot, for four years: empty
    for got in scale:                                                           # ... on the same scale
        # the top: the largest value drawn in any panel; the bottom: zero, where the labels across sit, since no
        # charge-off rate is below it
        assert _close(got[1], want[1]) and got[0] == 0 <= want[0], (got, want)


def test_compare_is_not_vintage_only_fico_by_channel_panels_by_system_approved(channels):
    """CHANNEL and SYS_FLAG, no dates at all: FICO across, a line per channel, a panel per SYS_FLAG value, each
    point the loan file's."""
    rows = _rows(channels["csv"])
    _fico = _fico_of(rows)
    few = _fewest(channels["calc"])
    tables = _tables(channels["calc"])
    assert list(tables) == [f"SYS_FLAG is {f}" for f in FLAGS]
    drawn = _series(channels["book"], channels["calc"])
    for p, flag in enumerate(FLAGS):
        shown = tables[f"SYS_FLAG is {flag}"]
        for i, lab in enumerate(shown):
            for k, c in enumerate(CHANNELS):
                pick = [r for r in rows if r["CHANNEL"] == c and _flag(r) == flag and _fico(r) == lab]
                rate, n = shown[lab][c]
                assert n == len(pick) and _close(rate, _bad(pick)), (flag, lab, c)
                assert (drawn[p][1 + k][i] is None) == (len(pick) < few), (flag, lab, c)
    assert all(v is None for k in range(1, 4) for v in drawn[2][k])          # the blanks: too few everywhere


# ---- two filters on Grids and Summary


def test_two_filters_grids_one_year_and_one_flag_every_cell_from_the_loan_file(vintage, tmp_path):
    """Grids' Only loans where ORIG_YEAR is 2023 and SYS_FLAG is Y: the loans with both, cell by cell; each filter
    alone too; vs the book still against the whole book."""
    import tabs
    from pocketbook import results
    from test_firm_answers_2026_09_29 import _bad_rate, _cells, _grids
    b = vintage["book"]
    rows = _rows(vintage["csv"])
    wb = load_workbook(b)
    assert tabs.options(wb, results.GRIDS, ONLY_YEAR) == [results.ALL_LOANS, *YEARS, "(no date)"]
    assert tabs.options(wb, results.GRIDS, AND_FLAG) == [results.ALL_LOANS, *FLAGS]
    book_rate = _bad_rate(rows)
    for year, flag in (("2023", "Y"), ("2023", results.ALL_LOANS), (results.ALL_LOANS, "N")):
        ws, blocks, said = _grids(b, tmp_path / f"{year[:3]}{flag[:1]}.xlsx", **{ONLY_YEAR: year, AND_FLAG: flag})
        mine = [r for r in rows if year in (results.ALL_LOANS, _year(r)) and flag in (results.ALL_LOANS, _flag(r))]
        rate, bk, loans = blocks["Rate"], blocks["vs the book"], blocks["Loans"]
        cells = _cells(mine, loans)
        assert {k for k, n in loans.items() if n} == set(cells), (year, flag)
        for k, got in cells.items():
            assert loans[k] == len(got) and rate[k] == pytest.approx(_bad_rate(got)), (year, flag, k)
            if isinstance(bk[k], (int, float)):
                assert bk[k] == pytest.approx(_bad_rate(got) / book_rate), (year, flag, k)
        where = {(results.ALL_LOANS, "N"): ", only loans where SYS_FLAG is N",
                 ("2023", results.ALL_LOANS): ", only loans where ORIG_YEAR is 2023",
                 ("2023", "Y"): ", only loans where ORIG_YEAR is 2023 and SYS_FLAG is Y"}[(year, flag)]
        assert said["name"].endswith(where), said["name"]


def test_two_filters_summary_one_year_and_one_flag_is_those_loans(vintage, tmp_path):
    import tabs
    from pocketbook import results
    from test_firm_answers_2026_09_29 import SUMMARY_ONLY, _summary_tab
    b = vintage["book"]
    rows = _rows(vintage["csv"])
    _fico = _fico_of(rows)
    assert tabs.options(load_workbook(b), results.SUMMARY, AND_FLAG) == [results.ALL_LOANS, *FLAGS]
    out = tmp_path / "s.xlsx"
    shutil.copy(b, out)
    wb = load_workbook(out)
    tabs.dropdown(wb[results.SUMMARY], AND_FLAG).value = "N"
    wb.save(out)
    _, _, shown, _ = _summary_tab(out, tmp_path / "s2.xlsx", band="FICO", only="2024")
    mine = [r for r in rows if _year(r) == "2024" and _flag(r) == "N"]
    assert shown["All"]["Loans"] == len(mine) and shown["All"]["Bad loans %"] == pytest.approx(_bad(mine))
    for lab, got in shown.items():
        if lab != "All" and " - " in lab:
            pick = [r for r in mine if _fico(r) == lab]
            assert got["Loans"] == len(pick) and got["Bad loans %"] == pytest.approx(_bad(pick)), lab


def test_two_filters_named_in_the_runs_lines_and_record(vintage):
    import tabs
    rows = _rows(vintage["csv"])
    counts = {f: sum(1 for r in rows if _flag(r) == f) for f in FLAGS}
    listed = ", ".join(f"{f} ({n:,} loans)" for f, n in counts.items())
    said = f" And by SYS_FLAG: {listed}; the two together keep the loans with both."
    assert any(said in line for line in vintage["ran"].lines), vintage["ran"].lines
    assert said in tabs.record(vintage["book"])["Grids filter"]


# ---- the launcher and the Run's refusals


def test_filter_2_in_the_launcher_alone_together_refused_twice_and_written_to_control(tmp_path, monkeypatch):
    from pocketbook import control
    from test_firm_answers_2026_09_29 import _flow
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    x = _file(tmp_path, 1500)
    f = _flow(x)
    f.pick_outcome("BAD_FLAG")
    f.answer_outcome(True)
    by = {r["name"]: r for r in f.rows()}
    assert by["SYS_FLAG"]["e"] == {"on": False, "radio": True} and by[ch.ORIG_YEAR]["e"] is not None
    assert by["FICO"]["e"] is None
    f.click("SYS_FLAG", "e")                                                  # Filter 2 alone is the one filter
    got = f.choices()
    assert (got.filter, got.filter2) == ("SYS_FLAG", None)
    f.click("SYS_FLAG", "d")                                                  # the same column twice: refused
    assert f.summary() == (False, ch.same_filter_twice("SYS_FLAG")) and f.states()["next"] == "disabled"
    f.click(ch.ORIG_YEAR, "d")
    ok, said = f.summary()
    assert ok and said.endswith("Grids can show only the loans of one ORIG_YEAR, one SYS_FLAG, or both at once."), said
    got = f.choices()
    assert (got.filter, got.filter2) == (ch.ORIG_YEAR, "SYS_FLAG")
    f.next()
    assert f.page == "answer", f.message
    ws = load_workbook(f.book())[control.SHEET]
    shown = {ws.cell(row=r, column=2).value: ws.cell(row=r, column=control.CHOOSE_COL).value
             for r in range(control.FIRST_ROW, ws.max_row + 1)}
    assert shown["Filter the Grids by"] == ch.ORIG_YEAR and shown["And filter them by"] == "SYS_FLAG"
    again = _flow(x)
    assert (again.filter, again.filter2) == (ch.ORIG_YEAR, "SYS_FLAG")


def test_two_filters_too_many_views_refused_in_words():
    assert ch.too_many_views("A", 6, "B", 6) is None                         # 7 x 7 = 49
    said = ch.too_many_views("A", 7, "B", 6)
    assert said == ("A (7 values) and B (6 values) together make 8 x 7 = 56 views of every grid, counting All loans "
                    "in each. Two filters can make 49 at most. Filter by a column with fewer values, or by one.")


def test_the_run_refuses_one_column_as_both_filters(tmp_path, monkeypatch):
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    x = _file(tmp_path, 1500)
    out = book.set_up(x, choices=ch.Choices(run_kind=ch.BLEED, bands=("FICO",), segments=("CHANNEL",),
                                            filter="SYS_FLAG", filter2="SYS_FLAG", outcome="BAD_FLAG"))
    _answer(out.book)
    ran = book.run(out.book)
    assert not ran.ok and ran.lines == [f"Couldn't run: {ch.same_filter_twice('SYS_FLAG')}"]
