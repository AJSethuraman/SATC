#!/usr/bin/env python3
"""Build the FRED Credit-Risk Dashboard workbook (BUILD SPEC phase 3 & 5).

Assembles every tab with openpyxl:
  * _config        -- the series dictionary + threshold bands + key cell (knob panel)
  * Raw_*          -- fixed-anchor, newest-first scaffolds (Python fills the values)
  * Dashboard_*    -- formula-driven panels referencing Raw_* (no Python to re-render)
  * Watchlist_Geo  -- ranked, validator-gated, geographic stress only
  * _code_py/_vba  -- the runner + macro as plain text (one source line per cell)
  * _readme        -- setup + run + boundary docs

It produces a base .xlsx; assemble_xlsm.py wraps it into the macro-enabled .xlsm
with the embedded vbaProject.bin. Keeping the two steps separate keeps the
xlwings/openpyxl write-path choice and the VBA embedding cleanly isolated.
"""
from __future__ import annotations

import os

from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

import runner as R
import series_seed as SEED

HERE = os.path.dirname(os.path.abspath(__file__))


def text_cell(ws, row, col, value):
    """Write a literal-text cell. openpyxl treats a string starting with '='
    as a formula; force it back to a string so source and doc lines (incl.
    '====' underlines and any leading-'=' code) round-trip faithfully."""
    cell = ws.cell(row, col, value)
    if isinstance(value, str) and value.startswith("="):
        cell.data_type = "s"
    return cell

# ---- palette -------------------------------------------------------------
NAVY = "1F3864"
STEEL = "2E5496"
LIGHT = "D9E1F2"
GREY = "808080"
ALERT_RED = "C00000"
ALERT_FILL = PatternFill("solid", fgColor="FFC7CE")
TIGHTEN_FILL = PatternFill("solid", fgColor="FFEB9C")
HDR_FILL = PatternFill("solid", fgColor=NAVY)
SUBHDR_FILL = PatternFill("solid", fgColor=STEEL)
BANNER_FILL = PatternFill("solid", fgColor=LIGHT)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WHITE_BOLD = Font(bold=True, color="FFFFFF")
NAVY_BOLD = Font(bold=True, color=NAVY)
ITALIC_GREY = Font(italic=True, color=GREY, size=9)


# ==========================================================================
# _config
# ==========================================================================
def config_rows():
    """The full _config content as a list of rows (the single source the sheet
    and the parser both consume)."""
    rows = [["FRED Credit-Risk Dashboard -- CONFIG (the knob panel). "
             "Edit values here; no code change needed."], []]
    rows.append(["[SETTINGS]"])
    rows.append(["key", "value", "help"])
    rows += [
        ["fred_api_key", "", "Optional: paste your FRED key here if you don't set "
         "the FRED_API_KEY environment variable. Get one free at "
         "https://fredaccount.stlouisfed.org/apikeys"],
        ["write_backend", "auto", "auto|xlwings|openpyxl. xlwings writes into the open book."],
        ["demo_mode", "FALSE", "TRUE = offline synthetic data (no key/network), for trying the button."],
        ["raw_slots", "100", "observations kept per series (newest-first)."],
        ["stale_multiplier", "2.0", "flag a series stale if older than this x its cadence."],
    ]
    rows += [[], ["[THRESHOLDS]"], ["key", "value", "help"]]
    rows.append(["zscore_band", 1.0, "flag a loss/delinquency series when its 8-period z-score >= this."])
    rows.append(["sloos_band", 20.0, "flag a SLOOS series when net-tightening >= this (percent)."])
    rows += [[], ["[SERIES]"], SEED.HEADER]
    for r in SEED.all_series():
        rows.append([r[h] for h in SEED.HEADER])
    rows += [[], ["[CBSA_EXTENSIONS]"],
             ["cbsa", "name", "series_id"]]
    for r in SEED.cbsa_extension_rows():
        rows.append([r["cbsa"], r["name"], r["series_id"]])
    rows += [[], ["# To add a metro: add an FHFA series row to [SERIES] using "
                  "series_id ATNHPIUS<CBSA>Q, category hpi_metro, lane price, "
                  "geo_segment cbsa:<CBSA>, watchlist_capable TRUE, transform yoy_pct."]]
    return rows


