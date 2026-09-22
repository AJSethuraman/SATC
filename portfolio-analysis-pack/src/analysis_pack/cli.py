"""The command line. JSON status on stdout, a human summary on stderr.

    pack inspect  DATA [--sheet NAME]
    pack init     DATA [-o question.yaml] [--sheet NAME]   # a question-file skeleton from the columns
    pack list     [DIR]                         # question files under DIR and whether each is accepted
    pack synth    --out DIR [--seed N] [--loans N] [--effect X] [--null] [--confounded]
    pack validate CONFIG --data DATA [--asof D] [--sheet NAME]
    pack suggest  CONFIG --data DATA --asof D [--field COL] [--sheet NAME]
    pack build    CONFIG --data DATA --asof D [--run-date D] [-o OUT.xlsx] [--sheet NAME]
    pack bundle   CONFIG [-o build_pack.py]

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
from .ingest import inspect_columns, read_table
from .population import AmbiguousDates, PopulationError, build_population


#: Set by the bundle to its own file name. The next-step line every command
#: prints is then spelled the way that script takes it, not the installed
#: tool's way (walk defect 3, 22 Sep 2026: a desk typed `pack validate`).
SCRIPT: str | None = None


def _say(msg: str) -> None:
    print(msg, file=sys.stderr)


def _next(kind: str, *, data: str, config: str, out: str | None = None, asof: str = "YYYY-MM-DD") -> str:
    """The next command, spelled for whichever front door is running."""
    if SCRIPT:
        if kind == "validate":
            return f"python {SCRIPT} --validate {data} --asof {asof} --config {config}"
        return f"python {SCRIPT} --data {data} --asof {asof} --config {config} -o {out}"
    if kind == "validate":
        return f"pack validate {config} --data {data} --asof {asof}"
    return f"pack build {config} --data {data} --asof {asof} -o {out}"


def _emit(status: dict) -> None:
    print(json.dumps(status, indent=2, default=str))


def _date(s: str) -> date:
    return date.fromisoformat(s)


def cmd_synth(a: argparse.Namespace) -> int:
    from . import synth
    mode = "null" if a.null else ("confounded" if a.confounded else "effect")
    planted = synth.generate(a.out, seed=a.seed, loans=a.loans, effect=a.effect, mode=mode)
    _say(f"wrote {a.out}/loans.csv, config.yaml, planted.json ({mode}, seed {a.seed}, {a.loans:,} loans)")
    _say("then: " + _next("build", data=f"{a.out}/loans.csv", config=f"{a.out}/config.yaml", out=f"{a.out}/pack.xlsx",
                          asof=str(planted.get("asof", "YYYY-MM-DD"))))
    _emit({"ok": True, "out": str(a.out), **planted})
    return 0


def cmd_inspect(a: argparse.Namespace) -> int:
    table = read_table(a.data, sheet=a.sheet)
    report = inspect_columns(table)
    _say(f"{table.path}: {len(table.rows):,} rows, {len(table.columns)} columns ({table.kind})")
    for e in report:
        blank = "n/a" if e["null_share"] is None else f"{e['null_share']:.1%}"   # no rows: nothing to share
        line = f"  {e['column']:<28} {e['kind']:<10} blank {blank}  distinct {e['distinct']:,}  e.g. {', '.join(e['samples'])}"
        _say(line)
        if "dates" in e:
            d = e["dates"]
            if d.get("also_integer"):
                _say(f"      all-digit values that also read as {d['resolved'] or 'dates'} dates; the build reads the column"
                     f" as dates where the question file names it as a date column")
            elif d["resolved"]:
                _say(f"      dates: every value fits {d['resolved']} — the pack will use it")
            elif d["ambiguous"]:
                readings = "; ".join(f"{pat} reads it as {plain}" for pat, plain in d["readings"])
                _say(f"      dates: {len(d['ambiguous'])} patterns fit every value ({readings}). "
                     f"Add population.date_format to say which.")
            elif d["typed"]:
                _say(f"      dates: {d['typed']:,} typed date cells; no pattern needed")
            else:
                _say(f"      dates: no pattern fits every value; best fits {d['fits']}")
    _emit({"ok": True, "path": table.path, "sha256": table.sha256, "rows": len(table.rows), "columns": report})
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
    except AmbiguousDates as exc:
        _say("refused: " + str(exc))
        _emit({"ok": False, "refused": "dates", "column": exc.detection.column,
               "candidates": list(exc.detection.ambiguous), "sample": exc.detection.sample,
               "readings": exc.detection.readings()})
        return None, 2
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


def cmd_init(a: argparse.Namespace) -> int:
    """Write a question-file skeleton from the extract's own columns, for the
    person at the desk to fill in. The firm, 20 Sep 2026: the tool is not
    specific to any bank; whoever holds the file designates its columns."""
    from .designate import count_markers, skeleton
    table = read_table(a.data, sheet=a.sheet)
    out = Path(a.out) if a.out else Path(a.data).parent / "question.yaml"
    if out.exists():
        _say(f"error: {out} already exists; pass -o to write the skeleton somewhere else")
        _emit({"ok": False, "error": f"{out} already exists"})
        return 1
    text = skeleton(table, inspect_columns(table))
    out.write_text(text, encoding="utf-8", newline="\n")
    n = count_markers(text)
    _say(f"wrote {out}: {len(table.columns)} columns listed, {n} values marked [CONFIRM: ...] for you to fill in")
    _say("then: fill in every [CONFIRM: ...] value, and " + _next("validate", data=str(a.data), config=str(out)))
    _emit({"ok": True, "path": str(out), "columns": table.columns, "markers": n})
    return 0


def cmd_list(a: argparse.Namespace) -> int:
    """PRD §6.16: the question files under a folder and whether each would be
    accepted, one line each (adversarial finding 12, 19 Sep 2026)."""
    root = Path(a.dir or "configs")
    paths = sorted(root.rglob("*.yaml")) if root.is_dir() else ([root] if root.is_file() else [])
    if not paths:
        _say(f"no question files under {root}")
    out = []
    for path in paths:
        try:
            cfg = load_config(path)
        except ConfigError as exc:
            first = exc.problems[0].splitlines()[0] if exc.problems else "refused"
            _say(f"  refused  {path}: {first}")
            out.append({"path": str(path), "ok": False, "problems": exc.problems})
            continue
        _say(f"  ok       {path}  ({cfg.name})")
        out.append({"path": str(path), "ok": True, "name": cfg.name})
    _emit({"ok": True, "configs": out})
    return 0


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
        note = why
        if not cfg.confounders:
            note = "no confounders listed: step 4 will have nothing to compare within"
            _say("note: " + note)
        _say("then: " + _next("build", data=str(a.data), config=str(a.config), asof=str(a.asof),
                              out=str(Path(a.data).with_name(f"{cfg.name}.xlsx"))))
        _emit({"ok": True, "rows": len(table.rows), "loans": len(pop.loans), "seasoned": len(pop.seasoned),
               "buildable": why is None, "note": note})
    else:
        _say(f"ok: question file and columns agree ({len(table.rows):,} rows). Add --asof to run the hygiene checks.")
        _emit({"ok": True, "rows": len(table.rows), "buildable": why is None, "note": why})
    return 0


def cmd_suggest(a: argparse.Namespace) -> int:
    from .suggest import render_text, suggest
    cfg, table, rc = _load(a)
    if rc:
        return rc
    pop, rc = _population(cfg, table, _date(a.asof), Path(a.data).parent, cfg.name)
    if rc:
        return rc
    if a.field and a.field not in table.columns:
        _say(f"refused: `{a.field}` is not a column of the extract; columns found: {', '.join(table.columns)}")
        _emit({"ok": False, "refused": "columns", "problems": [f"`{a.field}` is not a column of the extract"],
               "columns_found": table.columns})
        return 2
    fields = [a.field] if a.field else [c.field for c in cfg.confounders if c.schemes]
    if not fields:
        _say("nothing to suggest for: name a numeric column with --field, or declare a confounder with edges")
        _emit({"ok": False, "error": "no numeric field to suggest bands for"})
        return 1
    out = []
    for f in fields:
        try:
            s = suggest(pop, f)
        except (ValueError, KeyError) as exc:
            _say(f"{f}: {exc}")
            if a.field:
                # asked for by name and cannot be answered: a refusal, never a
                # green nothing (adversarial findings 13 and 14, 19 Sep 2026)
                _emit({"ok": False, "refused": "field", "field": f, "error": str(exc)})
                return 2
            continue
        _say(render_text(s))
        out.append({"field": s.field, "loans": s.loans, "events": s.events, "outcome": s.outcome_label,
                    "schemes": [{"name": sc.name, "edges": list(sc.edges), "labels": sc.labels, "loans": sc.loans,
                                 "events": sc.events, "thin": sc.thin()} for sc in s.schemes],
                    "outcome_cut": {"value": s.outcome_cut, "rates": list(s.outcome_cut_rates),
                                    "note": "information only; chosen on the outcome, not for step 4"}})
    _emit({"ok": True, "suggestions": out})
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
    run_date = _date(a.run_date) if a.run_date else None   # never guessed: the pack says "run date not given"
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
    model_s = sum(m.seconds for m in data.models)
    _say(f"  read {t1 - t0:.1f}s · population {t2 - t1:.1f}s · models {model_s:.1f}s · workbook {t3 - t2 - model_s:.1f}s")
    for facts, g in data.per_outcome:
        _say(f"  {facts.seasoned:,} seasoned loans, {facts.events:,} events ({g.outcome.label}), "
             f"{facts.unseasoned:,} unseasoned excluded; gradient reads: {g.word}")
        for st in data.strata:
            if st.outcome.key == g.outcome.key:
                _say(f"    step 4 {st.confounder} ({st.scheme}): {st.word}")
        if not cfg.confounders:
            _say("    step 4: nothing to compare within — the question file lists no confounders")
        for mr in data.models:
            if mr.outcome.key == g.outcome.key:
                for fit in (mr.m1, mr.m2):
                    fl = fit.flag()
                    if fit.estimable and fl:
                        _say(f"    step 6 {fit.label}: flag odds ratio {fl.odds_ratio:.2f} [{fl.lo:.2f}, {fl.hi:.2f}] "
                             f"on {fit.events:,} events over {fit.coefficients} coefficients, about {fit.epp:.0f} events per coefficient"
                             + (" (thin: the model wants at least ten)" if fit.warning else ""))
                    else:
                        _say(f"    step 6 {fit.label}: {fit.reason}")
    _say(f"  formula check: runs when Excel opens the file (this machine has no spreadsheet engine) — "
         f"{len(checks)} checks written to _check")
    if run_date is None:
        _say("  run date: not given, so the pack says so; pass --run-date YYYY-MM-DD to stamp it")
    _say(f"then: open {out} in Excel; the cover's last line should say every formula check agrees")
    _emit({"ok": True, "out": str(out), "sha256": digest, "seasoned": data.seasoned, "unseasoned": data.unseasoned,
           "outcomes": [{"label": g.outcome.label, "events": facts.events, "gradient": g.word,
                         "stratified": {f"{st.confounder}.{st.scheme}": st.word for st in data.strata
                                        if st.outcome.key == g.outcome.key}}
                        for facts, g in data.per_outcome],
           "gradient": data.per_outcome[0][1].word, "events": data.per_outcome[0][0].events,
           "date_formats": pop.date_formats,
           "models": [{"outcome": mr.outcome.label,
                       "m1": ({"flag_or": mr.m1.flag().odds_ratio, "lo": mr.m1.flag().lo, "hi": mr.m1.flag().hi,
                               "epp": mr.m1.epp, "warning": mr.m1.warning} if mr.m1.estimable and mr.m1.flag()
                              else {"reason": mr.m1.reason, "implicated": mr.m1.implicated}),
                       "m2": ({"flag_or": mr.m2.flag().odds_ratio, "lo": mr.m2.flag().lo, "hi": mr.m2.flag().hi,
                               "epp": mr.m2.epp, "warning": mr.m2.warning} if mr.m2.estimable and mr.m2.flag()
                              else {"reason": mr.m2.reason, "implicated": mr.m2.implicated}),
                       "tree_first_split": mr.tree.first_split, "seconds": round(mr.seconds, 2)}
                      for mr in data.models],
           "checks_written": len(checks), "formula_check": "not run here",
           "seconds": {"read": round(t1 - t0, 2), "population": round(t2 - t1, 2), "workbook": round(t3 - t2, 2)}})
    return 0


def cmd_bundle(a: argparse.Namespace) -> int:
    from .bundle import make_bundle
    try:
        load_config(a.config)
    except ConfigError as exc:
        _say("the question file was refused, so it was not bundled:")
        for p in exc.problems:
            _say("  - " + p.replace("\n", "\n    "))
        _emit({"ok": False, "refused": "config", "problems": exc.problems})
        return 2
    out = make_bundle(a.config, a.out)
    size = out.stat().st_size
    _say(f"wrote {out} ({size:,} bytes, pure ASCII). On the target: python {out.name} --data EXTRACT --asof YYYY-MM-DD")
    _emit({"ok": True, "out": str(out), "bytes": size})
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pack", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"pack {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    ins = sub.add_parser("inspect", help="list every column of an extract with what is in it")
    ins.add_argument("data"); ins.add_argument("--sheet")
    ins.set_defaults(fn=cmd_inspect)

    s = sub.add_parser("synth", help="write a made-up book with a known answer")
    s.add_argument("--out", required=True)
    s.add_argument("--seed", type=int, default=20260918)
    s.add_argument("--loans", type=int, default=40000)
    s.add_argument("--effect", type=float, default=2.0)
    s.add_argument("--null", action="store_true")
    s.add_argument("--confounded", action="store_true")
    s.set_defaults(fn=cmd_synth)

    ini = sub.add_parser("init", help="write a question-file skeleton from an extract's own columns, to fill in at the desk")
    ini.add_argument("data"); ini.add_argument("-o", "--out"); ini.add_argument("--sheet")
    ini.set_defaults(fn=cmd_init)

    ls = sub.add_parser("list", help="the question files under a folder (default: configs) and whether each would be accepted")
    ls.add_argument("dir", nargs="?")
    ls.set_defaults(fn=cmd_list)

    v = sub.add_parser("validate", help="check the question file against the data; refuse with the line to add")
    v.add_argument("config"); v.add_argument("--data", required=True); v.add_argument("--asof")
    v.add_argument("--sheet")
    v.set_defaults(fn=cmd_validate)

    sg = sub.add_parser("suggest", help="propose band cut points from the data, with counts")
    sg.add_argument("config"); sg.add_argument("--data", required=True); sg.add_argument("--asof", required=True)
    sg.add_argument("--field"); sg.add_argument("--sheet")
    sg.set_defaults(fn=cmd_suggest)

    bld = sub.add_parser("build", help="build the pack")
    bld.add_argument("config"); bld.add_argument("--data", required=True); bld.add_argument("--asof", required=True)
    bld.add_argument("--run-date"); bld.add_argument("-o", "--out"); bld.add_argument("--sheet")
    bld.set_defaults(fn=cmd_build)

    bu = sub.add_parser("bundle", help="write one pure-ASCII script that rebuilds the pack on a machine with only openpyxl and PyYAML")
    bu.add_argument("config"); bu.add_argument("-o", "--out")
    bu.set_defaults(fn=cmd_bundle)

    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except (OSError, ValueError) as exc:
        _say(f"error: {exc}")
        _emit({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":   # pragma: no cover
    sys.exit(main())
