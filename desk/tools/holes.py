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

REFUSALS ARE RECORDED IN THREE PLACES AND THIS READ ONE OF THEM. Written on
7 September, it globbed `unfiled/*.md` -- the queue a human files at close --
and nothing else. It therefore printed **Gaps (0), None recorded** on an evening
when five `context_not_on_file` refusals stood in the latest run, and the
document pointing the firm at it quoted that zero as a finding. The three:

    unfiled/*.md                  filed by hand at close. Durable
    desks/*/unsupported/*.md      filed by `ask.answer` as it refuses. Durable
    runs/<latest>/served.json     the last measured run. LIVE, and it moves

THE DURABLE QUEUES AND THE LIVE RUN ARE NOT SUMMED, and the separation is the
same one `run-down-a-question` already draws: the queue is every hole ever
found, holes get filled, and a total across both counts a closed hole twice. So
each is reported under its own heading, with what it was read from named -- a
count means nothing without the denominator, and "none recorded" means nothing
without knowing what was looked at.

ONLY THE LATEST RUN. An older run is a photograph of a record that has since
moved; six of the queue's eleven `authority_absent` gaps were answered within
two days of being written down.

NO VALUES ARE PRINTED, ever. A hole is the NAME of a fact nobody decided to
record and the position that wanted it; a gap is the name of a fact this
engagement does not carry. Neither needs the client's answer, and this output
goes into a repository.

    python3 tools/holes.py                 # every store, named
    python3 tools/holes.py path/to/queue.md path/to/served.json
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
for p in (str(HERE), str(HERE / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import unsupported                                          # noqa: E402

HOLE, GAP = "no_field_for_this_fact", "context_not_on_file"

#: The durable stores are reported together; the live run stands apart. Two
#: headings, never one number over both -- see the module docstring.
DURABLE, LIVE = "durable", "live"


@dataclasses.dataclass(frozen=True)
class Entry:
    """One refusal, from whichever store held it.

    A THIN SHAPE ON PURPOSE. `Unsupported` and a run's JSON row disagree about
    almost everything -- ids, dates, which model answered -- and the report
    needs four things from both. Converting at the edge keeps the branching in
    one place instead of in every line that prints.

    `fact` is the missing fact and `by` the position that asked for it. Both are
    blank where the store did not keep them, and a blank SAYS SO in the output
    rather than being filled in from the refusal's prose: `detail` names the
    fact in a sentence, and reading it back out would be inferring.
    """

    failed_because: str
    question: str
    ref: str = ""
    where: str = ""
    fact: str = ""
    by: str = ""
    recorded: str = ""
    model: str = ""
    desk: str = ""


def _from_queue(u, where: str) -> Entry:
    return Entry(failed_because=u.failed_because, question=u.question,
                 ref=u.id, where=where, fact=u.needs_field, by=u.asked_by,
                 recorded=u.recorded, model=u.model)


def _from_run(row: dict, where: str) -> Entry:
    return Entry(failed_because=row.get("reason", ""),
                 question=row.get("question", ""),
                 ref="Q%s" % row.get("q", "?"), where=where,
                 # ABSENT ON A RUN RECORDED BEFORE THE WRITER KEPT THEM, and
                 # left blank rather than recovered from `detail`.
                 fact=row.get("fact", ""), by=row.get("by_position", ""),
                 desk=row.get("desk", ""))


def stores(root: pathlib.Path | None = None) -> list[tuple[str, str, object]]:
    """Every place a refusal is recorded, newest run last.

    Returned rather than read so the report can NAME WHAT IT LOOKED AT. A store
    that exists and is empty and a store that was never opened are different
    findings, and the first version of this could not tell them apart.
    """
    root = root or HERE
    found: list[tuple[str, str, object]] = []
    for p in sorted((root / "unfiled").glob("*.md")):
        found.append((DURABLE, _where(p, root), p))
    for d in sorted((root / "desks").iterdir()) if (root / "desks").is_dir() else []:
        for p in sorted((d / "unsupported").glob("*.md")):
            found.append((DURABLE, _where(p, root), p))
    runs = sorted(p for p in (root / "runs").glob("*asked-*")
                  if (p / "served.json").is_file())
    if runs:
        p = runs[-1] / "served.json"
        found.append((LIVE, _where(p, root), p))
    return found


def _where(path, root) -> str:
    """A path as it appears IN A DOCUMENT A PERSON READS. Forward slashes, on
    every platform.

    `str(Path)` uses the platform separator, and on the firm's own Windows
    machine this report printed `desks\\fixed-assets\\unsupported\\forge.md`
    and a line reading `runs\\...` where the prose says `runs/`. Found by the
    desk running this suite there on 8 September 2026 -- six failures, three of
    them this one cause. `os.sep` leaking into a human's document is not a test
    problem; the test was reporting a real defect in what the reader sees.
    """
    return pathlib.Path(path).relative_to(root).as_posix()


def read(paths) -> list[Entry]:
    """Read the given paths, dispatching on suffix. Kept for callers that
    already know what they want; `stores()` is the front door."""
    out: list[Entry] = []
    for p in paths:
        out.extend(_read_one(p, pathlib.Path(p).as_posix()))
    return out


def _read_one(path, where: str) -> list[Entry]:
    path = pathlib.Path(path)
    if path.suffix == ".json":
        rows = json.loads(path.read_text(encoding="utf-8"))
        return [_from_run(r, where) for r in rows if not r.get("served")]
    return [_from_queue(u, where)
            for u in unsupported.parse(path.read_text(encoding="utf-8"))]


def _entries(items) -> list[Entry]:
    """Accept `Entry`, or `Unsupported` straight from `unsupported.parse`."""
    return [i if isinstance(i, Entry) else _from_queue(i, "") for i in items]


def _holes(out: list[str], holes: list[Entry]) -> None:
    out += [f"### Holes ({len(holes)})", "",
            "A fact a desk needed and **nothing anywhere can record**. Fixed by "
            "deciding the fact exists at all, which is the firm's and nobody "
            "else's.", ""]
    if not holes:
        # NOT SILENCE. An empty list here is a real finding -- it says no
        # ratified position has yet named a fact with no field -- and a report
        # that prints nothing reads as a report that failed to run. It is only
        # a finding about the stores named above it, which is why they are.
        out += ["**None recorded** in what was read. No position has asked for "
                "a fact that has nowhere to live.", ""]
    for u in holes:
        chain = (f"asked for by {u.by}" if u.by
                 else "**the position that asked is not recorded here**")
        out += [f"**{u.fact or '(field not recorded)'}** — {chain}", "",
                f"> {u.question}", "",
                f"`{u.ref}`" + (f" · {u.desk}" if u.desk else "")
                + (f" · recorded {u.recorded}" if u.recorded else "")
                + (f" · {u.model}" if u.model else ""), ""]


def _gaps(out: list[str], gaps: list[Entry]) -> None:
    out += [f"### Gaps ({len(gaps)})", "",
            "A fact there IS somewhere to record, that this engagement has not. "
            "Fixed by a preparer filling it in — not a hole.", ""]
    if not gaps:
        out += ["**None recorded** in what was read.", ""]
    for u in gaps:
        named = f" — needs `{u.fact}`" if u.fact else ""
        out += [f"- `{u.ref}`"
                + (f" {u.desk}" if u.desk else "") + named, f"  {u.question}", ""]


def report(items, read_from: list[tuple[str, str, int]] | None = None) -> str:
    """Holes first, gaps second, durable and live never summed."""
    entries = _entries(items)
    # PARTITIONED BY WHERE IT CAME FROM, not by comparing entries: two
    # identical refusals, one filed and one from tonight's run, are the normal
    # case and an equality test would drop the durable one.
    def _is_live(e):
        return bool(e.where) and e.where.endswith(".json")

    live = [e for e in entries if _is_live(e)]
    durable = [e for e in entries if not _is_live(e)]
    out = [f"# Holes and gaps — {len(entries)} refusals read", ""]

    if read_from is not None:
        out += ["## What was read", ""]
        if not read_from:
            # A REPORT OVER NOTHING IS NOT A CLEAN REPORT. Said first, because
            # every zero below it would otherwise read as an all-clear.
            out += ["**Nothing.** No store was found — every count below is a "
                    "count of an empty read, not a finding.", ""]
        for kind, where, n in read_from:
            note = "the latest run — live, and it moves" if kind == LIVE else "durable"
            out += [f"- `{where}` — {n} refusals ({note})"]
        out += [""]

    out += ["## Durable — filed and kept", ""]
    _holes(out, [e for e in durable if e.failed_because == HOLE])
    _gaps(out, [e for e in durable if e.failed_because == GAP])

    out += ["## Live — the latest run", "",
            "Not added to the durable counts above. The queue is every hole "
            "ever found and holes get filled; a total over both counts a closed "
            "one twice.", ""]
    _holes(out, [e for e in live if e.failed_because == HOLE])
    _gaps(out, [e for e in live if e.failed_because == GAP])
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if argv:
        paths = [pathlib.Path(a) for a in argv]
        missing = [p for p in paths if not p.is_file()]
        if missing:
            print("no queue at " + ", ".join(x.as_posix() for x in missing))
            return 1
        found = [(LIVE if p.suffix == ".json" else DURABLE, p.as_posix(), p)
                 for p in paths]
    else:
        found = stores()

    entries: list[Entry] = []
    read_from: list[tuple[str, str, int]] = []
    for kind, where, path in found:
        got = _read_one(path, where)
        entries.extend(got)
        read_from.append((kind, where, len(got)))
    print(report(entries, read_from))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
