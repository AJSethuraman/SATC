"""The isolation guard refuses live paths, pins the environment, and bans the outside.

Anything that imports satc_system's app runs in a subprocess: `STATE` is built
at import time and the guard refuses a process where that already happened.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from season_sim import guard, paths

HOME = Path.home()


@pytest.mark.parametrize("live", [
    HOME / ".satc" / "data", HOME / "Documents" / "Main" / "SATC" / "x",
    HOME / "SATC" / "client-documents" / "engagements", Path("C:/Occam/books"),
    Path("C:/DRAKE25/DATA"), Path("C:/DRAKEDDM"), paths.REPO / "client-documents" / "engagements",
    paths.PROJECT / "runs",
])
def test_a_run_directory_on_a_live_or_repo_path_is_refused(live):
    assert guard.refuses(live, paths.REPO)


def test_the_default_run_directory_is_outside_the_worktree():
    run = guard.default_run_dir(42, "t")
    assert not guard.refuses(run, paths.REPO)
    assert len(str(run)) < 100, "the Windows path budget (satc_system/tests/conftest.py)"


def _child(code: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=os.pathsep.join([str(paths.PROJECT / "src"),
                                           os.environ.get("PYTHONPATH", "")]))
    env.update(env_extra or {})
    return subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(code)], env=env,
                          capture_output=True, text=True, timeout=300)


def test_the_environment_is_assigned_not_defaulted(tmp_path):
    run = tmp_path / "run"
    proc = _child(f"""
        import json, os
        from season_sim import guard, paths
        iso = guard.pin_environment(r"{run}", paths.REPO)
        print(json.dumps({{k: os.environ.get(k) for k in (
            "SATC_DATA_DIR", "SATC_ENGAGEMENTS", "SATC_ROLE", "SATC_OLLAMA",
            "SATC_SQUARE_TOKEN", "ANTHROPIC_API_KEY", "SATC_PRINCIPALS", "SATC_ALLOW_CLOUD")}}))
    """, {"SATC_DATA_DIR": str(tmp_path / "someone-elses-store"), "SATC_SQUARE_TOKEN": "tok",
          "ANTHROPIC_API_KEY": "key", "SATC_PRINCIPALS": "x", "SATC_ALLOW_CLOUD": "1",
          "SATC_OLLAMA": "1"})
    assert proc.returncode == 0, proc.stderr
    got = json.loads(proc.stdout.strip().splitlines()[-1])
    assert Path(got["SATC_DATA_DIR"]) == run / "satc_data"
    assert Path(got["SATC_ENGAGEMENTS"]) == run / "engagements"
    assert got["SATC_ROLE"] == "owner" and got["SATC_OLLAMA"] == "0"
    for gone in ("SATC_SQUARE_TOKEN", "ANTHROPIC_API_KEY", "SATC_PRINCIPALS", "SATC_ALLOW_CLOUD"):
        assert got[gone] is None, gone


def test_the_guard_refuses_a_process_that_imported_satc_first(tmp_path):
    proc = _child(f"""
        from season_sim import guard, paths
        paths.put_projects_on_path()
        import satc
        try:
            guard.pin_environment(r"{tmp_path / 'run'}", paths.REPO)
        except guard.SimRefused as exc:
            print("REFUSED", exc)
    """)
    assert "REFUSED" in proc.stdout, proc.stdout + proc.stderr


def test_sockets_square_and_outlook_are_banned(tmp_path):
    proc = _child(f"""
        from season_sim import guard, paths
        guard.pin_environment(r"{tmp_path / 'run'}", paths.REPO)
        paths.put_projects_on_path()
        from satc.app.state import STATE
        import cli, payments, square_setup, socket
        from satc.intake import email_draft
        print("SHADOW", paths.assert_no_shadowing())
        guard.install_bans()
        out = []
        for name, fn in [("socket", lambda: socket.socket()),
                         ("connect", lambda: socket.create_connection(("127.0.0.1", 9))),
                         ("square", lambda: payments.processor()),
                         ("keyring", lambda: square_setup.stored_token(False))]:
            try:
                fn(); out.append(name + ":ALLOWED")
            except guard.SimRefused:
                out.append(name + ":refused")
        out.append("outlook:" + str(email_draft.outlook_available()))
        print(" ".join(out))
        print("STORE", STATE.store.dir)
    """)
    assert proc.returncode == 0, proc.stderr
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("socket:"))
    assert line == "socket:refused connect:refused square:refused keyring:refused outlook:False"
    store = next(ln for ln in proc.stdout.splitlines() if ln.startswith("STORE"))
    assert str(tmp_path / "run" / "satc_data") in store
