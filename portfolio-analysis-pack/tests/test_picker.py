"""The picker: designation at the desk by number, nothing edited by hand.

The firm, 22 Sep 2026: "I want no editing at the desk of Python or script
this is meant to be straight forward." `pack setup EXTRACT` asks one question
at a time, writes the question file from the answers, checks it and builds
the pack. These tests feed the answers a person would type.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from analysis_pack.cli import main
from analysis_pack.config import load_config
from analysis_pack.ingest import inspect_columns, read_table
from analysis_pack.picker import PROMPT_END, Picker

from conftest import ASOF


class Script:
    """Answers in order; records every prompt shown."""

    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.prompts: list[str] = []
        self.said: list[str] = []

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise AssertionError(f"the picker asked more than the script answers: {prompt!r}")
        return self.answers.pop(0)

    def say(self, text: str) -> None:
        self.said.append(text)


# the synthetic book's columns, in order: loan_id 1, origination_date 2,
# field_a 3, field_b 4, amount 5, category_1 6, category_2 7, code_1 8,
# outcome_date 9, flag_1 10, measure_a 11, measure_b 12
EFFECT_ANSWERS = [
    "",            # 1 loan number: the one column distinct on every row is proposed; Enter takes it
    "2",           # 2 origination date
    "3",           # 3 first rule column
    "4",           # 4 second
    "",            # 5 ratio
    "",            # 6 fires above 1
    "",            # 7 edges 0.5, 1, 2, 5
    "1",           # 8 outcome: a date column
    "9",           # 9 outcome date column
    "event",       # the word
    "",            # 24 months
    ASOF.isoformat(),
    "4, 5, 7",     # confounders: field_b (banded), amount (banded), category_2 (levels)
    "100000, 200000, 400000, 800000, 1600000",   # field_b edges
    "",            # amount edges: the quartiles proposed
    "",            # existing control: none
    "",            # nothing else known later
    "",            # no run date
]


def test_the_picker_writes_a_file_the_loader_accepts_from_numbers_alone(effect_book):
    table = read_table(effect_book / "loans.csv")
    s = Script(EFFECT_ANSWERS)
    p = Picker(table, inspect_columns(table), ask=s.ask, say=s.say)
    p.run()
    assert not s.answers, "every answer was used"
    text = p.to_yaml()
    raw = yaml.safe_load(text)
    assert raw["population"] == {"loan_id": "loan_id", "origination_date": "origination_date"}
    assert raw["rule"]["field_a"] == "field_a" and raw["rule"]["field_b"] == "field_b" and raw["rule"]["kind"] == "ratio"
    assert raw["rule"]["fires_when"] == {"op": ">", "value": 1.0} and raw["rule"]["buckets"] == [0.5, 1.0, 2.0, 5.0]
    assert raw["outcome"] == {"label": "event", "date_field": "outcome_date"}
    assert raw["fields"]["outcome_date"] == {"known": "later"} and raw["fields"]["field_a"] == {"known": "at_origination"}
    assert [c["name"] for c in raw["confounders"]] == ["field_b", "amount", "category_2"]
    assert raw["confounders"][0]["edges"] == [100000.0, 200000.0, 400000.0, 800000.0, 1600000.0]
    assert "edges" not in raw["confounders"][2], "a text column is taken level by level"
    amount_edges = raw["confounders"][1]["edges"]
    assert len(amount_edges) == 3 and amount_edges == sorted(amount_edges), "the quartiles were proposed and taken"
    assert raw["decompose_by"] == ["field_b", "amount", "category_2", "origination_year"]
    assert raw["existing_control"] == "none"
    # every column in use is declared, no others
    assert set(raw["fields"]) == {"loan_id", "origination_date", "field_a", "field_b", "amount", "category_2", "outcome_date"}
    assert "[CONFIRM" not in text
    # the column table was shown, numbered, before the first question
    assert any("The columns of loans.csv" in t for t in s.said) and any("  9  outcome_date" in t for t in s.said)
    # every prompt ends the same way, so a walk can find where the typing goes
    assert all(pr.endswith(PROMPT_END) for pr in s.prompts)
    out = effect_book / "picked.yaml"
    out.write_text(text, encoding="utf-8")
    cfg = load_config(out)
    assert cfg.name == "field_a_vs_field_b" and len(cfg.confounders) == 3


def test_a_wrong_answer_is_refused_and_asked_again(effect_book):
    table = read_table(effect_book / "loans.csv")
    answers = list(EFFECT_ANSWERS)
    # a text column for the first rule column, then a number beyond the list, then the right one
    answers[2:3] = ["6", "99", "3"]
    # the outcome date named as the second rule column: a leak, refused, then answered as intended
    s = Script(answers)
    p = Picker(table, inspect_columns(table), ask=s.ask, say=s.say)
    p.run()
    assert any("category_1 cannot be used here" in t and "needs a number column" in t for t in s.said)
    assert any("type the number beside the column" in t for t in s.said)
    assert p.answers["field_a"] == "field_a"


def test_a_column_known_later_cannot_sit_in_the_rule(effect_book):
    table = read_table(effect_book / "loans.csv")
    answers = list(EFFECT_ANSWERS)
    # says field_b (the second rule column) was known only later, then withdraws it
    answers[16:17] = ["4", ""]
    s = Script(answers)
    p = Picker(table, inspect_columns(table), ask=s.ask, say=s.say)
    p.run()
    assert any("field_b is the second rule column" in t and "leak" in t for t in s.said)
    assert p.answers["later"] == []


def test_the_flag_and_measure_outcomes_can_be_picked_too(effect_book):
    table = read_table(effect_book / "loans.csv")
    flag = list(EFFECT_ANSWERS)
    flag[7:10] = ["2", "10", "", "bad"]
    s = Script(flag)
    p = Picker(table, inspect_columns(table), ask=s.ask, say=s.say)
    p.run()
    raw = p.question()
    assert raw["outcome"] == {"label": "bad", "field": "flag_1", "op": "==", "value": 1.0, "basis": "windowed_by_bank"}
    assert raw["fields"]["flag_1"] == {"known": "later"}
    out = effect_book / "picked-flag.yaml"
    out.write_text(p.to_yaml(), encoding="utf-8")
    assert load_config(out).outcome.form == "flag"

    measure = list(EFFECT_ANSWERS)
    measure[7:10] = ["3", "11", "12", "", "1", "0.9", "high"]
    s = Script(measure)
    p = Picker(table, inspect_columns(table), ask=s.ask, say=s.say)
    p.run()
    raw = p.question()
    assert raw["outcome"]["measure"] == {"kind": "ratio", "field_a": "measure_a", "field_b": "measure_b"}
    assert raw["outcome"]["op"] == ">=" and raw["outcome"]["value"] == 0.9 and raw["outcome"]["basis"] == "snapshot_at_asof"
    assert raw["fields"]["measure_a"] == {"known": "later"} and raw["fields"]["measure_b"] == {"known": "later"}
    out = effect_book / "picked-measure.yaml"
    out.write_text(p.to_yaml(), encoding="utf-8")
    assert load_config(out).outcome.form == "snapshot"


def test_setup_at_the_command_line_writes_checks_and_builds(effect_book, tmp_path, monkeypatch, capsys):
    data = tmp_path / "extract.csv"
    shutil.copy(effect_book / "loans.csv", data)
    monkeypatch.setattr("sys.stdin", io.StringIO("\n".join(EFFECT_ANSWERS) + "\n"))
    rc = main(["setup", str(data), "--ask"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err[-1500:]
    assert (tmp_path / "question.yaml").exists()
    assert (tmp_path / "field_a_vs_field_b.xlsx").exists()
    assert "wrote" in captured.err and "from your answers" in captured.err
    assert "building" in captured.err and "step 4 field_b (edges): survives" in captured.err
    status = json.loads(captured.out)
    assert status["ok"] and status["seasoned"] == 29343
    # a second run finds the file and offers to reuse it
    monkeypatch.setattr("sys.stdin", io.StringIO("\n" + ASOF.isoformat() + "\n\n"))
    rc = main(["setup", str(data), "--ask"])
    captured = capsys.readouterr()
    assert rc == 0 and "already exists" in captured.err and "building" in captured.err


def test_the_bundle_runs_the_picker_and_needs_nothing_but_the_extract(effect_book, tmp_path, capsys):
    bundle = tmp_path / "build_pack.py"
    assert main(["bundle", str(effect_book / "config.yaml"), "-o", str(bundle)]) == 0
    capsys.readouterr()
    desk = tmp_path / "desk"
    desk.mkdir()
    shutil.copy(bundle, desk / bundle.name)
    shutil.copy(effect_book / "loans.csv", desk / "extract.csv")
    r = subprocess.run([sys.executable, bundle.name, "--setup", "extract.csv", "--ask"], cwd=desk, capture_output=True,
                       text=True, timeout=900, input="\n".join(EFFECT_ANSWERS) + "\n", env=dict(os.environ))
    assert r.returncode == 0, r.stderr[-2000:]
    assert "The columns of extract.csv" in r.stderr and "1. Which column numbers the loans" in r.stderr
    assert "wrote question.yaml from your answers" in r.stderr
    assert "then: open field_a_vs_field_b.xlsx in Excel" in r.stderr
    assert r.stdout.strip() == ""
    assert sorted(p.name for p in desk.iterdir()) == ["build_pack.py", "extract.csv", "field_a_vs_field_b.xlsx", "question.yaml"]
