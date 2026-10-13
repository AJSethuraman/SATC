"""peers.books: every bank's TTM rates and the all-peer composite must equal
the earlier build_peers.py output (tests/data/peers/expected_books.json) to 4
decimals, run on the roster pull with jump 0.25, minimum book $1bn and KeyBank
exempt. The earlier script is a separate program, so this is a tie-out, not
the code agreeing with itself. Synthetic cases pin the industry sum, the band,
best and worst, and the series file."""
import json

import pytest

from conftest import DATA
from threshold_engine.peers.books import (
    WHY_JUMP, WHY_MISSING, WHY_SMALL, band, bank_book, best_worst, composite, industry,
    label, quarter_end, quarterly_flows, write_series)
from threshold_engine.profile import percentile
from threshold_engine.workbook import read_series

PEERS = DATA / "peers"
ROSTER = json.loads((PEERS.parents[2] / "config" / "peers.json").read_text())["banks"]
KEYBANK = "17534"
PEER_CERTS = [b["cert"] for b in ROSTER if b["group"] == "peer"]
FOUR = ("Credit card", "Mortgage", "Home equity", "Other consumer")
#: The earlier build's settings, as it ran: 25% jump, $1bn ($000), KeyBank
#: exempt, and a composite needing five peers.
JUMP, MIN_BOOK, MIN_BANKS = 0.25, 1_000_000, 5


@pytest.fixture(scope="module")
def data():
    return json.loads((PEERS / "roster_2006.json").read_text())


@pytest.fixture(scope="module")
def expected():
    return json.loads((PEERS / "expected_books.json").read_text())


@pytest.fixture(scope="module")
def books(data):
    return {p: {b["cert"]: bank_book(data, b["cert"], p, JUMP, MIN_BOOK,
                                     exempt_min_book=b["cert"] == KEYBANK)
                for b in ROSTER} for p in FOUR}


def same(got, want):
    """Equal to 4 decimals, None matching None."""
    if want is None or got is None:
        return got is None and want is None
    return abs(round(got, 4) - want) < 1e-9


def test_roster_matches_the_earlier_build(expected):
    assert sorted(expected["banks"]) == sorted(b["cert"] for b in ROSTER)
    assert len(PEER_CERTS) == 15


def test_acceptance_1_every_bank_product_and_quarter(books, expected):
    checked, kept, bad = 0, 0, []
    for p in FOUR:
        for cert, want in expected["banks"].items():
            rows = books[p][cert]
            assert [r["quarter"] for r in rows] == expected["quarters"]
            for kind in ("gross", "net"):
                for r, w in zip(rows, want[p][kind]):
                    checked += 1
                    kept += w is not None
                    if not same(r[kind + "_rate"], w):
                        bad.append((p, cert, kind, r["quarter"], r[kind + "_rate"], w))
    assert not bad, bad[:10]
    assert checked == 4 * 16 * 2 * 78
    assert 0 < kept < checked                     # both kept and dropped values exist


def test_acceptance_2_the_all_peer_composite(books, expected):
    for p in FOUR:
        comp = composite(books[p], PEER_CERTS, min_banks=MIN_BANKS)
        want = expected["composite"][p]
        assert [r["quarter"] for r in comp] == expected["quarters"]
        assert [r["banks"] for r in comp] == want["peers_in"]
        for kind in ("gross", "net"):
            bad = [(r["quarter"], r[kind + "_rate"], w)
                   for r, w in zip(comp, want[kind]) if not same(r[kind + "_rate"], w)]
            assert not bad, (p, kind, bad[:5])


def test_composite_leaves_out_keybank_and_counts_dollars(books):
    p = "Credit card"
    comp = composite(books[p], PEER_CERTS, min_banks=MIN_BANKS)
    with_key = composite(books[p], PEER_CERTS + [KEYBANK], min_banks=MIN_BANKS)
    assert comp[-1]["gross_rate"] != with_key[-1]["gross_rate"]
    q = comp[-1]["quarter"]
    rows = [r for c in PEER_CERTS for r in books[p][c] if r["quarter"] == q and r["kept"]]
    assert comp[-1]["gross_rate"] == pytest.approx(
        100 * sum(r["gross"] for r in rows) / sum(r["avg_balance"] for r in rows))


