"""peers.delinquency: delinquency and nonaccrual by product, per bank, for the
composite, the band and the industry (docs/V1-ROUND2-SPEC.md, section A).

The synthetic cases pin the three acceptance rules (a missing bank is left out
of the composite, not counted as 0; a jump blanks the four-quarter average
but not the quarter-end rate; a balance of 0 gives None) and every refusal.
The fixture cases run on tests/data/peers/delinquency_roster.json, pulled once
from the public FDIC API on 12 Oct 2026; KeyBank's 2026Q2 amounts below are
the FDIC API's values as that pull holds them, written out by hand, so the
rates are checked against arithmetic on those values, not against the code.
Nothing here ties them to the RC-N filing itself: that is the spec's
acceptance item 2, a separate check against the FFIEC CDR."""
import inspect
import json

import pytest

from conftest import DATA
from threshold_engine.peers.books import CONSUMER as CONSUMER_PRODUCTS, write_series
from threshold_engine.peers.delinquency import (
    BASES, FIELDS, MEASURES, WHY_ABSENT, WHY_FEWER_THAN_FOUR, WHY_JUMP_PREFIX, WHY_NO_BOOK,
    WHY_SMALL,
    band_delinquency, bank_delinquency, basis_key, composite_delinquency, fields_for,
    industry_delinquency, values)
from threshold_engine.profile import percentile
from threshold_engine.workbook import read_series

PEERS = DATA / "peers"
ROSTER = json.loads((PEERS.parents[2] / "config" / "peers.json").read_text())["banks"]
KEYBANK = "17534"
PEER_CERTS = [b["cert"] for b in ROSTER if b["group"] == "peer"]
CARD = "Credit card"
#: The fixture was pulled for the consumer products (12 Oct 2026); the
#: commercial ones have their own (commercial_2007.json).
CONSUMER = [p for p in FIELDS if p in CONSUMER_PRODUCTS]


# ------------------------------------------------------------------ helpers

def row(cert, q, bal, p3=0, p9=0, na=0, product=CARD):
    ln, f3, f9, fn = FIELDS[product]
    return {"CERT": cert, "REPDTE": q, ln: bal, f3: p3, f9: p9, fn: na}


QS = ["20200331", "20200630", "20200930", "20201231", "20210331", "20210630"]


def flat(certs, bal=1000, p3=10, p9=5, na=3, qs=QS):
    """Every bank files every quarter with the same amounts."""
    return {q: [row(c, q, bal, p3, p9, na) for c in certs] for q in qs}


def by_q(rows):
    return {r["q"]: r for r in rows}


def book(data, cert, measure="90+ accruing", jump=0.25, min_book=0, exempt=False):
    return bank_delinquency(data, cert, CARD, measure, jump, min_book, exempt, acquired=())


# ------------------------------------------------------------------ the maps

def test_fields_are_the_spec_table():
    assert FIELDS == {
        "Credit card": ("LNCRCD", "P3CRCD", "P9CRCD", "NACRCD"),
        "Mortgage": ("LNRERSFM", "P3RERSFM", "P9RERSFM", "NARERSFM"),
        "Home equity": ("LNRELOC", "P3RELOC", "P9RELOC", "NARELOC"),
        "Other consumer": ("LNCONOTH+LNCONRP", "P3CONOTH", "P9CONOTH", "NACONOTH"),
        "Auto": ("LNAUTO", "P3AUTO", "P9AUTO", "NAAUTO"),
        # The commercial products, 16 Oct 2026: research-fdic.md's field table.
        "C&I": ("LNCI", "P3CI", "P9CI", "NACI"),
        "Construction": ("LNRECONS", "P3RECONS", "P9RECONS", "NARECONS"),
        "Multifamily": ("LNREMULT", "P3REMULT", "P9REMULT", "NAREMULT"),
        "Nonfarm nonresidential": ("LNRENRES", "P3RENRES", "P9RENRES", "NARENRES"),
        "Owner-occupied nonfarm nonresidential": ("LNRENROW", "P3RENROW", "P9RENROW", "NARENROW"),
        "Other nonfarm nonresidential": ("LNRENROT", "P3RENROT", "P9RENROT", "NARENROT"),
    }
    assert list(MEASURES) == ["30-89", "90+ accruing", "nonaccrual",
                              "90+ incl. nonaccrual", "30+ incl. nonaccrual"]
    assert list(BASES) == ["quarter-end", "four-quarter average"]


