"""The commercial products (16 Oct 2026): C&I, construction, multifamily,
nonfarm nonresidential and its owner-occupied and other splits, built by the
same peers code as the consumer products, with one difference the binding
rules require: a blank commercial field is not filed, never 0.

The fixture, tests/data/peers/commercial_2007.json, is five filers, 2006Q3 to
2008Q2, as the FDIC API returned them on 16 Oct 2026 (see the README beside
it): KeyBank (17534, FFIEC 031) and JPMorgan (628, 031); Sovereign Bank
(29950), a savings institution on the TFR (CALLFORM 100), which never filed
the nonfarm split; Bank of China (33653, CALLFORM 2), which files a C&I
balance and no charge-off, past-due or nonaccrual field; and Graystone Bank
(58166, 041), which filed the nonfarm split as 0 and 0 through 2007 and
filed it from 2008Q1. KeyBank's 2007Q1 amounts below are the API's, written
out by hand from research-fdic.md, which tied them before this code existed;
the rates are arithmetic on the fixture's values, done here, not by the code
under test."""
import json

import pytest

from conftest import DATA, ROOT
from threshold_engine import cli
from threshold_engine.peers import analyses, books, fdic
from threshold_engine.peers import delinquency as D
from threshold_engine.peers import run
from threshold_engine.peers.books import (
    COMMERCIAL, CONSUMER, NOT_FILED, PRODUCTS, WHY_JUMP, WHY_NOT_FILED, WHY_SMALL, bank_book,
    filed_amount, industry, not_filed, restarted, without_repeats)

PEERS = DATA / "peers"
KEYBANK, JPM, TFR, NO_FLOWS, ZERO_SPLIT = "17534", "628", "29950", "33653", "58166"
OO, OTHER, NFNR = ("Owner-occupied nonfarm nonresidential", "Other nonfarm nonresidential",
                   "Nonfarm nonresidential")


@pytest.fixture(scope="module")
def data():
    return json.loads((PEERS / "commercial_2007.json").read_text())


def by_q(rows, key="quarter"):
    return {r[key]: r for r in rows}


def row(data, q, cert):
    return next(r for r in data[q] if str(r["CERT"]) == cert)


# ---------------------------------------------------------------- the products

def test_the_commercial_products_are_the_research_tables_fields():
    """research-fdic.md, section 1: balance, then gross charge-offs and
    recoveries year to date; past due 30-89, 90+ and nonaccrual."""
    assert COMMERCIAL == {
        "C&I": ("LNCI", "DRCI", "CRCI"),
        "Construction": ("LNRECONS", "DRRECONS", "CRRECONS"),
        "Multifamily": ("LNREMULT", "DRREMULT", "CRREMULT"),
        "Nonfarm nonresidential": ("LNRENRES", "DRRENRES", "CRRENRES"),
        OO: ("LNRENROW", "DRRENROW", "CRRENROW"),
        OTHER: ("LNRENROT", "DRRENROT", "CRRENROT"),
    }
    assert list(PRODUCTS) == list(CONSUMER) + list(COMMERCIAL)
    assert list(CONSUMER) == ["Credit card", "Mortgage", "Home equity", "Other consumer", "Auto"]
    assert {p: D.FIELDS[p] for p in COMMERCIAL} == {
        "C&I": ("LNCI", "P3CI", "P9CI", "NACI"),
        "Construction": ("LNRECONS", "P3RECONS", "P9RECONS", "NARECONS"),
        "Multifamily": ("LNREMULT", "P3REMULT", "P9REMULT", "NAREMULT"),
        "Nonfarm nonresidential": ("LNRENRES", "P3RENRES", "P9RENRES", "NARENRES"),
        OO: ("LNRENROW", "P3RENROW", "P9RENROW", "NARENROW"),
        OTHER: ("LNRENROT", "P3RENROT", "P9RENROT", "NARENROT"),
    }
    # Every commercial charge-off field reads a blank as not filed; no consumer one does.
    assert NOT_FILED == {f for names in COMMERCIAL.values() for f in names}
    assert not NOT_FILED & {f for names in CONSUMER.values() for n in names for f in n.split("+")}
    # The window and the internal import still offer the consumer five only.
    from threshold_engine import internal, launcher
    assert launcher.PEER_PRODUCTS == tuple(CONSUMER) and internal.PRODUCTS == tuple(CONSUMER)
    # Each commercial product's notes say what it is and that a blank is not filed.
    for p in COMMERCIAL:
        assert books.NOT_FILED_NOTE in books.DEFINITIONS[p], p
    for p in (OO, OTHER):
        assert "first filed 2007Q1" in books.DEFINITIONS[p]
        assert "labelled, not dropped" in books.DEFINITIONS[p]


