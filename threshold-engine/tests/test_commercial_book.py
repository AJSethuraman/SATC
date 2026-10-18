"""A commercial book: the words its reader sees, stated by the book.

The firm, 17 Oct 2026: *"names in this should be changed to be more
commercial ... product sounds consumer"*. A book states its ``kind``; a
commercial one says Portfolio wherever a consumer one says Product, shows the
portfolios under commercial names (NDFI in full; the firm asked only for more
commercial names, and these were proposed by the session that built the book
the same day, the firm not objecting), and keeps the Call Report's
own name beside each on the Glossary. A consumer book keeps Product exactly
as before. Also here: the display problems the example commercial build found
on 17 Oct 2026 (the Peers headings, the share panel's title, the industry's
caption, the Internal tab).

The commercial book is built end to end on tests/data/peers/commercial_2007.json
(five filers, 2006Q3 to 2008Q2, public FDIC data; its README says how it was
pulled), with at least one bank in a composite so the peer series are
written from the one peer the fixture holds.
"""
import json
import re

import pytest
from openpyxl import load_workbook

from conftest import DATA, ROOT
from test_book import write_book
from threshold_engine import book as BK
from threshold_engine import kinds as KD
from threshold_engine.peers import books, fdic

PEERS = DATA / "peers"
WORD = re.compile(r"\bproducts?\b", re.I)
BARE_NDFI = re.compile(r"(?<!\()\bNDFI\b(?!\))")
#: The fixture's series that the peers build writes (measured: C&I's net
#: charge-offs hold 4 quarters, the nonaccrual rates 8, or 6 for the parts).
SERIES = [("C&I", "Net charge-offs", "c-i", "net"), ("C&I", "Nonaccrual", "c-i", "delinquency-nonaccrual_quarter-end"),
          ("Nonfarm nonresidential CRE", "Nonaccrual", "nonfarm-nonresidential", "delinquency-nonaccrual_quarter-end"),
          ("Owner-occupied CRE", "Nonaccrual", "owner-occupied-nonfarm-nonresidential",
           "delinquency-nonaccrual_quarter-end"),
          ("Investor CRE (non-owner-occupied)", "Nonaccrual", "other-nonfarm-nonresidential",
           "delinquency-nonaccrual_quarter-end")]
#: What the commercial book says of its settings, which are the consumer
#: book's because the firm has chosen none for commercial.
PENDING = "Settings: the consumer book's, pending the firm's choice"
SOURCES = [("Industry", "industry"), ("Peer median", "pack-median"), ("Peer total", "pack-composite"),
           ("KeyBank", "keybank")]


# ---------------------------------------------------------------- the words

def test_the_commercial_words_and_names():
    t = KD.commercial_text
    assert t("Pick a product and a measure. Products: Owner-occupied nonfarm nonresidential, "
             "Other nonfarm nonresidential, Nonfarm nonresidential.") == (
        "Pick a portfolio and a measure. Portfolios: Owner-occupied CRE, Investor CRE (non-owner-occupied), "
        "Nonfarm nonresidential CRE.")
    # Said once, never twice; the Call Report's own words are left alone.
    assert t("Nonfarm nonresidential CRE") == "Nonfarm nonresidential CRE"
    assert t("Loans secured by owner-occupied nonfarm nonresidential properties") == \
        "Loans secured by owner-occupied nonfarm nonresidential properties"
    assert t("NDFI and margin-loan revision") == "Loans to nonbank financials (NDFI) and margin-loan revision"
    assert t(KD.NDFI) == KD.NDFI
    assert t("Product") == "Portfolio" and t("product's") == "portfolio's"


def test_a_formula_has_only_its_quoted_text_reworded():
    f = '=IF(SUMPRODUCT((A1:A3="x")*1)>0,"Refused: this product is not whole",PRODUCT(B1:B2))'
    assert KD._formula(f) == '=IF(SUMPRODUCT((A1:A3="x")*1)>0,"Refused: this portfolio is not whole",PRODUCT(B1:B2))'
    # A quoted string grown past Excel's 255 characters is split, joined by &.
    long_ = '="%s"' % ("NDFI " * 50).strip()
    out = KD._formula(long_)
    pieces = re.findall(r'"((?:[^"]|"")*)"', out)
    assert all(len(p) <= KD.LITERAL_MAX for p in pieces) and len(pieces) > 1
    assert "".join(pieces) == KD.commercial_text(("NDFI " * 50).strip())


