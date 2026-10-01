"""Months to charge-off (the firm, 1 Oct 2026: "We worked in calculating charge off months right? If the data is
there"). It wasn't built. Chosen: the average months to charge-off, from a charge-off date column in the extract.

A column marked Charge-off date, beside one marked Origination date, gives each loan with a charge-off date its
months to charge-off: whole calendar months, (y2 - y1) * 12 + (m2 - m1), the day ignored. Summary shows the average
and the median among each row's charged-off loans, All and every filter view included; Grids offers it as a Measure.
A charge-off before origination, or a date that can't be read, is left out and counted in a warning, never silently.
With no charge-off date column, nothing changes.

Every figure checked against the loan file is worked out here from the CSV's text with plain arithmetic: nothing in
the checks is imported from pocketbook."""

import csv
import statistics

import pytest
from openpyxl import load_workbook

from pocketbook import book, choices as ch, results, synth
from test_book import _answer

import tabs
from recalc import need_soffice

PICKER = "band or category column"
ONLY = f"Only loans where {ch.ORIG_YEAR} is"
AVG, MED = "Avg months to charge-off", "Median months to charge-off"
BEFORE, NOT_A_DATE, NO_ORIG, DAY_EDGE = 11, 23, 37, 41      # which bad loans are bent, by their place among them


def _write(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


def _build(d, rows, name):
    from pocketbook import perm
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("POCKETBOOK_MEMORY", str(d / f"memory-{name}.yaml"))
        mp.setattr(perm, "SHUFFLES", 100)
        x = _write(rows, d / f"{name}.csv")
        out = book.set_up(x, choices=ch.Choices(run_kind=ch.BLEED, bands=("FICO",), segments=("CHANNEL",),
                                                filter=ch.ORIG_YEAR, outcome="BAD_FLAG"))
        _answer(out.book)
        ran = book.run(out.book)
        assert ran.ok, ran.lines
    return out.book


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    """The synthetic book with CO_DATE on every bad loan, four of them bent: one charged off before it was made, one
    whose charge-off date isn't a date, one with no origination date, and one 31 Jan to 1 Feb (1 month, days
    ignored). The same book without CO_DATE beside it."""
    d = tmp_path_factory.mktemp("co_months")
    src = synth.write_extract(d / "src", n=3000, chargeoff=True)
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    bad = [r for r in rows if r["CO_DATE"]]
    assert len(bad) > 100
    bad[BEFORE]["CO_DATE"] = f"{int(bad[BEFORE]['ORIG_DATE'][:4]) - 1}{bad[BEFORE]['ORIG_DATE'][4:]}"
    bad[NOT_A_DATE]["CO_DATE"] = "pending"
    bad[NO_ORIG]["ORIG_DATE"] = ""
    bad[DAY_EDGE]["ORIG_DATE"], bad[DAY_EDGE]["CO_DATE"] = "2024-01-31", "2024-02-01"
    with_co = _build(d, rows, "with")
    without = _build(d, [{k: v for k, v in r.items() if k != "CO_DATE"} for r in rows], "without")
    return with_co, without, rows


# --------------------------------------------------------------------------
# the arithmetic, from the CSV's text alone


def _ymd(s):
    try:
        y, m, dd = (int(p) for p in s.split("-"))
        return y, m, dd
    except (ValueError, AttributeError):
        return None


def _months(r):
    """A loan's months to charge-off, or None: no charge-off date, an unreadable date, or before it was made."""
    o, c = _ymd(r["ORIG_DATE"]), _ymd(r["CO_DATE"])
    if not r["CO_DATE"] or o is None or c is None or c < o:
        return None
    return (c[0] - o[0]) * 12 + (c[1] - o[1])


def _want(rs):
    got = [m for m in (_months(r) for r in rs) if m is not None]
    return (sum(got) / len(got), statistics.median(got)) if got else (None, None)


def _same(got, want):
    if want is None:
        return got in (None, "")
    return got == pytest.approx(want, rel=1e-9, abs=1e-9)


def _views(b):
    """Summary's rows as the Run put them on _views: {view key: [label, value per column]}."""
    ws = load_workbook(b)[results.VIEWS]
    return {r[0]: list(r[1:]) for r in ws.iter_rows(values_only=True) if isinstance(r[0], str)
            and r[0].startswith("S|")}


def _heads(b):
    """Summary's column headings as written (literal text, no formula)."""
    ws = load_workbook(b)[results.SUMMARY]
    h = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=3).value == "Loans")
    heads, c = [], 3
    while ws.cell(row=h, column=c).value not in (None, ""):
        heads.append(ws.cell(row=h, column=c).value)
        c += 1
    return heads