def test_fields_for_lists_each_field_once_in_table_order():
    assert fields_for(["Auto", CARD, "Auto"]) == [
        "LNAUTO", "P3AUTO", "P9AUTO", "NAAUTO", "LNCRCD", "P3CRCD", "P9CRCD", "NACRCD"]
    assert fields_for([]) == []
    with pytest.raises(ValueError, match="product must be one of"):
        fields_for(["Cards"])


def test_measures_sum_the_right_fields():
    data = {"20200331": [row(1, "20200331", 1000, p3=10, p9=5, na=3)]}
    want = {"30-89": 10, "90+ accruing": 5, "nonaccrual": 3,
            "90+ incl. nonaccrual": 8, "30+ incl. nonaccrual": 18}
    for m, n in want.items():
        r = book(data, 1, m)[0]
        assert (r["q"], r["numerator"], r["balance"], r["rate"]) == ("2020Q1", n, 1000, n / 10)


# ------------------------------------------------------------------ refusals

def test_every_judgement_is_required():
    sig = inspect.signature(bank_delinquency)
    for name in ("jump", "min_book", "exempt_min_book"):
        assert sig.parameters[name].default is inspect.Parameter.empty, name
    assert inspect.signature(composite_delinquency).parameters["min_banks"].default \
        is inspect.Parameter.empty
    assert inspect.signature(band_delinquency).parameters["min_banks"].default \
        is inspect.Parameter.empty
    with pytest.raises(TypeError):
        bank_delinquency(flat([1]), 1, CARD, "nonaccrual", 0.25, 0, acquired=())


@pytest.mark.parametrize("kw, msg", [
    (dict(jump=-0.1), "jump must be at least 0"),
    (dict(jump=float("nan")), "jump must be at least 0"),
    (dict(min_book=-1), "min_book must be at least 0"),
    (dict(exempt=None), "exempt_min_book must be True or False"),
    (dict(exempt=1), "exempt_min_book must be True or False"),
    (dict(measure="90+"), "measure must be one of"),
])
def test_bad_settings_are_refused(kw, msg):
    with pytest.raises(ValueError, match=msg):
        book(flat([1]), 1, **kw)


def test_unknown_product_basis_and_min_banks_are_refused():
    with pytest.raises(ValueError, match="product must be one of"):
        bank_delinquency(flat([1]), 1, "Cards", "nonaccrual", 0.25, 0, False, acquired=())
    with pytest.raises(ValueError, match="product must be one of"):
        industry_delinquency(flat([1]), "Cards", "nonaccrual")
    with pytest.raises(ValueError, match="basis must be one of"):
        basis_key("ttm")
    books = {"1": book(flat([1]), 1)}
    with pytest.raises(ValueError, match="min_banks must be at least 1"):
        composite_delinquency(books, ["1"], 0)
    with pytest.raises(ValueError, match="min_banks must be at least 1"):
        band_delinquency(books, ["1"], "quarter-end", min_banks=0)


@pytest.mark.parametrize("field, value", [
    ("LNCRCD", float("nan")), ("LNCRCD", float("inf")), ("P9CRCD", float("nan")),
    ("NACRCD", "-inf")])
def test_an_amount_that_is_not_a_finite_number_is_refused(field, value):
    """NaN passes ``bal <= 0`` and ``bal < min_book`` alike, so unrefused it
    came out kept with a NaN rate and made the composite NaN."""
    data = flat([1, 2], bal=1000, p9=10)
    data["20200331"][0][field] = value
    want = "CERT 1, REPDTE 20200331: %s is " % field
    with pytest.raises(ValueError, match=want):
        bank_delinquency(data, 1, CARD, "90+ incl. nonaccrual", 0.25, 500, False, acquired=())
    with pytest.raises(ValueError, match=want):
        industry_delinquency(data, CARD, "90+ incl. nonaccrual")


def test_a_bare_nan_in_a_cache_file_is_refused():
    """``json.loads`` reads a bare NaN, so a corrupt cache can hand one over."""
    data = json.loads('{"20200331": [{"CERT": 1, "REPDTE": "20200331", "LNCRCD": NaN, '
                      '"P3CRCD": 1, "P9CRCD": 1, "NACRCD": 1}]}')
    with pytest.raises(ValueError, match="LNCRCD is nan, not a filed amount"):
        book(data, 1, "nonaccrual")


