"""Dated outcomes (NEXT-GOAL 3.13, 3.14): months on book, months to bad, and the
outcome window, each checked against dates counted by hand.

The window: bad means bad in a loan's first N months on book. A loan under N
months on book hasn't had its N months and is left out, counted; a bad loan that
went bad later is good for the run. Without an outcome date the window is
refused, naming what is missing. The plain loan age filter keeps working for a
book with no outcome date: it is an age filter, not a window."""

from datetime import date
from pathlib import Path

import pytest

from conftest import cube, row, table
from origination_cube import config as cfgmod
from origination_cube import engine, prespec

AS_OF = "2026-06-30"


def dated(rows, dates):
    """Each row given (origination date, outcome date)."""
    for r, (made, went) in zip(rows, dates):
        r["ORIG"], r["BADD"] = made, went
    return rows


def windowed(n=12, **kw):
    return cube(window_months=n, origination_date="ORIG", outcome_date="BADD", **{"as_of": AS_OF, **kw})


def six():
    """The conftest book, dated: loan 1 went bad in month 4, loan 5 in month 23."""
    return dated([row(1, 600, "A", 100, 1, 50), row(2, 600, "A", 100, 0, 0), row(3, 700, "A", 200, 0, 0),
                  row(4, 700, "B", 200, 0, 0), row(5, 600, "B", 400, 1, 100), row(6, 700, "B", 1000, 0, 0)],
                 [("2022-01-15", "2022-05-01"), ("2022-06-30", ""), ("2025-12-01", ""), ("2023-07-01", ""),
                  ("2022-03-03", "2024-01-10"), ("2021-01-01", "")])


def test_months_are_whole_calendar_months():
    m = engine.months_between
    assert m(date(2024, 1, 15), date(2025, 7, 14)) == 17
    assert m(date(2024, 1, 15), date(2025, 7, 15)) == 18
    assert m(date(2024, 6, 30), date(2026, 6, 30)) == 24
    assert m(date(2024, 7, 1), date(2026, 6, 30)) == 23


def test_the_window_counts_bad_within_n_months_and_later_bad_as_good():
    res = engine.run(windowed(12), table(six()))
    d = res.dates
    # loan 3 is 6 months on book at 2026-06-30: left out. Loan 5 went bad 22 months in: good, in a 12-month window
    assert res.rows == 5 and res.aged_out == 1
    assert d.left_out == {"under 12 months on book": 1} and d.bad_after_window == 1
    out = res.total.rates["outcome_loans"]
    assert (out.num, out.units) == (1.0, 5)
    # only the yes/no outcome is windowed: loan 5's GCO is as the extract has it
    assert res.total.rates["gco_rate"].num == 150.0
    assert (d.first, d.last) == (date(2021, 1, 1), date(2023, 7, 1))
    assert d.window == 12 and d.as_of == date(2026, 6, 30) and d.as_of_from == "as given"


def test_the_window_ends_at_the_n_month_anniversary():
    rows = dated([row(i, 600, "A", 100, 1, 10) for i in range(4)],
                 [("2024-01-15", "2025-01-14"), ("2024-01-15", "2025-01-15"),   # 11 months: in; 12: out
                  ("2024-01-15", "2024-01-15"), ("2024-01-15", "2025-02-01")])  # made and bad the same day: in
    res = engine.run(windowed(12), table(rows))
    assert res.total.rates["outcome_loans"].num == 2.0 and res.dates.bad_after_window == 2
    # a loan exactly N months on book has had its N months, and stays
    rows = dated([row(1, 600, "A", 100, 0, 0), row(2, 600, "A", 100, 0, 0)],
                 [("2025-06-30", ""), ("2025-07-01", "")])
    res = engine.run(windowed(12), table(rows))
    assert res.rows == 1 and res.dates.left_out == {"under 12 months on book": 1}


