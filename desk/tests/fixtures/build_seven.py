"""Write the frozen inventory of the seven desk records. RUN ONCE, 10 Sep 2026.

`dec-kill` deleted `desks/`. `test_the_seven_records_became_one_corpus.py` has
to go on asserting that nothing the firm wrote was lost in the merge, and its
comparison was `record.load(each of seven)` — a directory that no longer exists.

So the inventory was written out of the working tree immediately before
`git rm -r desks/`, and this is the script that did it. It is kept beside its
output rather than deleted, because a data file nobody can see the provenance of
is a data file nobody can check: run it against any checkout that still has
`desks/` (`git show <commit>:desk/desks/...`, or the commit before the deletion)
and it reproduces the JSON byte for byte.

IT CANNOT RUN TODAY, and that is not a defect. It raises rather than writing an
empty inventory over a real one — which is the failure mode a script like this
actually has.

    cd desk && python tests/fixtures/build_seven.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

import record                                                # noqa: E402

DESKS = HERE / "desks"
OUT = Path(__file__).resolve().parent / "seven-records-2026-09-10.json"


def main() -> int:
    if not DESKS.is_dir():
        print(f"{DESKS} does not exist — the desks were deleted on 10 September "
              f"2026 (`dec-kill`). Check out a commit that still has them, or "
              f"leave {OUT.name} as it is; it is the record of what was there.")
        return 1
    records = []
    for d in sorted(DESKS.iterdir()):
        if not (d / "SUBJECTS.md").is_file():
            continue
        k = record.load(d)
        records.append({
            "name": k.name,
            "passages": [{"citation": p.citation, "chars": len(p.text)}
                         for p in k.passages],
            "positions": [[q.citation, q.position] for q in k.positions],
            "problems": [b.id for b in k.problems],
            "sources": [s.title.strip() for s in k.sources],
            "answered_by": {c: list(t) for c, t in k.answered_by.items()},
            "answered_from": {s: list(t) for s, t in k.answered_from.items()},
        })
    if len(records) != 7:
        print(f"{len(records)} records found, not 7 — refusing to write")
        return 1
    OUT.write_text(json.dumps({
        "what": "The seven desk records as they stood on 10 September 2026, the "
                "day `dec-kill` deleted them. Written by "
                "tests/fixtures/build_seven.py from the working tree, "
                "immediately before `git rm -r desks/`.",
        "why": "test_the_seven_records_became_one_corpus.py asserts that nothing "
               "the firm wrote was lost in the merge. Its subject is a directory "
               "that no longer exists, so the inventory it compares against is "
               "frozen here rather than re-derived. A frozen inventory is honest "
               "where a frozen assertion would be a test nobody can fail: this "
               "is a record of what was, and the corpus is checked against it.",
        "commit": "the working tree at desk 0.21.0 + the one-corpus migration",
        "records": records,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} — {sum(len(r['passages']) for r in records)} passages, "
          f"{sum(len(r['positions']) for r in records)} positions, "
          f"{sum(len(r['problems']) for r in records)} problems")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
