"""The workbook: the count cube, the formulas over it, and the check tab.

Every rate, interval, gap, multiple and word on a results tab is an Excel
formula over `_cube`, driven by the named knobs on `_config`. Beside each
formula cell, `_check` carries the value Python computed for it (`ladder.py`)
and a formula asking Excel whether the two agree, so the cover can print
"N of N formula checks agree" with no engine at the desk.

Newer Excel functions are written with the `_xlfn.` prefix: bare
`NORM.S.INV` and `BETA.INV` render `#NAME?` (LibreOffice 24.2, tested
18 Sep 2026; openpyxl 3.1.5 lists neither).

Determinism (PRD §6.13): `workbook_bytes` re-packs the saved zip with fixed
member timestamps and pins the document's created/modified stamps to the
run date, so the same inputs give the same bytes.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.data_source import NumDataSource, NumRef
from openpyxl.chart.error_bar import ErrorBars
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from . import __version__, keybank_style as ks, ladder, notes
from .config import Config
from .ingest import Table
from .population import Population

TOL_COUNT = 0.0
TOL_RATE = 1e-9          # relative, applied as absolute on values <= 1 and on ratios
TOL_INTERVAL = 1e-6      # absolute: BETA.INV differs a little between engines
TOL_POINTS = 1e-6        # percentage points

METHODS = ("Wilson", "Clopper-Pearson")
BOLD = Font(name="Calibri", size=11, bold=True, color=ks.INK_TEXT)   # composed from the style tokens

# The interval formulas, term for term the same as stats.py. N and X are cell
# addresses; the knobs are the named cells on _config.
WILSON_LO = "(({X}/{N})+Z^2/(2*{N}))/(1+Z^2/{N})-Z/(1+Z^2/{N})*SQRT(({X}/{N})*(1-{X}/{N})/{N}+Z^2/(4*{N}^2))"
WILSON_HI = "(({X}/{N})+Z^2/(2*{N}))/(1+Z^2/{N})+Z/(1+Z^2/{N})*SQRT(({X}/{N})*(1-{X}/{N})/{N}+Z^2/(4*{N}^2))"
CP_LO = "IF({X}=0,0,_xlfn.BETA.INV((1-CONF)/2,{X},{N}-{X}+1))"
CP_HI = "IF({X}={N},1,_xlfn.BETA.INV(1-(1-CONF)/2,{X}+1,{N}-{X}))"


def interval_formula(side: str, n: str, x: str) -> str:
    w = (WILSON_LO if side == "lo" else WILSON_HI).format(N=n, X=x)
    c = (CP_LO if side == "lo" else CP_HI).format(N=n, X=x)
    return f'=IF({n}=0,"",IF(METHOD="Wilson",{w},{c}))'


@dataclass
class Check:
    sheet: str
    cell: str
    formula: str
    python: object
    tol: float
    kind: str      # "number" | "text"


@dataclass
class Build:
    wb: Workbook
    checks: list[Check] = field(default_factory=list)

    def formula(self, ws, cell: str, text: str, python, tol: float = TOL_RATE, kind: str = "number", fmt: str | None = None):
        ws[cell] = text
        if fmt:
            ws[cell].number_format = fmt
        self.checks.append(Check(ws.title, cell, text, python, tol, kind))


def _error_bars(sheet: str, plus_rng: str, minus_rng: str) -> ErrorBars:
    """Custom error bars read from the interval helper cells, so the picture
    and the table cannot disagree: both come from the same formulas."""
    return ErrorBars(errDir="y", errBarType="both", errValType="cust",
                     plus=NumDataSource(numRef=NumRef(f=f"'{sheet}'!{plus_rng}")),
                     minus=NumDataSource(numRef=NumRef(f=f"'{sheet}'!{minus_rng}")))


def _rate_chart(ws, title: str, y_title: str, cats: Reference, series: list[tuple[Reference, str, str]],
                anchor: str, width: float = 14.0, height: float = 6.5) -> None:
    """A column chart of rates with interval bars. `series` is a list of
    (values reference incl. header, plus range, minus range)."""
    ch = BarChart()
    ch.type = "col"
    ch.title = title
    ch.y_axis.title = y_title
    ch.y_axis.number_format = "0.0%"
    ch.y_axis.majorGridlines = None
    ch.x_axis.title = None
    if len(series) > 1:
        ch.legend.position = "b"
    else:
        ch.legend = None
    for values, plus_rng, minus_rng in series:
        ch.add_data(values, titles_from_data=True)
        ch.series[-1].errBars = _error_bars(ws.title, plus_rng, minus_rng)
    ch.set_categories(cats)
    ch.width = width
    ch.height = height
    ws.add_chart(ch, anchor)


def _note(ws, row: int, text: str, ncols: int) -> int:
    last = get_column_letter(ncols)
    ws.merge_cells(f"A{row}:{last}{row}")
    c = ws.cell(row, 1, text)
    c.font = ks.SECONDARY
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[row].height = max(30, 15 * (1 + len(text) // 110))
    return row + 1


def _header_band(ws, ncols: int, title: str, cfg: Config, table: Table, facts: ladder.Facts, run_date: date,
                 n_outcomes: int = 1) -> int:
    # with several outcomes there is no single event count: each block states
    # its own (adversarial finding 7, 19 Sep 2026)
    events = f"{facts.events:,} events" if n_outcomes == 1 else "events per outcome in each block"
    row = ks.brand_banner(ws, 1, ncols, title,
                          f"{cfg.name} · source {table.path.split('/')[-1]} · sha256 {table.sha256[:16]}… · "
                          f"{facts.seasoned:,} seasoned loans · {events} · "
                          f"generator {__version__} · run {run_date.isoformat()}")
    return row


def _rule_sentence(cfg: Config) -> str:
    return notes.pick("cover.rule", cfg.rule.kind, field_a=cfg.rule.field_a, field_b=cfg.rule.field_b,
                      fires_op=cfg.rule.fires_op, fires_value=cfg.rule.fires_value)


def _fires_text(cfg: Config) -> str:
    return notes.fill("labels.fires", field_a=cfg.rule.field_a, field_b=cfg.rule.field_b,
                      kind_word=notes.pick("labels.kind_word", cfg.rule.kind),
                      fires_op=cfg.rule.fires_op, fires_value=cfg.rule.fires_value)


def build_workbook(cfg: Config, pop: Population, table: Table, run_date: date) -> tuple[Workbook, ladder.PackData, list[Check]]:
    data = ladder.run(cfg, pop)
    b = Build(Workbook())
    wb = b.wb
    cover = wb.active
    cover.title = "Cover"
    cap = wb.create_sheet("1_Capture")
    prev = wb.create_sheet("2_Prevalence")
    grad = wb.create_sheet("3_Gradient")
    strat = wb.create_sheet("4_Stratified")
    decomp = wb.create_sheet("5_Decomposition")
    mdl = wb.create_sheet("6_Model")
    ctrl = wb.create_sheet("7_Control") if data.control is not None else None
    cube = wb.create_sheet("_cube")
    conf = wb.create_sheet("_config")
    meth = wb.create_sheet("_method")
    check = wb.create_sheet("_check")
    prov = wb.create_sheet("_provenance")
    for ws in (cover, cap, prev, grad, strat, decomp, mdl, cube, conf, meth, check, prov) + ((ctrl,) if ctrl else ()):
        ks.hide_gridlines(ws)
        # print (and render) one page wide, as many pages tall as needed, so a
        # chart sits beside its table rather than on a page of its own
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.page_setup.orientation = "landscape"
    first_facts = data.per_outcome[0][0]
    n_out = len(data.per_outcome)
    facts_by = {g.outcome.key: f for f, g in data.per_outcome}
    snapshot = cfg.outcome.form == "snapshot"
    m_ = cfg.outcome.measure or {}
    measure_fields = m_["field"] if "field" in m_ else f"{m_.get('field_a')}, {m_.get('field_b')}"

    # -- _config: the knobs, as named cells ------------------------------
    conf.column_dimensions["A"].width = 34
    conf.column_dimensions["B"].width = 10
    conf.column_dimensions["C"].width = 22
    conf.column_dimensions["D"].width = 70
    row = ks.section_band(conf, 1, "Live knobs — change these and the workbook recalculates", 4)
    conf.cell(row, 1, "Confidence level"); conf.cell(row, 3, cfg.confidence).number_format = "0.00%"
    conf.cell(row, 4, "The interval width every rate carries. 0.95 means a 95% interval.")
    wb.defined_names["CONF"] = DefinedName("CONF", attr_text=f"_config!$C${row}")
    row += 1
    conf.cell(row, 1, "Interval method"); conf.cell(row, 3, cfg.method)
    conf.cell(row, 4, "Wilson (default) or Clopper-Pearson. Pick from the list.")
    dv = DataValidation(type="list", formula1='"Wilson,Clopper-Pearson"', allow_blank=False)
    conf.add_data_validation(dv); dv.add(f"C{row}")
    wb.defined_names["METHOD"] = DefinedName("METHOD", attr_text=f"_config!$C${row}")
    row += 1
    conf.cell(row, 1, "Survives threshold"); conf.cell(row, 3, cfg.survives_threshold).number_format = "0.00"
    conf.cell(row, 4, "Step 4 (not in this version): the share of the crude effect that must remain for 'survives'.")
    wb.defined_names["SURV_T"] = DefinedName("SURV_T", attr_text=f"_config!$C${row}")
    row += 1
    conf.cell(row, 1, "z for the confidence level")
    z_cell = f"C{row}"
    b.formula(conf, z_cell, "=_xlfn.NORM.S.INV(1-(1-CONF)/2)", ladder.stats.z_for_confidence(cfg.confidence), TOL_INTERVAL, fmt="0.000000")
    conf.cell(row, 4, "Derived from the confidence level; not a knob.")
    wb.defined_names["Z"] = DefinedName("Z", attr_text=f"_config!$C${row}")
    row += 2
    row = ks.section_band(conf, row, "Rebuild knobs — shown for the record; change the question file and build again", 4)
    outcome_text = f"{cfg.outcome.label} ({cfg.outcome.form}" + (
        f", at edges {', '.join(f'{e:g}' for e in cfg.outcome.edges)})" if cfg.outcome.edges else ")")
    for label, value in (("Question file", cfg.name), ("Rule", _fires_text(cfg)),
                         ("Bucket edges", ", ".join(f"{e:g}" for e in cfg.rule.buckets)),
                         ("Outcome", outcome_text),
                         ("Window (months)", cfg.window_months),
                         ("Filter", ", ".join(f"{k} in {list(v)}" for k, v in cfg.filter.items()) or "none"),
                         ("As-of date", pop.asof.isoformat())):
        conf.cell(row, 1, label); conf.cell(row, 3, value); row += 1
    row += 1
    _note(conf, row, notes.fill("notes.config"), 4)

    # -- _cube -----------------------------------------------------------
    cube.column_dimensions["A"].width = 22; cube.column_dimensions["B"].width = 26
    ks.header_row(cube, 1, ["block", "label", "loans", "events"], right_from=2)
    crow = 2
    addr: dict[str, tuple[str, str]] = {}   # block -> (loans cell, events cell) on _cube
    def put_cube(r: ladder.CubeRow):
        nonlocal crow
        cube.cell(crow, 1, r.block); cube.cell(crow, 2, r.label)
        cube.cell(crow, 3, r.n); cube.cell(crow, 4, r.events)
        addr[r.block] = (f"_cube!$C${crow}", f"_cube!$D${crow}")
        crow += 1
    for cr in data.capture:
        put_cube(ladder.CubeRow(f"s1.{cr.quarter}.loans", f"{cr.quarter} loans", cr.loans, 0))
        put_cube(ladder.CubeRow(f"s1.{cr.quarter}.unseasoned", f"{cr.quarter} unseasoned", cr.unseasoned, 0))
        put_cube(ladder.CubeRow(f"s1.{cr.quarter}.a_blank", f"{cr.quarter} {cfg.rule.field_a} blank", cr.a_blank, 0))
        put_cube(ladder.CubeRow(f"s1.{cr.quarter}.b_blank", f"{cr.quarter} {cfg.rule.field_b} blank", cr.b_blank, 0))
        put_cube(ladder.CubeRow(f"s1.{cr.quarter}.both", f"{cr.quarter} both present", cr.both, 0))
        if snapshot:
            put_cube(ladder.CubeRow(f"s1.{cr.quarter}.measure_blank", f"{cr.quarter} measure blank ({measure_fields})", cr.measure_blank, 0))
    for bc in data.band_counts:
        for i, (lab, n) in enumerate(zip(bc.labels, bc.counts)):
            put_cube(ladder.CubeRow(f"s1.band.{bc.confounder}.{bc.scheme}.{i}", f"{bc.confounder} {bc.scheme} {lab}", n, 0))
        put_cube(ladder.CubeRow(f"s1.band.{bc.confounder}.{bc.scheme}.blank", f"{bc.confounder} {bc.scheme} (blank)", bc.blank, 0))
    for pr in data.prevalence:
        put_cube(pr.capture)
        put_cube(pr.flag)
    for facts, g in data.per_outcome:
        for gr in g.rows:
            put_cube(gr.cube)
        put_cube(g.base.cube)
    for st in data.strata:
        for band in st.bands:
            put_cube(band.flagged)
            put_cube(band.unflagged)
            for gr in band.buckets:
                put_cube(gr.cube)
    for dc in data.decompositions:
        for r_ in dc.rows:
            put_cube(r_.flagged)
            put_cube(r_.unflagged)
    if data.control is not None:
        put_cube(data.control.both)
    if data.bands:
        for i, (lab, counts) in enumerate(data.bands.rows):
            for j, c in enumerate(counts):
                put_cube(ladder.CubeRow(f"s3.bands.bucket{i}.band{j}", f"{lab} | {data.bands.band_labels[j]}", c, 0))
    for q, n in data.unseasoned_by_quarter.items():
        put_cube(ladder.CubeRow(f"unseasoned.{q}", q, n, 0))

    # -- 1_Capture -------------------------------------------------------------
    ncols = 11 if snapshot else 9
    for col, wdt in zip("ABCDEFGHIJK", (22, 16, 12, 16, 9, 16, 9, 14, 9, 24, 9)):
        cap.column_dimensions[col].width = wdt
    row = _header_band(cap, ncols, "Step 1 — Capture", cfg, table, first_facts, run_date, n_out)
    cap_note = notes.fill("notes.capture", window_months=cfg.window_months, field_a=cfg.rule.field_a,
                          field_b=cfg.rule.field_b)
    row = _note(cap, row, cap_note, ncols)
    row += 1
    hdr = row
    ks.header_row(cap, hdr, ["Quarter", "Loans", "Unseasoned", f"{cfg.rule.field_a} blank", "share",
                             f"{cfg.rule.field_b} blank", "share", "Both present", "share"]
                  + ([f"measure blank ({measure_fields})", "share"] if snapshot else []), right_from=1)
    for i, cr in enumerate(data.capture):
        r = hdr + 1 + i
        cap.cell(r, 1, cr.quarter)
        b.formula(cap, f"B{r}", f"={addr[f's1.{cr.quarter}.loans'][0]}", cr.loans, TOL_COUNT, fmt="#,##0")
        b.formula(cap, f"C{r}", f"={addr[f's1.{cr.quarter}.unseasoned'][0]}", cr.unseasoned, TOL_COUNT, fmt="#,##0")
        b.formula(cap, f"D{r}", f"={addr[f's1.{cr.quarter}.a_blank'][0]}", cr.a_blank, TOL_COUNT, fmt="#,##0")
        b.formula(cap, f"E{r}", f'=IF(B{r}=0,"",D{r}/B{r})', cr.a_blank_share, fmt="0.0%")
        b.formula(cap, f"F{r}", f"={addr[f's1.{cr.quarter}.b_blank'][0]}", cr.b_blank, TOL_COUNT, fmt="#,##0")
        b.formula(cap, f"G{r}", f'=IF(B{r}=0,"",F{r}/B{r})', cr.b_blank_share, fmt="0.0%")
        b.formula(cap, f"H{r}", f"={addr[f's1.{cr.quarter}.both'][0]}", cr.both, TOL_COUNT, fmt="#,##0")
        b.formula(cap, f"I{r}", f'=IF(B{r}=0,"",H{r}/B{r})', cr.both_share, fmt="0.0%")
        if snapshot:
            # a blank measure is a non-event that is counted, never silent (adversarial finding 5)
            b.formula(cap, f"J{r}", f"={addr[f's1.{cr.quarter}.measure_blank'][0]}", cr.measure_blank, TOL_COUNT, fmt="#,##0")
            b.formula(cap, f"K{r}", f'=IF(B{r}=0,"",J{r}/B{r})', cr.measure_blank_share, fmt="0.0%")
    ks.freeze_below(cap, hdr)
    row = hdr + 1 + len(data.capture) + 1
    if data.band_counts:
        row = ks.section_band(cap, row, "Bands by scheme (seasoned loans)", ncols)
        row = _note(cap, row, notes.fill("notes.capture_bands"), ncols)
        for bc in data.band_counts:
            cap.cell(row, 1, f"{bc.confounder} · {bc.scheme}").font = BOLD
            row += 1
            ks.header_row(cap, row, ["Band", "Seasoned loans"], right_from=1)
            row += 1
            for i, lab in enumerate(bc.labels):
                cap.cell(row, 1, lab)
                b.formula(cap, f"B{row}", f"={addr[f's1.band.{bc.confounder}.{bc.scheme}.{i}'][0]}", bc.counts[i], TOL_COUNT, fmt="#,##0")
                row += 1
            cap.cell(row, 1, "(blank)")
            b.formula(cap, f"B{row}", f"={addr[f's1.band.{bc.confounder}.{bc.scheme}.blank'][0]}", bc.blank, TOL_COUNT, fmt="#,##0")
            row += 2

    # -- 2_Prevalence ------------------------------------------------------------
    ncols = 10
    for col, wdt in zip("ABCDEFGHIJ", (10, 14, 12, 12, 9, 9, 10, 10, 9, 9)):
        prev.column_dimensions[col].width = wdt
    row = _header_band(prev, ncols, "Step 2 — Prevalence", cfg, table, first_facts, run_date, n_out)
    quarters = [pr.quarter for pr in data.prevalence]
    prev_note = notes.fill("notes.prevalence", field_a=cfg.rule.field_a, field_b=cfg.rule.field_b,
                           fires_text=_fires_text(cfg), confidence=cfg.confidence, method=cfg.method,
                           first_quarter=quarters[0] if quarters else "—", last_quarter=quarters[-1] if quarters else "—")
    row = _note(prev, row, prev_note, ncols)
    row += 1
    hdr = row
    ks.header_row(prev, hdr, ["Quarter", "Seasoned loans", "Both present", "Capture rate", "Lower", "Upper",
                              "Flagged", "Flag rate", "Lower", "Upper"], right_from=1)
    for i, pr in enumerate(data.prevalence):
        r = hdr + 1 + i
        cn, cx = addr[pr.capture.block]
        fn, fx = addr[pr.flag.block]
        prev.cell(r, 1, pr.quarter)
        b.formula(prev, f"B{r}", f"={cn}", pr.capture.n, TOL_COUNT, fmt="#,##0")
        b.formula(prev, f"C{r}", f"={cx}", pr.capture.events, TOL_COUNT, fmt="#,##0")
        b.formula(prev, f"D{r}", f'=IF(B{r}=0,"",C{r}/B{r})', pr.capture_rate, fmt="0.0%")
        b.formula(prev, f"E{r}", interval_formula("lo", f"B{r}", f"C{r}"), pr.capture_lo, TOL_INTERVAL, fmt="0.0%")
        b.formula(prev, f"F{r}", interval_formula("hi", f"B{r}", f"C{r}"), pr.capture_hi, TOL_INTERVAL, fmt="0.0%")
        b.formula(prev, f"G{r}", f"={fx}", pr.flag.events, TOL_COUNT, fmt="#,##0")
        b.formula(prev, f"H{r}", f'=IF({fn}=0,"",G{r}/{fn})', pr.flag_rate, fmt="0.0%")
        b.formula(prev, f"I{r}", interval_formula("lo", fn, f"G{r}"), pr.flag_lo, TOL_INTERVAL, fmt="0.0%")
        b.formula(prev, f"J{r}", interval_formula("hi", fn, f"G{r}"), pr.flag_hi, TOL_INTERVAL, fmt="0.0%")
    ks.freeze_below(prev, hdr)

    # -- 3_Gradient: one block per outcome ------------------------------------
    ncols = 10
    for col, w in zip("ABCDEFGHIJKL", (26, 10, 10, 10, 10, 10, 11, 10, 14, 14, 9, 9)):
        grad.column_dimensions[col].width = w
    for col in "MNO":
        grad.column_dimensions[col].width = 11
    row = _header_band(grad, ncols, "Step 3 — Gradient", cfg, table, first_facts, run_date, n_out)
    grad_note = notes.fill("notes.gradient", rule_text=_rule_sentence(cfg),
                           with_both=data.per_outcome[0][1].with_both,
                           blank_either=data.per_outcome[0][1].blank_either,
                           edges=", ".join(f"{e:g}" for e in cfg.rule.buckets),
                           base_n=data.per_outcome[0][1].base.cube.n, fires_text=_fires_text(cfg),
                           confidence=cfg.confidence, method=cfg.method)
    row = _note(grad, row, grad_note, ncols)
    row += 1
    word_cells: list[tuple[ladder.Gradient, str]] = []
    first_hdr = None
    for facts, g in data.per_outcome:
        row = ks.section_band(grad, row, f"Outcome: {g.outcome.label} — {facts.events:,} events among {facts.seasoned:,} seasoned loans", ncols)
        hdr = row
        first_hdr = first_hdr or hdr
        ks.header_row(grad, hdr, ["Bucket", "Loans", "Events", "Rate", "Lower", "Upper", "Gap (pts)", "Multiple",
                                  "Rate change vs nearest bucket above with loans", "Interval clear of that bucket",
                                  "Bar up", "Bar down", "Last rate seen", "Last lower", "Last upper"], right_from=1)
        first = hdr + 1
        base_row = first + len(g.rows)
        n_base, x_base = addr[g.base.cube.block]
        seen: tuple = (None, None, None)     # rate, lower, upper of the last bucket with loans
        for i, gr in enumerate(g.rows):
            r = first + i
            n, x = addr[gr.cube.block]
            grad.cell(r, 1, gr.cube.label)
            b.formula(grad, f"B{r}", f"={n}", gr.cube.n, TOL_COUNT, fmt="#,##0")
            b.formula(grad, f"C{r}", f"={x}", gr.cube.events, TOL_COUNT, fmt="#,##0")
            b.formula(grad, f"D{r}", f'=IF(B{r}=0,"",C{r}/B{r})', gr.rate, fmt="0.00%")
            b.formula(grad, f"E{r}", interval_formula("lo", f"B{r}", f"C{r}"), gr.lo, TOL_INTERVAL, fmt="0.00%")
            b.formula(grad, f"F{r}", interval_formula("hi", f"B{r}", f"C{r}"), gr.hi, TOL_INTERVAL, fmt="0.00%")
            b.formula(grad, f"G{r}", f'=IF(OR(D{r}="",D{base_row}=""),"",(D{r}-D{base_row})*100)', gr.gap_pts, TOL_POINTS, fmt="0.00")
            b.formula(grad, f"H{r}", f'=IF(OR(D{r}="",D{base_row}=""),"",IF(D{base_row}=0,"",D{r}/D{base_row}))', gr.multiple, fmt="0.00")
            # M–O: the last rate, lower and upper seen at or above this row, so a
            # bucket with no loans does not break the chain (adversarial finding
            # 1, 19 Sep 2026); twinned like every other formula
            if gr.rate is not None:
                seen = (gr.rate, gr.lo, gr.hi)
            if i == 0:
                b.formula(grad, f"M{r}", f'=IF(D{r}="","",D{r})', seen[0], fmt="0.0000")
                b.formula(grad, f"N{r}", f'=IF(E{r}="","",E{r})', seen[1], TOL_INTERVAL, fmt="0.0000")
                b.formula(grad, f"O{r}", f'=IF(F{r}="","",F{r})', seen[2], TOL_INTERVAL, fmt="0.0000")
            else:
                pr = r - 1
                b.formula(grad, f"M{r}", f'=IF(D{r}="",M{pr},D{r})', seen[0], fmt="0.0000")
                b.formula(grad, f"N{r}", f'=IF(E{r}="",N{pr},E{r})', seen[1], TOL_INTERVAL, fmt="0.0000")
                b.formula(grad, f"O{r}", f'=IF(F{r}="",O{pr},F{r})', seen[2], TOL_INTERVAL, fmt="0.0000")
                b.formula(grad, f"I{r}", f'=IF(OR(D{r}="",M{pr}=""),"",D{r}-M{pr})', g.diffs[i - 1], fmt="0.0000")
                b.formula(grad, f"J{r}", f'=IF(OR(E{r}="",O{pr}=""),0,IF(E{r}>O{pr},1,0)+IF(F{r}<N{pr},1,0))', g.nonoverlap[i - 1], TOL_COUNT)
        r = base_row
        grad.cell(r, 1, "Base: rule does not fire").font = BOLD
        b.formula(grad, f"B{r}", f"={n_base}", g.base.cube.n, TOL_COUNT, fmt="#,##0")
        b.formula(grad, f"C{r}", f"={x_base}", g.base.cube.events, TOL_COUNT, fmt="#,##0")
        b.formula(grad, f"D{r}", f'=IF(B{r}=0,"",C{r}/B{r})', g.base.rate, fmt="0.00%")
        b.formula(grad, f"E{r}", interval_formula("lo", f"B{r}", f"C{r}"), g.base.lo, TOL_INTERVAL, fmt="0.00%")
        b.formula(grad, f"F{r}", interval_formula("hi", f"B{r}", f"C{r}"), g.base.hi, TOL_INTERVAL, fmt="0.00%")
        # interval helpers behind the chart's error bars, twinned like every other formula
        for i, gr in enumerate(g.rows):
            r = first + i
            b.formula(grad, f"K{r}", f'=IF(F{r}="","",F{r}-D{r})',
                      (None if gr.hi is None else gr.hi - gr.rate), TOL_INTERVAL, fmt="0.0000")
            b.formula(grad, f"L{r}", f'=IF(E{r}="","",D{r}-E{r})',
                      (None if gr.lo is None else gr.rate - gr.lo), TOL_INTERVAL, fmt="0.0000")
        last_bucket = first + len(g.rows) - 1
        _rate_chart(grad, f"{g.outcome.label}: rate by bucket, with intervals", f"{g.outcome.label} rate",
                    Reference(grad, min_col=1, min_row=first, max_row=last_bucket),
                    [(Reference(grad, min_col=4, min_row=hdr, max_row=last_bucket),
                      f"$K${first}:$K${last_bucket}", f"$L${first}:$L${last_bucket}")],
                    anchor=f"Q{hdr}")
        row = base_row + 2
        i_rng = f"I{first + 1}:I{first + len(g.rows) - 1}"
        j_rng = f"J{first + 1}:J{first + len(g.rows) - 1}"
        grad.cell(row, 1, "Monotonic?").font = BOLD
        word_cell = f"B{row}"
        b.formula(grad, word_cell,
                  f'=IF(COUNT({i_rng})=0,"no data",IF(AND(COUNTIF({i_rng},"<0")=0,COUNTIF({i_rng},">0")=0),"flat",'
                  f'IF(COUNTIF({i_rng},"<0")=0,"monotonic increasing",'
                  f'IF(COUNTIF({i_rng},">0")=0,"monotonic decreasing","not monotonic"))))', g.word, 0.0, "text")
        grad.merge_cells(f"B{row}:E{row}")
        word_cells.append((g, word_cell))
        row += 1
        grad.cell(row, 1, "Adjacent pairs whose intervals do not overlap").font = BOLD
        grad.merge_cells(f"A{row}:D{row}")
        b.formula(grad, f"E{row}", f"=SUM({j_rng})", g.nonoverlap_count, TOL_COUNT)
        row = max(row + 2, hdr + 15)          # leave room for the chart beside the block
    if data.bands:
        bt = data.bands
        row = ks.section_band(grad, row, "Where the measure sits, by bucket", ncols)
        row = _note(grad, row, notes.fill("notes.bands_table"), ncols)
        hdr = row
        cols = ["Bucket"] + [f"{lab} (loans)" for lab in bt.band_labels] + [f"{lab} (share)" for lab in bt.band_labels]
        ks.header_row(grad, hdr, cols, right_from=1)
        k = len(bt.band_labels)
        for j in range(2 * k):
            grad.column_dimensions[get_column_letter(2 + j)].width = max(
                grad.column_dimensions[get_column_letter(2 + j)].width or 0, 18)
        for i, (lab, counts) in enumerate(bt.rows):
            r = hdr + 1 + i
            grad.cell(r, 1, lab)
            for j, c in enumerate(counts):
                n, _ = addr[f"s3.bands.bucket{i}.band{j}"]
                b.formula(grad, f"{get_column_letter(2 + j)}{r}", f"={n}", c, TOL_COUNT, fmt="#,##0")
            total = f"SUM({get_column_letter(2)}{r}:{get_column_letter(1 + k)}{r})"
            for j in range(k):
                cnt = f"{get_column_letter(2 + j)}{r}"
                b.formula(grad, f"{get_column_letter(2 + k + j)}{r}", f'=IF({total}=0,"",{cnt}/{total})',
                          bt.shares[i][j], fmt="0.0%")
        row = hdr + 1 + len(bt.rows) + 1
    ks.freeze_below(grad, first_hdr)

    # -- 4_Stratified ----------------------------------------------------------
    ncols = 20
    for col, wdt in zip("ABCDEFGHIJKLMNOPQRST", (44, 14, 14, 12, 9, 9, 15, 15, 14, 9, 9, 10, 9, 9, 9, 9, 9, 9, 9, 9)):
        strat.column_dimensions[col].width = wdt
    row = _header_band(strat, ncols, "Step 4 — Stratified", cfg, table, first_facts, run_date, n_out)
    strat_note = notes.fill("notes.stratified",
                            confounder_list=", ".join(c.name for c in cfg.confounders) or "(no confounders declared)",
                            confidence=cfg.confidence, method=cfg.method, threshold=cfg.survives_threshold)
    row = _note(strat, row, strat_note, ncols)
    row += 1
    strat_first_hdr = None
    word_cells_s4: dict[str, list[tuple[ladder.Stratified, str]]] = {}
    for st in data.strata:
        f_ = facts_by[st.outcome.key]
        row = ks.section_band(strat, row, f"Outcome: {st.outcome.label} — {f_.events:,} events among {f_.seasoned:,} seasoned loans"
                              f" · {st.confounder} · {st.scheme}", ncols)
        if not st.bands:
            # nothing to stratify on: no table, no chart, and no formula over an
            # empty range, which the engine reads as #NULL! (adversarial finding 16)
            row = _note(strat, row, notes.fill("notes.stratified_empty", confounder=st.confounder), ncols)
            strat.cell(row, 1, "Word").font = BOLD
            word_cell = f"B{row}"
            b.formula(strat, word_cell, '="no data"', "no data", 0.0, "text")
            word_cells_s4.setdefault(st.outcome.key, []).append((st, word_cell))
            row += 3
            continue
        hdr = row
        strat_first_hdr = strat_first_hdr or hdr
        ks.header_row(strat, hdr, ["Band", "Flagged loans", "Flagged events", "Flagged rate", "Lower", "Upper",
                                   "Unflagged loans", "Unflagged events", "Unflagged rate", "Lower", "Upper",
                                   "Gap (pts)", "P", "Q", "R", "S",
                                   "Flagged bar up", "Flagged bar down", "Unflagged bar up", "Unflagged bar down"], right_from=1)
        first = hdr + 1
        for i, band in enumerate(st.bands):
            r = first + i
            fn, fx = addr[band.flagged.block]
            un, ux = addr[band.unflagged.block]
            strat.cell(r, 1, band.label)
            b.formula(strat, f"B{r}", f"={fn}", band.flagged.n, TOL_COUNT, fmt="#,##0")
            b.formula(strat, f"C{r}", f"={fx}", band.flagged.events, TOL_COUNT, fmt="#,##0")
            b.formula(strat, f"D{r}", f'=IF(B{r}=0,"",C{r}/B{r})', band.flagged_rate, fmt="0.00%")
            b.formula(strat, f"E{r}", interval_formula("lo", f"B{r}", f"C{r}"), band.flagged_lo, TOL_INTERVAL, fmt="0.00%")
            b.formula(strat, f"F{r}", interval_formula("hi", f"B{r}", f"C{r}"), band.flagged_hi, TOL_INTERVAL, fmt="0.00%")
            b.formula(strat, f"G{r}", f"={un}", band.unflagged.n, TOL_COUNT, fmt="#,##0")
            b.formula(strat, f"H{r}", f"={ux}", band.unflagged.events, TOL_COUNT, fmt="#,##0")
            b.formula(strat, f"I{r}", f'=IF(G{r}=0,"",H{r}/G{r})', band.unflagged_rate, fmt="0.00%")
            b.formula(strat, f"J{r}", interval_formula("lo", f"G{r}", f"H{r}"), band.unflagged_lo, TOL_INTERVAL, fmt="0.00%")
            b.formula(strat, f"K{r}", interval_formula("hi", f"G{r}", f"H{r}"), band.unflagged_hi, TOL_INTERVAL, fmt="0.00%")
            b.formula(strat, f"L{r}", f'=IF(OR(D{r}="",I{r}=""),"",(D{r}-I{r})*100)', band.gap_pts, TOL_POINTS, fmt="0.00")
            n_expr = f"(B{r}+G{r})"
            b.formula(strat, f"M{r}", f'=IF({n_expr}=0,0,(C{r}+(G{r}-H{r}))/{n_expr})', band.p, fmt="0.0000")
            b.formula(strat, f"N{r}", f'=IF({n_expr}=0,0,((B{r}-C{r})+H{r})/{n_expr})', band.q, fmt="0.0000")
            b.formula(strat, f"O{r}", f'=IF({n_expr}=0,0,C{r}*(G{r}-H{r})/{n_expr})', band.r, fmt="0.0000")
            b.formula(strat, f"P{r}", f'=IF({n_expr}=0,0,(B{r}-C{r})*H{r}/{n_expr})', band.s, fmt="0.0000")
        last = first + len(st.bands) - 1
        for i, band in enumerate(st.bands):
            r = first + i
            b.formula(strat, f"Q{r}", f'=IF(F{r}="","",F{r}-D{r})', (None if band.flagged_hi is None else band.flagged_hi - band.flagged_rate), TOL_INTERVAL, fmt="0.0000")
            b.formula(strat, f"R{r}", f'=IF(E{r}="","",D{r}-E{r})', (None if band.flagged_lo is None else band.flagged_rate - band.flagged_lo), TOL_INTERVAL, fmt="0.0000")
            b.formula(strat, f"S{r}", f'=IF(K{r}="","",K{r}-I{r})', (None if band.unflagged_hi is None else band.unflagged_hi - band.unflagged_rate), TOL_INTERVAL, fmt="0.0000")
            b.formula(strat, f"T{r}", f'=IF(J{r}="","",I{r}-J{r})', (None if band.unflagged_lo is None else band.unflagged_rate - band.unflagged_lo), TOL_INTERVAL, fmt="0.0000")
        _rate_chart(strat, f"{st.outcome.label} by {st.confounder} ({st.scheme}): flagged vs unflagged",
                    f"{st.outcome.label} rate",
                    Reference(strat, min_col=1, min_row=first, max_row=last),
                    [(Reference(strat, min_col=4, min_row=hdr, max_row=last), f"$Q${first}:$Q${last}", f"$R${first}:$R${last}"),
                     (Reference(strat, min_col=9, min_row=hdr, max_row=last), f"$S${first}:$S${last}", f"$T${first}:$T${last}")],
                    anchor=f"V{hdr}", width=16.0, height=7.0)
        rB, rC, rG, rH = f"B{first}:B{last}", f"C{first}:C{last}", f"G{first}:G{last}", f"H{first}:H{last}"
        rM, rN, rO, rP = f"M{first}:M{last}", f"N{first}:N{last}", f"O{first}:O{last}", f"P{first}:P{last}"
        row = last + 2
        A_, B_, C_, D_ = f"SUM({rC})", f"(SUM({rB})-SUM({rC}))", f"SUM({rH})", f"(SUM({rG})-SUM({rH}))"
        strat.cell(row, 1, "Crude odds ratio, whole population — ratio, lower, upper").font = BOLD
        crude_cell = f"B{row}"
        b.formula(strat, crude_cell, f'=IF(OR({A_}=0,{B_}=0,{C_}=0,{D_}=0),"not estimable",({A_}*{D_})/({B_}*{C_}))',
                  st.crude[0] if st.crude[0] is not None else "not estimable", TOL_RATE * 1e3,
                  "number" if st.crude[0] is not None else "text", fmt="0.00")
        se_crude = f"SQRT(1/{A_}+1/{B_}+1/{C_}+1/{D_})"
        b.formula(strat, f"C{row}", f'=IF({crude_cell}="not estimable","",EXP(LN({crude_cell})-Z*{se_crude}))',
                  st.crude[1], TOL_INTERVAL * 1e3, fmt="0.00")
        b.formula(strat, f"D{row}", f'=IF({crude_cell}="not estimable","",EXP(LN({crude_cell})+Z*{se_crude}))',
                  st.crude[2], TOL_INTERVAL * 1e3, fmt="0.00")
        row += 1
        strat.cell(row, 1, "Pooled odds ratio across bands (Mantel-Haenszel) — ratio, lower, upper").font = BOLD
        mh_cell = f"B{row}"
        b.formula(strat, mh_cell, f'=IF(OR(SUM({rO})=0,SUM({rP})=0),"not estimable",SUM({rO})/SUM({rP}))',
                  st.pooled[0] if st.pooled[0] is not None else "not estimable", TOL_RATE * 1e3,
                  "number" if st.pooled[0] is not None else "text", fmt="0.00")
        var_mh = (f"(SUMPRODUCT({rM},{rO})/(2*SUM({rO})^2)+(SUMPRODUCT({rM},{rP})+SUMPRODUCT({rN},{rO}))/(2*SUM({rO})*SUM({rP}))"
                  f"+SUMPRODUCT({rN},{rP})/(2*SUM({rP})^2))")
        b.formula(strat, f"C{row}", f'=IF({mh_cell}="not estimable","",EXP(LN({mh_cell})-Z*SQRT({var_mh})))',
                  st.pooled[1], TOL_INTERVAL * 1e3, fmt="0.00")
        b.formula(strat, f"D{row}", f'=IF({mh_cell}="not estimable","",EXP(LN({mh_cell})+Z*SQRT({var_mh})))',
                  st.pooled[2], TOL_INTERVAL * 1e3, fmt="0.00")
        crude_row, mh_row = row - 1, row
        row += 1
        strat.cell(row, 1, "Share of the crude log-odds the pooled ratio kept").font = BOLD
        kept_cell = f"B{row}"
        b.formula(strat, kept_cell,
                  f'=IF(OR({crude_cell}="not estimable",{mh_cell}="not estimable",{crude_cell}=1),"",LN({mh_cell})/LN({crude_cell}))',
                  st.kept, TOL_INTERVAL * 1e3, fmt="0.00")
        row += 1
        strat.cell(row, 1, "Word").font = BOLD
        word_cell = f"B{row}"
        b.formula(strat, word_cell,
                  f'=IF({crude_cell}="not estimable","no crude effect",'
                  f'IF(AND(C{crude_row}<=1,D{crude_row}>=1),"no crude effect",'
                  f'IF({mh_cell}="not estimable","unknown",'
                  f'IF({kept_cell}<1-SURV_T,"collapses",'
                  f'IF(OR(C{mh_row}>1,D{mh_row}<1),"survives","unknown")))))', st.word, 0.0, "text")
        strat.merge_cells(f"B{row}:D{row}")
        word_cells_s4.setdefault(st.outcome.key, []).append((st, word_cell))
        row += 2
        # the gradient inside each band
        for band in st.bands:
            strat.cell(row, 1, f"Inside band: {band.label}").font = BOLD
            row += 1
            ks.header_row(strat, row, ["Bucket", "Loans", "Events", "Rate", "Lower", "Upper"], right_from=1)
            row += 1
            for gr in band.buckets:
                n, x = addr[gr.cube.block]
                strat.cell(row, 1, gr.cube.label.split(" | ")[1])
                b.formula(strat, f"B{row}", f"={n}", gr.cube.n, TOL_COUNT, fmt="#,##0")
                b.formula(strat, f"C{row}", f"={x}", gr.cube.events, TOL_COUNT, fmt="#,##0")
                b.formula(strat, f"D{row}", f'=IF(B{row}=0,"",C{row}/B{row})', gr.rate, fmt="0.00%")
                b.formula(strat, f"E{row}", interval_formula("lo", f"B{row}", f"C{row}"), gr.lo, TOL_INTERVAL, fmt="0.00%")
                b.formula(strat, f"F{row}", interval_formula("hi", f"B{row}", f"C{row}"), gr.hi, TOL_INTERVAL, fmt="0.00%")
                row += 1
            row += 1
        row += 1
    if strat_first_hdr:
        ks.freeze_below(strat, strat_first_hdr)

    # -- 5_Decomposition -------------------------------------------------------
    ncols = 13
    for col, wdt in zip("ABCDEFGHIJKLM", (30, 14, 14, 12, 9, 9, 15, 15, 14, 9, 9, 10, 10)):
        decomp.column_dimensions[col].width = wdt
    row = _header_band(decomp, ncols, "Step 5 — Decomposition", cfg, table, first_facts, run_date, n_out)
    decomp_note = notes.fill("notes.decomposition", confidence=cfg.confidence, method=cfg.method)
    row = _note(decomp, row, decomp_note, ncols)
    row += 1
    decomp_first_hdr = None
    for dc in data.decompositions:
        f_ = facts_by[dc.outcome.key]
        row = ks.section_band(decomp, row, f"Outcome: {dc.outcome.label} — {f_.events:,} events among {f_.seasoned:,} seasoned loans"
                              f" · by {dc.dimension}", ncols)
        hdr = row
        decomp_first_hdr = decomp_first_hdr or hdr
        ks.header_row(decomp, hdr, [dc.dimension, "Flagged loans", "Flagged events", "Flagged rate", "Lower", "Upper",
                                    "Unflagged loans", "Unflagged events", "Unflagged rate", "Lower", "Upper",
                                    "Gap (pts)", "Share of flagged events"], right_from=1)
        first = hdr + 1
        last = hdr + len(dc.rows)
        for i, r_ in enumerate(dc.rows):
            r = first + i
            fn, fx = addr[r_.flagged.block]
            un, ux = addr[r_.unflagged.block]
            decomp.cell(r, 1, r_.label)
            b.formula(decomp, f"B{r}", f"={fn}", r_.flagged.n, TOL_COUNT, fmt="#,##0")
            b.formula(decomp, f"C{r}", f"={fx}", r_.flagged.events, TOL_COUNT, fmt="#,##0")
            b.formula(decomp, f"D{r}", f'=IF(B{r}=0,"",C{r}/B{r})', r_.flagged_rate, fmt="0.00%")
            b.formula(decomp, f"E{r}", interval_formula("lo", f"B{r}", f"C{r}"), r_.flagged_lo, TOL_INTERVAL, fmt="0.00%")
            b.formula(decomp, f"F{r}", interval_formula("hi", f"B{r}", f"C{r}"), r_.flagged_hi, TOL_INTERVAL, fmt="0.00%")
            b.formula(decomp, f"G{r}", f"={un}", r_.unflagged.n, TOL_COUNT, fmt="#,##0")
            b.formula(decomp, f"H{r}", f"={ux}", r_.unflagged.events, TOL_COUNT, fmt="#,##0")
            b.formula(decomp, f"I{r}", f'=IF(G{r}=0,"",H{r}/G{r})', r_.unflagged_rate, fmt="0.00%")
            b.formula(decomp, f"J{r}", interval_formula("lo", f"G{r}", f"H{r}"), r_.unflagged_lo, TOL_INTERVAL, fmt="0.00%")
            b.formula(decomp, f"K{r}", interval_formula("hi", f"G{r}", f"H{r}"), r_.unflagged_hi, TOL_INTERVAL, fmt="0.00%")
            b.formula(decomp, f"L{r}", f'=IF(OR(D{r}="",I{r}=""),"",(D{r}-I{r})*100)', r_.gap_pts, TOL_POINTS, fmt="0.00")
            b.formula(decomp, f"M{r}", f'=IF(SUM(C{first}:C{last})=0,"",C{r}/SUM(C{first}:C{last}))', r_.share, fmt="0.0%")
        row = last + 2
    if decomp_first_hdr:
        ks.freeze_below(decomp, decomp_first_hdr)

    # -- 6_Model (values only) ---------------------------------------------------
    for col, wdt in zip("ABCDEFG", (34, 12, 10, 10, 12, 11, 60)):
        mdl.column_dimensions[col].width = wdt
    row = _header_band(mdl, 7, "Step 6 — Model", cfg, table, first_facts, run_date, n_out)
    model_note = notes.fill("notes.model", confidence=cfg.confidence)
    row = _note(mdl, row, model_note, 7)
    row += 1
    model_lines: dict[str, str] = {}
    for mr in data.models:
        row = ks.section_band(mdl, row, f"Outcome: {mr.outcome.label}", 7)
        mdl.cell(row, 1, f"Loans in the design: {mr.used:,} seasoned loans with both rule fields and every predictor present; "
                         f"{mr.excluded_blank:,} left out for a blank predictor.")
        mdl.merge_cells(f"A{row}:G{row}"); row += 1
        for fit in (mr.m1, mr.m2):
            mdl.cell(row, 1, f"{fit.label}: {'flag + controls' if fit.label == 'M1' else 'M1 + confounders not already controls'}").font = BOLD
            row += 1
            head = (f"{fit.loans:,} loans · {fit.events:,} events · {fit.coefficients} estimated coefficients · "
                    f"events per parameter {fit.epp:.1f}" if fit.epp is not None else f"{fit.loans:,} loans · {fit.events:,} events")
            mdl.cell(row, 1, head); mdl.merge_cells(f"A{row}:G{row}"); row += 1
            if fit.warning:
                c = mdl.cell(row, 1, fit.warning); c.font = ks.ALERT_FONT; c.alignment = Alignment(wrap_text=True)
                mdl.merge_cells(f"A{row}:G{row}"); mdl.row_dimensions[row].height = 30; row += 1
            if fit.skipped:
                mdl.cell(row, 1, "Skipped: " + "; ".join(fit.skipped)); mdl.merge_cells(f"A{row}:G{row}"); row += 1
            if not fit.estimable:
                c = mdl.cell(row, 1, fit.reason + (f" — implicated: {', '.join(fit.implicated)}" if fit.implicated else ""))
                c.font = ks.ALERT_FONT; mdl.merge_cells(f"A{row}:G{row}"); row += 2
                continue
            ks.header_row(mdl, row, ["Term", "Odds ratio", "Lower", "Upper", "Coefficient", "Std error", "Reference level"], right_from=1)
            row += 1
            for term in fit.terms:
                mdl.cell(row, 1, term.name)
                mdl.cell(row, 2, term.odds_ratio).number_format = "0.000"
                mdl.cell(row, 3, term.lo).number_format = "0.000"
                mdl.cell(row, 4, term.hi).number_format = "0.000"
                mdl.cell(row, 5, term.coef).number_format = "0.0000"
                mdl.cell(row, 6, term.se).number_format = "0.0000"
                base = term.name.split("=")[0]
                if base in fit.references:
                    mdl.cell(row, 7, f"against {base}={fit.references[base]}")
                row += 1
            mdl.cell(row, 1, "intercept"); mdl.cell(row, 5, fit.intercept).number_format = "0.0000"; row += 2
        tr = mr.tree
        mdl.cell(row, 1, f"Tree, depth up to {cfg.model['tree_depth']}: {tr.loans:,} loans, {tr.events:,} events, "
                         f"overall rate {tr.overall_rate:.2%}" if tr.overall_rate is not None else "Tree: no loans").font = BOLD
        mdl.merge_cells(f"A{row}:G{row}"); row += 1
        ks.header_row(mdl, row, ["Rule", "Loans", "Events", "Rate", "Lift"], right_from=1); row += 1
        for leaf in tr.leaves:
            mdl.cell(row, 1, " and ".join(leaf.path) if leaf.path else "(no split found)")
            mdl.cell(row, 2, leaf.loans).number_format = "#,##0"
            mdl.cell(row, 3, leaf.events).number_format = "#,##0"
            if leaf.rate is not None:
                mdl.cell(row, 4, leaf.rate).number_format = "0.00%"
                if tr.overall_rate:
                    mdl.cell(row, 5, leaf.rate / tr.overall_rate).number_format = "0.00"
            row += 1
        row += 1
        f1, f2 = mr.m1.flag(), mr.m2.flag()
        if mr.m1.estimable and mr.m2.estimable and f1 and f2:
            model_lines[mr.outcome.key] = notes.pick("cover.answer_model", "both", m1=f1.odds_ratio, m1lo=f1.lo, m1hi=f1.hi,
                                                     m2=f2.odds_ratio, m2lo=f2.lo, m2hi=f2.hi, events=mr.m1.events)
        elif mr.m1.estimable and f1:
            model_lines[mr.outcome.key] = notes.pick("cover.answer_model", "m1_only", m1=f1.odds_ratio, m1lo=f1.lo, m1hi=f1.hi,
                                                     m2_reason=mr.m2.reason or "not estimable")
        else:
            model_lines[mr.outcome.key] = notes.pick("cover.answer_model", "unknown", reason=mr.m1.reason or "not estimable")

    # -- 7_Control ---------------------------------------------------------------
    control_lines: list[str] = []
    if ctrl is not None and data.control is not None:
        ctrl.column_dimensions["A"].width = 110
        ctrl.column_dimensions["B"].width = 16
        row = _header_band(ctrl, 2, "Step 7 — The observation that stands regardless", cfg, table, first_facts, run_date, n_out)
        row = _note(ctrl, row, notes.fill("notes.control"), 2)
        row += 1
        n_cell, x_cell = addr[data.control.both.block]
        ctrl.cell(row, 1, "Seasoned loans with both fields present"); b.formula(ctrl, f"B{row}", f"={n_cell}", data.control.both.n, TOL_COUNT, fmt="#,##0"); row += 1
        ctrl.cell(row, 1, "Of those, loans where the rule fires"); b.formula(ctrl, f"B{row}", f"={x_cell}", data.control.both.events, TOL_COUNT, fmt="#,##0"); row += 1
        ctrl.cell(row, 1, "Share"); b.formula(ctrl, f"B{row}", f'=IF(B{row - 2}=0,"",B{row - 1}/B{row - 2})', data.control.share, fmt="0.0%"); row += 2
        if data.control.share is None:
            # no seasoned loan carries both fields: there is no share, and "0.0%
            # of 0" would read as checked-and-never (adversarial finding 8)
            share_text = notes.fill("control.share_none", field_a=cfg.rule.field_a, field_b=cfg.rule.field_b,
                                    fires_text=_fires_text(cfg))
        else:
            share_text = notes.fill("control.share", share=data.control.share, both=data.control.both.n,
                                    field_a=cfg.rule.field_a, field_b=cfg.rule.field_b, fires_text=_fires_text(cfg))
        control_lines.append(share_text)
        for fld, key in ((cfg.rule.field_a, "field_a"), (cfg.rule.field_b, "field_b")):
            if cfg.drives.get(key):
                control_lines.append(notes.fill("control.drives_line", field=fld, text=cfg.drives[key]))
        if cfg.existing_control.lower() == "none":
            control_lines.append(notes.fill("control.none"))
        else:
            control_lines.append(notes.fill("control.some", text=cfg.existing_control))
        for line in control_lines:
            c = ctrl.cell(row, 1, line); c.alignment = Alignment(wrap_text=True); row += 1

    # -- Cover -----------------------------------------------------------
    cover.column_dimensions["A"].width = 110
    row = ks.brand_banner(cover, 1, 1, "Portfolio Analysis Pack",
                          f"{cfg.name} · run {run_date.isoformat()} · as-of {pop.asof.isoformat()} · generator {__version__}")
    row += 1
    cover.cell(row, 1, "The question").font = BOLD; row += 1
    row = _note(cover, row, notes.fill("cover.question", rule_sentence=_rule_sentence(cfg), outcome_label=cfg.outcome.label), 1)
    row += 1
    cover.cell(row, 1, "The answer, in three lines" + (" (per outcome)" if len(data.per_outcome) > 1 else "")).font = BOLD; row += 1
    for g, word_cell in word_cells:
        def v(key: str) -> str:
            return notes.pick("cover.answer_gradient", key, outcome_label=g.outcome.label).replace('"', '""')
        wc = f"'3_Gradient'!{word_cell}"
        b.formula(cover, f"A{row}",
                  f'=IF({wc}="monotonic increasing","{v("monotonic increasing")}",IF({wc}="monotonic decreasing","{v("monotonic decreasing")}",'
                  f'IF({wc}="not monotonic","{v("not monotonic")}",IF({wc}="flat","{v("flat")}","{v("no data")}"))))',
                  notes.pick("cover.answer_gradient", g.word, outcome_label=g.outcome.label), 0.0, "text")
        cover[f"A{row}"].alignment = Alignment(wrap_text=True)
        row += 1
    for facts, g in data.per_outcome:
        items = word_cells_s4.get(g.outcome.key, [])
        if not items:
            cover.cell(row, 1, notes.fill("cover.not_built", step="Survives or collapses (step 4)")); row += 1
            continue
        prefix = notes.fill("cover.answer_stratified_prefix", outcome_label=g.outcome.label).replace('"', '""')
        parts = []
        twin_parts = []
        for st, wc in items:
            # fill with a marker and cut at it, so the space before the live word survives the template's strip
            lead = notes.fill("cover.answer_stratified_item", confounder=st.confounder, scheme=st.scheme,
                              word="\x00").split("\x00")[0].replace('"', '""')
            parts.append(f'"{lead}"&\'4_Stratified\'!{wc}')
            twin_parts.append(notes.fill("cover.answer_stratified_item", confounder=st.confounder, scheme=st.scheme, word=st.word))
        b.formula(cover, f"A{row}", f'="{prefix}"&' + '&"; "&'.join(parts),
                  notes.fill("cover.answer_stratified_prefix", outcome_label=g.outcome.label) + "; ".join(twin_parts), 0.0, "text")
        cover[f"A{row}"].alignment = Alignment(wrap_text=True)
        row += 1
    for facts, g in data.per_outcome:
        line = model_lines.get(g.outcome.key) or notes.fill("cover.not_built", step="Model (step 6)")
        c = cover.cell(row, 1, line); c.alignment = Alignment(wrap_text=True); row += 1
    row += 1
    if control_lines:
        cover.cell(row, 1, notes.fill("control.cover_heading")).font = BOLD; row += 1
        for line in control_lines:
            row = _note(cover, row, line, 1)
        row += 1
    cover.cell(row, 1, "What it rests on").font = BOLD; row += 1
    for facts, g in data.per_outcome:
        row = _note(cover, row, notes.fill("cover.denominator", seasoned=facts.seasoned, events=facts.events,
                                           outcome_label=g.outcome.label, unseasoned=facts.unseasoned,
                                           window_months=cfg.window_months), 1)
    row += 1
    check_line_row = row
    row += 2
    cover.cell(row, 1, "Source").font = BOLD; row += 1
    _note(cover, row, f"{table.path.split('/')[-1]} · sha256 {table.sha256} · {pop.rows_read:,} rows read · "
                      f"question file {cfg.name} · sha256 {cfg.source_sha256[:16]}…", 1)

    # -- _method ---------------------------------------------------------
    meth.column_dimensions["A"].width = 120
    row = ks.section_band(meth, 1, "Method notes — generated from the question file and the counts", 1)
    filt = notes.fill("notes.filter_some", filter_text="; ".join(f"{k} in {list(v)}" for k, v in cfg.filter.items()),
                      rows_after_filter=pop.rows_after_filter) if cfg.filter else ""
    date_text = "; ".join(f"{col}: {fmt} ({pop.date_parsed[col]:,} values)" for col, fmt in pop.date_formats.items())
    for text in (
        notes.fill("notes.population", rows_read=pop.rows_read, source_name=table.path.split('/')[-1],
                   filter_sentence=filt, loans=len(pop.loans), asof=pop.asof.isoformat(),
                   window_months=cfg.window_months, seasoned=data.seasoned, unseasoned=data.unseasoned),
        notes.fill("notes.dates", date_text=date_text),
        _outcome_note(cfg),
        cap_note,
        prev_note,
        grad_note,
        strat_note,
        decomp_note,
        model_note,
        notes.fill("notes.check"),
    ):
        row = _note(meth, row, text, 1)

    # -- _provenance -----------------------------------------------------
    prov.column_dimensions["A"].width = 34; prov.column_dimensions["B"].width = 90
    row = ks.section_band(prov, 1, "Provenance", 2)
    items = [("Source file", table.path.split('/')[-1]), ("Source sha256", table.sha256),
             ("Source kind", table.kind), ("Rows read", pop.rows_read),
             ("Rows after filter", pop.rows_after_filter), ("Loans after typing", len(pop.loans)),
             ("Seasoned loans", data.seasoned), ("Unseasoned loans (excluded from rates)", data.unseasoned)]
    for facts, g in data.per_outcome:
        items.append((f"Events among seasoned loans ({g.outcome.label})", facts.events))
    items += [("Question file", cfg.name), ("Question file sha256", cfg.source_sha256)]
    for col, fmt in pop.date_formats.items():
        items.append((f"Date format: {col}", f"{fmt}, {pop.date_parsed[col]:,} of {pop.date_parsed[col]:,} parsed"))
    items += [("As-of date", pop.asof.isoformat()), ("Run date", run_date.isoformat()),
              ("Generator version", __version__),
              ("Window (months)", cfg.window_months), ("Confidence (at build)", cfg.confidence),
              ("Interval method (at build)", cfg.method)]
    for k, val in items:
        prov.cell(row, 1, k); prov.cell(row, 2, val); row += 1
    row += 1
    prov.cell(row, 1, "Range check, per declared field").font = BOLD; row += 1
    for name, checked in pop.range_checked.items():
        lo_hi = cfg.fields[name].plausible
        prov.cell(row, 1, name)
        prov.cell(row, 2, f"checked against {lo_hi[0]:g} – {lo_hi[1]:g}" if checked else "range check: not run (no plausible range given)")
        row += 1
    row += 1
    prov.cell(row, 1, "Unseasoned by origination quarter").font = BOLD; row += 1
    for q, n in data.unseasoned_by_quarter.items():
        prov.cell(row, 1, q); prov.cell(row, 2, n); row += 1

    # -- _check ----------------------------------------------------------
    for col, w in zip("ABCDEFG", (14, 8, 70, 16, 16, 12, 12)):
        check.column_dimensions[col].width = w
    ks.header_row(check, 1, ["Sheet", "Cell", "Formula", "Python", "Live", "Tolerance", "Agree?"], right_from=3)
    r = 2
    for c in b.checks:
        check.cell(r, 1, c.sheet); check.cell(r, 2, c.cell)
        ftext = check.cell(r, 3, c.formula)
        ftext.data_type = "s"        # the formula's TEXT, for the reader; not a live formula
        check.cell(r, 4, "" if c.python is None else c.python)
        check.cell(r, 5, f"='{c.sheet}'!{c.cell}")
        check.cell(r, 6, c.tol)
        if c.kind == "text":
            check.cell(r, 7, f'=IF(E{r}&""=D{r}&"","OK","MISMATCH")')
        else:
            check.cell(r, 7, f'=IF(AND(ISNUMBER(E{r}),ISNUMBER(D{r})),IF(ABS(E{r}-D{r})<=F{r},"OK","MISMATCH"),IF(E{r}&""=D{r}&"","OK","MISMATCH"))')
        r += 1
    last = r - 1
    ks.freeze_below(check, 1)
    # The Python column is a snapshot at the settings the pack was built with. A
    # reader who moves a live knob must not read a false count (adversarial
    # finding 15, 19 Sep 2026): the line then says the knobs moved.
    at_built = f'AND(CONF={cfg.confidence!r},METHOD="{cfg.method}",SURV_T={cfg.survives_threshold!r})'
    moved = notes.fill("cover.check_moved", confidence=cfg.confidence, method=cfg.method,
                       threshold=cfg.survives_threshold).replace('"', '""')
    cover[f"A{check_line_row}"] = (f'=IF({at_built},COUNTIF(_check!$G$2:$G${last},"OK")&" of "&COUNTA(_check!$G$2:$G${last})'
                                   f'&" formula checks agree (see _check)","{moved}")')
    cover[f"A{check_line_row}"].font = BOLD
    return wb, data, b.checks


def _outcome_note(cfg: Config) -> str:
    o = cfg.outcome
    if o.form == "event_date":
        return notes.fill("notes.outcome_event_date", outcome_label=o.label, date_field=o.date_field,
                          window_months=cfg.window_months)
    if o.form == "flag":
        return notes.fill("notes.outcome_flag", outcome_label=o.label, field=o.field, op=o.op, value=o.value,
                          window_months=cfg.window_months)
    m = o.measure or {}
    mt = m.get("field") or f"{m.get('field_a')} {'÷' if m.get('kind', 'ratio') == 'ratio' else '−'} {m.get('field_b')}"
    if o.edges:
        return notes.fill("notes.outcome_snapshot_bands", outcome_label=o.label, measure_text=mt,
                          edges=", ".join(f"{e:g}" for e in o.edges), window_months=cfg.window_months)
    return notes.fill("notes.outcome_snapshot", outcome_label=o.label, measure_text=mt, op=o.op, value=o.value,
                      window_months=cfg.window_months)


def workbook_bytes(wb: Workbook, run_date: date) -> bytes:
    """Serialize deterministically: same content and run date -> identical bytes."""
    raw = io.BytesIO()
    wb.save(raw)
    stamp = run_date.strftime("%Y-%m-%dT00:00:00Z").encode()
    out = io.BytesIO()
    with zipfile.ZipFile(raw) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for name in src.namelist():
            data = src.read(name)
            if name == "docProps/core.xml":
                data = re.sub(rb"<dcterms:modified[^>]*>[^<]*</dcterms:modified>",
                              b'<dcterms:modified xsi:type="dcterms:W3CDTF">' + stamp + b"</dcterms:modified>", data)
                data = re.sub(rb"<dcterms:created[^>]*>[^<]*</dcterms:created>",
                              b'<dcterms:created xsi:type="dcterms:W3CDTF">' + stamp + b"</dcterms:created>", data)
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(info, data)
    return out.getvalue()


def build_pack(cfg: Config, pop: Population, table: Table, run_date: date) -> tuple[bytes, ladder.PackData, list[Check]]:
    wb, data, checks = build_workbook(cfg, pop, table, run_date)
    return workbook_bytes(wb, run_date), data, checks
