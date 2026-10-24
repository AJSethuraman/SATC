"""The readings: where a level sits in its own history, whether a change is inside its normal movement,
changes counted as FRED counts them, the quarters the firm leaves out taken out, the October 2025 gap never
filled, and nothing read without the firm's settings."""
import datetime

import pytest

from threshold_engine.macro import pull as P
from threshold_engine.macro import readings as R
from threshold_engine.macro.catalog import BY_KEY, CARE, CARE_DERIVED, DERIVED_BY_KEY, READ
from threshold_engine.macro.settings import Refused, check, readings_of

from test_macro_settings import answered


def test_where_a_reading_sits_is_the_share_at_or_below_it_counted_from_the_lowest():
    ordered = [1.0, 2.0, 2.0, 3.0]
    assert R.percentile(2.0, ordered) == 75.0          # at or above 3 of 4
    assert R.percentile(3.0, ordered) == 100.0         # the highest is 100%
    assert R.percentile(1.0, ordered) == 25.0


def test_normal_movement_is_the_median_change_plus_or_minus_typical_moves_and_a_spike_does_not_widen_it():
    values = [-1.0, 0.0, 0.0, 1.0, 2.0]
    med, typical, low, high = R.normal_range(values, 1.0)
    # median 0; distances 1, 0, 0, 1, 2 have median 1; one typical move is 1.4826
    assert (med, typical, low, high) == (0.0, 1.4826, -1.4826, 1.4826)
    assert R.normal_range(values[:-1] + [500.0], 1.0)[1] == typical        # a spike moves nothing
    assert R.normal_range(values, 2.0)[2:] == (-2.9652, 2.9652)


def test_a_change_on_an_edge_reads_as_moving_as_a_tie_went_to_the_warning():
    assert R.direction(1.0, -1.0, 1.0) == R.INCREASING
    assert R.direction(-1.0, -1.0, 1.0) == R.DECREASING
    assert R.direction(0.999, -1.0, 1.0) == R.STABLE


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




def test_a_quarter_left_out_is_missing_to_every_measure_and_a_change_with_an_end_in_it_is_not_counted():
    pts = _monthly([1.0] * 12 + [2.0] * 12 + [3.0] * 12, start=(2019, 1))      # 2019, 2020, 2021
    out = R.kept(pts, [["2020Q2", "2020Q2"]])
    assert [d for d, v in out if v is None] == ["2020-04-01", "2020-05-01", "2020-06-01"]
    ch = dict(R.changes(out, 12, "monthly", "points"))
    assert "2020-05-01" not in ch and "2021-05-01" not in ch                  # either end in the quarter
    assert ch["2020-07-01"] == 1.0 and ch["2021-07-01"] == 1.0
    assert R.kept(pts, []) == pts


def _series(values, start=(2000, 1)):
    return _monthly(values, start=start)


def _settings(**over):
    s = {"history": "full", "change_months": 12, "normal_width": 1.0, "left_out": [], "axis_cut": 0,
         "show_sahm": False}
    s.update(over)
    return s


