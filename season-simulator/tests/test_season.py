"""A short season through the real doors: the mechanics CI holds (S22).

CI holds the MECHANICS and never the findings: `docs/SOFTWARE-TENETS.md:389-416`.
So nothing here asserts that a finding exists or that none do -- a test that
goes green when the product is broken, or red when somebody fixes it, is S25.
What is asserted:

  * the run-level guards held (no write outside the run dir, nothing in the
    worktree, the environment still pinned, no checker crashed);
  * the denominators are above a floor, so a check that examined nothing cannot
    pass for one that examined something (S2);
  * the same seed writes byte-identical findings and world files;
  * breaking a real function makes the invariant that guards it fire
    (principle 12), for three mutations.

Every season here runs in a worker subprocess, exactly as `python -m season_sim
run` does.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

from season_sim.__main__ import build_parser, launch_worker, repro

pytestmark = pytest.mark.season

SMOKE = dict(clients=12, days="checkpoints")
SEED = 42


@pytest.fixture(scope="session")
def baseline(tmp_path_factory):
    out = tmp_path_factory.mktemp("season") / "baseline"
    summary = launch_worker(SEED, out, label="t-base", **SMOKE)
    return out, summary


def test_the_run_level_guards_held(baseline):
    _out, s = baseline
    rl = s["run_level"]
    assert rl["worktree_unchanged"], rl.get("worktree_diff")
    assert rl["store_is_run_dir"] and rl["env_pinned_at_end"]
    assert rl["cd_default_store_untouched"] and rl["cd_out_untouched"]
    assert rl["banned_call_attempts"] == 0
    assert rl["days_simulator_copy_differed_from_route"] == {"today": 0, "work": 0,
                                                             "job_page": 0}
    assert s["checker_crashes"] == []
    assert set(s["banned"]) >= {"socket.socket", "payments.processor",
                                "email_draft.open_outlook_draft"}


# Checks that must have LOOKED at something in a 12-client smoke season. The
# floor is deliberately low: it is there to catch zero, not to pin a count.
FLOORS = ["A1", "A2", "A3", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B12", "C1", "C5",
          "D1", "D2", "D3", "E1", "E2", "E3", "E4", "F1", "F2", "F3", "G1", "G2", "G4", "K1"]


@pytest.mark.parametrize("code", FLOORS)
def test_each_core_check_examined_something(baseline, code):
    _out, s = baseline
    assert s["invariants"][code]["examined"] > 0, f"{code} examined nothing"


def test_every_day_was_read_and_every_client_acted(baseline):
    _out, s = baseline
    assert s["days_read"] >= 14 and s["clients"] == 12
    assert s["door_calls"]["total"] > 100
    assert any(o["delivered"] for o in s["outcomes"].values())


def test_the_same_seed_writes_byte_identical_findings(baseline, tmp_path):
    out, _ = baseline
    again = tmp_path / "again"
    launch_worker(SEED, again, label="t-again", **SMOKE)
    assert (again / "findings.jsonl").read_bytes() == (out / "findings.jsonl").read_bytes()
    assert (again / "world.json").read_bytes() == (out / "world.json").read_bytes()


def _findings(out: Path, code: str) -> list:
    return [json.loads(line) for line in (out / "findings.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip() and json.loads(line)["invariant"] == code]


@pytest.mark.parametrize("mutation,code", [
    ("deadline_shift", "A2"),
    ("drop_chase", "B6"),
    ("season_unsorted", "E2"),
])
def test_breaking_the_real_function_makes_its_invariant_fire(baseline, tmp_path, mutation, code):
    base_out, _ = baseline
    out = tmp_path / mutation
    s = launch_worker(SEED, out, mutation=mutation, label=f"t-{mutation}", **SMOKE)
    assert s["mutated"][0] == code
    before, after = _findings(base_out, code), _findings(out, code)
    assert len(after) > len(before), f"{mutation} broke {code}'s function and {code} said nothing"


def test_a_printed_repro_command_reproduces_its_finding(baseline, tmp_path):
    """The report prints a repro command under every finding. Run the printed
    command, as printed, and the same finding must come back for the same client
    with the same evidence. B11 first: a replay narrowed to one client once
    printed 'no finding' for it, because B11 depends on the whole practice.

    Asserts nothing about WHICH findings exist (S25): if the smoke season has no
    per-client finding at all, there is nothing to replay and the test says so."""
    out, _ = baseline
    rows = [json.loads(line) for line in (out / "findings.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    first: dict[str, dict] = {}
    for r in rows:
        if r["sim_client"].startswith("SIM-"):
            first.setdefault(r["invariant"], r)
    order = ["B11"] + sorted(c for c in first if c != "B11")
    chosen = [first[c] for c in order if c in first][:3]
    if not chosen:
        pytest.skip("the smoke season produced no per-client finding to replay")
    for r in chosen:
        argv = shlex.split(r["repro"])
        assert argv[:4] == ["python", "-B", "-m", "season_sim"], r["repro"]
        a = build_parser().parse_args(argv[4:])
        _s, got = repro(a.seed, a.until, client=a.client, check=a.check, clients=a.clients,
                        billing_door=a.billing_door, out=tmp_path / r["invariant"], keep=False)
        mine = [g for g in got if g["sim_client"] == r["sim_client"]]
        assert mine, f"`{r['repro']}` printed no finding for {r['sim_client']}"
        assert mine[0]["output"] == r["output"], (r["repro"], mine[0]["output"], r["output"])
