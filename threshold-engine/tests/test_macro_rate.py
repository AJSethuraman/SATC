"""The ratings: percentiles in a series' own history, changes counted as FRED counts
them, the October 2025 gap never filled, and nothing rated without the firm's settings."""
import datetime

import pytest

from threshold_engine.macro import pull as P
from threshold_engine.macro import rate as R
from threshold_engine.macro.catalog import DERIVED_BY_KEY, HIGHER, LOWER, RATED
from threshold_engine.macro.settings import NOT_RATED, Refused, check, readings_of

from test_macro_settings import answered


def test_percentile_is_the_share_at_or_beyond_in_the_direction_of_stress():
    ordered = [1.0, 2.0, 2.0, 3.0]
    assert R.percentile(2.0, ordered, HIGHER) == 75.0      # at or above 3 of 4
    assert R.percentile(2.0, ordered, LOWER) == 75.0       # at or below 3 of 4
    assert R.percentile(3.0, ordered, HIGHER) == 100.0     # a record is 100%
    assert R.percentile(3.0, ordered, LOWER) == 25.0


def test_a_reading_on_a_cutoff_takes_the_side_the_firm_chose():
    cut = [50.0, 75.0, 90.0, 95.0]
    assert R.rating(75.0, cut, "worse") == 3
    assert R.rating(75.0, cut, "better") == 2
    assert R.rating(49.9, cut, "worse") == 1 and R.rating(100.0, cut, "better") == 5


def _monthly(values, start=(2024, 1)):
    y, m = start
    out = []
    for v in values:
        out.append(("%04d-%02d-01" % (y, m), v))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def test_a_missing_month_has_no_change_and_none_a_year_later_and_nothing_is_filled():
    pts = _monthly([4.0] * 12 + [4.5, None, 5.0] + [5.0] * 10)
    ch = dict(R.changes(pts, 12, "monthly", "points"))
    assert ch["2025-01-01"] == 0.5
    assert "2025-02-01" not in ch                      # the month itself has no value
    assert "2026-02-01" not in ch                      # nor does the month a year on
    assert ch["2025-03-01"] == 1.0


def test_a_change_in_percent_is_of_the_earlier_reading():
    pts = _monthly([200.0] + [None] * 11 + [210.0])
    assert R.changes(pts, 12, "monthly", "percent") == [("2025-01-01", 5.0)]


def test_a_weekly_change_counts_52_weeks_so_a_holiday_week_matches_fred():
    # Freddie Mac's 30-year rate around Thanksgiving: the 2004 release moved to
    # Wednesday 24 Nov. FRED's change from a year ago is -0.17, against 28 Nov 2003.
    pts = [("2003-11-21", 5.83), ("2003-11-28", 5.89), ("2004-11-18", 5.74), ("2004-11-24", 5.72)]
    assert dict(R.changes(pts, 12, "weekly", "points"))["2004-11-24"] == pytest.approx(-0.17)


def test_a_daily_change_is_against_the_same_weekday_and_a_holiday_has_none():
    day = datetime.date(2025, 7, 4)                     # a Friday; 52 weeks later, 3 Jul 2026
    later = day + datetime.timedelta(weeks=52)
    pts = [(day.isoformat(), None), ((day + datetime.timedelta(days=-1)).isoformat(), 4.0),
           ((later - datetime.timedelta(days=1)).isoformat(), 4.5), (later.isoformat(), 4.6)]
    pts.sort()
    ch = dict(R.changes(pts, 12, "daily", "points"))
    assert later.isoformat() not in ch                 # the year-earlier day had no reading
    assert ch[(later - datetime.timedelta(days=1)).isoformat()] == 0.5