def test_a_change_past_its_normal_range_reads_increasing_and_says_since_when():
    import statistics
    # A rate that wanders a little around a slow rise, then jumps for its last three months.
    vals = [5.0 + 0.1 * (i // 12) + ((i * i) % 11) / 20 for i in range(120)] + [9.0, 9.5, 10.0]
    got, why = R.describe_change(BY_KEY["unemployment"], _series(vals), _settings())
    assert why is None
    changes = [b - a for a, b in zip(vals, vals[12:])]
    med = statistics.median(changes)
    typical = 1.4826 * statistics.median(abs(c - med) for c in changes)
    assert got["median"] == pytest.approx(med) and got["typical"] == pytest.approx(typical)
    assert (got["normal_low"], got["normal_high"]) == (pytest.approx(med - typical), pytest.approx(med + typical))
    assert got["value"] == pytest.approx(changes[-1]) and got["movement"] == pytest.approx((changes[-1] - med) / typical)
    assert got["direction"] == R.INCREASING and got["held"] == 3 and got["since"] == "2010-01-01"
    assert "Increasing since Jan 2010 (3 readings)" in got["sentence"] and got["readings"] == len(changes)
    wide, _ = R.describe_change(BY_KEY["unemployment"], _series(vals), _settings(normal_width=got["movement"] + 1))
    assert wide["direction"] == R.STABLE            # the same change, inside a range wider than its move


def test_a_level_is_described_where_it_sits_with_its_lowest_and_highest():
    got, _ = R.describe_level(BY_KEY["unemployment"], _series([4.0, 5.0, 3.0, 4.5]), _settings())
    assert (got["percentile"], got["lowest"], got["highest"], got["readings"]) == (75.0, 3.0, 5.0, 4)
    assert "at or above 75.0% of the 4 readings since Jan 2000 (lowest 3, highest 5)" in got["sentence"]
    assert "rating" not in got and "direction" not in got


def test_a_latest_reading_in_a_quarter_left_out_is_said_not_read_as_current():
    vals = [4.0 + (i % 3) / 10 for i in range(30)]          # Jan 2000 to Jun 2002
    got, _ = R.describe_level(BY_KEY["unemployment"], _series(vals), _settings(left_out=[["2002Q2", "2002Q2"]]))
    assert got["date"] == "2002-03-01" and got["left_out_after"] == "2002-06-01"
    assert "Later readings, to Jun 2002, fall in quarters left out." in got["sentence"]


def test_too_little_history_or_no_typical_move_is_not_read_and_says_why():
    _, why = R.describe_change(BY_KEY["unemployment"], _series([4.0] * 13), _settings())
    assert why.startswith("only one change over 12 months")
    _, why = R.describe_change(BY_KEY["unemployment"], _series([4.0] * 14 + [4.5]), _settings())
    assert "typical move is zero" in why
    _, why = R.describe_change(BY_KEY["unemployment"], _series([4.0] * 6), _settings())
    assert why.startswith("no change over 12 months can be counted")
    _, why = R.describe_level(BY_KEY["unemployment"], _series([4.0] * 6), _settings(left_out=[["2000Q1", "2000Q2"]]))
    assert why == "the pull holds no values for it outside the quarters left out"


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


def test_wages_after_inflation_come_out_as_bls_prints_them_but_one():
    # FRED's figures, pulled 22 Oct 2026 (CIU2020000000000I, CPIAUCNS), and BLS's June 2026 Employment Cost Index
    # release, Table A, private wages and salaries, 12 months, not seasonally adjusted, as the firm photographed
    # it that day: 3.5, 3.4, 3.1 in current dollars and 0.8, 0.1, -0.4 in constant dollars (June 2025, March 2026,
    # June 2026). bls.gov itself refused to serve the page here (403).
    wages = [("2024-04-01", 167.900), ("2025-01-01", 171.900), ("2025-04-01", 173.849), ("2026-01-01", 177.672),
             ("2026-04-01", 179.304)]
    prices = [("2024-06-01", 314.175), ("2025-03-01", 319.799), ("2025-06-01", 322.561), ("2026-03-01", 330.213),
              ("2026-06-01", 333.952), ("2026-09-01", None)]
    item = DERIVED_BY_KEY["real_wages_eci"]
    real = dict(R.changes(R.derive(item, {"wages_eci_nsa": wages, "cpi_nsa": prices}), 12, "quarterly", "percent"))
    nominal = dict(R.changes(wages, 12, "quarterly", "percent"))
    assert [round(nominal[d], 1) for d in ("2025-04-01", "2026-01-01", "2026-04-01")] == [3.5, 3.4, 3.1]
    assert [round(real[d], 1) for d in ("2026-01-01", "2026-04-01")] == [0.1, -0.4]
    assert real["2025-04-01"] == pytest.approx(0.851, abs=0.001)   # BLS prints 0.8: not explained, recorded
    # a quarter whose last month has no price is left out, never filled
    got = R.derive(item, {"wages_eci_nsa": [("2026-07-01", 180.0)], "cpi_nsa": prices})
    assert got == [("2026-07-01", None)]



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


def sce(i):
    """The survey's mean in month i of the fake workbook: irregular, so its changes have a typical move."""
    return 10 + ((i * i) % 11) / 2


def hh(i, j):
    """Household debt of type j in quarter i of the fake workbook, in trillions."""
    return round((j + 1) * (1 + i / 50 + ((i * i) % 9) / 100), 4)


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
        return 9.0 if d >= datetime.date(2026, 7, 1) else 4.0 + ((i * i) % 7) / 10

    series = {
        "UNRATE": ("monthly", start, unrate),
        "CPIAUCSL": ("monthly", start, lambda i, d: round(170 * 1.002 ** i * (1 + ((i * i) % 7) / 1000), 3)),
        "MORTGAGE30US": ("weekly", datetime.date(2000, 1, 6), lambda i, d: 6 + ((i * i) % 11) / 10),
        "DGS10": ("daily", start, lambda i, d: 4 + (i % 11) / 20),
        "CAUR": ("monthly", start, lambda i, d: None if d.isoformat() == "2025-10-01" else 5 + ((i * i) % 13) / 10),
    }

    # Three shown series: one described on its level and change, one that grows (change only), and the NY
    # Fed's survey, read from its workbook. The saving rate ends on its lowest reading.
    series["PSAVERT"] = ("monthly", start, lambda i, d: 1.0 if d >= datetime.date(2026, 9, 1) else
                         5 + ((i * i) % 13) / 6)
    series["DSPIC96"] = ("monthly", start, lambda i, d: round(10000 * 1.002 ** i, 3))

    def fetch(url):
        if "hhdc-iframe" in url:
            from test_macro_sources import hhdc_page
            return hhdc_page("2026Q2")
        if "HHD_C_Report" in url:
            from test_macro_sources import hhdc_workbook
            return hhdc_workbook([("%02d:Q%d" % (3 + i // 4, i % 4 + 1), *[hh(i, j) for j in range(7)])
                                  for i in range(94)])
        if "newyorkfed.org" in url:
            from test_macro_sources import sce_workbook
            return sce_workbook([(100 * (2013 + (5 + i) // 12) + (5 + i) % 12 + 1, sce(i)) for i in range(160)])
        sid = url.split("id=")[1]
        freq, first, value = series[sid]
        return csv(sid, freq, first, value)
    return fetch


@pytest.fixture
def cache(tmp_path):
    P.pull(tmp_path, keys=["unemployment", "cpi", "mortgage_rate", "treasury_10y", "unemployment_ca"],
           today="2026-10-15", fetcher=_fetcher())
    return tmp_path


def _by(result, key, reading):
    return next(r for r in result["readings"] if r["key"] == key and r["reading"] == reading)


def test_nothing_is_read_without_a_pull(tmp_path):
    with pytest.raises(Refused, match="no pull under"):
        R.read_all(tmp_path, check(answered()))


def test_a_jump_to_a_record_reads_increasing_and_the_level_sits_at_the_top(cache):
    s = check(answered(history="full", change_months=12, normal_width=1))
    result = R.read_all(cache, s)
    u, c = _by(result, "unemployment", "position"), _by(result, "unemployment", "change")
    assert u["percentile"] == 100.0 and u["date"] == "2026-09-01" and u["readings"] == 320   # less Oct 2025
    assert u["history_from"] == "2000-01-01" and (u["lowest"], u["highest"]) == (4.0, 9.0)
    assert c["direction"] == R.INCREASING and c["since"] == "2026-07-01" and c["held"] == 3
    assert "Sep 2026: 9 percent" in u["sentence"] and "Increasing since Jul 2026 (3 readings)" in c["sentence"]


def test_every_reading_the_catalog_holds_is_read_or_says_why_not(cache):
    result = R.read_all(cache, check(answered()))
    expected = {(i.key, r) for i in READ for r in readings_of(i)}
    every = result["readings"] + result["picked"]
    missing = result["not_read"] + result["picked_not_read"]
    got = {(r["key"], r["reading"]) for r in every} | {(x["key"], x["reading"]) for x in missing}
    assert got == expected and len(every) + len(missing) == len(expected)
    # the pick-only series' readings are kept apart, so the Overview, the what-if and the printout read as before
    pick = {i.key for i in READ if getattr(i, "pick_only", False)}
    assert {x["key"] for x in result["readings"] + result["not_read"]}.isdisjoint(pick)
    assert {x["key"] for x in result["picked"] + result["picked_not_read"]} <= pick
    why = {(x["key"], x["reading"]): x["why"] for x in result["not_read"]}
    assert why[("gasoline", "change")].startswith("not in the pull of 2026-10-15")
    assert why[("house_price_to_income", "position")].startswith("not in the pull of 2026-10-15")
    assert ("mortgage_spread", "position") not in why   # derived from two series that are in it
    assert result["vintage"] == "2026-10-15" and "ratings" not in result


def test_leaving_quarters_out_changes_what_each_reading_is_measured_against(cache):
    whole = R.read_all(cache, check(answered(history="full", change_months=12)))
    less = R.read_all(cache, check(answered(history="full", change_months=12, left_out=["2026Q3"])))
    assert _by(whole, "unemployment", "position")["date"] == "2026-09-01"
    u = _by(less, "unemployment", "position")
    assert u["date"] == "2026-06-01" and u["left_out_after"] == "2026-09-01" and u["readings"] == 317
    assert less["settings"]["left_out"] == [["2026Q3", "2026Q3"]]


def test_the_sahm_reading_is_shown_only_when_asked_and_never_read_as_a_change(cache):
    assert R.read_all(cache, check(answered(show_sahm=False)))["alongside"] == []
    shown = R.read_all(cache, check(answered(show_sahm=True)))
    (sahm,) = shown["alongside"]
    assert sahm["key"] == "unemployment" and sahm["trigger"] == 0.50 and "never used to read it" in sahm["sentence"]
    assert not any(r["reading"] == "sahm" for r in shown["readings"])


def test_the_sahm_reading_leaves_out_the_quarters_every_reading_leaves_out(cache):
    # Codex on #471: the Sahm reading was worked from every month, a quarter left out included.
    whole = R.read_all(cache, check(answered(show_sahm=True)))["alongside"][0]
    less = R.read_all(cache, check(answered(show_sahm=True, left_out=["2026Q3"])))["alongside"][0]
    assert whole["date"] == "2026-09-01" and whole["value"] > 4          # the jump to 9% in 2026 Q3
    assert less["date"] == "2026-06-01" and less["value"] < 1       # July's average borrows May and June: not shown


def test_an_earlier_pull_can_be_read_by_name(cache):
    P.pull(cache, keys=["unemployment"], today="2026-10-16", fetcher=_fetcher())
    s = check(answered())
    assert R.read_all(cache, s)["vintage"] == "2026-10-16"
    assert R.read_all(cache, s, vintage="2026-10-15")["vintage"] == "2026-10-15"


def test_a_file_several_series_share_is_read_once_and_its_fingerprint_is_of_those_bytes(tmp_path):
    # Codex on #452: the Fed's file holds three series and was read once for each. A file replaced part way
    # through a run mixed two versions, and the run published only the last one's fingerprint.
    import hashlib
    from test_macro_pull import _fake
    P.pull(tmp_path, keys=["gz_spread", "excess_bond_premium"], today="2026-10-17", fetcher=_fake()[0])
    pull = R.Pull(tmp_path)
    path = pull.folder / "fed_ebp.csv"
    first = path.read_bytes()
    assert pull._get("gz_spread")[-1] == ("2026-08-01", 1.0)
    path.write_bytes(b"date,gz_spread,ebp,est_prob\n2026-09-01,9,9.9,0.9\n")     # replaced part way through
    assert pull._get("excess_bond_premium")[-1] == ("2026-08-01", 0.1)         # from the bytes read first
    assert pull.read_sha == {"fed_ebp.csv": hashlib.sha256(first).hexdigest()}


# -- the usable-with-care group: read the same way, marked as needing care ---------------------------------------

CARE_KEYS = ["unemployment", "saving_rate", "real_income", "expected_missed_payment"]


@pytest.fixture
def care_cache(tmp_path):
    P.pull(tmp_path, keys=CARE_KEYS, today="2026-10-15", fetcher=_fetcher())
    return tmp_path


def test_a_series_used_with_care_is_read_exactly_as_the_core_is_and_carries_the_mark(care_cache):
    result = R.read_all(care_cache, check(answered(history="full")))
    got = {(x["key"], x["reading"]): x for x in result["readings"] if x["care"]}
    assert set(got) == {("saving_rate", "position"), ("saving_rate", "change"), ("real_income", "change"),
                        ("expected_missed_payment", "position"), ("expected_missed_payment", "change")}
    # counted from the lowest: the saving rate's latest is its lowest, so it is at or above itself alone
    low = got[("saving_rate", "position")]
    assert low["value"] == 1.0 and low["readings"] == 321 and low["percentile"] == pytest.approx(100 / 321)
    assert "at or above 0.3% of the 321 readings since Jan 2000 (lowest 1, highest 7)" in low["sentence"]
    assert got[("saving_rate", "change")]["direction"] == R.DECREASING
    # the survey: every month of its workbook, the latest at or above the share at or below it
    survey = got[("expected_missed_payment", "position")]
    values = [sce(i) for i in range(160)]
    assert survey["readings"] == 160 and survey["date"] == "2026-09-01"
    assert survey["percentile"] == pytest.approx(100 * sum(v <= values[-1] for v in values) / 160)
    assert survey["credit"].startswith("Source: Survey of Consumer Expectations")
    assert not any(x["care"] for x in result["readings"] if x["key"] == "unemployment")


def test_a_care_series_the_pull_lacks_says_why_like_any_other(cache):
    result = R.read_all(cache, check(answered()))
    missing = {(x["key"], x["reading"]): x["why"] for x in result["not_read"] if x["care"]}
    assert set(missing) == {(i.key, r) for i in CARE + CARE_DERIVED for r in readings_of(i)}
    assert all(w.startswith("not in the pull of 2026-10-15") for w in missing.values())


def test_the_runs_fingerprints_cover_every_file_it_read(care_cache):
    result = R.read_all(care_cache, check(answered()))
    assert {"nyfed_sce.xlsx", "fred-PSAVERT.csv", "fred-DSPIC96.csv", "fred-UNRATE.csv"} <= set(result["read_sha"])


def test_household_debt_is_read_from_the_ny_fed_workbook_by_type(tmp_path):
    keys = ["household_mortgage", "household_credit_card", "household_total"]
    P.pull(tmp_path, keys=keys, today="2026-10-22", fetcher=_fetcher())
    result = R.read_all(tmp_path, check(answered(history="full", change_months=12)))
    cards = _by(result, "household_credit_card", "change")
    assert cards["date"] == "2026-04-01" and cards["value"] == pytest.approx(100 * (hh(93, 3) / hh(89, 3) - 1))
    assert cards["credit"].startswith("Source: New York Fed Consumer Credit Panel / Equifax.")
    assert not any(r["key"] == "household_total" and r["reading"] == "position" for r in result["readings"])
    assert "nyfed_hhdc.xlsx" in result["read_sha"]
