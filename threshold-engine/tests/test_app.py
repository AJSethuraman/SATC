"""The one-file window (threshold_engine/app.py, tools/make_app.py): what it
writes into the folder picked, what stops it, and that the one file carries
everything it runs on."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from threshold_engine import app

ROOT = Path(__file__).resolve().parents[1]


def test_problems_name_what_stops_a_step(tmp_path):
    assert app.problems(str(tmp_path), "2026Q2", "") == []
    assert app.problems(str(tmp_path), "2026Q2", "", "A Name a@b.com") == []
    assert app.problems(str(tmp_path), "2026Q2", "", "no email here")[0].startswith("Type a name and a contact email")
    got = app.problems("", "2026-06", str(tmp_path / "missing.csv"))
    assert got == ["Choose a folder for the data and the workbook.",
                   "Type the latest quarter as YYYYQn, for example 2026Q2.",
                   "The internal file %s does not exist." % (tmp_path / "missing.csv")]
    for bad in ("2026Q5", "26Q2", "2026q2", " "):
        assert app.problems(str(tmp_path), bad, "")


def test_prepare_writes_the_book_with_the_folders_own_paths(tmp_path):
    path = app.prepare(tmp_path, "2026Q3", None, False)
    assert path == tmp_path / "Book" / "consumer-public.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    shipped = json.loads((ROOT / "books" / "consumer-public.json").read_text(encoding="utf-8"))
    cache = tmp_path / "FDIC data"
    assert cache.is_dir()
    assert raw["peers"]["cache"] == str(cache) and raw["peers"]["last"] == "2026Q3"
    assert raw["peers"]["mergers"] == str(cache / "mergers.json")
    assert raw["peers"]["absorptions"] == str(cache / "absorptions.json")
    assert raw["peers"]["roster"] == "peers.json" and raw["internal"] is None
    assert raw["loan_classes"] == {"file": "peer-loan-classes.json", "cache": str(tmp_path / "SEC filings")}
    assert raw["reporting_changes"] == "reporting-changes.json"
    assert (tmp_path / "Book" / "reporting-changes.json").read_bytes() == \
        (ROOT / "config" / "reporting-changes.json").read_bytes()
    # Every other setting is the book's own, unchanged.
    for k in shipped:
        if k not in ("peers", "internal", "loan_classes", "reporting_changes"):
            assert raw[k] == shipped[k], k
    for k in shipped["peers"]:
        if k not in ("cache", "mergers", "absorptions", "roster", "last"):
            assert raw["peers"][k] == shipped["peers"][k], k
    assert (tmp_path / "Book" / "peers.json").read_bytes() == (ROOT / "config" / "peers.json").read_bytes()
    assert (tmp_path / "Book" / "consumer-public-series.csv").read_bytes() == \
        (ROOT / "books" / "consumer-public-series.csv").read_bytes()


def test_prepare_names_the_internal_file_and_states_its_mapping(tmp_path):
    f = tmp_path / "internal.csv"
    f.write_text("quarter\n", encoding="utf-8")
    raw = json.loads(app.prepare(tmp_path / "w", "2026Q2", str(f), True).read_text(encoding="utf-8"))
    assert raw["internal"] == {"file": str(f.resolve()), "source": "KeyBank internal", "segments": True,
                               "measures": {"net-charge-off-rate": "Net charge-offs",
                                            "gross-charge-off-rate": "Gross charge-offs"},
                               "call_report_source": "KeyBank"}


def test_the_one_file_carries_the_package_the_book_and_openpyxl(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_app.py"), str(tmp_path)], check=True,
                   capture_output=True)
    target = tmp_path / "Consumer credit thresholds.pyzw"
    names = set(zipfile.ZipFile(target).namelist())
    assert "__main__.py" in names and "threshold_engine/app.py" in names
    assert {"threshold_engine/bundle/%s" % n for n, _ in app.BUNDLE} <= names
    assert "openpyxl/__init__.py" in names and "et_xmlfile/__init__.py" in names
    assert any(n.startswith("openpyxl-LICENCE") for n in names)
    assert not any("__pycache__" in n for n in names)
    # Without site-packages, the bundled openpyxl and book are the ones read.
    code = ("import sys; sys.path.insert(0, %r); import openpyxl, json; from threshold_engine import app; "
            "print(openpyxl.__file__); print(json.loads(app.bundled('consumer-public.json'))['peers']['last'])"
            % str(target))
    out = subprocess.run([sys.executable, "-I", "-S", "-c", code], check=True, capture_output=True,
                         text=True).stdout.split("\n")
    assert out[0].startswith(str(target)) and out[1] == \
        json.loads((ROOT / "books" / "consumer-public.json").read_text(encoding="utf-8"))["peers"]["last"]