def test_a_cert_named_twice_and_a_percentile_outside_0_to_100_are_refused():
    data = flat([1, 2])
    books = {str(c): book(data, c) for c in (1, 2)}
    with pytest.raises(ValueError, match="named twice: 2"):
        composite_delinquency(books, ["2", 2], 1)
    with pytest.raises(ValueError, match="named twice: 1"):
        band_delinquency(books, ["1", "2", "1"], "quarter-end", min_banks=1)
    for bad in (150, -1, True, "90", float("nan")):
        with pytest.raises(ValueError, match="percentiles must be numbers from 0 to 100"):
            band_delinquency(books, ["1", "2"], "quarter-end", (10, bad), min_banks=1)
    ok = band_delinquency(books, ["1", "2"], "quarter-end", (0, 100), min_banks=1)[0]
    assert ok["p0"] == ok["p100"] == pytest.approx(0.5)


def test_data_not_keyed_by_quarter_end_is_refused():
    with pytest.raises(ValueError, match="YYYYMMDD quarter-ends"):
        book({"2020Q1": [row(1, "20200331", 1000)]}, 1)


# ------------------------------------------------------------------ acceptance 3

def test_a_missing_bank_is_left_out_of_the_composite_not_counted_as_zero():
    data = flat([1, 2, 3], bal=1000, p9=10)
    data["20200930"] = [r for r in data["20200930"] if r["CERT"] != 3]
    data["20200930"][0]["P9CRCD"] = 40        # bank 1: 4% that quarter
    books = {str(c): book(data, c) for c in (1, 2, 3)}
    q3 = by_q(books["3"])["2020Q3"]
    assert (q3["rate"], q3["kept"], q3["why"]) == (None, False, WHY_ABSENT)
    comp = by_q(composite_delinquency(books, ["1", "2", "3"], 2))
    # (40 + 10) / (1000 + 1000), not (40 + 10 + 0) / 3000
    assert comp["2020Q3"]["banks"] == 2
    assert comp["2020Q3"]["rate"] == pytest.approx(2.5)
    assert comp["2020Q3"]["balance"] == 2000
    assert comp["2020Q2"]["rate"] == pytest.approx(1.0) and comp["2020Q2"]["banks"] == 3
    # with three banks required, that quarter has no composite at all
    assert by_q(composite_delinquency(books, ["1", "2", "3"], 3))["2020Q3"]["rate"] is None
    # and the industry leaves it out the same way
    ind = by_q(industry_delinquency(data, CARD, "90+ accruing"))
    assert ind["2020Q3"]["banks"] == 2 and ind["2020Q3"]["rate"] == pytest.approx(2.5)


def test_a_jump_blanks_the_four_quarter_average_but_not_the_quarter_end_rate():
    data = flat([1], bal=1000, p9=10)
    data["20201231"][0]["LNCRCD"] = 1300      # +30% into 2020Q4
    data["20201231"][0]["P9CRCD"] = 26
    rows = by_q(book(data, 1, jump=0.25))
    assert rows["2020Q4"]["rate"] == pytest.approx(2.0)
    assert rows["2020Q4"]["kept"] is True and rows["2020Q4"]["why"] is None
    assert rows["2020Q4"]["avg4"] is None
    assert rows["2020Q4"]["why_avg4"] == (
        "book moved more than the jump in this window: 2020Q4 +30.0% against the quarter before")
    # the jump sits at i-2 of 2021Q2's window too, so that average is blank as well
    assert rows["2021Q2"]["avg4"] is None and "2020Q4" in rows["2021Q2"]["why_avg4"]
    # a looser jump keeps the average: mean of 1, 1, 1, 2 (2020Q1..Q4)
    loose = by_q(book(data, 1, jump=0.5))
    assert loose["2020Q4"]["avg4"] == pytest.approx(1.25)
    assert loose["2020Q4"]["why_avg4"] is None


