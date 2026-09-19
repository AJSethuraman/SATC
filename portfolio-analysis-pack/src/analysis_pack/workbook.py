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


def _note(ws, row: int, text: str, ncols: int) -> int:
    last = get_column_letter(ncols)
    ws.merge_cells(f"A{row}:{last}{row}")
    c = ws.cell(row, 1, text)
    c.font = ks.SECONDARY
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[row].height = max(30, 15 * (1 + len(text) // 110))
    return row + 1


def _header_band(ws, ncols: int, title: str, cfg: Config, table: Table, facts: ladder.Facts, run_date: date) -> int:
    row = ks.brand_banner(ws, 1, ncols, title,
                          f"{cfg.name} · source {table.path.split('/')[-1]} · sha256 {table.sha256[:16]}… · "
                          f"{facts.seasoned:,} seasoned loans · {facts.events:,} events · "
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
    cube = wb.create_sheet("_cube")
    conf = wb.create_sheet("_config")
    meth = wb.create_sheet("_method")
    check = wb.create_sheet("_check")
    prov = wb.create_sheet("_provenance")
    for ws in (cover, cap, prev, grad, cube, conf, meth, check, prov):
        ks.hide_gridlines(ws)
    first_facts = data.per_outcome[0][0]

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
    if data.bands:
        for i, (lab, counts) in enumerate(data.bands.rows):
            for j, c in enumerate(counts):
                put_cube(ladder.CubeRow(f"s3.bands.bucket{i}.band{j}", f"{lab} | {data.bands.band_labels[j]}", c, 0))
    for q, n in data.unseasoned_by_quarter.items():
        put_cube(ladder.CubeRow(f"unseasoned.{q}", q, n, 0))

    # -- 1_Capture -------------------------------------------------------------
    ncols = 9
    for col, wdt in zip("ABCDEFGHI", (22, 16, 12, 16, 9, 16, 9, 14, 9)):
        cap.column_dimensions[col].width = wdt
    row = _header_band(cap, ncols, "Step 1 — Capture", cfg, table, first_facts, run_date)
    cap_note = notes.fill("notes.capture", window_months=cfg.window_months, field_a=cfg.rule.field_a,
                          field_b=cfg.rule.field_b)
    row = _note(cap, row, cap_note, ncols)
    row += 1
    hdr = row
    ks.header_row(cap, hdr, ["Quarter", "Loans", "Unseasoned", f"{cfg.rule.field_a} blank", "share",
                             f"{cfg.rule.field_b} blank", "share", "Both present", "share"], right_from=1)
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
    row = _header_band(prev, ncols, "Step 2 — Prevalence", cfg, table, first_facts, run_date)
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
    for col, w in zip("ABCDEFGHIJ", (26, 10, 10, 10, 10, 10, 11, 10, 14, 14)):
        grad.column_dimensions[col].width = w
    row = _header_band(grad, ncols, "Step 3 — Gradient", cfg, table, first_facts, run_date)
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
                                  "Rate change vs bucket above", "Interval clear of bucket above"], right_from=1)
        first = hdr + 1
        base_row = first + len(g.rows)
        n_base, x_base = addr[g.base.cube.block]
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
            if i > 0:
                pr = r - 1
                b.formula(grad, f"I{r}", f'=IF(OR(D{r}="",D{pr}=""),"",D{r}-D{pr})', g.diffs[i - 1], fmt="0.0000")
                b.formula(grad, f"J{r}", f'=IF(OR(E{r}="",F{pr}=""),0,IF(E{r}>F{pr},1,0)+IF(F{r}<E{pr},1,0))', g.nonoverlap[i - 1], TOL_COUNT)
        r = base_row
        grad.cell(r, 1, "Base: rule does not fire").font = BOLD
        b.formula(grad, f"B{r}", f"={n_base}", g.base.cube.n, TOL_COUNT, fmt="#,##0")
        b.formula(grad, f"C{r}", f"={x_base}", g.base.cube.events, TOL_COUNT, fmt="#,##0")
        b.formula(grad, f"D{r}", f'=IF(B{r}=0,"",C{r}/B{r})', g.base.rate, fmt="0.00%")
        b.formula(grad, f"E{r}", interval_formula("lo", f"B{r}", f"C{r}"), g.base.lo, TOL_INTERVAL, fmt="0.00%")
        b.formula(grad, f"F{r}", interval_formula("hi", f"B{r}", f"C{r}"), g.base.hi, TOL_INTERVAL, fmt="0.00%")
        row = base_row + 2
        i_rng = f"I{first + 1}:I{first + len(g.rows) - 1}"
        j_rng = f"J{first + 1}:J{first + len(g.rows) - 1}"
        grad.cell(row, 1, "Monotonic?").font = BOLD
        word_cell = f"B{row}"
        b.formula(grad, word_cell,
                  f'=IF(COUNT({i_rng})=0,"no data",IF(COUNTIF({i_rng},"<0")=0,"monotonic increasing",'
                  f'IF(COUNTIF({i_rng},">0")=0,"monotonic decreasing","not monotonic")))', g.word, 0.0, "text")
        grad.merge_cells(f"B{row}:E{row}")
        word_cells.append((g, word_cell))
        row += 1
        grad.cell(row, 1, "Adjacent pairs whose intervals do not overlap").font = BOLD
        grad.merge_cells(f"A{row}:D{row}")
        b.formula(grad, f"E{row}", f"=SUM({j_rng})", g.nonoverlap_count, TOL_COUNT)
        row += 2
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
                  f'IF({wc}="not monotonic","{v("not monotonic")}","{v("no data")}")))',
                  notes.pick("cover.answer_gradient", g.word, outcome_label=g.outcome.label), 0.0, "text")
        cover[f"A{row}"].alignment = Alignment(wrap_text=True)
        row += 1
    cover.cell(row, 1, notes.fill("cover.not_built", step="Survives or collapses (step 4)")); row += 1
    cover.cell(row, 1, notes.fill("cover.not_built", step="Model (step 6)")); row += 2
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
    cover[f"A{check_line_row}"] = (f'=COUNTIF(_check!$G$2:$G${last},"OK")&" of "&COUNTA(_check!$G$2:$G${last})'
                                   f'&" formula checks agree (see _check)"')
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