def test_the_fixture_is_five_filers_eight_quarters_as_pulled(data):
    assert sorted(data) == ["20060930", "20061231", "20070331", "20070630", "20070930", "20071231",
                            "20080331", "20080630"]
    for q, rows in data.items():
        assert [str(r["CERT"]) for r in rows] == [JPM, KEYBANK, TFR, NO_FLOWS, ZERO_SPLIT], q
    k = row(data, "20070331", KEYBANK)
    # research-fdic.md, section 2.A: KeyBank 2007Q1, the splits adding to the total.
    assert (k["LNRENROW"], k["LNRENROT"], k["LNRENRES"]) == (4278597, 4495612, 8774209)
    assert k["LNRENROW"] + k["LNRENROT"] == k["LNRENRES"]
    assert k["LNRECONS"] == 8517744
    # Before 2007Q1 no filer files the split; the TFR filer never does here.
    for q in ("20060930", "20061231"):
        assert all(r["LNRENROW"] is None and r["DRRENROT"] is None for r in data[q])
    assert all(row(data, q, TFR)["LNRENROW"] is None for q in data)
    assert all(row(data, q, TFR)["LNRENRES"] > 0 for q in data)
    # The CALLFORM 2 filer: a C&I balance, never a charge-off or a past due.
    assert all(row(data, q, NO_FLOWS)["LNCI"] > 0 and row(data, q, NO_FLOWS)["DRCI"] is None
               and row(data, q, NO_FLOWS)["NACI"] is None for q in data)
    # Graystone: nonfarm loans, the split filed as 0 and 0 in 2007, then filed.
    for q in ("20070331", "20070630", "20070930", "20071231"):
        z = row(data, q, ZERO_SPLIT)
        assert z["LNRENRES"] > 0 and z["LNRENROW"] == 0 and z["LNRENROT"] == 0
    assert row(data, "20080331", ZERO_SPLIT)["LNRENROW"] > 0


# ---------------------------------------------------------------- not filed, never 0

def test_filed_amount_and_not_filed_read_a_commercial_blank_as_not_filed():
    r = {"CERT": 1, "REPDTE": "20070331", "LNCI": 100, "DRCI": None, "CRCI": "", "LNCRCD": None}
    assert filed_amount(r, "LNCI") == 100.0
    assert filed_amount(r, "DRCI") is None and filed_amount(r, "CRCI") is None
    assert filed_amount(r, "LNCRCD") == 0.0                 # a consumer blank stays 0
    assert not_filed(r, "C&I") == "DRCI"
    assert not_filed(r, "Credit card") is None
    assert not_filed({"LNCI": 1, "DRCI": 0, "CRCI": 0}, "C&I") is None
    with pytest.raises(ValueError, match="product must be one of"):
        not_filed(r, "Leases")