def test_a_move_exactly_at_the_jump_is_not_a_jump():
    """The rule is a move of *more than* the jump: +25% against a 0.25 jump
    keeps the average, and a move just past it blanks it."""
    data = flat([1], bal=1000, p9=10)
    data["20201231"][0]["LNCRCD"] = 1250      # exactly +25% into 2020Q4
    rows = by_q(book(data, 1, jump=0.25))
    assert rows["2020Q4"]["why_avg4"] is None
    assert rows["2020Q4"]["avg4"] == pytest.approx((1 + 1 + 1 + 0.8) / 4)
    data["20201231"][0]["LNCRCD"] = 1251
    assert by_q(book(data, 1, jump=0.25))["2020Q4"]["avg4"] is None


def test_a_jump_at_i_minus_3_is_outside_the_window():
    """The move into i-3 is measured against i-4, outside the four filings the
    average spans, so it does not blank it."""
    qs = QS + ["20210930"]
    data = flat([1], bal=1000, p9=10, qs=qs)
    for q in qs[3:]:
        data[q][0]["LNCRCD"] = 2000
    rows = by_q(book(data, 1, jump=0.25))
    assert rows["2020Q4"]["avg4"] is None           # jump at i
    assert rows["2021Q2"]["avg4"] is None           # jump at i-2
    assert rows["2021Q3"]["avg4"] == pytest.approx(0.5)  # jump at i-3: kept


def test_a_move_from_zero_is_a_jump():
    data = flat([1], bal=1000, p9=10)
    data["20200630"][0]["LNCRCD"] = 0
    rows = by_q(book(data, 1))
    assert rows["2020Q2"]["rate"] is None and rows["2020Q2"]["why"] == WHY_NO_BOOK
    # the first move in the window is named: down to 0 in 2020Q2 ...
    assert rows["2020Q4"]["why_avg4"] == (
        "book moved more than the jump in this window: 2020Q2 -100.0% against the quarter before")
    # ... and once that is outside it, back up from 0 in 2020Q3
    assert rows["2021Q1"]["why_avg4"] == (
        "book moved more than the jump in this window: 2020Q3 from 0 to above 0")


def test_a_balance_of_zero_gives_none_not_a_division_error():
    data = flat([1, 2], bal=1000, p9=10)
    data["20200630"][0]["LNCRCD"] = 0
    data["20200930"][0]["LNCRCD"] = -5
    rows = by_q(book(data, 1))
    for q in ("2020Q2", "2020Q3"):
        assert rows[q]["rate"] is None and rows[q]["kept"] is False
        assert rows[q]["why"] == WHY_NO_BOOK
    # the same with no minimum at all and the bank exempt
    assert by_q(book(data, 1, exempt=True))["2020Q2"]["rate"] is None
    # an industry of nothing but zero books has no rate either
    zero = {q: [row(1, q, 0)] for q in QS}
    assert all(r["rate"] is None for r in industry_delinquency(zero, CARD, "nonaccrual"))
    comp = composite_delinquency({"1": book(zero, 1)}, ["1"], 1)
    assert all(r["rate"] is None and r["banks"] == 0 for r in comp)


# ------------------------------------------------------------------ the other rules

def test_under_the_minimum_unless_exempt():
    data = flat([1], bal=500, p9=10)
    r = book(data, 1, min_book=1000)[0]
    assert (r["rate"], r["why"], r["balance"], r["numerator"]) == (None, WHY_SMALL, 500, 10)
    assert book(data, 1, min_book=1000, exempt=True)[0]["rate"] == pytest.approx(2.0)
    assert book(data, 1, min_book=500)[0]["rate"] == pytest.approx(2.0)   # at the minimum is kept


def test_a_blank_field_is_not_filed_never_zero():
    data = flat([1, 2], bal=1000, p3=10, p9=5, na=3)
    del data["20200331"][0]["P3CRCD"]
    data["20200630"][0]["P3CRCD"] = None
    data["20200930"][0]["LNCRCD"] = None
    rows = by_q(book(data, 1, "30+ incl. nonaccrual"))
    assert rows["2020Q1"]["rate"] is None
    assert rows["2020Q1"]["why"] == "not filed this quarter: P3CRCD is blank"
    assert rows["2020Q2"]["why"] == "not filed this quarter: P3CRCD is blank"
    assert rows["2020Q3"]["why"] == "not filed this quarter: LNCRCD is blank"
    # a measure that does not use the blank field is unaffected
    assert by_q(book(data, 1, "90+ incl. nonaccrual"))["2020Q1"]["rate"] == pytest.approx(0.8)
    # the industry leaves the blank filer out of both sums
    ind = by_q(industry_delinquency(data, CARD, "30+ incl. nonaccrual"))
    assert ind["2020Q1"]["banks"] == 1 and ind["2020Q1"]["rate"] == pytest.approx(1.8)
    # and with nobody filing a field, there is no industry rate, not 0
    for q in QS:
        for r in data[q]:
            r["P3CRCD"] = None
    assert all(r["rate"] is None and r["numerator"] is None and r["banks"] == 0
               for r in industry_delinquency(data, CARD, "30-89"))


