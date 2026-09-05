"""S1, C3 and C5 -- the shipped artifact against its source of record.

**S1, the units defect.** ``series_seed.py`` carries a comment written the day
it was fixed::

    # MILLIONS, not billions: the Board prints 5,166,907.71 for June 2026

and the shipped ``FRED_Credit_Risk_Dashboard.xlsm`` ``_config`` tab declares
``billions $`` beside a ``TOTALSL`` of 5,166,907.71 -- three orders of
magnitude out, on the line a reader reads, with the number itself correct.
The source is fixed; the artifact a person opens is not, and
``example-output/`` is in ``.gitignore``, so nothing in version control can
tell you that.

The check is deliberately NOT "the workbook's units match the workbook's
numbers" -- that is one file agreeing with itself and it is one edit away from
being a mirror. It compares the shipped artifact, cell for cell, against
``series_seed.py``, which is the source of record. The builder already derives
``_config`` from the seed, so a freshly built workbook passes by construction;
what this catches is an artifact that is older than its source.

**C3, the vintage.** All 142 series in the shipped workbook carry
``vintage=2026-09-05``. Uniformity is the current state, so skew is new and
means part of the workbook did not refresh.

**C5, the date grid.** 142 of 142 series are regular today -- no duplicates,
no reversals, no irregular steps. Every transform downstream (``zscore_8q``,
``yoy_pct``) silently gives a wrong answer on a broken grid.

An interior HOLE -- a gap that is a whole number of steps -- is a third
answer, not a failure. ``DRTSSP`` has 19 of them and nothing in this
repository records whether the Board simply did not ask that quarter. The
design says UNKNOWN until somebody checks the SLOOS release history, so that
is what this returns.
"""
from __future__ import annotations

import openpyxl
import pytest

from credit_suite.engine import consistency as K
from credit_suite.sources.fred import consistency as C
from credit_suite.sources.fred import layout as build_workbook
from credit_suite.sources.fred import series_seed as SEED


# --------------------------------------------------------------------------
# S1 -- _config against the seed
# --------------------------------------------------------------------------

def test_the_builder_writes_a_config_that_matches_the_seed():
    result = C.config_matches_seed(build_workbook.config_rows())
    assert result.verdict == K.PASS
    assert result.examined == 142 * len(SEED.HEADER)


def test_the_denominator_is_every_cell_not_every_row():
    """A row-level comparison would report "142 of 142 series present" over a
    units column that had been rewritten."""
    result = C.config_matches_seed(build_workbook.config_rows())
    assert result.examined == 2130
    assert "2130" in result.summary()


def test_a_units_label_the_source_corrected_is_caught():
    """The shipped-workbook defect, replayed: the number stays right and the
    label goes back to what it was before 94d431f."""
    rows = [list(r) for r in build_workbook.config_rows()]
    header = None
    for row in rows:
        if row and row[0] == "series_id":
            header = row
        if header and row and row[0] == "TOTALSL":
            row[header.index("units")] = "billions $"
            break
    result = C.config_matches_seed(rows)
    assert result.verdict == K.FAIL
    assert "TOTALSL" in result.summary()
    assert "billions $" in result.summary() and "millions $" in result.summary()


def test_a_series_missing_from_the_artifact_is_caught():
    rows = [r for r in build_workbook.config_rows()
            if not (r and r[0] == "NESTHPI")]
    result = C.config_matches_seed(rows)
    assert result.verdict == K.FAIL
    assert "NESTHPI" in result.summary()


def test_a_series_the_seed_does_not_carry_is_caught():
    """Somebody added a row to the knob panel by hand. It is now a series the
    runner will pull and the seed knows nothing about."""
    rows = [list(r) for r in build_workbook.config_rows()]
    at = next(i for i, r in enumerate(rows) if r and r[0] == "series_id")
    rows.insert(at + 1, ["MADEUPQ"] + [""] * (len(SEED.HEADER) - 1))
    result = C.config_matches_seed(rows)
    assert result.verdict == K.FAIL
    assert "MADEUPQ" in result.summary()


def test_an_artifact_with_no_series_section_is_UNKNOWN_not_a_pass():
    """An older build, or a tab that did not parse. Nothing was compared, so
    there is nothing to pass."""
    result = C.config_matches_seed([["[SETTINGS]"], ["demo_mode", "FALSE"]])
    assert result.verdict == K.UNKNOWN
    assert result.examined == 0


def test_the_units_question_the_tie_out_could_not_settle_is_left_alone():
    """Two Z.1 commercial-property series where our config, FRED and the Board
    give three different answers. This check compares the artifact to the
    seed, so it takes no position on which is right -- and must not be read as
    having confirmed the seed."""
    assert C.UNRESOLVED_UNITS == ("BOGZ1FL075035403Q", "BOGZ1FL075035503Q")
    ids = {row["series_id"] for row in SEED.all_series()}
    for series_id in C.UNRESOLVED_UNITS:
        assert series_id in ids


# --------------------------------------------------------------------------
# S1 against a workbook that was actually built and opened
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def built_config(tmp_path_factory):
    base = str(tmp_path_factory.mktemp("s1") / "base.xlsx")
    build_workbook.build(base)
    wb = openpyxl.load_workbook(base)
    try:
        return [list(row) for row in wb["_config"].iter_rows(values_only=True)]
    finally:
        wb.close()


def test_the_workbook_on_disk_matches_the_seed(built_config):
    """Opened by the thing that reads it, not asserted about in the abstract."""
    result = C.config_matches_seed(built_config)
    assert (result.verdict, result.examined) == (K.PASS, 2130)


