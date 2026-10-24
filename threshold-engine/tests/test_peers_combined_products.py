"""Combined products (the analyst, 17 Oct 2026: "can we do a composite of all
loans as a top line to select from? ... maybe i want to see unsecured loans +
credit cards or something"). "All consumer" is every product; "A + B" is two
or more. A combined product's filed fields are its parts' added together
before any rate is taken, so its rate is dollar-weighted and every rule runs
on the combined book. Synthetic filings, worked by hand."""
import pytest

from threshold_engine.peers import books, delinquency as D
from threshold_engine.peers.run import _products, slug

QS = ("20250331", "20250630", "20250930", "20251231", "20260331")
CARD_OTHER = "Credit card + Other consumer"


def filing(q, cert="1", **amounts):
    row = {"CERT": cert, "REPDTE": q, "RSSDHCR": "9"}
    row.update(amounts)
    return row


def test_members():
    assert books.members(books.ALL) == list(books.CONSUMER)          # the consumer five, never commercial
    assert "C&I" not in books.members(books.ALL)
    assert books.members(CARD_OTHER) == ["Credit card", "Other consumer"]
    assert books.members("Auto") == ["Auto"]
    for bad in ("Credit card + Credit card", "Credit card + Boats", "Credit card+Auto", "credit card", "", None,
                "Credit card + ", books.ALL + " + Auto"):
        assert not books.is_product(bad)
        with pytest.raises(ValueError, match="joined by"):
            books.members(bad)


def test_a_class_and_a_class_inside_it_may_not_be_combined():
    """Codex on #442: Nonfarm nonresidential's fields already hold its two
    splits, so a combination of both would count the split twice."""
    for bad in ("Nonfarm nonresidential + Owner-occupied nonfarm nonresidential",
                "Other nonfarm nonresidential + C&I + Nonfarm nonresidential"):
        assert not books.is_product(bad)
        with pytest.raises(ValueError, match="twice"):
            books.members(bad)
    assert books.members("Owner-occupied nonfarm nonresidential + Other nonfarm nonresidential") == [
        "Owner-occupied nonfarm nonresidential", "Other nonfarm nonresidential"]
    assert books.members("Nonfarm nonresidential + C&I") == ["Nonfarm nonresidential", "C&I"]


def test_fields_are_the_parts_summed():
    assert books._fields(CARD_OTHER) == ("LNCRCD+LNCONOTH+LNCONRP", "DRCRCD+DRCONOTH", "CRCRCD+CRCONOTH")
    assert D._fields("Mortgage + Auto") == ("LNRERSFM+LNAUTO", "P3RERSFM+P3AUTO", "P9RERSFM+P9AUTO",
                                            "NARERSFM+NAAUTO")
    assert len(books._fields(books.ALL)[0].split("+")) == 6        # other consumer's balance is two lines


def test_the_rate_is_dollar_weighted_from_summed_flows():
    # Card: 1,000 each quarter-end, 10 of charge-offs a quarter, 2 recovered.
    # Other consumer (6.d 2,500 + 6.b 500): 30 of charge-offs a quarter, none recovered.
    # Year to date, so Q1 filings restart.
    data = {}
    for q in QS:
        n = {"03": 1, "06": 2, "09": 3, "12": 4}[q[4:6]]
        data[q] = [filing(q, LNCRCD=1000, DRCRCD=10 * n, CRCRCD=2 * n,
                          LNCONOTH=2500, LNCONRP=500, DRCONOTH=30 * n, CRCONOTH=0)]
    row = books.bank_book(data, "1", CARD_OTHER, 0.25, 0, acquired=[])[-1]
    assert row["quarter"] == "2026Q1" and row["kept"]
    assert row["gross"] == 160 and row["recoveries"] == 8 and row["avg_balance"] == 4000
    assert row["net_rate"] == pytest.approx(100 * 152 / 4000)       # 3.8%, not the mean of 3.2% and 4.0%
    alone = [books.bank_book(data, "1", p, 0.25, 0, acquired=[])[-1]["net_rate"]
             for p in ("Credit card", "Other consumer")]
    assert alone == [pytest.approx(3.2), pytest.approx(4.0)]


def test_the_jump_is_measured_on_the_combined_book():
    # Card doubles in 2025Q3 (a jump on its own); the combined book moves 1,000 on 9,000, about 11%.
    data = {q: [filing(q, LNCRCD=1000 if q < "20250930" else 2000, DRCRCD=0, CRCRCD=0,
                       LNCONOTH=8000, LNCONRP=0, DRCONOTH=0, CRCONOTH=0)] for q in QS}
    assert books.bank_book(data, "1", "Credit card", 0.25, 0, acquired=[])[-1]["why"] == books.WHY_JUMP
    assert books.bank_book(data, "1", CARD_OTHER, 0.25, 0, acquired=[])[-1]["kept"]


def test_a_combined_delinquency_is_not_filed_when_a_part_is_not():
    row = filing("20101231", LNCRCD=100, P3CRCD=1, P9CRCD=1, NACRCD=1, LNAUTO=None, P3AUTO=None)
    assert D._filed(row, D._fields("Credit card + Auto")[1]) is None
    assert D._filed(row, D._fields("Credit card")[1]) == 1


def test_definitions_say_what_is_added_then_each_parts_own():
    said = books.definitions(CARD_OTHER)
    assert said[0].startswith("Credit card + Other consumer: Credit card, Other consumer added together")
    assert said[1:] == [books.DEFINITIONS["Credit card"], books.DEFINITIONS["Other consumer"]]
    assert books.definitions("Auto") == []
    assert D.GUARANTEED in D.comparability("Mortgage + Home equity", "90+ accruing")
    assert D.GUARANTEED not in D.comparability(CARD_OTHER, "90+ accruing")


def test_products_and_file_names():
    assert _products([books.ALL, CARD_OTHER, "Auto"]) == [books.ALL, CARD_OTHER, "Auto"]
    with pytest.raises(ValueError, match="joined by"):
        _products(["Credit card+Auto"])
    assert slug(books.ALL) == "all-consumer"
    assert slug(CARD_OTHER) == "credit-card-plus-other-consumer"