def test_a_split_before_2007_is_not_filed_never_a_jump_from_zero(data):
    """Read as 0, the 2006 quarters would be a book of 0 and 2007Q1 a jump
    from 0: the reason given would be wrong and the number a guess. The jump
    test of window i reads the moves into i-4 to i, so i-5 must be filed
    too: the first window that can be measured is 2008Q2 (2007Q3-2008Q2,
    the moves from 2007Q1 on)."""
    for p in (OO, OTHER):
        rows = by_q(bank_book(data, KEYBANK, p, 0.25, 0, exempt_min_book=True, acquired=(), stated=()))
        assert [q for q in rows] == ["2007Q3", "2007Q4", "2008Q1", "2008Q2"]
        assert rows["2007Q3"]["why"] == rows["2007Q4"]["why"] == rows["2008Q1"]["why"] == WHY_NOT_FILED, p
        assert rows["2008Q2"]["kept"], p
    # The rate, by hand: four flows from the year-to-date fields over four balances.
    ytd = {q: (row(data, q, KEYBANK)["DRRENROW"], row(data, q, KEYBANK)["CRRENROW"],
               row(data, q, KEYBANK)["LNRENROW"]) for q in data}
    flows = [(ytd["20070930"][0] - ytd["20070630"][0], ytd["20070930"][1] - ytd["20070630"][1]),
             (ytd["20071231"][0] - ytd["20070930"][0], ytd["20071231"][1] - ytd["20070930"][1]),
             (ytd["20080331"][0], ytd["20080331"][1]),
             (ytd["20080630"][0] - ytd["20080331"][0], ytd["20080630"][1] - ytd["20080331"][1])]
    avg = sum(ytd[q][2] for q in ("20070930", "20071231", "20080331", "20080630")) / 4
    got = by_q(bank_book(data, KEYBANK, OO, 0.25, 0, exempt_min_book=True, acquired=(), stated=()))["2008Q2"]
    assert got["gross_rate"] == pytest.approx(100 * sum(g for g, _ in flows) / avg)
    assert got["net_rate"] == pytest.approx(100 * sum(g - c for g, c in flows) / avg)
    # The TFR filer never filed the split: every window says so, none says jump or small.
    tfr = bank_book(data, TFR, OO, 0.25, 0, acquired=(), stated=())
    assert {r["why"] for r in tfr} == {WHY_NOT_FILED}
    # The CALLFORM 2 filer's C&I: a balance and no charge-offs is not filed, not a 0% rate.
    assert {r["why"] for r in bank_book(data, NO_FLOWS, "C&I", 0.25, 0, acquired=(), stated=())} == {WHY_NOT_FILED}
    # Read the consumer way (blank = 0), the split would have said something else.
    as_zero = {q: [{k: (0 if v is None and k in NOT_FILED else v) for k, v in r.items()} for r in rows]
               for q, rows in data.items()}
    whys = {r["why"] for r in bank_book(as_zero, TFR, OO, 0.25, 0, acquired=(), stated=())}
    assert whys == {WHY_SMALL}
    k = by_q(bank_book(as_zero, KEYBANK, OO, 0.25, 0, exempt_min_book=True, acquired=(), stated=()))
    assert k["2007Q3"]["why"] == WHY_JUMP


def test_the_industry_leaves_out_what_was_not_filed(data):
    """C&I: the CALLFORM 2 filer's balance is out of the denominator, since
    its charge-offs are not in the numerator. The split: no quarter before
    2007Q1 has a flow, so the first four-quarter window is 2007Q4, and the
    TFR filer is in the nonfarm total but not in the split."""
    ci = by_q(industry(data, "C&I"))
    qs = ("20070331", "20070630", "20070930", "20071231")
    filers = (JPM, KEYBANK, TFR, ZERO_SPLIT)
    assert ci["2007Q4"]["avg_balance"] == pytest.approx(
        sum(row(data, q, c)["LNCI"] for q in qs for c in filers) / 4)
    gross = sum(row(data, "20071231", c)["DRCI"] for c in filers)     # Q1 to Q4, year to date
    assert ci["2007Q4"]["gross"] == pytest.approx(gross)
    oo = by_q(industry(data, OO))
    assert list(oo) == ["2007Q4", "2008Q1", "2008Q2"]
    split = (JPM, KEYBANK, ZERO_SPLIT)
    assert oo["2007Q4"]["avg_balance"] == pytest.approx(
        sum(row(data, q, c)["LNRENROW"] for q in qs for c in split) / 4)
    # Graystone filed 0 and 0 in 2007: counted as filed, which is the labelled gap.
    assert all(row(data, q, ZERO_SPLIT)["LNRENROW"] == 0 for q in qs)
    total = by_q(industry(data, NFNR))
    assert total["2007Q4"]["avg_balance"] == pytest.approx(
        sum(row(data, q, c)["LNRENRES"] for q in qs for c in (JPM, KEYBANK, TFR, ZERO_SPLIT)) / 4)
    # Read the consumer way, the split's 2006 quarters would be flows of 0 and
    # balances of 0, and a window holding them, 2007Q3, would be written.
    as_zero = {q: [{k: (0 if v is None and k in NOT_FILED else v) for k, v in r.items()} for r in rows]
               for q, rows in data.items()}
    assert [r["quarter"] for r in industry(as_zero, OO)][0] == "2007Q3"