def test_sahm_reproduces_fred_across_the_october_2025_gap():
    # UNRATE and SAHMCURRENT from FRED, read 15 Oct 2026. October 2025 has no
    # value; FRED averages the two months it has, and so does the tool.
    unrate = _monthly([3.7, 3.9, 3.9, 3.9, 3.9, 4.1, 4.2, 4.2, 4.1, 4.1, 4.2, 4.1,
                       4.0, 4.2, 4.2, 4.2, 4.3, 4.1, 4.3, 4.3, 4.4, None, 4.5, 4.4,
                       4.3, 4.4, 4.3, 4.3, 4.3, 4.2, 4.1, 4.1, 4.2])
    fred = {"2025-09": 0.23, "2025-10": 0.25, "2025-11": 0.35, "2025-12": 0.35, "2026-01": 0.30,
            "2026-02": 0.27, "2026-03": 0.20, "2026-04": 0.13, "2026-05": 0.10, "2026-06": 0.07,
            "2026-07": -0.03, "2026-08": -0.07, "2026-09": 0.00}
    mine = {d[:7]: round(v, 2) for d, v in R.sahm(unrate)}
    assert {k: mine[k] for k in fred} == fred
    assert "2025-01" not in mine                        # needs 12 months of averages before it


def test_the_history_window_ends_at_the_latest_reading():
    dated = [("2000-01-01", 1.0), ("2016-09-01", 2.0), ("2016-10-01", 3.0), ("2026-09-01", 4.0)]
    assert R.in_window(dated, "full") == dated
    assert [d for d, _ in R.in_window(dated, {"years": 10})] == ["2016-10-01", "2026-09-01"]


def test_house_prices_against_income_need_every_month_of_the_quarter():
    hpi = [("2026-01-01", 700.0), ("2026-04-01", 720.0)]
    income = [("2026-01-01", 69000.0), ("2026-02-01", 70000.0), ("2026-03-01", 71000.0),
              ("2026-04-01", 72000.0), ("2026-05-01", None), ("2026-06-01", 72000.0)]
    got = R.derive(DERIVED_BY_KEY["house_price_to_income"], {"house_prices": hpi, "income_per_person": income})
    assert got == [("2026-01-01", 10.0), ("2026-04-01", None)]


def test_the_mortgage_spread_uses_the_same_day_or_the_week_before_and_no_older():
    rate = [("2026-10-01", 7.28), ("2026-10-08", 7.40), ("2026-10-15", 7.50)]
    tsy = [("2026-09-24", 4.9), ("2026-09-30", 5.00), ("2026-10-08", 5.21)]
    got = R.derive(DERIVED_BY_KEY["mortgage_spread"], {"mortgage_rate": rate, "treasury_10y": tsy})
    assert got == [("2026-10-01", pytest.approx(2.28)), ("2026-10-08", pytest.approx(2.19)),
                   ("2026-10-15", None)]           # the last yield is 7 days old


# -- end to end, from a pull on disk ---------------------------------------

