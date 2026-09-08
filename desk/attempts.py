"""Every tie-out attempt, and what it did. Kept because the FAILURES matter.

THE FIRM, 8 September 2026, when a tie-out was still being treated as a check
the engine ran on a finished answer: *"It should state what happened when trying
to tie it out. I need info to make decisions down the line."*

That sentence is about the future, not about the answer in front of anybody. One
answer that could not reach a publisher is a shrug. Forty of them against the
same host is a decision -- retire the source, change the transport, admit a
mirror -- and it is a decision nobody can make if each attempt vanishes into an
answer nobody kept. So all three verdicts are recorded, not just the ones that
change what gets served:

    TIED        the words were there. Recorded, and it is not noise: a source
                that ties out for months and then stops is only visible if the
                months were written down.
    DIFFERS     the publisher no longer carries it. The answer was withdrawn.
    COULD NOT   we never reached the publisher. The answer may well have stood.

WHAT IS NEVER WRITTEN HERE. No passage text, no client data, no question. A
citation, a verdict, a moment, the host we asked and the note the proof carried
-- which is what a decision about a PUBLISHER needs and no more. `tools/holes.py`
draws the same line for the same reason: this output goes into a repository.

THE NOTE IS THE ONE FREE-TEXT FIELD and it comes from `proving`, which builds it
from an exception's type and message or from its own sentences. Nothing a
publisher serves reaches it, and `_flat` keeps it to one line so a document
cannot be smuggled through a store that is read back as records.

ONE LINE PER ATTEMPT, APPEND-ONLY. JSON Lines, because a reader wants counts by
verdict and by host, an interrupted write costs one line rather than the file,
and `desks/fixed-assets/runs/2026-09-04/forge.jsonl` already established the
shape here.
"""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path

#: Where a desk's attempts live. Beside `unsupported/`, which is the other
#: durable store `tools/holes.py` reads, and named for what it holds.
STORE = ("tie-outs", "attempts.jsonl")

#: The fields, in the order a reader wants them. Anything else on a `Proof` --
#: the digest, the byte count, the matched length -- belongs to ONE answer and
#: is evidence for that answer's reader. This store is about the PUBLISHER over
#: time, and carrying the rest would invite it to be read as a proof it is not.
FIELDS = ("at", "desk", "citation", "verdict", "host", "note")


@dataclasses.dataclass(frozen=True)
class Attempt:
    """One tie-out, as it will be counted later."""
    at: str
    desk: str
    citation: str
    verdict: str
    host: str = ""
    note: str = ""


def _flat(value: str, limit: int = 300) -> str:
    """One line, bounded. A note is a sentence, not a document."""
    return " ".join(str(value or "").split())[:limit]


def _host(url: str) -> str:
    """The host we asked, not the path. See `proving._host`.

    THE PATH IS DROPPED ON PURPOSE. A decision made from this store is about a
    publisher -- reachable or not, still carrying its own text or not -- and a
    per-page count would split one publisher across a hundred rows and hide it.
    """
    import urllib.parse
    host = urllib.parse.urlsplit(url or "").hostname or ""
    return host.lower().removeprefix("www.")


def from_proof(proof, desk: str = "") -> Attempt:
    """An attempt from a `proving.Proof`. Lossy, deliberately -- see FIELDS."""
    return Attempt(
        at=_flat(getattr(proof, "fetched_at", "")) or datetime.now(timezone.utc)
        .isoformat(timespec="seconds"),
        desk=_flat(desk),
        citation=_flat(getattr(proof, "citation", "")),
        verdict=_flat(getattr(proof, "verdict", "")),
        host=_host(getattr(proof, "url", "")),
        note=_flat(getattr(proof, "note", "")))


def append(path: Path, attempt: Attempt) -> Path:
    """Add one line. Creates the store; never rewrites what is already there."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dataclasses.asdict(attempt),
                            ensure_ascii=False, sort_keys=True) + "\n")
    return path


def parse(text: str) -> list[Attempt]:
    """Read a store back. A line that will not parse is SKIPPED, not raised.

    An append-only log written during answering can be truncated mid-line by a
    process that died, and a reader that raised on it would make one bad line
    hide every good one -- which is the opposite of what a store kept for
    later decisions is for. The count a reader prints is of what it could read,
    and `unreadable` says how much it could not.
    """
    out = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(Attempt(**{f: _flat(row.get(f, "")) for f in FIELDS}))
    return out


def unreadable(text: str) -> int:
    """How many non-blank lines `parse` had to skip. Reported, never hidden."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return len(lines) - len(parse(text))


def store_for(desks: Path, desk_name: str) -> Path:
    return Path(desks).joinpath(desk_name, *STORE)


def record(desks: Path, desk_name: str, proof) -> Path:
    """The one call `ask.answer` makes. Whatever the verdict was."""
    return append(store_for(desks, desk_name), from_proof(proof, desk_name))