def test_the_summed_industry_counts_each_product_where_it_was_filed(data):
    """Construction + multifamily + nonfarm, as --industry-combined writes it
    for the comparison with the Federal Reserve's CRE line."""
    cre = by_q(industry(data, "Construction", ["Multifamily", NFNR]))
    parts = [by_q(industry(data, p)) for p in ("Construction", "Multifamily", NFNR)]
    for q in cre:
        assert cre[q]["avg_balance"] == pytest.approx(sum(p[q]["avg_balance"] for p in parts))
        assert cre[q]["gross"] == pytest.approx(sum(p[q]["gross"] for p in parts))
        assert cre[q]["recoveries"] == pytest.approx(sum(p[q]["recoveries"] for p in parts))


def test_delinquency_reads_the_split_as_not_filed_before_2007(data):
    k = by_q(D.bank_delinquency(data, KEYBANK, OO, "nonaccrual", 0.25, 0, True, acquired=(), stated=()), "q")
    assert k["2006Q4"]["rate"] is None and k["2006Q4"]["why"] == D.WHY_BLANK % "LNRENROW"
    r = row(data, "20070331", KEYBANK)
    assert k["2007Q1"]["rate"] == pytest.approx(100 * r["NARENROW"] / r["LNRENROW"])
    ind = by_q(D.industry_delinquency(data, OO, "30+ incl. nonaccrual"), "q")
    assert ind["2006Q4"]["banks"] == 0 and ind["2006Q4"]["rate"] is None
    assert ind["2007Q1"]["banks"] == 3                       # JPMorgan, KeyBank, Graystone
    ci = by_q(D.industry_delinquency(data, "C&I", "nonaccrual"), "q")
    assert ci["2008Q2"]["banks"] == 4                        # not the CALLFORM 2 filer
    assert ci["2008Q2"]["balance"] == sum(row(data, "20080630", c)["LNCI"]
                                          for c in (JPM, KEYBANK, TFR, ZERO_SPLIT))


# ---------------------------------------------------------------- the year-to-date fixes

def _two(parent_a, parent_b, ytd_a, ytd_b, field="DRCI", product_fields=("LNCI", "DRCI", "CRCI")):
    base = {f: 100 for f in product_fields}
    prev = dict(base, CERT=1, REPDTE="20070630", RSSDHCR=parent_a, **{field: ytd_a})
    now = dict(base, CERT=1, REPDTE="20070930", RSSDHCR=parent_b, **{field: ytd_b})
    return now, prev


def test_a_blank_commercial_year_to_date_is_not_a_fall():
    """The push-down rule reads a fall in any year-to-date field under a new
    parent as a restart. A commercial field gone blank has not fallen; a
    consumer one still reads as 0, as before."""
    now, prev = _two("A", "B", 50, None)
    assert restarted(now, prev) is False
    now, prev = _two("A", "B", 50, 10)
    assert restarted(now, prev) is True
    now, prev = _two("A", "B", 50, None, field="DRCRCD", product_fields=("LNCRCD", "DRCRCD", "CRCRCD"))
    assert restarted(now, prev) is True


def test_taking_off_a_repeated_year_to_date_leaves_a_blank_blank():
    data = {"20070630": [{"CERT": 1, "REPDTE": "20070630", "DRCI": None, "DRCRCD": None}],
            "20070930": [{"CERT": 1, "REPDTE": "20070930", "DRCI": None, "DRCRCD": None}]}
    repeats = [{"acquirer": "1", "absorbed": "2", "quarter": "20070630", "field": "DRCI", "amount": 5.0},
               {"acquirer": "1", "absorbed": "2", "quarter": "20070630", "field": "DRCRCD", "amount": 5.0}]
    out = without_repeats(data, repeats)
    assert out["20070630"][0]["DRCI"] is None and out["20070930"][0]["DRCI"] is None
    assert out["20070630"][0]["DRCRCD"] == -5.0             # the consumer reading, unchanged


