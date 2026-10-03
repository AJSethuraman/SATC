"""Diagnosis only, on PocketBook's side (it runs PocketBook's own engine): one Benjamini-Hochberg family's raw
p-values as PocketBook works them out, to set beside this road's. Used for the Flag book's one DIFFERS (Pockets,
Split by SYS_FLAG, Earned before losses: 21 pockets that share one adjusted p-value).

    python3 diagnose_family.py "Flag book - PocketBook.xlsx" "Flag book.csv" "FICO x ASSET_CLASS / SYS_FLAG" \
        contribution_rate WORK/expected-flag-families.json "Earned before losses"
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))
os.environ.setdefault("POCKETBOOK_MEMORY", "/tmp/credit/memory-diagnose.yaml")

from pocketbook import book, config as cfgmod, engine  # noqa: E402
from pocketbook.ingest import read_table  # noqa: E402


def main():
    wb, csv_, grid, key, fams, measure = sys.argv[1:7]
    raw, problems, _ = book.read_book(Path(wb))
    cfg = cfgmod.parse(raw)
    captured = {}
    real_adjust = engine.adjust

    def spy(ps, how):
        out = real_adjust(ps, how)
        captured.setdefault(len(ps), []).append((list(ps), list(out)))
        return out
    engine.adjust = spy
    res = engine.run(cfg, read_table(Path(csv_)))
    mine = sorted(json.load(open(fams))[f"{grid}|{measure}|p_band"], key=lambda t: t[2])
    print("this road, the family's largest eight raw (adjusted):", [(round(r, 4), round(a, 4)) for *_, r, a in mine[-8:]])
    for ps, out in (x for got in captured.values() for x in got):
        srt = sorted((p, o) for p, o in zip(ps, out) if p is not None)
        if len(srt) == len(mine) and any(o is not None and abs(o - 0.981864500117153) < 1e-9 for _, o in srt):
            print("PocketBook, the family's largest eight raw (adjusted):", [(round(p, 4), round(o, 4)) for p, o in srt[-8:]])


if __name__ == "__main__":
    main()