def write_config(wb):
    ws = wb.create_sheet("_config")
    rows = config_rows()
    zrow = srow = None
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row, start=1):
            ws.cell(i, j, val)
        if row and row[0] == "zscore_band":
            zrow = i
        if row and row[0] == "sloos_band":
            srow = i
    ws["A1"].font = NAVY_BOLD
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 60
    ws.column_dimensions["O"].width = 50
    # Defined names so dashboard formulas reference the bands by name.
    wb.defined_names["zscore_band"] = DefinedName("zscore_band", attr_text=f"_config!$B${zrow}")
    wb.defined_names["sloos_band"] = DefinedName("sloos_band", attr_text=f"_config!$B${srow}")
    # Highlight the section markers.
    for i, row in enumerate(rows, start=1):
        if row and isinstance(row[0], str) and row[0].startswith("["):
            ws.cell(i, 1).font = WHITE_BOLD
            ws.cell(i, 1).fill = SUBHDR_FILL
    return ws


# ==========================================================================
# Raw_* scaffolds (fixed anchors; runner fills the values)
# ==========================================================================
def write_raw_scaffold(wb, specs, blocks):
    by_tab = {}
    for s in specs:
        by_tab.setdefault(blocks[s.series_id].tab, []).append(s)
    for tab, tab_specs in by_tab.items():
        ws = wb.create_sheet(tab)
        ws["A1"] = (f"{tab} -- raw FRED observations, newest-first. Written by runner.py; "
                    f"dashboards read these by formula. Do not edit by hand.")
        ws["A1"].font = ITALIC_GREY
        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 14
        ws.column_dimensions["C"].width = 38
        for s in tab_specs:
            b = blocks[s.series_id]
            ws.cell(b.header_row, 1, s.series_id).font = NAVY_BOLD
            ws.cell(b.header_row, 2, s.title)
            ws.cell(b.header_row, 3, f"freq={s.frequency}; transform={s.transform}; "
                                     f"{'WATCHLIST' if s.watchlist_capable else 'dashboard'}")
            ws.cell(b.header_row, 3).font = ITALIC_GREY
            ws.cell(b.label_row, 1, "date").font = Font(bold=True, size=9)
            ws.cell(b.label_row, 2, "value").font = Font(bold=True, size=9)
        ws.sheet_view.showGridLines = False
    return by_tab


# ==========================================================================
# Dashboards
# ==========================================================================
def _ref(b: "R.RawBlock", offset=0):
    return f"{b.tab}!{get_column_letter(R.RAW_VALUE_COL)}{b.first_data_row + offset}"


def _tier(series_id):
    if series_id.endswith("ACBS"):
        return "All banks"
    if series_id.endswith("T100S"):
        return "Top 100"
    if series_id.endswith("OBS"):
        return "Not top 100"
    return "-"


DASH_COLS = ["Tier", "Category", "Series ID", "Title", "Latest", "Prior",
             "YoY %", "Z-score (8)", "Flag"]
COL = {name: get_column_letter(i + 1) for i, name in enumerate(DASH_COLS)}


