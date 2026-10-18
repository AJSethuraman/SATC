"""peers.flows: 30+ to charge-off, from synthetic Call Report rows worked by
hand. Every rule that leaves a quarter out is exercised once."""
import pytest

from threshold_engine.peers import flows as F
from threshold_engine.peers.books import WHY_ACQUIRED, WHY_JUMP, WHY_STATED

QS = ["20240331", "20240630", "20240930", "20241231", "20250331", "20250630", "20250930", "20251231"]


def row(q, cert="1", bal=1000, p3=30, p9=20, na=10, dr=None, **over):
    """A card filing: delinquent 60 by default; DR year to date, 12 a quarter unless given."""
    n = {"03": 1, "06": 2, "09": 3, "12": 4}[q[4:6]]
    r = {"CERT": cert, "REPDTE": q, "RSSDHCR": "9", "LNCRCD": bal, "P3CRCD": p3, "P9CRCD": p9, "NACRCD": na,
         "DRCRCD": 12 * n if dr is None else dr, "CRCRCD": 0}
    r.update(over)
    return r


def data_of(rows):
    out = {}
    for r in rows:
        out.setdefault(r["REPDTE"], []).append(r)
    for q in QS:
        out.setdefault(q, [])
    return out


def test_the_share_is_the_next_two_quarters_over_the_delinquent_stock():
    rows = F.bank_flow(data_of([row(q) for q in QS]), "1", "Credit card", 0.25, acquired=[], stated=[])
    by = {r["q"]: r for r in rows}
    assert by["2024Q2"]["delinquent"] == 60 and by["2024Q2"]["charged_off"] == 24
    assert by["2024Q2"]["rate"] == pytest.approx(40.0) and by["2024Q2"]["kept"]
    # the first Q1 flow is its year to date (12), the Q2 flow 24 - 12 = 12
    assert by["2024Q4"]["charged_off"] == 24
    assert by["2025Q3"]["why"] == F.WHY_NEXT_MISSING and by["2025Q4"]["why"] == F.WHY_NEXT_MISSING
    assert by["2025Q2"]["avg4"] == pytest.approx(40.0) and by["2024Q3"]["why_avg4"] == F.WHY_FEWER_THAN_FOUR


def test_every_reason_a_quarter_is_left_out():
    rows = [row(q) for q in QS]
    rows[1] = row(QS[1], na="")                     # 2024Q2: a delinquency field blank
    rows[2] = row(QS[2], p3=0, p9=0, na=0)          # 2024Q3: no delinquent dollars
    rows[4] = row(QS[4], bal=1400)                  # 2025Q1: the balance jumps 40% (q+1 of 2024Q4)
    data = data_of(rows)
    data[QS[6]] = []                                # 2025Q3: the bank did not file
    out = {r["q"]: r for r in F.bank_flow(data, "1", "Credit card", 0.25, acquired=[], stated=[])}
    assert out["2024Q2"]["why"].startswith("not filed this quarter: NACRCD")
    assert out["2024Q3"]["why"] == F.WHY_NONE
    assert out["2024Q4"]["why"] == WHY_JUMP
    assert out["2025Q1"]["why"] == F.WHY_NEXT_NOT_FILED  # 2025Q3 not filed: no flow for 2025Q3, so none for q+2
    assert out["2025Q2"]["why"] == F.WHY_NEXT_NOT_FILED
    assert out["2025Q3"]["why"] == F.WHY_ABSENT
    assert out["2024Q1"]["kept"] and out["2024Q1"]["rate"] == pytest.approx(40.0)
    # an acquisition quarter in q+1..q+2 leaves q out, once the flows exist to measure
    out = {r["q"]: r for r in F.bank_flow(data_of([row(q) for q in QS]), "1", "Credit card", 0.25, acquired=[QS[3]],
                                                   stated=[])}
    assert out["2024Q2"]["why"] == WHY_ACQUIRED and out["2024Q3"]["why"] == WHY_ACQUIRED and out["2024Q1"]["kept"]


def test_a_stated_acquisition_leaves_its_quarters_out_with_its_own_reason():
    """The firm, 17 Oct 2026, question 14: every product's windows holding a
    stated acquisition are left out for its acquirer, 30+ to charge-off too.
    A recorded acquisition in the same quarters is named first."""
    data = data_of([row(q) for q in QS])
    out = {r["q"]: r for r in F.bank_flow(data, "1", "Credit card", 0.25, acquired=[], stated=[QS[3]])}
    assert out["2024Q2"]["why"] == WHY_STATED and out["2024Q3"]["why"] == WHY_STATED
    assert out["2024Q1"]["kept"] and out["2024Q4"]["kept"]
    both = {r["q"]: r for r in F.bank_flow(data, "1", "Credit card", 0.25, acquired=[QS[3]], stated=[QS[3]])}
    assert both["2024Q2"]["why"] == WHY_ACQUIRED
    with pytest.raises(TypeError, match="stated"):
        F.bank_flow(data, "1", "Credit card", 0.25, acquired=[])
    with pytest.raises(ValueError, match="stated is a list"):
        F.bank_flow(data, "1", "Credit card", 0.25, acquired=[], stated="20241231")


def test_the_composite_sums_kept_banks_and_needs_the_minimum():
    a = [row(q, "1") for q in QS]
    b = [row(q, "2", p3=300, p9=200, na=100, dr=None) for q in QS]        # delinquent 600, same flows: 4%
    data = data_of(a + b)
    books = {c: F.bank_flow(data, c, "Credit card", 0.25, acquired=[], stated=[]) for c in ("1", "2")}
    comp = {r["q"]: r for r in F.composite(books, ["1", "2"], 2)}
    assert comp["2024Q2"]["rate"] == pytest.approx(100 * 48 / 660) and comp["2024Q2"]["banks"] == 2
    one = {r["q"]: r for r in F.composite({"1": books["1"]}, ["1"], 2)}
    assert not one["2024Q2"]["kept"] and one["2024Q2"]["why"] == F.WHY_TOO_FEW % 2
    ind = {r["q"]: r for r in F.composite(books, ["1", "2"], 0)}
    assert ind["2024Q2"]["rate"] == comp["2024Q2"]["rate"]
    with pytest.raises(ValueError):
        F.composite(books, ["1"], -1)


def test_the_gap_is_mine_less_theirs_on_the_four_quarter_average():
    mine = [{"q": "2025Q1", "avg4": 80.0, "why_avg4": None}, {"q": "2025Q2", "avg4": None, "why_avg4": "x"}]
    theirs = [{"q": "2025Q1", "avg4": 88.4, "why_avg4": None}, {"q": "2025Q2", "avg4": 88.0, "why_avg4": None}]
    g = F.gap(mine, theirs)
    assert g[0]["avg4"] == pytest.approx(-8.4) and g[0]["kept"]
    assert g[1]["avg4"] is None and g[1]["why"].startswith("no four-quarter average of its own")
    assert F.values(g, "four-quarter average") == [("2025Q1", pytest.approx(-8.4)), ("2025Q2", None)]
