"""The consolidation's headline claim: the migrated monitors did not move a number.

Slow by nature -- each case builds a workbook and recomputes every formula in it
with the ``formulas`` engine. That cost is the point: a cheaper check would be
comparing the runner's own arithmetic against itself, which proves the code
agrees with the code.
"""

from __future__ import annotations

import pytest

import monitorbuild
from credit_suite import parity


@pytest.mark.parametrize("name", sorted(parity.SPINE_BASELINES))
def test_the_monitor_still_matches_its_pre_consolidation_golden(name):
    spec = parity.SPINE_BASELINES[name]
    golden_path = parity.repo_root() / spec["demo_golden"]

    with monitorbuild.built_monitor(name) as (workbook, _stdout):
        current = parity.snapshot_workbook(workbook, source=spec["workbook"])

    golden = parity.read_golden(golden_path)
    diffs = parity.diff_snapshots(golden, current,
                                  ignore=parity.MIGRATION_IGNORE)

    # Report the denominator: a parity pass over nothing proves nothing.
    compared = len(set(golden["cells"]) | set(current["cells"]))
    assert compared > 20000, "only %d cells compared" % compared
    assert not diffs, "%s moved:\n%s" % (name, parity.describe(diffs))


def test_the_migrated_monitor_is_built_by_the_engine_not_by_a_copy():
    """Guards the guard: if the FDIC recipe silently fell back to the legacy
    folder, the parity test above would still pass while proving nothing about
    the engine."""
    assert monitorbuild.RECIPES["fdic"].get("engine") is True
    assert "folder" not in monitorbuild.RECIPES["fdic"]
    assert monitorbuild.RECIPES["fdic"]["layout"].startswith("credit_suite.")
    assert monitorbuild.RECIPES["fdic"]["runner"].startswith("credit_suite.")


def test_the_engine_build_lights_the_flags_the_golden_recorded():
    """A workbook of blanks would also 'match' if the golden were blank. It is
    not -- so assert the run itself reports the numbers the baseline did."""
    with monitorbuild.built_monitor("fdic") as (_workbook, stdout):
        import json
        status = json.loads(stdout)
    assert status["mode"] == "demo"
    assert status["banks_landed"] == 12
    assert status["alert_banks"] == 2 and status["watch_banks"] == 2
    assert status["alert_flags"] == 50 and status["watch_flags"] == 47
    assert status["stale_banks"] == 0
    assert status["watchlist_refusals"] == []
    assert status["errors"] == []
