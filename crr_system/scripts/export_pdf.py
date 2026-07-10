"""Export an Excel workbook to PDF via a LibreOffice Basic macro.

Installs a RecalcStoreExport macro that loads the file itself (sandbox-safe:
no reliance on ThisComponent or CLI document arguments), recalculates,
stores, and writes <file>.pdf alongside it.

Requires libreoffice-calc. NOTE: in this environment only libreoffice-core
is preinstalled; run `apt-get update && apt-get install -y libreoffice-calc`
once per container or every LibreOffice spreadsheet operation fails with
"type detection failed".

    python scripts/export_pdf.py workbook.xlsx [timeout_seconds]
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from office.soffice import get_soffice_env  # noqa: E402

MACRO_DIR = Path("~/.config/libreoffice/4/user/basic/Standard").expanduser()
JOB_FILE = "/tmp/recalc_job.txt"
LOG_FILE = "/tmp/exportpdf.log"

MACRO = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module2" script:language="StarBasic">
    Sub RecalcStoreExport()
      Dim loadArgs(0) As New com.sun.star.beans.PropertyValue
      Dim pdfArgs(0) As New com.sun.star.beans.PropertyValue
      Dim oDoc As Object
      Dim src As String, job As String, target As String
      Dim n As Integer
      On Error Goto Fail
      n = Freefile
      Open "/tmp/recalc_job.txt" For Input As #n
      Line Input #n, src
      Line Input #n, job
      Close #n
      loadArgs(0).Name = "Hidden"
      loadArgs(0).Value = True
      oDoc = StarDesktop.loadComponentFromURL(ConvertToURL(src), "_blank", 0, loadArgs())
      oDoc.calculateAll()
      oDoc.store()
      If job = "pdf" Then
        pdfArgs(0).Name = "FilterName"
        pdfArgs(0).Value = "calc_pdf_Export"
        target = Left(oDoc.Url, Len(oDoc.Url) - 5) &amp; ".pdf"
        oDoc.storeToURL(target, pdfArgs())
      End If
      oDoc.close(False)
      n = Freefile
      Open "/tmp/exportpdf.log" For Output As #n
      Print #n, "OK " &amp; src
      Close #n
      StarDesktop.terminate()
      Exit Sub
      Fail:
      n = Freefile
      Open "/tmp/exportpdf.log" For Output As #n
      Print #n, "ERR " &amp; Err &amp; " " &amp; Error$ &amp; " at " &amp; Erl
      Close #n
      StarDesktop.terminate()
    End Sub
</script:module>"""


def export(path: Path, timeout: str = "300", job: str = "pdf") -> Path:
    MACRO_DIR.mkdir(parents=True, exist_ok=True)
    (MACRO_DIR / "Module2.xba").write_text(MACRO)
    xlb = MACRO_DIR / "script.xlb"
    if xlb.exists() and "Module2" not in xlb.read_text():
        xlb.write_text(xlb.read_text().replace(
            "</library:library>",
            ' <library:element library:name="Module2"/>\n</library:library>'))
    Path(JOB_FILE).write_text(f"{path.resolve()}\n{job}\n")
    Path(LOG_FILE).unlink(missing_ok=True)
    subprocess.run(
        ["timeout", timeout, "soffice", "--headless", "--norestore",
         "vnd.sun.star.script:Standard.Module2.RecalcStoreExport?language=Basic&location=application"],
        capture_output=True, env=get_soffice_env())
    log = Path(LOG_FILE).read_text() if Path(LOG_FILE).exists() else "(no log)"
    pdf = path.with_suffix(".pdf")
    if job == "pdf" and not pdf.exists():
        raise RuntimeError(f"PDF export failed: {log.strip()}")
    if not log.startswith("OK"):
        raise RuntimeError(f"Macro failed: {log.strip()}")
    return pdf


if __name__ == "__main__":
    target = Path(sys.argv[1])
    t = sys.argv[2] if len(sys.argv) > 2 else "300"
    print(export(target, t))
