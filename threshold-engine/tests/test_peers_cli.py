"""The peers commands: `peers pull` fills a cache through the FDIC downloader
(a fake here, never the network), and `peers build` reads only that cache,
writes the peer workbook, and writes series CSVs the `workbook` command takes.

The round trip is tied out to the earlier build: the all-peer composite CSV
and KeyBank's own CSVs must equal expected_books.json to 4 decimals. What is
passed on to the workbook is recorded and checked setting by setting, and
every setting a person states is refused when it is missing or out of range."""
import argparse
import csv
import json
import urllib.parse

import pytest
from openpyxl import load_workbook

from conftest import DATA, ROOT
from threshold_engine import cli
from threshold_engine.cli import main
from threshold_engine.peers import fdic
from threshold_engine.peers import roster as R
from threshold_engine.peers import peers_workbook
from threshold_engine.peers.books import bank_book, composite, industry, quarter_end

PEERS = DATA / "peers"
FOUR = ["Credit card", "Mortgage", "Home equity", "Other consumer"]
KEYBANK = "17534"

#: The earlier build's settings (expected_books.json["rules"]).
BUILD = ["--roster", str(ROOT / "config" / "peers.json"), "--first", "2006Q1", "--last", "2026Q2",
         "--products"] + FOUR + [
    "--mergers", str(PEERS / "mergers_roster.json"), "--extra-acquisitions", "6672=2022Q2",
    "--industry-combined", "--jump", "0.25", "--min-book", "1000000", "--exempt-self", "yes", "--pack", "all",
    "--min-banks", "5", "--rank-by", "net", "--last-n", "20", "--min-obs", "12",
    "--base-quarter", "2019Q4", "--index-min-book", "500000", "--lagged-years", "2019", "2025",
    "--lag-years", "2", "--normalisation-years", "2019", "2025", "--mix-base-year", "2019"]

MEASURE = ["--name", "Net charge-offs", "--unit", "%", "--direction", "higher_is_worse",
           "--frequency", "quarterly", "--smoothing", "1", "--floor-at-zero", "yes",
           "--moderate-halfwidth", "0.5", "--low-step", "1.0", "--high-z", "2.5",
           "--on-the-line", "worse", "--percentiles", "50", "75", "90", "95",
           "--horizon", "4", "--min-history", "12"]


def no_network(url):
    raise AssertionError("a test tried to fetch %s" % url)


