"""Question 18 of the round 2 commercial docket (the firm, 18 Oct 2026,
"agreed with the recommendation"): *"A listed deal leaves out only the
portfolios it brought"*. Each stated acquisition (config/stated-acquisitions.json,
peers/stated.py) has a required ``products`` list with its source, and a deal
leaves out only those products' windows: charge-offs, the delinquency
average and 30+ to charge-off.
"""
import copy
import json

import pytest

from conftest import ROOT
from threshold_engine.peers import books, peers_workbook as PW, run, stated as ST
from test_stated_acquisitions import FILE, build_kw, cache_of, flat_book, good, refused

ALL = list(books.PRODUCTS)


# ---- the file in the repository ------------------------------------------------------------------------

def test_the_whole_banks_list_every_product_and_the_asset_purchases_what_their_source_shows():
    """JPMorgan/WaMu and M&T/Wilmington were whole banks: every product.
    Wells Fargo/GE Capital: the release gives the deal as C&I loans and
    leases. Capital One/GE Healthcare: the filing names the business, not its
    loans; the data shows C&I and nonfarm nonresidential moving; everything
    else is listed as not settled (the safe side)."""
    got = {e["acquirer"]: e for e in ST.load(FILE)}
    assert got["628"]["products"] == ALL and got["628"]["products_unsettled"] == []
    assert got["588"]["products"] == ALL and got["588"]["products_unsettled"] == []
    assert got["3511"]["products"] == ["C&I"] and got["3511"]["products_unsettled"] == []
    assert "$26.7 billion from commercial and industrial loans and leases (3/1/16 close)" in \
        got["3511"]["products_source"]
    assert got["4297"]["products"] == ALL
    assert got["4297"]["products_unsettled"] == [
        "Credit card", "Mortgage", "Home equity", "Other consumer", "Auto", "Construction", "Multifamily",
        "Owner-occupied nonfarm nonresidential", "Other nonfarm nonresidential"]
    for e in got.values():
        assert "research-breaks.md" in e["products_source"] or "filing quoted" in e["products_source"]


# ---- the refusals ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("over, says", [
    ({"products": ["Commercial real estate"]}, "products names 'Commercial real estate', not a product"),
    ({"products": ["All consumer"]}, "products names 'All consumer', not a product"),
    ({"products": []}, "products must name at least one product"),
    ({"products": "C&I"}, "products must be a list of product names"),
    ({"products": ["C&I", "C&I"]}, "products names C&I more than once"),
    ({"products_unsettled": ["Auto"]}, "products_unsettled names Auto, which products does not"),
    ({"products_unsettled": ["Cards"]}, "products_unsettled names 'Cards', not a product"),
    ({"products_unsettled": None}, "products_unsettled must be a list of product names"),
    ({"products": ["Nonfarm nonresidential"]},
     "products names Nonfarm nonresidential without Owner-occupied nonfarm nonresidential and Other nonfarm "
     "nonresidential, which it holds"),
    ({"products": ["Nonfarm nonresidential", "Other nonfarm nonresidential"]},
     "products names Nonfarm nonresidential without Owner-occupied nonfarm nonresidential, which it holds"),
    ({"products": ["Other nonfarm nonresidential"]},
     "products names Other nonfarm nonresidential without Nonfarm nonresidential, which holds it"),
    ({"products_source": ""}, "products_source must say, on one line, where the list of products comes from"),
    ({"products_source": "two\nlines"}, "products_source must say"),
])
def test_a_bad_products_list_is_refused_by_entry(tmp_path, over, says):
    raw = good()
    raw["acquisitions"][0].update(over)
    msg = refused(raw, tmp_path)
    assert "acquisition 1 (certificate 628, 2008Q3)" in msg and says in msg, msg


def test_the_three_keys_are_required(tmp_path):
    for key in ("products", "products_source", "products_unsettled"):
        raw = good()
        del raw["acquisitions"][0][key]
        assert "is missing %r (every key is required" % key in refused(raw, tmp_path)


def test_a_whole_and_both_its_splits_is_accepted():
    raw = good()
    raw["acquisitions"][0]["products"] = ["Nonfarm nonresidential", "Owner-occupied nonfarm nonresidential",
                                          "Other nonfarm nonresidential"]
    raw["acquisitions"][0]["products_unsettled"] = ["Other nonfarm nonresidential"]
    assert ST.check(raw)[0]["products_unsettled"] == ["Other nonfarm nonresidential"]


# ---- which products an entry touches -------------------------------------------------------------------

