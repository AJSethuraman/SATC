"""Table slicers, written into a finished .xlsx without Excel.

A slicer is a panel of buttons over one column of a table: click a button and
the table shows only the rows with that value. The bank blocks macros, so this
is how a user picks one row of a table. openpyxl cannot write slicers, so the
parts are added to the package (the zip) here, after openpyxl has saved it.

What Excel 16 itself writes for a table slicer, and so what this writes
(taken from a workbook Excel saved after ``SlicerCaches.Add2(listObject, col)``
and ``Slicers.Add``):

    xl/slicerCaches/slicerCacheN.xml   one per column: its name (also a
                                       workbook defined name, ``#N/A``) and an
                                       ``x15:tableSlicerCache`` naming the
                                       table id and the tableColumn id
    xl/slicers/slicerN.xml             one per sheet: every slicer on it
    workbook.xml                       the defined names, and the caches in an
                                       ``x15:slicerCaches`` ext
    the sheet                          an ``x14:slicerList`` ext pointing at
                                       its slicers part
    the sheet's drawing                one ``twoCellAnchor`` per slicer, an
                                       ``mc:AlternateContent`` around a
                                       ``sle:slicer`` graphic frame
    the table                          the selection itself: an autoFilter
                                       ``filterColumn`` per slicer

A table slicer stores no list of items and no selection of its own. Excel
reads the buttons from the column and the selection from the table's
autoFilter each time the file opens, so the autoFilter *is* the state the
workbook opens in. Excel also writes the rows the filter hides as hidden, and
does not re-filter on open, so they are written hidden here too: otherwise
the file would open showing every row under a slicer that says one.

Every edit is a string insertion into the XML openpyxl wrote, never a parse
and re-serialise: ElementTree renames namespace prefixes, and a renamed
prefix named in ``mc:Ignorable`` is a repair prompt.
"""
from __future__ import annotations

import os
import posixpath
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as _escape

__all__ = ["add_table_slicers"]

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
X14 = "http://schemas.microsoft.com/office/spreadsheetml/2009/9/main"
X15 = "http://schemas.microsoft.com/office/spreadsheetml/2010/11/main"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
XDR = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"

R_WORKSHEET = REL_NS + "/worksheet"
R_TABLE = REL_NS + "/table"
R_DRAWING = REL_NS + "/drawing"
R_SHARED = REL_NS + "/sharedStrings"
R_SLICER = "http://schemas.microsoft.com/office/2007/relationships/slicer"
R_SLICER_CACHE = "http://schemas.microsoft.com/office/2007/relationships/slicerCache"

CT_SLICER = "application/vnd.ms-excel.slicer+xml"
CT_SLICER_CACHE = "application/vnd.ms-excel.slicerCache+xml"
CT_DRAWING = "application/vnd.openxmlformats-officedocument.drawing+xml"

# The ext URIs Excel uses for *table* slicers (pivot slicers use others).
URI_WB_SLICER_CACHES = "{46BE6895-7355-4a93-B00E-2C351335B9C9}"
URI_SHEET_SLICER_LIST = "{3A4CF648-6AED-40f4-86FF-DC5316D8AED3}"
URI_TABLE_SLICER_CACHE = "{2F2917AC-EB37-4324-AD4E-5DD8C200BD13}"

DEFAULT_STYLE = "SlicerStyleLight2"
ROW_HEIGHT_EMU = 241300            # what Excel wrote: one button row, 19pt

# CT_Worksheet children after <drawing>: a new <drawing> goes before the first.
_AFTER_DRAWING = ("legacyDrawing", "legacyDrawingHF", "drawingHF", "picture",
                  "oleObjects", "controls", "webPublishItems", "tableParts", "extLst")
# CT_Workbook children after <definedNames>.
_AFTER_DEFINED_NAMES = ("calcPr", "oleSize", "customWorkbookViews", "pivotCaches",
                        "smartTagPr", "smartTagTypes", "webPublishing",
                        "fileRecoveryPr", "webPublishObjects", "extLst")


