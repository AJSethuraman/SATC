"""Every tie-out this repository has recorded, counted -- with its denominator.

WHY A READER EXISTS AT ALL. `ask.answer` writes one line per attempt into each
desk's `tie-outs/attempts.jsonl`, whatever the attempt did. A store nobody reads
back is worse than no store: the firm did the work of running the desks and it
went nowhere. This is the read.

WHAT IT IS FOR, in the firm's words on 8 September 2026: *"It should state what
happened when trying to tie it out. I need info to make decisions down the
line."* The decisions are about PUBLISHERS, not about any one answer -- retire a
source, change the transport, admit a mirror -- so the counts are by host and by
verdict, and the note is shown only on the ones that did not tie out.

IT NAMES WHAT IT READ, and that is not a formality here. `tools/holes.py` printed
*"Gaps (0) -- the mechanism is live and has not fired"* on an evening when five
refusals stood in the run, because it globbed one of three stores. A count means
nothing without knowing what it was counted over, so every heading says how many
files were opened, and a desk with no store at all is listed as such rather than
being silently absent from the sum.

LINES THAT WOULD NOT PARSE ARE COUNTED, NOT DROPPED. An append-only log written
during answering can be cut mid-line by a process that died. `attempts.parse`
skips those so one bad line cannot hide the good ones, and this reports how many
it skipped -- otherwise the skipping is the same silent read the paragraph above
is about.

NO VALUES ARE PRINTED. No passage text, no client data, no questions -- see
`attempts.FIELDS`. This output goes into a repository.

    python3 tools/tieouts.py                 # every desk's store
    python3 tools/tieouts.py path/to/attempts.jsonl [...]
"""
from __future__ import annotations

import collections
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import attempts as attempts_store                           # noqa: E402

CORPUS = HERE / "corpus"


def stores(root: pathlib.Path = CORPUS) -> list[tuple[str, pathlib.Path, bool]]:
    """The record and where its store is. `(name, path, exists)`.

    STILL A LIST, AND STILL RETURNED WHEN THE STORE IS ABSENT. It walked seven
    desks until 10 September 2026 and `dec-kill` left one corpus, so the list
    has one entry — but the shape is what carries the finding that matters:
    "nothing has ever been tied out" and "everything tied out clean" are
    different results and must not render the same, which is exactly what
    omitting an absent store would do.
    """
    root = pathlib.Path(root)
    path = attempts_store.store_for(root)
    return [(root.name, path, path.exists())]


def read(paths) -> tuple[list, int, int]:
    """`(attempts, files_read, lines_skipped)` over the paths given."""
    rows, files, skipped = [], 0, 0
    for path in paths:
        path = pathlib.Path(path)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        rows += attempts_store.parse(text)
        skipped += attempts_store.unreadable(text)
        files += 1
    return rows, files, skipped


def report(root: pathlib.Path = CORPUS, paths=None) -> str:
    if paths:
        known = [(str(p), pathlib.Path(p), pathlib.Path(p).exists()) for p in paths]
    else:
        known = stores(root)
    rows, files, skipped = read(p for _n, p, ok in known if ok)

    out = ["TIE-OUTS", "=" * 8, ""]
    out += [f"Read {files} store{'' if files == 1 else 's'} of "
            f"{len(known)} looked for."]
    missing = [n for n, _p, ok in known if not ok]
    if missing:
        out += [f"No store yet: {', '.join(missing)} — nothing has been tied "
                f"out on {'it' if len(missing) == 1 else 'them'}."]
    if skipped:
        out += [f"{skipped} line(s) would not parse and are not counted below."]
    out += [""]

    if not rows:
        out += ["No attempt recorded anywhere. That is not the same as every "
                "attempt having passed — nothing has been asked to prove "
                "itself yet."]
        return "\n".join(out)

    by_verdict = collections.Counter(a.verdict for a in rows)
    out += [f"{len(rows)} attempt(s) recorded:"]
    for verdict, n in sorted(by_verdict.items(), key=lambda kv: -kv[1]):
        out += [f"  {n:>5}  {verdict}"]
    out += [""]

    out += ["By publisher — a decision about a source is made from this column,",
            "not from any one answer:"]
    by_host = collections.defaultdict(collections.Counter)
    for a in rows:
        by_host[a.host or "(no host recorded)"][a.verdict] += 1
    for host in sorted(by_host):
        counts = by_host[host]
        line = ", ".join(f"{n} {v}" for v, n in sorted(counts.items()))
        out += [f"  {host}: {sum(counts.values())} — {line}"]
    out += [""]

    failed = [a for a in rows if a.verdict != "TIED"]
    if not failed:
        out += [f"Every one of the {len(rows)} tied out. Recorded rather than "
                f"assumed."]
        return "\n".join(out)
    out += [f"What happened on the {len(failed)} that did not tie out:"]
    for a in failed:
        out += [f"  {a.at}  {a.desk}  {a.verdict}",
                f"      {a.citation}",
                f"      {a.note or '(no reason recorded)'}"]
    return "\n".join(out)


if __name__ == "__main__":                                  # pragma: no cover
    print(report(paths=sys.argv[1:] or None))