def test_for_product_keeps_only_the_deals_that_brought_the_product_or_a_part_of_it():
    entries = ST.load(FILE)
    quarters = ["20151231", "20160331"]
    assert ST.for_product(entries, "C&I", quarters) == {"3511": ["20160331"], "4297": ["20151231"]}
    assert ST.for_product(entries, "Construction", quarters) == {"4297": ["20151231"]}
    assert ST.for_product(entries, "Multifamily", ["20160331"]) == {}
    # A combined product is touched when any part is.
    assert ST.for_product(entries, "Construction + C&I", ["20160331"]) == {"3511": ["20160331"]}
    assert ST.for_product(entries, books.ALL, quarters) == {"4297": ["20151231"]}


def test_the_workbook_refuses_a_product_with_no_stated_mapping():
    with pytest.raises(ValueError, match="stated must give .* for every product drawn .*'C&I' has none"):
        PW._stated_for({"Construction": {}}, "C&I")
    assert PW._stated_for({"C&I": {"588": ["20110630"]}}, "C&I") == {"588": ["20110630"]}


# ---- the build: another product's deal leaves nothing out ----------------------------------------------

def listing(tmp_path, products, unsettled=()):
    """The repository's M&T entry, with ``products`` in place of every product."""
    raw = json.loads(FILE.read_text(encoding="utf-8"))
    mt = copy.deepcopy(next(e for e in raw["acquisitions"] if e["acquirer"] == "588"))
    mt.update(products=list(products), products_source="A test list.", products_unsettled=list(unsettled))
    raw["acquisitions"] = [mt]
    p = tmp_path / "stated-test.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    return p


def two_banks():
    """M&T and JPMorgan (a second bank keeps the composite going), each with a
    flat C&I book and the same flat construction book."""
    data = flat_book()
    for q, rows in flat_book(cert="628").items():
        data[q] = data[q] + rows
    for rows in data.values():
        for r in rows:
            r.update(LNRECONS=r["LNCI"], DRRECONS=r["DRCI"], CRRECONS=r["CRCI"], P3RECONS=r["P3CI"],
                     P9RECONS=r["P9CI"], NARECONS=r["NACI"])
    return data


BOTH = ["C&I", "Construction"]


def test_a_deal_that_brought_another_product_leaves_no_c_and_i_window_out(tmp_path):
    """M&T, listed as bringing Construction only: its C&I charge-offs, the
    C&I delinquency average and C&I 30+ to charge-off all run through 2011Q2,
    and the note says the deal leaves nothing out of C&I."""
    cache = cache_of(tmp_path, two_banks())
    run.build(tmp_path / "peers.xlsx", **build_kw(tmp_path, cache, delinquency=True, products=BOTH,
                                                  stated_acquisitions=listing(tmp_path, ["Construction"])))
    series = tmp_path / "series"
    net = (series / "banks" / "c-i_m-t_net.csv").read_text(encoding="utf-8")
    assert "date,value\n2011-03-31," in net and "2011-06-30," in net
    assert "(stated-test.json): none of the 1 in these quarters brought C&I, so nothing is left out for them: " \
           "M&T 2011Q2 (it brought Construction)." in net
    comp = (series / "c-i_pack-composite_delinquency-30-89_four-quarter-average.csv").read_text(encoding="utf-8")
    assert "blanked by a stated acquisition" not in comp
    flow = (series / "c-i_pack-composite_30-plus-to-charge-off_quarter-end.csv").read_text(encoding="utf-8")
    assert "none of the 1 in these quarters brought C&I" in flow
    # Construction, the product it brought, is left out, all three ways.
    cons_net = (series / "banks" / "construction_m-t_net.csv").read_text(encoding="utf-8")
    assert "date,value\n2012-06-30," in cons_net
    assert "(stated-test.json): 1 of the 1 in these quarters brought Construction, so each bank's windows " \
           "holding one are left out: M&T 2011Q2 (" in cons_net
    cons = (series / "construction_pack-composite_delinquency-30-89_four-quarter-average.csv").read_text(
        encoding="utf-8")
    assert "M&T (588) 2011Q2" in cons
    # The same deal listed as bringing C&I leaves the windows out, all three ways.
    run.build(tmp_path / "peers.xlsx", **build_kw(tmp_path, cache, delinquency=True, products=BOTH,
                                                  stated_acquisitions=listing(tmp_path, ["C&I"])))
    net = (series / "banks" / "c-i_m-t_net.csv").read_text(encoding="utf-8")
    assert "date,value\n2012-06-30," in net
    comp = (series / "c-i_pack-composite_delinquency-30-89_four-quarter-average.csv").read_text(encoding="utf-8")
    assert "blanked by a stated acquisition (an acquisition the FDIC record cannot see, listed with its " \
           "filing): M&T (588) 2011Q2" in comp