def _attr(text: str) -> str:
    """Escape for a double-quoted XML attribute, keeping whitespace literal."""
    return _escape(text, {'"': "&quot;", "\n": "&#10;", "\r": "&#13;", "\t": "&#9;"})


# --------------------------------------------------------------------- package

class _Package:
    """The zip's parts as text, edited in memory and written back once."""

    def __init__(self, path: Path):
        self.path = path
        with zipfile.ZipFile(path) as z:
            self.infos = z.infolist()
            self.parts: Dict[str, bytes] = {i.filename: z.read(i.filename) for i in self.infos}
        self.added: List[str] = []

    def text(self, name: str) -> str:
        return self.parts[name].decode("utf-8")

    def put(self, name: str, text: str) -> None:
        if name not in self.parts:
            self.added.append(name)
        self.parts[name] = text.encode("utf-8")

    def free(self, pattern: str) -> str:
        """The first unused part name for ``pattern % n``, n from 1."""
        n = 1
        while pattern % n in self.parts:
            n += 1
        return pattern % n

    def save(self) -> None:
        fd, tmp = tempfile.mkstemp(suffix=".xlsx", dir=str(self.path.parent))
        os.close(fd)
        try:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
                for info in self.infos:
                    out.writestr(info, self.parts[info.filename])
                for name in self.added:
                    out.writestr(name, self.parts[name])
            shutil.copymode(self.path, tmp)        # mkstemp's file is owner-only
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise


def _rels_name(part: str) -> str:
    d, f = posixpath.split(part)
    return posixpath.join(d, "_rels", f + ".rels")


def _resolve(source_part: str, target: str) -> str:
    """A relationship target as a part name (no leading slash)."""
    if target.startswith("/"):
        return target[1:]
    return posixpath.normpath(posixpath.join(posixpath.dirname(source_part), target))


def _rels(pkg: _Package, part: str) -> List[Tuple[str, str, str]]:
    """(Id, Type, resolved target) for each relationship of ``part``."""
    name = _rels_name(part)
    if name not in pkg.parts:
        return []
    root = ET.fromstring(pkg.parts[name])
    return [(r.get("Id"), r.get("Type"), _resolve(part, r.get("Target")))
            for r in root.iter("{%s}Relationship" % PKG_REL)
            if r.get("TargetMode") != "External"]


def _add_rel(pkg: _Package, part: str, rtype: str, target: str) -> str:
    """Add a relationship from ``part`` to ``target`` (a part name); its Id."""
    name = _rels_name(part)
    if name in pkg.parts:
        text = pkg.text(name)
    else:
        text = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="%s"></Relationships>' % PKG_REL)
    used = set(re.findall(r'\bId="([^"]*)"', text))
    n = 1
    while "rId%d" % n in used:
        n += 1
    rid = "rId%d" % n
    rel = '<Relationship Id="%s" Type="%s" Target="/%s"/>' % (rid, rtype, _attr(target))
    pkg.put(name, _insert_before_close(text, rel))
    return rid


def _add_override(pkg: _Package, part: str, content_type: str) -> None:
    text = pkg.text("[Content_Types].xml")
    if 'PartName="/%s"' % part in text:
        return
    text = _insert_before_close(
        text, '<Override PartName="/%s" ContentType="%s"/>' % (part, content_type))
    pkg.put("[Content_Types].xml", text)


# ------------------------------------------------------------ string surgery

_TOKEN = re.compile(
    r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<!.*?>"
    r"|<(/?)((?:[A-Za-z_][\w.-]*:)?([A-Za-z_][\w.-]*))"
    r"((?:\s+[^\s=/>]+\s*=\s*(?:\"[^\"]*\"|'[^']*'))*)\s*(/?)>", re.S)


