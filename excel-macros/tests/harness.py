"""Runs the macros in LibreOffice, headless, in its Excel-compatible mode (Option VBASupport 1).

LibreOffice is not Excel. What this proves is the macros' own logic: what they count, what they write, what they
refuse. What it cannot prove is that Excel runs them the same way. That is the firm's first run on a real machine,
and the reason every macro writes what it did to the log on its own sheet.
"""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

MACROS = Path(__file__).resolve().parents[1] / "macros"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def basic_source(bas: Path) -> str:
    """A .bas file as LibreOffice takes it: the Attribute lines Excel's importer reads are dropped, and the module is
    put in Excel-compatible mode."""
    lines = [ln for ln in bas.read_text(encoding="utf-8").splitlines() if not ln.startswith("Attribute VB_")]
    return "Option VBASupport 1\n" + "\n".join(lines) + "\n"


class Office:
    """One headless LibreOffice for a test session."""

    def __init__(self):
        import uno
        self._uno = uno
        self.profile = Path(tempfile.mkdtemp(prefix="lo_macros_"))
        self.port = _free_port()
        self.proc = subprocess.Popen(
            ["soffice", "--headless", "--invisible", "--norestore", "--nologo",
             f"-env:UserInstallation={self.profile.as_uri()}",
             f"--accept=socket,host=127.0.0.1,port={self.port};urp;"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        last = None
        for _ in range(120):
            try:
                self.ctx = resolver.resolve(
                    f"uno:socket,host=127.0.0.1,port={self.port};urp;StarOffice.ComponentContext")
                break
            except Exception as e:            # noqa: BLE001 - not up yet
                last = e
                time.sleep(0.5)
        else:
            raise RuntimeError(f"LibreOffice did not start: {last}")
        self.desktop = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)

    def _pv(self, name, value):
        from com.sun.star.beans import PropertyValue
        p = PropertyValue()
        p.Name, p.Value = name, value
        return p

    def run(self, xlsx: Path, out: Path, steps: list[tuple[str, str]], modules=("Hygiene",)) -> None:
        """Opens `xlsx`, loads the macro modules, and runs each (sheet to activate, macro) in order; then saves to
        `out` as xlsx. Messages go to the log, never a dialog (HygieneSetQuiet)."""
        doc = self.desktop.loadComponentFromURL(Path(xlsx).resolve().as_uri(), "_blank", 0,
                                                ())
        try:
            libs = doc.BasicLibraries
            if not libs.hasByName("Standard"):
                libs.createLibrary("Standard")
            lib = libs.getByName("Standard")
            for m in modules:
                src = basic_source(MACROS / f"{m}.bas")
                if lib.hasByName(m):
                    lib.replaceByName(m, src)
                else:
                    lib.insertByName(m, src)
            sp = doc.getScriptProvider()

            def call(name):
                sp.getScript(f"vnd.sun.star.script:Standard.{modules[0]}.{name}?language=Basic&location=document"
                             ).invoke((), (), ())
            if modules[0] == "Hygiene":
                call("HygieneSetQuiet")
            for sheet, macro in steps:
                if sheet:
                    doc.getCurrentController().setActiveSheet(doc.Sheets.getByName(sheet))
                call(macro)
            doc.calculateAll()
            doc.storeToURL(Path(out).resolve().as_uri(), (self._pv("FilterName", "Calc MS Excel 2007 XML"),))
        finally:
            doc.close(True)

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(20)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)
