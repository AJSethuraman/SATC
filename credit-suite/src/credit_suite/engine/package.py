"""Wrap a base .xlsx into a macro-enabled .xlsm with an embedded VBA project.

Zip surgery only (no Excel needed): copy every part from the base package,
inject xl/vbaProject.bin, switch the workbook part's content type to
macroEnabled, declare the vbaProject content type, and add the workbook->vba
relationship.

Lifted from the six monitors' ``assemble_xlsm.py``, which were identical except
for three tokens: the VBA module name and the two workbook file names. Those are
now arguments -- the module name is the only one this function needs, because a
caller that knows where its base and output live can say so.
"""

from __future__ import annotations

import os
import shutil
import zipfile
from typing import Optional

from credit_suite.engine import vba

WORKBOOK_SHEET_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
WORKBOOK_MACRO_CT = "application/vnd.ms-excel.sheet.macroEnabled.main+xml"
VBA_CT = "application/vnd.ms-office.vbaProject"
VBA_REL_TYPE = "http://schemas.microsoft.com/office/2006/relationships/vbaProject"


def _patch_content_types(xml: str) -> str:
    if WORKBOOK_SHEET_CT not in xml:
        raise RuntimeError("workbook content-type override not found in base package")
    xml = xml.replace(WORKBOOK_SHEET_CT, WORKBOOK_MACRO_CT)
    if "vbaProject.bin" not in xml:
        override = '<Override PartName="/xl/vbaProject.bin" ContentType="%s"/>' % VBA_CT
        xml = xml.replace("</Types>", override + "</Types>")
    return xml


def _patch_workbook_rels(xml: str) -> str:
    if "vbaProject.bin" in xml:
        return xml
    # pick an unused relationship id
    rid = "rIdVbaProject"
    rel = ('<Relationship Id="%s" Type="%s" Target="vbaProject.bin"/>'
           % (rid, VBA_REL_TYPE))
    return xml.replace("</Relationships>", rel + "</Relationships>")


def assemble(base_xlsx: str, out_xlsm: str, macro_bas: str,
             module_name: str, macro_source: Optional[str] = None) -> str:
    """Embed ``macro_bas`` as VBA module ``module_name`` into a copy of ``base_xlsx``.

    ``macro_source`` lets a caller pass the macro text directly instead of a
    path, which is what the self-contained bundle needs -- it has the source in
    memory and no file to point at.
    """
    if macro_source is None:
        with open(macro_bas, encoding="utf-8") as handle:
            macro_source = handle.read()
    vba_bin = vba.write_vba_project([vba.Module(module_name, macro_source)])

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