# ---------------------------------------------------------------- the book states its kind

def test_a_book_without_a_kind_is_refused_by_name(tmp_path):
    p = write_book(tmp_path)
    raw = json.loads(p.read_text())
    del raw["kind"]
    p.write_text(json.dumps(raw))
    with pytest.raises(BK.BookError, match="missing 'kind'"):
        BK.load(p)


@pytest.mark.parametrize("over, said", [
    (dict(kind="retail"), "kind must be one of consumer, commercial"),
    (dict(kind=None), "kind must be one of consumer, commercial"),
    (dict(kind="consumer", parts=["Portfolio", "Measure", "Source"]),
     "a consumer book calls its first part 'Product', not 'Portfolio'"),
    (dict(kind="commercial"), "a commercial book calls its first part 'Portfolio', not 'Product'"),
])
def test_the_kind_is_checked_and_decides_the_first_part(tmp_path, over, said):
    with pytest.raises(BK.BookError, match=re.escape(said)):
        BK.load(write_book(tmp_path, **over))


def commercial_rows(names):
    return [{"Portfolio": n, "Measure": "Net", "Source": "Industry", "file": "files/cards_nco_ttm.csv"} for n in names]


def test_a_commercial_book_names_its_portfolios_by_the_commercial_names(tmp_path):
    over = dict(kind="commercial", parts=["Portfolio", "Measure", "Source"], compare=None, not_in_book=[])
    # The peers build's name is the Call Report's, not the one shown.
    with pytest.raises(BK.BookError, match="by the commercial names .*not 'Owner-occupied nonfarm nonresidential'"):
        BK.load(write_book(tmp_path, series=commercial_rows(["Owner-occupied nonfarm nonresidential"]), **over))
    bk = BK.load(write_book(tmp_path, series=commercial_rows(["Owner-occupied CRE", "C&I"]), **over))
    assert bk["kind"] == "commercial" and bk["decide"]["kind"] == "commercial"


def test_a_combined_portfolio_is_its_parts_commercial_names_joined(tmp_path):
    """The combined products (the other branch, merged 18 Oct 2026) in a
    commercial book: the parts' commercial names joined by " + ", as a
    consumer book joins its products' names, and what the workbook's
    rewording turns the build's name into; a whole with a part it holds is
    refused here as the build refuses it (books.INSIDE)."""
    pairs = {"C&I + Multifamily": "C&I + Multifamily",
             "Owner-occupied CRE + Investor CRE (non-owner-occupied)":
                 "Owner-occupied nonfarm nonresidential + Other nonfarm nonresidential",
             "Construction": "Construction"}
    for shown, built in pairs.items():
        assert KD.commercial_product(shown) == built
        assert KD.commercial_text(built) == shown
    for bad in ("Nonfarm nonresidential CRE + Owner-occupied CRE", "C&I + C&I", "All consumer",
                "Credit card + C&I", "C&I +", "Owner-occupied nonfarm nonresidential", None):
        assert KD.commercial_product(bad) is None, bad
    over = dict(kind="commercial", parts=["Portfolio", "Measure", "Source"], compare=None, not_in_book=[])
    bk = BK.load(write_book(tmp_path, series=commercial_rows(["C&I", "C&I + Multifamily"]), **over))
    assert {v[0] for v in bk["decide"]["parts"].values()} == {"C&I", "C&I + Multifamily"}
    with pytest.raises(BK.BookError, match="or two or more of them joined by ' \\+ ', not "
                                           "'Nonfarm nonresidential CRE \\+ Investor CRE"):
        BK.load(write_book(tmp_path, series=commercial_rows(
            ["Nonfarm nonresidential CRE + Investor CRE (non-owner-occupied)"]), **over))


def test_the_glossary_says_what_a_combined_portfolio_is_without_consumer_words():
    from threshold_engine import glossary as G
    term = {t: (m, c) for t, m, c in G.terms_for(KD.KINDS["commercial"], measures=())}["Combined product"]
    said = KD.commercial_text(" ".join(term))
    assert "All consumer" not in said and "auto" not in said.lower() and "Combined portfolio" not in said
    assert said.startswith("A portfolio made of others: two or more joined by ' + '.")
    assert "Nonfarm nonresidential CRE may not be joined with Owner-occupied CRE or Investor CRE" in said
    assert G.COMBINED_CHANGES in " ".join(term)
    consumer = {t: (m, c) for t, m, c in G.terms_for(KD.KINDS["consumer"], measures=())}["Combined product"]
    assert "All consumer" in consumer[0] and G.COMBINED_CHANGES in consumer[1]