def test_every_date_problem_is_left_out_and_counted_by_why():
    rows = dated([row(i, 600, "A", 100, bad, 0) for i, bad in enumerate((1, 1, 0, 1, 0, 0, 1))],
                 [("2022-01-01", ""),                   # bad, no outcome date
                  ("2022-01-01", "2021-12-01"),         # went bad before it was made
                  ("2022-01-01", "2023-01-01"),         # an outcome date on a loan that isn't bad
                  ("2022-01-01", "2026-07-15"),         # went bad after the as-of date
                  ("2026-08-01", ""),                   # made after the as-of date
                  ("not a date", ""),                   # no readable origination date
                  ("2022-01-01", "2022-03-01")])        # fine: bad in month 2
    res = engine.run(windowed(12), table(rows))
    assert res.dates.left_out == {"bad, with no readable outcome date": 1, "went bad before it was made": 1,
                                  "an outcome date on a loan that isn't bad": 1, "went bad after the as-of date": 1,
                                  "made after the as-of date": 1, "no readable origination date": 1}
    assert res.rows == 1 and res.aged_out == 6
    assert any(w.startswith("outcome window: bad means bad in the first 12 months") for w in res.warnings)


def test_a_named_outcome_value_is_windowed_too():
    rows = dated([dict(row(i, 600, "A", 100, 0, 0), STATUS=s) for i, s in enumerate(("CO", "CO", "OK"))],
                 [("2022-01-01", "2022-06-01"), ("2022-01-01", "2024-06-01"), ("2022-01-01", "")])
    res = engine.run(windowed(12, outcome={"field": "STATUS", "is": "CO"}), table(rows))
    assert res.total.rates["outcome_loans"].num == 1.0 and res.dates.bad_after_window == 1


def test_seasoned_loans_say_how_much_of_the_loss_the_window_catches():
    # 6-month window: seasoned at 12 months on book. Four seasoned bad loans, gone bad in months 3, 5, 9 and 21
    made = "2024-01-10"
    rows = dated([row(i, 600, "A", 100, 1, g) for i, g in enumerate((10, 20, 30, 40))] +
                 [row(9, 600, "A", 100, 0, 0), row(10, 600, "A", 100, 1, 99)],
                 [(made, "2024-03-20"), (made, "2024-05-20"), (made, "2024-09-20"), (made, "2025-09-20"),
                  (made, ""), ("2025-12-01", "2026-01-15")])          # the last is 6 months on book: not seasoned
    res = engine.run(windowed(6), table(rows))
    d = res.dates
    assert d.seasoned_at == 12 and d.seasoned_loans == 5
    assert (d.seasoned_bad, d.seasoned_bad_by) == (4, 2)
    assert (d.seasoned_gco, d.seasoned_gco_by) == (100.0, 30.0)
    assert sorted(d.seasoned_months_to_bad) == [2, 4, 8, 20]


def test_as_of_latest_is_the_latest_origination_or_outcome_date():
    res = engine.run(windowed(12, as_of="latest"), table(six()))
    assert res.dates.as_of == date(2025, 12, 1) and "latest" in res.dates.as_of_from
    rows = six()
    rows[1]["BADD"], rows[1]["BAD"] = "2026-02-02", 1           # an outcome date later than every loan made
    res = engine.run(windowed(12, as_of="latest"), table(rows))
    assert res.dates.as_of == date(2026, 2, 2)


def test_dates_that_read_two_ways_are_refused_not_read_one_way():
    rows = dated(six(), [(f"0{m}/0{m + 1}/2022", "") for m in range(1, 7)])
    for r in rows:
        r["BAD"] = 0
    with pytest.raises(engine.DataRefused, match=r"`ORIG` .* read two ways: 01/02/2022 is .* or "):
        engine.run(windowed(12), table(rows))


def test_the_window_is_refused_without_its_dates_naming_each():
    with pytest.raises(cfgmod.ConfigError, match=r"needs the date each loan went bad: mark that column "
                                                 r"`means: outcome_date`"):
        cube(window_months=12, origination_date="ORIG", as_of=AS_OF)
    with pytest.raises(cfgmod.ConfigError, match="needs to know when each loan was made"):
        cube(window_months=12, outcome_date="BADD", as_of=AS_OF)
    with pytest.raises(cfgmod.ConfigError, match="needs the as-of date"):
        cube(window_months=12, outcome_date="BADD", origination_date="ORIG")


