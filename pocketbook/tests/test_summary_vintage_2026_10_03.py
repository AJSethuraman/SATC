"""Summary's vintage chart and its grey rows (the firm, 3 Oct 2026).

The chart: "Could the summary tab have vintage graphs as well? Showing our primary targeted info, maybe an option for
average booked, amount booked, basically whatever is there except graphed out"; chosen: "Pocket vs rest vs book". Under
the Summary table, one row of the column Summary shows (the pocket) against the rest of the book and the whole book,
per origination year, on any Summary measure, following Summary's Only loans where. A point with fewer loans than the
Run's Fewest loans in a pocket is #N/A, so not drawn. A book with no origination date gets one sentence instead.

The grey rows: "make the really low unit counts grayed out to a degree... However this count should be separately
adjustable from all other config items - no dependencies just a simple number for this view specifically". Grey rows
under [50] loans, at the top of Summary.

Every figure checked against the loan file is worked out here from the CSV's text with the csv module and plain
arithmetic: nothing in the checks is imported from pocketbook."""

import csv
import re
import shutil

import pytest
from openpyxl import load_workbook

from pocketbook import book, choices as ch, results, synth
from test_book import _answer
from test_firm_answers_2026_09_29 import _summary_label

import tabs
from recalc import need_soffice

FILTER = "CHANNEL"
ONLY = f"Only loans where {FILTER} is"
NO_DATE_EVERY = 211                 # every 211th loan's ORIG_DATE is blanked: in no year, so on no line
NO_DATE_SAID = "No vintage chart: no column in this extract is marked Origination date on Columns"


