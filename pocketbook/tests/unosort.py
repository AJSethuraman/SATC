"""Sort a range of a workbook the way a person does with the filter arrows, in LibreOffice, and save the result.

    /usr/bin/python3 tests/unosort.py IN.xlsx OUT.xlsx SHEET A10:S60 FIELD ASCENDING

FIELD is the column to sort by, counted from 0 at the range's first column; ASCENDING is 1 or 0. The sort moves
whole rows of the range, formulas and all, as Excel's and LibreOffice's sort do; the workbook is calculated after it
and saved with its values, for openpyxl to read back.

Run by tests/test_sorting_2026_10_17.py with the system Python, which is the one with LibreOffice's bridge (uno):
the suite's own Python usually has no uno. Standalone on purpose: it imports nothing from PocketBook."""

import os
import subprocess
import sys
import tempfile
import time
import uuid

import uno
from com.sun.star.beans import PropertyValue
from com.sun.star.table import TableSortField


def pv(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def main(src, out, sheet, ref, field, ascending):
    pipe = f"pocketbook-sort-{uuid.uuid4().hex}"
    profile = tempfile.mkdtemp(prefix="pocketbook-sort-profile-")
    proc = subprocess.Popen(["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--norestore",
                             "--nologo", f"--accept=pipe,name={pipe};urp;"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        ctx = None
        for _ in range(120):
            try:
                ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
                break
            except Exception:                                           # not listening yet
                time.sleep(0.5)
        if ctx is None:
            raise SystemExit("LibreOffice did not start")
        desk = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = desk.loadComponentFromURL(uno.systemPathToFileUrl(os.path.abspath(src)), "_blank", 0,
                                        (pv("Hidden", True),))
        doc.calculateAll()
        rng = doc.Sheets.getByName(sheet).getCellRangeByName(ref)
        f = TableSortField()
        f.Field, f.IsAscending = int(field), ascending == "1"
        desc = rng.createSortDescriptor()
        for p in desc:
            if p.Name == "SortFields":
                p.Value = uno.Any("[]com.sun.star.table.TableSortField", (f,))
            elif p.Name == "ContainsHeader":
                p.Value = False
        uno.invoke(rng, "sort", (desc,))
        doc.calculateAll()
        doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(out)), (pv("FilterName", "Calc MS Excel 2007 XML"),))
        doc.close(True)
    finally:
        try:
            desk.terminate()
        except Exception:
            pass
        proc.terminate()
        proc.wait(timeout=30)


if __name__ == "__main__":
    main(*sys.argv[1:7])
