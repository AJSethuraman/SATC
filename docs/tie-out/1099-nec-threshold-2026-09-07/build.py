"""Inline every capture into one self-contained HTML, then render it to PDF.

    cd docs/tie-out/1099-nec-threshold-2026-09-07 && python build.py

The deliverable is ONE file a person can forward. A note plus a folder of loose
images is correct and unusable: every picture in it is a path that resolves only
on the machine that wrote it, so the reader gets prose about evidence they
cannot see. So `IMG:<name>` in exhibit.src.html becomes a base64 data URI here,
and the rendered PDF carries the pictures inside it.
"""
import base64
import mimetypes
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "exhibit.src.html"
HTML = HERE / "TIE-OUT-1099-nec-threshold-2026-09-07.html"
PDF = HERE / "TIE-OUT-1099-nec-threshold-2026-09-07.pdf"

CHROMES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def inline(match: re.Match) -> str:
    name = match.group(1)
    path = HERE / name
    if not path.exists():
        raise SystemExit(f"missing capture: {name}")
    mime = mimetypes.guess_type(name)[0] or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


html = SRC.read_text(encoding="utf-8")
n = len(re.findall(r"IMG:([\w.-]+)", html))
html = re.sub(r"IMG:([\w.-]+)", inline, html)
if "IMG:" in html:
    raise SystemExit("an IMG: token survived — a picture would render as a broken link")
HTML.write_text(html, encoding="utf-8")
print(f"embedded {n} captures -> {HTML.name}  ({HTML.stat().st_size/1024:.0f} KB)")

chrome = next((c for c in CHROMES if pathlib.Path(c).exists()), None) or shutil.which("chrome")
if not chrome:
    print("chrome not found; the HTML is written and can be printed to PDF by hand")
    sys.exit(0)

subprocess.run([
    chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
    "--virtual-time-budget=12000",
    f"--print-to-pdf={PDF}", HTML.as_uri(),
], check=True, capture_output=True, timeout=180)
print(f"rendered -> {PDF.name}  ({PDF.stat().st_size/1024:.0f} KB)")