def test_a_measures_terms_are_given_only_where_the_book_holds_that_measure():
    """The 30+ to charge-off, gap and minimum payment terms define measures:
    a book's Glossary gives each only when it holds a series of one of them.
    The names are the ones the builds write (the real commercial build of 18
    Oct 2026 gave a commercial Glossary all three, its series holding none)."""
    from threshold_engine import glossary as G
    from threshold_engine.peers import flows, large_banks
    assert G.MEASURE_TERMS["30+ to charge-off"] == (flows.MEASURE,)
    assert G.MEASURE_TERMS["Share paying only the minimum"] == tuple(large_banks.MEASURES)
    consumer = json.loads((ROOT / "books" / "consumer-public.json").read_text())
    gaps = G.MEASURE_TERMS["Gap to peers on 30+ to charge-off, Gap to industry on 30+ to charge-off"]
    assert set(gaps) == set(consumer["floor_off"])
    for kind in ("commercial", "consumer"):
        none = [t for t, _, _ in G.terms_for(KD.KINDS[kind], measures=("Net charge-offs", "Nonaccrual"))]
        assert not set(none) & set(G.MEASURE_TERMS), kind
        assert "Floor at zero" in none and "Measure" in none, kind
    for term, held in G.MEASURE_TERMS.items():
        for m in held:
            got = [t for t, _, _ in G.terms_for(KD.KINDS["consumer"], measures=("Net charge-offs", m))]
            assert term in got and not set(got) & (set(G.MEASURE_TERMS) - {term}), (term, m)
    # Where they were: after Combined product, in the order TERMS holds them.
    every = [t for t, _, _ in G.terms_for(KD.KINDS["consumer"],
                                          measures=[m for ms in G.MEASURE_TERMS.values() for m in ms])]
    assert every == [t for t, _, _ in G.TERMS if t not in G.INTERNAL_TAB_TERMS or KD.KINDS["consumer"]["internal_tab"]]


def test_a_commercial_glossary_defines_no_measure_its_book_does_not_hold(built):
    """Built end to end: the commercial fixture book holds net charge-offs and
    nonaccrual only, so its Glossary defines none of the three."""
    terms = {r[1].value for r in load_workbook(built["commercial"][0])["Glossary"].iter_rows()
             if isinstance(r[1].value, str)}
    assert "Floor at zero" in terms and not terms & set(MEASURE_TERM_NAMES)


MEASURE_TERM_NAMES = ("30+ to charge-off", "Gap to peers on 30+ to charge-off, Gap to industry on 30+ to charge-off",
                      "Share paying only the minimum")


def test_a_commercial_book_has_no_internal_or_loan_classes_section(tmp_path):
    over = dict(kind="commercial", parts=["Portfolio", "Measure", "Source"], compare=None, not_in_book=[],
                series=commercial_rows(["C&I"]))
    with pytest.raises(BK.BookError, match="internal: a commercial book has no Internal tab"):
        BK.load(write_book(tmp_path, internal={k: "x" for k in BK.INTERNAL_KEYS}, **over))
    with pytest.raises(BK.BookError, match="loan_classes: the classes file records each peer's consumer book"):
        BK.load(write_book(tmp_path, loan_classes={"file": "x", "cache": "y"}, **over))


def test_the_names_are_not_said_to_be_the_firms():
    """The firm asked only for more commercial names (17 Oct 2026); the names
    themselves were proposed by the session that built the book and the firm
    did not object. Nothing says the firm named them."""
    texts = list((ROOT / "src").rglob("*.py")) + [ROOT / "books" / "README.md",
                                                  ROOT / "books" / "commercial-public.json"]
    for p in texts:
        text = p.read_text(encoding="utf-8")
        assert "as the firm named" not in text and "firm's names" not in text, p
    assert "did not object" in (ROOT / "src" / "threshold_engine" / "kinds.py").read_text(encoding="utf-8")


