"""The bank credit series: built by the threshold engine's own peers build from an FDIC cache, then read like any
other download. Run on the threshold engine's own test data (tests/data/peers: the roster banks' filed Call Report
rows), so no test reaches the FDIC."""
import json
import pathlib

import pytest

from conftest import DATA
from threshold_engine.macro import fdic_credit as F
from threshold_engine.macro.catalog import BY_KEY, SERIES

PEERS = DATA / "peers"


def _cache(root):
    """The roster banks' delinquency rows with their charge-off fields, 2017Q1 to 2026Q2, laid out as the FDIC
    cache 'peers pull --delinquency yes' writes (as tests/test_peers_into.py builds it)."""
    dl = json.loads((PEERS / "delinquency_roster.json").read_text())
    co = json.loads((PEERS / "roster_2006.json").read_text())
    cache = root / "fdic"
    cache.mkdir(parents=True)
    for q, rows in dl.items():
        merged = []
        for r in rows:
            row = dict(r)
            row.update(next(x for x in co[q] if x["CERT"] == r["CERT"]))
            merged.append(row)
        (cache / ("q%s.json" % q)).write_text(json.dumps(merged), encoding="utf-8")
    return dl


def _fetch(asked):
    """The FDIC as a test sees it: the merger record holds nothing, and the quarter after 2026Q2 has no filer yet
    (the API's own answer for an unpublished quarter, {"meta": {"total": 0}, "data": []})."""
    def fetch(url):
        asked.append(url)
        if "/history" in url or "REPDTE%3A20260930" in url or "REPDTE:20260930" in url:
            return {"data": [], "meta": {"total": 0}}
        raise AssertionError("a cached quarter was fetched again: %s" % url)
    return fetch


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("bank")
    dl = _cache(root)
    asked = []
    raw = F.build_file(root, "2026-10-23", fetch=_fetch(asked), first="2017Q1")
    return root, dl, json.loads(raw), raw, asked


def test_the_latest_quarter_is_the_one_just_ended():
    assert F.latest_quarter("2026-10-23") == "2026Q3"
    assert F.latest_quarter("2026-01-05") == "2025Q4"
    assert F.latest_quarter("2026-04-01") == "2026Q1"


def test_an_unpublished_quarter_steps_the_build_back_one_and_nothing_cached_is_fetched_again(built):
    root, _, got, _, asked = built
    assert got["last"] == "2026Q2" and got["first"] == "2017Q1"
    assert any("20260930" in u for u in asked) and not (root / "fdic" / "q20260930.json").exists()
    assert sum("/history" in u for u in asked) >= 1                 # the merger record, read afresh each pull


def test_every_bank_series_in_the_catalog_is_in_the_file(built):
    _, _, got, _, _ = built
    ids = {s.source_id for s in SERIES if s.source == "fdic"}
    assert len(ids) == 56 and ids <= set(got["series"])          # every product, both, net and six delinquencies
    assert got["self"] == {"cert": "17534", "name": "KeyBank NA"}
    assert got["settings"]["jump"] == F.book_settings()["jump"]    # the consumer book's answers, as recorded


def test_the_30_plus_rates_are_the_filings_own_arithmetic(built):
    # KeyBank's card 30+ at 2026Q2 is 100 x (30-89 + 90+ accruing + nonaccrual) / balance from its own row, and
    # every filer's is the same sums over every row: worked here from the cache, not from the threshold engine.
    _, dl, got, _, _ = built
    rows = dl["20260630"]
    me = next(r for r in rows if str(r["CERT"]) == "17534")
    mine = 100 * (me["P3CRCD"] + me["P9CRCD"] + me["NACRCD"]) / me["LNCRCD"]
    every = [r for r in rows if all(r.get(f) is not None for f in ("P3CRCD", "P9CRCD", "NACRCD", "LNCRCD"))]
    industry = 100 * sum(r["P3CRCD"] + r["P9CRCD"] + r["NACRCD"] for r in every) / sum(r["LNCRCD"] for r in every)
    late = dict(F.read(json.dumps(got).encode(), BY_KEY["card_late_keybank"].source_id))
    assert late["2026-04-01"] == pytest.approx(mine, abs=1e-9)
    late_all = dict(F.read(json.dumps(got).encode(), BY_KEY["card_late_all_banks"].source_id))
    assert late_all["2026-04-01"] == pytest.approx(industry, abs=1e-9)


