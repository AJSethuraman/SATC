"""Planted bugs: each breaks one guard in a macro, and the tests must go red. A bug the tests miss means a test is
missing. Run from excel-macros/: python tools/mutation_check.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

H = "macros/Hygiene.bas"
#: (name, file, old text that must occur exactly once, new text, pytest -k selector)
MUTATIONS = [
    ("case ignored when counting distinct values", H, '    KeyOf = "k" & s & ChrW(1) & m', '    KeyOf = "k" & s',
     "case_apart"),
    ("flag ones and zeros swapped", H, "                v(i, 1) = 1\n                ones = ones + 1",
     "                v(i, 1) = 0\n                ones = ones + 1", "flag_made"),
    ("a column with no decision built anyway", H,
     '            problems = AddProblem(problems, nProblems, nm & ": no decision in Keep?")',
     "            nDrop = nDrop", "no_decision"),
    ("two kept columns may share a name", H,
     '                If Lookup(names, LCase(outName(nKeep))) <> 0 Then', "                If False Then", "one_name"),
    ("the status never goes out of date", H, '"))>0),""Out of date', '"))>9999),""Out of date', "out_of_date"),
    ("a copied column not found", H, "                    WriteCell aud.Cells(c + 1, A_SAME_AS), names(d)",
     "                    WriteCell aud.Cells(c + 1, A_SAME_AS), Empty", "constant_empty_and_copied"),
    ("numbers stored as text not counted", H, "                    numText = numText + 1",
     "                    numText = numText", "text_problems"),
    ("trailing spaces not counted", H, "                If Trim(s) <> s Then spaces = spaces + 1",
     "                If False Then spaces = spaces + 1", "text_problems"),
    ("the no-break space not odd", H, "        If a < 32 Or a = 160 Or a = 8203 Or a = 65279 Then",
     "        If a < 32 Or a = 8203 Or a = 65279 Then", "text_problems"),
    ("decisions lost on a second Profile", H, "        RestoreDecision aud, r, names(c), kept\n", "\n",
     "keeps_the_decisions"),
    ("repeated keys not listed", H, "        If times(k) > 1 Then", "        If times(k) > 99 Then", "repeated_keys"),
    ("rows with a blank not listed", H, "        If n > 0 Then\n            out = out + 1\n            blankRows",
     "        If n > 99 Then\n            out = out + 1\n            blankRows", "repeated_keys or says_current"),
    ("Profile runs on its own sheets", H, "    If src.Name = AUDIT Or src.Name = FINAL", "    If False And src.Name = FINAL",
     "own_sheets"),
    # the review of 5 Oct 2026
    ("text Excel would re-read written plain", H, "    If VarType(x) = vbString Then cell.NumberFormat = \"@\"",
     "    If False Then cell.NumberFormat = \"@\"", "reread"),
    ("a data column's re-read text written plain", H,
     "                ws.Cells(i - LBound(v, 1) + 2, k).NumberFormat = \"@\"\n",
     "\n", "reread"),
    ("a text-only column not formatted as Text", H,
     "    If allText Then ws.Range(ws.Cells(2, k), ws.Cells(n + 1, k)).NumberFormat = \"@\"",
     "    If False Then ws.Range(ws.Cells(2, k), ws.Cells(n + 1, k)).NumberFormat = \"@\"", "reread"),
    ("columns sharing a name merged into one", H, "        ElseIf Lookup(seen, \"t\" & LCase(h)) <> 0 Then",
     "        ElseIf False Then", "sharing_a_name"),
    ("every row of a repeated key listed", H, "                If times(k) <= ROWS_LISTED Then rowsOf(k)",
     "                If True Then rowsOf(k)", "twenty_rows"),
    ("a one-cell block read as a scalar", H, "    If r1 = r2 And c1 = c2 Then\n",
     "    If False Then\n", "one_data_row"),
    ("columns found from row 1 only", H,
     "    Set f = ws.Cells.Find(What:=\"*\", LookIn:=xlFormulas, SearchOrder:=xlByColumns, SearchDirection:=xlPrevious)",
     "    Set f = ws.Rows(1).Find(What:=\"*\", LookIn:=xlFormulas, SearchOrder:=xlByColumns, SearchDirection:=xlPrevious)",
     "blank_heading"),
    ("the number 1 and the text 1 one value", H, '        TypedText = "t" & CStr(x)', '        TypedText = "n" & CStr(x)',
     "two_values"),
    ("IsNumeric back for numbers as text", H, "                If LooksNumeric(Trim(s)) Then",
     "                If IsNumeric(Trim(s)) Then", "only_what_reads"),
    ("keys compared untrimmed", H, "            s = Trim(CellText(data(r, keyCol)))",
     "            s = CellText(data(r, keyCol))", "compared_trimmed"),
    ("the source sheet written to", H, "        WriteCell aud.Cells(r, A_NAME), names(c)\n",
     "        WriteCell aud.Cells(r, A_NAME), names(c)\n        src.Cells(2, 1).Value = 0\n", "source_alone"),
]


def main() -> int:
    missed = []
    for name, f, old, new, sel in MUTATIONS:
        text = Path(f).read_text(encoding="utf-8")
        if text.count(old) != 1:
            print(f"BROKEN ENTRY ({text.count(old)} matches): {name}")
            missed.append(name)
            continue
        Path(f).write_text(text.replace(old, new), encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "-k", sel,
                                "tests"], capture_output=True, text=True)
        finally:
            Path(f).write_text(text, encoding="utf-8")
        caught = r.returncode == 1
        print(("caught " if caught else "MISSED ") + name, flush=True)
        if not caught:
            missed.append(name)
    print(f"{len(MUTATIONS) - len(missed)} of {len(MUTATIONS)} planted bugs caught")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
