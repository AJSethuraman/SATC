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
    ("a copied column not found", H, "                    aud.Cells(c + 1, A_SAME_AS).Value = names(d)",
     "                    aud.Cells(c + 1, A_SAME_AS).Value = Empty", "constant_empty_and_copied"),
    ("numbers stored as text not counted", H, "                    numText = numText + 1",
     "                    numText = numText", "text_problems"),
    ("trailing spaces not counted", H, "                If Trim(s) <> s Then spaces = spaces + 1",
     "                If False Then spaces = spaces + 1", "text_problems"),
    ("the no-break space not odd", H, "        If a < 32 Or a = 160 Or a = 8203 Or a = 65279 Then",
     "        If a < 32 Or a = 8203 Or a = 65279 Then", "text_problems"),
    ("decisions lost on a second Profile", H, "    RestoreDecision aud, r, nm, kept\n", "\n",
     "keeps_the_decisions"),
    ("repeated keys not listed", H, "        If times(k) > 1 Then", "        If times(k) > 99 Then", "repeated_keys"),
    ("rows with a blank not listed", H, "        If n > 0 Then\n            out = out + 1\n            blankRows",
     "        If n > 99 Then\n            out = out + 1\n            blankRows", "repeated_keys or says_current"),
    ("Profile runs on its own sheets", H, "    If src.Name = AUDIT Or src.Name = FINAL", "    If False And src.Name = FINAL",
     "own_sheets"),
    ("the source sheet written to", H, "        aud.Cells(r, A_NAME).Value = nm\n",
     "        aud.Cells(r, A_NAME).Value = nm\n        src.Cells(2, 1).Value = 0\n", "source_alone"),
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
