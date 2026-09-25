"""`cube` - the command line.

  cube inspect  EXTRACT                     every column: kind, blanks, distinct, samples
  cube validate CUBE.yaml --data EXTRACT    refuse or accept, and say why
  cube run      CUBE.yaml --data EXTRACT    build the cube and print it
  cube synth    --out DIR                   a synthetic book with a known answer

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
                    word = f"   {s.reading_topline}" if s.reading_topline else ""
                    out.append(f"    {b} / {d}: {_n(ex)} over   ({_x(s.vs_topline)} topline, "
                               f"{s.units:,} loans){word}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cube", description="Origination cube: where does the book bleed?")
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("inspect")
    pi.add_argument("extract")
    pi.add_argument("--sheet")
    for name in ("validate", "run"):
        sp = sub.add_parser(name)
        sp.add_argument("cube")
        sp.add_argument("--data", required=True)
        sp.add_argument("--sheet")
        if name == "run":
            sp.add_argument("--top", type=int, default=5, help="bleeding cells to list per grid")
    ps = sub.add_parser("synth")
    ps.add_argument("--out", required=True)
    ps.add_argument("--rows", type=int, default=20000)
    a = p.parse_args(argv)

    if a.cmd == "synth":
        cfg, data = synth.write(a.out, n=a.rows)
        print(f"wrote {data} and {cfg}")
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
