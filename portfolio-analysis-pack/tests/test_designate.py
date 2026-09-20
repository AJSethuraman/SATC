"""Designation at the desk (20 Sep 2026). The firm: "we design a tool that we
can put anything into and designate it to be something that the tool can work
with. The point is it isn't key specific." So `pack init` writes a question
file from any extract's own columns, the loader refuses one that is not yet
filled in and names every slot, and the bundle takes the filled file beside
it. Nothing about a column ever comes back to whoever built the tool."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from analysis_pack.cli import main
from analysis_pack.config import CONFIRM, ConfigError, load_config
from analysis_pack.ingest import read_table
from analysis_pack.population import build_population

from conftest import ASOF


def _init(book: Path, tmp_path: Path, capsys) -> tuple[Path, dict]:
    out = tmp_path / "question.yaml"
    rc = main(["init", str(book / "loans.csv"), "-o", str(out)])
    status = json.loads(capsys.readouterr().out)
    assert rc == 0 and status["ok"], status
    return out, status


def test_init_lists_every_column_of_the_extract_and_marks_every_slot_to_fill(effect_book, tmp_path, capsys):
    out, status = _init(effect_book, tmp_path, capsys)
    text = out.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    columns = read_table(effect_book / "loans.csv").columns
    assert list(raw["fields"].keys()) == columns, "every column of the extract, in the extract's order"
    assert status["columns"] == columns
    # the slots the person must choose are marked, and the tool chose none of them
    for slot in ("name", "existing_control"):
        assert raw[slot].startswith(CONFIRM), slot
    for slot in ("loan_id", "origination_date"):
        assert raw["population"][slot].startswith(CONFIRM), slot
    for slot in ("field_a", "field_b"):
        assert raw["rule"][slot].startswith(CONFIRM), slot
    for col in columns:
        assert raw["fields"][col]["known"].startswith(CONFIRM), col
    # eight slots of the question, plus one `known` per column
    assert status["markers"] == text.count(CONFIRM) == 8 + len(columns)
    # what inspect found travels as a comment beside each column, for the person choosing
    assert "reads as dates" in text
    assert "origination_date" in text and "e.g." in text


def test_a_skeleton_is_refused_naming_every_slot_still_to_fill(effect_book, tmp_path, capsys):
    out, status = _init(effect_book, tmp_path, capsys)
    try:
        load_config(out)
    except ConfigError as exc:
        problems = exc.problems
    else:
        raise AssertionError("a skeleton with markers was accepted")
    assert problems[0].endswith(f"{status['markers']} values still to fill in (written by `pack init`):")
    assert len(problems) == 1 + status["markers"]
    assert any(p.startswith("`population.loan_id` still reads") for p in problems)
    assert any(p.startswith("`fields.origination_date.known` still reads") for p in problems)
    rc = main(["validate", str(out), "--data", str(effect_book / "loans.csv")])
    refused = json.loads(capsys.readouterr().out)
    assert rc == 2 and refused["refused"] == "config"


def _fill(skeleton_path: Path, answers_path: Path) -> Path:
    """What the person at the desk does, done by hand here: replace each marker
    with an answer. The answers come from the synthetic book's own question
    file, so the filled skeleton asks the same question the fixture does."""
    raw = yaml.safe_load(skeleton_path.read_text(encoding="utf-8"))
    ans = yaml.safe_load(answers_path.read_text(encoding="utf-8"))
    raw["name"] = "designated_at_the_desk"
    raw["population"]["loan_id"] = ans["population"]["loan_id"]
    raw["population"]["origination_date"] = ans["population"]["origination_date"]
    outcome_col = ans["outcome"]["date_field"]
    used = set(ans["fields"].keys())
    raw["fields"] = {col: {"known": "later" if col == outcome_col else "at_origination"}
                     for col in raw["fields"] if col in used}
    raw["rule"]["field_a"] = ans["rule"]["field_a"]
    raw["rule"]["field_b"] = ans["rule"]["field_b"]
    raw["outcome"]["label"] = ans["outcome"]["label"]
    raw["outcome"]["date_field"] = outcome_col
    raw["existing_control"] = "none"
    filled = skeleton_path.with_name("filled.yaml")
    filled.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return filled


def test_a_filled_skeleton_validates_and_builds_with_no_code_change(effect_book, tmp_path, capsys):
    out, _ = _init(effect_book, tmp_path, capsys)
    filled = _fill(out, effect_book / "config.yaml")
    cfg = load_config(filled)
    assert cfg.name == "designated_at_the_desk" and cfg.rule.field_a == "field_a"
    pop = build_population(cfg, read_table(effect_book / "loans.csv").rows, ASOF)
    assert len(pop.seasoned) > 0
    rc = main(["validate", str(filled), "--data", str(effect_book / "loans.csv"), "--asof", ASOF.isoformat()])
    status = json.loads(capsys.readouterr().out)
    assert rc == 0 and status["ok"] and status["seasoned"] == len(pop.seasoned)


def test_init_is_deterministic_and_refuses_to_overwrite(effect_book, tmp_path, capsys):
    a, _ = _init(effect_book, tmp_path, capsys)
    b = tmp_path / "again.yaml"
    assert main(["init", str(effect_book / "loans.csv"), "-o", str(b)]) == 0
    capsys.readouterr()
    assert a.read_bytes() == b.read_bytes()
    rc = main(["init", str(effect_book / "loans.csv"), "-o", str(a)])
    status = json.loads(capsys.readouterr().out)
    assert rc == 1 and not status["ok"] and "already exists" in status["error"]


def test_the_bundle_writes_the_skeleton_and_builds_from_a_question_file_beside_it(effect_book, tmp_path, capsys):
    """The desk holds an extract the bundle's carried question file was never
    written for. `--init` writes the skeleton there; the filled file goes in
    with `--config`; the build never needs the carried one."""
    bundle = tmp_path / "build_pack.py"
    assert main(["bundle", str(effect_book / "config.yaml"), "-o", str(bundle)]) == 0
    capsys.readouterr()
    desk = tmp_path / "desk"
    desk.mkdir()
    shutil.copy(bundle, desk / bundle.name)
    shutil.copy(effect_book / "loans.csv", desk / "extract.csv")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (env.get("PYTHONPATH", ""),) if p)
    run = lambda *args: subprocess.run([sys.executable, bundle.name, *args], cwd=desk,  # noqa: E731
                                       capture_output=True, text=True, timeout=600, env=env)
    r = run("--init", "extract.csv")
    assert r.returncode == 0, r.stderr[-1500:]
    assert (desk / "question.yaml").exists() and "[CONFIRM:" in r.stderr
    # validating the unfilled skeleton beside the script is refused, naming the slots
    r = run("--validate", "extract.csv", "--config", "question.yaml")
    assert r.returncode == 2 and "still to fill in" in r.stderr, r.stderr[-1500:]
    filled = _fill(desk / "question.yaml", effect_book / "config.yaml")
    r = run("--validate", "extract.csv", "--asof", ASOF.isoformat(), "--config", filled.name)
    assert r.returncode == 0, r.stderr[-1500:]
    r = run("--data", "extract.csv", "--asof", ASOF.isoformat(), "--run-date", "2026-09-18",
            "--config", filled.name, "-o", "desk.xlsx")
    assert r.returncode == 0, r.stderr[-1500:]
    status = json.loads(r.stdout)
    built = (desk / "desk.xlsx").read_bytes()
    assert status["sha256"] == hashlib.sha256(built).hexdigest()
    assert status["sha256"][:16] in r.stderr
