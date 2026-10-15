"""The book file (book.py): everything a workbook is built from, in one file.

Every key is required and none has a default; problems are listed together;
relative paths are read from the book's own folder.
"""
import csv
import json
import shutil
from pathlib import Path

import pytest
from openpyxl import load_workbook

from conftest import DATA
from threshold_engine import book as BK

WORKBOOK = {"name": "N", "unit": "%", "direction": "higher_is_worse", "frequency": "quarterly", "smoothing": 1,
            "floor_at_zero": True, "moderate_halfwidth": 0.5, "low_step": 1.0, "high_z": 2.5, "on_the_line": "worse",
            "half_lives": [], "percentiles": [50], "horizon": 4, "min_history": 41}


def write_book(folder: Path, **over) -> Path:
    files = folder / "files"
    files.mkdir(parents=True, exist_ok=True)
    for name in ("cards_nco_ttm.csv", "home_equity_nco_ttm.csv", "mortgage_nco_ttm.csv"):
        shutil.copy(DATA / name, files / name)
    book = {"workbook": dict(WORKBOOK), "parts": ["Product", "Measure", "Source"],
            "series": [{"Product": "Card", "Measure": "Net", "Source": "Industry", "file": "files/cards_nco_ttm.csv"},
                       {"Product": "Card", "Measure": "Net", "Source": "Bank", "file": "files/home_equity_nco_ttm.csv"},
                       {"Product": "Mortgage", "Measure": "Net", "Source": "Industry",
                        "file": "files/mortgage_nco_ttm.csv"}],
            "not_in_book": [{"Product": "Mortgage", "Measure": "Net", "Source": "Bank", "why": "No file (a test)."}],
            "compare": ["Bank", "Industry"], "notes": ["A note."], "peers": None}
    book.update(over)
    p = folder / "book.json"
    p.write_text(json.dumps(book), encoding="utf-8")
    return p


def test_a_good_book_loads_with_paths_from_its_own_folder(tmp_path):
    bk = BK.load(write_book(tmp_path))
    assert [lbl for lbl, _ in bk["series"]] == ["Card - Net - Industry", "Card - Net - Bank",
                                                "Mortgage - Net - Industry"]
    assert bk["series"][0][1] == tmp_path.resolve() / "files" / "cards_nco_ttm.csv"
    assert bk["decide"]["compare"] == ("Bank", "Industry")
    assert bk["decide"]["absent"] == [{"parts": {"Product": "Mortgage", "Measure": "Net", "Source": "Bank"},
                                       "why": "No file (a test)."}]


def test_every_problem_is_listed_at_once(tmp_path):
    wb = dict(WORKBOOK)
    del wb["high_z"]
    wb["hight_z"] = 2.5
    p = write_book(tmp_path, workbook=wb, compare=["Bank", "Nobody"], notes="not a list")
    with pytest.raises(BK.BookError) as e:
        BK.load(p)
    msg = str(e.value)
    for said in ("missing 'high_z'", "'hight_z', which is not a key", "compare must be", "notes must be"):
        assert said in msg


def test_a_missing_top_key_is_refused_not_defaulted(tmp_path):
    p = write_book(tmp_path)
    raw = json.loads(p.read_text())
    del raw["not_in_book"]
    p.write_text(json.dumps(raw))
    with pytest.raises(BK.BookError, match="missing 'not_in_book'"):
        BK.load(p)


def test_series_may_be_a_csv_beside_the_book(tmp_path):
    p = write_book(tmp_path)
    raw = json.loads(p.read_text())
    with (tmp_path / "series.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["Product", "Measure", "Source", "file"])
        w.writeheader()
        w.writerows(raw["series"])
    raw["series"] = "series.csv"
    p.write_text(json.dumps(raw))
    bk = BK.load(p)
    assert len(bk["series"]) == 3 and all(path.exists() for _, path in bk["series"])


@pytest.mark.parametrize("row, said", [
    ({"Product": "Card", "Measure": "Net, TTM", "Source": "X", "file": "files/cards_nco_ttm.csv"}, "can't be used"),
    ({"Product": "Card", "Measure": "Net - TTM", "Source": "X", "file": "files/cards_nco_ttm.csv"}, "' - '"),
    ({"Product": "Card", "Measure": "Net", "Source": "Industry", "file": "files/cards_nco_ttm.csv"}, "listed twice"),
    ({"Product": "Card", "Measure": "Net", "Source": "Y", "file": "files/nope.csv"}, "does not exist"),
    ({"Product": "Card", "Measure": "Net", "file": "files/cards_nco_ttm.csv"}, "missing 'Source'"),
])
def test_a_bad_series_row_is_refused_by_name(tmp_path, row, said):
    p = write_book(tmp_path)
    raw = json.loads(p.read_text())
    raw["series"].append(row)
    p.write_text(json.dumps(raw))
    with pytest.raises(BK.BookError, match=said.replace("(", r"\(")):
        BK.load(p)


def test_peers_settings_must_be_complete(tmp_path):
    p = write_book(tmp_path, peers={"cache": "c", "roster": "r.json"})
    with pytest.raises(BK.BookError, match="peers is missing 'series_dir'"):
        BK.load(p)


def test_the_public_book_in_the_repository_loads():
    """books/consumer-public.json: 95 series, KeyBank's charge-offs explained,
    the peers build stated in full. Its series files are written by the peers
    build, so only the book itself is checked here."""
    p = Path(__file__).resolve().parents[1] / "books" / "consumer-public.json"
    bk = BK.load(p)
    assert len(bk["series"]) == 95
    assert {a["parts"]["Measure"] for a in bk["decide"]["absent"]} == {"Net charge-offs", "Gross charge-offs"}
    assert bk["peers"]["series_dir"] == p.parent / "out" / "series"