def test_every_dropped_quarter_says_why(books):
    whys = set()
    for p in FOUR:
        for rows in books[p].values():
            for r in rows:
                assert (r["why"] is None) == r["kept"]
                assert (r["gross_rate"] is None) == (not r["kept"])
                whys.add(r["why"])
    assert {WHY_JUMP, WHY_SMALL} <= whys


def test_keybank_exemption_is_what_keeps_its_small_books(data):
    exempt = bank_book(data, KEYBANK, "Credit card", JUMP, MIN_BOOK, exempt_min_book=True)
    held = bank_book(data, KEYBANK, "Credit card", JUMP, MIN_BOOK)
    small = [a for a, b in zip(exempt, held) if a["kept"] and not b["kept"]]
    assert small and all(b["why"] == WHY_SMALL for a, b in zip(exempt, held)
                         if a["kept"] and not b["kept"])
    assert all(a["avg_balance"] < MIN_BOOK for a in small)


def test_judgement_settings_have_no_default(data):
    with pytest.raises(TypeError):
        bank_book(data, KEYBANK, "Credit card")                      # noqa
    with pytest.raises(TypeError):
        composite({}, [])                                            # noqa
    with pytest.raises(TypeError):
        band({}, [], "net")                                          # noqa
    with pytest.raises(ValueError):
        bank_book(data, KEYBANK, "Boats", JUMP, MIN_BOOK)


# --- synthetic -----------------------------------------------------------

def row(cert, q, bal, dr, cr):
    return {"CERT": cert, "REPDTE": q, "LNCRCD": bal, "DRCRCD": dr, "CRCRCD": cr}


QS = ["20200331", "20200630", "20200930", "20201231", "20210331", "20210630"]


def test_quarterly_flows_from_year_to_date():
    data = {q: [row(1, q, 1000, 10 * (i % 4 + 1), i % 4 + 1)] for i, q in enumerate(QS)}
    data["20200930"] = []                                            # bank 1 missing Q3
    flows = quarterly_flows(data, 1, "Credit card")
    assert flows[0] == ("20200331", 10.0, 1.0, 1000.0)               # Q1 is its YTD
    assert flows[1] == ("20200630", 10.0, 1.0, 1000.0)               # 20 - 10
    assert flows[2] == ("20200930", None, None, None)                # missing
    assert flows[3] == ("20201231", None, None, 1000.0)              # previous missing
    assert flows[4] == ("20210331", 10.0, 1.0, 1000.0)               # Q1 again


def test_acceptance_4_a_missing_bank_is_left_out_of_the_industry_not_negative():
    # Bank 1 files every quarter: 10 a quarter, YTD 10, 20, 30, 40, 10, 20.
    # Bank 2 files YTD 100 a quarter but is missing from 2020Q3.
    data = {}
    for i, q in enumerate(QS):
        n = i % 4 + 1
        data[q] = [row(1, q, 1000, 10 * n, 1 * n)]
        if q != "20200930":
            data[q].append(row(2, q, 5000, 100 * n, 0))
    ind = industry(data, "Credit card")
    assert [r["quarter"] for r in ind] == ["2020Q4", "2021Q1", "2021Q2"]
    # Flows: Q1 110, Q2 110, Q3 10 (bank 2 absent, not 10 - 200 = -190),
    # Q4 10 (bank 2 not in Q3, so only bank 1: 40 - 30).
    first = ind[0]
    assert first["gross"] == 110 + 110 + 10 + 10
    assert first["recoveries"] == 4
    assert first["avg_balance"] == (6000 + 6000 + 1000 + 6000) / 4
    assert first["gross_rate"] == pytest.approx(100 * 240 / 4750)
    assert first["net_rate"] == pytest.approx(100 * 236 / 4750)
    assert first["date"] == "2020-12-31"
    assert all(r["gross"] > 0 for r in ind)


