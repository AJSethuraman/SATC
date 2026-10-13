"""Stage 1: a series is checked as declared, and never repaired."""
import pytest

from conftest import quarters
from threshold_engine import Point
from threshold_engine.series import SeriesError, check, smooth


def test_a_missing_quarter_is_refused_not_filled():
    pts = quarters([1, 2, 3, 4, 5])
    del pts[2]
    with pytest.raises(SeriesError) as exc:
        check(pts, "quarterly")
    assert exc.value.code == "gap" and pts[1].date in str(exc.value)


def test_a_duplicated_quarter_is_refused():
    pts = quarters([1, 2, 3])
    with pytest.raises(SeriesError) as exc:
        check(pts + [pts[1]], "quarterly")
    assert exc.value.code == "duplicate"


def test_an_unknown_frequency_is_refused():
    with pytest.raises(SeriesError) as exc:
        check(quarters([1, 2]), "annual")
    assert exc.value.code == "frequency"


def test_order_of_input_does_not_matter():
    pts = quarters([1, 2, 3])
    assert check(list(reversed(pts)), "quarterly") == pts


def test_smoothing_drops_partial_windows_rather_than_averaging_fewer():
    out = smooth(quarters([4, 8, 12, 16, 20]), 4)
    assert [p.value for p in out] == [10.0, 14.0]
    assert out[0].date == quarters([0] * 4)[3].date


def test_no_smoothing_is_the_series_itself():
    pts = quarters([3, 1, 2])
    assert smooth(pts, 1) == pts


def test_monthly_series_are_checked_monthly():
    pts = [Point("2020-%02d-01" % m, 1.0) for m in range(1, 13)]
    assert len(check(pts, "monthly")) == 12
    with pytest.raises(SeriesError):
        check(pts, "quarterly")


@pytest.mark.parametrize("bad", ["2020-13-31", "2020-03-99", "2021-02-29", "2020-3-31", "20200331", "2020-03-31T00"])
def test_a_date_that_is_not_on_the_calendar_is_refused(bad):
    """The Codex review (13 Oct 2026): 2020-13-31 passed the step test and
    became 2020Q5 in the workbook."""
    from threshold_engine.series import SeriesError, check
    pts = [Point(bad, 1.0), Point("2021-06-30", 2.0)]
    with pytest.raises(SeriesError, match="not a calendar date written YYYY-MM-DD"):
        check(pts, "quarterly")