def write_dashboard(wb, tab, specs, blocks, title, subtitle, lane):
    ws = wb.create_sheet(tab)
    ws.sheet_view.showGridLines = False
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=16, color=NAVY)
    ws["A2"] = subtitle
    ws["A2"].font = ITALIC_GREY
    # status block (filled by the runner / macro)
    for r, lab in ((1, "Last run:"), (2, "Series pulled:"), (3, "Alerts:"),
                   (4, "Stale warnings:"), (6, "Macro:")):
        ws.cell(r, 8, lab).font = NAVY_BOLD
    hdr = 8
    for c, name in enumerate(DASH_COLS, start=1):
        cell = ws.cell(hdr, c, name)
        cell.font = WHITE_BOLD
        cell.fill = HDR_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = BORDER
    rows = sorted([s for s in specs if s.dashboard_capable and not s.is_dead
                   and s.lane == lane],
                  key=lambda s: (s.category, s.series_id))
    r = hdr + 1
    for s in rows:
        b = blocks[s.series_id]
        ppy = R.periods_per_year(s.frequency)
        latest = _ref(b, 0)
        prior = _ref(b, 1)
        yago = _ref(b, ppy)
        win = f"{b.tab}!{get_column_letter(R.RAW_VALUE_COL)}{b.first_data_row}:" \
              f"{get_column_letter(R.RAW_VALUE_COL)}{b.first_data_row + 7}"
        ws.cell(r, 1, _tier(s.series_id))
        ws.cell(r, 2, s.category)
        ws.cell(r, 3, s.series_id)
        ws.cell(r, 4, s.title)
        ws.cell(r, 5, f"=IFERROR({latest},\"\")")
        ws.cell(r, 6, f"=IFERROR({prior},\"\")")
        ws.cell(r, 7, f"=IFERROR(({latest}-{yago})/{yago}*100,\"\")")
        ws.cell(r, 8, f"=IFERROR(({latest}-AVERAGE({win}))/STDEV({win}),\"\")")
        zc, lc = f"${COL['Z-score (8)']}{r}", f"${COL['Latest']}{r}"
        if s.alert_rule == "zscore":
            flag = f"=IF(AND(ISNUMBER({zc}),{zc}>=zscore_band),\"⚠ ALERT\",\"\")"
        elif s.alert_rule == "sloos_level":
            flag = f"=IF(AND(ISNUMBER({lc}),{lc}>=sloos_band),\"⚠ TIGHTENING\",\"\")"
        else:
            flag = ""
        ws.cell(r, 9, flag)
        for c in range(1, len(DASH_COLS) + 1):
            ws.cell(r, c).border = BORDER
        ws.cell(r, 7).number_format = "0.0"
        ws.cell(r, 8).number_format = "0.00"
        ws.cell(r, 5).number_format = "0.00"
        ws.cell(r, 6).number_format = "0.00"
        r += 1
    last = r - 1
    _dash_widths(ws)
    ws.freeze_panes = ws.cell(hdr + 1, 1)
    # heat: z-score color scale + flag highlight
    if last >= hdr + 1:
        zc = COL["Z-score (8)"]
        fc = COL["Flag"]
        ws.conditional_formatting.add(
            f"{zc}{hdr+1}:{zc}{last}",
            ColorScaleRule(start_type="num", start_value=-2, start_color="63BE7B",
                           mid_type="num", mid_value=0, mid_color="FFEB84",
                           end_type="num", end_value=2, end_color="F8696B"))
        ws.conditional_formatting.add(
            f"{fc}{hdr+1}:{fc}{last}",
            FormulaRule(formula=[f'ISNUMBER(SEARCH("ALERT",{fc}{hdr+1}))'],
                        fill=ALERT_FILL, font=Font(bold=True, color=ALERT_RED)))
        ws.conditional_formatting.add(
            f"{fc}{hdr+1}:{fc}{last}",
            FormulaRule(formula=[f'ISNUMBER(SEARCH("TIGHTENING",{fc}{hdr+1}))'],
                        fill=TIGHTEN_FILL, font=Font(bold=True)))
    return ws


def _dash_widths(ws):
    widths = {"A": 12, "B": 16, "C": 16, "D": 52, "E": 10, "F": 10, "G": 9,
              "H": 12, "I": 14}
    for k, v in widths.items():
        ws.column_dimensions[k].width = v


# ==========================================================================
# Watchlist_Geo -- ranked, validator-gated, geographic only
# ==========================================================================
BOUNDARY = ("Geographic stress watchlist -- apply against portfolio collateral "
            "location manually. National credit-quality series are excluded by "
            "design; they cannot localize a portfolio subset.")

