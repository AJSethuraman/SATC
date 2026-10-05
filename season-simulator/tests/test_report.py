"""The report puts findings first, keeps observations apart, and says what it skipped.

Built from a hand-made run output rather than a season, so it runs in a blink
and checks the shape: every finding carries seed, date, fake client, call,
output and the cited rule; observations are never headed as failures; the
"did NOT cover" section is present; the HTML twin is written.
"""

from __future__ import annotations

import json

import pytest

from season_sim import report

FINDING = {
    "finding_id": "abc", "kind": "failure", "invariant": "B11",
    "invariant_name": "a client with nothing started for the year is invited",
    "rule": "interview_invite means a client with no engagement for the year.",
    "source": ["satc_system/src/satc/actions/propose.py:44"], "note": "", "seed": 5,
    "first_seen": "2027-01-15", "last_seen": "2027-02-01", "days": 3, "sim_client": "SIM-004",
    "subject": "SATC-004000", "subjects": 1,
    "call": {"door": "http", "target": "GET /today", "clock": "frozen@2027-01-15T14:00Z"},
    "output": "no interview_invite; the client has jobs only for [2025]",
    "expected_per_source": "'Nothing started for 2026'", "denominators": {}, "env": {},
    "repro": "python -m season_sim repro --seed 5 --until 2027-01-15 --client SIM-004 --check B11",
}
SUMMARY = {
    "seed": 5, "clients": 3, "billing_door": "satc", "days": 288, "days_read": 288,
    "window": ["2027-01-01", "2027-10-15"], "invariants": {"B11": {"examined": 9,
    "days_checked": 288, "days_with_subjects": 3, "findings": 1}},
    "checker_crashes": [], "door_calls": {"total": 10, "not_ok": {}},
    "clock_audit": [], "what_if_H3": {"ran": True, "sim": "SIM-001", "stage": "complete",
                                      "why": "Accepted by the IRS on Apr 15, 2027.",
                                      "is_accepted": True, "filing": {"ack_code": "a"}},
    "observations": {"working_year_before_2026": {"days": 3}}, "run_level": {"ok": True},
    "banned": ["socket.socket"], "shadowed_modules": ["requests.py"],
    "outcomes": {"SIM-004": {"archetype": "never_reengages", "delivered": ""}},
    "env": {"repo_sha": "deadbeef", "python": "3.12", "pythonhashseed": "0"},
}


@pytest.fixture
def run_out(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "findings.jsonl").write_text(json.dumps(FINDING) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(SUMMARY), encoding="utf-8")
    return out


def test_findings_come_first_and_carry_their_evidence(run_out):
    md = report.markdown(run_out)
    assert md.index("## Clear bugs") < md.index("## Observations") < md.index("did NOT cover")
    block = md[md.index("### B11"):md.index("## Needs the firm")]
    for piece in ("seed 5", "2027-01-15", "SIM-004", "GET /today", "no interview_invite",
                  "propose.py:44", "repro"):
        assert piece in block, piece


def test_observations_are_never_headed_as_failures(run_out):
    md = report.markdown(run_out)
    obs = md[md.index("## Observations"):md.index("## What the simulator did NOT cover")]
    assert "never failures" in obs
    assert "## Clear bugs" not in obs and "failure*" not in obs


def test_the_report_and_its_html_twin_are_written(run_out, tmp_path):
    path = report.write(run_out, tmp_path / "reports")
    assert path.name == "season-2027-seed-5.md"
    page = (tmp_path / "reports" / "season-2027-seed-5.html").read_text(encoding="utf-8")
    assert "<h2>Clear bugs" in page and "prefers-color-scheme: dark" in page


def test_a_report_may_not_be_written_elsewhere_in_the_worktree(run_out):
    from season_sim import paths
    with pytest.raises(SystemExit):
        report.write(run_out, paths.REPO / "client-documents" / "reports")
