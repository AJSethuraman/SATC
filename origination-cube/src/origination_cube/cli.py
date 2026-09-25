"""`cube` - the command line.

  cube inspect  EXTRACT                     every column: kind, blanks, distinct, samples
  cube init     EXTRACT -o CUBE.yaml        what every column is, written as a cube file to confirm
  cube validate CUBE.yaml --data EXTRACT    refuse or accept, and say why
  cube run      CUBE.yaml --data EXTRACT    build the cube and print it
  cube synth    --out DIR                   a synthetic book with a known answer
  cube control  --out FILE.xlsx             the Control tab, on the recommended options
  cube control  --read FILE.xlsx            the settings in use, or what is wrong with them

Every warning is printed to the screen, never to a log nobody opens
(finding 7: the VBA sent them to Debug.Print).
"""

from __future__ import annotations

import argparse
import sys
import time

from . import config as cfgmod
from . import engine, synth
from .ingest import inspect_columns, read_table


def _pct(v):
    return "" if v is None else f"{v * 100:.2f}%"


def _x(v):
    return "" if v is None else f"{v:.2f}x"


def _n(v):
    return "" if v is None else f"{v:,.0f}"


def _p(v):
    if v is None:
        return "n/a"
    return "<0.0001" if v < 0.0001 else f"{v:.4f}"


