"""Open the workbook the way the analyst would see it: LibreOffice calculates every formula and prints it.

    python3 render.py BOOK.xlsx OUTDIR [DPI]

Copies the workbook (so the analyst's file is never touched), prints it to PDF, then one PNG per page named by
the tab it belongs to (the page whose first line is a tab's title starts that tab). Prints a page map.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
dpi = sys.argv[3] if len(sys.argv) > 3 else "80"
out.mkdir(parents=True, exist_ok=True)
copy = out / "book.xlsx"
shutil.copy(src, copy)
home = tempfile.mkdtemp()
subprocess.run(["soffice", f"-env:UserInstallation=file://{home}", "--headless", "--norestore", "--convert-to", "pdf",
                "--outdir", str(out), str(copy)], check=True, capture_output=True, env={"HOME": home, "PATH": "/usr/bin:/bin"})
shutil.rmtree(home, ignore_errors=True)
pdf = out / "book.pdf"
info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
pages = int(next(l for l in info.splitlines() if l.startswith("Pages:")).split()[1])
subprocess.run(["pdftoppm", "-r", dpi, "-png", str(pdf), str(out / "p")], check=True)
for p in range(1, pages + 1):
    txt = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-layout", str(pdf), "-"], capture_output=True,
                         text=True).stdout.strip().splitlines()
    print(p, "|", (txt[0].strip() if txt else "")[:90])
(out / "text.txt").write_text(subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True,
                                             text=True).stdout)