def _top(text: str) -> Tuple[str, str, List[Tuple[str, int, int]], int]:
    """The root element's prefix, local name, direct children as
    (local name, start, end), and where its closing tag starts (-1 when the
    root is written self-closing, ``<x/>``)."""
    depth, children, root, prefix, open_at = 0, [], None, "", None
    for m in _TOKEN.finditer(text):
        if m.group(2) is None:
            continue
        closing, qname, local, _, empty = m.groups()
        if not closing:
            if depth == 0:
                root, prefix = local, qname[:-len(local) - 1] if ":" in qname else ""
            elif depth == 1:
                open_at = (local, m.start())
            if empty:
                if depth == 0:
                    return prefix, root, [], -1
                if depth == 1:
                    children.append((local, m.start(), m.end()))
            else:
                depth += 1
        else:
            depth -= 1
            if depth == 1:
                children.append((open_at[0], open_at[1], m.end()))
            elif depth == 0:
                return prefix, root, children, m.start()
    raise ValueError("unbalanced XML")


def _insert_before_close(text: str, fragment: str) -> str:
    """Insert ``fragment`` as the root's last child."""
    close = _top(text)[3]
    if close < 0:                                  # <root .../>: open it
        m = next(m for m in _TOKEN.finditer(text) if m.group(2))
        opened = re.sub(r"\s*/>$", ">", m.group(0))
        return text[:m.start()] + opened + fragment + "</%s>" % m.group(2) + text[m.end():]
    return text[:close] + fragment + text[close:]


def _insert_child(text: str, fragment: str, before: Sequence[str]) -> str:
    """Insert ``fragment`` as a child of the root, ahead of the first child
    named in ``before`` (the schema's order), else last."""
    _, _, children, close = _top(text)
    at = next((s for name, s, _ in children if name in before), close)
    return text[:at] + fragment + text[at:]


def _child(text: str, local: str) -> Optional[Tuple[int, int]]:
    """(start, end) of the root's first direct child called ``local``."""
    _, _, children, _ = _top(text)
    return next(((s, e) for name, s, e in children if name == local), None)


def _append_into(text: str, span: Tuple[int, int], local: str, fragment: str) -> str:
    """Append ``fragment`` inside the element at ``span``, opening it if empty."""
    s, e = span
    element = text[s:e]
    if element.rstrip(">").rstrip().endswith("/"):
        opened = re.sub(r"\s*/>$", ">", element) + fragment + "</%s>" % local
    else:
        i = element.rindex("</")
        opened = element[:i] + fragment + element[i:]
    return text[:s] + opened + text[e:]


def _add_ext(text: str, ext: str) -> str:
    """Add ``ext`` to the root's extLst (always its last child), making one if needed."""
    span = _child(text, "extLst")
    if span:
        return _append_into(text, span, "extLst", ext)
    return _insert_before_close(text, "<extLst>" + ext + "</extLst>")


# --------------------------------------------------------------- reading cells

def _col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def _split_ref(ref: str) -> Tuple[int, int]:
    m = re.fullmatch(r"\$?([A-Z]{1,3})\$?(\d+)", ref)
    if not m:
        raise ValueError("bad cell reference %r" % ref)
    return _col_index(m.group(1)), int(m.group(2))


def _shared_strings(pkg: _Package) -> List[str]:
    for _, rtype, target in _rels(pkg, "xl/workbook.xml"):
        if rtype == R_SHARED and target in pkg.parts:
            root = ET.fromstring(pkg.parts[target])
            out = []
            for si in root.findall("{%s}si" % MAIN):
                # Rich text is several runs; phonetic hints (rPh) are not text.
                out.append("".join(t.text or "" for t in si.iter("{%s}t" % MAIN)
                                   if not _inside_rph(si, t)))
            return out
    return []


def _inside_rph(si, t) -> bool:
    for rph in si.findall("{%s}rPh" % MAIN):
        if t in list(rph.iter()):
            return True
    return False


