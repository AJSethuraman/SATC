"""The peer workbook: Excel's live composite, band and best/worst must equal
peers.books (which is itself tied out to the earlier build_peers.py), as built
for the all-peers and the regionals pack, and after one Include is flipped.
Recalculated with the `formulas` engine, so no copy of Excel is needed; a skip
is reported, never counted as a pass. The roster pull is
tests/data/peers/roster_2006.json, with the earlier build's settings."""
import datetime as dt
import json
import os
import re
import zipfile

import pytest
from openpyxl import Workbook, load_workbook

from conftest import DATA, ROOT
from threshold_engine.peers import roster as R
from threshold_engine.peers.analyses import calendar_year, lagged_rate, mix_factor, normalisation, organic_index
from threshold_engine.peers.books import band, bank_book, best_worst, composite, industry
from threshold_engine.peers.glossary import PEER_TERMS
from threshold_engine.peers.peers_workbook import build_peers_workbook

formulas = pytest.importorskip("formulas", reason="the formulas engine recalculates the workbook")

PEERS = DATA / "peers"
FOUR = ("Credit card", "Mortgage", "Home equity", "Other consumer")
KEYBANK, JPMORGAN, FIFTH_THIRD = "17534", "628", "6672"
#: The earlier build's settings: 25% jump, $1bn ($000), KeyBank exempt, five banks.
JUMP, MIN_BOOK, MIN_BANKS = 0.25, 1_000_000, 5
RANK = dict(rank_by="net", last_n=20, min_obs=12)
EXTRAS = {FIFTH_THIRD: ["2022Q2"]}
FIRST_PEER = 15                       # Pack: the first peer's row (header on 14)


def recalc(path):
    """Every cell's value after a full recalculation, keyed 'SHEET!A1'."""
    model = formulas.ExcelModel().loads(str(path)).finish()
    sol = model.calculate()
    out = {}
    for key, val in sol.items():
        ref = key.split("]")[-1].upper()
        v = getattr(val, "value", val)
        try:
            v = v.item(0) if hasattr(v, "item") else v
        except Exception:                          # noqa: BLE001
            pass
        out[ref.replace("'", "")] = v
    return out


def num(v):
    """A recalculated number, or None for #N/A, blank or text."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


@pytest.fixture(scope="module")
def data():
    return json.loads((PEERS / "roster_2006.json").read_text())


@pytest.fixture(scope="module")
def roster():
    return R.load(ROOT / "config" / "peers.json")


@pytest.fixture(scope="module")
def books(data, roster):
    return {p: {b["cert"]: bank_book(data, b["cert"], p, JUMP, MIN_BOOK,
                                     exempt_min_book=b["cert"] == KEYBANK)
                for b in roster} for p in FOUR}


def make(path, data, roster, pack, products=FOUR, base="2019Q4", **over):
    kw = dict(exempt_self=True, min_banks=MIN_BANKS, index_min_book=500_000, lagged_years=(2019, 2025),
              lag_years=2, normalisation_years=(2019, 2025), mix_base_year=2019, industry=None,
              delinquency=None, **RANK)
    kw.update(over)
    return build_peers_workbook(path, data, roster, products, JUMP, MIN_BOOK, pack, MERGERS(), EXTRAS, base, **kw)


def MERGERS():
    return json.loads((PEERS / "mergers_roster.json").read_text())


@pytest.fixture(scope="module")
def recent(data):
    """2017 on: enough for the 2019 base and the 2019 to 2025 tabs, and quick to build."""
    return {q: rows for q, rows in data.items() if q >= "20170331"}


@pytest.fixture(scope="module")
def all_peers(tmp_path_factory, data, roster):
    p = tmp_path_factory.mktemp("peers") / "all.xlsx"
    info = make(p, data, roster, "all")
    return p, info, recalc(p)


@pytest.fixture(scope="module")
def regionals(tmp_path_factory, data, roster):
    # Built on other consumer, so the product picker's offset is exercised too.
    p = tmp_path_factory.mktemp("peers") / "regionals.xlsx"
    info = make(p, data, roster, "regionals", product="Other consumer")
    return p, info, recalc(p)


def column(vals, info, name, offset=0):
    """A live helper column on Peers, one value per TTM quarter."""
    from openpyxl.utils import column_index_from_string, get_column_letter
    c = get_column_letter(column_index_from_string(info["peers_helpers"][name]) + offset)
    first = info["peers_first_row"]
    return [vals.get("PEERS!%s%d" % (c, first + k)) for k in range(len(info["quarters"]))]


def same(got, want, places=9):
    """Equal within rounding, a missing value (#N/A) matching None."""
    if want is None:
        return num(got) is None
    return num(got) is not None and abs(num(got) - want) < 10 ** -places


def assert_series(got, want, what):
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if not same(g, w)]
    assert len(got) == len(want)
    assert not bad, (what, bad[:5])


def assert_composite(vals, info, books_p, certs):
    want = composite(books_p, certs, min_banks=MIN_BANKS)
    assert [r["quarter"] for r in want] == info["quarters"]
    assert [num(v) for v in column(vals, info, "banks")] == [r["banks"] for r in want]
    assert_series(column(vals, info, "cg"), [r["gross_rate"] for r in want], "composite gross")
    assert_series(column(vals, info, "cn"), [r["net_rate"] for r in want], "composite net")
    return want


def short_of(roster, cert):
    return next(b["short"] for b in roster if b["cert"] == cert)


# --- the live composite -------------------------------------------------------

def test_all_peers_composite_equals_books(all_peers, books, roster):
    _, info, vals = all_peers
    certs = [b["cert"] for b in R.peers(roster)]
    assert info["pack"] == certs and len(certs) == 15
    want = assert_composite(vals, info, books["Credit card"], certs)
    # 2007Q1 to 2010Q3 have fewer than five kept card books, so #N/A there
    # is checked as well as the 63 quarters with a composite.
    assert sum(r["net_rate"] is not None for r in want) == 63


def test_regionals_composite_equals_books(regionals, books, roster):
    _, info, vals = regionals
    certs = [b["cert"] for b in R.regionals(roster)]
    assert info["pack"] == certs and len(certs) == 10
    assert vals["PEERS!B4"] == "Other consumer"
    want = assert_composite(vals, info, books["Other consumer"], certs)
    assert any(r["net_rate"] is not None for r in want)


def test_flipping_one_include_drops_that_bank(all_peers, books, roster, tmp_path):
    p, info, before = all_peers
    peers = R.peers(roster)
    j = [b["cert"] for b in peers].index(JPMORGAN)
    wb = load_workbook(p)
    assert wb["Pack"].cell(FIRST_PEER + j, 1).value == "JPMorgan"
    wb["Pack"].cell(FIRST_PEER + j, 4).value = False
    q = tmp_path / "flip.xlsx"
    wb.save(q)
    after = recalc(q)
    without = [b["cert"] for b in peers if b["cert"] != JPMORGAN]
    assert_composite(after, info, books["Credit card"], without)
    moved = [i for i, (a, b) in enumerate(zip(column(before, info, "cn"), column(after, info, "cn")))
             if num(a) is not None and num(b) is not None and abs(num(a) - num(b)) > 1e-6]
    assert len(moved) > 40                       # JPMorgan's card book moves the composite
    # and the band follows the pack too
    want = band(books["Credit card"], without, "net", min_banks=MIN_BANKS)
    assert_series(column(after, info, "n10"), [r["p10"] for r in want], "band after flip")


