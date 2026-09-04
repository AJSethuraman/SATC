#!/usr/bin/env python3
"""Emit a monitor's self-contained, pure-ASCII builder (contract section 11).

    python tools/make_bundle.py             # every spine monitor
    python tools/make_bundle.py fdic -o .   # one, into a directory

The output is the transmission format: a single plain-text script that carries
the shared engine, the source adapter and the config inside it as gzip+base64,
and builds the workbook wherever it lands. Nothing binary is ever emailed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from credit_suite.bundles import SPECS            # noqa: E402
from credit_suite.engine import inline            # noqa: E402


def emit(name: str, out_dir: Path) -> Path:
    spec = SPECS[name]
    text = inline.render_bundle(spec)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / ("build_%s.py" % spec.name)
    with open(path, "w", encoding="ascii", newline="\n") as handle:
        handle.write(text)

    modules = inline.discover(list(spec.roots))
    print("%s: %d modules inlined -> %s (%.1f KB)"
          % (name, len(modules), path, len(text) / 1024.0))
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("monitors", nargs="*", choices=[*SPECS, []])
    ap.add_argument("-o", "--out-dir", default=".")
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)
    for name in (args.monitors or list(SPECS)):
        emit(name, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