def _column_text(sheet_xml: bytes, shared: List[str], col: int, first: int,
                 last: int, header: str) -> Dict[int, Optional[str]]:
    """Each row's text in column ``col`` for rows first..last (None if blank).

    Refuses a number, a boolean, an error or a formula with no saved result:
    a slicer button and a filter value are the text Excel *displays*, and
    that cannot be known here for anything but text."""
    root = ET.fromstring(sheet_xml)
    data = root.find("{%s}sheetData" % MAIN)
    out: Dict[int, Optional[str]] = {r: None for r in range(first, last + 1)}
    for row in data.findall("{%s}row" % MAIN):
        r = int(row.get("r"))
        if r < first or r > last:
            continue
        for c in row.findall("{%s}c" % MAIN):
            ci, cr = _split_ref(c.get("r"))
            if ci != col:
                continue
            t = c.get("t", "n")
            v = c.find("{%s}v" % MAIN)
            f = c.find("{%s}f" % MAIN)
            if t == "inlineStr":
                is_ = c.find("{%s}is" % MAIN)
                text = "".join(x.text or "" for x in is_.iter("{%s}t" % MAIN)) if is_ is not None else ""
            elif t == "s" and v is not None:
                text = shared[int(v.text)]
            elif t == "str" and v is not None:
                text = v.text or ""
            elif v is None and f is None:
                text = None
            else:
                what = "a formula with no saved result" if v is None else "not text (type %s)" % t
                raise ValueError("column %r, row %d: %s; a slicer column must hold text"
                                 % (header, r, what))
            out[r] = text if text != "" else None
    return out


# ---------------------------------------------------------------- the edits

def _find_sheet(pkg: _Package, title: str) -> str:
    wb = ET.fromstring(pkg.parts["xl/workbook.xml"])
    rid = None
    for s in wb.iter("{%s}sheet" % MAIN):
        if s.get("name") == title:
            rid = s.get("{%s}id" % REL_NS)
    if rid is None:
        raise ValueError("no sheet named %r" % title)
    for i, rtype, target in _rels(pkg, "xl/workbook.xml"):
        if i == rid and rtype == R_WORKSHEET:
            return target
    raise ValueError("sheet %r has no worksheet part" % title)


def _find_table(pkg: _Package, sheet_part: str, name: str) -> str:
    for _, rtype, target in _rels(pkg, sheet_part):
        if rtype == R_TABLE:
            t = ET.fromstring(pkg.parts[target])
            if name in (t.get("name"), t.get("displayName")):
                return target
    raise ValueError("no table named %r on that sheet" % name)


def _defined_name(base: str, taken: set) -> str:
    """Excel's cache name for a column: Slicer_ + the header, word characters only."""
    stem = "Slicer_" + (re.sub(r"[^\w.]", "_", base, flags=re.UNICODE) or "Column")
    name, n = stem, 1
    while name.lower() in taken:
        name = "%s%d" % (stem, n)
        n += 1
    taken.add(name.lower())
    return name


def _anchor(spec) -> Tuple[int, int, int, int]:
    a = tuple(spec)
    if len(a) != 4 or not all(isinstance(x, int) and x >= 0 for x in a):
        raise ValueError("anchor must be (from_col, from_row, to_col, to_row), 0-based "
                         "cell indices; got %r" % (spec,))
    if a[2] <= a[0] or a[3] <= a[1]:
        raise ValueError("anchor %r: the 'to' cell must be right of and below the 'from' cell" % (a,))
    return a


