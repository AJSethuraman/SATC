#!/usr/bin/env python3
"""Capture the M1 parity baselines from the CURRENT, pre-consolidation monitors.

This is a Slice-0 tool with a deliberately short life: it drives each legacy
monitor's own ``make_workbook.py`` + ``runner.py --demo`` to record what the
suite does *today*, before any engine is shared. Once FDIC and FRED are
migrated (issues #165/#166) their legacy modules are deleted and this tool
stops working -- by then the goldens it wrote are committed and the migration
is measured against them.

    python tools/capture_baselines.py            # both spine monitors
    python tools/capture_baselines.py fred       # just one

Each monitor yields two goldens:

* ``<name>-shipped.json`` -- the committed ``.xlsm`` exactly as it ships. It is
  an unpopulated template, so it pins the *shape*: formulas, config, labels,
  defined names.
* ``<name>-demo.json``    -- built fresh and run ``--demo --asof <fixed date>``.
  This is the one that pins values and statuses, because it has data in it.

The tool also rebuilds the workbook without running it and diffs that against
the shipped golden, which answers the question a baseline has to answer before
anyone trusts it: *is the committed ``.xlsm`` actually what today's code
produces?* A drift there is reported, not hidden.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from credit_suite import parity  # noqa: E402

#: How each legacy monitor is built and run today. Folder-relative argv.
LEGACY_RECIPES: dict[str, dict[str, object]] = {
    "fdic": {
        "folder": "fdic-peer-monitor",
        "build": ["make_workbook.py"],
        "run": ["runner.py", "--workbook", "{workbook}", "--demo", "--asof", "{asof}"],
    },
    "fred": {
        "folder": "fred-credit-risk-dashboard",
        "build": ["make_workbook.py"],
        "run": ["runner.py", "--workbook", "{workbook}", "--demo", "--asof", "{asof}"],
    },
}


def _run(argv: list[str], cwd: Path) -> None:
    result = subprocess.run([sys.executable, *argv], cwd=cwd,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            "FAILED (exit %d): %s\n--- stdout ---\n%s\n--- stderr ---\n%s"
            % (result.returncode, " ".join(argv), result.stdout, result.stderr)
        )


def capture(name: str, root: Path, keep: Path | None = None) -> None:
    spec = parity.SPINE_BASELINES[name]
    recipe = LEGACY_RECIPES[name]
    shipped = root / spec["workbook"]
    workbook_name = shipped.name

    print("== %s ==" % name)

    shipped_snapshot = parity.snapshot_workbook(shipped, source=spec["workbook"])
    parity.write_golden(root / spec["shipped_golden"], shipped_snapshot)
    print("  shipped: %d cells -> %s" % (len(shipped_snapshot["cells"]),
                                         spec["shipped_golden"]))

    workdir = Path(tempfile.mkdtemp(prefix="credit-suite-baseline-"))
    try:
        folder = workdir / name
        shutil.copytree(root / str(recipe["folder"]), folder)
        (folder / workbook_name).unlink(missing_ok=True)

        _run([str(a) for a in recipe["build"]], folder)
        built = folder / workbook_name
        if not built.is_file():
            raise SystemExit("%s: build produced no %s" % (name, workbook_name))

        # Is the committed .xlsm what today's code produces? Answer before
        # anyone leans on the baseline.
        rebuilt = parity.snapshot_workbook(built, source=spec["workbook"])
        drift = parity.diff_snapshots(shipped_snapshot, rebuilt)
        if drift:
            print("  WARNING: rebuild differs from the committed workbook")
            print("  " + parity.describe(drift, limit=10).replace("\n", "\n  "))
        else:
            print("  rebuild reproduces the committed workbook exactly")

        run_argv = [str(a).format(workbook=workbook_name, asof=spec["asof"])
                    for a in recipe["run"]]
        _run(run_argv, folder)

        demo = parity.snapshot_workbook(built, source=spec["workbook"])
        parity.write_golden(root / spec["demo_golden"], demo)
        print("  demo (--asof %s): %d cells -> %s"
              % (spec["asof"], len(demo["cells"]), spec["demo_golden"]))

        populated = sum(1 for payload in demo["cells"].values()
                        if len(payload) > 1 and payload[0] not in (None, ""))
        print("  %d formula cells resolve to a value" % populated)

        if keep is not None:
            keep.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(built, keep / workbook_name)
            print("  kept the demo workbook at %s" % (keep / workbook_name))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("monitors", nargs="*", choices=[*parity.SPINE_BASELINES, []],
                    help="default: every spine monitor")
    ap.add_argument("--keep-workbooks", metavar="DIR",
                    help="also copy each demo-run workbook here (for inspection)")
    args = ap.parse_args(argv)

    root = parity.repo_root()
    keep = Path(args.keep_workbooks) if args.keep_workbooks else None
    for name in (args.monitors or list(parity.SPINE_BASELINES)):
        capture(name, root, keep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