# --- the band -----------------------------------------------------------------

@pytest.mark.parametrize("kind", ["gross", "net"])
def test_band_equals_books(all_peers, regionals, books, roster, kind):
    k = kind[0]
    for (_, info, vals), product, certs in (
            (all_peers, "Credit card", [b["cert"] for b in R.peers(roster)]),
            (regionals, "Other consumer", [b["cert"] for b in R.regionals(roster)])):
        want = band(books[product], certs, kind, min_banks=MIN_BANKS)
        for pct in (10, 25, 75, 90):
            assert_series(column(vals, info, "%s%d" % (k, pct)), [r["p%d" % pct] for r in want],
                          "%s %s p%d" % (product, kind, pct))

def test_band_is_drawn_as_up_down_bars_under_the_lines(all_peers):
    """A stacked area cannot leave a gap: Excel drew the band falling to 0 at
    every quarter without one (a wedge from 0% at 2010Q3, seen in Excel on 12
    Oct 2026). Up-down bars between the 10th and 90th, and the 25th and 75th,
    are drawn only where both ends have a value. They come first in the plot,
    so the lines are drawn over them."""
    p, info, _ = all_peers
    with zipfile.ZipFile(p) as z:
        peers_charts = [n for n in sorted(z.namelist()) if re.match(r"xl/charts/chart\d+\.xml$", n)
                        and "'Peers'!" in z.read(n).decode("utf-8")]
        assert len(peers_charts) == 2
        for n, k in zip(peers_charts, "gn"):
            xml = z.read(n).decode("utf-8")
            assert "<areaChart>" not in xml and "<barChart>" not in xml
            groups = re.findall(r"<lineChart>.*?</lineChart>", xml)
            assert len(groups) == 3
            for g, (lo, hi) in zip(groups[:2], ((10, 90), (25, 75))):
                assert "<upDownBars>" in g
                refs = re.findall(r"<val><numRef><f>'Peers'!\$([A-Z]+)\$", g)
                assert refs == [info["peers_helpers"]["%s%d" % (k, lo)], info["peers_helpers"]["%s%d" % (k, hi)]]
                sers = re.findall(r"<ser>.*?</ser>", g)
                assert len(sers) == 2 and all("<a:ln><a:noFill />" in x for x in sers)   # invisible ends
            assert "<upDownBars>" not in groups[2]
            refs = re.findall(r"<val><numRef><f>'Peers'!\$([A-Z]+)\$", groups[2])
            assert refs == [info["peers_helpers"][name + k] for name in ("c", "k", "a", "b")]


# --- best and worst, KeyBank, Peer A and B ------------------------------------

def test_best_and_worst_resolve_to_books(all_peers, regionals, books, roster):
    for (_, info, vals), product, certs in (
            (all_peers, "Credit card", [b["cert"] for b in R.peers(roster)]),
            (regionals, "Other consumer", [b["cert"] for b in R.regionals(roster)])):
        best, worst = best_worst(books[product], certs, RANK["rank_by"], RANK["last_n"], RANK["min_obs"])
        assert best and worst and best != worst
        assert vals["PACK!B11"] == short_of(roster, best)
        assert vals["PACK!B12"] == short_of(roster, worst)
        assert vals["PACK!C5"] == short_of(roster, worst)          # Peer A starts as Worst in pack
        assert vals["PACK!C6"] == short_of(roster, best)           # Peer B as Best in pack
        assert short_of(roster, best) in vals["PEERS!A7"] and short_of(roster, worst) in vals["PEERS!A7"]
        for name, cert in (("an", worst), ("bn", best), ("kn", KEYBANK)):
            assert_series(column(vals, info, name), [r["net_rate"] for r in books[product][cert]], name)
        for name, cert in (("ag", worst), ("bg", best), ("kg", KEYBANK)):
            assert_series(column(vals, info, name), [r["gross_rate"] for r in books[product][cert]], name)


def window_counts(books_p, certs, kind, last_n):
    """Per peer: (kept quarters in the last ``last_n``, their mean), as books.best_worst counts them."""
    out = {}
    for c in certs:
        rates = [r["%s_rate" % kind] for r in books_p[c][-last_n:] if r["%s_rate" % kind] is not None]
        out[c] = (len(rates), sum(rates) / len(rates) if rates else None)
    return out


def test_pack_window_counts_and_means_equal_books(all_peers, books, roster):
    """Pack column F counts each included peer's kept quarters in exactly the
    last ``last_n``, and column E is their mean once there are ``min_obs``."""
    _, _, vals = all_peers
    peers = R.peers(roster)
    want = window_counts(books["Credit card"], [b["cert"] for b in peers], "net", RANK["last_n"])
    for j, b in enumerate(peers):
        n, mean = want[b["cert"]]
        assert num(vals["PACK!F%d" % (FIRST_PEER + j)]) == n, b["short"]
        e = vals["PACK!E%d" % (FIRST_PEER + j)]
        if n >= RANK["min_obs"]:
            assert num(e) == pytest.approx(mean, abs=1e-9), b["short"]
        else:
            assert num(e) is None, b["short"]


def test_a_peer_with_exactly_min_obs_kept_quarters_qualifies(all_peers, books, roster, tmp_path):
    """The boundary: Capital One has exactly 10 kept card quarters in the last
    20, so with 10 needed it is ranked, and best and worst follow books."""
    p, _, _ = all_peers
    peers = R.peers(roster)
    certs = [b["cert"] for b in peers]
    counts = window_counts(books["Credit card"], certs, "net", 20)
    edge = [c for c in certs if 0 < counts[c][0] < 20]
    assert edge, "no peer sits between 0 and 20 kept quarters, so the boundary is not tested"
    need = counts[edge[0]][0]
    wb = load_workbook(p)
    wb["Pack"]["B9"] = need
    q = tmp_path / "minobs.xlsx"
    wb.save(q)
    vals = recalc(q)
    j = certs.index(edge[0])
    assert num(vals["PACK!E%d" % (FIRST_PEER + j)]) == pytest.approx(counts[edge[0]][1], abs=1e-9)
    best, worst = best_worst(books["Credit card"], certs, "net", 20, need)
    assert (vals["PACK!B11"], vals["PACK!B12"]) == (short_of(roster, best), short_of(roster, worst))


def test_a_named_peer_pick_draws_that_peer_whether_or_not_included(all_peers, books, roster, tmp_path):
    p, info, _ = all_peers
    peers = R.peers(roster)
    j = [b["cert"] for b in peers].index(FIFTH_THIRD)
    wb = load_workbook(p)
    wb["Pack"]["B5"] = "Fifth Third"
    wb["Pack"].cell(FIRST_PEER + j, 4).value = False
    q = tmp_path / "pick.xlsx"
    wb.save(q)
    vals = recalc(q)
    assert vals["PACK!C5"] == "Fifth Third"
    assert_series(column(vals, info, "an"), [r["net_rate"] for r in books["Credit card"][FIFTH_THIRD]], "A")
    certs = [b["cert"] for b in peers if b["cert"] != FIFTH_THIRD]
    best, worst = best_worst(books["Credit card"], certs, "net", 20, 12)
    assert (vals["PACK!B11"], vals["PACK!B12"]) == (short_of(roster, best), short_of(roster, worst))