def test_four_quarter_average_needs_four_present_consecutive_rates():
    data = flat([1], bal=1000, p9=10)
    data["20200930"][0]["P9CRCD"] = 30
    rows = book(data, 1)
    assert [r["why_avg4"] for r in rows[:3]] == [WHY_FEWER_THAN_FOUR] * 3
    assert rows[3]["avg4"] == pytest.approx((1 + 1 + 3 + 1) / 4)
    # a quarter-end the data skips breaks every window across it
    gap = {q: v for q, v in data.items() if q != "20201231"}
    rows = by_q(book(gap, 1))
    assert rows["2021Q1"]["avg4"] is None and rows["2021Q1"]["why_avg4"] == WHY_FEWER_THAN_FOUR
    # a rate left out inside the window is named
    data["20200630"][0]["LNCRCD"] = 990       # under the minimum, not a jump
    rows = by_q(book(data, 1, min_book=995))
    assert rows["2020Q4"]["avg4"] is None
    assert rows["2020Q4"]["why_avg4"] == (
        "a quarter-end rate in the window is None: 2020Q2 (book under the minimum)")


def test_a_skipped_quarter_breaks_every_average_across_it_and_says_so():
    """The data skips 2020Q4. No four-quarter average, bank, composite or
    industry, spans the gap; and a bank's ``why_avg4`` gives the reason
    wherever in i-2..i the gap sits, so an average that is None always has
    one."""
    qs = QS + ["20210930"]
    data = {q: v for q, v in flat([1, 2], bal=1000, p9=10, qs=qs).items() if q != "20201231"}
    books = {str(c): book(data, c) for c in (1, 2)}
    comp = by_q(composite_delinquency(books, ["1", "2"], 1))
    ind = by_q(industry_delinquency(data, CARD, "90+ accruing"))
    for q in ("2021Q1", "2021Q2", "2021Q3"):
        assert comp[q]["rate"] == pytest.approx(1.0) and comp[q]["avg4"] is None, q
        assert ind[q]["rate"] == pytest.approx(1.0) and ind[q]["avg4"] is None, q
        assert by_q(books["1"])[q]["why_avg4"] == WHY_FEWER_THAN_FOUR, q
    for r in books["1"]:
        assert (r["avg4"] is None) == (r["why_avg4"] is not None), r["q"]


def test_composite_four_quarter_average_is_the_mean_of_its_quarter_end_rates():
    data = flat([1, 2], bal=1000, p9=10)
    data["20201231"][1]["P9CRCD"] = 50
    books = {str(c): book(data, c) for c in (1, 2)}
    comp = composite_delinquency(books, ["1", "2"], 2)
    rates = [r["rate"] for r in comp]
    assert rates[3] == pytest.approx(3.0)
    assert [r["avg4"] for r in comp[:3]] == [None] * 3
    assert comp[3]["avg4"] == pytest.approx(sum(rates[:4]) / 4)
    assert comp[5]["avg4"] == pytest.approx(sum(rates[2:6]) / 4)
    # one composite quarter under min_banks blanks every average across it
    books["2"] = [dict(r, kept=False, rate=None) if r["q"] == "2020Q3" else r
                  for r in books["2"]]
    comp = by_q(composite_delinquency(books, ["1", "2"], 2))
    assert comp["2020Q3"]["rate"] is None
    assert all(comp[q]["avg4"] is None for q in ("2020Q4", "2021Q1", "2021Q2"))


