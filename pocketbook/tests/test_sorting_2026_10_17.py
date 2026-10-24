"""Sorting with the filter arrows keeps each row's pocket together (the review of 17 Oct 2026).

The firm wants easy filtering, and slicers later ("slicers that get added would need to adapt"). Pockets' visible
cells find their pocket through hidden index columns; a sort that left those out moved the visible formulas and
every row worked its pocket out again where it was, so only # moved. The filter and sort range now spans every
column a row reads from, so a sort carries the index with the row, and # keeps the Run's order as a label.

Proved by sorting a built book in LibreOffice through its Python bridge (tests/unosort.py, run with the system
Python), on Pockets and on RANR vs GCOs, the other tab with filter arrows."""

from __future__ import annotations

import os
import re
import subprocess
from collections import Counter

import pytest
from openpyxl import load_workbook
from openpyxl.utils import range_boundaries

import tabs
from conftest import TEST_SHUFFLES
from pocketbook import book, choices as ch, live, perm, results, synth
from recalc import need_soffice
from test_book import _answer

HERE = os.path.dirname(__file__)
SYSTEM_PYTHON = "/usr/bin/python3"


def _need_uno():
    need_soffice()
    ok = os.path.exists(SYSTEM_PYTHON) and subprocess.run([SYSTEM_PYTHON, "-c", "import uno"],
                                                          capture_output=True).returncode == 0
    if not ok and os.environ.get("CI"):
        pytest.fail("LibreOffice's Python bridge (python3-uno) isn't installed in CI, so no sort can be proved")
    if not ok:
        pytest.skip("LibreOffice's Python bridge (python3-uno) isn't installed here")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("sorting")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("POCKETBOOK_MEMORY", str(d / "memory.yaml"))
        mp.setattr(perm, "SHUFFLES", TEST_SHUFFLES)
        x = synth.write_extract(d, n=6000, chargeoff=True, big_lines=True)
        out = book.set_up(x, choices=ch.Choices(run_kind=ch.BLEED, bands=("FICO", "ORIG_BAL"),
                                                segments=("CHANNEL", "ASSET_CLASS"), outcome="BAD_FLAG"))
        assert out.ok, out.lines
        _answer(out.book)
        assert book.run(out.book).ok
    return {"b": out.book, "d": d}


def _sort(src, out, sheet: str, ref: str, field: int, ascending: bool):
    _need_uno()
    got = subprocess.run([SYSTEM_PYTHON, os.path.join(HERE, "unosort.py"), str(src), str(out), sheet, ref,
                          str(field), "1" if ascending else "0"], capture_output=True, text=True, timeout=600)
    assert got.returncode == 0, got.stderr
    return load_workbook(out, data_only=True)[sheet]


def _rows(ws, top: int, bottom: int, first: int, last: int) -> list[tuple]:
    """Every row of a range that has something in it, its cells rounded so a save and a reload compare equal."""
    out = []
    for r in range(top, bottom + 1):
        vals = tuple(round(v, 9) if isinstance(v, float) else (None if v == "" else v)
                     for v in (ws.cell(row=r, column=c).value for c in range(first, last + 1)))
        if any(v is not None for v in vals):
            out.append(vals)
    return out


def _filter_rows(ws):
    """The filter range's data rows, below its heading, from the written sheet."""
    c0, r0, c1, r1 = range_boundaries(ws.auto_filter.ref)
    return c0, r0, c1, r1


# --------------------------------------------------------------------------
# Pockets


def test_every_cell_of_a_pockets_row_reads_only_its_own_row(built):
    """A sort moves rows, so a row's formulas may read their own row, or a fixed cell above the table, and nothing
    else on the tab; the hidden index columns too."""
    ws = load_workbook(built["b"])[results.POCKETS]
    c0, r0, c1, r1 = _filter_rows(ws)
    ref = re.compile(r"(?<![A-Za-z_'!$])\$?([A-Z]{1,3})(\$?)(\d+)\b")
    for r in range(r0 + 1, r1 + 1):
        for c in range(c0, c1 + 1):
            f = ws.cell(row=r, column=c).value
            if not (isinstance(f, str) and f.startswith("=")):
                continue
            # references into other sheets ('_list'!$A$2:$A$90, '_pockets'!...) are left out: a sort doesn't touch them
            local = re.sub(r"'[^']+'!\$?[A-Z]+\$?\d+(:\$?[A-Z]+\$?\d+)?", "", f)
            local = re.sub(r'"[^"]*"', "", local)
            for _col, fixed, row in ref.findall(local):
                assert fixed or int(row) == r, (r, c, f)


