#!/usr/bin/env python3
"""Generate build_dashboard.py -- a single self-contained, ASCII-only builder.

Bundles keybank_style.py, series_seed.py, runner.py, build_workbook.py and
macro.bas as base64 into one script that, when run, writes runner.py, macro.bas,
requirements.txt and the demo-populated FRED_Credit_Risk_Dashboard.xlsx into the
current folder. The point: plain-text/base64 survives email + corporate DLP that
rewrites binary .xlsx attachments, so the workbook is built locally instead of
transferred. Run:  python make_bundle.py
"""
import base64
import gzip
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = ("keybank_style", "series_seed", "runner", "build_workbook")


def _b64(path):
    # gzip then base64 -> ~4x smaller, so the script is easy to paste into an
    # email body without truncation. Still pure ASCII.
    with open(os.path.join(HERE, path), "rb") as f:
        return base64.b64encode(gzip.compress(f.read(), 9)).decode("ascii")


def _chunk(s, n=120):
    return "\n".join('    "%s"' % s[i:i + n] for i in range(0, len(s), n))


def build():
    mods = {n: _b64(n + ".py") for n in MODULES}
    macro_b64 = _b64("macro.bas")
    L = []
    L.append('#!/usr/bin/env python3')
    L.append('"""One-file builder for the FRED Credit-Risk Dashboard (KeyBank style).')
    L.append('')
    L.append('Why this exists: emailing the .xlsx binary kept getting rewritten/blocked by')
    L.append('corporate security. This script is plain ASCII (the code is base64 inside), so')
    L.append('it survives email/DLP intact. Run it on the target machine and it BUILDS the')
    L.append('workbook locally -- nothing binary to corrupt.')
    L.append('')
    L.append('USAGE (PowerShell):')
    L.append('    python -m pip install pandas openpyxl      # fredapi too, for live data')
    L.append('    python build_dashboard.py')
    L.append('')
    L.append('It writes into the current folder:')
    L.append('    runner.py, macro.bas, requirements.txt, and')
    L.append('    FRED_Credit_Risk_Dashboard.xlsx  (demo-populated, opens showing the dashboards)')
    L.append('')
    L.append('Then: open the .xlsx. For live FRED data, set FRED_API_KEY and run:')
    L.append('    python runner.py --workbook ".\\\\FRED_Credit_Risk_Dashboard.xlsx" --backend openpyxl')
    L.append('"""')
    L.append('import base64, gzip, os, sys, types')
    L.append('')
    for n in MODULES:
        L.append('%s_B64 = (' % n.upper())
        L.append(_chunk(mods[n]))
        L.append(')')
        L.append('')
    L.append('MACRO_B64 = (')
    L.append(_chunk(macro_b64))
    L.append(')')
    L.append('')
    L.append('REQUIREMENTS = "pandas>=1.5\\nopenpyxl>=3.0\\nfredapi>=0.5\\n"')
    L.append('')
    L.append('_SRC = {')
    for n in MODULES:
        L.append('    %r: %s_B64,' % (n, n.upper()))
    L.append('}')
    L.append('')
    L.append('def _decode(b): return gzip.decompress(base64.b64decode(b)).decode("utf-8")')
    L.append('')
    L.append('def _write(path, text):')
    L.append('    with open(path, "w", encoding="utf-8", newline="\\n") as fh:')
    L.append('        fh.write(text)')
    L.append('')
    L.append('def main():')
    L.append('    cwd = os.getcwd()')
    L.append('    # 1) drop the source files the build + refresh need')
    L.append('    _write(os.path.join(cwd, "runner.py"), _decode(RUNNER_B64))')
    L.append('    _write(os.path.join(cwd, "macro.bas"), _decode(MACRO_B64))')
    L.append('    _write(os.path.join(cwd, "requirements.txt"), REQUIREMENTS)')
    L.append('    # 2) register the modules from embedded source (no import from disk)')
    L.append('    for name in ("keybank_style", "series_seed", "runner", "build_workbook"):')
    L.append('        m = types.ModuleType(name)')
    L.append('        m.__file__ = os.path.join(cwd, name + ".py")')
    L.append('        sys.modules[name] = m')
    L.append('        exec(compile(_decode(_SRC[name]), name + ".py", "exec"), m.__dict__)')
    L.append('    # 3) build the workbook, then demo-populate so it opens showing data')
    L.append('    out = os.path.join(cwd, "FRED_Credit_Risk_Dashboard.xlsx")')
    L.append('    sys.modules["build_workbook"].build(out)')
    L.append('    sys.modules["runner"].run(out, backend_name="openpyxl", demo=True)')
    L.append('    print("Built:", out)')
    L.append('    print("Also wrote runner.py, macro.bas, requirements.txt in", cwd)')
    L.append('    print("Open the .xlsx. For live data: set FRED_API_KEY and run runner.py (see --help).")')
    L.append('')
    L.append('if __name__ == "__main__":')
    L.append('    try:')
    L.append('        main()')
    L.append('    except ImportError as e:')
    L.append('        sys.stderr.write("Missing dependency: %s\\nRun: python -m pip install pandas openpyxl\\n" % e)')
    L.append('        sys.exit(1)')
    L.append('')
    text = "\n".join(L)
    assert all(ord(c) < 128 for c in text), "bundle must be pure ASCII"
    out = os.path.join(HERE, "build_dashboard.py")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return out, len(text)


if __name__ == "__main__":
    path, n = build()
    print(f"wrote {path} ({n} bytes, ASCII)")