def test_a_bank_added_pro_forma_that_did_not_file_the_product_is_not_filed(data):
    """JPMorgan with Sovereign added in, say, to 2008Q2: Sovereign filed no
    split, so no window of the combined split can be measured, rather than
    being read as JPMorgan alone."""
    rows = bank_book(data, JPM, OO, 0.25, 0, acquired=(), members=[(TFR, "20080630")], stated=())
    assert {r["why"] for r in rows} == {WHY_NOT_FILED}
    # The total, which Sovereign did file, combines as before.
    both = by_q(bank_book(data, JPM, NFNR, 10.0, 0, acquired=(), members=[(TFR, "20080630")], stated=()))
    alone = by_q(bank_book(data, JPM, NFNR, 10.0, 0, acquired=(), stated=()))
    assert both["2008Q1"]["kept"] and both["2008Q1"]["avg_balance"] > alone["2008Q1"]["avg_balance"]


def test_the_side_analyses_read_a_blank_as_not_filed(data):
    year = analyses.calendar_year(data, KEYBANK, OO, 2006)
    assert year == {"year": 2006, "net": None, "gross": None, "recoveries": None, "balance": None}
    y07 = analyses.calendar_year(data, KEYBANK, OO, 2007)
    r = row(data, "20071231", KEYBANK)
    assert y07["gross"] == r["DRRENROW"] and y07["net"] == r["DRRENROW"] - r["CRRENROW"]
    trend = {t["quarter"]: t for t in analyses.balance_trend(data, KEYBANK, OO)}
    assert trend["2006Q4"]["balance"] is None and trend["2007Q1"]["change"] is None
    assert trend["2007Q2"]["change"] == row(data, "20070630", KEYBANK)["LNRENROW"] - 4278597


# ---------------------------------------------------------------- pull and build

class Fake:
    """The FDIC API over the fixture: the fields asked for, nulls where a row
    lacks one, and no history."""

    def __init__(self, data):
        self.data, self.urls = data, []

    def __call__(self, url):
        import urllib.parse
        self.urls.append(url)
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        if url.startswith(fdic.HISTORY_URL):
            return {"data": [], "meta": {"total": 0}}
        asked = q["fields"][0].split(",")
        rows = [{f: r.get(f) for f in asked} for r in self.data[q["filters"][0].split(":")[1]]]
        offset, limit = int(q["offset"][0]), int(q["limit"][0])
        return {"data": [{"data": r} for r in rows[offset:offset + limit]], "meta": {"total": len(rows)}}


def test_pull_asks_for_every_commercial_field(data, tmp_path, monkeypatch, capsys):
    fake = Fake(data)
    monkeypatch.setattr(fdic, "urllib_fetch", fake)
    cache = tmp_path / "cache"
    assert cli.main(["peers", "pull", "--cache", str(cache), "--first", "2006Q3", "--last", "2008Q2",
                     "--products"] + list(COMMERCIAL) + ["--delinquency", "yes"]) == 0
    import urllib.parse
    asked = urllib.parse.parse_qs(urllib.parse.urlsplit(fake.urls[0]).query)["fields"][0].split(",")
    want = run.charge_off_fields(list(COMMERCIAL)) + [books.PARENT] + D.fields_for(COMMERCIAL)
    assert set(asked) == {"CERT", "REPDTE"} | set(want)
    assert len(list(cache.glob("q*.json"))) == 8
    # A null came back as a null and was cached as one, never as a 0.
    cached = json.loads((cache / "q20061231.json").read_text())
    assert all(r["LNRENROW"] is None for r in cached)


@pytest.fixture(scope="module")
def built(data, tmp_path_factory):
    base = tmp_path_factory.mktemp("commercial")
    cache = base / "cache"
    cache.mkdir()
    for q, rows in data.items():
        (cache / ("q%s.json" % q)).write_text(json.dumps(rows), encoding="utf-8")
    (base / "mergers.json").write_text("{}", encoding="utf-8")
    (base / "absorptions.json").write_text("[]", encoding="utf-8")
    out, series = base / "peers.xlsx", base / "series"
    mp = pytest.MonkeyPatch()
    mp.setattr(fdic, "urllib_fetch", lambda url: (_ for _ in ()).throw(AssertionError(url)))
    try:
        rc = cli.main(["peers", "build", str(out), "--cache", str(cache), "--roster",
                       str(ROOT / "config" / "peers.json"), "--series-dir", str(series),
                       "--first", "2006Q3", "--last", "2008Q2", "--products"] + list(COMMERCIAL) + [
            "--mergers", str(base / "mergers.json"), "--absorptions", str(base / "absorptions.json"),
            "--extra-acquisitions", "--industry-combined", "Construction+Multifamily+Nonfarm nonresidential",
            "--delinquency", "yes", "--reporting-changes", str(ROOT / "config" / "reporting-changes.json"),
            "--stated-acquisitions", "none",
            "--jump", "0.25", "--acquisition-share", "0.05", "--min-book", "0", "--exempt-self", "yes",
            "--pro-forma", "yes", "--pack", "all", "--min-banks", "5", "--rank-by", "net", "--last-n", "8",
            "--min-obs", "6", "--base-quarter", "2007Q4", "--index-min-book", "1000000",
            "--lagged-years", "2007", "--lag-years", "1", "--normalisation-years", "2007", "2007",
            "--mix-base-year", "2007"])
    finally:
        mp.undo()
    return dict(rc=rc, out=out, series=series)


