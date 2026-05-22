from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

def _col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

def write_xlsx(path: str | Path, sheets: dict[str, list[dict]], styles: bool = False) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(sheets)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", """<?xml version='1.0' encoding='UTF-8'?>
<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>
<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>
<Default Extension='xml' ContentType='application/xml'/>
<Override PartName='/xl/workbook.xml' ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'/>
<Override PartName='/xl/styles.xml' ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml'/>
""" + "".join(f"<Override PartName='/xl/worksheets/sheet{i}.xml' ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'/>" for i in range(1, len(names)+1)) + "</Types>")
        z.writestr("_rels/.rels", """<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' Target='xl/workbook.xml'/></Relationships>""")
        z.writestr("xl/_rels/workbook.xml.rels", "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>" + "".join(f"<Relationship Id='rId{i}' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet' Target='worksheets/sheet{i}.xml'/>" for i in range(1, len(names)+1)) + f"<Relationship Id='rId{len(names)+1}' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles' Target='styles.xml'/></Relationships>")
        z.writestr("xl/workbook.xml", f"<workbook xmlns='{_NS}' xmlns:r='{_REL}'><sheets>" + "".join(f"<sheet name='{html.escape(name)}' sheetId='{i}' r:id='rId{i}'/>" for i, name in enumerate(names, 1)) + "</sheets></workbook>")
        z.writestr("xl/styles.xml", _styles_xml())
        for idx, name in enumerate(names, 1):
            z.writestr(f"xl/worksheets/sheet{idx}.xml", _sheet_xml(sheets[name]))
    return path

def _styles_xml() -> str:
    return f"""<styleSheet xmlns='{_NS}'><fonts count='2'><font><sz val='11'/><name val='Calibri'/></font><font><b/><color rgb='FFFFFFFF'/><sz val='12'/><name val='Calibri'/></font></fonts><fills count='6'><fill><patternFill patternType='none'/></fill><fill><patternFill patternType='gray125'/></fill><fill><patternFill patternType='solid'><fgColor rgb='FF0B1F3A'/></patternFill></fill><fill><patternFill patternType='solid'><fgColor rgb='FFC9A227'/></patternFill></fill><fill><patternFill patternType='solid'><fgColor rgb='FFE5E7EB'/></patternFill></fill><fill><patternFill patternType='solid'><fgColor rgb='FF166534'/></patternFill></fill></fills><borders count='1'><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count='1'><xf numFmtId='0' fontId='0' fillId='0' borderId='0'/></cellStyleXfs><cellXfs count='6'><xf numFmtId='0' fontId='0' fillId='0' borderId='0'/><xf numFmtId='0' fontId='1' fillId='2' borderId='0' applyFill='1' applyFont='1'/><xf numFmtId='0' fontId='0' fillId='3' borderId='0' applyFill='1'/><xf numFmtId='0' fontId='0' fillId='4' borderId='0' applyFill='1'/><xf numFmtId='4' fontId='0' fillId='0' borderId='0' applyNumberFormat='1'/><xf numFmtId='14' fontId='0' fillId='0' borderId='0' applyNumberFormat='1'/></cellXfs></styleSheet>"""

def _sheet_xml(rows: list[dict]) -> str:
    headers = list(rows[0].keys()) if rows else []
    matrix = [headers] + [[r.get(h, "") for h in headers] for r in rows]
    body = []
    for r_idx, row in enumerate(matrix, 1):
        cells = []
        for c_idx, value in enumerate(row, 1):
            ref = f"{_col(c_idx)}{r_idx}"
            style = " s='3'" if r_idx == 1 else ""
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f"<c r='{ref}'{style}><v>{value}</v></c>")
            else:
                text = html.escape("" if value is None else str(value))
                cells.append(f"<c r='{ref}' t='inlineStr'{style}><is><t>{text}</t></is></c>")
        body.append(f"<row r='{r_idx}'>" + "".join(cells) + "</row>")
    cols = "".join(f"<col min='{i}' max='{i}' width='{max(12, min(45, len(h)+6))}' customWidth='1'/>" for i, h in enumerate(headers, 1))
    return f"<worksheet xmlns='{_NS}'><sheetViews><sheetView workbookViewId='0'><pane ySplit='1' topLeftCell='A2' activePane='bottomLeft' state='frozen'/></sheetView></sheetViews><cols>{cols}</cols><sheetData>{''.join(body)}</sheetData></worksheet>"

def read_xlsx(path: str | Path) -> dict[str, list[dict]]:
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        sheet_names = [s.attrib["name"] for s in wb.findall(f".//{{{_NS}}}sheet")]
        out = {}
        for i, name in enumerate(sheet_names, 1):
            root = ET.fromstring(z.read(f"xl/worksheets/sheet{i}.xml"))
            rows = []
            for row in root.findall(f".//{{{_NS}}}row"):
                values = []
                for c in row.findall(f"{{{_NS}}}c"):
                    inline = c.find(f"{{{_NS}}}is/{{{_NS}}}t")
                    v = c.find(f"{{{_NS}}}v")
                    values.append(inline.text if inline is not None else (v.text if v is not None else ""))
                rows.append(values)
            if rows:
                headers = rows[0]
                out[name] = [dict(zip(headers, r + [""] * (len(headers)-len(r)))) for r in rows[1:]]
            else:
                out[name] = []
        return out