# --- the tabs of values -------------------------------------------------------

def rows_of(ws):
    return [[c.value for c in r] for r in ws.iter_rows()]


def section(ws, title):
    """The rows under a section band, up to the next band or a blank row."""
    rows = rows_of(ws)
    i = next(k for k, r in enumerate(rows) if r[0] == title)
    out = []
    for r in rows[i + 2:]:
        if r[0] is None or r[0] in FOUR:
            break
        out.append(r)
    return out


def test_lagged_tab_carries_the_acceptance_numbers(all_peers):
    p, _, _ = all_peers
    rows = {r[0]: r for r in section(load_workbook(p)["Lagged"], "Credit card")}
    # docs/PEERS-SPEC.md: card, 2025 net over the 2023 book; 2019 over 2017.
    for name, y2019, y2025 in (("Fifth Third", 6.18, 3.47), ("KeyBank", 3.52, 3.82), ("Huntington", 7.89, 4.92)):
        assert (round(rows[name][1], 2), round(rows[name][2], 2)) == (y2019, y2025)


def test_every_lagged_row_and_total_equals_analyses(all_peers, data, roster):
    """Each bank's row and both totals equal analyses.lagged_rate over the
    banks the label names. The regionals total is every peer the roster marks
    regional (ten), not the spec's six, so its label carries the count and the
    note names them; the six-regional 4.35 / 4.53 is analyses' acceptance."""
    p, _, _ = all_peers
    ws = load_workbook(p)["Lagged"]
    peers, regs = R.peers(roster), R.regionals(roster)
    sets = {b["short"]: b["cert"] for b in roster}
    sets["All peers, total (%d banks)" % len(peers)] = [b["cert"] for b in peers]
    sets["Regionals, total (%d banks)" % len(regs)] = [b["cert"] for b in regs]
    for product in FOUR:
        rows = {r[0]: r for r in section(ws, product)}
        assert set(rows) == set(sets), product
        for name, certs in sets.items():
            for c_, year in ((1, 2019), (2, 2025)):
                want = lagged_rate(data, certs, product, year, 2)["rate"]
                got = rows[name][c_]
                assert (got is None) if want is None else got == pytest.approx(want), (product, name, year)
    text = " ".join(str(r[0]) for r in rows_of(ws) if r[0])
    assert "marks regional: " + ", ".join(b["short"] for b in regs) in text


def test_balances_tab_carries_the_acceptance_numbers(all_peers):
    p, _, _ = all_peers
    rows = {r[0]: r for r in section(load_workbook(p)["Balances"], "Credit card: book index, 2019Q4 = 100")}
    # As reported / without acquisitions at 2026Q2 (docs/PEERS-SPEC.md).
    for name, rep, org in (("M&T", 156, 145), ("PNC", 100, 80), ("KeyBank", 82, 82), ("Fifth Third", 66, 67)):
        assert (round(rows[name][2]), round(rows[name][3])) == (rep, org)
    assert "2022Q2 (declared)" in rows["Fifth Third"][4]


def test_balances_index_table_and_the_minimum_book(all_peers, data, roster):
    """Each bank's note and figures follow organic_index and index_min_book,
    and the table under each chart holds, without acquisitions first, then as
    reported, every indexed bank's quarters from the base."""
    p, info, _ = all_peers
    ws = load_workbook(p)["Balances"]
    mergers = MERGERS()
    title = "Credit card: book index, 2019Q4 = 100"
    rows = {r[0]: r for r in section(ws, title)}
    indexed = []
    for b in roster:
        acq = list(mergers.get(b["cert"], [])) + EXTRAS.get(b["cert"], [])
        try:
            idx = organic_index(data, b["cert"], "Credit card", "2019Q4", acq)
        except ValueError:
            idx = None
        row = rows[b["short"]]
        if idx is None:
            assert row[5] == "no book at the base", b["short"]
            continue
        at_base = next(x["balance"] for x in idx if x["date"] == "2019-12-31")
        assert row[1] == pytest.approx(at_base / 1000)
        if at_base < 500_000:
            assert row[5] == "under the minimum at the base: not indexed" and row[2] is None, b["short"]
        else:
            assert row[5] is None and row[2] == pytest.approx(idx[-1]["reported"]), b["short"]
            assert row[3] == pytest.approx(idx[-1]["organic"]), b["short"]
            indexed.append((b, [x for x in idx if x["date"] >= "2019-12-31"]))
    assert any(r[5] == "under the minimum at the base: not indexed" for r in rows.values())
    assert len(indexed) >= 5
    # The chart's table: the first header row after this section's band.
    all_rows = rows_of(ws)
    start = next(i for i, r in enumerate(all_rows) if r[0] == title)
    head = next(i for i in range(start, len(all_rows)) if all_rows[i][0] == "Quarter")
    n = len(indexed)
    assert all_rows[head - 1][1] == "Without acquisitions" and all_rows[head - 1][2 + n] == "As reported"
    assert all_rows[head][1:1 + n] == [b["short"] for b, _ in indexed]
    assert all_rows[head][2 + n:2 + 2 * n] == [b["short"] for b, _ in indexed]
    for j, (b, idx) in enumerate(indexed):
        for k, x in enumerate(idx):
            got = all_rows[head + 1 + k]
            assert got[0] == x["quarter"]
            for c_, v in ((1 + j, x["organic"]), (2 + n + j, x["reported"])):
                assert (got[c_] is None) if v is None else got[c_] == pytest.approx(v), (b["short"], x["quarter"])


def test_the_visible_peers_table_reads_the_live_lines(all_peers):
    """The table under the charts (header on row 64) is the live helpers, column by column."""
    _, info, vals = all_peers
    for k, q in enumerate(info["quarters"]):
        r = 65 + k
        assert vals["PEERS!A%d" % r] == q
        assert num(vals["PEERS!B%d" % r]) == num(column(vals, info, "banks")[k])
        for c_, name in zip("CDEFGH", ("cg", "cn", "kg", "kn", "an", "bn")):
            want = num(column(vals, info, name)[k])
            got = vals["PEERS!%s%d" % (c_, r)]
            assert (num(got) is None) if want is None else num(got) == pytest.approx(want), (q, name)


def test_normalisation_tab_carries_the_acceptance_numbers(all_peers):
    p, _, _ = all_peers
    rows = {r[0]: r for r in section(load_workbook(p)["Normalisation"], "Credit card")}
    for name, a, b in (("KeyBank", 3.29, 4.30), ("Citizens", 3.82, 5.51), ("Fifth Third", 5.07, 3.79)):
        assert (round(rows[name][1], 2), round(rows[name][2], 2)) == (a, b)


