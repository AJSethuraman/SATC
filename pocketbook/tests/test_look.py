"""The Look tab (fix 3.8, the audit's item f: band edges were chosen blind; the redesign's section 4).

Set up shows each number column's spread and its likely code beside a live column chart; a number column
splitting the pockets adds a scatter of it against each band column (docs/statistics.md A9). Every number is
checked against a count made by hand from the CSV, not against look.py's own arithmetic. The live bars, the
edge lines and the one-load Run are in tests/test_answer_tabs.py."""

import csv
import statistics

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, ScatterChart

from pocketbook import book, choices as ch, house, look, synth
from pocketbook.ingest import read_table
from test_book_results import _ready
from test_book_dates import _choose

#: the number columns Look draws: those that can be cut into bands. GCO_AMT and RANR_AMT are outcomes (H, the firm,
#: 27 Sep 2026)
NUMBER_COLUMNS = ["FICO", "ORIG_BAL", "REV_DEBT"]


def _csv(path, col) -> list[str]:
    with open(path, newline="", encoding="utf-8") as f:
        return [row[col].strip() for row in csv.DictReader(f)]


def _numbers(raw: list[str]) -> list[float]:
    out = []
    for v in raw:
        try:
            out.append(float(v))
        except ValueError:
            pass
    return out


def _blocks(ws) -> dict[str, dict]:
    """Each block by column: its row and its labelled lines as (value, share)."""
    out: dict[str, dict] = {}
    for c in ws["B"]:
        if c.value in NUMBER_COLUMNS and (c.fill.fgColor.rgb or "")[-6:] == house.INK and c.row >= look.FIRST:
            r = c.row
            lines = {ws.cell(row=r + k, column=2).value: (ws.cell(row=r + k, column=3).value,
                                                          ws.cell(row=r + k, column=4).value)
                     for k in range(1, look.R_MAX + 1)}
            fmt = {ws.cell(row=r + k, column=2).value: ws.cell(row=r + k, column=3).number_format
                   for k in range(1, look.R_MAX + 1)}
            out[c.value] = {"row": r, "lines": lines, "fmt": fmt}
    return out


def _title(chart) -> str:
    return chart.title.tx.rich.p[0].r[0].t


def _main_charts(ws):
    """The column charts beside the blocks (anchored at H), not the red code bars (at F)."""
    return [c for c in ws._charts if isinstance(c, BarChart) and c.anchor._from.col + 1 == 8]


def _dots(ds, header: str) -> list[tuple]:
    for col in range(1, ds.max_column + 1):
        if ds.cell(row=3, column=col).value == header:
            return [(ds.cell(row=r, column=col).value, ds.cell(row=r, column=col + 1).value)
                    for r in range(4, ds.max_row + 1) if ds.cell(row=r, column=col).value is not None]
    raise KeyError(header)


def test_set_up_writes_a_block_and_a_chart_for_every_number_column(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=3000))
    wb = load_workbook(out.book)
    assert wb.sheetnames.index("Look") == wb.sheetnames.index("Columns") + 1
    assert wb["_look"].sheet_state == "hidden"
    ws = wb["Look"]
    assert ws["B1"].value == "Look" and "before you choose its band edges" in ws["C1"].value
    blocks = _blocks(ws)
    # the loan number, the channel, the 0/1 flag and the four asset classes have no edges to choose
    assert list(blocks) == NUMBER_COLUMNS
    assert not [c for c in ws._charts if isinstance(c, ScatterChart)]                   # no split chosen
    assert sorted(c.anchor._from.row for c in _main_charts(ws)) == sorted(b["row"] for b in blocks.values())
    text = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
    assert any(t.startswith("None: nothing splits the pockets.") for t in text)