def test_an_outcome_date_needs_the_window_said():
    """Bad as the extract has it and bad within a window are different questions: whose call it is, not ours."""
    with pytest.raises(cfgmod.ConfigError, match="an outcome date .* is marked, so say what bad means"):
        cube(outcome_date="BADD")
    assert cube(outcome_date="BADD", window_months=0).window_months == 0


def test_the_age_filter_and_the_window_together_are_refused():
    with pytest.raises(cfgmod.ConfigError, match="both leave out young loans"):
        windowed(12, min_age_months=24)


def test_the_plain_age_filter_still_works_without_an_outcome_date():
    rows = six()
    for r in rows:
        del r["BADD"]
    res = engine.run(cube(min_age_months=24, origination_date="ORIG", as_of=AS_OF), table(rows))
    assert res.rows == 5 and res.dates.window == 0 and res.dates.left_out == {"under 24 months on book": 1}
    assert res.total.rates["outcome_loans"].num == 2.0          # an age filter: bad at any time still counts


def test_a_date_that_is_not_a_real_day_is_a_plain_refusal(tmp_path):
    """Found by another agent: `as_of: 2026-13-01` made config.load raise a bare ValueError."""
    from conftest import BASE
    import yaml
    text = yaml.safe_dump({**BASE, "min_age_months": 12, "origination_date": "ORIG"}, sort_keys=False)
    p = tmp_path / "cube.yaml"
    p.write_text(text + "as_of: 2026-13-01\n", encoding="utf-8")
    with pytest.raises(cfgmod.ConfigError) as exc:
        cfgmod.load(p)
    line = len(text.splitlines()) + 1
    assert f"line {line}: 2026-13-01 isn't a real date" in str(exc.value)
    with pytest.raises(cfgmod.ConfigError, match="`as_of: 2026-02-30` isn't a real date"):
        cube(min_age_months=12, origination_date="ORIG", as_of="2026-02-30")


def test_one_column_per_date_role():
    """Which of two origination dates the window counts from is not a guess to make."""
    from conftest import BASE
    raw = {k: v for k, v in BASE.items() if k not in cfgmod.CORE}
    raw.update(columns_confirmed=True, columns={"ID": "key", "BAL": "booked", "BAD": "outcome", "GCO": "gco",
                                                "RANR": "ranr", "D1": "origination_date", "D2": "origination_date"})
    with pytest.raises(cfgmod.ConfigError, match="at most one column that means origination_date; found 2: D1, D2"):
        cfgmod.parse(raw)


def test_cube_init_finds_the_outcome_date_and_asks_for_the_window(tmp_path):
    from origination_cube import profile, synth
    from origination_cube.ingest import read_table
    x = synth.write_extract(tmp_path, n=2000, dated=True)
    path, _, _ = profile.write_cube_file(read_table(x), tmp_path / "cube.yaml")
    text = path.read_text(encoding="utf-8")
    assert "BAD_DATE:" in text and "{means: outcome_date}" in text
    assert 'window_months: "[CONFIRM: outcome window: bad means it went bad within? Pick 0 / 12 / 18 / 24' in text
    # an outcome date is blank on every loan that didn't go bad: that is what it is, not something to look at
    assert "BAD_DATE: 9" not in text and "BAD_DATE:" in text
    with pytest.raises(cfgmod.ConfigError, match="`window_months` still reads"):
        cfgmod.load(path)


def test_the_window_is_the_pre_specs_window():
    """3.15 will compare the run with the pre-spec: the window is the same number under the same name."""
    ps = prespec.load(Path(__file__).parents[1] / "docs" / "prespec-example.yaml")
    cfg = windowed(ps.window_months)
    assert not [x for x in prespec.deviations(ps, {"window_months": cfg.window_months}) if "window" in x]
    assert any("outcome window is 12 months" in x for x in prespec.deviations(ps, {"window_months": 12}))