def test_every_normalisation_row_equals_analyses(all_peers, books, roster):
    """Each bank and both composites equal analyses.normalisation over the
    series the label names, and the spec's regional composite reads 3.82 to
    4.25. A ratio is blank where the base is net recoveries, and the note and
    the glossary say so."""
    p, _, _ = all_peers
    ws = load_workbook(p)["Normalisation"]
    peers, regs = R.peers(roster), R.regionals(roster)
    for product in FOUR:
        rows = {r[0]: r for r in section(ws, product)}
        series = {b["short"]: [(x["quarter"], x["net_rate"]) for x in books[product][b["cert"]]] for b in roster}
        for name, certs in (("All-peer composite (%d banks)" % len(peers), peers),
                            ("Regional composite (%d banks)" % len(regs), regs)):
            comp = composite(books[product], [b["cert"] for b in certs], min_banks=MIN_BANKS)
            series[name] = [(x["quarter"], x["net_rate"]) for x in comp]
        assert set(rows) == set(series), product
        for name, ser in series.items():
            want = normalisation(ser, 2019, 2025)
            for c_, key in ((1, "base"), (2, "end"), (3, "ratio")):
                got = rows[name][c_]
                assert (got is None) if want[key] is None else got == pytest.approx(want[key]), (product, name, key)
    card = {r[0]: r for r in section(ws, "Credit card")}["Regional composite (10 banks)"]
    assert (round(card[1], 2), round(card[2], 2)) == (3.82, 4.25)
    mortgage = {r[0]: r for r in section(ws, "Mortgage")}["JPMorgan"]
    assert mortgage[1] < 0 and mortgage[3] is None
    text = " ".join(str(r[0]) for r in rows_of(ws) if r[0])
    assert "0 or below" in text
    assert "0 or below" in {t: c for t, _, c in PEER_TERMS}["Normalisation"]


def test_mix_tab_says_when_no_industry_was_supplied(all_peers):
    p, _, _ = all_peers
    text = " ".join(str(v) for r in rows_of(load_workbook(p)["Mix"]) for v in r if v)
    assert "No industry series was supplied for Credit card" in text


def test_mix_tab_with_an_industry(tmp_path, data, roster):
    from threshold_engine.peers.books import industry
    ind = {p: industry(data, p) for p in FOUR}      # the roster's aggregate, standing in for a test
    p = tmp_path / "mix.xlsx"
    make(p, data, roster, "all", industry=ind)
    rows = section(load_workbook(p)["Mix"], "Credit card")
    first = rows[0]                                 # the base year, under the header
    assert first[0] == 2019 and first[3] == pytest.approx(1) and first[5] == pytest.approx(1)
    # Every year, every column, as analyses works it for KeyBank.
    years = list(range(2019, 2026))
    ind_rate = {int(x["quarter"][:4]): x["net_rate"] for x in ind["Credit card"] if x["quarter"].endswith("Q4")}

    def mix(cert):
        rate = {y: lagged_rate(data, cert, "Credit card", y, 0)["rate"] for y in years}
        bal = {y: calendar_year(data, cert, "Credit card", y)["balance"] for y in years}
        return rate, mix_factor(rate, {y: ind_rate.get(y) for y in years}, bal, 2019)

    rate, want = mix(KEYBANK)
    assert [r[0] for r in rows] == years
    for got, x in zip(rows, want):
        for c_, v in ((1, rate[x["year"]]), (2, ind_rate[x["year"]]), (3, x["bank_ratio"]),
                      (4, x["industry_ratio"]), (5, x["own_factor"]), (6, x["balance_factor"])):
            assert (got[c_] is None) if v is None else got[c_] == pytest.approx(v), (x["year"], c_)
    # The own factor of every bank, by year.
    all_rows = rows_of(load_workbook(p)["Mix"])
    at = next(i for i, r in enumerate(all_rows) if r[0] == "Own factor, every bank")
    assert all_rows[at + 1][1:1 + len(years)] == [str(y) for y in years]
    table = {r[0]: r for r in all_rows[at + 2:at + 2 + len(roster)]}
    for b in roster:
        own = {x["year"]: x["own_factor"] for x in mix(b["cert"])[1]}
        for j, y in enumerate(years):
            got = table[b["short"]][1 + j]
            assert (got is None) if own[y] is None else got == pytest.approx(own[y]), (b["short"], y)


# --- the glossary, the data, the structure ------------------------------------

def test_every_glossary_term_is_on_the_glossary_tab(all_peers):
    p, _, _ = all_peers
    on_tab = {r[0] for r in rows_of(load_workbook(p)["Glossary"])}
    terms = [t for t, _, _ in PEER_TERMS]
    assert set(terms) <= on_tab
    for must in ("Structural move", "Pack", "Composite", "Band", "Lagged rate", "Organic index", "Own factor"):
        assert must in terms
    assert all(m and c for _, m, c in PEER_TERMS)


def test_data_tab_holds_every_bank_product_and_quarter(all_peers, books, roster):
    p, info, _ = all_peers
    ws = load_workbook(p)["Data"]
    assert info["data_rows"] == 4 * 16 * len(info["quarters"]) == ws.max_row - 1
    want = books["Credit card"][KEYBANK][0]
    first = [c.value for c in ws[2 + 8 * len(info["quarters"])]]        # KeyBank is ninth on the roster
    assert first[:4] == ["Credit card", "KeyBank", KEYBANK, want["quarter"]]
    assert first[9] is want["kept"] and first[10] == want["why"]


def test_charts_are_line_based_with_gaps_and_hidden_helpers(all_peers):
    p, info, _ = all_peers
    wb = load_workbook(p)
    pe = wb["Peers"]
    with zipfile.ZipFile(p) as z:
        charts = [n for n in z.namelist() if re.match(r"xl/charts/chart\d+\.xml$", n)]
        assert charts
        for n in charts:
            xml = z.read(n).decode("utf-8")
            assert 'dispNaAsBlank val="1"' in xml and '<dispBlanksAs val="gap"' in xml
            assert '<plotVisOnly val="0"' in xml
            # The line chart is the base: it comes before any area in the plot.
            if "<areaChart>" in xml:
                assert xml.index("<lineChart>") < xml.index("<areaChart>")
    from openpyxl.utils import column_index_from_string
    first_helper = column_index_from_string(info["peers_helpers"]["uk"]) - 2
    for c in range(first_helper, column_index_from_string(info["peers_helpers"]["bn"]) + 1):
        from openpyxl.utils import get_column_letter
        assert pe.column_dimensions[get_column_letter(c)].hidden
    visible = [c.column for row in pe.iter_rows(max_col=first_helper - 1) for c in row if c.value is not None]
    assert max(visible) < first_helper


def formulas_reaching_above_row_1(wb):
    """Formulas that do, or could at recalculation, refer above row 1: a
    literal row below 1 (what ``"A%d" % (r - 1)`` writes when r is 1), or an
    OFFSET or INDIRECT, whose reach a reading of the formula cannot see. The
    workbook uses neither, so any one of them is reported."""
    bad = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    text = re.sub(r'"[^"]*"', "", c.value)            # not inside text
                    if re.search(r"\b(OFFSET|INDIRECT)\(", text, re.I) or any(
                            int(m.group(1)) < 1
                            for m in re.finditer(r"(?<![A-Z0-9_.])\$?[A-Z]{1,3}\$?(\d+)\b", text)):
                        bad.append((ws.title, c.coordinate, c.value))
    return bad


def test_no_formula_refers_to_a_row_above_row_1(all_peers):
    p, _, _ = all_peers
    bad = formulas_reaching_above_row_1(load_workbook(p))
    assert not bad, bad[:3]


def test_the_row_check_can_fail():
    """The control: the check above reports each kind of reach it looks for,
    and leaves an ordinary formula alone."""
    wb = Workbook()
    ws = wb.active
    ws["A1"] = "=SUM(B1:B3)"
    ws["A2"] = '="A0 in text"&B2'
    assert formulas_reaching_above_row_1(wb) == []
    for f in ("=B0+1", "=SUM($C$0:C4)", "=OFFSET(A1,-1,0)", '=INDIRECT("A"&ROW()-1)'):
        ws["A3"] = f
        assert formulas_reaching_above_row_1(wb), f


