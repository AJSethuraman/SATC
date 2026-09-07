"""The conformance check must pass on the spine -- and must be able to fail.

A guard nobody has watched fail is a guard nobody should trust. Each check here
is exercised twice: once against the real repository, and once against a planted
regression that must be caught AND named.
"""

from __future__ import annotations

import shutil

import pytest

import monitorbuild
from credit_suite import conformance
from credit_suite.engine import runtime
from credit_suite.parity import repo_root


@pytest.fixture(scope="module")
def spine_tabs():
    import openpyxl

    tabs = {}
    for name in sorted(conformance.MIGRATED_FOLDERS.values()):
        with monitorbuild.built_monitor(name, run_demo=False) as (workbook, _):
            wb = openpyxl.load_workbook(workbook, keep_vba=True, read_only=True)
            try:
                tabs[name] = list(wb.sheetnames)
            finally:
                wb.close()
    return tabs


# --------------------------------------------------------------------------
# it passes on the spine
# --------------------------------------------------------------------------

def test_the_spine_is_single_sourced():
    findings, pending, examined = conformance.check_single_sourced()
    assert examined["python files scanned"] > 100, "scanned almost nothing"
    assert examined["engine modules"] >= 10
    assert not findings, "\n".join(str(f) for f in findings)


def test_the_outstanding_copies_are_reported_not_hidden():
    """The four unmigrated monitors still carry copies. That is scheduled work,
    so it does not fail the spine -- but it must be visible, or the check has
    quietly stopped looking for the thing it exists to find."""
    _findings, pending, _examined = conformance.check_single_sourced()
    assert pending, "no outstanding copies reported at all -- did the scan stop?"
    folders = {str(f.subject).split("/")[0] for f in pending}
    assert folders <= set(conformance.UNMIGRATED_FOLDERS), folders
    assert all("M2" in f.detail for f in pending)


def test_a_migrated_folder_keeps_only_its_generated_bundle():
    root = repo_root()
    for folder in conformance.MIGRATED_FOLDERS:
        loose = [p.name for p in (root / folder).glob("*.py")
                 if not conformance.GENERATED.match(p.name)]
        assert not loose, "%s still carries source: %s" % (folder, loose)


def test_the_spine_tabs_match_the_contract(spine_tabs):
    findings, examined = conformance.check_tabs(spine_tabs)
    assert examined["monitors"] == 2
    assert examined["tabs"] > 15, "only %d tabs seen" % examined["tabs"]
    assert not findings, "\n".join(str(f) for f in findings)


def test_the_exit_codes_match_the_contract():
    findings, examined = conformance.check_exit_codes(runtime)
    assert examined["exit codes"] == 4
    assert not findings, "\n".join(str(f) for f in findings)


def test_every_migrated_runner_accepts_the_contract_flags():
    from credit_suite.sources.fdic import runner as fdic_runner

    findings, examined = conformance.check_cli({"fdic": fdic_runner.build_parser()})
    assert examined["flag checks"] == 3
    assert not findings, "\n".join(str(f) for f in findings)


# --------------------------------------------------------------------------
# it can fail: planted regressions
# --------------------------------------------------------------------------

def test_a_copied_engine_module_is_caught_and_named(tmp_path):
    """The regression this whole check exists for: someone copies a module back.

    Built as a miniature repository rather than by writing into the real one --
    a test that has to mutate the working tree to prove a point leaves a mess
    when it fails.
    """
    root = tmp_path
    engine = root / "credit-suite" / "src" / "credit_suite" / "engine"
    engine.mkdir(parents=True)
    (engine / "style.py").write_text("PALETTE = {'ink': '#101820'}\n",
                                     encoding="utf-8")
    (root / "TEMPLATE_CONTRACT.md").write_text("x", encoding="utf-8")

    monitor = root / "fdic-peer-monitor"
    monitor.mkdir()
    (monitor / "build_fdic_monitor.py").write_text("# generated\n", encoding="utf-8")

    findings, pending, _ = conformance.check_single_sourced(root)
    assert not findings, "a clean miniature repo should pass"

    # Plant the copy.
    shutil.copyfile(engine / "style.py", monitor / "keybank_style.py")
    findings, pending, _ = conformance.check_single_sourced(root)
    assert len(findings) == 1
    assert "fdic-peer-monitor/keybank_style.py" in findings[0].subject
    assert "engine/style.py" in findings[0].detail, "the offender is not named"


