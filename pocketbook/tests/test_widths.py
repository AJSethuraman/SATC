"""Column widths (the firm, 29 Sep 2026: "take a look at column spacing. i prefer to have nice even layouts, or at
least the column sizes should make sense for the data we see"; the survey and its plan are
docs/column-widths-survey-2026-09-29.md).

Every width here is worked out from the Run's own labels and values, so the checks read the labels and values back
and hold the widths to them: Grids' data columns one width across all four blocks and wide enough for every label on
two lines and every value on one (G1, G3, G5), its two label columns one width (G2), a split grid's segment over its
parts (G4), the groups' booked dollars in thousands before they would overflow (G6), Split's two grids alike (S1),
the label columns of Pockets, Paid cost kept and Start here fitted to the Run's labels (P1), and Look's labels (L1).
Each check reads the workbook as written; none needs LibreOffice."""

from __future__ import annotations

import csv
import math
import random

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

from pocketbook import book, choices as ch, config as cfgmod, engine, house, look, perm, results, synth
from pocketbook.ingest import read_table
from test_book import _answer

#: the survey's long labels: the bank's channel names, and a loan-amount bucket
LONG = {"Branch": "Customer/Branch", "Broker": "Non-Customer/VLA", "Online": "Non-Customer/Online Direct"}


def _width(ws, c: int) -> float:
    return ws.column_dimensions[get_column_letter(c)].width


def _extract(folder, n=3000, long=True):
    """The synthetic book with the survey's additions: the channels renamed long, a loan-amount bucket
    (AMT_BUCKET, "$10k–<$15k"), and SYS_FLAG (Y or N, a blank on every 97th loan)."""
    src = synth.write_extract(folder / "src", n=n)
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    rng = random.Random(29)
    for i, r in enumerate(rows):
        r["CHANNEL"] = LONG.get(r["CHANNEL"], r["CHANNEL"]) if long else r["CHANNEL"]
        try:
            lo = int(float(r["ORIG_BAL"]) // 5000) * 5
            r["AMT_BUCKET"] = f"${lo}k–<${lo + 5}k" if lo < 40 else "$40k+"
        except ValueError:
            r["AMT_BUCKET"] = ""
        r["SYS_FLAG"] = "" if i % 97 == 0 else rng.choice("YN")
    out = folder / "long.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return out


def _run(folder, long=True, **picks):
    """A whole Run on that book, and the engine's result for it."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("POCKETBOOK_MEMORY", str(folder / "memory.yaml"))
        mp.setattr(perm, "SHUFFLES", 500)
        x = _extract(folder, long=long)
        b = book.set_up(x, choices=ch.Choices(run_kind=ch.BLEED, outcome="BAD_FLAG", **picks)).book
        _answer(b)
        ran = book.run(b)
        assert ran.ok, ran.lines
        raw, problems, _ = book.read_book(b)
        assert not problems
        res = engine.run(cfgmod.parse(raw), read_table(x))
    return {"book": b, "wb": load_workbook(b), "res": res}


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    """Three Runs: long labels split at REV_DEBT's median (the survey's run C), a category split (run B), and no
    split at all (run A)."""
    d = tmp_path_factory.mktemp("widths")
    return {"long": _run(d / "long", bands=("FICO",), segments=("CHANNEL", "AMT_BUCKET"), split="REV_DEBT"),
            "category": _run(d / "cat", long=False, bands=("FICO", "ORIG_BAL"), segments=("CHANNEL", "ASSET_CLASS"),
                             split="SYS_FLAG"),
            "plain": _run(d / "plain", long=False, bands=("FICO",), segments=("CHANNEL", "ASSET_CLASS"))}


KINDS = ("long", "category", "plain")


def _grids(run):
    """Grids as written: the sheet, where its blocks sit, and what the Run's grids put on _views."""
    ws = run["wb"][results.GRIDS]
    views = {r[0]: [v for v in r[1:] if v is not None] for r in run["wb"][results.VIEWS].iter_rows(values_only=True)
             if isinstance(r[0], str)}
    low, right = next((c.row, x.column) for c in ws["B"] if c.value == "vs rest of band" for x in ws[c.row]
                      if x.value == "Loans")
    top = next(c.row for c in ws["B"] if isinstance(c.value, str) and c.value.startswith('="Rate · "'))
    return ws, views, top, low, right