def test_the_pack_counts_refuse_anything_but_a_whole_number_of_at_least_1(all_peers):
    """Excel refuses a 0 typed into the window, the kept quarters needed or the
    banks needed, as the build does: a 0 there turned best, worst, Peer A and
    B and the caption into #DIV/0! (seen in Excel, 12 Oct 2026)."""
    p, _, _ = all_peers
    dvs = load_workbook(p)["Pack"].data_validations.dataValidation
    whole = [d for d in dvs if d.type == "whole"]
    assert len(whole) == 1
    d = whole[0]
    assert d.operator == "greaterThanOrEqual" and d.formula1 == "1" and not d.allow_blank and d.showErrorMessage
    assert {str(c) for c in d.sqref.ranges} == {"B8", "B9", "B10"}


def test_run_tab_states_the_rules_as_built(all_peers):
    p, _, _ = all_peers
    rows = {r[0]: r for r in rows_of(load_workbook(p)["Run"]) if r and r[0]}
    assert rows["Jump"][1] == JUMP
    assert rows["Minimum book ($000)"][1] == MIN_BOOK and rows["Minimum book ($000)"][2] == "KeyBank exempt"
    assert rows["Banks needed for a composite or band (starting)"][1] == MIN_BANKS
    assert rows["Pack (starting)"][1] == "all"
    assert rows["Pulled"][1].startswith("not recorded")          # no cache folder was given
    mergers = MERGERS()
    fp = rows["Acquisitions record (SHA-256 of it as canonical JSON)"]
    assert fp[2] == "%d banks, %d acquisition quarters" % (len(mergers), sum(len(v) for v in mergers.values()))
    assert re.fullmatch(r"[0-9a-f]{64}", fp[1])


def test_run_tab_records_when_each_quarter_and_the_mergers_were_pulled(tmp_path, recent, roster):
    """The spec's Run tab: sources, pull dates, the cache fingerprints. A
    cache file is written when its quarter is fetched, so its time is the
    pull date; the acquisitions file is named with its own."""
    cache = tmp_path / "cache"
    cache.mkdir()
    pulled = dt.datetime(2026, 10, 1, 9, 30, 0)
    stamp = pulled.timestamp()
    for q, rows in recent.items():
        f = cache / ("q%s.json" % q)
        f.write_text(json.dumps(rows), encoding="utf-8")
        os.utime(f, (stamp, stamp))
    late = cache / ("q%s.json" % max(recent))
    later = dt.datetime(2026, 10, 2, 8, 0, 0)
    os.utime(late, (later.timestamp(), later.timestamp()))
    mfile = tmp_path / "mergers.json"
    mfile.write_text(json.dumps(MERGERS()), encoding="utf-8")
    os.utime(mfile, (stamp, stamp))
    p = tmp_path / "run.xlsx"
    make(p, recent, roster, "all", products=("Credit card",), cache_dir=cache, mergers_file=mfile)
    rows = [r for r in rows_of(load_workbook(p)["Run"])]
    by = {r[0]: r for r in rows if r and r[0]}
    assert by["Pulled (cache files written)"][1] == "2026-10-01T09:30:00 to 2026-10-02T08:00:00"
    files = {r[0]: r for r in rows if r and isinstance(r[0], str) and r[0].startswith("q")}
    assert len(files) == len(recent)
    assert files[late.name][1] == "2026-10-02T08:00:00"
    first = cache / ("q%s.json" % min(recent))
    assert files[first.name][1] == "2026-10-01T09:30:00"
    import hashlib
    assert files[first.name][2] == hashlib.sha256(first.read_bytes()).hexdigest()
    m = by["Acquisitions file"]
    assert m[1] == str(mfile) and "2026-10-01T09:30:00" in m[2]
    assert hashlib.sha256(mfile.read_bytes()).hexdigest() in m[2]


@pytest.mark.parametrize("over, why", [
    (dict(products=("Credit card", "Credit card")), "distinct"),
    (dict(products=("Credit card", "Cars")), "distinct"),
    (dict(normalisation_years=(2019,)), "normalisation_years"),
    (dict(min_banks=0), "min_banks"),
    (dict(min_banks=2.5), "min_banks"),
    (dict(min_banks=True), "min_banks"),
    (dict(last_n=0), "last_n"),
    (dict(min_obs=0), "min_obs"),
    (dict(product="Mortgage", products=("Credit card",)), "starting product"),
    (dict(base="2031Q4"), "base quarter 2031Q4 is not in the data"),
    (dict(base="2019Q5"), "not a quarter"),
    (dict(products=("Credit card", "Auto")), "LNAUTO"),
])
def test_a_bad_setting_is_refused_with_its_reason(tmp_path, recent, roster, over, why):
    over = dict(over)
    kw = {k: over.pop(k) for k in ("products", "base") if k in over}
    with pytest.raises(ValueError, match=why):
        make(tmp_path / "x.xlsx", recent, roster, "all", **kw, **over)
    assert not (tmp_path / "x.xlsx").exists()


def test_data_too_short_for_a_ttm_quarter_is_refused(tmp_path, data, roster):
    four = {q: data[q] for q in ("20190331", "20190630", "20190930", "20191231")}
    with pytest.raises(ValueError, match="no TTM quarter"):
        make(tmp_path / "x.xlsx", four, roster, "all", products=("Credit card",))


def test_a_roster_without_peers_or_without_regionals(tmp_path, recent, roster):
    """No peers: refused by name. No regionals: a regionals pack is refused
    by name; an all-peers pack builds, with no regionals total or composite
    rather than a crash inside lagged_rate."""
    me = [b for b in roster if b["group"] == "self"]
    with pytest.raises(ValueError, match="no peers"):
        make(tmp_path / "x.xlsx", recent, me, "all", products=("Credit card",))
    flat = [dict(b, regional=False) for b in roster]
    with pytest.raises(ValueError, match="regional"):
        make(tmp_path / "x.xlsx", recent, flat, "regionals", products=("Credit card",))
    p = tmp_path / "flat.xlsx"
    make(p, recent, flat, "all", products=("Credit card",))
    wb = load_workbook(p)
    lagged = [r[0] for r in section(wb["Lagged"], "Credit card")]
    assert "All peers, total (15 banks)" in lagged and not any(str(n).startswith("Regionals") for n in lagged)
    norm = [r[0] for r in section(wb["Normalisation"], "Credit card")]
    assert "All-peer composite (15 banks)" in norm and not any(str(n).startswith("Regional ") for n in norm)


def test_mix_says_so_when_the_data_lacks_a_quarter_of_the_base_year(tmp_path, recent, roster):
    """An industry with the base year, over roster data without 2019Q2, is
    said in words rather than raised from inside mix_factor."""
    ind = {"Credit card": industry(recent, "Credit card")}
    gap = {q: rows for q, rows in recent.items() if q != "20190630"}
    p = tmp_path / "gap.xlsx"
    make(p, gap, roster, "all", products=("Credit card",), industry=ind)
    text = " ".join(str(v) for r in rows_of(load_workbook(p)["Mix"]) for v in r if v)
    assert "does not hold all four quarters of 2019" in text


