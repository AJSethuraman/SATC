"""The command line. JSON status on stdout, a human summary on stderr.

    pack synth    --out DIR [--seed N] [--loans N] [--effect X] [--null] [--confounded]
    pack validate CONFIG --data DATA [--asof D] [--sheet NAME]
    pack build    CONFIG --data DATA --asof D [--run-date D] [-o OUT.xlsx] [--sheet NAME]

Exit codes: 0 OK · 1 error · 2 refused (the question file or the data).
The clock is never read: the as-of date is required and the run date
defaults to it.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import date
from pathlib import Path

from . import __version__
from .config import ConfigError, buildable, check_columns_present, load_config
from .ingest import read_table
from .population import PopulationError, build_population


def _say(msg: str) -> None:
    print(msg, file=sys.stderr)


def _emit(status: dict) -> None:
    print(json.dumps(status, indent=2, default=str))


def _date(s: str) -> date:
    return date.fromisoformat(s)


def cmd_synth(a: argparse.Namespace) -> int:
    from . import synth
    mode = "null" if a.null else ("confounded" if a.confounded else "effect")
    planted = synth.generate(a.out, seed=a.seed, loans=a.loans, effect=a.effect, mode=mode)
    _say(f"wrote {a.out}/loans.csv, config.yaml, planted.json ({mode}, seed {a.seed}, {a.loans:,} loans)")
    _emit({"ok": True, "out": str(a.out), **planted})
    return 0


def _load(a: argparse.Namespace):
    try:
        cfg = load_config(a.config)
    except ConfigError as exc:
        _say("the question file was refused:")
        for p in exc.problems:
            _say("  - " + p.replace("\n", "\n    "))
        _emit({"ok": False, "refused": "config", "problems": exc.problems})
        return None, None, 2
    table = read_table(a.data, sheet=a.sheet)
    missing = check_columns_present(cfg, table.columns)
    if missing:
        _say("the data was refused:")
        for p in missing:
            _say("  - " + p)
        _emit({"ok": False, "refused": "columns", "problems": missing, "columns_found": table.columns})
        return None, None, 2
    return cfg, table, 0


def _population(cfg, table, asof: date, out_dir: Path, name: str):
    try:
        return build_population(cfg, table.rows, asof), 0
    except PopulationError as exc:
        path = out_dir / f"hygiene-{name}.csv"
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["loan_id", "column", "value", "reason"])
            w.writerows(exc.rows)
        _say(f"refused: {exc}")
        _say(f"the offending rows are in {path}; clean the extract and run again")
        counts: dict[str, int] = {}
        for _, _, _, reason in exc.rows:
            counts[reason] = counts.get(reason, 0) + 1
        _emit({"ok": False, "refused": "hygiene", "counts": counts, "file": str(path)})
        return None, 2


def cmd_validate(a: argparse.Namespace) -> int:
    cfg, table, rc = _load(a)
    if rc:
        return rc
    why = buildable(cfg)
    if why:
        _say("valid, but: " + why)
    if a.asof:
        pop, rc = _population(cfg, table, _date(a.asof), Path(a.data).parent, cfg.name)
        if rc:
            return rc
        _say(f"ok: {len(table.rows):,} rows, {len(pop.loans):,} loans, {len(pop.seasoned):,} seasoned at {a.asof}")
        _emit({"ok": True, "rows": len(table.rows), "loans": len(pop.loans), "seasoned": len(pop.seasoned),
               "buildable": why is None, "note": why})
    else:
        _say(f"ok: question file and columns agree ({len(table.rows):,} rows). Add --asof to run the hygiene checks.")
        _emit({"ok": True, "rows": len(table.rows), "buildable": why is None, "note": why})
    return 0


def cmd_build(a: argparse.Namespace) -> int:
    from .workbook import build_pack
    t0 = time.perf_counter()
    cfg, table, rc = _load(a)
    if rc:
        return rc
    why = buildable(cfg)
    if why:
        _say("refused: " + why)
        _emit({"ok": False, "refused": "rule_type", "problems": [why]})
        return 2
    asof = _date(a.asof)
    run_date = _date(a.run_date) if a.run_date else asof
    out = Path(a.out) if a.out else Path(a.data).with_name(f"{cfg.name}.xlsx")
    t1 = time.perf_counter()
    pop, rc = _population(cfg, table, asof, out.parent, cfg.name)
    if rc:
        return rc
    t2 = time.perf_counter()
    blob, data, checks = build_pack(cfg, pop, table, run_date)
    t3 = time.perf_counter()
    out.write_bytes(blob)
    import hashlib
    digest = hashlib.sha256(blob).hexdigest()
    _say(f"wrote {out} ({len(blob):,} bytes, sha256 {digest[:16]}…)")
    _say(f"  read {t1 - t0:.1f}s · population {t2 - t1:.1f}s · workbook {t3 - t2:.1f}s")
    _say(f"  {data.facts.seasoned:,} seasoned loans, {data.facts.events:,} events, "
         f"{data.facts.unseasoned:,} unseasoned excluded; gradient reads: {data.gradient.word}")
    _say(f"  formula check: not run here (no engine); Excel verifies on open — {len(checks)} checks written to _check")
    _emit({"ok": True, "out": str(out), "sha256": digest, "seasoned": data.facts.seasoned,
           "events": data.facts.events, "unseasoned": data.facts.unseasoned, "gradient": data.gradient.word,
           "checks_written": len(checks), "formula_check": "not run here",
           "seconds": {"read": round(t1 - t0, 2), "population": round(t2 - t1, 2), "workbook": round(t3 - t2, 2)}})
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pack", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"pack {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("synth", help="write a made-up book with a known answer")
    s.add_argument("--out", required=True)
    s.add_argument("--seed", type=int, default=20260918)
    s.add_argument("--loans", type=int, default=40000)
    s.add_argument("--effect", type=float, default=2.0)
    s.add_argument("--null", action="store_true")
    s.add_argument("--confounded", action="store_true")
    s.set_defaults(fn=cmd_synth)

    v = sub.add_parser("validate", help="check the question file against the data; refuse with the line to add")
    v.add_argument("config"); v.add_argument("--data", required=True); v.add_argument("--asof")
    v.add_argument("--sheet")
    v.set_defaults(fn=cmd_validate)

    bld = sub.add_parser("build", help="build the pack")
    bld.add_argument("config"); bld.add_argument("--data", required=True); bld.add_argument("--asof", required=True)
    bld.add_argument("--run-date"); bld.add_argument("-o", "--out"); bld.add_argument("--sheet")
    bld.set_defaults(fn=cmd_build)

    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except (OSError, ValueError) as exc:
        _say(f"error: {exc}")
        _emit({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":   # pragma: no cover
    sys.exit(main())
