"""A peers pull and build from 1991Q1.

The firm, 17 Oct 2026, on the commercial proposal's question 6 ("agreed
with the recommendation" on the docket form): "Pull commercial history from
1991Q1, not 2006Q1 as for consumer?" The recommendation: "The early-1990s CRE
losses are in it; splits still start 2007Q1."

What blocked it was the merger record since 1990: FDIC history codes 213 and
225 were on neither list, so 'peers pull --mergers 1990-01-01' refused, and
a build from 1991Q1 had no merger record to read. Question 17 placed both
(213 an acquisition, 225 not). These tests hold the whole path from 1991Q1:
the pull of the merger record since 1990, then a build from 1991Q1 that
reads it.

The data are public and real. tests/data/peers/keybank_ci_1991.json is
KeyBank (17534) and the four banks the FDIC record says it absorbed in 1992
and 1993 (6568, 746, 26650, 777), 1991Q1 to 1993Q4, as they are in the
commercial cache. tests/data/peers/history_1990.json is twelve FDIC history
rows as the API returned them on 18 Oct 2026: the three 213 rows (May 1990),
the one 225 row (1991), and KeyBank's four absorptions of 1992 and 1993 with
the 810 mirror row of each. The README beside them says how each was taken.
The rates below are arithmetic on the fixture, done here, not by the code
under test.
"""
import json
import urllib.parse

import pytest

from conftest import ROOT
from threshold_engine import cli
from threshold_engine.peers import fdic
from threshold_engine.series import read_csv, read_notes

PEERS = ROOT / "tests" / "data" / "peers"
KEYBANK, ABSORBED = "17534", ("6568", "746", "26650", "777")


def fixture():
    return json.loads((PEERS / "keybank_ci_1991.json").read_text(encoding="utf-8"))


def history():
    return json.loads((PEERS / "history_1990.json").read_text(encoding="utf-8"))


class Fake:
    """The FDIC API over the two fixtures: financials by quarter, the fields
    asked for (a null where a row lacks one), and the history rows, paged the
    way the API pages."""

    def __init__(self, data, rows):
        self.data, self.rows = data, rows

    def __call__(self, url):
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        offset, limit = int(q["offset"][0]), int(q["limit"][0])
        if url.startswith(fdic.HISTORY_URL):
            rows = self.rows
        elif url.startswith(fdic.INSTITUTIONS_URL):
            rows = json.loads((PEERS / "institutions_keybank.json").read_text(encoding="utf-8"))
        else:
            asked = q["fields"][0].split(",")
            rows = [{f: r.get(f) for f in asked} for r in self.data[q["filters"][0].split(":")[1]]]
        return {"data": [{"data": r} for r in rows[offset:offset + limit]], "meta": {"total": len(rows)}}


def no_sleep(seconds):
    return None


def pull(cache, monkeypatch, rows):
    monkeypatch.setattr(fdic, "urllib_fetch", Fake(fixture(), rows))
    monkeypatch.setattr(fdic.time, "sleep", no_sleep)
    return cli.main(["peers", "pull", "--cache", str(cache), "--first", "1991Q1", "--last", "1993Q4",
                     "--products", "C&I", "--delinquency", "yes", "--mergers", "1990-01-01"])


def test_the_fixtures_are_what_the_readme_says():
    data = fixture()
    assert sorted(data) == ["%d%s" % (y, md) for y in (1991, 1992, 1993)
                            for md in ("0331", "0630", "0930", "1231")]
    certs = {str(r["CERT"]) for rows in data.values() for r in rows}
    assert certs == {KEYBANK, *ABSORBED}
    assert sum(len(v) for v in data.values()) == 38
    # The 1992Q1 step as filed: KeyBank's own C&I rose 37%, the quarter 6568 joined it.
    kb = {q: next(r for r in rows if str(r["CERT"]) == KEYBANK) for q, rows in data.items()}
    assert kb["19920331"]["LNCI"] / kb["19911231"]["LNCI"] - 1 == pytest.approx(0.3726, abs=1e-4)
    codes = sorted(r["CHANGECODE"] for r in history())
    assert codes == [213, 213, 213, 222, 223, 223, 223, 225, 810, 810, 810, 810]


def test_the_merger_record_since_1990_is_pulled_now_that_213_and_225_are_placed(tmp_path, monkeypatch, capsys):
    cache = tmp_path / "cache"
    assert pull(cache, monkeypatch, history()) == 0
    mergers = json.loads((cache / "mergers.json").read_text(encoding="utf-8"))
    # 213 is an acquisition: each of its three acquirers is marked in 1990Q2.
    # 225 is not: its acquirer (15689) is not marked.
    assert mergers == {"17534": ["1992-03-31", "1992-09-30", "1993-09-30"],
                       "33057": ["1990-06-30"], "33097": ["1990-06-30"], "33110": ["1990-06-30"]}
    links = json.loads((cache / "absorptions.json").read_text(encoding="utf-8"))
    assert [ln for ln in links if ln["acquirer"] == KEYBANK] == [
        {"acquirer": "17534", "absorbed": "6568", "quarter": "1992-03-31"},
        {"acquirer": "17534", "absorbed": "26650", "quarter": "1992-09-30"},
        {"acquirer": "17534", "absorbed": "746", "quarter": "1992-09-30"},
        {"acquirer": "17534", "absorbed": "777", "quarter": "1993-09-30"}]
    assert len(links) == 7
    assert len(list(cache.glob("q*.json"))) == 12