def test_30_plus_still_accruing_is_worked_from_the_filings_never_by_adding_two_rates(built):
    # Not one of the threshold engine's measures, so worked out from the same filings: KeyBank's own 100 x (30-89 +
    # 90+ accruing) / balance, and every filer's that filed all three, summed, worked here from the cache.
    _, dl, got, _, _ = built
    rows = dl["20260630"]
    me = next(r for r in rows if str(r["CERT"]) == "17534")
    mine = 100 * (me["P3CRCD"] + me["P9CRCD"]) / me["LNCRCD"]
    every = [r for r in rows if all(r.get(f) is not None for f in ("P3CRCD", "P9CRCD", "LNCRCD"))]
    industry = 100 * sum(r["P3CRCD"] + r["P9CRCD"] for r in every) / sum(r["LNCRCD"] for r in every)
    raw = json.dumps(got).encode()
    assert dict(F.read(raw, BY_KEY["card_late_30_accruing_keybank"].source_id))["2026-04-01"] == \
        pytest.approx(mine, abs=1e-9)
    assert dict(F.read(raw, BY_KEY["card_late_30_accruing_all_banks"].source_id))["2026-04-01"] == \
        pytest.approx(industry, abs=1e-9)
    # and it is 30+ incl. nonaccrual less the nonaccrual, for KeyBank, whose rates share one balance
    incl = dict(F.read(raw, BY_KEY["card_late_keybank"].source_id))["2026-04-01"]
    non = dict(F.read(raw, BY_KEY["card_nonaccrual_keybank"].source_id))["2026-04-01"]
    assert incl - non == pytest.approx(mine, abs=1e-9)
    note = got["series"][BY_KEY["card_late_30_accruing_all_banks"].source_id]["note"]
    assert any("Worked out in the Macrobook" in n for n in note) and any("read with care" in n for n in note)


def test_a_quarter_is_dated_by_its_first_month_and_the_cache_path_stays_out(built):
    root, _, got, raw, _ = built
    pts = F.read(raw, BY_KEY["card_losses_all_banks"].source_id)
    assert all(d[5:7] in ("01", "04", "07", "10") and d.endswith("-01") for d, _ in pts)
    assert str(root) not in raw.decode()                          # notes name "the pull's FDIC cache", not a path
    notes = [n for v in got["series"].values() for n in v["note"]]
    assert any("from the pull's FDIC cache." in n for n in notes) and not any("the cache the" in n for n in notes)
    assert any("Credit card, net charge-off rate" in n for n in got["series"]["credit-card_industry_net"]["note"])


def test_an_installed_copy_reads_the_book_from_the_folder_it_is_run_from_and_refuses_without_it(tmp_path,
                                                                                                monkeypatch):
    # "pip install ." puts the module under site-packages, away from books/ and config/ (Codex on #472): the
    # build then reads them from the folder it is run from, threshold-engine/, and says what it needs elsewhere.
    engine = pathlib.Path(F.__file__).resolve().parents[3]
    monkeypatch.setattr(F, "HERE", tmp_path / "lib" / "site-packages" / "threshold_engine" / "macro" / "f.py")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="books/consumer-public.json.*run it from threshold-engine/"):
        F.book_settings()
    with pytest.raises(RuntimeError, match="run it from threshold-engine/"):
        F.build_file(tmp_path, "2026-10-23", fetch=_fetch([]))
    monkeypatch.chdir(engine)
    assert F.engine_folder() == engine
    assert F.book_settings() == json.loads((engine / "books" / "consumer-public.json").read_text())["peers"]


def test_reading_refuses_a_file_that_is_not_the_bank_credit_file():
    with pytest.raises(ValueError, match="not the bank credit file"):
        F.read(b"<html>", "credit-card_keybank_net")
    with pytest.raises(ValueError, match="has no series"):
        F.read(json.dumps({"series": {}}).encode(), "credit-card_keybank_net")