def _write(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


def _build(d, rows, name, filter_by):
    from pocketbook import perm
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("POCKETBOOK_MEMORY", str(d / f"memory-{name}.yaml"))
        mp.setattr(perm, "SHUFFLES", 100)
        x = _write(rows, d / f"{name}.csv")
        out = book.set_up(x, choices=ch.Choices(run_kind=ch.BLEED, bands=("FICO",), segments=("CHANNEL",),
                                                filter=filter_by, outcome="BAD_FLAG"))
        _answer(out.book)
        wb = load_workbook(out.book)
        for r in book.table_rows(wb["Columns"]):           # every odd value but FICO's is real
            key = r[book.C_QKEY - 1].value
            if isinstance(key, str) and key.count("|") == 2 and not key.startswith("FICO"):
                r[book.C_TREAT - 1].value = "Real"
        wb.save(out.book)
        ran = book.run(out.book)
        assert ran.ok, ran.lines
    return out.book


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    """The synthetic book filtered by CHANNEL, a few loans with no origination date; and the same book with no
    ORIG_DATE column at all."""
    d = tmp_path_factory.mktemp("summary_vintage")
    src = synth.write_extract(d / "src", n=3000)
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    for i, r in enumerate(rows):
        if i % NO_DATE_EVERY == 3:
            r["ORIG_DATE"] = ""
    dated = _build(d, rows, "dated", FILTER)
    undated = _build(d, [{k: v for k, v in r.items() if k != "ORIG_DATE"} for r in rows], "undated", None)
    return dated, undated, rows


# --------------------------------------------------------------------------
# the arithmetic, from the CSV's text alone


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _year(r):
    return r["ORIG_DATE"][:4] if re.match(r"^\d{4}-\d\d-\d\d$", r["ORIG_DATE"] or "") else None


def _figures(rs):
    """Loans, Avg line (booked dollars over the loans with a booked amount) and GCOs ÷ Booked (GCO dollars over the
    booked dollars of the loans with both amounts)."""
    booked = [_f(r["ORIG_BAL"]) for r in rs if _f(r["ORIG_BAL"]) is not None]
    pairs = [(_f(r["GCO_AMT"]), _f(r["ORIG_BAL"])) for r in rs]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    den = sum(b for _, b in pairs)
    return {"Loans": len(rs), "Avg line": sum(booked) / len(booked) if booked else None,
            "GCOs ÷ Booked": sum(a for a, _ in pairs) / den if den else None}


def _same(got, want):
    if want is None:
        return got in (None, "")
    return got == pytest.approx(want, rel=1e-9, abs=1e-9)


# --------------------------------------------------------------------------
# what the Run wrote


def _views(b):
    ws = load_workbook(b)[results.VIEWS]
    return {r[0]: list(r[1:]) for r in ws.iter_rows(values_only=True)
            if isinstance(r[0], str) and r[0].startswith("V|")}


def _measures(b):
    """The Vintage measure dropdown's headings, and Summary's column keys beside them, as _choices holds them."""
    ws = load_workbook(b)[results.CHOICES]
    c = next(c.column for c in ws[1] if c.value == "Summary: Vintage measure")
    heads = [ws.cell(row=r, column=c).value for r in range(2, ws.max_row + 1)]
    heads = heads[:heads.index(None)] if None in heads else heads
    return heads


def _flat(row, heads, years, head, y):
    """One measure's value in one year on a flat _views row: measure after measure, year after year."""
    j = heads.index(head) * len(years) + years.index(y)
    return row[j] if j < len(row) else None


def test_the_points_tie_to_the_loan_file(made):
    """No LibreOffice: every FICO row, the rest of the book and the whole book, every year, All loans and each
    CHANNEL, for Loans, Avg line and GCOs ÷ Booked, as the Run put them on _views."""
    b, _, rows = made
    v = _views(b)
    heads = _measures(b)
    assert heads == ["Loans", "% of loans", "Bad loans", "Bad loans %", "Booked $", "Avg line", "Line × book",
                     "% of booked", "GCOs ($)", "GCOs ÷ Booked", "× book", "% of GCOs", "RANR $", "RANR ÷ Booked",
                     "% of RANR"]                       # every Summary column, in Summary's order
    years = sorted({_year(r) for r in rows if _year(r)})
    assert len(years) >= 4
    labels = v["V|FICO|rows"][1:1 + v["V|FICO|rows"][0]]
    assert labels[-1] == "(marked missing)" and "All" not in labels
    bands = [x for x in labels if not x.startswith("(")]
    checked = 0
    for only in [None, "Branch", "Broker", "Online"]:
        view = [r for r in rows if only is None or r[FILTER] == only]
        pre = "V|FICO" + (f"|where {only}" if only else "")
        book_row = v[f"{pre}|book"]
        for y in years:
            want = _figures([r for r in view if _year(r) == y])
            for head in ("Loans", "Avg line", "GCOs ÷ Booked"):
                assert _same(_flat(book_row, heads, years, head, y), want[head]), (only, y, head)
        for i, lab in enumerate(labels, start=1):
            pocket, rest = v[f"{pre}|{i}"], v[f"{pre}|{i}|rest"]
            for y in years:
                yr = [r for r in view if _year(r) == y]
                mine = [r for r in yr if _summary_label(r["FICO"], bands) == lab]
                others = [r for r in yr if _summary_label(r["FICO"], bands) != lab]
                assert len(mine) + len(others) == len(yr)
                for got_row, want in ((pocket, _figures(mine)), (rest, _figures(others))):
                    for head in ("Loans", "Avg line", "GCOs ÷ Booked"):
                        assert _same(_flat(got_row, heads, years, head, y), want[head]), (only, lab, y, head)
                        checked += 1
    assert checked > 500
    # a loan with no origination date is on no line: the years' loans add up to the dated loans only
    total = sum(_flat(v["V|FICO|book"], heads, years, "Loans", y) for y in years)
    assert total == sum(1 for r in rows if _year(r)) < len(rows)


def _tab(b, out, **picks):
    named = {"Vintage measure": picks.get("measure"), "Vintage row": picks.get("row"), ONLY: picks.get("only")}
    return tabs.calculated(tabs.choose(b, out, results.SUMMARY, **{k: v for k, v in named.items() if v}),
                           results.SUMMARY)


def test_the_chart_redraws_with_the_dropdowns_and_leaves_thin_points_off(made, tmp_path):
    """LibreOffice: Vintage measure GCOs ÷ Booked, a FICO band, only Broker loans. The points under the chart are
    the loan file's; the chart's three lines read the helper cells, where a point with fewer loans than Fewest loans
    in a pocket is #N/A, and the rest are the points shown."""
    need_soffice()
    b, _, rows = made
    got = _views(b)["V|FICO|rows"]
    labels = got[1:1 + got[0]]
    band = labels[0]
    bands = [x for x in labels if not x.startswith("(")]
    ws = _tab(b, tmp_path / "pick.xlsx", measure="GCOs ÷ Booked", row=band, only="Broker")
    note = next(c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)
                and "in Fewest loans in a pocket on Control is left off its line" in c.value)
    few = int(re.search(r"fewer loans than the ([\d,]+) in Fewest", note).group(1).replace(",", ""))
    cap = next(c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)
               and c.value.startswith("GCOs ÷ Booked (per cent) by origination year"))
    assert band in cap and "only loans where CHANNEL is Broker" in cap
    t = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=2).value == "Year")
    assert ws.cell(row=t, column=3).value == band
    years = sorted({_year(r) for r in rows if _year(r)})
    view = [r for r in rows if r[FILTER] == "Broker"]
    shown = {}
    for k, y in enumerate(years):
        r = t + 1 + k
        assert str(ws.cell(row=r, column=2).value) == y
        yr = [x for x in view if _year(x) == y]
        mine = [x for x in yr if _summary_label(x["FICO"], bands) == band]
        others = [x for x in yr if _summary_label(x["FICO"], bands) != band]
        for c, want in ((3, _figures(mine)), (5, _figures(others)), (7, _figures(yr))):
            assert _same(ws.cell(row=r, column=c).value, want["GCOs ÷ Booked"]), (y, c)
            assert ws.cell(row=r, column=c + 1).value == want["Loans"]
            shown[(c, y)] = (want["GCOs ÷ Booked"], want["Loans"])
    # the chart: three series, each reading a helper column of years
    charts = ws.formulas._charts
    assert len(charts) == 1
    series = charts[0].series
    assert len(series) == 3
    thin = drawn = 0
    for c, s in zip((3, 5, 7), series):
        ref = s.yVal.numRef.f.split("!")[1].replace("$", "")
        first, last = ref.split(":")
        col_, r0 = re.match(r"([A-Z]+)(\d+)", first).groups()
        for k, y in enumerate(years):
            got = ws[f"{col_}{int(r0) + k}"].value
            rate, loans = shown[(c, y)]
            if rate is None or loans < few:
                assert got == "#N/A", (c, y, got)
                thin += rate is not None
            else:
                assert got == pytest.approx(rate * 100, rel=1e-9), (c, y)       # drawn in per cent
                drawn += 1
    assert thin >= 1 and drawn >= 6


