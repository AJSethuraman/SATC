"""Dates are for the scouting pipeline, not the bleed analysis (the firm, 26 Sep
2026): "when we are doing our bleed analysis and such I don't want to hide
things from view. They are distinct." And: "Data hygiene we would already have
sorted this issue out. We wouldn't have data in the future."

So a run shows every loan in the extract. The loan age filter, the outcome
window, the as-of date and the outcome date are gone, and an old file that
still has one is refused by name, saying why, rather than quietly ignored. The
origination date stays, for the development / holdout split, and Check gives
the range of it among the loans run: a fact, which removes nothing."""

from datetime import date
from pathlib import Path

import pytest
import yaml

from conftest import BASE, cube, row, table
from origination_cube import config as cfgmod
from origination_cube import engine, prespec

WHY = "A run now shows every loan in the extract as the extract has it"
OLD_LINES = {"min_age_months": 24, "window_months": 18, "as_of": "2026-06-30", "outcome_date": "BADD"}


@pytest.mark.parametrize("key", list(OLD_LINES))
def test_an_old_cube_file_with_a_removed_line_is_refused_by_name(tmp_path, key):
    p = tmp_path / "cube.yaml"
    p.write_text(yaml.safe_dump({**BASE, key: OLD_LINES[key]}, sort_keys=False), encoding="utf-8")
    with pytest.raises(cfgmod.ConfigError) as exc:
        cfgmod.load(p)
    said = exc.value.problems
    assert len(said) == 1, said                      # one plain refusal, not "unknown line" as well
    assert said[0].startswith(f"`{key}:` is no longer read: ") and WHY in said[0]
    assert "Delete the line" in said[0] and "unknown line" not in said[0]


def test_an_old_cube_file_with_a_zero_is_refused_too():
    """`min_age_months: 0` and `window_months: 0` changed nothing, and every old file carries the first. Still
    refused: a line the run doesn't read is the silent fallback the loader exists to stop."""
    for key in ("min_age_months", "window_months"):
        with pytest.raises(cfgmod.ConfigError, match=f"`{key}:` is no longer read"):
            cube(**{key: 0})


@pytest.mark.parametrize("means", ["outcome_date", "as_of_date"])
def test_a_removed_meaning_on_columns_is_refused_by_name(means):
    raw = {k: v for k, v in BASE.items() if k not in cfgmod.CORE}
    raw.update(columns_confirmed=True, columns={"ID": "key", "BAL": "booked", "BAD": "outcome", "GCO": "gco",
                                                "RANR": "ranr", "D": means})
    with pytest.raises(cfgmod.ConfigError) as exc:
        cfgmod.parse(raw)
    assert exc.value.problems == [p for p in exc.value.problems if p.startswith(f"columns.D: `means: {means}` is no "
                                                                             f"longer read: ")]
    assert WHY in exc.value.problems[0] and "Mark the column `unused`" in exc.value.problems[0]


def test_an_old_pre_spec_with_window_months_is_refused_the_same_way(tmp_path):
    text = (Path(__file__).parents[1] / "docs" / "prespec-example.yaml").read_text(encoding="utf-8")
    p = tmp_path / "old.yaml"
    p.write_text(text + "window_months: 18\n", encoding="utf-8")
    with pytest.raises(prespec.PreSpecError) as exc:
        prespec.load(p)
    assert len(exc.value.problems) == 1, exc.value.problems
    said = exc.value.problems[0]
    assert said.startswith("`window_months:` is no longer read: the outcome window was removed")
    assert WHY in said and "unknown line" not in said


def _dated(rows, dates):
    for r, d in zip(rows, dates):
        r["ORIG"] = d
    return rows


def test_no_loan_is_left_out_for_its_age_or_its_dates():
    """Loans made last week, made after the day the data was taken, and with no date at all are all run."""
    rows = _dated([row(i, 600 + 50 * (i % 3), "AB"[i % 2], 100, i % 2, 10 * (i % 2)) for i in range(8)],
                  ["2026-09-20", "2026-09-25", "2026-09-26", "2030-01-01",     # days old, and "in the future"
                   "2021-06-30", "", "not a date", "2024-12-28"])
    res = engine.run(cube(origination_date="ORIG"), table(rows))
    assert res.rows == len(rows) == 8
    assert res.total.rates["outcome_loans"].units == 8
    assert not any("left out" in w and "month" in w for w in res.warnings)


def test_check_gets_the_range_of_origination_dates_and_how_many_have_none():
    rows = _dated([row(i, 600, "A", 100, 0, 0) for i in range(6)],
                  ["2024-12-28", "2021-06-30", "", "not a date", "2023-01-01", "2022-02-02"])
    d = engine.run(cube(origination_date="ORIG"), table(rows)).dates
    assert (d.first, d.last, d.loans, d.unreadable, d.problem) == (date(2021, 6, 30), date(2024, 12, 28), 6, 2, None)
    assert engine.run(cube(), table(rows)).dates is None         # no origination column marked: no line


def test_dates_that_read_two_ways_are_said_and_never_stop_the_run():
    rows = _dated([row(i, 600, "A", 100, 0, 0) for i in range(6)], [f"0{m}/0{m + 1}/2022" for m in range(1, 7)])
    res = engine.run(cube(origination_date="ORIG"), table(rows))
    assert res.rows == 6
    assert "`ORIG`" in res.dates.problem and "read two ways: 01/02/2022 is " in res.dates.problem


def test_a_date_that_is_not_a_real_day_is_a_plain_refusal(tmp_path):
    """Found by another agent: `as_of: 2026-13-01` made config.load raise a bare ValueError. An old file with it
    still gets words, naming the line."""
    text = yaml.safe_dump(BASE, sort_keys=False)
    p = tmp_path / "cube.yaml"
    p.write_text(text + "as_of: 2026-13-01\n", encoding="utf-8")
    with pytest.raises(cfgmod.ConfigError) as exc:
        cfgmod.load(p)
    assert f"line {len(text.splitlines()) + 1}: 2026-13-01 isn't a real date" in str(exc.value)


def test_one_column_per_date_role():
    """Which of two origination dates splits the holdout is not a guess to make."""
    raw = {k: v for k, v in BASE.items() if k not in cfgmod.CORE}
    raw.update(columns_confirmed=True, columns={"ID": "key", "BAL": "booked", "BAD": "outcome", "GCO": "gco",
                                                "RANR": "ranr", "D1": "origination_date", "D2": "origination_date"})
    with pytest.raises(cfgmod.ConfigError, match="at most one column that means origination_date; found 2: D1, D2"):
        cfgmod.parse(raw)
