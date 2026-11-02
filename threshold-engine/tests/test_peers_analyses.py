"""peers.analyses: every acceptance number in docs/PEERS-SPEC.md ("analyses.py")
reproduced from the roster pull (tests/data/peers/roster_2006.json) and the
classified acquisitions (mergers_roster.json). The numbers were produced
earlier by a separate script, so this is a tie-out, not the code agreeing with
itself. Synthetic cases pin the rules the roster data does not reach: gaps,
refusals, the backward chain and the mix factor."""
import json

import pytest

from conftest import DATA, as_earlier_build
from threshold_engine.peers.analyses import (
    annual_means, balance_trend, calendar_year, lagged_rate, mix_factor, normalisation,
    organic_index)
from threshold_engine.peers.books import bank_book, composite, quarterly_flows

PEERS = DATA / "peers"
KEYBANK = "17534"
FIFTH_THIRD = "6672"
#: The six regionals of the lagged-rate pack.
SIX = {"6548": "U.S. Bank", "6384": "PNC", "6672": "Fifth Third", "6560": "Huntington",
       "57957": "Citizens", "12368": "Regions"}
#: The ten regionals of the normalisation composite: the six plus four.
TEN = list(SIX) + ["9846", "11063", "588", "2270"]
#: The earlier build's settings: 25% jump, $1bn ($000), KeyBank exempt, five peers.
JUMP, MIN_BOOK, MIN_BANKS = 0.25, 1_000_000, 5
#: Fifth Third's Dividend Finance: a nonbank purchase, not in the FDIC record.
EXTRAS = {FIFTH_THIRD: ["2022Q2"]}
CARD, OTHER = "Credit card", "Other consumer"


@pytest.fixture(scope="module")
def data():
    return as_earlier_build(json.loads((PEERS / "roster_2006.json").read_text()))


@pytest.fixture(scope="module")
def mergers():
    return json.loads((PEERS / "mergers_roster.json").read_text())


def acquisitions(mergers, cert):
    return mergers.get(cert, []) + EXTRAS.get(cert, [])


def card_book(data, cert):
    return bank_book(data, cert, CARD, JUMP, MIN_BOOK, exempt_min_book=cert == KEYBANK, acquired=())


# --- acceptance: lagged rates -------------------------------------------------

LAGGED = {
    2025: ({"6672": 3.47, "6384": 3.50, KEYBANK: 3.82, "6548": 4.54, "12368": 4.59,
            "57957": 4.75, "6560": 4.92}, 4.35),
    2019: ({"6672": 6.18, "6560": 7.89, "6384": 4.49, "12368": 4.80, "57957": 4.66,
            "6548": 4.24, KEYBANK: 3.52}, 4.53),
}


@pytest.mark.parametrize("year", sorted(LAGGED))
def test_acceptance_card_lagged_net_rate(data, year):
    banks, total = LAGGED[year]
    for cert, want in banks.items():
        r = lagged_rate(data, cert, CARD, year, 2)
        assert r["base_year"] == year - 2
        assert round(r["rate"], 2) == want, (cert, r["rate"])
    pack = lagged_rate(data, list(SIX), CARD, year, 2)
    assert round(pack["rate"], 2) == total
    # the pack total is summed dollars, not a mean of the six rates
    each = [lagged_rate(data, c, CARD, year, 2) for c in SIX]
    assert pack["net"] == sum(r["net"] for r in each)
    assert pack["balance"] == sum(r["balance"] for r in each)


# --- acceptance: normalisation ------------------------------------------------

NORMALISATION = {KEYBANK: (3.29, 4.30), "6384": (3.53, 4.07), "57957": (3.82, 5.51),
                 "6672": (5.07, 3.79), "12368": (4.34, 4.07), "6548": (3.82, 4.16)}


def test_acceptance_card_normalisation_per_bank(data):
    for cert, (base, end) in NORMALISATION.items():
        n = normalisation([(r["quarter"], r["net_rate"]) for r in card_book(data, cert)],
                          2019, 2025)
        assert (round(n["base"], 2), round(n["end"], 2)) == (base, end), cert
        assert n["ratio"] == pytest.approx(n["end"] / n["base"])


def test_acceptance_card_normalisation_ten_regional_composite(data):
    comp = composite({c: card_book(data, c) for c in TEN}, TEN, min_banks=MIN_BANKS)
    n = normalisation([(r["quarter"], r["net_rate"]) for r in comp], 2019, 2025)
    assert (round(n["base"], 2), round(n["end"], 2)) == (3.82, 4.25)