# --------------------------------------------------------------------------
# C3 -- the vintage moves forward, and moves together
# --------------------------------------------------------------------------

def test_one_vintage_across_every_series_is_the_pass():
    current = {"A": "2026-09-05", "B": "2026-09-05"}
    result = C.vintage_check(current, previous={"A": "2026-09-01",
                                                "B": "2026-09-01"})
    assert (result.verdict, result.examined) == (K.PASS, 2)


def test_a_series_that_did_not_refresh_shows_as_skew():
    """B is exactly where it was, so nothing moved backwards -- it simply did
    not move. Written the other way round at first, with B's previous vintage
    LATER than its current one, and the mutation harness found that the
    backwards rule was carrying the test: deleting the skew rule left it
    green. Two rules, two cases."""
    current = {"A": "2026-09-05", "B": "2026-08-01"}
    result = C.vintage_check(current, previous={"A": "2026-08-01",
                                                "B": "2026-08-01"})
    assert result.verdict == K.FAIL
    assert "2026-08-01" in result.summary()
    assert "backwards" not in result.summary()


def test_a_vintage_that_went_backwards_is_a_failure():
    result = C.vintage_check({"A": "2026-08-01"}, previous={"A": "2026-09-05"})
    assert result.verdict == K.FAIL
    assert "backwards" in result.summary()


def test_the_same_vintage_twice_is_not_backwards():
    """A rerun on the same day refreshes nothing new and is not a fault."""
    assert C.vintage_check({"A": "2026-09-05"},
                           previous={"A": "2026-09-05"}).verdict == K.PASS


def test_no_previous_run_to_compare_against_is_UNKNOWN():
    """The first run against a fresh workbook. Ship, and say so."""
    result = C.vintage_check({"A": "2026-09-05", "B": "2026-09-05"},
                             previous=None)
    assert result.verdict == K.UNKNOWN
    assert result.examined == 2


def test_a_block_carrying_no_vintage_at_all_is_UNKNOWN():
    result = C.vintage_check({"A": "2026-09-05", "B": None},
                             previous={"A": "2026-09-01", "B": "2026-09-01"})
    assert result.verdict == K.UNKNOWN
    assert "B" in result.summary()


def test_the_vintage_is_read_off_the_block_the_runner_writes():
    """Not a second parser: the string is the one ``block_meta`` produces."""
    from credit_suite.sources.fred import runner as R
    spec = R.SeriesSpec(series_id="TOTALSL", title="t", category="g19",
                        lane="consumer", metric_type="level",
                        frequency="monthly", sa_nsa="SA", units="millions $",
                        level_rate_index="level", geo_segment="national",
                        dashboard_capable=True, watchlist_capable=False,
                        transform="yoy_pct", alert_rule="none", notes="")
    import datetime
    meta = R.block_meta(spec, datetime.date(2026, 9, 5))
    assert C.vintage_of(meta) == "2026-09-05"
    assert C.vintage_of(R.block_meta(spec, None)) is None


# --------------------------------------------------------------------------
# C5 -- the date grid
# --------------------------------------------------------------------------

QUARTERS = ["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01",
            "2026-01-01"]


def test_a_regular_quarterly_grid_passes():
    result = C.date_grid("DRTSSP", QUARTERS, "quarterly")
    assert (result.verdict, result.examined) == (K.PASS, 5)


def test_a_duplicated_date_is_a_failure():
    dates = QUARTERS[:2] + ["2025-04-01"] + QUARTERS[2:]
    result = C.date_grid("X", dates, "quarterly")
    assert result.verdict == K.FAIL
    assert "duplicate" in result.summary()


def test_an_out_of_order_date_is_a_failure():
    dates = ["2025-01-01", "2025-07-01", "2025-04-01"]
    result = C.date_grid("X", dates, "quarterly")
    assert result.verdict == K.FAIL
    assert "order" in result.summary()


def test_a_step_that_is_not_the_declared_cadence_is_a_failure():
    """A monthly observation inside a quarterly series -- a merge fault."""
    dates = ["2025-01-01", "2025-04-01", "2025-05-01"]
    result = C.date_grid("X", dates, "quarterly")
    assert result.verdict == K.FAIL
    assert "step" in result.summary()


def test_an_interior_hole_is_UNKNOWN_rather_than_a_refusal():
    """DRTSSP has 19 of these and nothing here records whether the Board
    simply did not ask that quarter. Refusing the build on it would be the
    false alarm the design warns about."""
    dates = ["2025-01-01", "2025-04-01", "2026-01-01"]
    result = C.date_grid("DRTSSP", dates, "quarterly")
    assert result.verdict == K.UNKNOWN
    assert "hole" in result.summary()
    assert "2025-04-01" in result.summary()


def test_the_workbook_order_is_accepted_when_it_is_declared():
    """The raw blocks are written newest-first."""
    result = C.date_grid("X", list(reversed(QUARTERS)), "quarterly",
                         newest_first=True)
    assert result.verdict == K.PASS


def test_a_frequency_nobody_declared_is_UNKNOWN_not_a_pass():
    result = C.date_grid("X", QUARTERS, "fortnightly")
    assert result.verdict == K.UNKNOWN


def test_a_series_with_no_observations_reports_NONE():
    result = C.date_grid("X", [], "quarterly")
    assert (result.verdict, result.examined) == (K.NONE, 0)


def test_the_sweep_reports_the_series_count_as_its_denominator():
    grids = {"A": (QUARTERS, "quarterly"),
             "B": (["2025-01-01", "2025-02-01"], "monthly")}
    result = C.date_grid_all(grids)
    assert (result.verdict, result.examined) == (K.PASS, 2)