def _slicer_anchor(name: str, shape_id: int, a: Tuple[int, int, int, int]) -> str:
    """One floating slicer frame, as Excel writes it (with the fallback shape
    Excel 2007 shows in its place)."""
    fc, fr, tc, tr = a
    return (
        '<xdr:twoCellAnchor editAs="absolute" xmlns:xdr="%(xdr)s" xmlns:a="%(a)s">'
        '<xdr:from><xdr:col>%(fc)d</xdr:col><xdr:colOff>0</xdr:colOff>'
        '<xdr:row>%(fr)d</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>'
        '<xdr:to><xdr:col>%(tc)d</xdr:col><xdr:colOff>0</xdr:colOff>'
        '<xdr:row>%(tr)d</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>'
        '<mc:AlternateContent xmlns:mc="%(mc)s">'
        '<mc:Choice xmlns:sle15="http://schemas.microsoft.com/office/drawing/2012/slicer" Requires="sle15">'
        '<xdr:graphicFrame macro=""><xdr:nvGraphicFramePr>'
        '<xdr:cNvPr id="%(id)d" name="%(name)s"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>'
        '<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm>'
        '<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/drawing/2010/slicer">'
        '<sle:slicer xmlns:sle="http://schemas.microsoft.com/office/drawing/2010/slicer" name="%(name)s"/>'
        '</a:graphicData></a:graphic></xdr:graphicFrame></mc:Choice>'
        '<mc:Fallback><xdr:sp macro="" textlink=""><xdr:nvSpPr><xdr:cNvPr id="0" name=""/>'
        '<xdr:cNvSpPr><a:spLocks noTextEdit="1"/></xdr:cNvSpPr></xdr:nvSpPr>'
        '<xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1828800" cy="2524125"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:prstClr val="white"/></a:solidFill>'
        '<a:ln w="1"><a:solidFill><a:prstClr val="green"/></a:solidFill></a:ln></xdr:spPr>'
        '<xdr:txBody><a:bodyPr vertOverflow="clip" horzOverflow="clip"/><a:lstStyle/>'
        '<a:p><a:r><a:rPr lang="en-US" sz="1100"/><a:t>This shape represents a table slicer. '
        'Table slicers are not supported in this version of Excel.</a:t></a:r></a:p></xdr:txBody>'
        '</xdr:sp></mc:Fallback></mc:AlternateContent><xdr:clientData/></xdr:twoCellAnchor>'
    ) % {"xdr": XDR, "a": A, "mc": MC, "fc": fc, "fr": fr, "tc": tc, "tr": tr,
         "id": shape_id, "name": _attr(name)}


def _set_row_hidden(sheet: str, first: int, last: int, hidden: set) -> str:
    """Rows first..last: hidden exactly when in ``hidden``. A row with no
    element yet (every cell blank) gets one if it must be hidden."""
    seen = set()

    def fix(m):
        tag = m.group(0)
        r = int(re.search(r'\br="(\d+)"', tag).group(1))
        if r < first or r > last:
            return tag
        seen.add(r)
        tag = re.sub(r'\s+hidden="[^"]*"', "", tag)
        if r in hidden:
            tag = re.sub(r"^<row\b", '<row hidden="1"', tag)
        return tag

    sheet = re.sub(r"<row\b[^>]*>", fix, sheet)
    missing = sorted(r for r in hidden if r not in seen)
    for r in missing:
        new = '<row r="%d" hidden="1"/>' % r
        later = [m for m in re.finditer(r'<row\b[^>]*\br="(\d+)"', sheet) if int(m.group(1)) > r]
        if later:
            i = later[0].start()
            sheet = sheet[:i] + new + sheet[i:]
        elif re.search(r"<sheetData\s*/>", sheet):
            sheet = re.sub(r"<sheetData\s*/>", "<sheetData>" + new + "</sheetData>", sheet, 1)
        else:
            i = sheet.index("</sheetData>")
            sheet = sheet[:i] + new + sheet[i:]
    return sheet