def test_judgements_are_required_and_bad_ones_refused(tmp_path, data, roster):
    with pytest.raises(TypeError):
        build_peers_workbook(tmp_path / "x.xlsx", data, roster, FOUR, JUMP, MIN_BOOK, "all", {}, {}, "2019Q4")
    with pytest.raises(ValueError, match="pack"):
        make(tmp_path / "x.xlsx", data, roster, "everyone")
    with pytest.raises(ValueError, match="rank_by"):
        make(tmp_path / "x.xlsx", data, roster, "all", rank_by="mean")
    with pytest.raises(ValueError, match="peer pick"):
        make(tmp_path / "x.xlsx", data, roster, "all", peer_a="KeyBank")


# --- delinquency and nonaccrual (docs/V1-ROUND2-SPEC.md, section A) ------------
#
# Built over tests/data/peers/delinquency_roster.json (the 16 roster banks,
# 2017Q1 to 2026Q2, pulled once from the public FDIC API on 12 Oct 2026) with
# two products, so the product-and-measure picker's offset is exercised while
# each recalculation stays near a minute. The live lines must equal
# peers.delinquency, which is itself checked against arithmetic on the filing.

from openpyxl.utils import column_index_from_string, get_column_letter  # noqa: E402

from threshold_engine.peers import delinquency as D                     # noqa: E402

TWO = ("Credit card", "Mortgage")
DQ_RULES = dict(jump=0.25, min_book=1_000_000, exempt_self=True)


@pytest.fixture(scope="module")
def dl_data():
    return json.loads((PEERS / "delinquency_roster.json").read_text())


def dq_spec(dl_data, **over):
    spec = dict(data=dl_data, products=TWO, measure="90+ accruing", basis="quarter-end", **DQ_RULES)
    spec.update(over)
    return spec


def dl_books(dl_data, roster, product, measure):
    return {b["cert"]: D.bank_delinquency(dl_data, b["cert"], product, measure, DQ_RULES["jump"],
                                          DQ_RULES["min_book"], DQ_RULES["exempt_self"] and b["cert"] == KEYBANK)
            for b in roster}


@pytest.fixture(scope="module")
def dlq(tmp_path_factory, recent, dl_data, roster):
    """The all-peers pack with delinquency, as built: card, 90+ accruing, quarter-end."""
    p = tmp_path_factory.mktemp("delinquency") / "dlq.xlsx"
    info = make(p, recent, roster, "all", products=("Credit card",), delinquency=dq_spec(dl_data))
    return p, info, recalc(p)


def dcol(vals, info, name, offset=0):
    """A live helper column on Delinquency, one value per quarter-end."""
    d = info["delinquency"]
    c = get_column_letter(column_index_from_string(d["helpers"][name]) + offset)
    return [vals.get("DELINQUENCY!%s%d" % (c, d["first_row"] + k)) for k in range(len(d["quarters"]))]


def assert_delinquency(vals, info, books, certs, basis, what, min_banks=MIN_BANKS):
    """Composite, both bank counts and the band on ``basis`` equal peers.delinquency."""
    comp = D.composite_delinquency(books, certs, min_banks)
    assert [r["q"] for r in comp] == info["delinquency"]["quarters"]
    assert [num(v) for v in dcol(vals, info, "banks")] == [r["banks"] for r in comp], what
    key = D.basis_key(basis)
    assert_series(dcol(vals, info, "c"), [r[key] for r in comp], what + " composite")
    want = D.band_delinquency(books, certs, basis, min_banks=min_banks)
    assert [num(v) for v in dcol(vals, info, "bandn")] == [r["banks"] for r in want], what + " band count"
    for pct in (10, 25, 75, 90):
        assert_series(dcol(vals, info, "p%d" % pct), [r["p%d" % pct] for r in want], "%s p%d" % (what, pct))
    return comp, want


def assert_lines(vals, info, books, roster, basis):
    """KeyBank, Peer A and Peer B are their own rows on ``basis``, whoever A and B resolve to."""
    key = D.basis_key(basis)
    cert = {b["short"]: b["cert"] for b in roster}
    for name, who in (("k", KEYBANK), ("a", cert[vals["PACK!C5"]]), ("bb", cert[vals["PACK!C6"]])):
        assert_series(dcol(vals, info, name), [r[key] for r in books[who]], name)


def test_delinquency_composite_and_band_equal_the_module(dlq, dl_data, roster):
    _, info, vals = dlq
    books = dl_books(dl_data, roster, "Credit card", "90+ accruing")
    certs = [b["cert"] for b in R.peers(roster)]
    comp, band_ = assert_delinquency(vals, info, books, certs, "quarter-end", "card 90+")
    assert len(info["delinquency"]["quarters"]) == 38
    assert sum(r["rate"] is not None for r in comp) == 38 and all(r["p10"] is not None for r in band_)
    assert_lines(vals, info, books, roster, "quarter-end")
    assert vals["DELINQUENCY!B4"] == "Credit card" and vals["DELINQUENCY!B5"] == "90+ accruing"


def test_delinquency_follows_one_include_flipped(dlq, dl_data, roster, tmp_path):
    p, info, before = dlq
    peers = R.peers(roster)
    j = [b["cert"] for b in peers].index(JPMORGAN)
    wb = load_workbook(p)
    assert wb["Pack"].cell(FIRST_PEER + j, 1).value == "JPMorgan"
    wb["Pack"].cell(FIRST_PEER + j, 4).value = False
    q = tmp_path / "flip.xlsx"
    wb.save(q)
    after = recalc(q)
    books = dl_books(dl_data, roster, "Credit card", "90+ accruing")
    without = [b["cert"] for b in peers if b["cert"] != JPMORGAN]
    assert_delinquency(after, info, books, without, "quarter-end", "after the flip")
    moved = [k for k, (a, b) in enumerate(zip(dcol(before, info, "c"), dcol(after, info, "c")))
             if abs(num(a) - num(b)) > 1e-6]
    assert len(moved) == 38                         # JPMorgan's card book moves every quarter-end


def test_delinquency_pickers_move_product_measure_and_basis(dlq, dl_data, roster, tmp_path):
    """Mortgage (the second product), 30+ incl. nonaccrual (the last measure),
    four-quarter average: the composite is the mean of four composite
    quarter-ends, the band is over the banks' four-quarter averages, and
    the first three quarter-ends have neither."""
    p, info, _ = dlq
    wb = load_workbook(p)
    ws = wb["Delinquency"]
    ws["B4"], ws["B5"], ws["B6"] = "Mortgage", "30+ incl. nonaccrual", "four-quarter average"
    q = tmp_path / "pick.xlsx"
    wb.save(q)
    vals = recalc(q)
    books = dl_books(dl_data, roster, "Mortgage", "30+ incl. nonaccrual")
    certs = [b["cert"] for b in R.peers(roster)]
    comp, band_ = assert_delinquency(vals, info, books, certs, "four-quarter average", "mortgage 30+ avg")
    assert [r["avg4"] is None for r in comp[:4]] == [True, True, True, False]
    assert sum(r["avg4"] is not None for r in comp) == 35
    assert_lines(vals, info, books, roster, "four-quarter average")
    # The table counts the composite's banks and the band's separately: on
    # this basis they differ, and one "Banks in" said 11 over a blank band.
    differ = 0
    for k, (c, b) in enumerate(zip(comp, band_)):
        r = 39 + k
        assert num(vals["DELINQUENCY!B%d" % r]) == c["banks"] and num(vals["DELINQUENCY!G%d" % r]) == b["banks"]
        differ += c["banks"] != b["banks"]
    assert differ >= 10, differ


