"""Photograph the two workbooks as LibreOffice Calc shows them, recalculated on load (as Excel would), one view per
shot, into raw/. Run under a virtual display:

    xvfb-run -a -s "-screen 0 2000x1200x24" python3 workbook_shots.py

Each view is a copy of the workbook with the sheet, the top-left cell and any dropdown set the way an analyst would
set them; nothing else is touched. (The first tie-out's workbook-shots.py, generalised to both workbooks.)"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
BLEED = HERE / "Consumer book Q3 - PocketBook.xlsx"
SCOUT = HERE / "Scouting book - PocketBook.xlsx"
WORK = Path(tempfile.mkdtemp(prefix="shots-"))
PROFILE = WORK / "profile"
SHOTS = HERE / "raw"

XCU = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="ODFRecalcMode" oor:op="fuse"><value>0</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="ShowTipOfTheDay" oor:op="fuse"><value>false</value></prop></item>
<item oor:path="/org.openoffice.Setup/Office"><prop oor:name="FirstStartWizardCompleted" oor:op="fuse"><value>true</value></prop></item>
</oor:items>
"""

VIEWS = {
    # name: (book, sheet, top-left cell, selected cell, {(sheet, cell): value})
    "start-here": (BLEED, "Start here", "A2", "F17", {}),
    "pockets-kept": (BLEED, "Pockets", "A17", "L23", {("Pockets", "C18"): "Kept after losses"}),
    "new-variables": (SCOUT, "New variables", "A28", "J45", {}),
    "look-util": (SCOUT, "Look", "A103", "C113", {}),
}


def main():
    (PROFILE / "user").mkdir(parents=True, exist_ok=True)
    (PROFILE / "user" / "registrymodifications.xcu").write_text(XCU, encoding="utf-8")
    SHOTS.mkdir(exist_ok=True)
    for name in sys.argv[1:] or list(VIEWS):
        book, sheet, top, sel, sets = VIEWS[name]
        d = WORK / name
        d.mkdir(parents=True, exist_ok=True)
        f = d / book.name
        shutil.copy(book, f)
        wb = load_workbook(f)
        for (sh, cell), v in sets.items():
            wb[sh][cell].value = v
        ws = wb[sheet]
        wb.active = wb.sheetnames.index(sheet)
        for w in wb.worksheets:
            w.sheet_view.tabSelected = w.title == sheet
        if ws.sheet_view.pane is not None:
            ws.sheet_view.pane.topLeftCell = top
        else:
            ws.sheet_view.topLeftCell = top
        ws.sheet_view.selection[0].activeCell = sel
        ws.sheet_view.selection[0].sqref = sel
        wb.save(f)
        p = subprocess.Popen(["soffice", f"-env:UserInstallation={PROFILE.as_uri()}", "--norestore", "--nologo",
                              "--calc", str(f)], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(float(os.environ.get("WAIT", "16")))
        subprocess.run(["import", "-window", "root", str(SHOTS / f"{name}.png")], check=False)
        os.killpg(p.pid, signal.SIGTERM)
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
        time.sleep(2)
        print("shot", name, flush=True)
    shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    main()