def _dates(freq, start, end):
    d, out = start, []
    while d <= end:
        if freq != "daily" or d.weekday() < 5:
            out.append(d)
        if freq == "monthly":
            d = (d.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        else:
            d += datetime.timedelta(days=7 if freq == "weekly" else 1)
    return out


def _fetcher():
    start, end = datetime.date(2000, 1, 1), datetime.date(2026, 9, 30)

    def csv(sid, freq, first, value):
        rows = ["observation_date,%s" % sid]
        for i, d in enumerate(_dates(freq, first, end)):
            v = value(i, d)
            rows.append("%s,%s" % (d.isoformat(), "." if v is None else v))
        return ("\n".join(rows) + "\n").encode()

    def unrate(i, d):
        if d.isoformat() == "2025-10-01":
            return None                                 # FRED's "." for the lapse
        return 9.0 if d >= datetime.date(2026, 7, 1) else 4.0 + (i % 5) / 10

    series = {
        "UNRATE": ("monthly", start, unrate),
        "CPIAUCSL": ("monthly", start, lambda i, d: round(170 * 1.002 ** i, 3)),
        "MORTGAGE30US": ("weekly", datetime.date(2000, 1, 6), lambda i, d: 6 + (i % 7) / 10),
        "DGS10": ("daily", start, lambda i, d: 4 + (i % 11) / 20),
    }

    def fetch(url):
        sid = url.split("id=")[1]
        freq, first, value = series[sid]
        return csv(sid, freq, first, value)
    return fetch


@pytest.fixture
def cache(tmp_path):
    P.pull(tmp_path, keys=["unemployment", "cpi", "mortgage_rate", "treasury_10y"], today="2026-10-15",
           fetcher=_fetcher())
    return tmp_path


def _by(result, key, reading):
    return next(r for r in result["ratings"] if r["key"] == key and r["reading"] == reading)


def test_nothing_is_rated_without_a_pull(tmp_path):
    with pytest.raises(Refused, match="no pull under"):
        R.rate_all(tmp_path, check(answered()))


def test_a_record_is_rated_5_and_says_how_long_it_has_held(cache):
    s = check(answered(cutoffs=[50, 75, 90, 99.5], history="full"))
    u = _by(R.rate_all(cache, s), "unemployment", "position")
    assert u["rating"] == 5 and u["percentile"] == 100.0
    assert u["held"] == 3 and u["since"] == "2026-07-01" and u["date"] == "2026-09-01"
    assert u["readings"] == 320                         # 321 months, less October 2025: not a zero
    assert u["direction_from"] == "research" and u["history_from"] == "2000-01-01"
    assert "Sep 2026: 9 percent" in u["sentence"] and "Rated 5 since Jul 2026 (3 readings)" in u["sentence"]


def test_the_firms_direction_is_used_and_said(cache):
    s = check(answered())
    c = _by(R.rate_all(cache, s), "cpi", "change")
    assert c["direction"] == LOWER and c["direction_from"] == "firm"
    assert "at or below" in c["sentence"]


def test_every_reading_the_settings_call_for_is_rated_or_says_why_not(cache):
    s = check(answered())
    result = R.rate_all(cache, s)
    expected = {(i.key, r) for i in RATED for r in readings_of(i, s["change_for"])}
    got = {(r["key"], r["reading"]) for r in result["ratings"]} | {(x["key"], x["reading"])
                                                                  for x in result["not_rated"]}
    assert got == expected and len(result["ratings"]) + len(result["not_rated"]) == len(expected)
    why = {(x["key"], x["reading"]): x["why"] for x in result["not_rated"]}
    assert why[("gasoline", "change")].startswith("not in the pull of 2026-10-15")
    assert why[("house_price_to_income", "position")].startswith("not in the pull of 2026-10-15")
    assert ("mortgage_spread", "position") not in why   # derived from two series that are in it
    assert result["vintage"] == "2026-10-15"


def test_a_reading_the_firm_chose_not_to_rate_is_listed_not_dropped(cache):
    t = answered()
    t["directions"]["answer"]["cpi"]["change"] = NOT_RATED
    result = R.rate_all(cache, check(t))
    assert {"key": "cpi", "reading": "change", "why": "the firm chose not to rate it"} in result["not_rated"]


def test_the_sahm_reading_is_shown_only_when_asked_and_never_rated(cache):
    assert R.rate_all(cache, check(answered(show_sahm=False)))["alongside"] == []
    shown = R.rate_all(cache, check(answered(show_sahm=True)))
    (sahm,) = shown["alongside"]
    assert sahm["key"] == "unemployment" and sahm["trigger"] == 0.50 and "Shown, not rated" in sahm["sentence"]
    assert not any(r["reading"] == "sahm" for r in shown["ratings"])


def test_an_earlier_pull_can_be_rated_by_name(cache):
    P.pull(cache, keys=["unemployment"], today="2026-10-16", fetcher=_fetcher())
    s = check(answered())
    assert R.rate_all(cache, s)["vintage"] == "2026-10-16"
    assert R.rate_all(cache, s, vintage="2026-10-15")["vintage"] == "2026-10-15"
