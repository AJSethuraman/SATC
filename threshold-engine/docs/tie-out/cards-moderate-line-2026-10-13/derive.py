"""Where Moderate begins for credit cards, from the Federal Reserve's table alone.

Python's standard library only; nothing from threshold_engine. Run from this
folder:  python derive.py

Reads board-credit-cards-sa.csv (the Board's quarterly card charge-off rates)
and the repository's tests/data/cards_nco_ttm.csv, and prints:
  1. the roster: every quarter of the repository file against the four-quarter
     mean of the Board's rates;
  2. the line, step by step, from the Board's rates, exactly (Decimal) and
     as the repository file holds them (three decimals);
  3. whether any quarter kept changes score between the two.
"""
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).parent
REPO_FILE = HERE.parents[2] / "tests" / "data" / "cards_nco_ttm.csv"
CRISIS, PANDEMIC = ("2007Q4", "2012Q4"), ("2021Q3", "2023Q1")
HALF_WIDTH, STEP, Z = Decimal("0.5"), Decimal("1.0"), Decimal("2.5")
K = Decimal("1.4826")


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def label(y, q):
    return "%dQ%d" % (y, q)


board = {}
for line in open(HERE / "board-credit-cards-sa.csv"):
    if line[:1].isdigit():
        q, v = line.strip().split(",")
        board[(int(q[:4]), int(q[5]))] = Decimal(v)
keys = sorted(board)

repo = {}
for line in open(REPO_FILE):
    if line[:1].isdigit():
        d, v = line.strip().split(",")
        repo[(int(d[:4]), (int(d[5:7]) - 1) // 3 + 1)] = Decimal(v)

# 1. the roster
ttm = {}
for i in range(3, len(keys)):
    ttm[keys[i]] = sum(board[k] for k in keys[i - 3:i + 1]) / 4          # exact: rates have 2 decimals
same, half, other = [], [], []
for q, v in sorted(repo.items()):
    exact = ttm[q]
    if v == exact.quantize(Decimal("0.001")) and abs(v - exact) < Decimal("0.0005"):
        same.append(q)
    elif abs(v - exact) == Decimal("0.0005"):
        half.append((label(*q), str(exact), str(v), "up" if v > exact else "down"))
    else:
        other.append((label(*q), str(exact), str(v)))
print("1. Roster: %d quarters in the repository file" % len(repo))
print("   equal to the Board's four-quarter mean at 3 decimals:   %d" % len(same))
print("   a mean ending in 5 at the 4th decimal, rounded:         %d" % len(half))
for h in half:
    print("      %s  exact %s  file %s  (%s)" % h)
print("   otherwise different:                                   %d" % len(other))
for o in other:
    print("      %s  exact %s  file %s" % o)


# 2. the line
def line(values, name):
    qs = sorted(values)
    left = lambda q: any(a <= label(*q) <= b for a, b in (CRISIS, PANDEMIC))   # noqa: E731
    kept = {q: values[q] for q in qs if not left(q)}
    med = median(kept.values())
    changes = [values[qs[i]] - values[qs[i - 4]] for i in range(4, len(qs))
               if qs[i] in kept and qs[i - 4] in kept]
    mc = median(changes)
    move = K * median([abs(c - mc) for c in changes])
    spread = K * median([abs(v - med) for v in kept.values()])
    lines = [med - STEP * move, med - HALF_WIDTH * move, med + HALF_WIDTH * move, med + Z * spread]
    print("\n2. %s" % name)
    print("   quarters %d, kept %d (left out %s to %s and %s to %s)" % ((len(qs), len(kept)) + CRISIS + PANDEMIC))
    print("   median kept                         %s" % med)
    print("   four-quarter changes, both ends kept %d, their median %s" % (len(changes), mc))
    print("   typical yearly move = 1.4826 x median |change - %s| = %s" % (mc, move))
    print("   3 Moderate from = median - 0.5 x move = %s - 0.5 x %s = %s" % (med, move, lines[1]))
    print("   all four lines: %s" % " / ".join("%.6f" % x for x in lines))
    return kept, lines


def score(v, lines):
    if v <= 0:
        return 1
    return 1 + sum(1 for b in lines if v >= b)                              # on the line: worse


kept_e, lines_e = line(ttm, "From the Board's rates, exact four-quarter means")
kept_r, lines_r = line({q: v for q, v in repo.items()}, "From the repository file (three decimals)")

# 3. does any quarter change score?
moved = [label(*q) for q in kept_e if score(kept_e[q], lines_e) != score(kept_r[q], lines_r)]
counts = lambda kept, lines: [sum(1 for v in kept.values() if score(v, lines) == s) for s in range(1, 6)]  # noqa
print("\n3. Kept quarters per score, exact:  %s" % counts(kept_e, lines_e))
print("   Kept quarters per score, file:   %s" % counts(kept_r, lines_r))
print("   Quarters whose score differs:    %s" % (", ".join(moved) or "none"))
latest = keys[-1]
print("   Latest %s: exact %s scores %d; file %s scores %d" % (
    label(*latest), ttm[latest], score(ttm[latest], lines_e), repo[latest], score(repo[latest], lines_r)))