def _summary(b, out, pick, only=None):
    picks = {PICKER: pick, **({ONLY: only} if only else {})}
    ws = tabs.calculated(tabs.choose(b, out, results.SUMMARY, **picks), results.SUMMARY)
    h = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=3).value == "Loans")
    heads, c = [], 3
    while ws.cell(row=h, column=c).value not in (None, ""):
        heads.append(ws.cell(row=h, column=c).value)
        c += 1
    rows, r = {}, h + 1
    while ws.cell(row=r, column=2).value not in (None, ""):
        rows[ws.cell(row=r, column=2).value] = {hd: ws.cell(row=r, column=3 + j).value for j, hd in enumerate(heads)}
        r += 1
    return rows, heads


def _text(b):
    wb = load_workbook(b)
    return "\n".join(str(c.value) for ws in wb for row in ws.iter_rows() for c in row if isinstance(c.value, str))


# --------------------------------------------------------------------------


def test_the_bent_loans_are_what_the_fixture_says(made):
    """The checks below lean on these four: say them from the CSV first."""
    _, _, rows = made
    bad = [r for r in rows if r["CO_DATE"]]
    assert _months(bad[BEFORE]) is None and _ymd(bad[BEFORE]["CO_DATE"]) < _ymd(bad[BEFORE]["ORIG_DATE"])
    assert _months(bad[NOT_A_DATE]) is None and _months(bad[NO_ORIG]) is None
    assert _months(bad[DAY_EDGE]) == 1


def test_summary_by_channel_ties_to_the_loan_file(made, tmp_path):
    """CHANNEL down the side, every row and All: the average and the median months to charge-off among the row's
    charged-off loans, after LibreOffice calculates the tab, against the CSV."""
    need_soffice()
    b, _, rows = made
    shown, heads = _summary(b, tmp_path / "ch.xlsx", "CHANNEL")
    assert heads[-2:] == [AVG, MED]
    for lab, got in shown.items():
        rs = rows if lab == "All" else [r for r in rows if (r["CHANNEL"] or "(blank)") == lab]
        avg, med = _want(rs)
        assert avg is not None
        assert _same(got[AVG], avg), (lab, got[AVG], avg)
        assert _same(got[MED], med), (lab, got[MED], med)


def test_summary_on_one_origination_year_ties_to_the_loan_file(made, tmp_path):
    """The filter: one origination year's loans only, each FICO band and All."""
    need_soffice()
    b, _, rows = made
    year = sorted({r["ORIG_DATE"][:4] for r in rows if r["ORIG_DATE"]})[1]
    mine = [r for r in rows if r["ORIG_DATE"][:4] == year]
    shown, _ = _summary(b, tmp_path / "yr.xlsx", "CHANNEL", only=year)
    for lab, got in shown.items():
        rs = mine if lab == "All" else [r for r in mine if r["CHANNEL"] == lab]
        avg, med = _want(rs)
        assert _same(got[AVG], avg), (lab, got[AVG], avg)
        assert _same(got[MED], med), (lab, got[MED], med)


def test_every_summary_view_on_the_views_sheet_ties_to_the_loan_file(made):
    """No LibreOffice: every Summary view the Run wrote, FICO bands included, by each year and All. A FICO band's
    loans are found from the CSV here: -9999 answered missing, a blank its own row."""
    b, _, rows = made
    views = _views(b)
    heads = _heads(b)
    a, m = 1 + heads.index(AVG), 1 + heads.index(MED)
    assert [k for k in views if k.startswith("S|CHANNEL|")]
    checked = 0
    for k, v in views.items():
        _, col, *rest = k.split("|")
        if col != "CHANNEL":
            continue
        year = rest[0].removeprefix("where ") if len(rest) == 2 else None
        rs = [r for r in rows if year is None or r["ORIG_DATE"][:4] == year
              or (year == ch.NO_DATE and not r["ORIG_DATE"])]
        lab = v[0]
        if lab != "All":
            rs = [r for r in rs if (r["CHANNEL"] or "(blank)") == lab]
        avg, med = _want(rs)
        assert _same(v[a], avg) and _same(v[m], med), (k, v[a], v[m], avg, med)
        checked += 1
    assert checked >= 4 * 4
    # FICO, whole book: the bands' charged-off loans add up to the book's, so the averages weigh back to All's
    fico = [v for k, v in views.items() if k.startswith("S|FICO|") and "where" not in k]
    whole = next(v for v in fico if v[0] == "All")
    assert _same(whole[a], _want(rows)[0]) and _same(whole[m], _want(rows)[1])


def test_the_left_out_loans_are_counted_in_a_warning(made):
    """A charge-off before origination, a charge-off date that isn't a date, and no origination date: each counted
    on the Log and Check, never silently dropped."""
    b, _, _ = made
    said = _text(b)
    assert "Months to charge-off: 3 loans with a charge-off date are left out of it" in said
    for part in ('1 with a CO_DATE that isn\'t a date', "1 with no readable ORIG_DATE",
                 "1 charged off before they were made (CO_DATE before ORIG_DATE)"):
        assert part in said, part


