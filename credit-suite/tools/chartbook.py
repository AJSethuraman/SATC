#!/usr/bin/env python3
"""Build a SECOND workbook: the same numbers, as charts.

    python tools/chartbook.py --workbook Bank_Peer_Monitor.xlsm
    python tools/chartbook.py --workbook Bank_Peer_Monitor.xlsm --out Peers_Charts.xlsx

The monitor answers "who is bad now". This answers "who is getting worse, and
how does that compare", which is the question a credit review actually asks. It
reads the history already sitting in `Raw_FDIC` -- sixteen quarters, twelve
banks -- and writes native Excel line charts over it.

WHY A SECOND WORKBOOK RATHER THAN A TAB IN THE FIRST

Carried lesson L4 says no native charts, for two reasons, and they turned out to
have different lifespans. **Both were tested on the build PC rather than
inherited**, because a lesson that blocks something valuable is worth
re-checking:

* *"the top unreadable-content / recovered trigger"* -- **did not reproduce.**
  A native openpyxl LineChart opened cleanly in Excel 16.0, twice: once in a
  bare `.xlsx`, and once added to the real `Bank_Peer_Monitor.xlsm` beside its
  VBA project, where the ExtractFiles macro still ran afterwards. Zero dialogs
  in both.
* *"they re-emit on every refresh"* -- **still true, and it is the binding
  one.** The runner rewrites the monitor on every run, so a chart tab there
  would be regenerated each time and any analyst's customisation lost.

So charts live here instead. Regenerated wholesale, nothing to re-emit. And
because this workbook carries no macros it opens with **no security banner** --
the monitor's own `.xlsm` is blocked by Excel's Mark of the Web when it arrives
by email, and a chart nobody can see is not a chart.

The numbers are not recomputed here. They come from the monitor's own engine, so
a chart cannot disagree with the dashboard it was drawn from.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import openpyxl                                        # noqa: E402
from openpyxl.chart import LineChart, Reference        # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter           # noqa: E402

from trend import MEANS, WORSE_WHEN, read_panel        # noqa: E402

try:
    from credit_suite.sources.fdic import plain
except ImportError:                                    # pragma: no cover
    plain = None

#: Peer-comparison sheets: one metric, every bank.
PEER_METRICS = ["NCLNLSR", "NTLNLSQR", "PD3089R", "LNRESNCR", "TEXAS", "EQV"]

#: The four stages of a loan going wrong, for the one-bank view. Same book at
#: each stage, so the lines are comparable and the lead-lag is the point.
STAGES = [("P3CONOTHR", "30-89 days late"),
          ("P9CONOTHR", "90+ days, still accruing"),
          ("NACONOTHR", "Nonaccrual"),
          ("NTCONOTQR", "Net charge-offs (annualised)")]

HEAD = PatternFill("solid", fgColor="1E3D63")
HEAD_FONT = Font(color="FFFFFF", bold=True, size=10)
TITLE_FONT = Font(bold=True, size=13)
NOTE_FONT = Font(size=9, color="667286")


def _quarter(iso: str) -> str:
    return "%sQ%d" % (iso[2:4], (int(iso[5:7]) + 2) // 3)


def _sheet_name(prefix: str, name: str) -> str:
    """Excel caps sheet names at 31 chars and forbids []:*?/\\ ."""
    clean = "".join(c for c in name if c not in "[]:*?/\\")
    return ("%s_%s" % (prefix, clean))[:31]


def _write_grid(ws, row0: int, periods: List[str], rows: List[tuple]) -> int:
    """Header + one row per series. Returns the last row written."""
    ws.cell(row0, 1, "Series").fill = HEAD
    ws.cell(row0, 1).font = HEAD_FONT
    for i, iso in enumerate(periods):
        cell = ws.cell(row0, 2 + i, _quarter(iso))
        cell.fill, cell.font = HEAD, HEAD_FONT
        cell.alignment = Alignment(horizontal="center")
    for j, (label, values) in enumerate(rows, start=1):
        ws.cell(row0 + j, 1, label)
        for i, v in enumerate(values):
            c = ws.cell(row0 + j, 2 + i)
            if v is not None:
                c.value = round(float(v), 4)
                c.number_format = "0.00"
    ws.column_dimensions["A"].width = 30
    for i in range(len(periods)):
        ws.column_dimensions[get_column_letter(2 + i)].width = 8
    return row0 + len(rows)


def _add_chart(ws, title: str, subtitle: str, row0: int, n_rows: int,
               n_cols: int, anchor: str) -> None:
    chart = LineChart()
    chart.title = title
    chart.style = 2
    chart.height, chart.width = 9.5, 26
    chart.y_axis.title = subtitle
    chart.y_axis.majorGridlines = None
    data = Reference(ws, min_col=1, max_col=1 + n_cols,
                     min_row=row0 + 1, max_row=row0 + n_rows)
    chart.add_data(data, titles_from_data=True, from_rows=True)
    chart.set_categories(Reference(ws, min_col=2, max_col=1 + n_cols,
                                   min_row=row0, max_row=row0))
    for series in chart.series:
        series.smooth = False
    ws.add_chart(chart, anchor)


def build(source: Path, out: Path, banks: Optional[List[str]] = None) -> Path:
    panels = read_panel(source)
    if "NCLNLSR" not in panels:
        raise SystemExit("no trendable data in %s" % source.name)
    periods = list(reversed(panels["NCLNLSR"].series[
        next(iter(panels["NCLNLSR"].series))].periods))
    all_banks = sorted(panels["NCLNLSR"].series)
    chosen = [b for b in all_banks if not banks or b in banks]

    wb = openpyxl.Workbook()
    about = wb.active
    about.title = "About"
    about["A1"] = "%s -- charts" % source.stem
    about["A1"].font = Font(bold=True, size=15)
    lines = [
        "",
        "What this is",
        "  The same numbers as the monitor, drawn over time. The monitor shows the latest",
        "  quarter against a threshold; this shows the direction, the pace, and how each",
        "  bank compares with its peers.",
        "",
        "Where the numbers come from",
        "  Read from the monitor's own Raw_FDIC block and computed by its own engine, so a",
        "  chart here cannot disagree with a dashboard there. Every measure traces to its",
        "  Call Report schedule, line and MDRM code -- run the monitor with --tieout to see",
        "  the full map, in plain English, with a link to the filed document.",
        "",
        "This workbook has no macros",
        "  So it opens without the security banner that blocks the monitor's own .xlsm when",
        "  that arrives by email. Nothing here needs to be enabled or unblocked.",
        "",
        "It is generated, not edited",
        "  Re-running the tool replaces it. Keep your own notes somewhere else.",
        "",
        "Coverage",
        "  %d banks, %d quarters (%s to %s), %d peer-comparison sheets and one"
        % (len(chosen), len(periods), _quarter(periods[0]),
           _quarter(periods[-1]), len(PEER_METRICS)),
        "  stage-comparison sheet per bank.",
    ]
    for i, text in enumerate(lines, start=2):
        about.cell(i, 1, text)
        if text and not text.startswith("  "):
            about.cell(i, 1).font = Font(bold=True, size=11)
    about.column_dimensions["A"].width = 95

    # --- one metric, every bank ------------------------------------------
    for metric in PEER_METRICS:
        panel = panels.get(metric)
        if panel is None:
            continue
        ws = wb.create_sheet(_sheet_name("Peers", metric))
        ws["A1"] = metric
        ws["A1"].font = TITLE_FONT
        meaning = (plain.describe(metric) if plain else None) or MEANS.get(metric, "")
        ws["A2"] = meaning
        ws["A2"].font = NOTE_FONT
        direction = WORSE_WHEN.get(metric)
        ws["A3"] = ("Higher is worse." if direction == "up"
                    else "Lower is worse." if direction == "down"
                    else "Direction is not a verdict for this measure.")
        ws["A3"].font = NOTE_FONT
        rows = []
        for bank in chosen:
            series = panel.series.get(bank)
            if series:
                rows.append((bank, list(reversed(series.values))))
        last = _write_grid(ws, 20, periods, rows)
        _add_chart(ws, "%s -- all peers" % metric, meaning[:40], 20,
                   len(rows), len(periods), "A5")
        ws.freeze_panes = "B21"

    # --- one bank, the four stages ---------------------------------------
    for bank in chosen:
        ws = wb.create_sheet(_sheet_name("Stages", bank))
        ws["A1"] = "%s -- other consumer loans, four stages" % bank
        ws["A1"].font = TITLE_FONT
        ws["A2"] = ("The same loan book at each stage of going wrong. If arrears "
                    "lead write-offs, these move in sequence rather than together.")
        ws["A2"].font = NOTE_FONT
        ws["A3"] = ("Charge-offs are annualised (a quarter's flow x4); the others "
                    "are point-in-time balances. Compare shapes, not heights.")
        ws["A3"].font = NOTE_FONT
        rows = []
        for metric, label in STAGES:
            panel = panels.get(metric)
            series = panel.series.get(bank) if panel else None
            if series:
                rows.append((label, list(reversed(series.values))))
        if not rows:
            continue
        _write_grid(ws, 20, periods, rows)
        _add_chart(ws, "%s -- delinquency to charge-off" % bank,
                   "% of that loan book", 20, len(rows), len(periods), "A5")
        ws.freeze_panes = "B21"

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-w", "--workbook", required=True)
    ap.add_argument("-o", "--out")
    ap.add_argument("--bank", action="append",
                    help="limit to these banks (repeatable)")
    args = ap.parse_args(argv)
    source = Path(args.workbook)
    out = Path(args.out) if args.out else source.with_name(source.stem + "_Charts.xlsx")
    written = build(source, out, args.bank)
    book = openpyxl.load_workbook(written)
    print("wrote %s" % written)
    print("  %d sheets, %d charts"
          % (len(book.sheetnames),
             sum(len(book[s]._charts) for s in book.sheetnames)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