# --------------------------------------------------------------------------
# The helpers


def test_lines_break_as_excel_does_at_a_space_or_after_a_hyphen_never_inside_a_word_that_fits():
    assert house.lines_at("Non-Customer/VLA A", 14) == 2               # "Non-Customer/" can't break at the slash
    assert house.two_line_width("Non-Customer/VLA A") == 14            # "Non-Customer/VLA" / "A" is 16; "Non-" first
    assert house.two_line_width("Non-Customer/Online Direct") == 19    # "Non-Customer/Online" / "Direct"
    assert house.two_line_width("Branch") == 6                         # a word is never broken to make two lines
    assert house.two_line_width("$10k–<$15k") == 10                    # an en dash is not a hyphen
    assert house.lines_at("Non-Customer/Online Direct", 14) == 3
    assert house.fit(["ab", "abcdef"], floor=3, cap=20) == 8 and house.fit([], floor=9, cap=20) == 9
    assert house.fit(["x" * 40], floor=3, cap=20) == 20


# --------------------------------------------------------------------------
# Grids


def test_grid_widths_follow_the_longest_label_value_and_segment():
    """G1 and G2 worked out by hand: the bank's "Non-Customer/VLA A" is 14 on two lines, so its column is 16; a
    segment over two parts shares its width between them; a value's characters + 2; the cap and floor hold."""
    fit = lambda **k: {"heads": set(), "segs": set(), "parts": 0, "rows": set(), "values": 0, **k}   # noqa: E731
    assert results.grid_widths(fit(heads={"Non-Customer/VLA A"}))[0] == 16
    assert results.grid_widths(fit(heads={"Branch", "All"}))[0] == 9                     # the floor
    assert results.grid_widths(fit(heads={"high"}, values=9))[0] == 11                   # "+0.99 pts"
    assert results.grid_widths(fit(segs={"Non-Customer/Online Direct"}, parts=2))[0] == 11   # 19 + 2 over two
    assert results.grid_widths(fit(heads={"Non-Customer/Online Direct"}))[0] == results.DATA_CAP
    assert results.grid_widths(fit(), {"values": 11})[0] == 13                           # the groups' "388,477,052"
    assert results.grid_widths(fit(rows={"15,760 - 26,665", "(marked missing)"}))[1] == 19
    assert results.grid_widths(fit(rows={"x" * 40}))[1] == results.LABEL_CAP


@pytest.mark.parametrize("kind", KINDS)
def test_grids_data_columns_are_one_width_in_all_four_blocks_and_the_label_columns_match(runs, kind):
    ws, _, _, _, right = _grids(runs[kind])
    left, nc = 2, right - 4
    data = [_width(ws, c) for c in list(range(left + 1, left + nc + 1)) + list(range(right + 1, right + nc + 1))]
    assert len(set(data)) == 1, data                                     # G1, G5
    assert _width(ws, left) == _width(ws, right)                         # G2
    assert _width(ws, right - 1) == 3
    assert results.DATA_FLOOR <= data[0] <= results.DATA_CAP
    assert results.LABEL_FLOOR <= _width(ws, left) <= results.LABEL_CAP


@pytest.mark.parametrize("kind", KINDS)
def test_grids_column_labels_fit_two_lines_or_the_width_is_at_its_cap(runs, kind):
    ws, views, _, _, right = _grids(runs[kind])
    dw = _width(ws, 3)
    heads = {str(h) for k, v in views.items() if k.startswith("G|") and k.endswith("|heads") for h in v}
    segs = {str(s) for k, v in views.items() if k.startswith("G|") and k.endswith("|segs") for s in v if s}
    parts = len(results._split_layout(runs[kind]["res"]))
    assert heads
    for h in heads:
        # every label two lines at most, or the width is as wide as it may go
        assert dw >= min(results.DATA_CAP, house.two_line_width(h) + 2), h
        if house.two_line_width(h) + 2 <= results.DATA_CAP:
            assert house.lines_at(h, dw - 2) <= 2, h
    for s in segs:                                                       # G4: a segment over all its parts
        assert parts * dw >= min(parts * results.DATA_CAP, house.two_line_width(s) + 2), s
    # G3: two lines at most, but for the survey's 26-character "Non-Customer/Online Direct", which can't fit two
    # lines at the cap; its header row is then given the lines it needs, never clipped
    assert max(house.lines_at(h, dw - 2) for h in heads
               if house.two_line_width(h) + 2 <= results.DATA_CAP) <= 2
    lines = max(house.lines_at(h, dw - 2) for h in heads)
    _, _, top, _, _ = _grids(runs[kind])
    hdr = 2 if parts else 1
    assert ws.row_dimensions[top + hdr].height >= results.HEAD_LINE * lines


