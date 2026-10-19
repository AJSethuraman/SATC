"""peers.long_industry: the industry's charge-offs over a cache that starts
before 2006, as separate series, computed as books.industry computes them."""
import json
from pathlib import Path

import pytest

from threshold_engine.cli import main
from threshold_engine.peers.books import industry
from threshold_engine.workbook import read_notes, read_series

ROOT = Path(__file__).resolve().parents[1]
PEERS = Path(__file__).parent / "data" / "peers"
CHANGES = ROOT / "config" / "reporting-changes.json"


@pytest.fixture(scope="module")
def cache_1992(tmp_path_factory):
    d = json.loads((PEERS / "roster_1992.json").read_text())
    cache = tmp_path_factory.mktemp("cache_1992_long")
    for q, rows in d.items():
        (cache / ("q%s.json" % q)).write_text(json.dumps(rows), encoding="utf-8")
    return cache, d


def test_the_long_series_are_books_industry_over_the_whole_cache(cache_1992, tmp_path, capsys):
    cache, d = cache_1992
    out = tmp_path / "long"
    rc = main(["peers", "industry-long", str(out), "--cache", str(cache), "--first", "1992Q1", "--last", "2026Q2",
               "--products", "Other consumer", "--absorptions", str(PEERS / "absorptions_none.json"),
               "--reporting-changes", str(CHANGES)])
    assert rc == 0, capsys.readouterr().err
    for kind in ("gross", "net"):
        p = out / ("other-consumer_industry-from-1992_%s.csv" % kind)
        pts = read_series(p)
        want = {r["date"]: r[kind + "_rate"] for r in industry(d, "Other consumer")}
        got = {x.date: x.value for x in pts}
        assert got == pytest.approx({k: want[k] for k in got}, abs=1e-12)
        assert min(got) < "2006-01-01" and len(got) >= len(want) - 4
        notes = [t for _, t in read_notes(p)]
        assert notes[0] == "Other consumer, %s charge-off rate, trailing four quarters, %%." % kind
        assert any(n.startswith("Industry from 1992: every filer in the cache") for n in notes)
        assert any("before the merger record begins (2005-10-01), a repeated year to date stays in the sum" in n for n in notes)
        assert any(n.startswith("Reporting changes: reporting-changes.json, SHA-256 ") for n in notes)
    assert "Wrote" in capsys.readouterr().out


def test_a_missing_quarter_or_a_commercial_product_is_refused(cache_1992, tmp_path, capsys):
    cache, _ = cache_1992
    base = ["peers", "industry-long", str(tmp_path / "x"), "--cache", str(cache), "--absorptions",
            str(PEERS / "absorptions_none.json"), "--reporting-changes", str(CHANGES)]
    assert main(base + ["--first", "1990Q1", "--last", "2026Q2", "--products", "Other consumer"]) == 2
    assert "first missing 19900331" in capsys.readouterr().err
    assert main(base + ["--first", "1992Q1", "--last", "2026Q2", "--products", "C&I"]) == 2
    assert "consumer products" in capsys.readouterr().err
    assert not (tmp_path / "x").exists()