def test_composite_average_leaves_out_the_banks_the_band_leaves_out():
    """Bank 2 grows 40% into 2020Q4: its own four-quarter average is blanked
    there and in the two quarters after, so the band on that basis leaves it
    out, and so does the composite's average (the bank's decision, 12 Oct
    2026): each of the four quarter-end rates is recomputed without it, and
    ``avg4_left_out`` names it."""
    data = flat([1, 2, 3], bal=1000, p9=10)
    for c in (1, 3):                                   # bank 2's rate differs from the others'
        for q in data:
            data[q][c - 1]["P9CRCD"] = 10 * c
    for q in ("20201231", "20210331", "20210630"):
        data[q][1]["LNCRCD"] = 1400
    books = {str(c): book(data, c) for c in (1, 2, 3)}
    comp = by_q(composite_delinquency(books, ["1", "2", "3"], 1))
    assert [comp[q]["avg4_left_out"] for q in sorted(comp)] == [[], [], [], ["2"], ["2"], ["2"]]
    without = by_q(composite_delinquency(books, ["1", "3"], 1))
    with_ = [r["rate"] for r in composite_delinquency(books, ["1", "2", "3"], 1)]
    for q in ("2020Q4", "2021Q1", "2021Q2"):
        assert comp[q]["avg4"] == pytest.approx(without[q]["avg4"]), q
        assert comp[q]["avg4"] != pytest.approx(sum(with_[:4]) / 4), q
    # outside the jump the average is the plain mean of the composite rates, bank 2 in
    assert comp["2020Q3"]["avg4"] is None                       # only three quarters by then
    # the quarter-end composite is never touched by the jump
    assert comp["2020Q4"]["rate"] == pytest.approx(with_[3]) and comp["2020Q4"]["banks"] == 3
    band = by_q(band_delinquency(books, ["1", "2", "3"], "four-quarter average", min_banks=1))
    assert band["2020Q4"]["banks"] == 2
    # leaving a bank out can take a quarter below the banks needed: then no average
    assert by_q(composite_delinquency(books, ["1", "2", "3"], 3))["2020Q4"]["avg4"] is None
    # kept only at i-3 of 2021Q1's window (2020Q2) still counts as left out there
    gone = ("2020Q3", "2020Q4", "2021Q1")
    books["2"] = [dict(r, kept=False, rate=None) if r["q"] in gone else r for r in books["2"]]
    assert by_q(composite_delinquency(books, ["1", "2", "3"], 1))["2021Q1"]["avg4_left_out"] == ["2"]
    # a bank kept in none of the four composite quarters was never in, so is not named
    books["2"] = [dict(r, kept=False, rate=None) for r in books["2"]]
    assert all(r["avg4_left_out"] == [] for r in composite_delinquency(books, ["1", "2", "3"], 1))


def test_composite_average_with_no_jump_is_the_mean_of_its_quarter_end_rates():
    data = flat([1, 2], bal=1000, p9=10)
    for q in data:
        data[q][1]["P9CRCD"] = 30
    books = {str(c): book(data, c) for c in (1, 2)}
    comp = composite_delinquency(books, ["1", "2"], 2)
    rates = [r["rate"] for r in comp]
    assert comp[3]["avg4"] == pytest.approx(sum(rates[:4]) / 4)
    assert all(r["avg4_left_out"] == [] for r in comp)


def test_band_is_percentile_inc_of_the_kept_rates_on_each_basis():
    certs = [1, 2, 3, 4, 5]
    data = {q: [row(c, q, 1000, p9=10 * c) for c in certs] for q in QS}
    data["20200930"] = [r for r in data["20200930"] if r["CERT"] != 5]
    books = {str(c): book(data, c) for c in certs}
    keys = [str(c) for c in certs]
    band = by_q(band_delinquency(books, keys, "quarter-end", min_banks=3))
    assert band["2020Q1"]["banks"] == 5
    for p in (10, 25, 75, 90):
        assert band["2020Q1"]["p%g" % p] == percentile([1, 2, 3, 4, 5], p)
        assert band["2020Q3"]["p%g" % p] == percentile([1, 2, 3, 4], p)
    avg = by_q(band_delinquency(books, keys, "four-quarter average", min_banks=3))
    assert avg["2020Q4"]["banks"] == 4                # bank 5's window holds the gap
    assert avg["2020Q4"]["p90"] == percentile([1, 2, 3, 4], 90)
    assert avg["2020Q3"]["banks"] == 0 and avg["2020Q3"]["p10"] is None
    few = by_q(band_delinquency(books, keys, "quarter-end", min_banks=6))
    assert few["2020Q1"]["p10"] is None and few["2020Q1"]["banks"] == 5
    # exactly the banks needed is enough
    just = by_q(band_delinquency(books, keys, "quarter-end", min_banks=5))
    assert just["2020Q1"]["p10"] == percentile([1, 2, 3, 4, 5], 10)
    assert just["2020Q3"]["p10"] is None and just["2020Q3"]["banks"] == 4


