"""Whole-column references to the Run's hidden tables, bounded at the table's last row before the workbook is saved.

The firm, 30 Sep 2026: the workbook "takes quite some time to open particularly in the last stretch of loading".
openpyxl writes no calculated values, so Excel works out every formula as it opens, and a formula reading a whole
column ('_views'!$B:$ZZ is a million rows by 701 columns) is one Excel has to track over the whole column. The
result tabs are written before the hidden tables they read are finished, so they are written with whole columns
and bounded here, once every table is written.

Only the tables a Run writes afresh (`TABLES`) are bounded, and only at the Run that wrote them: Set up rewrites
the tabs the analyst fills in and leaves these alone, so a bound never goes stale. Every row a formula can reach is
inside the bound: each row number comes from a MATCH over the same table's keys, so it is a row the table has, and
a row past the bound was blank before as it is now. The columns are left as they were. Every number reads the same,
which tests/test_speed_2026_09_30.py checks cell by cell in a calculated copy.
"""

from __future__ import annotations

import re

#: the Run's hidden tables whose whole columns other tabs read, rewritten at every Run
TABLES = ("_views", "_pockets")
LAST_ROW = 1048576
#: sheets not read through: Look's 50,000 cells hold no reference to the tables, and Record keeps its lines word
#: for word as the Run worked them out (a dozen COUNTIFS, which Excel limits to the used rows anyway)
SKIP = ("_look", "_dots", "Record")

_WHOLE = re.compile(r"(?P<sheet>'(?P<quoted>[^']+)'|(?P<bare>[A-Za-z_][\w.]*))!"
                    r"\$(?P<a>[A-Z]{1,3})(?P<ra>\$\d+)?:\$(?P<b>[A-Z]{1,3})(?P<rb>\$\d+)?(?![\w$(])")


def bound(wb) -> int:
    """Every whole-column reference to a table in TABLES, and every name over one to its last row (1048576), made
    to end at the table's last row. Returns how many formulas, rules, lists and names changed."""
    last = {t: max(wb[t].max_row, 1) for t in TABLES if t in wb.sheetnames}
    if not last:
        return 0

    def fix(text):
        if not isinstance(text, str) or "!" not in text:
            return text

        def sub(m):
            name = m.group("quoted") or m.group("bare")
            ra, rb = m.group("ra"), m.group("rb")
            if name not in last or (ra, rb) != (None, None) and (ra is None or rb != f"${LAST_ROW}"):
                return m.group(0)                             # another sheet, or already bounded
            top = int(ra[1:]) if ra else 1
            return f"{m.group('sheet')}!${m.group('a')}${top}:${m.group('b')}${max(last[name], top)}"
        return _WHOLE.sub(sub, text)

    changed = 0
    for ws in wb.worksheets:
        if ws.title in last or ws.title in SKIP:
            continue
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, str) and v.startswith("=") and "!$" in v:
                    got = fix(v)
                    if got != v:
                        c.value = got
                        changed += 1
        for rng in ws.conditional_formatting:
            for rule in rng.rules:
                if rule.formula:
                    got = [fix(f) for f in rule.formula]
                    if got != list(rule.formula):
                        rule.formula = got
                        changed += 1
        for dv in ws.data_validations.dataValidation:
            for k in ("formula1", "formula2"):
                v = getattr(dv, k)
                if v and fix(v) != v:
                    setattr(dv, k, fix(v))
                    changed += 1
    for name in list(wb.defined_names):
        dn = wb.defined_names[name]
        got = fix(dn.attr_text)
        if got != dn.attr_text:
            dn.attr_text = got
            changed += 1
    return changed