def test_the_flows_follow_the_products_list(tmp_path, monkeypatch):
    """30+ to charge-off: the bank's stated quarters reach flows.bank_flow
    only for a product the deal brought."""
    from threshold_engine.peers import flows as FL
    seen = {}
    real = FL.bank_flow

    def spy(data, cert, product, jump, *, acquired, stated):
        seen[(cert, product)] = list(stated)
        return real(data, cert, product, jump, acquired=acquired, stated=stated)
    monkeypatch.setattr(FL, "bank_flow", spy)
    cache = cache_of(tmp_path, two_banks())
    run.build(tmp_path / "peers.xlsx", **build_kw(tmp_path, cache, delinquency=True, products=BOTH,
                                                  stated_acquisitions=listing(tmp_path, ["Construction"])))
    assert seen[("588", "C&I")] == [] and seen[("588", "Construction")] == ["20110630"]
    run.build(tmp_path / "peers.xlsx", **build_kw(tmp_path, cache, delinquency=True, products=BOTH,
                                                  stated_acquisitions=listing(tmp_path, ["C&I"])))
    assert seen[("588", "C&I")] == ["20110630"] and seen[("588", "Construction")] == []


def test_the_delinquency_follows_the_products_list(tmp_path, monkeypatch):
    from threshold_engine.peers import delinquency as D
    seen = {}
    real = D.bank_delinquency

    def spy(data, cert, product, measure, *a, acquired, stated, **kw):
        seen[(cert, product)] = list(stated)
        return real(data, cert, product, measure, *a, acquired=acquired, stated=stated, **kw)
    monkeypatch.setattr(D, "bank_delinquency", spy)
    cache = cache_of(tmp_path, two_banks())
    run.build(tmp_path / "peers.xlsx", **build_kw(tmp_path, cache, delinquency=True, products=BOTH,
                                                  stated_acquisitions=listing(tmp_path, ["Construction"])))
    assert seen[("588", "C&I")] == [] and seen[("588", "Construction")] == ["20110630"]
    run.build(tmp_path / "peers.xlsx", **build_kw(tmp_path, cache, delinquency=True, products=BOTH,
                                                  stated_acquisitions=listing(tmp_path, ["C&I"])))
    assert seen[("588", "C&I")] == ["20110630"] and seen[("588", "Construction")] == []


def test_the_book_index_follows_the_products_list(tmp_path, monkeypatch):
    """Review, 19 Oct 2026: every stated quarter used to be added to every
    product's declared acquisitions, so a deal flattened the organic book
    index of products it did not bring (Wells Fargo's construction,
    multifamily and nonfarm in 2016Q1, for a C&I-only deal). Question 18:
    "A listed deal leaves out only the portfolios it brought"."""
    from openpyxl import load_workbook
    seen = {}
    real = PW.organic_index

    def spy(data, cert, product, base_quarter, acquisitions):
        seen[(str(cert), product)] = [books.label(books.quarter_end(a).replace("-", "")) for a in acquisitions]
        return real(data, cert, product, base_quarter, acquisitions)
    monkeypatch.setattr(PW, "organic_index", spy)
    cache = cache_of(tmp_path, two_banks())
    out = tmp_path / "peers.xlsx"
    run.build(out, **build_kw(tmp_path, cache, products=BOTH,
                              stated_acquisitions=listing(tmp_path, ["Construction"])))
    assert seen[("588", "C&I")] == [] and seen[("588", "Construction")] == ["2011Q2"]
    rows = {r[1]: r[2] for r in load_workbook(out)["Run"].iter_rows(values_only=True) if len(r) > 2 and r[1]}
    assert rows["M&T"] == "2011Q2 (stated: Construction)"
    assert rows["Declared acquisitions"] == "none"
    run.build(out, **build_kw(tmp_path, cache, products=BOTH, stated_acquisitions=listing(tmp_path, ["C&I"])))
    assert seen[("588", "C&I")] == ["2011Q2"] and seen[("588", "Construction")] == []


def test_the_note_names_the_deals_that_did_not_bring_the_product_beside_those_that_did():
    entries = [e for e in ST.load(FILE) if e["acquirer"] in ("3511", "4297")]
    names = {"3511": "Wells Fargo", "4297": "Capital One"}
    note = run.stated_note(FILE, entries, "Construction", names)
    assert "1 of the 2 in these quarters brought Construction, so each bank's windows holding one are left out: " \
           "Capital One 2015Q4 (" in note
    assert "listed because the source does not settle them: Credit card, Mortgage" in note
    assert note.endswith("The rest did not bring Construction, so nothing is left out for them: Wells Fargo 2016Q1 "
                         "(it brought C&I).")
    assert run.stated_note(None, entries, "C&I", names).endswith("(none read): none named, so none is read.")
    assert run.stated_note(FILE, [], "C&I", names).endswith("none in these quarters.")