def test_industry_sums_every_filer_and_averages_its_quarter_end_rates():
    data = {q: [row(1, q, 1000, na=10), row(2, q, 3000, na=10 * (i + 1)),
                row(3, q, 50, na=0)] for i, q in enumerate(QS)}
    ind = industry_delinquency(data, CARD, "nonaccrual")
    want = [100 * (10 + 10 * (i + 1)) / 4050 for i in range(len(QS))]
    assert [r["rate"] for r in ind] == pytest.approx(want)
    assert [r["banks"] for r in ind] == [3] * len(QS)
    assert ind[0]["date"] == "2020-03-31" and ind[0]["q"] == "2020Q1"
    assert [r["avg4"] for r in ind[:3]] == [None] * 3
    assert ind[4]["avg4"] == pytest.approx(sum(want[1:5]) / 4)


def test_values_feed_write_series(tmp_path):
    data = flat([1], bal=1000, p9=10)
    rows = book(data, 1)
    assert values(rows, "quarter-end")[0] == ("2020Q1", 1.0)
    assert values(rows, "four-quarter average")[:4] == [
        ("2020Q1", None), ("2020Q2", None), ("2020Q3", None), ("2020Q4", 1.0)]
    path = write_series(values(rows, "four-quarter average"), tmp_path / "s.csv",
                        "KeyBank-style test series")
    pts = read_series(path)
    assert [p.date for p in pts] == ["2020-12-31", "2021-03-31", "2021-06-30"]


# ------------------------------------------------------------------ the fixture

@pytest.fixture(scope="module")
def roster_data():
    return json.loads((PEERS / "delinquency_roster.json").read_text())


def test_fixture_holds_every_roster_bank_every_quarter_and_field(roster_data):
    assert len(roster_data) == 38
    assert min(roster_data) == "20170331" and max(roster_data) == "20260630"
    want = {"CERT", "REPDTE"} | set(fields_for(CONSUMER))
    for q, rows in roster_data.items():
        assert sorted(str(r["CERT"]) for r in rows) == sorted(b["cert"] for b in ROSTER), q
        for r in rows:
            assert set(r) == want | {"RSSDHCR"} and r["REPDTE"] == q
            assert all(r[f] is not None for f in want), (q, r["CERT"])
            # the parent is blank only for Zions, after its holding company merged into the bank
            assert r["RSSDHCR"] is not None or (str(r["CERT"]) == "2270" and q >= "20180930"), (q, r["CERT"])


def test_keybank_2026q2_against_the_filed_amounts(roster_data):
    """The amounts are KeyBank's 2026Q2 values from the FDIC API as the fixture
    holds them ($000), not read off the RC-N filing; the rates are the
    arithmetic on them."""
    filed = {
        "Credit card": (926589, 8528, 9346, 6401),
        "Mortgage": (20584113, 23309, 15000, 120395),
        "Home equity": (2929570, 15639, 2072, 54307),
        # RC-C 6.d 4,200,208 plus 6.b 268,825: RC-N 5.c's past-due lines
        # include other revolving credit plans, so the balance does too
        "Other consumer": (4469033, 27723, 21007, 4680),
        "Auto": (62212, 302, 23, 371),
    }
    for product, (bal, p3, p9, na) in filed.items():
        nums = {"30-89": p3, "90+ accruing": p9, "nonaccrual": na,
                "90+ incl. nonaccrual": p9 + na, "30+ incl. nonaccrual": p3 + p9 + na}
        for measure, n in nums.items():
            got = by_q(bank_delinquency(roster_data, KEYBANK, product, measure,
                                        0.25, 1_000_000, True, acquired=()))["2026Q2"]
            assert (got["numerator"], got["balance"]) == (n, bal), (product, measure)
            assert got["rate"] == 100 * n / bal, (product, measure)
    # without the exemption, KeyBank's $62m auto book is under a $1bn minimum
    auto = by_q(bank_delinquency(roster_data, KEYBANK, "Auto", "nonaccrual",
                                 0.25, 1_000_000, False, acquired=()))["2026Q2"]
    assert auto["rate"] is None and auto["why"] == WHY_SMALL