@pytest.mark.parametrize("kind", KINDS)
def test_no_grids_value_is_wider_than_its_column(runs, kind):
    """Every number a block shows, as its cell's format shows it, fits the data width with room to spare."""
    ws, views, _, _, _ = _grids(runs[kind])
    dw = _width(ws, 3)
    pts = {m.name for m in runs[kind]["res"].measures if m.in_points}
    longest = 0
    for k, v in views.items():
        if not k.startswith("G|") or k.endswith(("|cols", "|rows", "|names", "|heads", "|segs", "|meta", "|total")):
            continue
        parts = k.split("|")
        what = parts[-2] if parts[-1].isdigit() else parts[-1]
        meas = parts[-3] if parts[-1].isdigit() and len(parts) > 3 else ""
        fmt = ("n" if what == "loans" else "usd" if meas == results.SIZE and what in ("rate", "median")
               else "amt" if meas.startswith("show_") else "pct" if what == "rate"
               else "pts" if meas in pts else "x")
        longest = max([longest] + [len(results._shown(x, fmt)) for x in v if isinstance(x, (int, float))])
    assert longest
    assert dw >= min(results.DATA_CAP, longest + 2), (dw, longest)


@pytest.mark.parametrize("kind", KINDS)
def test_the_four_blocks_line_up_and_their_headers_are_one_height(runs, kind):
    ws, _, top, low, right = _grids(runs[kind])
    split = bool(results._split_layout(runs[kind]["res"]))
    hdr = 2 if split else 1
    # side by side on the same rows, and the lower pair the same distance under the upper
    assert str(ws.cell(row=top, column=right).value).startswith('=IF(ISNUMBER(')
    assert ws.cell(row=low, column=right).value == "Loans"
    heights = []
    for t in (top, low):
        heights.append([ws.row_dimensions[t + k].height for k in range(1, hdr + 1)])
        assert all(ws.cell(row=t + hdr, column=c).alignment.wrap_text for c in (3, right + 1))
    assert heights[0] == heights[1] and all(heights[0])
    # G4: a split grid's segments are merged over their parts, in both columns of blocks
    merged = [m for m in ws.merged_cells.ranges if m.min_row in (top + 1, low + 1) and m.max_col > m.min_col]
    assert bool(merged) == split
    if split:
        parts = len(results._split_layout(runs[kind]["res"]))
        assert all(m.max_col - m.min_col + 1 == parts for m in merged)


def test_a_split_grids_header_reads_back_as_its_segment_and_part(runs):
    """What the tests read (tabs.block) is the same label the grid had before the header became two rows."""
    import tabs
    from recalc import SOFFICE, recalc
    if SOFFICE is None:
        pytest.skip("LibreOffice isn't installed")
    run = runs["long"]
    res = run["res"]
    g = res.three_way[0]
    names = book._names(res)
    name = f"{names[g.band]} x {names[g.dimension]}"
    out = tabs.choose(run["book"], run["book"].parent / "g.xlsx", results.GRIDS, grid=name)
    loans = tabs.block(recalc(out, out.parent / "rc")[results.GRIDS], "Loans")
    for (bl, d), c in g.inner():
        assert loans[(bl, results._short(res, d))] == c.rows


def test_booked_dollars_too_long_for_the_widest_column_show_in_thousands(runs, monkeypatch):
    """G6: at the bank a grid's booked dollars run to 13 characters ("3,884,770,520"); past the cap they are shown
    in thousands, never as ####."""
    res = runs["category"]["res"]
    for cap, thousands in ((results.DATA_CAP, False), (10, True)):
        monkeypatch.setattr(results, "DATA_CAP", cap)
        wb = Workbook()
        results.write_grids(wb, res, results.Choices(wb), results.Views(wb))
        ws = wb[results.GRIDS]
        fmts = {c.number_format for row in ws.iter_rows() for c in row}
        assert (results.THOUSANDS_FMT in fmts) == thousands, cap


# --------------------------------------------------------------------------
# Split


