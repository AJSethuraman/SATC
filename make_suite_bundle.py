#!/usr/bin/env python3
"""Generate build_suite.py -- ONE pure-ASCII file that carries the whole suite.

Instead of transferring six template bundles + control_center.py (7 files),
transfer this one script. Run it on the target machine and pick what to
build; it writes control_center.py plus each chosen template's builder into
its own subfolder and runs it (demo-populated workbooks, fallbacks, runners).

Discovery is dynamic: any */build_*.py bundle in the repo is embedded, so new
templates join the suite bundle automatically on regeneration.

Run:  python make_suite_bundle.py     (in the repo root, after builds)
"""
import base64
import glob
import gzip
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "build_suite.py")


def _b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(gzip.compress(f.read(), 9)).decode("ascii")


def _chunk(s, n=120):
    return "\n".join('    "%s"' % s[i:i + n] for i in range(0, len(s), n))


def collect():
    bundles = {}
    for p in sorted(glob.glob(os.path.join(HERE, "*", "build_*.py"))):
        name = os.path.basename(p)                    # build_fdic_monitor.py
        if name == "build_workbook.py":
            continue          # internal builder module, not a transfer bundle
        folder = os.path.basename(os.path.dirname(p))  # fdic-peer-monitor
        bundles[name] = (folder, _b64(p))
    return bundles


def build():
    bundles = collect()
    cc = _b64(os.path.join(HERE, "control_center.py"))
    L = []
    L.append('#!/usr/bin/env python3')
    L.append('"""Credit-Risk Template Suite -- one-file installer (pure ASCII).')
    L.append('')
    L.append('USAGE (PowerShell):')
    L.append('    python -m pip install pandas openpyxl')
    L.append('    python build_suite.py            # menu: pick templates or all')
    L.append('    python build_suite.py --all      # build everything')
    L.append('    python build_suite.py --list     # show what is inside')
    L.append('')
    L.append('It writes control_center.py here, plus each chosen template into its')
    L.append('own subfolder (demo-populated workbook + fallback + runner). Then:')
    L.append('    python control_center.py         # the GUI for everything')
    L.append('"""')
    L.append('import base64, gzip, os, subprocess, sys')
    L.append('')
    L.append('CC_B64 = (')
    L.append(_chunk(cc))
    L.append(')')
    L.append('')
    L.append('BUNDLES = {}')
    for name, (folder, b64) in bundles.items():
        var = name.replace(".", "_").replace("-", "_").upper()
        L.append('%s = (' % var)
        L.append(_chunk(b64))
        L.append(')')
        L.append('BUNDLES[%r] = (%r, %s)' % (name, folder, var))
        L.append('')
    L.append('def _write(path, b64):')
    L.append('    with open(path, "wb") as fh:')
    L.append('        fh.write(gzip.decompress(base64.b64decode(b64)))')
    L.append('')
    L.append('def main():')
    L.append('    names = sorted(BUNDLES)')
    L.append('    if "--list" in sys.argv:')
    L.append('        for i, n in enumerate(names, 1):')
    L.append('            print(f"{i}. {n}  ->  {BUNDLES[n][0]}/")')
    L.append('        return 0')
    L.append('    _write(os.path.join(os.getcwd(), "control_center.py"), CC_B64)')
    L.append('    print("wrote control_center.py")')
    L.append('    if "--all" in sys.argv:')
    L.append('        chosen = names')
    L.append('    else:')
    L.append('        for i, n in enumerate(names, 1):')
    L.append('            print(f"  {i}. {n}")')
    L.append('        raw = input("Build which? (numbers space-separated, or a=all): ").strip()')
    L.append('        chosen = names if raw.lower() in ("a", "all") else \\')
    L.append('            [names[int(x) - 1] for x in raw.split()]')
    L.append('    for n in chosen:')
    L.append('        folder, b64 = BUNDLES[n]')
    L.append('        os.makedirs(folder, exist_ok=True)')
    L.append('        dest = os.path.join(folder, n)')
    L.append('        _write(dest, b64)')
    L.append('        print(f"== building {n} in {folder}/ ==")')
    L.append('        r = subprocess.run([sys.executable, n], cwd=folder)')
    L.append('        if r.returncode != 0:')
    L.append('            print(f"   FAILED (exit {r.returncode}) -- fix and rerun; continuing")')
    L.append('    print("Done. Next: python control_center.py")')
    L.append('    return 0')
    L.append('')
    L.append('if __name__ == "__main__":')
    L.append('    try:')
    L.append('        sys.exit(main())')
    L.append('    except ImportError as e:')
    L.append('        sys.stderr.write("Missing dependency: %s\\nRun: python -m pip install pandas openpyxl\\n" % e)')
    L.append('        sys.exit(1)')
    L.append('')
    text = "\n".join(L)
    assert all(ord(c) < 128 for c in text), "suite bundle must be pure ASCII"
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return OUT, len(text), list(bundles)


if __name__ == "__main__":
    path, n, names = build()
    print(f"wrote {path} ({n:,} bytes, ASCII) embedding {len(names)} template "
          f"bundles + control_center.py:")
    for x in names:
        print("  -", x)