def test_the_books_in_the_repository_state_their_kinds():
    assert json.loads((ROOT / "books" / "consumer-public.json").read_text())["kind"] == "consumer"
    bk = BK.load(ROOT / "books" / "commercial-public.json")
    assert bk["kind"] == "commercial"
    # The firm has chosen no commercial settings: the book says so in its
    # name (Summary's and Chart's titles, the Run tab's Measure line) and first note.
    assert bk["workbook"]["name"].endswith(PENDING)
    assert bk["decide"]["notes"][0].startswith(PENDING)
    assert {v[0] for v in bk["decide"]["parts"].values()} == set(KD.COMMERCIAL_NAMES.values())
    assert bk["decide"]["compare"] == ("KeyBank", "Peer median (15 banks)")
    assert bk["peers"]["first"] == "1991Q1" and bk["peers"]["min_book"] == 0
    # No extra acquisition: the consumer book's (Fifth Third, 6672=2022Q2) is a
    # consumer deal, and no commercial one is recorded. The acquisitions the
    # FDIC record cannot see come from the stated list (question 14).
    assert bk["peers"]["extra_acquisitions"] == []
    assert bk["peers"]["stated_acquisitions"] is not None
    assert bk["internal"] is None and bk["loan_classes"] is None
    # Question 3: nonaccrual leads every CRE portfolio.
    first = {}
    for p, m, _ in bk["decide"]["parts"].values():
        first.setdefault(p, m)
    assert {p: m for p, m in first.items() if p != "C&I"} == {p: "Nonaccrual" for p in first if p != "C&I"}
    # Question 4: each portfolio and measure has the median and the total beside it.
    srcs = {s for _, _, s in bk["decide"]["parts"].values()}
    assert srcs == {"Industry", "Peer median (15 banks)", "Peer total (15 banks)", "KeyBank"}


# ---------------------------------------------------------------- built end to end

def _book(base, data, kind):
    cache = base / "cache"
    cache.mkdir()
    for q, rows in data.items():
        (cache / ("q%s.json" % q)).write_text(json.dumps(rows), encoding="utf-8")
    (base / "mergers.json").write_text("{}", encoding="utf-8")
    (base / "absorptions.json").write_text("[]", encoding="utf-8")
    word = KD.KINDS[kind]["word"]
    shown = (lambda p: p) if kind == "commercial" else (
        lambda p: next(k for k, v in KD.COMMERCIAL_NAMES.items() if v == p))
    series = [{word: shown(p), "Measure": m, "Source": s, "file": "series/%s_%s_%s.csv" % (slug, f, ms)}
              for p, m, slug, ms in SERIES for s, f in SOURCES]
    name = json.loads((ROOT / "books" / "commercial-public.json").read_text())["workbook"]["name"]
    book = {"kind": kind, "workbook": {"name": name if kind == "commercial" else "Commercial", "unit": "%", "direction": "higher_is_worse",
                                        "frequency": "quarterly", "smoothing": 1, "floor_at_zero": True,
                                        "moderate_halfwidth": 0.5, "low_step": 1.0, "high_z": 2.5,
                                        "on_the_line": "worse", "half_lives": [], "percentiles": [50, 75, 90, 95],
                                        "horizon": 4, "min_history": 41},
            "parts": [word, "Measure", "Source"], "lines_from": {"part": "Source", "start": None},
            "series": series, "not_in_book": [], "compare": ["KeyBank", "Peer median"],
            "notes": ["A test book on the commercial fixture."],
            "peers": {"cache": str(cache), "roster": str(ROOT / "config" / "peers.json"), "series_dir": "series",
                      "first": "2006Q3", "last": "2008Q2", "products": list(books.COMMERCIAL),
                      "mergers": str(base / "mergers.json"), "absorptions": str(base / "absorptions.json"),
                      "extra_acquisitions": [], "industry_combined": [], "jump": 0.25, "acquisition_share": 0.05,
                      "min_book": 0, "exempt_self": True, "pro_forma": True, "pack": "all", "min_banks": 1,
                      "rank_by": "net", "last_n": 8, "min_obs": 6, "base_quarter": "2007Q4",
                      "index_min_book": 1000000, "lagged_years": [2007, 2007], "lag_years": 1,
                      "normalisation_years": [2007, 2007], "mix_base_year": 2007, "delinquency": True,
                      "stated_acquisitions": None},
            "internal": None, "loan_classes": None,
            "reporting_changes": str(ROOT / "config" / "reporting-changes.json"), "floor_off": [], "large_banks": None, "signals": None}
    p = base / "book.json"
    p.write_text(json.dumps(book), encoding="utf-8")
    return p