# --- acceptance: organic index ------------------------------------------------

ORGANIC = {
    CARD: {"588": (156, 145), "6548": (133, 126), "6560": (138, 123), "12368": (108, 104),
           "57957": (104, 99), KEYBANK: (82, 82), "6384": (100, 80), "9846": (78, 78),
           "6672": (66, 67)},
    OTHER: {"588": (246, 238), "6672": (296, 226), "6548": (132, 130), "6560": (163, 121),
            KEYBANK: (109, 109), "9846": (104, 104), "12368": (129, 61), "57957": (59, 59),
            "6384": (39, 34)},
}


@pytest.mark.parametrize("product", sorted(ORGANIC))
def test_acceptance_organic_index_2026q2(data, mergers, product):
    for cert, (reported, organic) in ORGANIC[product].items():
        rows = organic_index(data, cert, product, "2019Q4", acquisitions(mergers, cert))
        base = next(r for r in rows if r["quarter"] == "2019Q4")
        assert base["reported"] == base["organic"] == 100
        assert base["balance"] >= 500_000, cert       # books of at least $500m at the base
        last = rows[-1]
        assert last["quarter"] == "2026Q2"
        assert (round(last["reported"]), round(last["organic"])) == (reported, organic), cert


def test_fifth_thirds_declared_extra_is_what_moves_its_other_consumer(data, mergers):
    without = organic_index(data, FIFTH_THIRD, OTHER, "2019Q4", mergers[FIFTH_THIRD])[-1]
    assert round(without["organic"]) != 226


# --- acceptance: KeyBank other consumer, calendar year ------------------------

KEY_OTHER = {2018: 1.67, 2019: 1.34, 2020: 0.66, 2021: 0.47, 2022: 0.50, 2023: 0.76,
             2024: 1.11, 2025: 1.04}
KEY_OTHER_BALANCE_M = {2018: 2394, 2021: 5416, 2025: 4681}


def test_acceptance_keybank_other_consumer_calendar_year(data):
    flows = {q: (g, r) for q, g, r, _ in quarterly_flows(data, KEYBANK, OTHER)}
    for year, want in KEY_OTHER.items():
        r = lagged_rate(data, KEYBANK, OTHER, year, 0)
        assert round(r["rate"], 2) == want, year
        # four quarterly flows summed equal the Q4 year-to-date as filed
        four = [flows["%d%s" % (year, md)] for md in ("0331", "0630", "0930", "1231")]
        assert sum(g - rc for g, rc in four) == pytest.approx(r["net"])
        if year in KEY_OTHER_BALANCE_M:
            assert round(r["balance"] / 1000) == KEY_OTHER_BALANCE_M[year]


# --- synthetic rules ----------------------------------------------------------

def row(cert, q, bal, dr=0, cr=0):
    return {"CERT": cert, "REPDTE": q, "LNCRCD": bal, "DRCRCD": dr, "CRCRCD": cr}


def year_of(cert, y, bals, dr_ytd, cr_ytd):
    return {"%d%s" % (y, md): [row(cert, "%d%s" % (y, md), b, d, c)]
            for md, b, d, c in zip(("0331", "0630", "0930", "1231"), bals, dr_ytd, cr_ytd)}


def test_calendar_year_is_q4_as_filed_and_the_mean_balance():
    data = year_of(1, 2020, [100, 200, 300, 400], [1, 2, 3, 10], [0, 0, 1, 4])
    assert calendar_year(data, 1, CARD, 2020) == {
        "year": 2020, "net": 6, "gross": 10, "recoveries": 4, "balance": 250}


def test_calendar_year_short_a_quarter_is_none_not_a_partial_year():
    data = year_of(1, 2020, [100, 200, 300, 400], [1, 2, 3, 10], [0, 0, 1, 4])
    del data["20200630"]
    assert calendar_year(data, 1, CARD, 2020)["balance"] is None
    assert lagged_rate(data, 1, CARD, 2020, 0)["rate"] is None


def test_lagged_rate_divides_by_the_earlier_years_book():
    data = {**year_of(1, 2018, [1000] * 4, [0] * 4, [0] * 4),
            **year_of(1, 2020, [4000] * 4, [5, 10, 15, 30], [0, 0, 0, 10])}
    r = lagged_rate(data, 1, CARD, 2020, 2)
    assert (r["net"], r["balance"], r["rate"]) == (20, 1000, 2.0)


