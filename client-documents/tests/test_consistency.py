"""Do the documents in one package agree with each other?

`test_merge` proves a template fills. `test_registry` proves the templates and
the registry agree about field NAMES. Neither asks whether the resolved VALUES
tell one story, which is the question the firm asked on 26 August 2026 -- "show
me how you can tell it all goes together (so i can see consistency)" -- and the
question both real bugs lived in:

  * The engagement letter's scope said "Schedules A, C, and SE" while the
    estimate billed a $145 Rental schedule.
  * A fee estimate with an empty services table and "Total estimate $785".

Every test here breaks one join on purpose. A check nothing can fail is
decoration.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import consistency  # noqa: E402

SAMPLES = ROOT / "samples"


@pytest.fixture(scope="module")
def record():
    return cli.build_record(
        json.loads((SAMPLES / "tax-opening-package.json").read_text(encoding="utf-8")))


def _report(record):
    rendered = consistency.render_package(record, cli.DOCUMENTS, cli.TEMPLATE_DIR)
    return {c.name: c for c in consistency.report(record, rendered)}


def _fails(record, name):
    checks = _report(record)
    assert name in checks, f"the {name!r} check did not run at all"
    return checks[name]


# ── the demo package, which is the one anyone looks at ────────────────────

def test_the_demo_package_agrees_with_itself(record):
    checks = _report(record)
    assert checks, "no check ran, so nothing was compared"
    broken = [c.name for c in checks.values() if not c.ok]
    assert not broken, f"the sample package disagrees with itself: {broken}"


def test_every_check_reports_something_a_human_can_act_on(record):
    for check in _report(record).values():
        assert check.detail.strip(), f"{check.name} states no detail"


# ── each join, broken on purpose ──────────────────────────────────────────

def test_a_schedule_billed_outside_the_scope_is_caught(record):
    """The bug, reproduced. The estimate prices a rental; the letter's scope
    is narrowed to what it said before the firm caught it."""
    broken = dict(record, FederalReturns="Form 1040 with Schedules A, C, and SE")
    check = _fails(broken, "nothing is billed outside the scope")
    assert not check.ok
    assert "Schedule E" in check.detail


def test_a_scope_line_missing_from_one_document_is_caught(record):
    """`StateReturns` is on the letter and on the estimate. A value that
    reaches one and not the other is two documents describing one engagement
    differently, which is the thing the estimate's scope block exists to stop.
    """
    rendered = consistency.render_package(record, cli.DOCUMENTS, cli.TEMPLATE_DIR)
    rendered["fee-estimate"] = rendered["fee-estimate"].replace(
        record["StateReturns"], "somewhere else entirely")
    checks = {c.name: c for c in consistency.report(record, rendered)}
    check = checks["the letter and the estimate state one scope"]
    assert not check.ok and "StateReturns" in check.detail


def test_a_total_that_is_not_the_sum_of_the_lines_is_caught(record):
    broken = dict(record, EstimateTotal="$785.00")
    check = _fails(broken, "the total is the sum of the lines")
    assert not check.ok and "785" in check.detail


def test_a_reference_that_does_not_reach_every_document_is_caught(record):
    rendered = consistency.render_package(record, cli.DOCUMENTS, cli.TEMPLATE_DIR)
    rendered["onboarding-letter"] = rendered["onboarding-letter"].replace(
        record["EngagementRef"], "2027-9999")
    checks = {c.name: c for c in consistency.report(record, rendered)}
    check = checks["one engagement reference"]
    assert not check.ok and "onboarding-letter" in check.detail


def test_two_dates_on_one_package_are_caught(record):
    rendered = consistency.render_package(record, cli.DOCUMENTS, cli.TEMPLATE_DIR)
    rendered["fee-estimate"] = rendered["fee-estimate"].replace(
        record["LetterDate"], "February 9, 2027")
    checks = {c.name: c for c in consistency.report(record, rendered)}
    assert not checks["one letter date"].ok


def test_two_deadlines_on_one_package_are_caught(record):
    """The organizer, the letter and the onboarding letter all print it, and
    the FIELDS docs call a mismatch between them the organizer's most likely
    bug."""
    rendered = consistency.render_package(record, cli.DOCUMENTS, cli.TEMPLATE_DIR)
    rendered["onboarding-letter"] = rendered["onboarding-letter"].replace(
        record["MaterialsDeadline"], "April 1, 2027")
    checks = {c.name: c for c in consistency.report(record, rendered)}
    assert not checks["one materials deadline"].ok


# ── the reading of a schedule list ────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("Form 1040 with Schedules A, C, E, and SE", {"A", "C", "E", "SE"}),
    ("Form 1040 with Schedules A and C", {"A", "C"}),
    ("Schedule E, covering up to 3", {"E"}),
    # "and Schedule L" must not read the S of "Schedule" as a schedule.
    ("Schedule K-1 and Schedule L", {"K-1", "L"}),
    ("we will agree the schedule and the fee", set()),
    ("", set()),
])
def test_a_schedule_list_is_read_as_a_list(text, expected):
    assert consistency.schedules(text) == expected


# ── the command ───────────────────────────────────────────────────────────

def test_the_check_command_passes_on_the_demo_record(capsys):
    rc = cli.main(["check", str(SAMPLES / "tax-opening-package.json")])
    assert rc == 0
    out = capsys.readouterr().out
    assert "All" in out and "agree" in out


def test_the_check_command_fails_loudly_when_a_join_breaks(tmp_path, capsys):
    """A report that returns 0 on a broken package is worse than no report."""
    record = json.loads((SAMPLES / "tax-opening-package.json").read_text(encoding="utf-8"))
    record["FederalReturns"] = "Form 1040 with Schedules A, C, and SE"
    path = tmp_path / "narrowed.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    rc = cli.main(["check", str(path)])
    assert rc == 1
    assert "FAIL" in capsys.readouterr().out