def test_the_rows_dropdown_follows_the_column_and_avg_line_draws_in_dollars(made, tmp_path):
    """LibreOffice: Summary's column switched to CHANNEL, the Vintage row picked from its values, Avg line: the
    points are each channel's booked dollars per loan that year, not per cent."""
    need_soffice()
    b, _, rows = made
    out = tmp_path / "chan.xlsx"
    tabs.choose(b, out, results.SUMMARY, **{"band or category column": "CHANNEL", "Vintage measure": "Avg line",
                                           "Vintage row": "Online"})
    ws = tabs.calculated(out, results.SUMMARY)
    cap = next(c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)
               and c.value.startswith("Avg line by origination year"))
    assert "Online" in cap and "per cent" not in cap
    t = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=2).value == "Year")
    years = sorted({_year(r) for r in rows if _year(r)})
    for k, y in enumerate(years):
        yr = [x for x in rows if _year(x) == y]
        mine = [x for x in yr if x["CHANNEL"] == "Online"]
        others = [x for x in yr if x["CHANNEL"] != "Online"]
        for c, want in ((3, _figures(mine)), (5, _figures(others)), (7, _figures(yr))):
            assert _same(ws.cell(row=t + 1 + k, column=c).value, want["Avg line"]), (y, c)


def test_no_origination_date_says_why_in_one_sentence(made):
    """The same book with no ORIG_DATE: no chart, no dropdowns, one plain sentence where the chart would be; the
    Summary table above is as it was."""
    _, b, _ = made
    ws = load_workbook(b)[results.SUMMARY]
    said = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith(
        "No vintage chart")]
    assert said == [NO_DATE_SAID + ", so there are no years to draw across."] * 2      # the note, and the block
    head = next(r for r in range(1, ws.max_row + 1) if str(ws.cell(row=r, column=2).value).startswith("Vintage: "))
    assert ws.cell(row=head + 1, column=2).value == said[0]
    assert ws._charts == []
    assert not any(c.value in ("VINTAGE MEASURE", "VINTAGE ROW") for row in ws.iter_rows() for c in row)
    assert not any(isinstance(k, str) and k.startswith("V|") for k in _views(b))
    assert ws["B2"].value == "Grey rows under" and ws["C2"].value == 50      # the grey rows don't need a date