def test_without_213_placed_the_same_pull_is_refused_by_name(tmp_path, monkeypatch, capsys):
    # What question 17 unblocked: with 213 on neither list, the pull stops
    # and names each row, and no merger record is written.
    monkeypatch.delitem(fdic.ACQUISITIONS, 213)
    assert pull(tmp_path / "cache", monkeypatch, history()) == 2
    err = capsys.readouterr().err
    assert "3 FDIC history row(s)" in err
    assert "code 213 (Merger - Assisted), acquirer 33097, effective 1990-05-04" in err
    assert not (tmp_path / "cache" / "mergers.json").exists()


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("from1991")
    cache = tmp / "cache"
    mp = pytest.MonkeyPatch()
    try:
        assert pull(cache, mp, history()) == 0
        mp.setattr(fdic, "urllib_fetch", lambda url: (_ for _ in ()).throw(AssertionError(url)))
        rc = cli.main([
            "peers", "build", str(tmp / "peers.xlsx"), "--cache", str(cache),
            "--roster", str(ROOT / "config" / "peers.json"), "--series-dir", str(tmp / "series"),
            "--first", "1991Q1", "--last", "1993Q4", "--products", "C&I",
            "--mergers", str(cache / "mergers.json"), "--absorptions", str(cache / "absorptions.json"),
            "--extra-acquisitions", "--industry-combined", "--delinquency", "yes",
            "--reporting-changes", str(ROOT / "config" / "reporting-changes.json"),
            "--stated-acquisitions", str(ROOT / "config" / "stated-acquisitions.json"),
            "--jump", "0.25", "--acquisition-share", "0.05", "--min-book", "0", "--exempt-self", "yes",
            "--pro-forma", "yes", "--pack", "all", "--min-banks", "1", "--rank-by", "net",
            "--last-n", "4", "--min-obs", "2", "--base-quarter", "1992Q4", "--index-min-book", "0",
            "--lagged-years", "1992", "--lag-years", "1", "--normalisation-years", "1992", "1993",
            "--mix-base-year", "1992"])
    finally:
        mp.undo()
    return dict(rc=rc, tmp=tmp)


def test_a_build_from_1991q1_runs_and_keybanks_ci_starts_at_its_first_window(built):
    assert built["rc"] == 0 and (built["tmp"] / "peers.xlsx").exists()
    path = built["tmp"] / "series" / "c-i_keybank_net.csv"
    pts = read_csv(path)
    # A bank's window needs the quarter before it too (the jump is measured
    # against it), so KeyBank's first is 1992Q1 (1991Q2 to 1992Q1). Eight
    # windows to 1993Q4, none left out: pro forma adds the four banks KeyBank
    # absorbed, so the 1992 acquisitions (37% and 60% steps as filed) neither
    # break the series nor trip the jump.
    assert [p.date for p in pts] == ["1992-03-31", "1992-06-30", "1992-09-30", "1992-12-31",
                                     "1993-03-31", "1993-06-30", "1993-09-30", "1993-12-31"]
    assert not [v for k, v in read_notes(path) if k == "left-out"]
    # 1992Q1 by hand. Every row in the fixture is KeyBank pro forma until its
    # absorption, and an absorbed bank stops filing when absorbed (6568 has no
    # 1992Q1 row), so the window is every row's flow, summed:
    # 1991Q2 to Q4 = Q4 year-to-date less Q1's (no bank changed parent in
    # 1991), and 1992Q1 = its year-to-date.
    data = fixture()

    def net(q):
        return sum(r["DRCI"] - r["CRCI"] for r in data[q])

    for q in ("19910331", "19911231"):
        assert len({r["RSSDHCR"] for r in data[q] if str(r["CERT"]) in ("746", "26650")}) == 1
    flows = net("19911231") - net("19910331") + net("19920331")
    avg = sum(sum(r["LNCI"] for r in data[q]) for q in ("19910630", "19910930", "19911231", "19920331")) / 4
    assert pts[0].value == pytest.approx(100 * flows / avg)


def test_the_build_from_1991q1_writes_the_industry_and_the_delinquency_it_can(built):
    series = built["tmp"] / "series"
    # The industry applies no jump, so its first window is 1991Q4.
    ind = read_csv(series / "c-i_industry_net.csv")
    assert (ind[0].date, ind[-1].date, len(ind)) == ("1991-12-31", "1993-12-31", 9)
    # Nonaccrual is filed from 1991Q1. Delinquency is each bank as filed, so
    # KeyBank's quarter-end rate is its own, from 1991Q1.
    na = read_csv(series / "c-i_keybank_delinquency-nonaccrual_quarter-end.csv")
    kb = next(r for r in fixture()["19910331"] if str(r["CERT"]) == KEYBANK)
    assert na[0].date == "1991-03-31"
    assert na[0].value == pytest.approx(100 * kb["NACI"] / kb["LNCI"])
    # 30-89 days past due is first filed in 2001Q1: blank in every row here,
    # so neither measure that reads it (30-89, 30+ incl. nonaccrual) is
    # written for KeyBank or the industry, never as zeros.
    assert all(r["P3CI"] is None for rows in fixture().values() for r in rows)
    assert not list(series.glob("c-i_*_delinquency-30-*"))
    assert len(list(series.glob("c-i_keybank_delinquency-*"))) == 6