WL_COLS = ["Geography", "Series ID", "Source", "Latest", "YoY %", "Rank", "Trend (recent->older)"]


def _geo_label(spec):
    title = spec.title
    if " -- " in title:
        return title.split(" -- ", 1)[1]
    return spec.geo_segment


def _source(category):
    return {"hpi_state": "FHFA state", "hpi_metro": "FHFA metro (CBSA)",
            "hpi_caseshiller": "Case-Shiller metro"}.get(category, category)


def write_watchlist(wb, specs, blocks):
    # The hard gate, enforced again at build time.
    R.validate_watchlist(specs)
    wl = sorted(R.watchlist_series(specs), key=lambda s: (s.category, _geo_label(s)))

    ws = wb.create_sheet("Watchlist_Geo")
    ws.sheet_view.showGridLines = False
    ws["A1"] = "Watchlist_Geo -- Geographic Stress Watchlist"
    ws["A1"].font = Font(bold=True, size=16, color=NAVY)
    ws.merge_cells("A2:G2")
    ws["A2"] = BOUNDARY
    ws["A2"].font = Font(bold=True, color=ALERT_RED)
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[2].height = 42

    hdr = 4
    for c, name in enumerate(WL_COLS, start=1):
        cell = ws.cell(hdr, c, name)
        cell.font = WHITE_BOLD
        cell.fill = HDR_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = BORDER
    first = hdr + 1
    last = hdr + len(wl)
    yoy_col = get_column_letter(5)
    yoy_range = f"${yoy_col}${first}:${yoy_col}${last}"
    r = first
    for s in wl:
        b = blocks[s.series_id]
        ppy = R.periods_per_year(s.frequency)
        latest = _ref(b, 0)
        yago = _ref(b, ppy)
        v0, v1, v2, v3 = _ref(b, 0), _ref(b, 1), _ref(b, 2), _ref(b, 3)
        ws.cell(r, 1, _geo_label(s))
        ws.cell(r, 2, s.series_id)
        ws.cell(r, 3, _source(s.category))
        ws.cell(r, 4, f"=IFERROR({latest},\"\")")
        ws.cell(r, 5, f"=IFERROR(({latest}-{yago})/{yago}*100,\"\")")
        ws.cell(r, 6, f"=IFERROR(RANK({yoy_col}{r},{yoy_range},1),\"\")")
        arrow = (f"=IFERROR(IF({v0}>{v1},\"▲\",IF({v0}<{v1},\"▼\",\"→\"))"
                 f"&IF({v1}>{v2},\"▲\",IF({v1}<{v2},\"▼\",\"→\"))"
                 f"&IF({v2}>{v3},\"▲\",IF({v2}<{v3},\"▼\",\"→\")),\"\")")
        ws.cell(r, 7, arrow)
        ws.cell(r, 5).number_format = "0.0"
        ws.cell(r, 4).number_format = "0.0"
        for c in range(1, len(WL_COLS) + 1):
            ws.cell(r, c).border = BORDER
        r += 1
    widths = {"A": 40, "B": 16, "C": 18, "D": 10, "E": 9, "F": 8, "G": 16}
    for k, v in widths.items():
        ws.column_dimensions[k].width = v
    ws.freeze_panes = ws.cell(first, 1)
    if last >= first:
        # red = most negative YoY (deterioration), green = appreciation
        ws.conditional_formatting.add(
            f"{yoy_col}{first}:{yoy_col}{last}",
            ColorScaleRule(start_type="num", start_value=-10, start_color="F8696B",
                           mid_type="num", mid_value=0, mid_color="FFFFFF",
                           end_type="num", end_value=10, end_color="63BE7B"))
        rank_col = get_column_letter(6)
        ws.conditional_formatting.add(
            f"{rank_col}{first}:{rank_col}{last}",
            ColorScaleRule(start_type="min", start_color="F8696B",
                           end_type="max", end_color="63BE7B"))
    return ws