def test_grey_rows_read_their_own_number_and_nothing_else(made):
    """Grey rows under [50] loans: a plain 50 in C2, not a formula and not a name; one conditional format over the
    whole Summary table greys a row whose Loans is under it; and no other cell, rule or name in the workbook reads it
    or feeds it, Control and Fewest loans included."""
    b, _, _ = made
    wb = load_workbook(b)
    ws = wb[results.SUMMARY]
    assert (ws["B2"].value, ws["C2"].value, ws["D2"].value) == ("Grey rows under", 50, "loans")
    assert ws["C2"].data_type == "n"
    h = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=3).value == "Loans")
    grey = []
    for rng in ws.conditional_formatting:
        for rule in rng.rules:
            if "$C$2" in rule.formula[0]:
                grey.append((str(rng.sqref), rule.formula[0], rule.dxf.font.color.rgb))
    assert len(grey) == 1
    sqref, formula, colour = grey[0]
    assert sqref.startswith(f"B{h + 1}:") and colour.endswith("9A958C")         # light grey, the font only
    assert formula == f'AND($B{h + 1}<>"",AND(ISNUMBER($C$2),ISNUMBER($C{h + 1}),$C{h + 1}<$C$2))'
    # nothing else reads it: no formula on any sheet, no rule but this one, no defined name
    for other in wb.worksheets:
        for row in other.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    assert not re.search(r"Summary'?!\$?C\$?2\b", c.value), (other.title, c.coordinate)
                    if other.title == results.SUMMARY:
                        assert not re.search(r"(?<![A-Z$])\$?C\$?2(?!\d)", c.value), c.coordinate
    for name in wb.defined_names:
        assert "Summary" not in str(wb.defined_names[name].attr_text)


def test_the_grey_number_typed_survives_the_next_run(made, tmp_path):
    """The firm: the grey number is "separately adjustable from all other config items". A Run rewrites Summary, so
    the number typed must be read first and put back: 75 typed, the next Run, still 75, and the rule still reads it.
    A book with no Summary yet gets the default."""
    from pocketbook import perm, summary_chart
    b = tmp_path / "again.xlsx"
    shutil.copy(made[0], b)
    wb = load_workbook(b)
    wb[results.SUMMARY]["C2"].value = 75
    wb.save(b)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
        mp.setattr(perm, "SHUFFLES", 100)
        assert book.run(b).ok
    ws = load_workbook(b)[results.SUMMARY]
    assert (ws["B2"].value, ws["C2"].value) == ("Grey rows under", 75)
    assert summary_chart.typed_grey(load_workbook(made[0])) == 50