def test_the_visible_delinquency_table_reads_the_live_lines(dlq):
    p, info, vals = dlq
    ws = load_workbook(p)["Delinquency"]
    heads = [ws.cell(38, c).value for c in range(1, 10)]
    assert heads == ["Quarter-end", "Banks in the quarter-end composite", "Pack composite", "KeyBank", "Peer A",
                     "Peer B", "Banks in the band", "10th", "90th"]
    for c, h in enumerate(heads, 1):
        # A header wraps between words, never inside one ('Pack composi/te', 'KeyBan/k' in Excel).
        width = ws.column_dimensions[get_column_letter(c)].width
        assert width >= max(len(w) for w in h.split()) + 3, (h, width)
    for k, q in enumerate(info["delinquency"]["quarters"]):
        r = 39 + k
        assert vals["DELINQUENCY!A%d" % r] == q
        assert num(vals["DELINQUENCY!B%d" % r]) == num(dcol(vals, info, "banks")[k])
        assert num(vals["DELINQUENCY!G%d" % r]) == num(dcol(vals, info, "bandn")[k])
        for c_, name in zip("CDEFHI", ("c", "k", "a", "bb", "p10", "p90")):
            want = num(dcol(vals, info, name)[k])
            got = vals["DELINQUENCY!%s%d" % (c_, r)]
            assert (num(got) is None) if want is None else num(got) == pytest.approx(want), (q, name)


def test_delinquency_banks_needed_is_met_at_exactly_that_many(dlq, dl_data, roster, tmp_path):
    """Pack's banks needed set to 15 on mortgage, four-quarter average: the
    composite and the band are drawn with exactly 15 banks in (>=, not >),
    and the composite's average is blank wherever one of its four
    quarter-ends had fewer, though the others have a rate."""
    p, info, _ = dlq
    wb = load_workbook(p)
    wb["Pack"]["B10"] = 15
    ws = wb["Delinquency"]
    ws["B4"], ws["B5"], ws["B6"] = "Mortgage", "30-89", "four-quarter average"
    q = tmp_path / "fifteen.xlsx"
    wb.save(q)
    vals = recalc(q)
    books = dl_books(dl_data, roster, "Mortgage", "30-89")
    certs = [b["cert"] for b in R.peers(roster)]
    comp, band_ = assert_delinquency(vals, info, books, certs, "four-quarter average", "mortgage at 15",
                                     min_banks=15)
    assert max(r["banks"] for r in comp) == 15                           # 15 is the most there ever are
    assert sum(r["avg4"] is not None for r in comp) == 2                  # four straight quarter-ends at 15
    assert [r["banks"] for r in band_ if r["p10"] is not None] == [15, 15]
    partial = [r["q"] for i, r in enumerate(comp) if i >= 3 and r["avg4"] is None
               and any(x["rate"] is not None for x in comp[i - 3:i + 1])]
    assert len(partial) == 8, partial


def test_delinquency_average_needs_four_consecutive_quarter_ends(tmp_path, recent, roster, dl_data):
    """2020Q2 missing from the data: the four rows before 2020Q3 hold four
    quarter-ends, but not consecutive ones, so the composite's and the
    banks' averages are blank at 2020Q3 to 2021Q1, as in the module."""
    gap = {q: rows for q, rows in dl_data.items() if q != "20200630"}
    p = tmp_path / "gap.xlsx"
    info = make(p, recent, roster, "all", products=("Credit card",),
                delinquency=dq_spec(gap, products=("Credit card",), basis="four-quarter average"))
    vals = recalc(p)
    books = dl_books(gap, roster, "Credit card", "90+ accruing")
    certs = [b["cert"] for b in R.peers(roster)]
    comp, band_ = assert_delinquency(vals, info, books, certs, "four-quarter average", "card, 2020Q2 gone")
    assert len(comp) == 37 and "2020Q2" not in [r["q"] for r in comp]
    blank = [r["q"] for r in comp[3:] if r["avg4"] is None]
    assert blank == ["2020Q3", "2020Q4", "2021Q1"]
    assert all(r["rate"] is not None for r in comp)                      # every quarter-end has a composite
    assert [r["q"] for r in band_[3:] if r["p10"] is None] == blank
    assert_lines(vals, info, books, roster, "four-quarter average")


def test_delinquency_peer_note_names_the_product_best_and_worst_are_ranked_on(dlq):
    """Peer A and B's best and worst are ranked on the Pack tab's charge-off
    product, which need not be the delinquency product: the note says which."""
    _, _, vals = dlq
    assert vals["PACK!B4"] == "Credit card"
    assert "ranked there on credit card charge-offs" in vals["DELINQUENCY!C7"]


def test_delinquency_data_tab_holds_the_module_rows(dlq, dl_data, roster):
    p, info, _ = dlq
    ws = load_workbook(p)["DelinquencyData"]
    nq, nb, nm = 38, len(roster), len(D.MEASURES)
    assert info["delinquency"]["data_rows"] == len(TWO) * nm * nb * nq == ws.max_row - 1
    rows = rows_of(ws)
    for pi, product in enumerate(TWO):
        for mi, measure in enumerate(D.MEASURES):
            books = dl_books(dl_data, roster, product, measure)
            for bi, b in enumerate(roster):
                at = 1 + ((pi * nm + mi) * nb + bi) * nq
                for k, want in enumerate(books[b["cert"]]):
                    got = rows[at + k]
                    assert got[:5] == [product, measure, b["short"], b["cert"], want["q"]]
                    # Numbers to the precision the file keeps (openpyxl writes 15-16 digits).
                    assert got[5:] == pytest.approx([want["numerator"], want["balance"], want["rate"],
                                                     want["kept"], want["why"], want["avg4"],
                                                     want["avg4"] is not None, want["why_avg4"],
                                                     (want["why_avg4"] or "").startswith(D.WHY_JUMP_PREFIX)],
                                                    rel=1e-14, abs=1e-14)


def test_delinquency_chart_is_drawn_as_the_peers_charts(dlq):
    """Up-down bars between invisible 10th/90th and 25th/75th lines, then the
    composite, KeyBank, Peer A and Peer B, on a LineChart base; #N/A a gap."""
    p, info, _ = dlq
    h = info["delinquency"]["helpers"]
    with zipfile.ZipFile(p) as z:
        charts = [n for n in sorted(z.namelist()) if re.match(r"xl/charts/chart\d+\.xml$", n)
                  and "'Delinquency'!" in z.read(n).decode("utf-8")]
        assert len(charts) == 1
        xml = z.read(charts[0]).decode("utf-8")
    assert "<areaChart>" not in xml and "<barChart>" not in xml
    assert 'dispNaAsBlank val="1"' in xml and '<dispBlanksAs val="gap"' in xml and '<plotVisOnly val="0"' in xml
    groups = re.findall(r"<lineChart>.*?</lineChart>", xml)
    assert len(groups) == 3
    for g, (lo, hi) in zip(groups[:2], ((10, 90), (25, 75))):
        assert "<upDownBars>" in g
        assert re.findall(r"<val><numRef><f>'Delinquency'!\$([A-Z]+)\$", g) == [h["p%d" % lo], h["p%d" % hi]]
        assert all("<a:ln><a:noFill />" in x for x in re.findall(r"<ser>.*?</ser>", g))
    lines = re.findall(r"<val><numRef><f>'Delinquency'!\$([A-Z]+)\$", groups[2])
    assert lines == [h[n] for n in ("c", "k", "a", "bb")]
    ws = load_workbook(p)["Delinquency"]
    for c in range(column_index_from_string(h["uk"]) - 2, column_index_from_string(h["lb"]) + 1):
        assert ws.column_dimensions[get_column_letter(c)].hidden
    pickers = {str(r) for d in ws.data_validations.dataValidation for r in d.sqref.ranges}
    assert pickers == {"B4", "B5", "B6"}


