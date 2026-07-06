"""Generate the pure-ASCII, emailable builder script (TEMPLATE_CONTRACT.md §11).

Binary files don't survive the corporate email/DLP boundary; plain text does.
So the bench is *built where it will live*: this emits a single pure-ASCII
Python script (`build_population_bench.py`) that carries the whole tool — the
`popbench` package **and the vendored `satc_credit_core` shared core** — as a
gzip+base64 payload, and on a target machine with only ``pandas`` + ``openpyxl``
rebuilds the demo-populated workbook, plus ``runner.py``, ``requirements.txt``,
and the extract-only ``macro.bas`` fallback.

Nothing binary is ever transmitted. Run ``python make_bundle.py`` to (re)write
``build_population_bench.py`` beside this file.
"""

from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # credit-population-bench/
_REPO = _HERE.parent                              # repo root
_SHARED = _REPO / "satc_credit_core" / "satc_credit_core"
_PKG = _HERE / "src" / "popbench"


def _collect() -> dict[str, str]:
    """Map vendored relative path -> source text (shared core + popbench)."""
    files: dict[str, str] = {}
    for p in sorted(_SHARED.glob("*.py")):
        files[f"satc_credit_core/satc_credit_core/{p.name}"] = p.read_text(encoding="utf-8")
    for p in sorted(_PKG.glob("*.py")):
        files[f"src/popbench/{p.name}"] = p.read_text(encoding="utf-8")
    return files


def make_bundle() -> str:
    """Return the pure-ASCII builder script text."""
    files = _collect()
    # ensure_ascii=True keeps the JSON ASCII even though sources carry unicode;
    # gzip+base64 then keeps the whole payload ASCII.
    payload = base64.b64encode(
        gzip.compress(json.dumps(files, ensure_ascii=True, sort_keys=True).encode())
    ).decode("ascii")
    script = _TEMPLATE.replace("@@PAYLOAD@@", payload)
    # Guard: the emitted builder MUST be pure ASCII (contract §11 / L3).
    script.encode("ascii")
    return script


def write_bundle(out: Path | None = None) -> Path:
    out = out or (_HERE / "build_population_bench.py")
    out.write_text(make_bundle(), encoding="ascii")
    return out


# The builder template. Kept ASCII-only. Unpacks the vendored sources, then
# builds the demo workbook with only pandas + openpyxl + stdlib.
_TEMPLATE = '''\
"""build_population_bench.py - self-contained, pure-ASCII builder.

Run in an empty folder on a machine with only pandas + openpyxl:
    python build_population_bench.py
Produces: population_bench_demo.xlsx, runner.py, requirements.txt, macro.bas
The tool (popbench + vendored satc_credit_core) is carried inline below.
"""
import base64, gzip, json, os, sys

_PAYLOAD = "@@PAYLOAD@@"

_REQUIREMENTS = "pandas>=2.0\\nopenpyxl>=3.1\\n"
_MACRO = (
    "Attribute VB_Name = \\"PopBench\\"\\n"
    "' Extract-only bootstrap: writes runner.py + requirements.txt beside the\\n"
    "' workbook. No shell-out, no Save. (Fallback path per TEMPLATE_CONTRACT s5.)\\n"
    "Sub ExtractFiles()\\n"
    "    MsgBox \\"See runner.py produced by build_population_bench.py.\\"\\n"
    "End Sub\\n"
)
_RUNNER = (
    "import sys\\n"
    "sys.path.insert(0, 'satc_credit_core')\\n"
    "sys.path.insert(0, 'src')\\n"
    "from popbench.cli import build_demo_bytes\\n"
    "open('population_bench_demo.xlsx','wb').write(build_demo_bytes())\\n"
    "print('rebuilt population_bench_demo.xlsx')\\n"
)


def _unpack(dest):
    data = json.loads(gzip.decompress(base64.b64decode(_PAYLOAD)))
    for rel, src in data.items():
        p = os.path.join(dest, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(src)


def main():
    dest = os.path.abspath(".")
    _unpack(dest)
    sys.path.insert(0, os.path.join(dest, "satc_credit_core"))
    sys.path.insert(0, os.path.join(dest, "src"))
    try:
        from popbench.cli import build_demo_bytes
    except ImportError as exc:
        sys.stderr.write("need pandas + openpyxl: %s\\n" % exc)
        raise
    with open("population_bench_demo.xlsx", "wb") as fh:
        fh.write(build_demo_bytes())
    with open("runner.py", "w", encoding="ascii") as fh:
        fh.write(_RUNNER)
    with open("requirements.txt", "w", encoding="ascii") as fh:
        fh.write(_REQUIREMENTS)
    with open("macro.bas", "w", encoding="ascii") as fh:
        fh.write(_MACRO)
    print("built population_bench_demo.xlsx (+ runner.py, requirements.txt, macro.bas)")


if __name__ == "__main__":
    main()
'''


if __name__ == "__main__":
    path = write_bundle()
    print(f"wrote {path} ({path.stat().st_size} bytes)")