# ==========================================================================
# Code-in-tab + readme
# ==========================================================================
def write_code_tab(wb, tab, source_path, language):
    ws = wb.create_sheet(tab)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 120
    with open(source_path, "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]                      # drop trailing newline artifact
    for i, line in enumerate(lines, start=1):
        text_cell(ws, i, 1, line)
        ws.cell(i, 1).font = Font(name="Consolas", size=9)
    return len(lines)


README = """\
FRED CREDIT-RISK DASHBOARD -- README
====================================

WHAT THIS IS
  A self-contained, reusable template. One workbook pulls credit-risk data from
  FRED (Federal Reserve Economic Data), lands it raw, and presents it as
  formula-driven dashboards plus a geographic stress watchlist for commercial
  loan-portfolio targeting. All code, config and docs live inside this workbook,
  so it can be emailed, opened on another machine, and re-run with one click.

ONE-TIME SETUP
  1. Install Python 3 (add it to PATH) and the dependencies:
         pip install fredapi xlwings openpyxl pandas
  2. Get a free FRED API key: https://fredaccount.stlouisfed.org/apikeys
  3. Provide the key ONE of two ways (never hardcoded in code):
       - set an environment variable  FRED_API_KEY=your_key   (preferred), or
       - paste it into the _config tab: [SETTINGS] -> fred_api_key cell.
  4. Enable macros when prompted (the button needs them).

RUN IT
  Click "Extract & Run" on Dashboard_Consumer. The macro:
    - writes the runner from the _code_py tab to runner.py next to this file,
    - shells Python to pull FRED per _config and fill the Raw_* tabs,
    - the dashboards recalc from formulas; status shows in the top-right cells.
  No key yet? Set _config [SETTINGS] demo_mode = TRUE to populate the workbook
  with offline synthetic data and see the machinery work end-to-end.

WHY xlwings (the write path)
  xlwings lets Python write into the already-open workbook, so the button is a
  true one-click on the work machine. openpyxl is kept as an isolated fallback
  (writes the closed file) for headless/no-Excel use. Either is selected by
  _config [SETTINGS] write_backend = auto|xlwings|openpyxl.

THE TABS
  Dashboard_Consumer / _Commercial / _Price  -- formula-driven panels: latest,
      trailing trend, YoY, an 8-period z-score, and a Flag column. Heat shading
      marks stress. Bank-tier rows (All / Top 100 / Not top 100) sit together.
  Watchlist_Geo  -- the commercial sample-targeting output: states & metros
      ranked by house-price deterioration (YoY). Join these geographies to your
      book's collateral locations manually.
  Raw_Consumer / _Commercial / _Price  -- raw observations, newest-first, one
      block per series. Python writes here; the dashboards read these by formula
      so you can re-render without re-pulling.
  _config  -- THE KNOB PANEL. The series dictionary, the threshold bands, the
      API-key fallback cell, and the metro-extension list. Edit here to add or
      remove series or change thresholds -- no code change needed.
  _code_py / _code_vba  -- the complete runner and macro as plain text (one
      source line per cell). The button rebuilds runner.py from _code_py, so the
      workbook -- not the repo -- is the source of truth.

THE WATCHLIST BOUNDARY (why some series can't reach the watchlist)
  Only house-price indices that carry a geographic key a loan portfolio can join
  on (FHFA state/metro, Case-Shiller metros) may feed Watchlist_Geo. Charge-off,
  delinquency, G.19, debt-service, SLOOS and CRE-price series are NATIONAL
  aggregates -- they describe the whole country and cannot point at a subset of
  your loans. The runner refuses (with an error naming the series) if _config
  ever marks a non-geographic series watchlist_capable. Presenting a national
  trend as if it could localize a portfolio is the failure this gate prevents.

ADD / REMOVE SERIES
  Edit the [SERIES] table in _config. Each row is pulled per its series_id and
  routed by its lane (consumer|commercial|price). To make a series eligible for
  the watchlist it must be a geographically-keyed house-price index: lane=price,
  category=hpi_state|hpi_metro|hpi_caseshiller, a real geo_segment, and
  watchlist_capable=TRUE. Anything else marked watchlist_capable is rejected.

KNOWN DATA TRAPS (handled, but know they exist)
  - FRED returns "." for missing -- coerced to blank/NaN, never 0.
  - Quarterly series are not force-aligned to a monthly grid.
  - Methodology breaks: debt-service ratios moved to a credit-bureau method in
    2024:Q2; G.19 dropped the nonfinancial-business sector in the May 2025
    release; FODSP was discontinued after 2023:Q3 (kept as documented-dead, not
    pulled live). These are noted in _config so alerts don't misread a step.
  - Several bank-tier delinquency series lag; the stale-check logs them.
  - Case-Shiller data is copyrighted: internal monitoring only, not for
    redistribution.

NO AI IS INVOLVED IN THE DATA PATH. Thresholds, transforms and rankings are
deterministic and config-driven: the same FRED data always yields the same
workbook.
"""


def write_readme(wb):
    ws = wb.create_sheet("_readme")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 100
    for i, line in enumerate(README.split("\n"), start=1):
        text_cell(ws, i, 1, line)
        if line and not line.startswith(" ") and line == line.upper() and len(line) > 3 \
                and not line.startswith("="):
            ws.cell(i, 1).font = NAVY_BOLD
    return ws


# ==========================================================================
# Orchestration
# ==========================================================================
def build(out_path):
    rows = config_rows()
    cfg = R.parse_config(rows)
    specs = cfg.series
    # Hard gates at build time (BUILD SPEC sec 0.1, sec 3).
    R.validate_watchlist(specs)
    R.validate_transforms(specs)
    blocks = R.raw_layout(specs, slots=cfg.raw_slots)

    wb = Workbook()
    wb.remove(wb.active)                          # drop default sheet

    # presentation tabs first (nice tab order), then raw, then system
    write_raw_scaffold(wb, specs, blocks)         # creates Raw_* (needed by formulas)
    write_dashboard(wb, "Dashboard_Consumer", specs, blocks,
                    "Consumer Credit-Risk Dashboard",
                    "Charge-offs, delinquencies, G.19, debt-service, SLOOS -- national (bank-tier where available).",
                    lane="consumer")
    write_dashboard(wb, "Dashboard_Commercial", specs, blocks,
                    "Commercial Credit-Risk Dashboard",
                    "C&I, CRE, all-loans charge-offs/delinquencies + SLOOS diffusion -- national.",
                    lane="commercial")
    write_dashboard(wb, "Dashboard_Price", specs, blocks,
                    "Price Dashboard",
                    "National house-price indices + commercial-real-estate price context.",
                    lane="price")
    write_watchlist(wb, specs, blocks)
    write_config(wb)
    write_code_tab(wb, "_code_py", os.path.join(HERE, "runner.py"), "python")
    write_code_tab(wb, "_code_vba", os.path.join(HERE, "macro.bas"), "vba")
    write_readme(wb)

    # tab order
    order = ["Dashboard_Consumer", "Dashboard_Commercial", "Dashboard_Price",
             "Watchlist_Geo", "Raw_Consumer", "Raw_Commercial", "Raw_Price",
             "_config", "_code_py", "_code_vba", "_readme"]
    wb._sheets.sort(key=lambda s: order.index(s.title) if s.title in order else 99)
    wb.active = wb.sheetnames.index("Dashboard_Consumer")
    wb.save(out_path)
    return out_path, len(specs), len(R.watchlist_series(specs))


if __name__ == "__main__":
    out = os.path.join(HERE, "build", "FRED_Credit_Risk_Dashboard_base.xlsx")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    path, n, nwl = build(out)
    print(f"built {path}: {n} series, {nwl} watchlist-capable")