def test_grids_offers_it_as_a_measure_and_it_ties_to_the_loan_file(made, tmp_path):
    """Months to charge-off (avg) on Grids: CHANNEL's All row, each segment, against the CSV."""
    need_soffice()
    b, _, rows = made
    assert results.CO_MONTHS_NAME in tabs.options(load_workbook(b), results.GRIDS, "Measure")
    grid = tabs.options(load_workbook(b), results.GRIDS, "Grid")[0]
    ws = tabs.calculated(tabs.choose(b, tmp_path / "g.xlsx", results.GRIDS, grid=grid,
                                     measure=results.CO_MONTHS_NAME), results.GRIDS)
    rate = tabs.block(ws, "Rate")
    for seg in ("Branch", "Broker", "Online"):
        assert _same(rate[("All", seg)], _want([r for r in rows if r["CHANNEL"] == seg])[0]), seg
    assert _same(rate[("All", "All")], _want(rows)[0])


def test_columns_offers_charge_off_date_and_does_not_grey_it(made):
    """Set up suggests CO_DATE as Charge-off date, and the bleed uses it, so its row isn't grey as unused."""
    b, _, _ = made
    ws = load_workbook(b)["Columns"]
    row = next(r for r in book.table_rows(ws) if r[book.C_NAME - 1].value == "CO_DATE")
    assert row[book.C_MEANS - 1].value == "Charge-off date"
    assert book.NOT_USED not in str(row[book.C_LOOK - 1].value or "")


def test_without_a_charge_off_date_nothing_changes(made):
    """The same book without CO_DATE: Summary has its thirteen columns and no more, Grids no new Measure, and no
    warning names months to charge-off."""
    _, b, _ = made
    assert _heads(b) == ["Loans", "% of loans", "Bad loans", "Bad loans %", "Booked $", "% of booked", "GCOs ($)",
                         "GCOs ÷ Booked", "× book", "% of GCOs", "RANR $", "RANR ÷ Booked", "% of RANR"]
    assert results.CO_MONTHS_NAME not in tabs.options(load_workbook(b), results.GRIDS, "Measure")
    assert "months to charge-off" not in _text(b).lower()


# --------------------------------------------------------------------------
# the engine alone, on a book small enough to check by eye


def _small(co_dates, orig="2024-01-31", columns=None):
    from conftest import cube, row, table
    rows = [{**row(i, 600 + 100 * (i % 2), "A" if i < 3 else "B", 100, 1 if d else 0, 50 if d else 0),
             "OPEN_DT": orig, "CO_DT": d} for i, d in enumerate(co_dates)]
    cfg = cube(key=None, booked=None, outcome=None, gco=None, ranr=None, columns_confirmed=True,
               columns=columns or {"ID": "key", "BAL": "booked", "BAD": "outcome", "GCO": "gco", "RANR": "ranr",
                                  "SCORE": "fico", "CHAN": "category", "OPEN_DT": "origination_date",
                                  "CO_DT": "chargeoff_date"})
    from pocketbook import engine
    return engine.run(cfg, table(rows))


def test_the_engine_counts_whole_calendar_months_and_ignores_the_day():
    """31 Jan to 1 Feb is 1, to 29 Feb is 1, to 1 Mar is 2, to 31 Jan the next year is 12; blank never charged off."""
    from pocketbook import engine
    res = _small(["2024-02-01", "2024-02-29", "", "2024-03-01", "2025-01-31", ""])
    rows = dict(engine.summary_rows(res, "chan"))
    assert rows["A"]["co_avg"] == pytest.approx(1.0) and rows["A"]["co_median"] == 1
    assert rows["B"]["co_avg"] == pytest.approx(7.0) and rows["B"]["co_median"] == pytest.approx(7.0)
    assert rows["All"]["co_avg"] == pytest.approx((1 + 1 + 2 + 12) / 4) and rows["All"]["co_median"] == 1.5
    assert not [w for w in res.warnings if "charge-off" in w]


def test_a_charge_off_date_without_an_origination_date_is_said():
    """Charge-off date marked, no Origination date: no new columns, and a warning says why, never silence."""
    from pocketbook import engine
    res = _small(["2024-02-01", ""], columns={"ID": "key", "BAL": "booked", "BAD": "outcome", "GCO": "gco",
                                              "RANR": "ranr", "SCORE": "fico", "CHAN": "category",
                                              "OPEN_DT": "unused", "CO_DT": "chargeoff_date"})
    assert "co_avg" not in engine.summary_columns(res)
    assert any("no column in the extract is marked Origination date" in w for w in res.warnings)