def report(res: engine.Result, top: int = 5) -> str:
    out = []
    cfg = res.config
    out.append(f"Cube: {cfg.name}   ({res.source}, {res.rows:,} rows)")
    out.append(f"Tie-out: {res.tie_outs} of {res.tie_outs} checks agree "
               f"(every grid adds up to the book; medians are not added up, by design)")
    if res.warnings:
        out.append("")
        out.append("WARNINGS")
        out += [f"  - {w}" for w in res.warnings]
    out.append("")
    out.append("Left out of a figure, and counted rather than read as zero")
    any_lo = False
    for m in res.measures:
        lo = res.left_out[m.name]
        if lo:
            any_lo = True
            parts = "; ".join(f"{k} x {col} {why}" for (col, why), k in sorted(lo.items()))
            out.append(f"  {m.name}: {sum(lo.values()):,} rows ({parts})")
    if not any_lo:
        out.append("  none")
    out.append("")
    out.append("Topline (the whole book)")
    for m in res.measures:
        if m.is_rate:
            s = res.total.rates[m.name]
            out.append(f"  {m.name:<14} {_pct(s.rate):>9}   {m.label()}   ({s.units:,} loans)")
        elif m.mode == "median":
            s = res.total.medians[m.name]
            out.append(f"  {m.name:<14} {s.median if s.median is not None else '':>9}   {m.label()}")
        else:
            out.append(f"  {m.name:<14} {res.total.rates[m.name].units:>9,}   {m.label()}")
    bench = cfg.benchmark
    if res.band_edges:
        out.append("")
        out.append("Band edges used")
        for name, edges in res.band_edges.items():
            out.append(f"  {name}: {', '.join(engine._fmt(e) for e in edges)}")
    if res.loans_needed:
        out.append("")
        out.append("What this book can show (evidence for your settings, not a setting)")
        for ln in res.loans_needed.values():
            out.append(f"  {ln.sentence()}")
        out.append("  A pocket smaller than that can still show a bigger gap; each pocket below says the")
        out.append("  smallest gap its size could show.")

    for g in res.grids:
        for m in res.measures:
            out.append("")
            head = f"Grid {g.band} x {g.dimension} - {m.name}: {m.label()}"
            if m.is_rate:
                head += f"   topline {_pct(res.total.rates[m.name].rate)}"
                if bench is not None:
                    head += f", median of cells {_pct(g.benchmarks[m.name])}"
            out.append(head)
            if m.is_rate:
                out.append("  each cell: rate, then rate over topline")
            cols = g.dim_labels + [engine.ALL]
            width = max(12, *(len(c) + 2 for c in cols))
            first = max(len(b) for b in g.band_labels + [engine.ALL]) + 2
            out.append(" " * first + "".join(f"{c:>{width * (2 if m.is_rate else 1)}}" for c in cols))
            for b in g.band_labels + [engine.ALL]:
                line = f"{b:<{first}}"
                for d in cols:
                    c = g.cells.get((b, d))
                    if c is None:
                        line += " " * (width * (2 if m.is_rate else 1))
                    elif m.is_rate:
                        s = c.rates[m.name]
                        line += f"{_pct(s.rate):>{width}}{_x(s.vs_topline):>{width}}"
                    elif m.mode == "median":
                        s = c.medians[m.name]
                        line += f"{'' if s.median is None else f'{s.median:g}':>{width}}"
                    else:
                        line += f"{c.rates[m.name].units:>{width},}"
                out.append(line)
            if m.is_rate and res.total.rates[m.name].rate is not None:
                ranked = sorted(((c.rates[m.name].excess, k, c) for k, c in g.inner()
                                 if c.rates[m.name].excess is not None), key=lambda t: -t[0])
                out.append(f"  Where it bleeds: excess {m.numerator()} over the topline rate, largest first")
                for ex, (b, d), c in ranked[:top]:
                    if ex <= 0:
                        break
                    s = c.rates[m.name]
                    out.append(f"    {b} / {d}: {_n(ex)} over, {s.units:,} loans")
                    if bench is not None:
                        out.append(f"      share of losses / share of volume {_x(s.vs_topline)}")
                        out.append(f"      vs rest of book {_x(s.vs_rest)} (p {_p(s.p_book)}): {s.reading_topline}")
                        out.append(f"      vs rest of band {_x(s.vs_band)} (p {_p(s.p_band)}): {s.reading_band}")
                        if s.smallest_gap:
                            out.append(f"      this many loans can show a gap of {s.smallest_gap:.2f}x or more")
                if bench is not None:
                    out.append("  Materiality evidence: what each level would keep (the level is your call)")
                    for row in engine.materiality(g, m, res.total):
                        out.append(f"    {row.share_of_losses:>5.1%} of book losses ({_n(row.threshold)}): "
                                   f"{row.pockets} pocket(s), {row.captured:.0%} of this grid's excess")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cube", description="Origination cube: where does the book bleed?")
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("inspect")
    pi.add_argument("extract")
    pi.add_argument("--sheet")
    pn = sub.add_parser("init")
    pn.add_argument("extract")
    pn.add_argument("-o", "--out", required=True)
    pn.add_argument("--sheet")
    pn.add_argument("--control", help="a filled-in Control tab; its answers go into the file")
    for name in ("validate", "run"):
        sp = sub.add_parser(name)
        sp.add_argument("cube")
        sp.add_argument("--data", required=True)
        sp.add_argument("--sheet")
        if name == "run":
            sp.add_argument("--top", type=int, default=5, help="bleeding cells to list per grid")
    pc = sub.add_parser("control")
    g = pc.add_mutually_exclusive_group(required=True)
    g.add_argument("--out")
    g.add_argument("--read")
    ps = sub.add_parser("synth")
    ps.add_argument("--out", required=True)
    ps.add_argument("--rows", type=int, default=20000)
    a = p.parse_args(argv)

    if a.cmd == "control":
        from . import control
        if a.out:
            print(f"wrote {control.build_control_book(a.out)}")
            return 0
        try:
            for k, v in control.read_control(a.read).items():
                print(f"{k:<16} {v}")
        except control.ControlError as exc:
            print(f"REFUSED: {len(exc.problems)} setting(s) to fix:", file=sys.stderr)
            for prob in exc.problems:
                print(f"  - {prob}", file=sys.stderr)
            return 2
        return 0
    if a.cmd == "synth":
        cfg, data = synth.write(a.out, n=a.rows)
        print(f"wrote {data} and {cfg}")
        return 0
    if a.cmd == "init":
        from . import control, profile
        use = None
        if a.control:
            try:
                use = control.read_control(a.control)
            except control.ControlError as exc:
                print(f"REFUSED: {a.control} has {len(exc.problems)} setting(s) to answer:", file=sys.stderr)
                for prob in exc.problems:
                    print(f"  - {prob}", file=sys.stderr)
                return 2
        path, cols = profile.write_cube_file(read_table(a.extract, a.sheet), a.out, use)
        roles = {}
        for c in cols:
            roles.setdefault(c.role, []).append(c.name)
        print(f"wrote {path}")
        for role in ("band", "dimension", "key", "date", "skipped", "question"):
            if role in roles:
                print(f"  {role:<10} {', '.join(roles[role])}")
        qs = sum(len(c.questions) for c in cols)
        print(f"  {qs} odd value pattern(s) raised as questions; each is used as recorded until answered")
        print("  Next: answer every [CONFIRM: ...] in the file, then `cube validate`.")
        return 0
    if a.cmd == "inspect":
        for e in inspect_columns(read_table(a.extract, a.sheet)):
            print(f"{e['column']:<24} {e['kind']:<10} blank {e['null_share'] or 0:>7.2%}  "
                  f"distinct {e['distinct']:>7,}  {', '.join(e['samples'])}")
        return 0

    try:
        cfg = cfgmod.load(a.cube)
    except cfgmod.ConfigError as exc:
        print(f"REFUSED: {a.cube} has {len(exc.problems)} problem(s):", file=sys.stderr)
        for prob in exc.problems:
            print(f"  - {prob}", file=sys.stderr)
        return 2
    t0 = time.perf_counter()
    table = read_table(a.data, a.sheet)
    t1 = time.perf_counter()
    try:
        res = engine.run(cfg, table)
    except engine.ColumnsMissing as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    t2 = time.perf_counter()
    if a.cmd == "validate":
        print(f"accepted: {cfg.name} over {len(table.rows):,} rows, {len(res.grids)} grid(s), "
              f"{res.tie_outs} tie-out checks agree")
        for w in res.warnings:
            print(f"  WARNING: {w}")
        return 0
    print(report(res, top=a.top))
    print(f"\n(read {t1 - t0:.1f}s, cube {t2 - t1:.1f}s)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