@pytest.fixture(scope="module")
def data():
    return json.loads((PEERS / "commercial_2007.json").read_text())


@pytest.fixture(scope="module")
def built(data, tmp_path_factory):
    out = {}
    mp = pytest.MonkeyPatch()
    mp.setattr(fdic, "urllib_fetch", lambda url: (_ for _ in ()).throw(AssertionError(url)))
    try:
        for kind in ("commercial", "consumer"):
            base = tmp_path_factory.mktemp(kind)
            said = []
            BK.build(_book(base, data, kind), base / "book.xlsx", say=said.append)
            out[kind] = (base / "book.xlsx", said)
    finally:
        mp.undo()
    return out


def test_the_run_tab_and_the_titles_say_the_settings_are_the_consumer_books(built):
    def measure_line(wb):
        run = wb["Run"]
        return next(run.cell(r, 3).value for r in range(1, 20) if run.cell(r, 2).value == "Measure")
    wb = load_workbook(built["commercial"][0])
    assert PENDING in measure_line(wb)
    assert PENDING in wb["Summary"]["B1"].value
    assert PENDING not in measure_line(load_workbook(built["consumer"][0]))


def texts(wb):
    """Every piece of text a reader can see: cells (a formula's quoted text
    only), dropdown prompts and titles, by tab."""
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, str):
                    for t in (re.findall(r'"((?:[^"]|"")*)"', v) if v.startswith("=") else [v]):
                        yield ws.title, c.coordinate, t
        for dv in ws.data_validations.dataValidation:
            for t in (dv.prompt, dv.promptTitle, dv.error, dv.errorTitle):
                if isinstance(t, str):
                    yield ws.title, "validation %s" % dv.sqref, t


def test_a_commercial_book_says_portfolio_on_every_tab_and_never_product(built):
    path, said = built["commercial"]
    wb = load_workbook(path)
    hits = [(t, c, x[:80]) for t, c, x in texts(wb) if WORD.search(x)]
    assert hits == []
    # The part's own headings and the pickers.
    assert wb["Decide"]["B8"].value == "Portfolio"
    assert wb["Summary"]["B5"].value == "Portfolio"
    assert wb["Peers"]["B4"].value == "Portfolio"
    assert any(r[0].value == "Portfolio" for r in wb["Glossary"].iter_rows(min_col=2, max_col=2))
    assert any(s.startswith("commercial names: ") for s in said)


def test_a_consumer_book_keeps_product_exactly(built):
    path, _ = built["consumer"]
    wb = load_workbook(path)
    # The one "portfolio" is a source's own words, quoted on Reporting changes.
    hits = [x for t, c, x in texts(wb) if re.search(r"\bportfolios?\b", x, re.I)]
    assert len(hits) == 1 and hits[0].startswith(
        "FDIC Quarterly Banking Profile, First Quarter 2020: C&I loan portfolio increased by $339.4 billion")
    assert wb["Decide"]["B8"].value == "Product"
    assert wb["Summary"]["B5"].value == "Product"
    assert wb["Peers"]["B4"].value == "Product"
    gl = {r[1].value: r[2].value for r in wb["Glossary"].iter_rows()}
    assert gl["Product"] == "The first of the three parts that name a series, such as Credit card."
    assert "Internal" in wb.sheetnames and "Internal data" in wb.sheetnames
    # The Peers tab lists the peers build's own names, as before.
    wk = wb["Peers workings"]
    assert [wk.cell(r, 5).value for r in range(2, 8)] == list(books.COMMERCIAL)