def test_industry_sums_products_together():
    a = {"20200331": [{"CERT": 1, "LNCONOTH": 100, "DRCONOTH": 1, "CRCONOTH": 0,
                       "LNAUTO": None, "DRAUTO": None, "CRAUTO": None}]}
    for q in QS[1:4]:
        a[q] = [{"CERT": 1, "LNCONOTH": 100, "DRCONOTH": 1, "CRCONOTH": 0,
                 "LNAUTO": 300, "DRAUTO": 6, "CRAUTO": 2}]
    alone = industry(a, "Other consumer")
    both = industry(a, "Other consumer", products=["Other consumer", "Auto"])
    assert alone[0]["gross"] == 1 and alone[0]["avg_balance"] == 100
    # auto: Q1 blank (0), Q2 6 - 0, Q3 6 - 6, Q4 6 - 6
    assert both[0]["gross"] == 1 + 6 and both[0]["recoveries"] == 2
    assert both[0]["avg_balance"] == 100 + 225


def book(rates):
    """A bank_book-shaped list from rates, None meaning not kept."""
    return [{"quarter": "%dQ%d" % (2020 + i // 4, i % 4 + 1), "kept": r is not None,
             "gross_rate": r, "net_rate": None if r is None else r / 2,
             "gross": None if r is None else r, "recoveries": 0.0, "avg_balance": 100.0}
            for i, r in enumerate(rates)]


def test_band_is_percentile_inc_over_kept_banks():
    books = {"a": book([1, 2, 3]), "b": book([2, None, 5]), "c": book([4, 6, 7]),
             "d": book([None, 8, 9])}
    out = band(books, list(books), "gross", min_banks=3)
    assert out[0]["banks"] == 3
    assert out[0]["p10"] == pytest.approx(percentile([1, 2, 4], 10))
    assert out[0]["p90"] == pytest.approx(percentile([1, 2, 4], 90))
    assert out[2]["p25"] == pytest.approx(percentile([3, 5, 7, 9], 25))
    assert band(books, ["a", "b"], "gross", min_banks=3)[0]["p10"] is None
    net = band(books, list(books), "net", pcts=(50,), min_banks=3)
    assert net[0]["p50"] == pytest.approx(1.0)


def test_best_and_worst_need_enough_kept_quarters():
    books = {"low": book([1, 1, 1, 1]), "high": book([9, 9, 9, 9]),
             "mid": book([5, 5, 5, 5]), "thin": book([None, None, None, 99])}
    assert best_worst(books, list(books), "gross", last_n=4, min_obs=3) == ("low", "high")
    assert best_worst(books, list(books), "gross", last_n=4, min_obs=1) == ("low", "thin")
    assert best_worst(books, list(books), "gross", last_n=2, min_obs=3) == (None, None)


def test_write_series_round_trips_through_the_workbook_reader(tmp_path):
    p = write_series([("2020Q1", None), ("2020Q2", 1.25), ("20200930", 1.5),
                      ("2020-12-31", 2.0)], tmp_path / "s.csv", "FDIC BankFind\nnet, %")
    text = p.read_text()
    assert text.startswith("# FDIC BankFind\n# net, %\n")
    assert "2020-03-31" in text.splitlines()[2]                      # the gap is stated
    pts = read_series(p)
    assert [(x.date, x.value) for x in pts] == [
        ("2020-06-30", 1.25), ("2020-09-30", 1.5), ("2020-12-31", 2.0)]


# --- the guards the rule states, each pinned ---------------------------------

def card_data(quarters, bal=1000, step=10):
    """One bank, cert 1, a flat book of ``bal`` and ``step`` charged off a
    quarter (year-to-date 10, 20, 30, 40), one recovery a quarter."""
    out = {}
    for q in quarters:
        n = (int(q[4:6]) - 1) // 3 + 1
        out[q] = [row(1, q, bal, step * n, n)]
    return out


EIGHT = ["2020%s" % m for m in ("0331", "0630", "0930", "1231")] + \
        ["2021%s" % m for m in ("0331", "0630", "0930", "1231")]


def test_a_book_exactly_at_the_minimum_is_kept():
    rows = bank_book(card_data(EIGHT), 1, "Credit card", JUMP, 1000)
    assert rows[-1]["avg_balance"] == 1000 and rows[-1]["kept"]
    assert rows[-1]["gross_rate"] == pytest.approx(4.0)              # 40 over 1000
    assert rows[-1]["net_rate"] == pytest.approx(3.6)
    assert bank_book(card_data(EIGHT), 1, "Credit card", JUMP, 1000.01)[-1]["why"] == WHY_SMALL


def test_a_move_exactly_at_the_jump_is_kept():
    data = card_data(EIGHT)
    data["20210630"] = [row(1, "20210630", 1250, 20, 2)]             # +25.0%, not more
    data["20210930"] = [row(1, "20210930", 1000, 30, 3)]             # -20%
    assert all(r["kept"] for r in bank_book(data, 1, "Credit card", 0.25, 0))
    data["20210630"] = [row(1, "20210630", 1251, 20, 2)]
    assert bank_book(data, 1, "Credit card", 0.25, 0)[-1]["why"] == WHY_JUMP


def test_why_names_the_first_reason_jump_then_minimum_then_missing():
    data = card_data(EIGHT, bal=10)
    data["20210630"] = [row(1, "20210630", 100, 20, 2)]              # jumps and is small
    assert bank_book(data, 1, "Credit card", JUMP, 1000)[-1]["why"] == WHY_JUMP
    data = card_data(EIGHT, bal=10)
    data["20211231"] = []                                            # small and missing
    assert bank_book(data, 1, "Credit card", 1.0, 1000)[-1]["why"] == WHY_SMALL


def test_a_missing_quarter_is_missing_not_a_crash():
    # A jump of 1 or more lets a fall to 0 through, so only the missing flow
    # can stop the last quarter: the bank did not file 2021Q4.
    data = card_data(EIGHT)
    data["20211231"] = []
    last = bank_book(data, 1, "Credit card", 1.0, 0)[-1]
    assert last["why"] == WHY_MISSING and not last["kept"]
    assert last["gross_rate"] is None and last["gross"] is None
    assert last["avg_balance"] == 750


def test_a_quarter_the_data_skips_breaks_the_window():
    # 2019Q4 is not in the data at all, so no window touching it is four
    # consecutive quarters (the Q1 after it is still a year-to-date flow).
    qs = ["2019%s" % m for m in ("0331", "0630", "0930")] + EIGHT
    rows = {r["quarter"]: r for r in bank_book(card_data(qs), 1, "Credit card", JUMP, 0)}
    for q in ("2020Q2", "2020Q3", "2020Q4"):
        assert rows[q]["why"] == WHY_MISSING and rows[q]["gross_rate"] is None
    # 2021Q1's window is 2020Q2 to 2021Q1, its jump test reaches back to 2020Q1:
    # all consecutive, so it is kept.
    assert rows["2021Q1"]["kept"] and rows["2021Q1"]["gross_rate"] == pytest.approx(4.0)
    ind = industry(card_data(qs), "Credit card")
    assert [r["quarter"] for r in ind] == ["2020Q4", "2021Q1", "2021Q2", "2021Q3", "2021Q4"]
    assert all(r["gross_rate"] == pytest.approx(4.0) for r in ind)


def test_an_empty_quarter_is_not_a_quarter_of_no_charge_offs():
    # A quarter the FDIC has not published arrives as []: the true rate is 4%
    # every quarter, and an empty quarter must not show up as a dip.
    data = card_data(EIGHT)
    data["20211231"] = []
    ind = industry(data, "Credit card")
    assert [r["quarter"] for r in ind] == ["2020Q4", "2021Q1", "2021Q2", "2021Q3"]
    assert all(r["gross_rate"] == pytest.approx(4.0) for r in ind)
    data = card_data(EIGHT)
    data["20200331"] = []                                            # nor does it zero Q2
    ind = industry(data, "Credit card")
    assert [r["quarter"] for r in ind] == ["2021Q2", "2021Q3", "2021Q4"]
    assert all(r["gross_rate"] == pytest.approx(4.0) for r in ind)


def test_industry_with_no_balance_has_no_rate():
    ind = industry(card_data(EIGHT, bal=0), "Credit card")
    assert ind and all(r["gross_rate"] is None and r["net_rate"] is None for r in ind)
    assert ind[0]["gross"] == 40


def test_industry_counts_a_product_named_twice_once():
    a = {q: [{"CERT": 1, "LNCONOTH": 100, "DRCONOTH": 1, "CRCONOTH": 0,
              "LNAUTO": 300, "DRAUTO": 3 * n, "CRAUTO": 0}]
         for n, q in enumerate(QS[:4], 1)}
    once = industry(a, "Other consumer", products=["Auto"])
    twice = industry(a, "Other consumer", products=["Auto", "Auto", "Other consumer"])
    assert once == twice
    assert once[0]["gross"] == 1 + 12 and once[0]["avg_balance"] == 400


def test_a_tie_goes_to_the_bank_named_first():
    books = {"x": book([5, 5]), "y": book([5, 5])}
    assert best_worst(books, ["x", "y"], "gross", last_n=2, min_obs=1) == ("x", "x")
    assert best_worst(books, ["y", "x"], "gross", last_n=2, min_obs=1) == ("y", "y")


def test_settings_that_cannot_be_right_are_refused(data):
    books = {"a": book([1, 2]), "b": book([3, 4])}
    for bad in (0, -1):
        with pytest.raises(ValueError):
            composite(books, ["a", "b"], bad)
        with pytest.raises(ValueError):
            band(books, ["a", "b"], "gross", min_banks=bad)
        with pytest.raises(ValueError):
            best_worst(books, ["a", "b"], "gross", last_n=bad, min_obs=1)
        with pytest.raises(ValueError):
            best_worst(books, ["a", "b"], "gross", last_n=2, min_obs=bad)
    with pytest.raises(ValueError):
        bank_book(data, KEYBANK, "Credit card", -0.01, MIN_BOOK)
    with pytest.raises(ValueError):
        bank_book(data, KEYBANK, "Credit card", float("nan"), MIN_BOOK)
    with pytest.raises(ValueError):
        bank_book(data, KEYBANK, "Credit card", JUMP, -5)


@pytest.mark.parametrize("q", ["2020Q0", "2020Q5", "20200015", "20201301", "2020-00-01",
                               "2020-13-31", "2020Q", "20Q1", ""])
def test_quarter_end_refuses_what_is_not_a_quarter(q):
    with pytest.raises(ValueError):
        quarter_end(q)


def test_quarter_end_and_label_on_good_quarters():
    assert [quarter_end(q) for q in ("2020Q1", "20200630", "2020-09-30", "2020-11-15")] == [
        "2020-03-31", "2020-06-30", "2020-09-30", "2020-12-31"]
    assert label("20211231") == "2021Q4"
    for bad in ("2021-03-31", "20210031", "2021Q1"):
        with pytest.raises(ValueError):
            label(bad)


def test_data_keyed_by_anything_but_repdte_is_refused():
    iso = {quarter_end(q): v for q, v in card_data(EIGHT).items()}
    for f in (lambda d: bank_book(d, 1, "Credit card", JUMP, 0),
              lambda d: industry(d, "Credit card"),
              lambda d: quarterly_flows(d, 1, "Credit card")):
        with pytest.raises(ValueError):
            f(iso)


def test_write_series_keeps_every_digit(tmp_path):
    v = 1.2345678901234567
    p = write_series([("2020Q1", v)], tmp_path / "s.csv", "note")
    assert [(x.date, x.value) for x in read_series(p)] == [("2020-03-31", v)]


def test_write_series_comments_every_note_line_and_refuses_a_repeat(tmp_path):
    p = write_series([("2020Q1", 1.0)], tmp_path / "n.csv", ["line one\nline two", "three"])
    assert p.read_text().startswith("# line one\n# line two\n# three\ndate,value\n")
    assert [(x.date, x.value) for x in read_series(p)] == [("2020-03-31", 1.0)]
    with pytest.raises(ValueError):
        write_series([("2020Q1", 1.0), ("20200331", 2.0)], tmp_path / "d.csv", "x")
    with pytest.raises(ValueError):
        write_series([("2020Q1", None), ("2020-03-31", 2.0)], tmp_path / "d.csv", "x")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "inf", "-Infinity"])
@pytest.mark.parametrize("field", ["DRCRCD", "CRCRCD", "LNCRCD"])
def test_an_amount_that_is_not_a_number_is_refused_by_bank_quarter_and_field(bad, field):
    """The Codex review (13 Oct 2026): a cached NaN or "inf" charge-off was
    kept and carried into every rate; it is refused, as delinquency refuses it."""
    data = card_data(EIGHT)
    data["20200930"][0][field] = bad
    with pytest.raises(ValueError, match=r"certificate 1, 20200930: %s is .*, not a number" % field):
        bank_book(data, 1, "Credit card", JUMP, 0)
    with pytest.raises(ValueError, match="not a number"):
        industry(data, "Credit card")
