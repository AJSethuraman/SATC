"""The one DIFFERS, looked at with far more shuffles -- PocketBook's side (it runs PocketBook's own code).

    python3 long_shuffle_pocketbook.py "Flag book - PocketBook.xlsx" "Flag book.csv" SHUFFLES REPEATS

PocketBook's engine is run on the Flag book with its own settings, but perm.run is caught before it deals: what it
is handed (every rate's rows, the band structure and the grid's pocket layout) is kept, and PocketBook's own
perm.run is then called again on the band structure alone, for the FICO x ASSET_CLASS / SYS_FLAG grid and Earned
before losses only, with SHUFFLES shuffles, once with the Run's own seed and then with REPEATS - 1 other seeds.
The pocket read out is FICO 746 - 921 / ASSET_CLASS 1 / Y against the rest of its band -- the pocket whose raw
p-value sets the 21 cells. Nothing in PocketBook is changed.
"""
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))
os.environ.setdefault("POCKETBOOK_MEMORY", "/tmp/credit/memory-long-shuffle.yaml")

from pocketbook import book, config as cfgmod, engine, perm  # noqa: E402
from pocketbook.ingest import read_table  # noqa: E402

BAND, SEG = "746 - 921", ("1", "Y")


def main():
    wb, csv_, shuffles, repeats = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    raw, _, _ = book.read_book(Path(wb))
    cfg = cfgmod.parse(raw)
    caught = {}
    real_run = perm.run

    def catch(n, columns, structures, shuffles_, seed, **kw):
        caught.update(n=n, columns=columns, structures=structures, seed=seed, shuffles=shuffles_)
        return 0
    perm.run = catch
    res = engine.run(cfg, read_table(Path(csv_)))
    perm.run = real_run
    # the grid, in the order the engine built it: per band, per segment, the two-way grid then its three-way one
    fico = [g for g, bname, _ in [(g, g.band, None) for g in res.grids + res.three_way] if "FICO" in str(bname)]
    print([(g.band, g.dimension) for g in res.three_way])
    grid = res.three_way[1]
    measure = next(m for m in res.measures if m.name == "contribution_rate")
    inner = [k for k, _ in grid.inner()]
    print([k for k in inner if k[0] == BAND])
    target = next(i for i, k in enumerate(inner) if k[0] == BAND and str(k[1]).endswith("SYS_FLAG Y") and str(k[1]).split()[0] in ("1", "ASSET_CLASS"))
    print("PocketBook's pocket:", inner[target], "| run seed", caught["seed"], "| run shuffles", caught["shuffles"])
    print([s.name for s in caught["structures"]])
    band_s = next(s for s in caught["structures"] if s.name.startswith("rest of the band"))
    # FICO's band structure holds FICO x CHANNEL, its split, FICO x ASSET_CLASS, its split: the fourth
    li = 3
    assert len(set(band_s.layouts[li])) == len(inner), (len(set(band_s.layouts[li])), len(inner))
    col = next(c for c in caught["columns"] if c.name == measure.name)
    out = []
    for r in range(repeats):
        seed = caught["seed"] if r == 0 else perm.seed_of("tie-out 29 Sep 2026, long shuffle", r)
        st = perm.RestGap()
        s = perm.Structure("one grid, one rate", band_s.group, [band_s.layouts[li]], {(0, measure.name): st})
        perm.run(caught["n"], [col], [s], shuffles, seed)
        a = st.answers[target]
        se = math.sqrt(a.p * (1 - a.p) / shuffles)
        out.append({"seed": "the Run's" if r == 0 else f"other {r}", "gap": a.gap, "hits": a.hits,
                    "shuffles": a.shuffles, "p": a.p, "se": se})
        print(f"  PocketBook  seed {out[-1]['seed']:9s}  gap {a.gap:+.9f}  hits {a.hits:7d} of {a.shuffles}  "
              f"p {a.p:.5f}  se {se:.5f}", flush=True)
    Path(HERE / "results" / "long-shuffle-pocketbook.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
