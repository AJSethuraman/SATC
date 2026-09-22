"""Slice 8 (issue #368): the pure-ASCII bundle rebuilds the pack in an empty
directory with only openpyxl and PyYAML on the path, byte-identical."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from analysis_pack.bundle import make_bundle
from analysis_pack.cli import main


@pytest.fixture(scope="module")
def bundle(effect_book, tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("bundle") / "build_pack.py"
    assert main(["bundle", str(effect_book / "config.yaml"), "-o", str(out)]) == 0
    return out


def test_the_bundle_is_pure_ascii_with_no_nul_byte(bundle):
    raw = bundle.read_bytes()
    raw.decode("ascii")
    assert b"\x00" not in raw


def test_the_bundle_carries_the_package_and_the_question_file_but_never_the_data(bundle, effect_book):
    text = bundle.read_text(encoding="ascii")
    head = text.split("FILES")[0]
    assert "import formulas" not in head and "pytest" not in head
    files = [line.split(":")[0].strip().strip("'") for line in text.splitlines() if line.startswith("    'analysis_pack/") or line.startswith("    'question/")]
    assert "analysis_pack/workbook.py" in files and "question/config.yaml" in files
    # the made-up-book generator travels (a desk tests on a book with a known
    # answer, 21 Sep 2026); the test helpers, the render harness and any data do not
    assert "analysis_pack/synth.py" in files
    assert not any(f.endswith(".csv") or f.endswith("recalc.py") or f.endswith("render.py") for f in files)
    assert "loans.csv" not in text


def _isolated_libs(dest: Path) -> Path:
    """A folder holding exactly openpyxl (and its one dependency) and PyYAML,
    copied from wherever this interpreter found them."""
    libs = dest / "libs"
    libs.mkdir()
    for mod in ("openpyxl", "et_xmlfile", "yaml"):
        m = importlib.import_module(mod)
        src = Path(m.__file__).parent
        shutil.copytree(src, libs / mod)
    return libs


def test_the_bundle_rebuilds_the_pack_byte_identical_in_an_empty_directory(bundle, effect_book, effect_pack, tmp_path):
    work = tmp_path / "target"
    work.mkdir()
    libs = _isolated_libs(work)
    shutil.copy(bundle, work / bundle.name)
    shutil.copy(effect_book / "loans.csv", work / "loans.csv")
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(work), "PYTHONPATH": str(libs)}
    r = subprocess.run([sys.executable, "-S", bundle.name, "--data", "loans.csv", "--asof", "2026-06-30",
                        "--run-date", "2026-09-18", "-o", "target.xlsx", "--json"],
                       cwd=work, capture_output=True, text=True, timeout=900, env=env)
    assert r.returncode == 0, r.stderr[-2000:]
    built = (work / "target.xlsx").read_bytes()
    direct = hashlib.sha256(effect_pack["bytes"]).hexdigest()
    assert hashlib.sha256(built).hexdigest() == direct
    assert direct[:16] in r.stderr
    status = json.loads(r.stdout)
    assert status["formula_check"] == "not run here"
    # the bundle's own inspect works from the same script
    r2 = subprocess.run([sys.executable, "-S", bundle.name, "--inspect", "loans.csv"],
                        cwd=work, capture_output=True, text=True, timeout=300, env=env)
    assert r2.returncode == 0 and "origination_date" in r2.stderr


def test_a_file_backed_grouping_travels_with_the_bundle(tmp_path):
    examples = Path(__file__).resolve().parents[1] / "configs" / "examples"
    out = make_bundle(examples / "stated_vs_bureau_income_auto.yaml", tmp_path / "auto_bundle.py")
    text = out.read_text(encoding="ascii")
    assert "'question/regions.csv'" in text


def test_a_refused_question_file_is_not_bundled(effect_book, tmp_path, capsys):
    import yaml
    raw = yaml.safe_load((effect_book / "config.yaml").read_text())
    raw.pop("existing_control")
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False))
    rc = main(["bundle", str(p), "-o", str(tmp_path / "x.py")])
    out = capsys.readouterr()
    assert rc == 2 and not (tmp_path / "x.py").exists()
    assert "existing_control: none" in out.err
