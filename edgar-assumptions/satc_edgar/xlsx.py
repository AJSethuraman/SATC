"""Minimal, dependency-free, deterministic XLSX writer.

Produces a styled .xlsx (OOXML) workbook using only the standard library, so
the project keeps zero runtime dependencies and stays reproducible. Supports
the formatting this tool needs: bold headers, per-cell number formats
(percent / ratio "x" / days / integer), solid fills, frozen header rows, frozen
columns, column widths, and per-sheet auto-filters.

Determinism: all zip members are written in a fixed order with a fixed
timestamp, so a given workbook serializes identically on every run within an
environment. Inline strings are used (no shared-string table) to keep output
order stable and self-contained.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

# Common number-format codes (registered as custom formats).
FMT_PCT1 = '0.0%'
FMT_RATIO = '0.00"x"'
FMT_DAYS = '0.0'
FMT_INT = '#,##0'
FMT_USD = '#,##0'

Value = Union[str, int, float, None]


@dataclass(frozen=True)
class Cell:
    value: Value = None
    fmt: Optional[str] = None      # number-format code (numbers only)
    bold: bool = False
    fill: Optional[str] = None     # 6-hex RGB, e.g. "D9E1F2"
    wrap: bool = False


def txt(value: Value, *, bold: bool = False, fill: Optional[str] = None,
        wrap: bool = False) -> Cell:
    return Cell(value=value, bold=bold, fill=fill, wrap=wrap)


def num(value: Value, fmt: Optional[str] = None, *, bold: bool = False,
        fill: Optional[str] = None) -> Cell:
    return Cell(value=value, fmt=fmt, bold=bold, fill=fill)


@dataclass
class Sheet:
    name: str
    rows: List[List[Cell]] = field(default_factory=list)
    col_widths: Dict[int, float] = field(default_factory=dict)  # 0-based col -> width
    freeze_rows: int = 0
    freeze_cols: int = 0
    autofilter: bool = False

    def add_row(self, cells: List[Cell]) -> None:
        self.rows.append(cells)

    def set_widths(self, widths: Dict[int, float]) -> None:
        self.col_widths.update(widths)


class Workbook:
    def __init__(self) -> None:
        self.sheets: List[Sheet] = []
        # Style registry: maps (numFmt, bold, fill, wrap) -> cellXfs index.
        self._styles: Dict[Tuple[Optional[str], bool, Optional[str], bool], int] = {}
        self._numfmts: Dict[str, int] = {}
        self._fills: Dict[str, int] = {}
        # Style 0 is the default (no format, not bold, no fill).
        self._styles[(None, False, None, False)] = 0

    def add_sheet(self, name: str) -> Sheet:
        sheet = Sheet(name=_safe_sheet_name(name, [s.name for s in self.sheets]))
        self.sheets.append(sheet)
        return sheet

    # -- style resolution --------------------------------------------------
    def _style_id(self, cell: Cell) -> int:
        key = (cell.fmt, cell.bold, cell.fill, cell.wrap)
        if key in self._styles:
            return self._styles[key]
        if cell.fmt and cell.fmt not in self._numfmts:
            self._numfmts[cell.fmt] = 164 + len(self._numfmts)
        if cell.fill and cell.fill not in self._fills:
            # fill ids 0 (none) and 1 (gray125) are reserved.
            self._fills[cell.fill] = 2 + len(self._fills)
        sid = len(self._styles)
        self._styles[key] = sid
        return sid

    # -- save --------------------------------------------------------------
    def save(self, path: str) -> None:
        # Pre-compute style ids for every cell (also fills registries).
        for sheet in self.sheets:
            for row in sheet.rows:
                for cell in row:
                    self._style_id(cell)

        parts: List[Tuple[str, str]] = []
        parts.append(("[Content_Types].xml", self._content_types()))
        parts.append(("_rels/.rels", _ROOT_RELS))
        parts.append(("docProps/core.xml", _CORE_XML))
        parts.append(("docProps/app.xml", _APP_XML))
        parts.append(("xl/workbook.xml", self._workbook_xml()))
        parts.append(("xl/_rels/workbook.xml.rels", self._workbook_rels()))
        parts.append(("xl/styles.xml", self._styles_xml()))
        for i, sheet in enumerate(self.sheets, 1):
            parts.append((f"xl/worksheets/sheet{i}.xml", self._sheet_xml(sheet)))

        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name, data in parts:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                zf.writestr(info, data)

    # -- xml builders ------------------------------------------------------
    def _content_types(self) -> str:
        overrides = [
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
            '<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
            '<Override PartName="/docProps/app.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
        ]
        for i in range(1, len(self.sheets) + 1):
            overrides.append(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            + "".join(overrides)
            + "</Types>"
        )

    def _workbook_xml(self) -> str:
        sheets_xml = "".join(
            f'<sheet name="{_xml_escape(s.name)}" sheetId="{i}" r:id="rId{i}"/>'
            for i, s in enumerate(self.sheets, 1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{sheets_xml}</sheets></workbook>"
        )

    def _workbook_rels(self) -> str:
        rels = []
        for i in range(1, len(self.sheets) + 1):
            rels.append(
                f'<Relationship Id="rId{i}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{i}.xml"/>'
            )
        styles_rid = len(self.sheets) + 1
        rels.append(
            f'<Relationship Id="rId{styles_rid}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rels)
            + "</Relationships>"
        )

    def _styles_xml(self) -> str:
        # numFmts
        numfmt_items = sorted(self._numfmts.items(), key=lambda kv: kv[1])
        numfmts = "".join(
            f'<numFmt numFmtId="{nid}" formatCode="{_xml_escape(code)}"/>'
            for code, nid in numfmt_items
        )
        numfmts_block = f'<numFmts count="{len(numfmt_items)}">{numfmts}</numFmts>' if numfmt_items else ""

        # fonts: 0 normal, 1 bold
        fonts = (
            '<fonts count="2">'
            '<font><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><name val="Calibri"/></font>'
            "</fonts>"
        )

        # fills: 0 none, 1 gray125, then custom solids
        fill_items = sorted(self._fills.items(), key=lambda kv: kv[1])
        custom_fills = "".join(
            f'<fill><patternFill patternType="solid">'
            f'<fgColor rgb="FF{rgb}"/><bgColor indexed="64"/></patternFill></fill>'
            for rgb, _ in fill_items
        )
        fills = (
            f'<fills count="{2 + len(fill_items)}">'
            '<fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill>'
            + custom_fills
            + "</fills>"
        )

        borders = '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        cellstylexfs = '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'

        # cellXfs, ordered by style id
        ordered = sorted(self._styles.items(), key=lambda kv: kv[1])
        xfs = []
        for (fmt, bold, fill, wrap), _sid in ordered:
            num_id = self._numfmts.get(fmt, 0) if fmt else 0
            font_id = 1 if bold else 0
            fill_id = self._fills.get(fill, 0) if fill else 0
            attrs = [
                f'numFmtId="{num_id}"',
                f'fontId="{font_id}"',
                f'fillId="{fill_id}"',
                'borderId="0"',
                'xfId="0"',
            ]
            if num_id:
                attrs.append('applyNumberFormat="1"')
            if font_id:
                attrs.append('applyFont="1"')
            if fill_id:
                attrs.append('applyFill="1"')
            if wrap:
                attrs.append('applyAlignment="1"')
                xfs.append(f'<xf {" ".join(attrs)}><alignment wrapText="1" vertical="top"/></xf>')
            else:
                xfs.append(f'<xf {" ".join(attrs)}/>')
        cellxfs = f'<cellXfs count="{len(xfs)}">{"".join(xfs)}</cellXfs>'
        cellstyles = '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            + numfmts_block + fonts + fills + borders + cellstylexfs + cellxfs + cellstyles
            + "</styleSheet>"
        )

    def _sheet_xml(self, sheet: Sheet) -> str:
        n_rows = len(sheet.rows)
        n_cols = max((len(r) for r in sheet.rows), default=0)

        # sheetViews / freeze
        view = '<sheetView workbookViewId="0">'
        if sheet.freeze_rows or sheet.freeze_cols:
            top_left = f"{_col_letter(sheet.freeze_cols)}{sheet.freeze_rows + 1}"
            if sheet.freeze_rows and sheet.freeze_cols:
                active = "bottomRight"
            elif sheet.freeze_rows:
                active = "bottomLeft"
            else:
                active = "topRight"
            view += (
                f'<pane xSplit="{sheet.freeze_cols}" ySplit="{sheet.freeze_rows}" '
                f'topLeftCell="{top_left}" activePane="{active}" state="frozen"/>'
                f'<selection pane="{active}" activeCell="{top_left}" sqref="{top_left}"/>'
            )
        view += "</sheetView>"
        sheet_views = f"<sheetViews>{view}</sheetViews>"

        # cols
        cols_xml = ""
        if sheet.col_widths:
            items = []
            for col, width in sorted(sheet.col_widths.items()):
                c = col + 1
                items.append(f'<col min="{c}" max="{c}" width="{width:.2f}" customWidth="1"/>')
            cols_xml = f"<cols>{''.join(items)}</cols>"

        # rows
        rows_xml = []
        for ri, row in enumerate(sheet.rows, 1):
            cells_xml = []
            for ci, cell in enumerate(row):
                ref = f"{_col_letter(ci)}{ri}"
                sid = self._style_id(cell)
                cells_xml.append(_cell_xml(ref, sid, cell))
            rows_xml.append(f'<row r="{ri}">{"".join(cells_xml)}</row>')
        sheet_data = f"<sheetData>{''.join(rows_xml)}</sheetData>"

        autofilter = ""
        if sheet.autofilter and n_rows and n_cols:
            ref = f"A1:{_col_letter(n_cols - 1)}{n_rows}"
            autofilter = f'<autoFilter ref="{ref}"/>'

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            + sheet_views
            + '<sheetFormatPr defaultRowHeight="15"/>'
            + cols_xml + sheet_data + autofilter
            + "</worksheet>"
        )


# -- helpers ---------------------------------------------------------------
def _cell_xml(ref: str, style_id: int, cell: Cell) -> str:
    s_attr = f' s="{style_id}"' if style_id else ""
    v = cell.value
    if v is None or v == "":
        return f'<c r="{ref}"{s_attr}/>'
    if isinstance(v, bool):
        v = "TRUE" if v else "FALSE"
        return f'<c r="{ref}"{s_attr} t="inlineStr"><is><t xml:space="preserve">{v}</t></is></c>'
    if isinstance(v, (int, float)):
        return f'<c r="{ref}"{s_attr}><v>{_num_repr(v)}</v></c>'
    text = _xml_escape(str(v))
    return f'<c r="{ref}"{s_attr} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _num_repr(v: Union[int, float]) -> str:
    if isinstance(v, int):
        return str(v)
    if v == int(v):
        return str(int(v))
    return repr(round(float(v), 6))


def _col_letter(idx0: int) -> str:
    """0-based column index -> Excel column letter (0 -> A)."""
    idx = idx0 + 1
    letters = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _safe_sheet_name(name: str, existing: List[str]) -> str:
    # Excel: <=31 chars, no : \ / ? * [ ]
    bad = ':\\/?*[]'
    clean = "".join("_" if ch in bad else ch for ch in name)[:31]
    base = clean or "Sheet"
    candidate = base
    n = 2
    while candidate in existing:
        suffix = f"_{n}"
        candidate = base[: 31 - len(suffix)] + suffix
        n += 1
    return candidate


_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="xl/workbook.xml"/>'
    '<Relationship Id="rId2" '
    'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
    'Target="docProps/core.xml"/>'
    '<Relationship Id="rId3" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
    'Target="docProps/app.xml"/>'
    "</Relationships>"
)

# Fixed (timestamp-free) docProps so output is byte-stable.
_CORE_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<cp:coreProperties '
    'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/">'
    '<dc:creator>SATC EDGAR assumption tool</dc:creator>'
    '<cp:lastModifiedBy>SATC EDGAR assumption tool</cp:lastModifiedBy>'
    "</cp:coreProperties>"
)

_APP_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties '
    'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
    '<Application>SATC EDGAR assumption tool</Application>'
    "</Properties>"
)
