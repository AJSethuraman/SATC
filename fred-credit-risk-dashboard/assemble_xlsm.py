#!/usr/bin/env python3
"""Wrap the base .xlsx into a macro-enabled .xlsm with an embedded VBA project.

Zip surgery only (no Excel needed): copy every part from the base package,
inject xl/vbaProject.bin, switch the workbook part's content type to
macroEnabled, declare the vbaProject content type, and add the workbook->vba
relationship. Isolated from build_workbook.py so the embedding can change
independently.
"""
from __future__ import annotations

import os
import shutil
import zipfile

import vba_writer

HERE = os.path.dirname(os.path.abspath(__file__))

WORKBOOK_SHEET_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
WORKBOOK_MACRO_CT = "application/vnd.ms-excel.sheet.macroEnabled.main+xml"
VBA_CT = "application/vnd.ms-office.vbaProject"
VBA_REL_TYPE = "http://schemas.microsoft.com/office/2006/relationships/vbaProject"


def _patch_content_types(xml: str) -> str:
    if WORKBOOK_SHEET_CT not in xml:
        raise RuntimeError("workbook content-type override not found in base package")
    xml = xml.replace(WORKBOOK_SHEET_CT, WORKBOOK_MACRO_CT)
    if "vbaProject.bin" not in xml:
        override = f'<Override PartName="/xl/vbaProject.bin" ContentType="{VBA_CT}"/>'
        xml = xml.replace("</Types>", override + "</Types>")
    return xml


def _patch_workbook_rels(xml: str) -> str:
    if "vbaProject.bin" in xml:
        return xml
    # pick an unused relationship id
    rid = "rIdVbaProject"
    rel = (f'<Relationship Id="{rid}" Type="{VBA_REL_TYPE}" '
           f'Target="vbaProject.bin"/>')
    return xml.replace("</Relationships>", rel + "</Relationships>")


def assemble(base_xlsx: str, out_xlsm: str, macro_bas: str = None) -> str:
    macro_bas = macro_bas or os.path.join(HERE, "macro.bas")
    src = open(macro_bas, encoding="utf-8").read()
    vba_bin = vba_writer.write_vba_project([vba_writer.Module("FREDDashboard", src)])

    tmp = out_xlsm + ".tmp"
    with zipfile.ZipFile(base_xlsx, "r") as zin, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        names = set(zin.namelist())
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = _patch_content_types(data.decode("utf-8")).encode("utf-8")
            elif item.filename == "xl/_rels/workbook.xml.rels":
                data = _patch_workbook_rels(data.decode("utf-8")).encode("utf-8")
            zout.writestr(item, data)
        if "xl/_rels/workbook.xml.rels" not in names:
            raise RuntimeError("base package missing xl/_rels/workbook.xml.rels")
        zout.writestr("xl/vbaProject.bin", vba_bin)
    shutil.move(tmp, out_xlsm)
    return out_xlsm


if __name__ == "__main__":
    base = os.path.join(HERE, "build", "FRED_Credit_Risk_Dashboard_base.xlsx")
    out = os.path.join(HERE, "FRED_Credit_Risk_Dashboard.xlsm")
    assemble(base, out)
    print(f"assembled {out} ({os.path.getsize(out)} bytes)")