def test_no_delinquency_formula_refers_above_row_1(dlq):
    p, _, _ = dlq
    bad = formulas_reaching_above_row_1(load_workbook(p))
    assert not bad, bad[:3]


def test_not_built_the_tabs_say_so(all_peers):
    p, info, _ = all_peers
    wb = load_workbook(p)
    assert info["delinquency"] is None
    for name in ("Delinquency", "DelinquencyData"):
        assert "Delinquency was not built" in wb[name]["A1"].value
    run = {r[0]: r for r in rows_of(wb["Run"]) if r and r[0]}
    assert run["Delinquency"][1] == "not built"


def test_delinquency_is_a_required_argument(tmp_path, recent, roster):
    kw = dict(exempt_self=True, min_banks=MIN_BANKS, index_min_book=500_000, lagged_years=(2019, 2025),
              lag_years=2, normalisation_years=(2019, 2025), mix_base_year=2019, industry=None, **RANK)
    with pytest.raises(TypeError, match="delinquency"):
        build_peers_workbook(tmp_path / "x.xlsx", recent, roster, ("Credit card",), JUMP, MIN_BOOK, "all",
                             MERGERS(), EXTRAS, "2019Q4", **kw)


def test_delinquency_run_tab_and_glossary(dlq):
    p, _, _ = dlq
    wb = load_workbook(p)
    run = {r[0]: r for r in rows_of(wb["Run"]) if r and r[0]}
    assert run["Delinquency"][1:3] == ["Credit card, Mortgage", "quarter-ends 2017Q1 to 2026Q2"]
    assert run["Delinquency jump"][1] == 0.25
    assert run["Delinquency minimum book ($000)"][1:3] == [1_000_000, "KeyBank exempt"]
    terms = [t for t, _, _ in PEER_TERMS]
    for must in ["Delinquency rate", "Measure", "Basis", "Quarter-end rate", "Four-quarter average",
                 "Not filed", "Delinquency composite", "Delinquency band", "Banks in the quarter-end composite",
                 "Banks in the band"] + list(D.MEASURES):
        assert must.lower() in [t.lower() for t in terms], must
    assert set(terms) <= {r[0] for r in rows_of(wb["Glossary"])}


def test_glossary_lists_everything_left_out_and_why(dlq):
    """The bank asked (12 Oct 2026) that what is omitted, and why, be stated
    plainly: one Glossary row per reason, each saying why, the rule, and where
    each omission is recorded."""
    p, _, _ = dlq
    rows = [r for r in rows_of(load_workbook(p)["Glossary"]) if r and r[0]]
    left = {r[0]: r for r in rows if r[0].startswith("Left out:")}
    assert sorted(left) == sorted([
        "Left out: an acquisition (the jump)", "Left out: a small book (the minimum book)",
        "Left out: not filed", "Left out: fewer than four quarters", "Left out: not included",
        "Left out: too few banks", "Left out: before a gap (series files)"])
    terms = [r[0] for r in rows]
    first = terms.index("Left out, and why")
    assert set(terms[first + 1:first + 1 + len(left)]) == set(left)       # together, under the heading
    assert "counted as 0" in rows[first][1]
    assert all(r[1] and r[2] for r in left.values())
    jump = left["Left out: an acquisition (the jump)"][2]
    assert "left out of the pack composite's four-quarter average" in jump and "last column" in jump
    for term, where in (("an acquisition (the jump)", "Why not kept"), ("a small book (the minimum book)", "Why not kept"),
                        ("not filed", "Why not kept"), ("fewer than four quarters", "Why no four-quarter average"),
                        ("not included", "Include is FALSE"), ("too few banks", "never drawn from fewer"),
                        ("before a gap (series files)", "note names")):
        assert where in left["Left out: " + term][2], term


@pytest.mark.parametrize("over, why", [
    (dict(measure=None), "missing: measure"),
    (dict(measure="60+"), "measure must be one of"),
    (dict(basis="annual"), "basis must be one of"),
    (dict(products=("Credit card", "Credit card")), "distinct"),
    (dict(products=("Cars",)), "distinct"),
    (dict(products=()), "distinct"),
    (dict(exempt_self="yes"), "exempt_self must be True or False"),
    (dict(jump=-0.1), "jump"),
    (dict(min_book=-1), "min_book"),
    (dict(data={}), "no quarter-ends"),
    (dict(cutoff=3), "not known: cutoff"),
    (dict(measure=["30-89"]), "measure must be one of"),
    (dict(basis=["quarter-end"]), "basis must be one of"),
    (dict(jump="0.25"), "jump must be a number"),
    (dict(jump=True), "jump must be a number"),
    (dict(min_book="1"), "min_book must be a number"),
    (dict(data=[{}]), r"data must be \{REPDTE: \[rows\]\}.*not a list"),
])
def test_a_bad_delinquency_setting_is_refused(tmp_path, recent, roster, dl_data, over, why):
    spec = dq_spec(dl_data)
    for k, v in over.items():
        if v is None:
            spec.pop(k)
        else:
            spec[k] = v
    with pytest.raises(ValueError, match=why):
        make(tmp_path / "x.xlsx", recent, roster, "all", products=("Credit card",), delinquency=spec)
    assert not (tmp_path / "x.xlsx").exists()


def test_delinquency_refuses_a_field_that_was_not_pulled(tmp_path, recent, roster, dl_data):
    """A field absent from every row of a quarter was not asked for: refused,
    not read as 'not filed'. Anything but None or a dict is refused too."""
    gap = {q: [{k: v for k, v in r.items() if k != "P9RERSFM"} if q == "20200630" else r for r in rows]
           for q, rows in dl_data.items()}
    with pytest.raises(ValueError, match="P9RERSFM.*1 quarter.*20200630"):
        make(tmp_path / "x.xlsx", recent, roster, "all", products=("Credit card",), delinquency=dq_spec(gap))
    with pytest.raises(ValueError, match="None .not built. or a dict"):
        make(tmp_path / "x.xlsx", recent, roster, "all", products=("Credit card",), delinquency=[dl_data])
    # A quarter with no rows: nobody filed, not a field left out of the pull.
    with pytest.raises(ValueError, match="no rows .no filer. in 1 quarter.*20200630"):
        make(tmp_path / "x.xlsx", recent, roster, "all", products=("Credit card",),
             delinquency=dq_spec(dict(dl_data, **{"20200630": []})))
    assert not (tmp_path / "x.xlsx").exists()
