"""The command line: each command runs, refuses plainly, and will not run on
a judgement nobody stated."""
import pytest

from conftest import DATA
from threshold_engine.cli import main

MEASURE = ["--name", "Card net charge-offs", "--unit", "%", "--direction", "higher_is_worse",
           "--frequency", "quarterly", "--smoothing", "1"]
SCALE = ["--floor-at-zero", "yes", "--moderate-halfwidth", "0.5", "--low-step", "1.0",
         "--high-z", "2.5", "--on-the-line", "worse"]


def test_evidence_reports_on_the_workbooks_scale(capsys):
    assert main(["evidence", str(DATA / "cards_nco_ttm.csv")] + MEASURE + SCALE) == 0
    out = capsys.readouterr().out
    assert "on the workbook's scale" in out and "High z 2.5" in out
    assert "lines 3.066 / 3.393 / 4.047 / 5.972" in out       # scenario C: 2008 run left out


def test_a_refusal_exits_non_zero_and_says_why(tmp_path, capsys):
    bad = tmp_path / "gap.csv"
    bad.write_text("date,value\n2020-03-31,1\n2020-09-30,2\n", encoding="utf-8")
    assert main(["evidence", str(bad)] + MEASURE + SCALE) == 2
    assert "REFUSED" in capsys.readouterr().err


@pytest.mark.parametrize("drop", ["--high-z", "--low-step", "--on-the-line"])
def test_every_scale_setting_must_be_stated(drop):
    i = SCALE.index(drop)
    with pytest.raises(SystemExit):
        main(["evidence", str(DATA / "cards_nco_ttm.csv")] + MEASURE + SCALE[:i] + SCALE[i + 2:])


def test_the_old_cutoffs_command_is_gone():
    with pytest.raises(SystemExit):
        main(["cutoffs", str(DATA / "cards_nco_ttm.csv")] + MEASURE)


def test_the_workbook_command_writes_a_workbook(tmp_path, capsys):
    out = tmp_path / "t.xlsx"
    rc = main(["workbook", str(out), "--series", "Credit card=%s" % (DATA / "cards_nco_ttm.csv")]
              + MEASURE + SCALE + ["--percentiles", "50", "75", "90", "95", "--horizon", "4",
                                   "--min-history", "41"])
    assert rc == 0 and out.exists() and "163 quarters" in capsys.readouterr().out


def test_a_badly_formed_series_argument_is_refused(tmp_path, capsys):
    rc = main(["workbook", str(tmp_path / "t.xlsx"), "--series", "no-equals-sign"]
              + MEASURE + SCALE + ["--percentiles", "50", "--horizon", "4", "--min-history", "41"])
    assert rc == 2 and "LABEL=FILE" in capsys.readouterr().err


PROFILE = ["--name", "Mortgage net charge-offs", "--unit", "%", "--direction",
           "higher_is_worse", "--frequency", "quarterly", "--smoothing", "1"]


def test_a_profile_takes_no_judgement_settings(capsys):
    assert main(["profile", str(DATA / "mortgage_nco_ttm.csv")] + PROFILE) == 0
    out = capsys.readouterr().out
    assert "SPELLS WORSE THAN THE MEDIAN (0.122%)" in out
    assert "PERCENTILES WITHOUT THE LARGEST SPELL" in out


def test_a_profile_refuses_a_judgement_setting():
    with pytest.raises(SystemExit):
        main(["profile", str(DATA / "mortgage_nco_ttm.csv")] + PROFILE + ["--high-z", "2.5"])