def test_a_pack_total_with_a_bank_missing_is_refused():
    data = {**year_of(1, 2018, [1000] * 4, [0] * 4, [0] * 4),
            **year_of(1, 2020, [1000] * 4, [0, 0, 0, 30], [0] * 4)}
    assert lagged_rate(data, [1], CARD, 2020, 2)["rate"] == 3.0
    for q in data:
        data[q] = data[q] + [row(2, q, 500, 1, 0)]
    del data["20180331"][1]
    assert lagged_rate(data, [1, 2], CARD, 2020, 2)["rate"] is None
    with pytest.raises(ValueError):
        lagged_rate(data, [], CARD, 2020, 2)


def test_normalisation_needs_all_four_quarters_of_a_year():
    series = [("2019Q1", 1.0), ("2019Q2", 2.0), ("2019Q3", 3.0), ("2019Q4", 6.0),
              ("2025Q1", 3.0), ("2025Q2", None), ("2025Q3", 3.0), ("2025Q4", 3.0)]
    assert annual_means(series) == {2019: 3.0, 2025: None}
    n = normalisation(series, 2019, 2025)
    assert (n["base"], n["end"], n["ratio"]) == (3.0, None, None)
    series[5] = ("2025-06-30", 6.0)               # dates work as well as YYYYQn
    assert normalisation(series, 2019, 2025)["ratio"] == pytest.approx(1.25)


def test_balance_trend_changes_and_gaps():
    data = {"20200331": [row(1, "20200331", 100)], "20200630": [row(1, "20200630", 150)],
            "20200930": [row(9, "20200930", 1)], "20201231": [row(1, "20201231", 120)]}
    t = balance_trend(data, 1, CARD)
    assert [r["quarter"] for r in t] == ["2020Q1", "2020Q2", "2020Q3", "2020Q4"]
    assert [r["balance"] for r in t] == [100, 150, None, 120]
    assert [r["change"] for r in t] == [None, 50, None, None]
    assert t[1]["change_pct"] == 50
    assert t[3]["date"] == "2020-12-31"


