#!/usr/bin/env python3
"""Generate build_cfpb_monitor.py -- a single self-contained, ASCII-only
builder (the transmission format: TEMPLATE_CONTRACT.md sec 11).

Corporate email/DLP rewrites or blocks binary attachments, so the workbook is
never transmitted -- this ONE plain-text script is. Run it on the target
machine (PowerShell / VS Code terminal) and it builds everything locally:

    python -m pip install pandas openpyxl
    python build_cfpb_monitor.py

It writes into the current folder:
    Mortgage_Delinquency_Monitor.xlsm          (macro embedded, demo-populated)
    Mortgage_Delinquency_Monitor_fallback.xlsx (no VBA -- if your Excel
                                     rejects the embedded project, open
                                     this, paste macro.bas into the VBA
                                     editor, save as .xlsm)
    runner.py, macro.bas, requirements.txt

Run:  python make_bundle.py   (in this repo folder, after make_workbook.py)
"""
import base64
import gzip
import os

HERE = os.path.dirname(os.path.abspath(__file__))
# exec order matters: each module must find its imports already registered.
MODULES = ("keybank_style", "series_seed", "runner", "vba_writer",
           "assemble_xlsm", "build_workbook")
OUT_NAME = "build_cfpb_monitor.py"
WB = "Mortgage_Delinquency_Monitor"


def _b64(path):
    # gzip then base64 -> ~4x smaller, easy to paste into an email body
    # without truncation, still pure ASCII.
    with open(os.path.join(HERE, path), "rb") as f:
        return base64.b64encode(gzip.compress(f.read(), 9)).decode("ascii")


def _chunk(s, n=120):
    return "\n".join('    "%s"' % s[i:i + n] for i in range(0, len(s), n))


def build():
    mods = {n: _b64(n + ".py") for n in MODULES}
    macro_b64 = _b64("macro.bas")
    L = []
    L.append('#!/usr/bin/env python3')
    L.append('"""One-file builder for the County Mortgage Delinquency Monitor (CFPB).')
    L.append('')
    L.append('Plain ASCII (the code rides inside as base64), so it survives corporate')
    L.append('email/DLP intact. Run it on the target machine and it BUILDS the workbook')
    L.append('locally -- nothing binary is ever transmitted.')
    L.append('')
    L.append('USAGE (PowerShell):')
    L.append('    python -m pip install pandas openpyxl')
    L.append('    python build_cfpb_monitor.py')
    L.append('')
    L.append('It writes into the current folder:')
    L.append('    %s.xlsm           (macro embedded, demo-populated)' % WB)
    L.append('    %s_fallback.xlsx  (no VBA; if Excel rejects the .xlsm,' % WB)
    L.append('                      open this, paste macro.bas via Alt+F11, save as .xlsm)')
    L.append('    runner.py, macro.bas, requirements.txt')
    L.append('')
    L.append('Refresh later (workbook CLOSED):')
    L.append('    python runner.py --workbook ".\\\\%s.xlsm" --demo   # offline demo' % WB)
    L.append('    python runner.py --workbook ".\\\\%s.xlsm"          # LIVE -- keyless' % WB)
    L.append('    python runner.py --lookup "Cook"                   # find a county FIPS')
    L.append('The footprint lives in the _config [FOOTPRINT] tab: edit a row + re-run,')
    L.append('no rebuild. A county absent from the CFPB file shows SUPPRESSED -- use its')
    L.append('state row. Or drop control_center.py next to it: python control_center.py')
    L.append('"""')
    L.append('import base64, gzip, os, shutil, sys, types')
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
    L.append('REQUIREMENTS = "pandas>=1.5\\nopenpyxl>=3.0\\n"')
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
    L.append('    # 1) drop the files the refresh/fallback flows need')
    L.append('    _write(os.path.join(cwd, "runner.py"), _decode(_SRC["runner"]))')
    L.append('    _write(os.path.join(cwd, "macro.bas"), _decode(MACRO_B64))')
    L.append('    _write(os.path.join(cwd, "requirements.txt"), REQUIREMENTS)')
    L.append('    # 2) register modules from embedded source (no imports from disk)')
    L.append('    for name in %r:' % (tuple(MODULES),))
    L.append('        m = types.ModuleType(name)')
    L.append('        m.__file__ = os.path.join(cwd, name + ".py")')
    L.append('        sys.modules[name] = m')
    L.append('        exec(compile(_decode(_SRC[name]), name + ".py", "exec"), m.__dict__)')
    L.append('    # 3) build base workbook -> embed VBA -> demo-populate the .xlsm')
    L.append('    base = os.path.join(cwd, "%s_fallback.xlsx")' % WB)
    L.append('    out = os.path.join(cwd, "%s.xlsm")' % WB)
    L.append('    sys.modules["build_workbook"].build(base)')
    L.append('    sys.modules["assemble_xlsm"].assemble(base, out,')
    L.append('        macro_bas=os.path.join(cwd, "macro.bas"))')
    L.append('    sys.modules["runner"].run(out, demo=True)')
    L.append('    # 4) demo-populate the fallback too, so it opens showing dashboards')
    L.append('    sys.modules["runner"].run(base, demo=True)')
    L.append('    print("Built:", out)')
    L.append('    print("Fallback (no VBA):", base)')
    L.append('    print("Also wrote runner.py, macro.bas, requirements.txt in", cwd)')
    L.append('    print("Open the .xlsm (enable macros). If Excel rejects it, open the")')
    L.append('    print("fallback .xlsx, paste macro.bas via Alt+F11, save as .xlsm.")')
    L.append('    print("Live CFPB pulls are KEYLESS -- public domain, no account needed.")')
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
    out = os.path.join(HERE, OUT_NAME)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return out, len(text)


if __name__ == "__main__":
    path, n = build()
    print(f"wrote {path} ({n} bytes, ASCII)")
