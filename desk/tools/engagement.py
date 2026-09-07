"""Start an engagement's fact file, and check one that exists.

    python tools/engagement.py new alpha-2026 > ~/engagements/alpha-2026.md
    python tools/engagement.py check ~/engagements/alpha-2026.md

`new` prints a blank file carrying EVERY fact the desks currently declare, each
with the desk that asks for it named in a comment. It is generated rather than
kept as a template, because a template is a second copy of the `Records:` lines
and the copy is what goes stale: add a desk that records something new and the
blank file grows a stub for it without anybody remembering.

The file goes wherever the firm keeps its files. Not here -- `engagements.load`
refuses a path inside this plugin, which is a checkout that gets pushed.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import engagements                                          # noqa: E402


def new(ref: str) -> int:
    known = engagements.declared()
    print(f"# Engagement · {ref}")
    print()
    print("<!-- Every fact the desks record. Fill in what you know and DELETE")
    print("     the rest: a fact with no value is refused, and that is right --")
    print("     a half-written record reads exactly like a recorded one. -->")
    for name, desks in sorted(known.items()):
        print()
        print(f"## {name}")
        print()
        print(f"<!-- asked for by: {', '.join(desks)} -->")
        print("**Value:** ")
        print("**Recorded by:** ")
        print(f"**Recorded on:** {date.today().isoformat()}")
        print("**From:** ")
    return 0


def check(path: str) -> int:
    try:
        eng = engagements.load(Path(path))
    except engagements.EngagementError as exc:
        print(f"REFUSED  {exc}")
        return 1

    print(f"Engagement {eng.ref}")
    print(f"  {eng.path}")
    print()
    print("Recorded:")
    for f in eng.facts:
        print(f"  {f.name:<24} {f.value}")
        print(f"  {'':24} — {f.by}, {f.on}" + (f" · {f.source}" if f.source else ""))
    missing = engagements.gaps(eng)
    print()
    if not missing:
        print("Missing: nothing. Every fact the desks record is on file.")
        return 0
    # THE HALF THAT MATTERS, and it is printed even when it is empty above. A
    # report that lists what a file holds leaves the reader to assume the rest
    # were not needed.
    print("Missing — a desk asking for one of these will refuse:")
    for name, desks in missing.items():
        print(f"  {name:<24} asked for by {', '.join(desks)}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "new":
        return new(argv[1])
    if len(argv) == 2 and argv[0] == "check":
        return check(argv[1])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
