"""A low-default book: the walk's synthetic book with every bad rate cut to a sixth.

    WALK=<scratch> CUBE_SRC=<frozen src> python3.12 lowdefault.py [N]

Walk 5 couldn't check a book at a 1 to 2% bad rate, where the suggested floor and the
fallback matter most. This writes $WALK/lowdef/Consumer book low.csv from synth.make_rows
with p 0.03 -> 0.005, 0.06 -> 0.01 and the planted pocket's 0.30 -> 0.05 (the debt and
asset-class multipliers unchanged). N defaults to 5,000 loans."""
import csv, inspect, os, sys
from pathlib import Path
sys.path.insert(0, os.environ["CUBE_SRC"])
from origination_cube import synth  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
src = (inspect.getsource(synth.make_rows).replace("p = 0.03 if fico >= 680 else 0.06", "p = 0.005 if fico >= 680 else 0.01")
       .replace("p = 0.30", "p = 0.05"))
assert "0.005" in src and "0.05\n" in src
ns = {"CHANNELS": synth.CHANNELS}
exec("import random\n" + src, ns)
out = Path(os.environ["WALK"]) / "lowdef" / "Consumer book low.csv"
out.parent.mkdir(exist_ok=True)
rows = ns["make_rows"](n, 31)
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=synth.COLUMNS)
    w.writeheader()
    w.writerows(rows)
bad = sum(1 for r in rows if r["BAD_FLAG"] == 1)
print(out, n, "loans,", bad, "bad", f"({bad / n:.2%})")