def read_csv(path):
    """(notes, [(date, value)]) from a series CSV."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    notes = [ln[2:] for ln in lines if ln.startswith("#")]
    rows = list(csv.DictReader(ln for ln in lines if not ln.startswith("#")))
    return notes, [(r["date"], float(r["value"])) for r in rows]


@pytest.fixture(scope="module")
def data():
    return json.loads((PEERS / "roster_2006.json").read_text())


@pytest.fixture(scope="module")
def built(tmp_path_factory, data):
    """roster_2006.json laid out as a pull's cache, then `peers build` over it,
    with the downloader replaced by one that fails the test if it is called."""
    base = tmp_path_factory.mktemp("peers_cli")
    cache = base / "cache"
    cache.mkdir()
    for q, rows in data.items():
        (cache / ("q%s.json" % q)).write_text(json.dumps(rows), encoding="utf-8")
    mp = pytest.MonkeyPatch()
    mp.setattr(fdic, "urllib_fetch", no_network)
    try:
        out, series = base / "peers.xlsx", base / "series"
        rc = main(["peers", "build", str(out), "--cache", str(cache), "--series-dir", str(series)] + BUILD)
    finally:
        mp.undo()
    return dict(rc=rc, out=out, series=series, cache=cache, base=base)


def test_build_writes_the_workbook_and_six_series_per_product(built):
    assert built["rc"] == 0
    wb = load_workbook(built["out"])
    assert wb.sheetnames[:2] == ["Pack", "Peers"] and "Run" in wb.sheetnames
    names = sorted(p.name for p in built["series"].glob("*.csv"))
    assert len(names) == 4 * 6
    for slug in ("credit-card", "mortgage", "home-equity", "other-consumer"):
        for who in ("pack-composite", "keybank", "industry"):
            for kind in ("gross", "net"):
                assert "%s_%s_%s.csv" % (slug, who, kind) in names


def test_the_pack_composite_series_ties_out_to_the_earlier_build(built):
    """Acceptance 2, through the CLI and a CSV: the all-15-peer composite."""
    expected = json.loads((PEERS / "expected_books.json").read_text())
    dates = [quarter_end(q) for q in expected["quarters"]]
    checked = 0
    for p, slug in zip(FOUR, ("credit-card", "mortgage", "home-equity", "other-consumer")):
        for kind in ("gross", "net"):
            want = dict(zip(dates, expected["composite"][p][kind]))
            _, rows = read_csv(built["series"] / ("%s_pack-composite_%s.csv" % (slug, kind)))
            assert rows and rows[-1][0] == "2026-06-30"
            for d, v in rows:
                assert want[d] is not None and round(v, 4) == pytest.approx(want[d], abs=1e-9), (p, kind, d)
                checked += 1
            # Everything after the first written quarter is written: no gap, no fill.
            after = [d for d in dates if d >= rows[0][0]]
            assert [d for d, _ in rows] == after
    assert checked > 500


def test_a_break_is_named_and_the_series_starts_after_it(built):
    """KeyBank's card book breaks (2016-17 jump): written from after the break,
    the earlier quarters named in a note, never filled."""
    notes, rows = read_csv(built["series"] / "credit-card_keybank_net.csv")
    assert rows[0][0] == "2018-03-31" and rows[-1][0] == "2026-06-30"
    assert any("left out" in n and "2017Q4" in n for n in notes)
    assert any("KeyBank exempt" in n for n in notes)
    assert not any("Ends at" in n for n in notes)


def test_keybanks_own_series_tie_out_to_the_earlier_build(built):
    """Acceptance 1 for the bank itself, through the CLI and a CSV: gross and
    net, every product, equal expected_books.json["banks"]["17534"] to 4
    decimals, and each CSV is exactly the latest unbroken run of its values."""
    expected = json.loads((PEERS / "expected_books.json").read_text())
    dates = [quarter_end(q) for q in expected["quarters"]]
    for p, slug in zip(FOUR, ("credit-card", "mortgage", "home-equity", "other-consumer")):
        for kind in ("gross", "net"):
            want = list(zip(dates, expected["banks"][KEYBANK][p][kind]))
            end = len(want)
            while want[end - 1][1] is None:
                end -= 1
            start = end
            while start and want[start - 1][1] is not None:
                start -= 1
            _, rows = read_csv(built["series"] / ("%s_keybank_%s.csv" % (slug, kind)))
            assert [d for d, _ in rows] == [d for d, _ in want[start:end]], (p, kind)
            assert [round(v, 4) for _, v in rows] == pytest.approx(
                [v for _, v in want[start:end]], abs=1e-9), (p, kind)
    _, gross = read_csv(built["series"] / "credit-card_keybank_gross.csv")
    _, net = read_csv(built["series"] / "credit-card_keybank_net.csv")
    assert all(g > n for (_, g), (_, n) in zip(gross, net))     # gross is not net


def test_the_industry_series_is_books_industry_over_the_cache(built, data):
    notes, rows = read_csv(built["series"] / "mortgage_industry_gross.csv")
    want = {r["date"]: r["gross_rate"] for r in industry(data, "Mortgage")}
    assert len(rows) == len(want) == 79
    assert all(v == pytest.approx(want[d], abs=1e-12) for d, v in rows)
    assert any("every filer in the cache (16 in 2026Q2)" in n for n in notes)


def test_the_workbook_command_takes_the_series(built, capsys):
    """The round trip: peers build's CSVs feed the main workbook as they are."""
    s = built["series"]
    labels = [("Card pack net", "credit-card_pack-composite_net.csv"),
              ("Card KeyBank net", "credit-card_keybank_net.csv"),
              ("Card industry net", "credit-card_industry_net.csv"),
              ("Other consumer pack gross", "other-consumer_pack-composite_gross.csv")]
    out = built["base"] / "thresholds.xlsx"
    capsys.readouterr()
    rc = main(["workbook", str(out)] + [a for lbl, f in labels for a in ("--series", "%s=%s" % (lbl, s / f))]
              + MEASURE)
    printed = capsys.readouterr()
    assert rc == 0, printed.err
    assert "Card pack net, Card KeyBank net, Card industry net, Other consumer pack gross" in printed.out
    da = load_workbook(out)["Data"]
    head = [c.value for c in da[1]]
    _, pack = read_csv(s / "credit-card_pack-composite_net.csv")
    col = head.index("Card pack net")
    by_q = {r[0].value: r[col].value for r in da.iter_rows(min_row=2)}
    got = [by_q["%sQ%d" % (d[:4], (int(d[5:7]) - 1) // 3 + 1)] for d, _ in pack]
    assert got == pytest.approx([v for _, v in pack], abs=1e-12)


def test_build_never_fetches_and_refuses_a_quarter_not_in_the_cache(built, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fdic, "urllib_fetch", no_network)
    cache = tmp_path / "cache"
    cache.mkdir()
    for f in built["cache"].glob("q2006*.json"):
        (cache / f.name).write_bytes(f.read_bytes())
    args = with_value(BUILD, "--extra-acquisitions")      # 2022Q2 is outside 2006Q1-2007Q1
    args[args.index("--last") + 1] = "2007Q1"
    rc = main(["peers", "build", str(tmp_path / "x.xlsx"), "--cache", str(cache),
               "--series-dir", str(tmp_path / "s")] + args)
    err = capsys.readouterr().err
    assert rc == 2 and "REFUSED" in err and "peers pull" in err and "20070331" in err
    assert not (tmp_path / "x.xlsx").exists()


def test_a_badly_formed_declared_acquisition_is_refused(built, tmp_path, capsys):
    args = list(BUILD)
    args[args.index("6672=2022Q2")] = "6672=Q2-2022"
    rc = main(["peers", "build", str(tmp_path / "x.xlsx"), "--cache", str(built["cache"]),
               "--series-dir", str(tmp_path / "s")] + args)
    assert rc == 2 and "CERT=YYYYQn" in capsys.readouterr().err


#: Every flag `peers build` takes. Each is a judgement or a location, and none has a default.
BUILD_FLAGS = ["--cache", "--series-dir", "--roster", "--first", "--last", "--products", "--mergers",
               "--extra-acquisitions", "--industry-combined", "--jump", "--min-book", "--exempt-self",
               "--pack", "--min-banks", "--rank-by", "--last-n", "--min-obs", "--base-quarter",
               "--index-min-book", "--lagged-years", "--lag-years", "--normalisation-years",
               "--mix-base-year"]


def without(args, flag):
    """``args`` with ``flag`` and its values taken out."""
    i = args.index(flag)
    j = i + 1
    while j < len(args) and not args[j].startswith("--"):
        j += 1
    return args[:i] + args[j:]


def test_the_flag_list_is_every_build_flag():
    """So the parametrized test below cannot fall behind the parser."""
    def sub(parser, name):
        return next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction)).choices[name]
    bu = sub(sub(cli._parser(), "peers"), "build")
    stated = sorted(s for a in bu._actions for s in a.option_strings if s.startswith("--") and s != "--help")
    assert stated == sorted(BUILD_FLAGS)


@pytest.mark.parametrize("drop", BUILD_FLAGS)
def test_every_build_judgement_must_be_stated(built, tmp_path, drop, capsys):
    args = ["peers", "build", str(tmp_path / "x.xlsx"), "--cache", str(built["cache"]),
            "--series-dir", str(tmp_path / "s")] + BUILD
    with pytest.raises(SystemExit) as stop:
        main(without(args, drop))
    assert stop.value.code == 2 and drop in capsys.readouterr().err
    assert not (tmp_path / "x.xlsx").exists()


def test_no_declared_acquisitions_is_stated_by_the_bare_flag():
    a = cli._parser().parse_args(["peers", "build", "x.xlsx", "--cache", "c", "--series-dir", "s"]
                                 + BUILD[:BUILD.index("6672=2022Q2")] + BUILD[BUILD.index("6672=2022Q2") + 1:])
    assert a.extra_acquisitions == []


def test_unbroken_tail_names_what_is_left_out_at_both_ends():
    rows = [("2010Q1", None), ("2010Q2", 1.0), ("2010Q3", None), ("2010Q4", 2.0),
            ("2011Q1", 3.0), ("2011Q2", None), ("2011Q3", None)]
    tail, before, after = cli._unbroken_tail(rows)
    assert tail == [("2010Q4", 2.0), ("2011Q1", 3.0)]
    assert before == ["2010Q1", "2010Q2", "2010Q3"]
    assert after == ["2011Q2", "2011Q3"]
    assert cli._unbroken_tail([("2010Q1", None)]) == ([], [], ["2010Q1"])
    assert cli._unbroken_tail([("2010Q1", 1.0)]) == ([("2010Q1", 1.0)], [], [])


# ---------------------------------------------------------------- pull

class FakeFDIC:
    """Stands in for the FDIC API: financials rows for the asked REPDTE, and
    history rows; records every URL."""

    def __init__(self, data, history=()):
        self.data, self.history, self.urls = data, list(history), []

    def __call__(self, url):
        self.urls.append(url)
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        offset, limit = int(q["offset"][0]), int(q["limit"][0])
        if url.startswith(fdic.HISTORY_URL):
            rows = self.history
        else:
            rows = self.data[q["filters"][0].split(":")[1]]
        page = rows[offset:offset + limit]
        return {"data": [{"data": r} for r in page], "meta": {"total": len(rows)}}


def test_pull_fills_the_cache_then_fetches_only_what_is_missing(data, tmp_path, monkeypatch, capsys):
    fake = FakeFDIC(data)
    monkeypatch.setattr(fdic, "urllib_fetch", fake)
    cache = tmp_path / "cache"
    pull = ["peers", "pull", "--cache", str(cache), "--products", "Credit card", "Mortgage"]
    assert main(pull + ["--first", "2025Q1", "--last", "2025Q4"]) == 0
    assert len(fake.urls) == 4 and "fetched" in capsys.readouterr().out
    assert sorted(p.name for p in cache.glob("q*.json")) == [
        "q20250331.json", "q20250630.json", "q20250930.json", "q20251231.json"]
    assert json.loads((cache / "q20251231.json").read_text()) == data["20251231"]
    assert "LNCRCD" in fake.urls[0] and "DRRERSFM" in fake.urls[0]

    assert main(pull + ["--first", "2025Q1", "--last", "2026Q2"]) == 0
    assert len(fake.urls) == 6                              # 2026Q1 and Q2 only
    assert "6 quarters 2025Q1 to 2026Q2, 2 fetched, 4 already there" in capsys.readouterr().out

    assert main(pull + ["--first", "2025Q1", "--last", "2026Q2", "--refresh"]) == 0
    assert len(fake.urls) == 12


def test_pull_with_mergers_writes_the_classified_record(data, tmp_path, monkeypatch, capsys):
    history = [
        {"CHANGECODE": 223, "ACQ_CERT": "6672", "EFFDATE": "2019-01-15", "OUT_CERT": "1"},
        {"CHANGECODE": 712, "ACQ_CERT": "6672", "EFFDATE": "2020-05-01"},     # branch purchase: not one
    ]
    fake = FakeFDIC({"20260630": data["20260630"]}, history)
    monkeypatch.setattr(fdic, "urllib_fetch", fake)
    cache = tmp_path / "cache"
    rc = main(["peers", "pull", "--cache", str(cache), "--first", "2026Q2", "--last", "2026Q2",
               "--products", "Credit card", "--mergers", "2005-10-01"])
    assert rc == 0
    assert json.loads((cache / "mergers.json").read_text()) == {"6672": ["2019-03-31"]}
    assert any(u.startswith(fdic.HISTORY_URL) and "2005-10-01" in urllib.parse.unquote_plus(u)
               for u in fake.urls)
    assert "Filers in 2026Q2: 16" in capsys.readouterr().out


def test_pull_refuses_a_bad_quarter_and_a_failed_fetch(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fdic, "urllib_fetch", no_network)
    rc = main(["peers", "pull", "--cache", str(tmp_path), "--first", "2026-06", "--last", "2026Q2",
               "--products", "Auto"])
    assert rc == 2 and "2006Q1" in capsys.readouterr().err

    def broken(url):
        raise OSError("connection refused")
    monkeypatch.setattr(fdic, "urllib_fetch", broken)
    real_pull = fdic.pull                                   # the 5, 10, 15 s waits, skipped
    monkeypatch.setattr(fdic, "pull", lambda *a, **k: real_pull(*a, sleep=lambda s: None, **k))
    rc = main(["peers", "pull", "--cache", str(tmp_path / "c"), "--first", "2026Q2", "--last", "2026Q2",
               "--products", "Auto"])
    assert rc == 2 and "connection refused" in capsys.readouterr().err
    assert not list((tmp_path / "c").glob("q*.json"))


def test_the_roster_in_the_build_is_the_one_in_config():
    assert R.self_bank(R.load(ROOT / "config" / "peers.json"))["cert"] == KEYBANK


# ---------------------------------------------------------------- build: what it stated, what it refuses

def build_into(tmp_path, cache, args, series=None):
    """`peers build` into ``tmp_path``; (rc, workbook path, series dir)."""
    out, series = tmp_path / "p.xlsx", series or tmp_path / "s"
    rc = main(["peers", "build", str(out), "--cache", str(cache), "--series-dir", str(series)] + args)
    return rc, out, series


def with_value(args, flag, *values):
    """``args`` with ``flag``'s values replaced."""
    return without(args, flag) + [flag] + list(values)


def test_every_stated_setting_reaches_the_workbook(built, tmp_path, monkeypatch, capsys):
    """Each setting goes to build_peers_workbook as stated, none swapped,
    dropped or fixed. The values here differ from BUILD's, so a constant left
    in the code cannot pass by coinciding with the usual run's."""
    seen = {}
    real = peers_workbook.build_peers_workbook

    def record(*args, **kwargs):
        seen["args"], seen["kwargs"] = args, kwargs
        return real(*args, **kwargs)
    monkeypatch.setattr(peers_workbook, "build_peers_workbook", record)
    mergers = {"6672": ["2019-03-31"], "6560": ["2021-06-30"]}
    mfile = tmp_path / "m.json"
    mfile.write_text(json.dumps(mergers))
    args = list(BUILD)
    for flag, values in (("--products", ["Mortgage", "Credit card"]), ("--mergers", [str(mfile)]),
                         ("--extra-acquisitions", ["6384=2021Q4", "6384=2023Q1"]),
                         ("--jump", ["0.3"]), ("--min-book", ["750000"]), ("--exempt-self", ["no"]),
                         ("--pack", ["regionals"]), ("--min-banks", ["4"]), ("--rank-by", ["gross"]),
                         ("--last-n", ["16"]), ("--min-obs", ["10"]), ("--base-quarter", ["2018Q4"]),
                         ("--index-min-book", ["400000"]), ("--lagged-years", ["2020", "2024"]),
                         ("--lag-years", ["3"]), ("--normalisation-years", ["2018", "2024"]),
                         ("--mix-base-year", ["2018"])):
        args = with_value(args, flag, *values)
    rc, out, _ = build_into(tmp_path, built["cache"], args)
    assert rc == 0, capsys.readouterr().err
    pos, kw = seen["args"], seen["kwargs"]
    assert list(pos[3]) == ["Mortgage", "Credit card"]
    assert pos[4:10] == (0.3, 750000.0, "regionals", mergers, {"6384": ["2021Q4", "2023Q1"]}, "2018Q4")
    assert kw["exempt_self"] is False and kw["min_banks"] == 4 and kw["rank_by"] == "gross"
    assert kw["last_n"] == 16 and kw["min_obs"] == 10 and kw["index_min_book"] == 400000.0
    assert list(kw["lagged_years"]) == [2020, 2024] and kw["lag_years"] == 3
    assert list(kw["normalisation_years"]) == [2018, 2024] and kw["mix_base_year"] == 2018
    assert set(kw["industry"]) == {"Mortgage", "Credit card"}
    assert kw["industry"]["Mortgage"] == industry(json.loads((PEERS / "roster_2006.json").read_text()),
                                                  "Mortgage")
    assert out.exists() and not (tmp_path / "p.part.xlsx").exists()


def test_a_declared_acquisition_reaches_the_balances_tab(built):
    """Fifth Third's Dividend Finance (2022Q2) is listed as declared."""
    ba = load_workbook(built["out"])["Balances"]
    cells = [str(c.value) for row in ba.iter_rows() for c in row if c.value is not None]
    assert any("2022Q2 (declared)" in c for c in cells)


def test_the_regionals_pack_and_no_exemption(built, data, tmp_path, capsys):
    """--pack regionals: the composite is over the regionals only; --exempt-self
    no: KeyBank's own series keeps only quarters at or over the minimum."""
    args = with_value(with_value(BUILD, "--pack", "regionals"), "--exempt-self", "no")
    rc, out, series = build_into(tmp_path, built["cache"], with_value(args, "--products", "Credit card"))
    assert rc == 0, capsys.readouterr().err
    roster = R.load(ROOT / "config" / "peers.json")
    regionals = [b["cert"] for b in R.regionals(roster)]
    assert 0 < len(regionals) < len(R.peers(roster))
    books = {b["cert"]: bank_book(data, b["cert"], "Credit card", 0.25, 1_000_000) for b in roster}
    want = {quarter_end(r["quarter"]): r["net_rate"] for r in composite(books, regionals, 5)}
    notes, rows = read_csv(series / "credit-card_pack-composite_net.csv")
    assert rows and all(v == pytest.approx(want[d], abs=1e-12) for d, v in rows)
    assert any("%d regionals" % len(regionals) in n for n in notes)
    every = composite(books, [b["cert"] for b in R.peers(roster)], 5)
    assert any(abs(v - r["net_rate"]) > 1e-6 for (d, v), r in zip(rows, every[-len(rows):]))

    notes, rows = read_csv(series / "credit-card_keybank_net.csv")
    kept = [(quarter_end(r["quarter"]), r["net_rate"]) for r in books[KEYBANK]]
    assert [d for d, _ in rows] == [d for d, v in kept if v is not None][-len(rows):]
    assert len(rows) < 30                     # exempt, the card series runs 2018Q1 to 2026Q2 (34)
    assert not any("exempt" in n for n in notes)
    pk = load_workbook(out)["Pack"]
    include = {str(r[1].value): r[3].value for r in pk.iter_rows(min_row=1) if str(r[1].value).isdigit()}
    assert {c for c, v in include.items() if v is True} == set(regionals)


def test_a_series_that_ends_early_says_so(built, data, tmp_path, capsys):
    """KeyBank's card book jumps 60% in the last quarter, so 2026Q2 is not
    kept: the CSV ends at 2026Q1 and both the note and the console say the
    latest quarter is left out, so 2026Q1 is not read as the latest."""
    cache = tmp_path / "cache"
    cache.mkdir()
    for f in built["cache"].glob("q*.json"):
        (cache / f.name).write_bytes(f.read_bytes())
    last = json.loads((cache / "q20260630.json").read_text())
    for r in last:
        if str(r["CERT"]) == KEYBANK:
            r["LNCRCD"] = r["LNCRCD"] * 1.6
    (cache / "q20260630.json").write_text(json.dumps(last))
    capsys.readouterr()
    rc, _, series = build_into(tmp_path, cache, with_value(BUILD, "--products", "Credit card"))
    printed = capsys.readouterr().out
    assert rc == 0
    notes, rows = read_csv(series / "credit-card_keybank_net.csv")
    assert rows[-1][0] == "2026-03-31"
    assert any(n.startswith("Ends at 2026Q1") and "latest quarter, 2026Q2, has no value" in n for n in notes)
    assert "ends 2026Q1: 1 later quarter with no value" in printed


def test_a_series_with_no_value_removes_the_earlier_runs_csv(built, tmp_path, capsys):
    """An earlier run's CSV was built under other rules; it must not stay
    beside this run's files to be read as current."""
    args = with_value(BUILD, "--products", "Credit card")
    rc, _, series = build_into(tmp_path, built["cache"], args)
    assert rc == 0 and (series / "credit-card_pack-composite_net.csv").exists()
    capsys.readouterr()
    rc, _, _ = build_into(tmp_path, built["cache"], with_value(args, "--min-banks", "99"), series)
    printed = capsys.readouterr().out
    assert rc == 0
    assert not (series / "credit-card_pack-composite_net.csv").exists()
    assert not (series / "credit-card_pack-composite_gross.csv").exists()
    assert (series / "credit-card_keybank_net.csv").exists()
    assert "credit-card_pack-composite_net.csv has no value; the file from an earlier run is removed" in printed


def test_a_refusal_leaves_no_new_workbook(built, tmp_path, monkeypatch, capsys):
    """The series folder cannot be made (a file is in the way): refused before
    the workbook is built, and no workbook, finished or part-written, is left.
    A failure after the workbook is built leaves none either."""
    calls = []
    real = peers_workbook.build_peers_workbook
    monkeypatch.setattr(peers_workbook, "build_peers_workbook",
                        lambda *a, **k: calls.append(1) or real(*a, **k))
    blocker = tmp_path / "s"
    blocker.write_text("a file, not a folder")
    args = with_value(BUILD, "--products", "Credit card")
    rc, out, _ = build_into(tmp_path, built["cache"], args, blocker)
    assert rc == 2 and "REFUSED" in capsys.readouterr().err
    assert calls == [] and not out.exists() and not (tmp_path / "p.part.xlsx").exists()

    from threshold_engine.peers import books

    def broken(rows, path, note):
        raise OSError("disk full")
    monkeypatch.setattr(books, "write_series", broken)
    rc, out, series = build_into(tmp_path, built["cache"], args, tmp_path / "s2")
    assert rc == 2 and "disk full" in capsys.readouterr().err
    assert calls == [1] and not out.exists() and not (tmp_path / "p.part.xlsx").exists()
    assert not list(series.glob("*"))


@pytest.mark.parametrize("flag,value", [("--jump", "-1"), ("--jump", "nan"), ("--jump", "inf"),
                                        ("--min-book", "nan"), ("--min-book", "-5"),
                                        ("--index-min-book", "nan"), ("--index-min-book", "-1"),
                                        ("--min-banks", "0"), ("--last-n", "0"), ("--min-obs", "0"),
                                        ("--lag-years", "-1")])
def test_a_rule_out_of_range_is_refused_before_anything_is_written(built, tmp_path, capsys, flag, value):
    rc, out, series = build_into(tmp_path, built["cache"], with_value(BUILD, flag, value))
    err = capsys.readouterr().err
    assert rc == 2 and "REFUSED" in err and flag in err
    assert not out.exists() and not series.exists()


@pytest.mark.parametrize("item,says", [("99999=2022Q2", "not on the roster"),
                                       ("6672=1990Q2", "outside the quarters read (2006Q1 to 2026Q2)"),
                                       ("6672=2026Q3", "outside the quarters read"),
                                       ("=2022Q2", "CERT=YYYYQn")])
def test_a_declared_acquisition_that_cannot_apply_is_refused(built, tmp_path, capsys, item, says):
    rc, out, _ = build_into(tmp_path, built["cache"], with_value(BUILD, "--extra-acquisitions", item))
    err = capsys.readouterr().err
    assert rc == 2 and says in err
    assert not out.exists()


@pytest.mark.parametrize("content,says", [
    ('{"6672": null}', "must have a list of quarter-end dates"),
    ('{"6672": [20190331]}', "must have a list of quarter-end dates"),
    ('{"6672": "2019-03-31"}', "must have a list of quarter-end dates"),
    ('{"6672": ["2019-13-31"]}', "not a quarter-end date"),
    ('["6672"]', "must hold {cert: [quarter-end dates]}"),
    ('{"6672": [', "is not valid JSON"),
])
def test_a_bad_mergers_file_is_refused_not_a_traceback(built, tmp_path, capsys, content, says):
    mfile = tmp_path / "m.json"
    mfile.write_text(content)
    rc, out, _ = build_into(tmp_path, built["cache"], with_value(BUILD, "--mergers", str(mfile)))
    err = capsys.readouterr().err
    assert rc == 2 and "REFUSED" in err and says in err
    assert not out.exists()


def test_an_empty_cached_quarter_is_refused_not_read_as_zero(built, tmp_path, capsys):
    """A quarter cached before the FDIC published it holds no filers. Read as
    a quarter, it would put a made-up industry value into every series."""
    cache = tmp_path / "cache"
    cache.mkdir()
    for f in built["cache"].glob("q*.json"):
        (cache / f.name).write_bytes(f.read_bytes())
    (cache / "q20150630.json").write_text("[]")
    rc, out, series = build_into(tmp_path, cache, BUILD)
    err = capsys.readouterr().err
    assert rc == 2 and "q20150630.json holds no filers" in err
    assert not out.exists() and not series.exists()


# ---------------------------------------------------------------- build: industry over products summed

@pytest.fixture(scope="module")
def cache_1992(tmp_path_factory):
    """roster_1992.json (home equity, other consumer and auto, 1992-2026) as a cache."""
    d = json.loads((PEERS / "roster_1992.json").read_text())
    cache = tmp_path_factory.mktemp("cache_1992")
    for q, rows in d.items():
        (cache / ("q%s.json" % q)).write_text(json.dumps(rows), encoding="utf-8")
    return cache, d


def test_the_industry_with_products_summed_is_written(cache_1992, tmp_path, capsys):
    """Acceptance 3's second series, other consumer with auto, through the
    CLI: books.industry with products=[Auto], beside other consumer as filed."""
    cache, d = cache_1992
    args = with_value(with_value(with_value(with_value(
        BUILD, "--first", "1992Q1"), "--products", "Other consumer"),
        "--industry-combined", "Other consumer+Auto"), "--extra-acquisitions")
    rc, _, series = build_into(tmp_path, cache, args)
    assert rc == 0, capsys.readouterr().err
    for kind in ("gross", "net"):
        notes, rows = read_csv(series / ("other-consumer-auto_industry_%s.csv" % kind))
        want = {r["date"]: r[kind + "_rate"] for r in industry(d, "Other consumer", ["Auto"])}
        filed = {r["date"]: r[kind + "_rate"] for r in industry(d, "Other consumer")}
        assert len(rows) == len(want) and all(v == pytest.approx(want[dd], abs=1e-12) for dd, v in rows)
        assert any(abs(want[dd] - filed[dd]) > 1e-6 for dd in want if dd >= "2012-12-31")
        assert notes[0] == "Other consumer plus Auto, %s charge-off rate, trailing four quarters, %%." % kind
        assert any("Other consumer and Auto summed" in n for n in notes)
        _, plain = read_csv(series / ("other-consumer_industry_%s.csv" % kind))
        assert dict(plain) == pytest.approx(filed, abs=1e-12)


@pytest.mark.parametrize("item", ["Auto", "Auto+Auto", "Other consumer+Cars", "Other consumer+"])
def test_a_badly_formed_combination_is_refused(built, tmp_path, capsys, item):
    rc, out, _ = build_into(tmp_path, built["cache"], with_value(BUILD, "--industry-combined", item))
    assert rc == 2 and "--industry-combined takes two or more products" in capsys.readouterr().err
    assert not out.exists()


def test_a_combination_the_cache_was_not_pulled_for_is_refused(built, tmp_path, capsys):
    """roster_2006 has no auto fields: refused by name, never read as zero."""
    rc, out, _ = build_into(tmp_path, built["cache"],
                            with_value(BUILD, "--industry-combined", "Other consumer+Auto"))
    assert rc == 2 and "LNAUTO" in capsys.readouterr().err
    assert not out.exists()


# ---------------------------------------------------------------- pull: refusals

def test_pull_refuses_a_bad_mergers_date_before_fetching_anything(data, tmp_path, monkeypatch, capsys):
    fake = FakeFDIC(data)
    monkeypatch.setattr(fdic, "urllib_fetch", fake)
    rc = main(["peers", "pull", "--cache", str(tmp_path / "c"), "--first", "2025Q1", "--last", "2026Q2",
               "--products", "Credit card", "--mergers", "2005/10/01"])
    assert rc == 2 and "2005/10/01" in capsys.readouterr().err
    assert fake.urls == [] and not list(tmp_path.glob("c/q*.json"))


def test_pull_refuses_a_quarter_not_yet_published(data, tmp_path, monkeypatch, capsys):
    """The FDIC answers an unpublished quarter with no rows. Refused, and
    nothing cached, so the next pull asks again."""
    fake = FakeFDIC({"20260630": data["20260630"], "20260930": []})
    monkeypatch.setattr(fdic, "urllib_fetch", fake)
    cache = tmp_path / "c"
    rc = main(["peers", "pull", "--cache", str(cache), "--first", "2026Q2", "--last", "2026Q3",
               "--products", "Credit card"])
    assert rc == 2 and "not published" in capsys.readouterr().err
    assert not (cache / "q20260930.json").exists()


def test_an_incomplete_pull_is_refused_not_a_traceback(tmp_path, monkeypatch, capsys):
    """fdic raises RuntimeError for a pull that does not add up; the command
    says REFUSED with the reason."""
    def short(*a, **k):
        raise RuntimeError("the FDIC stated 10 rows but 9 arrived")
    monkeypatch.setattr(fdic, "pull", short)
    rc = main(["peers", "pull", "--cache", str(tmp_path), "--first", "2026Q2", "--last", "2026Q2",
               "--products", "Auto"])
    assert rc == 2 and "REFUSED: the FDIC stated 10 rows but 9 arrived" in capsys.readouterr().err
