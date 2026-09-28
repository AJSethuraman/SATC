"""Codex's review of #394 when it was marked ready, 28 Sep 2026: three ways a value that is not a number, or two
columns with one name, got into a Run without a word. Each is now refused or read as non-numeric."""

from __future__ import annotations

import copy
import math

import openpyxl
import pytest

from conftest import BASE
from pocketbook import config as cfgmod
from pocketbook.ingest import Bad, parse_number, read_table


@pytest.mark.parametrize("v", ["NaN", "nan", "Infinity", "-inf", "1e9999", "(1e9999)", float("nan"),
                               float("inf"), -float("inf")])
def test_a_value_that_is_not_a_finite_number_reads_as_non_numeric(v):
    """NaN or Infinity in an extract (or a number too big for a float) is counted as unreadable, never put in a
    band or a sum."""
    got = parse_number(v)
    assert isinstance(got, Bad) and got.reason == "non-numeric"


def test_finite_numbers_still_read():
    assert parse_number("(1,250.50)") == -1250.5 and parse_number("3") == 3.0 and parse_number(7) == 7.0
    assert all(math.isfinite(parse_number(x)) for x in ("1e300", "-0", "0.000001"))


def test_a_csv_with_two_columns_of_one_name_is_refused(tmp_path):
    """Read as rows, the second BAL would quietly replace the first in every loan."""
    f = tmp_path / "book.csv"
    f.write_text("ID,BAL,BAD, BAL\n1,100,0,999\n", encoding="utf-8")
    with pytest.raises(ValueError, match="two columns called BAL"):
        read_table(f)


def test_an_xlsx_with_two_columns_of_one_name_is_refused(tmp_path):
    f = tmp_path / "book.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID", "GCO ", "BAD", "GCO"])
    ws.append([1, 5, 0, 7])
    wb.save(f)
    with pytest.raises(ValueError, match="two columns called GCO"):
        read_table(f)


def test_unnamed_columns_are_left_alone(tmp_path):
    f = tmp_path / "book.csv"
    f.write_text("ID,BAL,,\n1,100,,\n", encoding="utf-8")
    assert read_table(f).columns == ["ID", "BAL", "", ""]


@pytest.mark.parametrize("where, bad", [("edge", float("nan")), ("edge", float("inf")),
                                        ("worse_at", float("nan")), ("worse_at", float("inf"))])
def test_a_setting_of_nan_or_infinity_is_refused(where, bad):
    """YAML reads .nan and .inf as numbers. A NaN band edge slipped past "must rise"; a NaN worse-at made every
    comparison false, so a worse pocket read as better."""
    raw = copy.deepcopy(BASE)
    if where == "edge":
        raw["bands"] = [{"name": "score", "field": "SCORE", "edges": [650, bad]}]
    else:
        raw["benchmark"]["worse_at"] = bad
    with pytest.raises(cfgmod.ConfigError):
        cfgmod.parse(raw)