def notes_and_rows(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln[2:] for ln in lines if ln.startswith("#")], [ln for ln in lines[1:] if not ln.startswith("#")]


def test_build_writes_the_commercial_series_with_their_notes(built, data):
    assert built["rc"] == 0 and built["out"].exists()
    s = built["series"]
    for p in COMMERCIAL:
        f = s / ("%s_industry_net.csv" % run.slug(p))
        assert f.exists(), f
        notes, _ = notes_and_rows(f)
        assert books.DEFINITIONS[p] in notes, p
    # The split: the industry's first window is 2007Q4; KeyBank's own starts 2008Q1.
    notes, rows = notes_and_rows(s / "owner-occupied-nonfarm-nonresidential_industry_net.csv")
    assert rows[1].startswith("2007-12-31,")
    assert any(n.startswith("reporting-change: 2008Q1, Loans classified as trading") for n in notes)
    notes, rows = notes_and_rows(s / "owner-occupied-nonfarm-nonresidential_keybank_net.csv")
    assert rows[1:] == [rows[1]] and rows[1].startswith("2008-06-30,")
    assert any("2007Q3 to 2008Q1" in n for n in notes)       # the left-out quarters, named
    # The 2007Q1 split change is linked to the note that says it, not said twice.
    notes, rows = notes_and_rows(
        s / "owner-occupied-nonfarm-nonresidential_industry_delinquency-nonaccrual_quarter-end.csv")
    assert rows[1].startswith("2007-03-31,")
    assert any(n.startswith("reporting-change: 2007Q1, Construction, nonfarm and lease splits. The note above "
                            "that says \"first filed 2007Q1\" describes this change.") for n in notes)
    # The CRE sum for the Federal Reserve comparison.
    f = s / "construction-multifamily-nonfarm-nonresidential_industry_net.csv"
    notes, rows = notes_and_rows(f)
    want = by_q(industry(data, "Construction", ["Multifamily", NFNR]))["2008Q2"]["net_rate"]
    assert float(rows[-1].split(",")[1]) == pytest.approx(want)
    # A commercial note never mentions the consumer definitions.
    assert not any("Securitized cards" in n or "6.d" in n for n in notes)
    # A summed series says each note once, though every product's definition ends with the same one.
    assert len(notes) == len(set(notes))
    assert notes.count(books.NOT_FILED_NOTE) <= 1


def test_a_product_list_too_long_for_its_note_is_counted_not_cut():
    """The peer workbook's one-line note for a product picked with nothing
    built named every product built; the six commercial names do not fit in
    a line, and the build refused. The consumer five still fit, word for
    word as before."""
    from threshold_engine.peers.peers_workbook import NOTE_CHARS, _not_built
    five = _not_built("charge-offs were", list(CONSUMER))
    assert five == ("No charge-offs were built for this product. The products built are: Credit card, Mortgage, "
                    "Home equity, Other consumer, Auto.")
    six = _not_built("delinquency was", list(COMMERCIAL))
    assert six == ("No delinquency was built for this product. 6 products were built; the product picker "
                   "lists them.")
    assert len(six) <= NOTE_CHARS and len(_not_built("charge-offs were", list(PRODUCTS))) <= NOTE_CHARS


# ---------------------------------------------------------------- review findings, 17 Oct 2026

def _ci(q, cert, bal, ytd, rec, parent="9"):
    """One C&I filing; None leaves a field blank, which is not filed."""
    return {"CERT": cert, "REPDTE": q, "LNCI": bal, "DRCI": ytd, "CRCI": rec, books.PARENT: parent}