def test_a_commercial_book_shows_the_commercial_names_and_the_call_reports_beside_them(built, data):
    path, _ = built["commercial"]
    wb = load_workbook(path)
    wk = wb["Peers workings"]
    assert [wk.cell(r, 5).value for r in range(2, 8)] == [KD.COMMERCIAL_NAMES[p] for p in books.COMMERCIAL]
    assert {wb["Peers data"].cell(r, 1).value for r in range(2, wb["Peers data"].max_row + 1)} == \
        set(KD.COMMERCIAL_NAMES.values())
    # NDFI is never bare.
    assert [(t, c) for t, c, x in texts(wb) if BARE_NDFI.search(x)] == []
    assert any(KD.NDFI in x for t, _, x in texts(wb) if t == "Reporting changes")
    # The Glossary's last section: each name as shown beside the Call Report's.
    gl = wb["Glossary"]
    rows = [tuple(c.value for c in r[1:4]) for r in gl.iter_rows()]
    at = rows.index(("Shown as", "The Call Report's name", "Where it is filed"))
    assert rows[at + 1:at + 1 + len(KD.CALL_REPORT)] == list(KD.CALL_REPORT)
    assert "Internal" not in wb.sheetnames and "Internal data" not in wb.sheetnames
    gterms = {r[0] for r in rows}
    assert not (gterms & {"Internal data", "Competitive check", "CRR grade"})
    assert gl.cell(5, 3).value == "The first of the three parts that name a series, such as C&I."


def test_peers_headings_show_the_name_as_built_never_lower_cased(built):
    for kind in ("commercial", "consumer"):
        pe = load_workbook(built[kind][0])["Peers"]
        fs = [c.value for r in pe.iter_rows() for c in r if isinstance(c.value, str) and c.value.startswith("=")]
        heads = [f for f in fs if re.match(r'="(Charge-offs|Delinquency|Book size|Lagged rate|Book index): ', f)
                 or f.startswith('="Against the industry')]
        assert len(heads) == 6
        assert not [f for f in heads if "LOWER('Peers'!$B$5)" in f or "LOWER(Peers!$B$5)" in f]


def test_the_share_panel_names_the_books_own_kind(built):
    for kind, want in (("commercial", "KeyBank's commercial book: share by portfolio"),
                       ("consumer", "KeyBank's consumer book: share by product")):
        pe = load_workbook(built[kind][0])["Peers"]
        assert any(isinstance(c.value, str) and want in c.value for r in pe.iter_rows() for c in r), kind
        assert not any(isinstance(c.value, str) and "consumer book" in c.value for r in pe.iter_rows()
                       for c in r) or kind == "consumer"


def test_the_glossary_names_the_share_panel_as_the_book_kind_says(built):
    """The panel says "KeyBank's commercial book: share by portfolio"; its
    Glossary term said "Consumer book by portfolio", "KeyBank's consumer book".
    A consumer book keeps its term exactly."""
    for kind, term, meaning in (
            ("commercial", "Commercial book by portfolio",
             "The share of KeyBank's commercial book in each portfolio built, the portfolio picked drawn first "
             "in red."),
            ("consumer", "Consumer book by product",
             "The share of KeyBank's consumer book in each product built, the product picked drawn first in red.")):
        gl = load_workbook(built[kind][0])["Glossary"]
        rows = {r[1].value: r[2].value for r in gl.iter_rows() if isinstance(r[1].value, str)}
        assert rows.get(term) == meaning, (kind, {t: m for t, m in rows.items() if "book by" in t})
        if kind == "commercial":
            assert not [t for t, m in rows.items() if t.startswith("Consumer book")
                        or "KeyBank's consumer book" in (m or "")]

def test_the_industry_caption_states_how_many_filers_it_holds(built, data):
    last = sorted(data)[-1]
    n = len(data[last])
    want = []
    for p in books.COMMERCIAL:
        k = books.industry_filers(data, [p], last)
        want.append("all %d filers" % n if k == n else "%d of %d filers" % (k, n))
    # The fixture's Bank of China files no charge-off field, so no commercial
    # industry series holds every filer.
    assert all(" of %d filers" % n in w for w in want)
    for kind in ("commercial", "consumer"):
        wb = load_workbook(built[kind][0])
        wk = wb["Peers workings"]
        assert wk.cell(1, 11).value == "Industry filers, last quarter"
        assert [wk.cell(2 + i, 11).value for i in range(len(want))] == want
        f = [c.value for r in wb["Peers"].iter_rows() for c in r
             if isinstance(c.value, str) and "Industry filers" not in c.value and "$K$2:$K$7" in c.value]
        assert len(f) == 1 and "every filer" not in f[0] and '"not supplied"' in f[0]


