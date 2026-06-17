"""Export an SATC workbook to a branded PDF using headless LibreOffice.

Usage:
    python scripts/export_pdf.py <workbook.xlsx> [output_dir]

Page header/footer branding is set per-sheet by the workbook builder
(``ws.oddFooter`` / ``ws.oddHeader``); this script performs the conversion. It
reuses the same ``office.soffice`` environment shim as recalc.py so it works in
sandboxed environments where AF_UNIX sockets are restricted.
"""

import json
import platform
import subprocess
import sys
from pathlib import Path

from office.soffice import get_soffice_env


def export_pdf(xlsx_path: str, out_dir: str | None = None, timeout: int = 120) -> dict:
    src = Path(xlsx_path)
    if not src.exists():
        return {"error": f"File not found: {src}"}
    out_directory = Path(out_dir) if out_dir else src.parent
    out_directory.mkdir(parents=True, exist_ok=True)

    cmd = [
        "soffice", "--headless", "--norestore",
        "--convert-to", "pdf:calc_pdf_Export",
        "--outdir", str(out_directory.absolute()),
        str(src.absolute()),
    ]
    if platform.system() == "Linux":
        cmd = ["timeout", str(timeout)] + cmd

    result = subprocess.run(cmd, capture_output=True, text=True, env=get_soffice_env())
    pdf_path = out_directory / (src.stem + ".pdf")
    if not pdf_path.exists():
        return {
            "error": "PDF was not produced",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    return {"status": "success", "pdf": str(pdf_path), "bytes": pdf_path.stat().st_size}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/export_pdf.py <workbook.xlsx> [output_dir]")
        sys.exit(1)
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(export_pdf(sys.argv[1], out_dir), indent=2))


if __name__ == "__main__":
    main()
