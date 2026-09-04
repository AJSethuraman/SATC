"""Build a monitor into a scratch directory and hand back its workbook.

Shared by ``capture_baselines.py`` (which records what the monitors did before
consolidation) and ``check_parity.py`` (which asks whether they still do it).
Both need exactly the same thing -- a clean copy of a monitor, built and demo-run
at a fixed ``--asof`` -- and two copies of that would drift.

The build always happens in a temp directory, never in the repo, so a parity
check can never leave a half-built workbook behind for the next run to read.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from credit_suite import parity  # noqa: E402

#: How each monitor is built and run. ``build`` and ``run`` are argv lists
#: relative to the monitor folder; ``{workbook}`` and ``{asof}`` are filled in.
RECIPES: dict[str, dict[str, object]] = {
    # FDIC is migrated: built and run through the shared engine, not from a
    # per-monitor folder. `engine` marks that, and `built_monitor` takes the
    # in-process path for it.
    "fdic": {
        "engine": True,
        "workbook": "Bank_Peer_Monitor.xlsm",
        "layout": "credit_suite.sources.fdic.layout",
        "runner": "credit_suite.sources.fdic.runner",
        "macro_module": "PeerMonitor",
    },
    "fred": {
        "engine": True,
        "workbook": "FRED_Credit_Risk_Dashboard.xlsm",
        "layout": "credit_suite.sources.fred.layout",
        "runner": "credit_suite.sources.fred.runner",
        "macro_module": "FREDDashboard",
    },
}


class BuildFailed(RuntimeError):
    """A monitor's own build or run refused. The output is the finding."""


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    result = subprocess.run([sys.executable, *argv], cwd=cwd,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise BuildFailed(
            "exit %d from %s\n--- stdout ---\n%s\n--- stderr ---\n%s"
            % (result.returncode, " ".join(argv), result.stdout, result.stderr)
        )
    return result


@contextmanager
def built_monitor(name: str, root: Path | None = None,
                  run_demo: bool = True) -> Iterator[tuple[Path, str]]:
    """Yield ``(workbook_path, run_stdout)`` for a freshly built monitor.

    The scratch directory is removed on exit, so callers that want to keep the
    workbook must copy it out inside the ``with`` block.
    """
    root = root or parity.repo_root()
    recipe = RECIPES[name]
    spec = parity.SPINE_BASELINES[name]
    workbook_name = str(recipe["workbook"])

    if recipe.get("engine"):
        yield from _built_through_engine(name, recipe, spec, run_demo)
        return

    workdir = Path(tempfile.mkdtemp(prefix="credit-suite-build-"))
    try:
        folder = workdir / name
        shutil.copytree(root / str(recipe["folder"]), folder,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache",
                                                      "build", "tests"))
        (folder / workbook_name).unlink(missing_ok=True)

        _run([str(a) for a in recipe["build"]], folder)
        workbook = folder / workbook_name
        if not workbook.is_file():
            raise BuildFailed("%s: build produced no %s" % (name, workbook_name))

        stdout = ""
        if run_demo:
            argv = [str(a).format(workbook=workbook_name, asof=spec["asof"])
                    for a in recipe["run"]]
            stdout = _run(argv, folder).stdout
        yield workbook, stdout
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _built_through_engine(name: str, recipe: dict, spec: dict, run_demo: bool):
    """A migrated monitor: built and run in-process through the shared engine.

    No folder to copy and no subprocess -- the engine IS the build. The scratch
    directory still exists so a parity check never writes into the repo.
    """
    import importlib

    from credit_suite.engine import package

    layout = importlib.import_module(str(recipe["layout"]))
    runner = importlib.import_module(str(recipe["runner"]))

    workdir = Path(tempfile.mkdtemp(prefix="credit-suite-build-"))
    try:
        base = workdir / (Path(str(recipe["workbook"])).stem + "_base.xlsx")
        workbook = workdir / str(recipe["workbook"])
        layout.build(str(base))
        package.assemble(str(base), str(workbook),
                         str(Path(layout.HERE) / "macro.bas"),
                         str(recipe["macro_module"]))

        stdout = ""
        if run_demo:
            from datetime import date
            asof = date.fromisoformat(str(spec["asof"]))
            status = runner.run(str(workbook), demo=True, asof=asof)
            stdout = json.dumps({k: v for k, v in status.items()
                                 if k != "digest"})
        yield workbook, stdout
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
