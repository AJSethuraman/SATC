"""The firm at the bank machine, 30 Sep 2026 (BACKLOG §6d): the bureau's missing codes.

- "still not seeming to identify that things that aren't recent delinquency have negative values ... it's useful to
  see the value because they are generally just missing items"
- "I can guarantee you that they are the bureau missing codes so I think it's just not working correctly."

A numeric column read as a category (installment delinquencies of 0, 1, 2 and -99,000,900) was asked nothing, and
the one cell that was asked read "-9.90009e+07 on 12,410 loans". Every numeric column is now asked about, the cell
shows the codes as a person writes them, a category answered Missing gets "(marked missing)", and Control carries
one question more: "Treat values ≤ -99,000,000 as missing in every column?". The extract here is synthetic.
"""

import csv
import random

import pytest
from openpyxl import load_workbook

from pocketbook import book, choices as ch, config as cfgmod, control, engine, look, perm, profile, synth
from test_book import _answer, treat_odd

CODE = -99000900
INST = "INST_30D"          # a count of 0, 1 or 2 read as a category, with the bureau's code for "none on file"
HIST = "SHORT_HIST"        # months of history, a band, with four codes from -99,000,901


def _extract(tmp_path, n=1500):
    src = synth.write_extract(tmp_path / "src", n=n)
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    rng = random.Random(30)
    for i, r in enumerate(rows):
        r[INST] = CODE if i % 25 == 0 else rng.choice([0, 0, 0, 1, 2])
        r[HIST] = -99000901 - (i // 40) % 4 if i % 40 == 0 else rng.randint(0, 435)
    out = tmp_path / "codes.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return out


def _count(path, column, test) -> int:
    """Loans in the CSV itself whose `column` passes `test`: the independent count."""
    return sum(1 for r in csv.DictReader(open(path, encoding="utf-8")) if test(float(r[column])))


def _set_up(tmp_path, monkeypatch):
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    monkeypatch.setattr(perm, "SHUFFLES", 200)
    x = _extract(tmp_path)
    b = book.set_up(x, choices=ch.Choices(run_kind=ch.BLEED, bands=("FICO", HIST), segments=("CHANNEL", INST),
                                          outcome="BAD_FLAG")).book
    return x, b


def _odd_cells(b) -> dict[str, list[str]]:
    ws = load_workbook(b)["Columns"]
    out: dict[str, list[str]] = {}
    for r in book.table_rows(ws):
        key = r[book.C_QKEY - 1].value
        if isinstance(key, str) and key.count("|") == 2:
            out.setdefault(key.split("|")[0], []).append(str(r[book.C_ODD - 1].value))
    return out


def _control(b, key, value) -> None:
    wb = load_workbook(b)
    for r in wb[control.SHEET].iter_rows(min_row=control.FIRST_ROW):
        if r[control.KEY_COL - 1].value == key:
            r[control.CHOOSE_COL - 1].value = value
            wb.save(b)
            return
    raise KeyError(key)


def _log_text(b) -> str:
    wb = load_workbook(b)
    return " ".join(str(c.value) for t in wb.sheetnames for row in wb[t].iter_rows() for c in row
                    if isinstance(c.value, str) and "treated as missing (Control)" in c.value)


def _engine(b, x):
    raw, problems, _ = book.read_book(b)
    assert raw is not None, problems
    cfg = cfgmod.parse(raw)
    return cfg, engine.run(cfg, book.read_table(x))


def _grid(res, cfg, dim=None, band=None):
    """The grid whose segment reads `dim` (and, given, whose bands read `band`): by field, as the extract names it."""
    dname = next(d.name for d in cfg.dimensions if d.field == dim) if dim else None
    bname = next(b.name for b in cfg.bands if b.field == band) if band else None
    return next(g for g in res.grids if (dname is None or g.dimension == dname) and (bname is None or g.band == bname))


# ---- detection on every numeric column, a category's too


def test_a_numeric_column_read_as_a_category_is_asked_about_its_code(tmp_path):
    x = _extract(tmp_path)
    t = book.read_table(x)
    inst = next(c for c in profile.classify(t, 12, 50) if c.name == INST)
    assert inst.role == "dimension"                         # read as a category, and still asked
    q = [q for q in inst.questions if q["pattern"] == "negatives"]
    assert q and q[0]["rows"] == _count(x, INST, lambda v: v < 0) == 60
    assert q[0]["shown"] == [(CODE, 60)] and q[0]["highest"] == CODE


def test_a_zero_one_step_from_the_rest_is_never_asked_about():
    assert profile.odd_values("FLAG", [0.0] * 900 + [1.0] * 100) == []
    assert profile.odd_values("N", [0.0] * 800 + [1.0] * 150 + [2.0] * 50) == []


def test_the_odd_values_cell_shows_the_codes_and_their_loans_never_scientific_notation(tmp_path, monkeypatch):
    x, b = _set_up(tmp_path, monkeypatch)
    cells = _odd_cells(b)
    assert cells[INST] == [f"-99,000,900 on {_count(x, INST, lambda v: v == CODE):,} loans"]
    hist = cells[HIST][0]
    for code in (-99000901, -99000902, -99000903, -99000904):
        assert f"{cfgmod.plain_value(code)} on {_count(x, HIST, lambda v, c=code: v == c)}" in hist
    assert book._odd_rows(hist) == _count(x, HIST, lambda v: v < 0) == 38
    text = " ".join(v for vs in cells.values() for v in vs)
    assert "e+" not in text and "e-0" not in text


def test_plain_value_is_what_a_person_writes():
    assert cfgmod.plain_value(-99000900.0) == "-99,000,900"
    assert cfgmod.plain_value(-9999) == "-9,999" and cfgmod.plain_value(0.35) == "0.35"
    assert "e" not in cfgmod.plain_value(-9.90009e7) and "e" not in cfgmod.plain_value(1.5e-7)


# ---- a category answered Missing: (marked missing)


def test_a_category_answered_missing_puts_its_codes_in_marked_missing(tmp_path, monkeypatch):
    x, b = _set_up(tmp_path, monkeypatch)
    wb = load_workbook(b)
    assert treat_odd(wb, INST, "Missing")
    wb.save(b)
    _answer(b)
    assert book.run(b).ok
    cfg, res = _engine(b, x)
    g = _grid(res, cfg, INST)
    assert engine.MISSING_RULE_LABEL in g.dim_labels
    assert not [lb for lb in g.dim_labels if "99" in str(lb)]           # the code is no category of its own
    assert g.cell(engine.ALL, engine.MISSING_RULE_LABEL).rows == _count(x, INST, lambda v: v == CODE)


# ---- Control: "Treat values ≤ -99,000,000 as missing in every column?"


def test_control_asks_the_codes_question_in_the_firms_words():
    s = next(s for s in control.load_settings() if s.key == book.BUREAU)
    assert s.question == "Treat values ≤ -99,000,000 as missing in every column?"
    assert [o.label for o in s.options] == ["Yes", "No"] and s.optional


def test_control_yes_makes_every_columns_codes_missing_and_the_run_counts_them(tmp_path, monkeypatch):
    x, b = _set_up(tmp_path, monkeypatch)
    _answer(b, odd=False)                                   # no Treat as answered on Columns at all
    _control(b, book.BUREAU, "Yes")
    ran = book.run(b)
    assert ran.ok, ran.lines
    n_inst, n_hist = _count(x, INST, lambda v: v <= -99e6), _count(x, HIST, lambda v: v <= -99e6)
    assert (n_inst, n_hist) == (60, 38)
    line = next(ln for ln in ran.lines if "treated as missing (Control)" in ln)
    assert f"{INST} on {n_inst} loans" in line and f"{HIST} on {n_hist} loans" in line
    assert "FICO" not in line                              # FICO's -9999 is nowhere near the line
    assert f"{INST} on {n_inst} loans" in _log_text(b)
    cfg, res = _engine(b, x)
    assert cfg.missing[INST].at_or_below == cfg.missing[HIST].at_or_below == cfgmod.BUREAU_CODE_LINE
    g = _grid(res, cfg, INST)
    assert g.cell(engine.ALL, engine.MISSING_RULE_LABEL).rows == n_inst
    assert engine.MISSING_RULE_LABEL in g.dim_labels and not [lb for lb in g.dim_labels if "99" in str(lb)]
    # Columns says Control answered them, and nothing is left to answer on them
    cells = _odd_cells(b)
    assert cells[INST][0].endswith(book.BUREAU_WORDS) and cells[HIST][0].endswith(book.BUREAU_WORDS)


def test_control_no_or_blank_changes_nothing(tmp_path, monkeypatch):
    x, b = _set_up(tmp_path, monkeypatch)
    _answer(b, odd=False)
    for said in ("No", None):
        _control(b, book.BUREAU, said)
        ran = book.run(b)
        assert ran.ok, ran.lines
        assert not [ln for ln in ran.lines if "treated as missing (Control)" in ln]
        cfg, res = _engine(b, x)
        assert INST not in cfg.missing and HIST not in cfg.missing
        assert engine.MISSING_RULE_LABEL not in _grid(res, cfg, INST).dim_labels
        assert not [v for vs in _odd_cells(b).values() for v in vs if book.BUREAU_WORDS in v]


def test_a_column_answered_real_keeps_its_codes_whatever_control_says(tmp_path, monkeypatch):
    x, b = _set_up(tmp_path, monkeypatch)
    wb = load_workbook(b)
    treat_odd(wb, INST, "Real")
    wb.save(b)
    _answer(b, odd=False)
    _control(b, book.BUREAU, "Yes")
    assert book.run(b).ok
    cfg, _ = _engine(b, x)
    assert INST not in cfg.missing and cfg.missing[HIST].at_or_below == cfgmod.BUREAU_CODE_LINE


# ---- never in a calculation: band cuts and Look's percentiles


def test_codes_are_left_out_of_band_cuts_and_looks_percentile_lines(tmp_path, monkeypatch):
    x, b = _set_up(tmp_path, monkeypatch)
    _answer(b, odd=False)
    _control(b, book.BUREAU, "Yes")
    assert book.run(b).ok
    cfg, res = _engine(b, x)
    edges = next(bd for bd in cfg.bands if bd.field == HIST).edges or engine.cut_edges(
        [v for v in (engine.classify_number(r[HIST], cfg.missing[HIST])[0] for r in book.read_table(x).rows)
         if v is not None], 5, "quantile")
    assert edges and min(edges) >= 0
    g = _grid(res, cfg, band=HIST)
    assert not [lb for lb in g.band_labels if "99,000" in str(lb) or "e+" in str(lb)]
    assert engine.MISSING_RULE_LABEL in g.band_labels
    # Look's five percentile lines, from the values the Run reads: the codes left out
    real = sorted(v for v in (float(r[HIST]) for r in csv.DictReader(open(x, encoding="utf-8"))) if v > -99e6)
    shape = look.shape_of(book.read_table(x), HIST, None, cfg.missing[HIST])
    assert shape.pcts == look.percentiles(real) and min(shape.pcts) >= 0
    assert shape.marked == _count(x, HIST, lambda v: v <= -99e6)
    # and without the rule the same code would pull P10 far below zero: the check can fail
    assert look.shape_of(book.read_table(x), HIST, None, None).values[0] < 0
