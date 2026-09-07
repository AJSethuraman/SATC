"""What nothing can answer — the holes, and the gaps that are not holes.

THE FIRM, 7 September 2026, cutting a design down to what it should always have
been: *"what's the simplest thing? like the desk can simply ask for info, if we
don't have it and if we do not (and it the answer can't be tied to some data
point) it's a hole in what we need to know"*.

That is two states and the engine already tells them apart. What it did not have
is anywhere to READ THEM OUT, so the rarer and more valuable of the two sat in a
queue of thirty entries with nothing pointing at it.

    A GAP  the desk asked for a fact, there is somewhere to record it, and this
           engagement has not.                       `context_not_on_file`
           Fixed by a preparer filling it in.

    A HOLE the desk asked for a fact and there is NOWHERE to record it. Not in
           this engagement -- anywhere.              `no_field_for_this_fact`
           Fixed by the firm deciding the fact exists at all.

The second is the one the whole mechanism is for, and it is the firm's own
reasoning from 6 September: *"if the follow up has no answer we know there's a
legit hole to fix because the accountant or firm never assigned it up front...
What if this mattered only sometimes and we never even made a field for it."*

NO VALUES ARE PRINTED, ever. A hole is the NAME of a fact nobody decided to
record and the position that wanted it; a gap is the name of a fact this
engagement does not carry. Neither needs the client's answer, and this output
goes into a repository.

    python3 tools/holes.py                 # every queue under unfiled/
    python3 tools/holes.py path/to/queue.md
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
for p in (str(HERE), str(HERE / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import unsupported                                          # noqa: E402

HOLE, GAP = "no_field_for_this_fact", "context_not_on_file"


def read(paths) -> list:
    out = []
    for p in paths:
        out.extend(unsupported.parse(p.read_text(encoding="utf-8")))
    return out


def report(entries: list) -> str:
    holes = [u for u in entries if u.failed_because == HOLE]
    gaps = [u for u in entries if u.failed_because == GAP]
    out = [f"# Holes and gaps — {len(entries)} refusals read", ""]

    out += [f"## Holes ({len(holes)})", "",
            "A fact a desk needed and **nothing anywhere can record**. Fixed by "
            "deciding the fact exists at all, which is the firm's and nobody "
            "else's.", ""]
    if not holes:
        # NOT SILENCE. An empty list here is a real finding -- it says no
        # ratified position has yet named a fact with no field -- and a report
        # that prints nothing reads as a report that failed to run.
        out += ["**None recorded.** No position has asked for a fact that has "
                "nowhere to live. The mechanism is live and has not fired.", ""]
    for u in holes:
        out += [f"**{u.needs_field or '(unnamed)'}** — asked for by "
                f"{u.asked_by or '(unnamed position)'}",
                "",
                f"> {u.question}", "",
                f"`{u.id}` · recorded {u.recorded}"
                + (f" · {u.model}" if u.model else ""), ""]

    out += [f"## Gaps ({len(gaps)})", "",
            "A fact there IS somewhere to record, that this engagement has not. "
            "Fixed by a preparer filling it in — not a hole.", ""]
    if not gaps:
        out += ["**None recorded.**", ""]
    for u in gaps:
        out += [f"- `{u.id}` {u.question}", ""]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    paths = ([pathlib.Path(a) for a in argv] if argv
             else sorted((HERE / "unfiled").glob("*.md")))
    missing = [p for p in paths if not p.is_file()]
    if missing:
        print("no queue at " + ", ".join(str(p) for p in missing))
        return 1
    if not paths:
        print("no queue files under unfiled/ — nothing has been refused yet")
        return 0
    print(report(read(paths)))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