SIX = ["20200331", "20200630", "20200930", "20201231", "20210331", "20210630"]


def test_the_first_window_is_not_marked_not_filed_by_the_last_quarter():
    """The not-filed test of window i reads quarters i-5 to i. For the first
    window (i = 4) i-5 is before the data, and read as index -1 it was the
    LAST quarter: a blank only in 2021Q2 dropped the 2021Q1 window, whose
    quarters 2020Q1 to 2021Q1 are all filed."""
    data = {q: [_ci(q, 1, 100000, 10 * (k % 4 + 1), 0)] for k, q in enumerate(SIX)}
    data[SIX[-1]] = [_ci(SIX[-1], 1, 100000, None, 0)]
    rows = by_q(bank_book(data, "1", "C&I", 0.25, 0, acquired=(), stated=()))
    assert rows["2021Q1"]["why"] is None and rows["2021Q1"]["kept"], rows["2021Q1"]
    assert rows["2021Q1"]["gross_rate"] == pytest.approx(100 * 40 / 100000)
    assert rows["2021Q2"]["why"] == WHY_NOT_FILED


def test_avg_balance_is_not_a_zero_for_a_bank_that_never_filed_the_split(data):
    """Read as 0, the TFR filer's split balance went to Data column G, which
    the balance charts read, as a book of 0."""
    rows = bank_book(data, TFR, OO, 0.25, 0, acquired=(), stated=())
    assert rows and all(r["why"] == WHY_NOT_FILED for r in rows)
    assert [(r["quarter"], r["avg_balance"]) for r in rows if r["avg_balance"] is not None] == []
    # The book's path is then not stated, and the line says why, not "fewer quarters held".
    assert books.balance_path(rows, 2) == ("Book: no four-quarter average balance in 2008Q1, 2008Q2 (a field "
                                           "of the product not filed), so its path over the last 2 quarters "
                                           "is not stated")


def test_avg_balance_does_not_average_a_blank_quarter_in_as_zero(data):
    """KeyBank's 2007Q3 window holds 2006Q4, when the split was not filed:
    three filed balances over four is no balance at all. A window whose own
    four quarters are filed keeps its average even when a quarter only the
    jump test reads (i-5, i-4) was blank: 2007Q4 is 2007Q1 to 2007Q4."""
    rows = by_q(bank_book(data, KEYBANK, OO, 0.25, 0, exempt_min_book=True, acquired=(), stated=()))
    assert row(data, "20061231", KEYBANK)["LNRENROW"] is None
    assert rows["2007Q3"]["why"] == WHY_NOT_FILED and rows["2007Q3"]["avg_balance"] is None
    four = ("20070331", "20070630", "20070930", "20071231")
    assert rows["2007Q4"]["why"] == WHY_NOT_FILED
    assert rows["2007Q4"]["avg_balance"] == pytest.approx(sum(row(data, q, KEYBANK)["LNRENROW"] for q in four) / 4)
    # A consumer product's blank is still 0, so nothing changes there.
    assert all(r["avg_balance"] is not None for r in bank_book(data, KEYBANK, "Credit card", 10.0, 0,
                                                               exempt_min_book=True, acquired=(), stated=()))


def test_the_workbook_writes_no_average_balance_where_the_window_is_not_filed(built):
    from openpyxl import load_workbook
    ws = load_workbook(built["out"])["Data"]
    head = [c.value for c in ws[1]]
    col = head.index("Average balance ($000)")
    hits = [r for r in ws.iter_rows(min_row=2, values_only=True)
            if any(v == "17534" or v == 17534 for v in r) and OO in r and "2007Q3" in r]
    assert hits, "KeyBank owner-occupied 2007Q3 is not on the Data tab"
    assert all(r[col] is None for r in hits), [(r[col], r[head.index("why") if "why" in head else -1]) for r in hits]


def test_a_summed_industry_is_not_written_where_one_of_its_products_was_not_filed(data):
    """C&I plus the owner-occupied split: no filer filed the split in 2006,
    so a window holding a 2006 quarter is C&I alone for part of it and must
    not be written under the two names."""
    alone = {r["quarter"] for r in industry(data, OO)}
    both = {r["quarter"] for r in industry(data, "C&I", [OO])}
    assert sorted(both - alone) == []
    assert both == alone == {"2007Q4", "2008Q1", "2008Q2"}