def test_summary_is_wide_enough_for_the_longest_portfolio_name(built):
    ws = load_workbook(built["commercial"][0])["Summary"]
    longest = max((n for n, *_ in SERIES), key=len)
    cols = [c.column_letter for c in ws[5] if c.value == "Portfolio"]
    assert len(cols) == 2                        # the two panels
    for col in cols:
        assert ws.column_dimensions[col].width >= len(longest)
    assert longest in [ws["%s%d" % (col, r)].value for col in cols for r in range(6, 20)]
    wb = load_workbook(built["commercial"][0])
    for tab in ("Thresholds", "Lines by source"):
        assert wb[tab].column_dimensions["B"].width >= len(longest), tab
    # A consumer book's names keep the widths they always had.
    from threshold_engine.summary_tab import W_PRODUCT, product_width
    consumer = ["Credit card", "Mortgage", "Home equity", "Other consumer", "Auto"]
    assert product_width(consumer) == W_PRODUCT and product_width(consumer, 16.43) == 16.43


# ---------------------------------------------------------------- the share panel stacks no loan twice

def test_stacking_takes_the_parts_or_the_whole_never_both():
    nnr, oo, other = "Nonfarm nonresidential", "Owner-occupied nonfarm nonresidential", "Other nonfarm nonresidential"
    c = list(books.COMMERCIAL)
    roles = dict(zip(c, books.stacking(c)))
    assert roles[nnr] == ("whole", (c.index(oo), c.index(other)))
    assert roles[oo] == roles[other] == ("part", (c.index(oo), c.index(other)))
    assert {roles[p] for p in ("C&I", "Construction", "Multifamily")} == {("own", ())}
    # The parent with one part: the parent holds it, so the part is not stacked.
    assert books.stacking([nnr, oo]) == [("own", ()), ("inside", ())]
    # The parts without the parent overlap nothing.
    assert books.stacking([oo, other, "C&I"]) == [("own", ())] * 3
    # Consumer products overlap nothing.
    assert books.stacking(list(books.CONSUMER)) == [("own", ())] * len(books.CONSUMER)


def test_the_share_panel_counts_no_loan_twice(built):
    """KeyBank's share panel stacks every portfolio built, so Nonfarm
    nonresidential and its two parts were counted twice. Each mix cell is
    evaluated (Excel's rules, by ``formulas``) on the Data tab's figures with
    the first portfolio picked, and checked against KeyBank's balances read
    from the Data tab directly: the parts in a quarter KeyBank files both, the
    whole in a quarter it does not, never both."""
    import formulas
    import schedula as sh
    wb = load_workbook(built["commercial"][0])
    wk, da = wb["Peers workings"], wb["Peers data"]
    head = [c.value for c in da[1]]
    col = {h: i for i, h in enumerate(head)}
    bal = {}
    for row in da.iter_rows(min_row=2, values_only=True):
        if row[col["Bank"]] == "KeyBank":
            bal[row[col["Portfolio"]], row[col["Quarter"]]] = row[col["Average balance ($000)"]]
    products = list(books.COMMERCIAL)
    shown = [KD.COMMERCIAL_NAMES[p] for p in products]
    mix = [c.column for c in wk[2] if isinstance(c.value, str) and c.value.startswith("=CHOOSE(")
           and "'Peers data'!$G$" in c.value]
    assert len(mix) == len(products)
    qcol = next(c.column for c in wk[1] if c.value == "Quarter")
    pick = re.match(r"=CHOOSE\(\$?([A-Z]+)\$?(\d+),", wk.cell(2, mix[0]).value)
    pick = pick.group(1) + pick.group(2)
    nnr, oo, other = (shown[products.index(p)] for p in ("Nonfarm nonresidential",
                                                          "Owner-occupied nonfarm nonresidential",
                                                          "Other nonfarm nonresidential"))
    regimes = set()
    for r in range(2, wk.max_row + 1):
        q = wk.cell(r, qcol).value
        if not q:
            break
        got = []
        for j, c_ in enumerate(mix):
            f = wk.cell(r, c_).value
            fn = formulas.Parser().ast(f)[1].compile()
            args = []
            for ref in fn.inputs:
                if "!" not in ref:                     # Workings' own cell: the portfolio picked
                    assert ref == pick, (ref, pick)
                    args.append(1)
                    continue
                sheet, cell = ref.rsplit("!", 1)
                assert sheet == "'PEERS DATA'", ref
                v = da[cell].value
                args.append(sh.EMPTY if v is None else v)
            got.append(float(fn(*args)))
        both = all(isinstance(bal.get((p, q)), (int, float)) for p in (oo, other))
        regimes.add(both)
        want = [float(bal.get((p, q)) or 0) for p in shown]
        if both:
            want[shown.index(nnr)] = 0.0
        else:
            want[shown.index(oo)] = want[shown.index(other)] = 0.0
        assert got == want, (q, got, want)
    # The fixture holds quarters of both kinds, so both branches were read.
    assert regimes == {True, False}