def add_table_slicers(path, sheet_title: str, table_name: str, slicers: list) -> None:
    """Add one slicer per entry, over table ``table_name`` on ``sheet_title``.

    ``slicers``: a list of dicts, laid out by the caller's anchors:

        {"column":   "Product",             # the table column it filters
         "caption":  "Product",             # the title over the buttons
         "anchor":   (1, 2, 3, 11),         # (from_col, from_row, to_col, to_row),
                                            # 0-based cells; the slicer floats
         "selected": "Credit card",         # the one button pressed at open
         "name":     "PickProduct",         # optional; default the column name
         "style":    "SlicerStyleLight2"}   # optional

    The buttons are every distinct value in the column, one column of them.
    The table's autoFilter is written to the selection, and the rows it hides
    are written hidden, so the file opens showing what the slicers say.
    Rewrites ``path`` in place. Refuses (ValueError) rather than guesses: an
    unknown sheet, table or column, a selection that is not in the column, a
    column that is not text, a sheet that already has slicers, or a table
    whose autoFilter already filters something.
    """
    path = Path(path)
    if not slicers:
        raise ValueError("no slicers asked for")
    pkg = _Package(path)
    sheet_part = _find_sheet(pkg, sheet_title)
    table_part = _find_table(pkg, sheet_part, table_name)
    sheet = pkg.text(sheet_part)
    table = pkg.text(table_part)
    workbook = pkg.text("xl/workbook.xml")
    if any(_top(x)[0] for x in (sheet, workbook, table)):
        raise ValueError("expected SpreadsheetML in the default namespace, as openpyxl writes it")
    if "slicerList" in sheet:
        raise ValueError("sheet %r already has slicers; add them all in one call" % sheet_title)

    # ---- the table: its id, its columns, its data rows
    t = ET.fromstring(table.encode("utf-8"))
    table_id = t.get("id")
    columns = [(c.get("id"), c.get("name")) for c in t.find("{%s}tableColumns" % MAIN)]
    top_left, bottom_right = t.get("ref").split(":")
    c0, r0 = _split_ref(top_left)
    _, r1 = _split_ref(bottom_right)
    if t.get("headerRowCount", "1") != "1":
        raise ValueError("table %r has no header row, so it cannot be filtered" % table_name)
    first, last = r0 + 1, r1 - int(t.get("totalsRowCount") or 0)
    if last < first:
        raise ValueError("table %r has no data rows" % table_name)
    af = t.find("{%s}autoFilter" % MAIN)
    if af is not None and len(af):
        raise ValueError("table %r already filters on something; refusing to guess what "
                         "rows it shows" % table_name)

    shared = _shared_strings(pkg)
    taken_names = {m.lower() for m in re.findall(r'<definedName\b[^>]*\bname="([^"]*)"', workbook)}
    plan, slicer_names = [], set()
    for spec in slicers:
        col = spec["column"]
        idx = [i for i, (_, nm) in enumerate(columns) if nm == col]
        if not idx:
            raise ValueError("table %r has no column %r" % (table_name, col))
        i = idx[0]
        if any(p["col_index"] == i for p in plan):
            raise ValueError("two slicers on column %r; one per column" % col)
        values = _column_text(pkg.parts[sheet_part], shared, c0 + i, first, last, col)
        selected = spec["selected"]
        # Excel matches a filter value regardless of case; so does this.
        match = [v for v in values.values() if v is not None
                 and isinstance(selected, str) and v.casefold() == selected.casefold()]
        if not match:
            raise ValueError("column %r has no value %r to select" % (col, selected))
        name = spec.get("name") or col
        if name.casefold() in slicer_names:
            raise ValueError("two slicers named %r" % name)
        slicer_names.add(name.casefold())
        plan.append({
            "col_index": i, "column_id": columns[i][0], "column": col,
            "caption": spec.get("caption", col), "anchor": _anchor(spec["anchor"]),
            "selected": match[0], "name": name, "values": values,
            "style": spec.get("style", DEFAULT_STYLE),
            "cache": _defined_name(col, taken_names),
        })

    # ---- the selection: the table's autoFilter, and the rows it hides
    filters = "".join(
        '<filterColumn colId="%d"><filters><filter val="%s"/></filters></filterColumn>'
        % (p["col_index"], _attr(p["selected"]))
        for p in sorted(plan, key=lambda p: p["col_index"]))
    span = _child(table, "autoFilter")
    if span:
        table = _append_into(table, span, "autoFilter", filters)
    else:
        ref = "%s:%s%d" % (top_left, re.match(r"\$?[A-Z]+", bottom_right).group(0), last)
        table = _insert_child(table, '<autoFilter ref="%s">%s</autoFilter>' % (ref, filters),
                              ("sortState", "tableColumns"))
    pkg.put(table_part, table)

    hidden = {r for r in range(first, last + 1)
              if any((p["values"][r] or "").casefold() != p["selected"].casefold() for p in plan)}
    sheet = _set_row_hidden(sheet, first, last, hidden)

    # ---- the caches: one part each, related from the workbook
    cache_rids = []
    for p in plan:
        part = pkg.free("xl/slicerCaches/slicerCache%d.xml")
        pkg.put(part, (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<slicerCacheDefinition xmlns="%s" xmlns:mc="%s" mc:Ignorable="x" xmlns:x="%s" '
            'name="%s" sourceName="%s"><extLst><x:ext uri="%s" xmlns:x15="%s">'
            '<x15:tableSlicerCache tableId="%s" column="%s"/></x:ext></extLst>'
            '</slicerCacheDefinition>'
        ) % (X14, MC, MAIN, _attr(p["cache"]), _attr(p["column"]), URI_TABLE_SLICER_CACHE,
             X15, table_id, p["column_id"]))
        _add_override(pkg, part, CT_SLICER_CACHE)
        cache_rids.append(_add_rel(pkg, "xl/workbook.xml", R_SLICER_CACHE, part))

    names = "".join('<definedName name="%s">#N/A</definedName>' % _attr(p["cache"]) for p in plan)
    span = _child(workbook, "definedNames")
    if span:
        workbook = _append_into(workbook, span, "definedNames", names)
    else:
        workbook = _insert_child(workbook, "<definedNames>%s</definedNames>" % names,
                                 _AFTER_DEFINED_NAMES)
    workbook = _add_ext(workbook, (
        '<ext uri="%s" xmlns:x15="%s"><x15:slicerCaches xmlns:x14="%s">%s</x15:slicerCaches></ext>'
    ) % (URI_WB_SLICER_CACHES, X15, X14, "".join(
        '<x14:slicerCache xmlns:r="%s" r:id="%s"/>' % (REL_NS, rid) for rid in cache_rids)))
    pkg.put("xl/workbook.xml", workbook)

    # ---- the slicers part, related from the sheet
    slicer_part = pkg.free("xl/slicers/slicer%d.xml")
    pkg.put(slicer_part, (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<slicers xmlns="%s" xmlns:mc="%s" mc:Ignorable="x" xmlns:x="%s">%s</slicers>'
    ) % (X14, MC, MAIN, "".join(
        '<slicer name="%s" cache="%s" caption="%s" style="%s" rowHeight="%d"/>'
        % (_attr(p["name"]), _attr(p["cache"]), _attr(p["caption"]), _attr(p["style"]),
           ROW_HEIGHT_EMU) for p in plan)))
    _add_override(pkg, slicer_part, CT_SLICER)
    slicer_rid = _add_rel(pkg, sheet_part, R_SLICER, slicer_part)

    # ---- the frames, in the sheet's own drawing (one is made if it has none)
    span = _child(sheet, "drawing")
    if span:
        rid = re.search(r'\s[\w.-]+:id="([^"]+)"', sheet[span[0]:span[1]]).group(1)
        drawing_part = next(tg for i, _, tg in _rels(pkg, sheet_part) if i == rid)
        drawing = pkg.text(drawing_part)
    else:
        drawing_part = pkg.free("xl/drawings/drawing%d.xml")
        drawing = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                   '<xdr:wsDr xmlns:xdr="%s" xmlns:a="%s"></xdr:wsDr>' % (XDR, A))
        _add_override(pkg, drawing_part, CT_DRAWING)
        rid = _add_rel(pkg, sheet_part, R_DRAWING, drawing_part)
        sheet = _insert_child(sheet, '<drawing xmlns:r="%s" r:id="%s"/>' % (REL_NS, rid),
                              _AFTER_DRAWING)
    ids = [int(x) for x in re.findall(r'cNvPr\b[^>]*?\bid="(\d+)"', drawing)]
    next_id = max(ids + [1]) + 1
    frames = "".join(_slicer_anchor(p["name"], next_id + k, p["anchor"])
                     for k, p in enumerate(plan))
    pkg.put(drawing_part, _insert_before_close(drawing, frames))

    sheet = _add_ext(sheet, (
        '<ext uri="%s" xmlns:x15="%s"><x14:slicerList xmlns:x14="%s">'
        '<x14:slicer xmlns:r="%s" r:id="%s"/></x14:slicerList></ext>'
    ) % (URI_SHEET_SLICER_LIST, X15, X14, REL_NS, slicer_rid))
    pkg.put(sheet_part, sheet)

    pkg.save()