def test_the_industry_leaves_a_balance_out_where_its_flow_is_out():
    """Bank 2 left C&I blank in 2007Q1, so its 2007Q2 flow (measured from
    the blank) is out of the industry; its 2007Q2 balance must be out too,
    or the rate is 60 / 1750 rather than 60 / 1500."""
    qs = ["20070331", "20070630", "20070930", "20071231"]
    data = {}
    for k, q in enumerate(qs):
        ytd = 10 * (k + 1)
        data[q] = [_ci(q, 1, 1000, ytd, 0),
                   _ci(q, 2, None, None, None) if k == 0 else _ci(q, 2, 1000, ytd, 0)]
    ind = by_q(industry(data, "C&I"))
    assert ind["2007Q4"]["gross"] == pytest.approx(10 + 10 + 20 + 20)
    assert ind["2007Q4"]["avg_balance"] == pytest.approx((1000 + 1000 + 2000 + 2000) / 4)
    assert ind["2007Q4"]["gross_rate"] == pytest.approx(4.0)
    # The same quarters as consumer figures (a blank is 0) are unchanged.
    card = {q: [{"CERT": r["CERT"], "REPDTE": q, "LNCRCD": r["LNCI"], "DRCRCD": r["DRCI"], "CRCRCD": r["CRCI"],
                 books.PARENT: "9"} for r in rows] for q, rows in data.items()}
    c = by_q(industry(card, "Credit card"))
    assert c["2007Q4"]["avg_balance"] == pytest.approx((1000 + 2000 + 2000 + 2000) / 4)


def test_an_absorbed_book_not_filed_is_not_read_as_no_book():
    """Bank 2 never filed the split (its nonfarm total is 5,000 against bank
    1's split of 1,000), so its share of bank 1's split is unknown: the
    acquisition is not read as bringing in nothing."""
    q0, q1 = "20071231", "20080331"

    def r(q, cert, ow, nr):
        return {"CERT": cert, "REPDTE": q, "LNRENROW": ow, "DRRENROW": None if ow is None else 0,
                "CRRENROW": None if ow is None else 0, "LNRENRES": nr, books.PARENT: str(cert)}
    data = {q0: [r(q0, 1, 1000, 2000), r(q0, 2, None, 5000)], q1: [r(q1, 1, 1100, 7000)]}
    links = [{"acquirer": "1", "absorbed": "2", "quarter": "2008Q1"}]
    assert books.acquired_quarters(data, links, OO, 0.05) == {"1": [q1]}
    assert books.acquired_quarters(data, links, NFNR, 0.05) == {"1": [q1]}      # 5,000 of 2,000, measured
    # A consumer blank is still 0: an absorbed bank with no card book brings in none.
    card = {q: [{"CERT": x["CERT"], "REPDTE": q, "LNCRCD": None if x["CERT"] == 2 else 1000,
                 books.PARENT: "1"} for x in rows] for q, rows in data.items()}
    assert books.acquired_quarters(card, links, "Credit card", 0.05) == {}


def test_the_industry_note_counts_the_filers_in_the_series(built, data):
    """The CALLFORM 2 filer files no C&I charge-off field, so it is in no
    C&I industry series: the note must not say every filer is."""
    s = built["series"]
    notes, _ = notes_and_rows(s / "c-i_industry_net.csv")
    assert any("4 of the 5 filers in the cache in 2008Q2" in n for n in notes), notes
    assert not any("every filer in the cache (5 in 2008Q2)" in n for n in notes)
    assert books.industry_filers(data, ["C&I"], "20080630") == 4
    notes, _ = notes_and_rows(s / "c-i_industry_delinquency-nonaccrual_quarter-end.csv")
    assert any("4 of the 5 filers in the cache in 2008Q2" in n for n in notes), notes
    # The split: JPMorgan, KeyBank and Graystone.
    notes, _ = notes_and_rows(s / "owner-occupied-nonfarm-nonresidential_industry_net.csv")
    assert any("3 of the 5 filers in the cache in 2008Q2" in n for n in notes), notes
    # The CRE sum: every filer but the CALLFORM 2 one files the total.
    notes, _ = notes_and_rows(s / "construction-multifamily-nonfarm-nonresidential_industry_net.csv")
    assert any("4 of the 5 filers in the cache in 2008Q2" in n for n in notes), notes