def test_the_numbers_match_a_count_by_hand(tmp_path):
    x = synth.write_extract(tmp_path, n=3000)
    wb = load_workbook(book.set_up(x).book)
    blocks = _blocks(wb["Look"])

    fico = _csv(x, "FICO")
    blank = sum(1 for v in fico if v == "")
    nums = _numbers(fico)
    rest = [v for v in nums if v != -9999]
    f = blocks["FICO"]["lines"]
    assert f["Loans"][0] == 3000
    assert f["Blank"] == (blank, blank / 3000) and blank == 1
    assert f["At -9999, likely a code"] == (60, 60 / 3000)               # every 50th loan
    assert f["Smallest"][0] == min(rest) and f["Largest"][0] == max(rest)
    assert f["Median"][0] == statistics.median(rest)
    assert f["Mean"][0] == statistics.fmean(rest)                        # the firm: the mean beside the median
    assert min(rest) > 300                                                # the code is out of the spread
    assert blocks["FICO"]["fmt"]["Median"] == "#,##0"                     # a score reads as a whole number
    # the slices hold every loan in the spread, and none of the code
    hs = wb["_look"]
    g = next(c for c in range(2, hs.max_column + 1) if hs.cell(row=look.DATA_TOP - 1, column=c).value == "FICO")
    counts = [hs.cell(row=look.DATA_TOP + i, column=g + look.G_COUNT).value for i in range(look.SLICES)]
    below = hs.cell(row=look.S_BELOW, column=g + look.G_VALUE).value
    above = hs.cell(row=look.S_ABOVE, column=g + look.G_VALUE).value
    assert sum(counts) + below + above == len(rest)

    bal = _csv(x, "ORIG_BAL")
    got = blocks["ORIG_BAL"]["lines"]
    vals = _numbers(bal)
    assert got["Blank"] == (1, 1 / 3000) and got["Likely a code"] == ("none found", None)
    assert (got["Smallest"][0], got["Median"][0], got["Largest"][0]) == \
        (min(vals), statistics.median(vals), max(vals))
    assert blocks["ORIG_BAL"]["fmt"]["Median"] == "#,##0"                 # dollars too
    assert look.shape_of(read_table(x), "GCO_AMT").text == 1              # the "#N/A", counted as not a number


def test_the_slices_sit_on_round_numbers_around_the_1st_and_99th_percentile():
    vals = sorted([500.0] + [600.0 + i % 250 for i in range(5000)] + [990.0])
    lo, hi = look.span(vals)
    assert (lo, hi) == (600.0, 850.0)
    counts, below, above = look.slices(vals, lo, hi)
    assert len(counts) == look.SLICES and below == 1 and above == 1 and sum(counts) == 5000
    bars, low, high = look.regroup(vals, 10, lo, hi, lo, hi)
    assert (low, high) == (1, 1) and sum(bars) == 5000 and len(bars) == 10


def test_a_run_split_by_revolving_debt_adds_a_scatter_against_each_band_column(tmp_path):
    b = _ready(tmp_path, n=3000)
    _choose(b, split="REV_DEBT")
    raw, _, _ = book.read_book(b)
    bands = [x["field"] for x in raw["bands"]]
    assert bands == ["FICO", "ORIG_BAL"]
    assert book.run(b).ok
    wb = load_workbook(b)
    assert wb.sheetnames.index("Look") == wb.sheetnames.index("Columns") + 1        # the Run kept its place
    ws, ds = wb["Look"], wb["_dots"]
    assert len(_main_charts(ws)) == len(NUMBER_COLUMNS)                              # the blocks' charts kept
    scatters = [c for c in ws._charts if isinstance(c, ScatterChart)]
    assert sorted(_title(c) for c in scatters) == [f"REV_DEBT against {x}" for x in bands]
    text = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
    assert any("random sample of 2,000" in t for t in text)                 # it says it's a sample
    assert "Moves together (correlation)" in text
    x = b.with_name("loans.csv")
    rev = _csv(x, "REV_DEBT")
    for band in bands:
        # every dot is a real loan's (band, REV_DEBT), at most 2,000 of them, and never the -9999 code
        dots = _dots(ds, band)
        loans = set(zip(_numbers_or_none(_csv(x, band)), _numbers_or_none(rev)))
        assert len(dots) == 2000 and all(d in loans for d in dots)
        assert all(d[0] != -9999 for d in dots)


def test_the_split_chosen_in_the_launcher_draws_its_scatters_at_set_up(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=2000), choices=ch.Choices(run_kind=ch.BLEED, split="REV_DEBT"))
    ws = load_workbook(out.book)["Look"]
    assert sorted(_title(c) for c in ws._charts if isinstance(c, ScatterChart)) == \
        ["REV_DEBT against FICO", "REV_DEBT against ORIG_BAL"]


def _numbers_or_none(raw):
    out = []
    for v in raw:
        try:
            out.append(float(v))
        except ValueError:
            out.append(None)
    return out


def test_the_sample_is_the_same_every_time(tmp_path):
    table = read_table(synth.write_extract(tmp_path, n=3000))
    got = []
    for _ in range(2):
        wb = Workbook()
        look.write_look(wb, table, NUMBER_COLUMNS, "REV_DEBT", ["FICO"])
        got.append(_dots(wb["_dots"], "FICO"))
    assert got[0] == got[1] and len(got[0]) == look.SAMPLE


def test_set_up_again_rebuilds_the_tab_without_a_copy(tmp_path):
    x = synth.write_extract(tmp_path, n=2000)
    book.set_up(x)
    out = book.set_up(x)
    wb = load_workbook(out.book)
    assert [n for n in wb.sheetnames if "look" in n.lower()] == ["Look", "_look"]
    assert len(_main_charts(wb["Look"])) == len(NUMBER_COLUMNS)
    assert wb.sheetnames.index("Look") == wb.sheetnames.index("Columns") + 1
