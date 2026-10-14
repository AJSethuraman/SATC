"""compare: two series of one measure matched by calendar quarter, the
differences stated as facts (the Fed kept as a cross-check, 13 Oct 2026)."""
import pytest

from conftest import DATA
from threshold_engine.cli import main
from threshold_engine.compare import by_quarter, compare
from threshold_engine.series import Point


def test_first_day_and_quarter_end_meet_in_one_quarter():
    a = [Point("2020-01-01", 1.0), Point("2020-04-01", 2.0), Point("2020-07-01", 3.0)]
    b = [Point("2020-06-30", 1.5), Point("2020-09-30", 2.0), Point("2020-12-31", 9.0)]
    c = compare(a, b, "fed", "fdic")
    assert [r[0] for r in c["rows"]] == ["2020Q2", "2020Q3"]
    assert c["rows"] == [("2020Q2", 2.0, 1.5, 0.5), ("2020Q3", 3.0, 2.0, 1.0)]
    assert c["mean"] == pytest.approx(0.75) and c["max_abs"] == 1.0 and c["max_at"] == "2020Q3"
    assert c["only_a"] == ["2020Q1"] and c["only_b"] == ["2020Q4"]


def test_two_values_in_a_quarter_and_no_overlap_are_refused():
    with pytest.raises(ValueError, match="two values in 2020Q1"):
        by_quarter([Point("2020-01-31", 1.0), Point("2020-02-29", 1.0)], "m")
    with pytest.raises(ValueError, match="share no quarter"):
        compare([Point("2020-03-31", 1.0)], [Point("2021-03-31", 1.0)])


def test_the_command_prints_facts_and_refuses_cleanly(capsys, tmp_path):
    f = DATA / "cards_nco_ttm.csv"
    assert main(["compare", str(f), str(f), "--every"]) == 0
    out = capsys.readouterr().out
    assert "mean difference +0.000" in out and "largest 0.000" in out
    bad = tmp_path / "x.csv"
    bad.write_text("date,value\n2001-03-31,1\n", encoding="utf-8")
    assert main(["compare", str(f), str(bad)]) == 0
    other = tmp_path / "y.csv"
    other.write_text("date,value\n1900-03-31,1\n", encoding="utf-8")
    assert main(["compare", str(f), str(other)]) == 2