@pytest.mark.parametrize("kind", ("long", "category"))
def test_split_grids_share_one_data_width_and_the_dropdown_spans_three_columns(runs, kind):
    ws = runs[kind]["wb"][results.SPLIT]
    res = runs[kind]["res"]
    t = next(c.row for c in ws["B"] if isinstance(c.value, str) and c.value.startswith("=") and
             c.value.endswith(('", value vs rest"', '", high vs low"')))
    right = next(c.column for c in ws[t] if c.value == "p-value per pocket")
    nd = right - 4
    summary = set(range(3, 10))
    data = [_width(ws, c) for c in list(range(3, 3 + nd)) + list(range(right + 1, right + nd + 1))
            if c not in summary]
    assert len(set(data)) <= 1, data
    assert all(_width(ws, c) >= results.SPLIT_FLOOR for c in list(range(3, 3 + nd)) + list(range(right + 1, right + nd + 1)))
    assert _width(ws, 2) == _width(ws, right) or right in summary
    grid = next(c for c in ws["B"] if c.value == "GRID").row + 1
    assert any(m.min_row == grid and (m.min_col, m.max_col) == (2, 4) for m in ws.merged_cells.ranges)
    need = max(house.two_line_width(str(d)) + 2 for g in res.grids for d in g.dim_labels)
    assert _width(ws, right + 1) >= min(results.DATA_CAP, need)


# --------------------------------------------------------------------------
# Pockets, Paid cost kept, Start here, Look


@pytest.mark.parametrize("kind", KINDS)
def test_the_segment_and_band_columns_fit_the_runs_labels(runs, kind):
    run = runs[kind]
    res, wb = run["res"], run["wb"]
    names = book._names(res)
    segs = [results._segment(names, g, d) for g in res.grids for d in g.dim_labels]
    bands = [f"{names[g.band]} {bl}" for g in res.grids for bl in g.band_labels]
    need = lambda xs: min(results.LABELS_CAP, max(len(x) for x in xs) + 3)          # noqa: E731
    pk = wb[results.POCKETS]
    assert _width(pk, results.K_SEG) >= need(segs) and _width(pk, results.K_BAND) >= need(bands)
    pck = wb[results.PCK]
    assert _width(pck, results.C_SEG) >= need([str(d) for g in res.grids for d in g.dim_labels])
    assert _width(pck, results.C_BAND) >= need([str(bl) for g in res.grids for bl in g.band_labels])
    sh = wb["Start here"]
    tops = [r for r in wb[book.FOUND].iter_rows(values_only=True) if r and r[0] == "top"]
    if tops:
        assert _width(sh, 3) >= need([r[book.TOP_SEG - 1] for r in tops])
    assert _width(sh, 2) >= len("Largest, worse and material") + 2
    # P2: a heading longer than its values sets its column
    assert _width(pk, results.K_CAUGHT) >= len("Could have caught") + 2
    assert _width(pk, results.K_P) >= len("under 0.01%") + 2


@pytest.mark.parametrize("kind", KINDS)
def test_look_labels_fit_their_column(runs, kind):
    ws = runs[kind]["wb"]["Look"]
    labels = [c.value for c in ws["B"] if isinstance(c.value, str) and not c.value.startswith("=")
              and c.row > look.FIRST and c.font and not c.font.b and len(c.value) < 40]
    assert "Moves together (correlation)" in labels or kind != "long"     # a number split has its scatter
    assert _width(ws, 2) >= math.ceil(max(len(x) for x in labels) * look.LOOK_PER_CHAR + 2)


@pytest.mark.parametrize("kind", KINDS)
def test_worse_and_together_fit_the_borderline_flag(runs, kind):
    """Borderline landed with the widths (29 Sep 2026, evening): Worse? can read "Not sure · borderline (p 0.052)" and
    Together "Earns less, not from losses · borderline (p 0.048)"; each column fits the widest it can print."""
    from pocketbook import live, stats
    wb = runs[kind]["wb"]
    worse = f"{live.NOT_SURE} · {stats.borderline_words(0.052, 0.95)}"
    assert _width(wb[results.POCKETS], results.K_WORSE) >= len(worse)
    longest = max(len(f"{t} · {stats.borderline_words(0.048, 0.95)}") for t in results.TOGETHER.values())
    assert _width(wb[results.PCK], results.C_TOG) >= longest