def test_the_share_panel_says_how_it_is_stacked(built):
    pe = load_workbook(built["commercial"][0])["Peers"]
    said = [c.value for r in pe.iter_rows() for c in r if isinstance(c.value, str) and "counted twice" in c.value]
    assert said == ["No loan counted twice: the two parts of Nonfarm nonresidential CRE where KeyBank files both, "
                    "the whole where it does not."]
    gl = load_workbook(built["commercial"][0])["Glossary"]
    calc = {r[1].value: r[3].value for r in gl.iter_rows() if isinstance(r[1].value, str)}
    assert calc["Commercial book by portfolio"].endswith(said[0])


# ---------------------------------------------------------------- terms only for tabs the book has

LOAN_TERMS = ("Peer loan classes", "Counted as", "For an unsecured comparison", "How the amount was read")


def test_a_book_without_the_loan_classes_tab_does_not_define_its_terms(built):
    """Neither fixture book has a loan_classes section, so neither workbook has
    the Peer loan classes tab, and neither Glossary defines its terms."""
    for kind in ("commercial", "consumer"):
        wb = load_workbook(built[kind][0])
        assert "Peer loan classes" not in wb.sheetnames
        terms = {r[1].value for r in wb["Glossary"].iter_rows() if isinstance(r[1].value, str)}
        assert "Rank tables" in terms and not terms & set(LOAN_TERMS), kind


def test_a_workbook_with_the_loan_classes_tab_defines_its_terms_where_they_were():
    """Written into a workbook that has the tab (a consumer book with a
    loan_classes section), the four terms follow Rank tables, as before; into
    one without it, of either kind, they are left out."""
    from openpyxl import Workbook
    from threshold_engine.peers import glossary as G
    from threshold_engine.peers import loan_classes_tab as LC
    from threshold_engine.peers import peers_workbook as PW
    assert G.LOAN_CLASS_TAB == LC.TITLE
    assert [t for t, _, _ in G.LOAN_CLASS_TERMS] == list(LOAN_TERMS)
    for kind, tab in (("consumer", True), ("consumer", False), ("commercial", False), (None, False)):
        wb = Workbook()
        gl = wb.active
        gl.title = "Glossary"
        if tab:
            wb.create_sheet(LC.TITLE)
        PW._write_glossary(gl, 1, 2, PW._Tabs({t: t for t in PW.TABS}), "Peers terms", kind)
        terms = [gl.cell(r, 2).value for r in range(1, gl.max_row + 1)]
        if tab:
            at = terms.index("Rank tables")
            assert terms[at + 1:at + 5] == list(LOAN_TERMS)
        else:
            assert not set(terms) & set(LOAN_TERMS), (kind, tab)
        # Every other term is there either way.
        assert {t for t, _, _ in G.PEER_TERMS} - {"Consumer book by product"} <= set(terms)


def test_decide_wraps_a_long_portfolio_name_and_keeps_its_column(built):
    """'Investor CRE (non-owner-occupied)' is wider than Decide's first column
    (16.43, the design's: widening it would move the slicers and the chart),
    so its cell wraps, onto rows tall enough for two lines."""
    ws = load_workbook(built["commercial"][0])["Decide"]
    assert ws.column_dimensions["B"].width == 16.43
    rows = [c for c in ws["B"] if c.value == "Investor CRE (non-owner-occupied)"]
    assert len(rows) == 1
    for c in ws["B"][8:]:
        if c.value in KD.COMMERCIAL_NAMES.values():
            assert c.alignment.wrap_text, c.coordinate
            assert ws.row_dimensions[c.row].height >= 2 * 15, c.coordinate