def test_sorting_pockets_by_its_p_value_keeps_each_pocket_together(built, tmp_path):
    """Sort GCOs ($) by p-value, smallest first, as the filter arrow does: every row afterwards is a row from before,
    # and all, none lost or mixed with another pocket's figures, and the p-values now run in order."""
    b = tabs.choose(built["b"], tmp_path / "gco.xlsx", results.POCKETS, measure="GCOs ($)")
    written = load_workbook(b)[results.POCKETS]
    c0, r0, c1, r1 = _filter_rows(written)
    assert c1 >= results.K_ROW and c0 <= results.K_NUM            # the hidden index travels with the row
    before_ws = tabs.calculated(b, results.POCKETS)
    before = _rows(before_ws, r0 + 1, r1, results.K_NUM, results.K_HOLDS)
    ref = f"{results.col(c0)}{r0 + 1}:{results.col(c1)}{r1}"
    after_ws = _sort(b, tmp_path / "sorted.xlsx", results.POCKETS, ref, results.K_PV - c0, True)
    after = _rows(after_ws, r0 + 1, r1, results.K_NUM, results.K_HOLDS)
    assert Counter(after) == Counter(before) and after != before
    p = [x[results.K_PV - results.K_NUM] for x in after if isinstance(x[results.K_PV - results.K_NUM], float)]
    assert p == sorted(p) and len(p) > 5
    # # is the Run's order, and stays with its pocket
    num = {x[0]: x for x in before}
    assert all(num[x[0]] == x for x in after)


def test_sorting_pockets_by_excess_keeps_each_pocket_together(built, tmp_path):
    b = tabs.choose(built["b"], tmp_path / "bad.xlsx", results.POCKETS, measure="Bad loans")
    c0, r0, c1, r1 = _filter_rows(load_workbook(b)[results.POCKETS])
    before = _rows(tabs.calculated(b, results.POCKETS), r0 + 1, r1, results.K_NUM, results.K_HOLDS)
    ref = f"{results.col(c0)}{r0 + 1}:{results.col(c1)}{r1}"
    after = _rows(_sort(b, tmp_path / "sorted.xlsx", results.POCKETS, ref, results.K_EX - c0, False),
                  r0 + 1, r1, results.K_NUM, results.K_HOLDS)
    assert Counter(after) == Counter(before) and after != before
    ex = [x[results.K_EX - results.K_NUM] for x in after if isinstance(x[results.K_EX - results.K_NUM], float)]
    assert ex == sorted(ex, reverse=True)


# --------------------------------------------------------------------------
# RANR vs GCOs, the other tab with filter arrows


def test_sorting_ranr_vs_gcos_by_gco_dollars_keeps_each_pocket_together(built, tmp_path):
    written = load_workbook(built["b"])[results.PCK]
    c0, r0, c1, r1 = _filter_rows(written)
    assert c1 >= results.C_H_BR                                    # its hidden helpers are inside the range
    before = _rows(tabs.calculated(built["b"], results.PCK), r0 + 1, r1, results.C_BAND, results.C_TOG)
    ref = f"{results.col(c0)}{r0 + 1}:{results.col(c1)}{r1}"
    after = _rows(_sort(built["b"], tmp_path / "pck.xlsx", results.PCK, ref, results.C_COST_D - c0, False),
                  r0 + 1, r1, results.C_BAND, results.C_TOG)
    assert Counter(after) == Counter(before) and after != before
    d = [x[results.C_COST_D - results.C_BAND] for x in after if isinstance(x[results.C_COST_D - results.C_BAND], float)]
    assert d == sorted(d, reverse=True) and len(d) > 5
