#!/usr/bin/env python3
"""Open the artifact: render a built pack through LibreOffice and look.

    python tools/render.py PACK.xlsx [--out DIR]

Writes PACK.pdf (to look at) and PACK.html (every sheet as text) and scans
the HTML for the error strings Excel shows when a formula did not evaluate:
#NAME?, #DIV/0!, #VALUE!, #REF!, #N/A. Prints the count of each and exits 2
when any is present, 1 when LibreOffice is missing or fails.

Needs `libreoffice-calc` installed: the bare `soffice` reports "source file
could not be loaded" for a workbook without it (found 18 Sep 2026).

This is a harness, not a test: a test would need something to assert
against, and the thing worth asserting here is what a person sees.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ERRORS = ("#NAME?", "#DIV/0!", "#VALUE!", "#REF!", "#N/A", "#NUM!")


def render(pack: Path, out_dir: Path) -> dict:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return {"ok": False, "error": "LibreOffice (soffice) not found on PATH"}
    out_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    home = Path(tempfile.mkdtemp(prefix="pack-render-"))
    env["HOME"] = str(home)
    results: dict = {"ok": True, "pack": str(pack), "out": str(out_dir)}
    for fmt in ("pdf", "html"):
        r = subprocess.run([soffice, "--headless", "--norestore", "--convert-to", fmt,
                            "--outdir", str(out_dir), str(pack)],
                           capture_output=True, text=True, timeout=300, env=env)
        target = out_dir / (pack.stem + "." + fmt)
        if r.returncode != 0 or not target.exists():
            results["ok"] = False
            results[f"{fmt}_error"] = (r.stderr or r.stdout).strip()[-400:]
        else:
            results[fmt] = str(target)
    shutil.rmtree(home, ignore_errors=True)
    html = out_dir / (pack.stem + ".html")
    if html.exists():
        text = html.read_text(encoding="utf-8", errors="replace")
        counts = {e: len(re.findall(re.escape(e), text)) for e in ERRORS}
        results["error_cells"] = {k: v for k, v in counts.items() if v}
        results["sheets_seen"] = len(re.findall(r"<table", text, flags=re.I))
    return results


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pack"); p.add_argument("--out", default=None)
    a = p.parse_args(argv)
    pack = Path(a.pack)
    out_dir = Path(a.out) if a.out else pack.parent / "rendered"
    res = render(pack, out_dir)
    for k, v in res.items():
        print(f"{k}: {v}")
    if not res.get("ok"):
        return 1
    if res.get("error_cells"):
        print("ERROR CELLS PRESENT — the workbook does not evaluate cleanly")
        return 2
    print(f"clean: no error cells in {res.get('sheets_seen', 0)} sheets; open {res.get('pdf')} and look")
    return 0


if __name__ == "__main__":
    sys.exit(main())