def test_a_renamed_copy_is_caught_too(tmp_path):
    """Renaming is the obvious way to make a copy look like not-a-copy, so the
    check is content-hashed rather than name-matched."""
    root = tmp_path
    engine = root / "credit-suite" / "src" / "credit_suite" / "engine"
    engine.mkdir(parents=True)
    (engine / "vba.py").write_text("def write_vba_project(mods):\n    return b''\n",
                                   encoding="utf-8")
    (root / "TEMPLATE_CONTRACT.md").write_text("x", encoding="utf-8")
    monitor = root / "fred-credit-risk-dashboard"
    monitor.mkdir()
    shutil.copyfile(engine / "vba.py", monitor / "totally_different_name.py")

    findings, _pending, _ = conformance.check_single_sourced(root)
    assert any("engine/vba.py" in f.detail for f in findings), \
        "a renamed copy slipped through"


def test_loose_source_in_a_migrated_folder_is_caught_even_if_not_a_copy(tmp_path):
    """A migrated monitor should carry no source at all. Something new and
    hand-written there is how the next divergence starts."""
    root = tmp_path
    (root / "credit-suite" / "src" / "credit_suite" / "engine").mkdir(parents=True)
    (root / "TEMPLATE_CONTRACT.md").write_text("x", encoding="utf-8")
    monitor = root / "fdic-peer-monitor"
    monitor.mkdir()
    (monitor / "helper.py").write_text("# brand new, not a copy\n", encoding="utf-8")

    findings, _pending, _ = conformance.check_single_sourced(root)
    assert len(findings) == 1
    assert "helper.py" in findings[0].subject
    assert "no Python source" in findings[0].detail


def test_a_missing_tab_is_caught_and_named():
    tabs = {"fdic": ["Dashboard_AssetQuality", "Watchlist", "Raw_FDIC",
                     "_config", "_code_py", "_code_vba"]}          # no _readme
    findings, _ = conformance.check_tabs(tabs)
    assert any("_readme" in f.detail for f in findings), findings


def test_an_unknown_tab_is_caught_and_named():
    """The Control Center drives what the contract names and nothing else."""
    tabs = {"fdic": ["Dashboard_X", "Watchlist", "Raw_FDIC", "_config",
                     "_code_py", "_code_vba", "_readme", "Scratch"]}
    findings, _ = conformance.check_tabs(tabs)
    assert any("Scratch" in f.detail for f in findings), findings


def test_a_missing_gated_lane_is_caught():
    tabs = {"fdic": ["Dashboard_X", "Raw_FDIC", "_config", "_code_py",
                     "_code_vba", "_readme"]}
    findings, _ = conformance.check_tabs(tabs)
    assert any("gated lane" in f.detail for f in findings), findings


def test_freds_grandfathered_watchlist_name_is_accepted():
    """Watchlist_Geo is grandfathered by the contract; the check must not
    'fix' it, because output parity pins the name."""
    tabs = {"fred": ["Dashboard_Consumer", "Watchlist_Geo", "Raw_Consumer",
                     "_config", "_code_py", "_code_vba", "_readme"]}
    findings, _ = conformance.check_tabs(tabs)
    assert not findings, findings


def test_a_cli_missing_a_contract_flag_is_caught_and_named():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--workbook")
    parser.add_argument("--demo", action="store_true")
    # --asof deliberately absent
    findings, _ = conformance.check_cli({"drifted": parser})
    assert len(findings) == 1
    assert "--asof" in findings[0].detail


def test_a_moved_exit_code_is_caught_and_named():
    class Drifted:
        EXIT_OK = 0
        EXIT_RUN_ERROR = 1
        EXIT_GATE_ERROR = 9           # moved
        EXIT_MISSING_SECRET = 3

    findings, _ = conformance.check_exit_codes(Drifted)
    assert len(findings) == 1
    assert "EXIT_GATE_ERROR" in findings[0].subject
    assert "expected 2" in findings[0].detail


def test_the_report_states_what_it_examined():
    """A green check that examined nothing looks exactly like a green check that
    examined everything."""
    empty = conformance.Report([], {})
    assert "NOTHING" in empty.describe()

    real = conformance.Report([], {"python files scanned": 289})
    assert "289 python files scanned" in real.describe()
    assert "conformance OK" in real.describe()