def _quarters(cert, bals, first=2019):
    out = {}
    for i, b in enumerate(bals):
        q = "%d%s" % (first + i // 4, ("0331", "0630", "0930", "1231")[i % 4])
        if b is not None:
            out[q] = [row(cert, q, b)]
        else:
            out[q] = [row(99, q, 1)]
    return out


def test_organic_index_holds_growth_at_1_in_an_acquisition_quarter():
    data = _quarters(1, [80, 100, 110, 220, 242])
    rows = organic_index(data, 1, CARD, "2019Q2", ["2019-12-31"])
    assert [r["reported"] for r in rows] == [80, 100, 110, 220, 242]
    assert [round(r["organic"], 6) for r in rows] == [80, 100, 110, 110, 121]
    assert [r["acquisition"] for r in rows] == [False, False, False, True, False]
    # an acquisition named as YYYYQn is the same quarter
    again = organic_index(data, 1, CARD, "2019Q2", ["2019Q4"])
    assert [r["organic"] for r in again] == [r["organic"] for r in rows]


def test_organic_index_runs_backwards_from_the_base_on_the_same_rule():
    data = _quarters(1, [50, 100, 110, 121])
    rows = organic_index(data, 1, CARD, "2019Q4", ["2019Q2"])
    # into Q2 is an acquisition, so Q1 carries Q2's index; the rest chain back
    assert [round(r["organic"], 6) for r in rows] == [
        round(100 / 1.21, 6), round(100 / 1.21, 6), round(100 / 1.1, 6), 100]


def test_a_missing_quarter_breaks_the_organic_chain():
    data = _quarters(1, [100, 110, None, 130, 140])
    rows = organic_index(data, 1, CARD, "2019Q1", [])
    assert rows[1]["organic"] == pytest.approx(110)
    assert [r["organic"] for r in rows[2:]] == [None, None, None]
    assert rows[3]["reported"] == 130


def test_organic_index_refuses_a_base_with_no_book():
    data = _quarters(1, [0, 100])
    with pytest.raises(ValueError):
        organic_index(data, 1, CARD, "2019Q1", [])
    with pytest.raises(ValueError):
        organic_index(data, 1, CARD, "2018Q4", [])


def test_mix_factor():
    rows = mix_factor({2019: 2.0, 2025: 3.0}, {2019: 4.0, 2025: 5.0},
                      {2019: 100.0, 2025: 125.0}, 2019)
    assert rows[0] == {"year": 2019, "bank_ratio": 1.0, "industry_ratio": 1.0,
                       "own_factor": 1.0, "balance_factor": 1.0}
    r = rows[1]
    assert r["year"] == 2025
    assert r["bank_ratio"] == pytest.approx(1.5)
    assert r["industry_ratio"] == pytest.approx(1.25)
    assert r["own_factor"] == pytest.approx(1.2)
    assert r["balance_factor"] == pytest.approx(0.8)


def test_mix_factor_refuses_a_missing_base_year_and_skips_partial_years():
    with pytest.raises(ValueError):
        mix_factor({2025: 1.0}, {2019: 1.0, 2025: 1.0}, {2019: 1.0, 2025: 1.0}, 2019)
    rows = mix_factor({2019: 1.0, 2020: 2.0, 2021: 1.0}, {2019: 1.0, 2021: 0.0},
                      {2019: 1.0, 2020: 1.0, 2021: 2.0}, 2019)
    assert [r["year"] for r in rows] == [2019, 2021]
    assert rows[1]["own_factor"] is None          # the industry fell to 0: no ratio


# --- refusals: a ratio over a base of 0 or below ------------------------------

def test_mix_factor_refuses_a_base_year_of_net_recoveries():
    # net recoveries (-0.5) to losses (1.0) is worse; as a ratio it reads -2.0, "better"
    rows = mix_factor({2019: -0.5, 2025: 1.0}, {2019: 1.0, 2025: 1.0},
                      {2019: 1.0, 2025: 1.0}, 2019)
    assert [(r["bank_ratio"], r["own_factor"]) for r in rows] == [(None, None), (None, None)]
    assert [r["industry_ratio"] for r in rows] == [1.0, 1.0]
    rows = mix_factor({2019: 1.0, 2025: 1.0}, {2019: 0.0, 2025: 1.0},
                      {2019: 1.0, 2025: 1.0}, 2019)
    assert [r["industry_ratio"] for r in rows] == [None, None]


def test_mix_factor_refuses_an_industry_ratio_below_0():
    # the industry fell to net recoveries: bank_ratio 2 over industry_ratio -1 is not "better"
    rows = mix_factor({2019: 1.0, 2025: 2.0}, {2019: 1.0, 2025: -1.0},
                      {2019: 1.0, 2025: 1.0}, 2019)
    assert (rows[1]["bank_ratio"], rows[1]["industry_ratio"]) == (2.0, -1.0)
    assert rows[1]["own_factor"] is None


def test_mix_factor_balance_factor_is_none_on_an_empty_book():
    rows = mix_factor({2019: 1.0, 2025: 1.0}, {2019: 1.0, 2025: 1.0},
                      {2019: 100.0, 2025: 0.0}, 2019)
    assert rows[1]["balance_factor"] is None


def test_mix_factor_on_keybanks_mortgage_net_recoveries(data):
    # KeyBank and the six were both in net recoveries on mortgages in 2022:
    # no ratio to that base is published, rather than one that reads backwards
    years = range(2022, 2026)
    key = {y: lagged_rate(data, KEYBANK, "Mortgage", y, 0) for y in years}
    pack = {y: lagged_rate(data, list(SIX), "Mortgage", y, 0)["rate"] for y in years}
    assert key[2022]["rate"] < 0 and pack[2022] < 0
    rows = mix_factor({y: key[y]["rate"] for y in years}, pack,
                      {y: key[y]["balance"] for y in years}, 2022)
    assert [r["own_factor"] for r in rows] == [None] * 4
    assert rows[0]["balance_factor"] == 1.0


def test_normalisation_refuses_a_base_of_0_or_below():
    def series(base, end):
        return ([("2019Q%d" % i, base) for i in range(1, 5)]
                + [("2025Q%d" % i, end) for i in range(1, 5)])
    assert normalisation(series(-1.0, 1.0), 2019, 2025)["ratio"] is None
    n = normalisation(series(0.0, 1.0), 2019, 2025)
    assert (n["base"], n["end"], n["ratio"]) == (0.0, 1.0, None)
    assert normalisation(series(2.0, -1.0), 2019, 2025)["ratio"] == -0.5


# --- the guards each refusal rests on -----------------------------------------

def test_a_pack_total_with_a_bank_missing_a_quarter_of_the_loss_year_is_refused():
    data = {**year_of(1, 2018, [1000] * 4, [0] * 4, [0] * 4),
            **year_of(1, 2020, [1000] * 4, [0, 0, 0, 30], [0] * 4)}
    for q in data:
        data[q] = data[q] + [row(2, q, 500, 1, 0)]
    del data["20200630"][1]
    r = lagged_rate(data, [1, 2], CARD, 2020, 2)
    assert (r["net"], r["rate"]) == (None, None)
    assert r["balance"] == 1500


def test_lagged_rate_on_an_empty_base_book_is_none():
    data = {**year_of(1, 2018, [0] * 4, [0] * 4, [0] * 4),
            **year_of(1, 2020, [1000] * 4, [0, 0, 0, 30], [0] * 4)}
    r = lagged_rate(data, 1, CARD, 2020, 2)
    assert (r["net"], r["balance"], r["rate"]) == (30, 0, None)


def test_lagged_rate_refuses_a_bank_named_twice_and_a_negative_lag():
    data = {**year_of(1, 2018, [1000] * 4, [0] * 4, [0] * 4),
            **year_of(1, 2020, [1000] * 4, [0, 0, 0, 30], [0] * 4)}
    with pytest.raises(ValueError, match="twice"):
        lagged_rate(data, [1, "1"], CARD, 2020, 2)
    with pytest.raises(ValueError, match="lag_years"):
        lagged_rate(data, 1, CARD, 2018, -2)


def test_annual_means_counts_quarters_not_values():
    # three quarters is not a year, however the quarters are written
    assert annual_means([("2019Q1", 1.0), ("2019Q2", 2.0), ("2019Q3", 3.0)]) == {2019: None}
    with pytest.raises(ValueError, match="2019Q1"):
        annual_means([("2019Q1", 1.0), ("2019-03-31", 1.0), ("2019Q2", 2.0), ("2019Q3", 3.0)])
    with pytest.raises(ValueError, match="twice"):
        annual_means([("2019Q1", 1.0), ("2019Q1", 1.0), ("2019Q2", 2.0), ("2019Q3", 3.0),
                      ("2019Q4", 4.0)])


def test_balance_trend_does_not_bridge_a_quarter_absent_from_the_data():
    data = {"20200331": [row(1, "20200331", 100)], "20200930": [row(1, "20200930", 150)]}
    t = balance_trend(data, 1, CARD)
    assert [r["quarter"] for r in t] == ["2020Q1", "2020Q3"]
    assert [(r["change"], r["change_pct"]) for r in t] == [(None, None), (None, None)]


def test_an_acquisition_does_not_bridge_a_quarter_absent_from_the_data():
    data = {"20190331": [row(1, "20190331", 100)], "20190930": [row(1, "20190930", 300)],
            "20191231": [row(1, "20191231", 330)]}
    rows = organic_index(data, 1, CARD, "2019Q1", ["2019Q3"])
    assert [r["organic"] for r in rows] == [100.0, None, None]
    # the same as when the quarter is in the data and the bank did not file it
    data["20190630"] = [row(9, "20190630", 1)]
    rows = organic_index(data, 1, CARD, "2019Q1", ["2019Q3"])
    assert [r["organic"] for r in rows] == [100.0, None, None, None]
    # and backwards from the base: Q3 chains back from Q4, Q1 cannot cross the gap
    del data["20190630"]
    rows = organic_index(data, 1, CARD, "2019Q4", ["2019Q3"])
    assert [r["organic"] for r in rows] == [None, pytest.approx(100 / 1.1), 100.0]


def test_organic_chain_backwards_stops_at_an_empty_quarter():
    # into Q2 the book fell to 0: growth 0, so Q1 cannot be worked back to
    data = _quarters(1, [100, 0, 50, 60])
    rows = organic_index(data, 1, CARD, "2019Q4", ["2019Q3"])
    assert rows[0]["organic"] is None
    assert rows[3]["organic"] == 100.0


def test_organic_chain_backwards_breaks_at_an_unfiled_quarter_before_an_acquisition():
    data = _quarters(1, [100, None, 50, 60])
    rows = organic_index(data, 1, CARD, "2019Q4", ["2019Q3"])
    assert [r["organic"] for r in rows] == [None, None, pytest.approx(100 / 1.2), 100.0]
