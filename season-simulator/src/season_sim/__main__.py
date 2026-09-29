"""`python -m season_sim ...` -- the launcher. It never imports satc itself.

    run      one season per seed, each in its own worker process
    repro    replay a seed up to a date -- EVERY client, because a finding can
             depend on the whole practice -- and print one client's findings
    mutants  check the checker: break a real function, confirm the invariant fires
    report   rebuild the Markdown/HTML report from a run's output

Each worker gets PYTHONHASHSEED=0 and PYTHONDONTWRITEBYTECODE=1. The worktree's
`git status --porcelain --ignored` is taken before and after every worker; a
difference is a run-level failure (the harness wrote inside the repository).

Run the launcher itself as `python -B -m season_sim`: `-B` stops the launcher
writing `season_sim/__pycache__` into the worktree (git-ignored, but a write all
the same). The package sets `sys.dont_write_bytecode` as soon as it is imported,
which covers every module but the package's own `__init__`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from season_sim import guard, paths

DEFAULT_OUT = Path(tempfile.gettempdir()) / "satc-sim" / "out"
REPORTS = paths.PROJECT / "reports"


def _git(*args) -> str:
    try:
        return subprocess.run(["git", "-C", str(paths.REPO), *args], capture_output=True,
                              text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return "(git unavailable)"


def _outside(path: Path, what: str) -> Path:
    why = guard.refuses(Path(path), paths.REPO)
    if why:
        raise SystemExit(f"refusing {what}: {why}")
    return Path(path)


def launch_worker(seed: int, out: Path, *, clients=None, days="all", until=None, mutation="",
                  only=None, checks=None, keep=False, billing_door=None, label="",
                  pages=True) -> dict:
    run_dir = _outside(guard.default_run_dir(seed, label or "w"), "the run dir")
    if run_dir.exists():
        # The name carries this launcher's pid, so an existing one is a leftover
        # (a --keep run, or a crash) -- never another session's live store, and
        # never deleted on a guess.
        raise SystemExit(f"refusing to reuse {run_dir}: it already exists. Delete it "
                         f"if it is a leftover of your own.")
    out = _outside(out, "--out")
    out.mkdir(parents=True, exist_ok=True)
    before = _git("status", "--porcelain", "--ignored")
    sha = _git("rev-parse", "--short=8", "HEAD").strip()
    cmd = [sys.executable, "-B", "-m", "season_sim", "_worker", "--seed", str(seed),
           "--run-dir", str(run_dir), "--out", str(out), "--days", days, "--sha", sha]
    if clients:
        cmd += ["--clients", str(clients)]
    if until:
        cmd += ["--until", str(until)]
    if mutation:
        cmd += ["--mutation", mutation]
    if only:
        cmd += ["--only", ",".join(sorted(only))]
    if checks:
        cmd += ["--checks", ",".join(sorted(checks))]
    if billing_door:
        cmd += ["--billing-door", billing_door]
    if not pages:
        cmd += ["--no-pages"]
    env = dict(os.environ, PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=os.pathsep.join([str(paths.PROJECT / "src"),
                                           os.environ.get("PYTHONPATH", "")]))
    proc = subprocess.run(cmd, env=env, cwd=str(run_dir.parent), capture_output=True, text=True)
    after = _git("status", "--porcelain", "--ignored")
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout[-4000:] + proc.stderr[-8000:])
        raise SystemExit(f"worker for seed {seed} failed (exit {proc.returncode})")
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["run_level"]["worktree_unchanged"] = before == after
    if before != after:
        summary["run_level"]["worktree_diff"] = sorted(set(after.splitlines())
                                                       ^ set(before.splitlines()))[:20]
    summary["run_dir_kept"] = str(run_dir) if keep else ""
    summary_path.write_text(json.dumps(summary, indent=1, sort_keys=True, default=str),
                            encoding="utf-8")
    if not keep:
        shutil.rmtree(run_dir, ignore_errors=True)
    return summary


def cmd_worker(a) -> int:
    from season_sim.run import Season
    s = Season(seed=a.seed, run_dir=Path(a.run_dir), out_dir=Path(a.out), clients=a.clients,
               until=date.fromisoformat(a.until) if a.until else None, days_mode=a.days,
               mutation=a.mutation or "", repo_sha=a.sha,
               only_clients=set(a.only.split(",")) if a.only else None,
               checks=set(a.checks.split(",")) if a.checks else None,
               billing_door=a.billing_door, pages=not a.no_pages)
    s.run()
    return 0


def cmd_run(a) -> int:
    from season_sim import report
    for seed in a.seed:
        out = Path(a.out) / f"seed-{seed}" if a.out else DEFAULT_OUT / f"seed-{seed}"
        summary = launch_worker(seed, out, clients=a.clients, days=a.days, until=a.until,
                                keep=a.keep, billing_door=a.billing_door, label="run")
        print(f"seed {seed}: {summary['clients']} clients, {summary['days_read']} days read, "
              f"{sum(v['findings'] for v in summary['invariants'].values())} findings -> {out}")
        if a.report:
            md = report.write(out, Path(a.report_dir) if a.report_dir else REPORTS)
            print(f"  report: {md}")
    return 0


def repro(seed: int, until: str, *, client: str = "", check: str = "", clients=None,
          billing_door=None, out: Path | None = None,
          keep: bool = True) -> tuple[dict, list[dict]]:
    """Replay the WHOLE world to `until`, the owner acting every weekday exactly as
    in the season, read only that one day, and keep one client's findings.

    The whole world, not the one client: a check like B11 depends on the practice
    (Today's working year moves only once SOME client has a 2026 request), so a
    replay narrowed to one client answers a different question. Reading only the
    last day is safe because reads write nothing (B5 holds every day)."""
    out = out or DEFAULT_OUT / f"repro-{seed}-{client or 'all'}-{until}-{os.getpid()}"
    summary = launch_worker(seed, out, until=until, days="last",
                            checks={check} if check else None, keep=keep,
                            billing_door=billing_door, label=f"rp{check}", clients=clients)
    rows = [json.loads(line) for line in (out / "findings.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    rows = [r for r in rows if (not check or r["invariant"] == check)
            and (not client or r["sim_client"] in (client, "-"))]
    return summary, rows


def cmd_repro(a) -> int:
    summary, rows = repro(a.seed, a.until, client=a.client or "", check=a.check or "",
                          clients=a.clients, billing_door=a.billing_door)
    print(f"replayed seed {a.seed} to {a.until} ({summary['clients']} clients, all of "
          f"them; read on {a.until} only); run dir kept at {summary['run_dir_kept']}")
    for r in rows:
        print(f"\n[{r['kind']}] {r['invariant']} {r['sim_client']} first {r['first_seen']}")
        print(f"  call:     {json.dumps(r['call'])}")
        print(f"  output:   {r['output']}")
        print(f"  expected: {r['expected_per_source']}")
        print(f"  source:   {', '.join(r['source'])}")
    if not rows:
        print("no finding for that check and client on that replay")
    return 0


def cmd_mutants(a) -> int:
    from season_sim.mutations import MUTATIONS
    names = a.names.split(",") if a.names else sorted(MUTATIONS)
    base_out = DEFAULT_OUT / f"mutants-{a.seed}"
    base = launch_worker(a.seed, base_out / "baseline", clients=a.clients, days=a.days,
                         label="mut-base", until=a.until)
    results = []
    for name in names:
        inv, what, _ = MUTATIONS[name]
        s = launch_worker(a.seed, base_out / name, clients=a.clients, days=a.days,
                          mutation=name, label=f"mut-{name}", until=a.until)
        before = base["invariants"].get(inv, {}).get("findings", 0)
        after = s["invariants"].get(inv, {}).get("findings", 0)
        base_rows = _rows(base_out / "baseline", inv)
        mut_rows = _rows(base_out / name, inv)
        caught = mut_rows != base_rows and len(mut_rows) >= len(base_rows) and after > 0
        results.append({"mutation": name, "breaks": what, "invariant": inv,
                        "baseline_findings": before, "mutant_findings": after,
                        "caught": caught,
                        "first_new": next((r for r in mut_rows if r not in base_rows), None)})
        print(f"{name:20} {inv:4} baseline {before:3} mutant {after:3}  "
              f"{'CAUGHT' if caught else 'NOT CAUGHT'}  ({what})")
    (base_out / "mutants.json").write_text(json.dumps(results, indent=1, default=str),
                                           encoding="utf-8")
    missed = [r for r in results if not r["caught"]]
    return 1 if missed else 0


def _rows(out: Path, inv: str) -> list:
    rows = []
    for line in (out / "findings.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r["invariant"] == inv:
                rows.append((r["sim_client"], r["first_seen"], r["days"], r["output"]))
    return rows


def cmd_report(a) -> int:
    from season_sim import report
    print(report.write(Path(a.input), Path(a.report_dir) if a.report_dir else REPORTS))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="season_sim")
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("_worker")
    w.add_argument("--seed", type=int, required=True)
    w.add_argument("--run-dir", required=True)
    w.add_argument("--out", required=True)
    w.add_argument("--clients", type=int)
    w.add_argument("--days", default="all", choices=["all", "checkpoints", "last"])
    w.add_argument("--until")
    w.add_argument("--mutation")
    w.add_argument("--only")
    w.add_argument("--checks")
    w.add_argument("--sha", default="")
    w.add_argument("--billing-door", choices=["satc", "client_documents"])
    w.add_argument("--no-pages", action="store_true")
    w.set_defaults(fn=cmd_worker)

    r = sub.add_parser("run", help="simulate the season for one or more seeds")
    r.add_argument("--seed", type=int, nargs="+", default=[42])
    r.add_argument("--clients", type=int)
    r.add_argument("--days", default="all", choices=["all", "checkpoints"])
    r.add_argument("--until")
    r.add_argument("--out", help=f"default {DEFAULT_OUT}; refused inside the worktree")
    r.add_argument("--keep", action="store_true", help="keep the run directory for repro")
    r.add_argument("--billing-door", choices=["satc", "client_documents"])
    r.add_argument("--report", action="store_true", help="write the Markdown/HTML report")
    r.add_argument("--report-dir", help=f"default {REPORTS}")
    r.set_defaults(fn=cmd_run)

    rp = sub.add_parser("repro", help="replay one client up to a date")
    rp.add_argument("--seed", type=int, required=True)
    rp.add_argument("--until", required=True)
    rp.add_argument("--client")
    rp.add_argument("--check")
    rp.add_argument("--clients", type=int)
    rp.add_argument("--billing-door", choices=["satc", "client_documents"])
    rp.set_defaults(fn=cmd_repro)

    m = sub.add_parser("mutants", help="break a real function; the invariant must fire")
    m.add_argument("--seed", type=int, default=42)
    m.add_argument("--clients", type=int, default=16)
    m.add_argument("--days", default="checkpoints", choices=["all", "checkpoints"])
    m.add_argument("--until")
    m.add_argument("--names")
    m.set_defaults(fn=cmd_mutants)

    rep = sub.add_parser("report", help="rebuild the report from a run's output")
    rep.add_argument("--input", required=True)
    rep.add_argument("--report-dir")
    rep.set_defaults(fn=cmd_report)

    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
