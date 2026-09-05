"""Check the checker: plant known-wrong values and confirm it says DIFFERS.

The bank verifier has already produced a mass false result once -- 7,598
balances reported as differences because I divided by a thousand twice. It was
declared fixed when the score went to zero, and a score going to zero is exactly
what a checker that has stopped checking also produces.

So: corrupt the filing side by a known amount and confirm the comparison goes
red, at several magnitudes and on several kinds of field. A checker that cannot
be made to fail is not passing.

Nothing is written back. The planted values live in memory only.
"""
import json
import pathlib
import re
import sys

CS = pathlib.Path(r"C:\Users\ajish\SATC-cs\credit-suite")
SB = pathlib.Path(r"C:\Users\ajish\AppData\Local\Temp\claude"
                  r"\C--Users-ajish-SATC\261f7248-3cbc-4aa2-aacf-e4ff9181778a\scratchpad")
sys.path.insert(0, str(CS / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from credit_suite.sources.fdic import filing as F                # noqa: E402
from credit_suite.sources.fdic import provenance_seed as PS      # noqa: E402

PROV = {r[0]: r[3] for r in PS.ALL_ROWS}
FACTS = json.loads((SB / "filings" / "facts-17534-2026-06-30.json").read_text())
LANDED = json.loads((SB / "bank_landed.json").read_text())["17534"]

#: (field, what we plant, what a correct checker must say)
CASES = [
    ("ASSET", "unchanged", "TIES"),
    ("ASSET", "off by 1 thousand", "DIFFERS"),
    ("ASSET", "off by 1 percent", "DIFFERS"),
    ("ASSET", "transposed digits", "DIFFERS"),
    ("DEP", "off by 1 thousand", "DIFFERS"),
    ("LNLSGR", "off by 1 thousand", "DIFFERS"),
    ("LNCRCD", "off by 1 thousand", "DIFFERS"),
    ("P3CI", "off by 1 thousand", "DIFFERS"),
    ("NACONOTH", "off by 1 thousand", "DIFFERS"),
    ("DEPUNINS", "sign flipped", "DIFFERS"),
]


def compare(field, facts):
    """Exactly the comparison the verifier makes for a filed line."""
    expr = PROV.get(field, "")
    parsed = F.parse_mdrm(expr)
    if parsed is None:
        return "NO CITATION", None
    v, _used = F.filed_value(facts, parsed)
    if v is None:
        return "NOT ON FILING", None
    ours = LANDED.get(field)
    if ours is None:
        return "NOT LANDED", None
    return ("TIES" if abs(float(ours) - float(v)) < 0.51 else "DIFFERS"), v


def plant(field, how):
    """A copy of the filing with the line the checker ACTUALLY READS corrupted.

    The first version of this harness corrupted whichever code it could find in
    the citation string. For a line written "RCON2170 (RCFD2170 031)" that is
    the RCON code -- and the checker reads the RCFD one, because these banks
    file form 031. So three planted corruptions never reached the value under
    test and the harness reported the checker as blind. It was the harness.

    `filed_value` returns the codes it used. Corrupt those.
    """
    facts = dict(FACTS)
    expr = PROV.get(field, "")
    parsed = F.parse_mdrm(expr)
    if parsed is None:
        return None
    _v, used = F.filed_value(facts, parsed)
    codes = [c for c in re.findall(r"[A-Z]{4}[A-Z0-9]{4}", used or "")
             if c in facts]
    if not codes:
        return None
    c = codes[0]
    v = float(facts[c])
    if how == "unchanged":
        return facts
    if how == "off by 1 thousand":
        facts[c] = v + 1000
    elif how == "off by 1 percent":
        facts[c] = v * 1.01
    elif how == "transposed digits":
        # Swap the first PAIR OF DIFFERENT digits. The first version swapped
        # positions 1 and 2 blindly, and on 188555486 those are both 8 -- a
        # mutation that changes nothing looks exactly like a checker that
        # notices nothing.
        s = list(str(int(abs(v))))
        for i in range(len(s) - 1):
            if s[i] != s[i + 1]:
                s[i], s[i + 1] = s[i + 1], s[i]
                break
        facts[c] = float("".join(s))
    elif how == "sign flipped":
        facts[c] = -v
    return facts


print("%-11s %-20s %-9s %-9s %s" % ("field", "planted", "wanted", "got", "verdict"))
killed = survived = 0
for field, how, want in CASES:
    facts = plant(field, how)
    if facts is None:
        print("%-11s %-20s  no resolvable code -- SKIPPED" % (field, how))
        continue
    got, _v = compare(field, facts)
    ok = got == want
    killed += ok
    survived += (not ok)
    print("%-11s %-20s %-9s %-9s %s"
          % (field, how, want, got, "ok" if ok else "*** CHECKER IS BLIND ***"))

print("\n%d of %d planted cases behaved correctly" % (killed, killed + survived))

# ---- the specific bug that produced the mass false result -------------------
print("\nthe unit bug that once reported 7,598 false differences:")
v, _ = F.filed_value(FACTS, F.parse_mdrm(PROV["ASSET"]))
ours = LANDED["ASSET"]
print("   filed_value returns          %s" % v)
print("   the workbook holds           %s" % ours)
print("   equal, so no division needed: %s" % (abs(float(ours) - float(v)) < 0.51))
print("   dividing again would give    %s  -> DIFFERS (the old bug)" % (v / 1000.0))

# ---- how much of the tie count is zero against zero -------------------------
rows = json.loads((SB / "bank_history_rows.json").read_text())
ties = [r for r in rows if r["verdict"] == "TIES"]
zero = [r for r in ties if float(r["ours"]) == 0 and float(r["theirs"] or 0) == 0]
print("\nof %d bank ties, %d are zero matched against zero (%.1f%%)"
      % (len(ties), len(zero), 100.0 * len(zero) / len(ties)))
print("   they are true, and they are the weakest form of agreement.")
