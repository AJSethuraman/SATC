"""The command line: a report, a refusal, and no run on an unstated setting."""
import pytest

from conftest import DATA
from threshold_engine.cli import main

ARGS = ["--name", "Card net charge-offs", "--unit", "%", "--direction",
        "higher_is_worse", "--frequency", "quarterly", "--smoothing", "1",
        "--floor-at-zero", "yes", "--scale-points", "5", "--top-fraction", "0.75",
        "--episode-height", "0.25", "--materiality", "none", "--outlier-ratio",
        "2", "--min-other-episodes", "1"]


def test_a_report_names_its_cutoffs_and_its_data(capsys):
    assert main([str(DATA / "cards_nco_ttm.csv")] + ARGS) == 0
    out = capsys.readouterr().out
    assert "2 -> 3  at 4.498%" in out and "data sha256 " in out
    assert "not thresholds" in out


def test_a_refusal_exits_non_zero_and_says_why(capsys):
    rc = main([str(DATA / "other_consumer_as_filed_nco_ttm.csv")] + ARGS
              + ["--window", "2011-03-31", "2026-06-30"])
    assert rc == 2 and "no_episode" in capsys.readouterr().err


@pytest.mark.parametrize("drop", ["--materiality", "--direction", "--top-fraction"])
def test_every_setting_must_be_stated(drop):
    i = ARGS.index(drop)
    with pytest.raises(SystemExit):
        main([str(DATA / "cards_nco_ttm.csv")] + ARGS[:i] + ARGS[i + 2:])
