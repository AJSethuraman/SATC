"""#259: a ratio on a book that does not exist is "N/A", never "OK".

Bank of New York Mellon has no credit-card book. The FDIC publishes 0.00 for
its card delinquency rate, 0.00 is a number, and the Watchlist read OK --
"checked and clean" where the truth was "nothing to check". Behaviour 6:
unknown is a third answer, drawn differently from both.

Three places have to agree, and each is pinned here: the engine's value, the
digest's status, and the workbook's formulas.
"""
from __future__ import annotations

import re

import openpyxl
import pytest

from credit_suite.engine import digest, metrics, thresholds
from credit_suite.engine.config import Threshold
from credit_suite.sources.fdic import engine_api as R
from credit_suite.sources.fdic import layout

ABOVE = Threshold(1.0, 2.0, "above")


# --------------------------------------------------------------------------
# the engine's value
# --------------------------------------------------------------------------

def test_a_direct_class_ratio_on_a_zero_book_reads_none_not_zero():
    """What the FDIC publishes (0.00) versus what is true (no book)."""
    assert R.metric_value("P3CRCDR", {"P3CRCDR": 0.0, "LNCRCD": 0}) is None
    assert R.metric_value("P3CRCDR", {"P3CRCDR": 0.0, "LNCRCD": None}) is None
    assert R.metric_value("P3CRCDR", {"P3CRCDR": 0.0, "LNCRCD": 5_000}) == 0.0
    assert R.metric_value("P3CRCDR", {"P3CRCDR": 1.7, "LNCRCD": 5_000}) == 1.7


def test_an_unguarded_direct_metric_is_untouched():
    assert R.metric_value("NCLNLSR", {"NCLNLSR": 0.0}) == 0.0


@pytest.mark.parametrize("metric,balance", [
    ("P3CRCDR", "LNCRCD"), ("NACRCDR", "LNCRCD"),        # guarded direct
    ("NTCONOTQ_BOOK", "LNCONOTH"), ("NTCIQ_BOOK", "LNCI"),       # declarative ratio
    ("P3REMULT_BOOK", "LNREMULT"), ("UNINSDEPR", "DEP"),
    ("TEXAS", None), ("CRECONR", None), ("NCLNLSR", None),
    ("P3RELOCR", None),          # HELOC: no balance is landed, so no guard
])
def test_every_metric_knows_the_book_it_stands_on(metric, balance):
    assert R.balance_field(metric) == balance


def test_the_guard_is_declared_per_class_not_per_metric():
    """Every direct class ratio whose class has a landed balance is guarded;
    the count is the denominator a reader should check against."""
    guarded = {m for m, (consumed, fn) in R.METRICS.items()
               if fn is None and len(consumed) > 1}
    expect = {m for m, cls in R.LOANBOOK_CLASS.items()
              if m in R.METRICS and R.METRICS[m][1] is None
              and cls in R.CLASS_BALANCE}
    assert guarded == expect
    assert len(guarded) == 12                      # 4 classes x 3 rates


# --------------------------------------------------------------------------
# the digest's status: three blanks, three different answers
# --------------------------------------------------------------------------

def test_no_book_is_not_applicable_and_no_number_is_blank():
    reg = R.METRICS
    assert digest.metric_status(reg, "P3CRCDR", {"P3CRCDR": 0.0, "LNCRCD": 0}, ABOVE) == "N/A"
    assert digest.metric_status(reg, "P3CRCDR", {"P3CRCDR": None, "LNCRCD": 5_000}, ABOVE) == ""
    assert digest.metric_status(reg, "P3CRCDR", {"P3CRCDR": 0.4, "LNCRCD": 5_000}, ABOVE) == "OK"
    assert digest.metric_status(reg, "P3CRCDR", {"P3CRCDR": 2.5, "LNCRCD": 5_000}, ABOVE) == "ALERT"


def test_a_declarative_ratio_gets_the_same_split():
    reg = R.METRICS
    assert digest.metric_status(reg, "NTCONOTQ_BOOK", {"NTCONOTQ": 5_318, "LNCONOTH": 0}, ABOVE) == "N/A"
    assert digest.metric_status(reg, "NTCONOTQ_BOOK", {"NTCONOTQ": None, "LNCONOTH": 3_173}, ABOVE) == ""


def test_the_third_answer_is_neither_ok_nor_blank():
    assert thresholds.NOT_APPLICABLE not in (thresholds.OK, "")
    assert thresholds.status_for(None, ABOVE) == thresholds.OK   # unchanged: the split lives above it


# --------------------------------------------------------------------------
# the workbook's formulas say the same thing
# --------------------------------------------------------------------------

def test_the_value_cell_blanks_a_guarded_ratio_on_a_zero_book():
    formula = layout.metric_formula("P3CRCDR", 1, 16)
    ref = layout._fref(1, "P3CRCDR", 16)
    bal = layout._fref(1, "LNCRCD", 16)
    assert formula == '=IF(OR(%s="",%s="",%s=0),"",%s)' % (ref, bal, bal, ref)


def test_an_unguarded_direct_keeps_the_plain_blank_guard():
    ref = layout._fref(1, "NCLNLSR", 16)
    assert layout.metric_formula("NCLNLSR", 1, 16) == '=IF(%s="","",%s)' % (ref, ref)


@pytest.fixture(scope="module")
def watchlist_helpers(tmp_path_factory):
    """The Watchlist helper formulas of a freshly built (unpopulated) workbook,
    keyed by metric id, for peer slot 1."""
    import monitorbuild
    with monitorbuild.built_monitor("fdic") as (workbook, _stdout):
        wb = openpyxl.load_workbook(workbook, keep_vba=True)
        ws = wb["Watchlist"]
        cfg = R.parse_config(list(wb["_config"].iter_rows(values_only=True)))
        r = layout.wl_row(1)
        out = {s.id: ws.cell(r, layout.WL_HELPER_COL0 + k).value
               for k, s in enumerate(cfg.series)}
        wb.close()
    return out


def test_the_watchlist_helper_says_na_when_the_book_is_zero(watchlist_helpers):
    f = watchlist_helpers["P3CRCDR"]
    bal = layout._fref(1, "LNCRCD", 16)
    assert 'IF(OR(%s="",%s=0),"N/A","")' % (bal, bal) in f
    assert re.search(r'"ALERT".*"WATCH".*"OK"', f)


def test_a_metric_with_no_book_keeps_the_plain_blank(watchlist_helpers):
    f = watchlist_helpers["TEXAS"]
    assert "N/A" not in f
    assert f.startswith('=IF(NOT(ISNUMBER(')