def test_fixture_composite_band_and_industry_hold_together(roster_data):
    for product in CONSUMER:
        for measure in MEASURES:
            books = {c: bank_delinquency(roster_data, c, product, measure, 0.25,
                                         1_000_000, c == KEYBANK, acquired=())
                     for c in [b["cert"] for b in ROSTER]}
            comp = by_q(composite_delinquency(books, PEER_CERTS, 5))
            last = comp["2026Q2"]
            kept = [by_q(books[c])["2026Q2"] for c in PEER_CERTS]
            kept = [r for r in kept if r["kept"]]
            assert last["banks"] == len(kept)
            if len(kept) >= 5:
                assert last["rate"] == pytest.approx(
                    100 * sum(r["numerator"] for r in kept) / sum(r["balance"] for r in kept))
            band = by_q(band_delinquency(books, PEER_CERTS, "quarter-end", min_banks=5))["2026Q2"]
            if band["p10"] is not None:
                assert band["p10"] <= band["p25"] <= band["p75"] <= band["p90"]
            ind = industry_delinquency(roster_data, product, measure)
            assert ind[-1]["banks"] == 16
            assert ind[-1]["rate"] == pytest.approx(
                100 * sum(r["numerator"] for r in books.values() for r in [by_q(r)["2026Q2"]])
                / sum(by_q(r)["2026Q2"]["balance"] for r in books.values()))


def test_fixture_composite_leaves_jpmorgan_out_through_first_republic(roster_data):
    """JPMorgan's mortgage book in 2023Q2-Q4, the First Republic quarters: its
    own four-quarter average is blanked by the jump, and the composite's
    average leaves it out: where it is the only bank left out, the average
    equals the composite of the pack without it."""
    books = {c: bank_delinquency(roster_data, c, "Mortgage", "nonaccrual", 0.25, 1_000_000, False, acquired=())
             for c in PEER_CERTS}
    comp = by_q(composite_delinquency(books, PEER_CERTS, 5))
    rest = by_q(composite_delinquency(books, [c for c in PEER_CERTS if c != "628"], 5))
    for q in ("2023Q2", "2023Q3", "2023Q4"):
        assert by_q(books["628"])[q]["why_avg4"].startswith(WHY_JUMP_PREFIX), q
        assert "628" in comp[q]["avg4_left_out"], q
        if comp[q]["avg4_left_out"] == ["628"]:
            assert comp[q]["avg4"] == pytest.approx(rest[q]["avg4"]), q
    left = {(c, q) for q, r in comp.items() for c in r["avg4_left_out"]}
    kept_jumped = {(c, r["q"]) for c in PEER_CERTS for r in books[c]
                   if r["kept"] and (r["why_avg4"] or "").startswith(WHY_JUMP_PREFIX)}
    assert kept_jumped <= left



def test_other_consumer_before_2001_names_the_line_not_filed():
    """6.b (LNCONRP) is blank before 2001Q1: the balance is not filed, and
    the reason names LNCONRP, not the sum (review, 14 Oct 2026)."""
    from threshold_engine.peers.delinquency import DEFINITIONS, bank_delinquency
    row = {"CERT": 1, "LNCONOTH": 500.0, "LNCONRP": None, "P3CONOTH": 5.0, "P9CONOTH": 1.0, "NACONOTH": 1.0}
    data = {"20001231": [dict(row, REPDTE="20001231")],
            "20010331": [dict(row, REPDTE="20010331", LNCONRP=100.0)]}
    rows = bank_delinquency(data, "1", "Other consumer", "30-89", 1.0, 0, False, acquired=())
    assert rows[0]["rate"] is None and rows[0]["why"] == "not filed this quarter: LNCONRP is blank"
    assert rows[1]["rate"] == 100 * 5 / 600
    assert "no other consumer delinquency rate is written before then" in DEFINITIONS["Other consumer"]
