"""Time actually spent, recorded by the software rather than by a person.

THE FIRM SET THE CONSTRAINT AND IT DECIDES THE WHOLE DESIGN: *"I want it as I
work and to automate everything possible about recording time because I am bad
at doing so."* Anything with a start button and a stop button is a chore, and a
chore this firm does not do is a feature that reports nothing. So nothing here
has a button.

WHAT IT ACTUALLY RECORDS, said plainly because the number gets compared to a
price. Every command that names an engagement appends one row here, with a
timestamp, automatically. Rows close together in time are one SITTING, and a
sitting's length is first touch to last touch. That measures **when the software
was being used on this engagement**. It is not a claim about billable time and
must never be presented as one.

THE BLIND SPOT IS THE BIGGEST PART OF THE JOB. The return is prepared in Drake,
and this software cannot see Drake at all -- so the measured figure is a FLOOR,
and usually a low one. `add()` is the one manual entry, for the work that
happened somewhere we cannot watch, and every report keeps the two apart:
MEASURED is what the software saw, STATED is what a person said. Adding them
into one number would produce a total that looks authoritative and is not, which
is the failure this whole repository keeps having.

A SINGLE TOUCH IS NOT ZERO MINUTES. One command on its own has no span, and
recording it as nothing would say the work did not happen. It counts as the
firm's own `minimum_increment` from the fee schedule -- the floor below which
they do not bill anything -- because that is the firm's existing answer to
"how long is the shortest piece of work", and inventing a second one here would
be a number nobody chose.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import tins

LOG = "time.jsonl"

# How long a gap can be before two touches are separate sittings. Thirty minutes
# is a judgement, not a measurement, and it is the one number here worth
# revisiting once there is real data: too short and a return prepared in Drake
# between two commands is split into fragments; too long and yesterday evening
# joins this morning.
IDLE_GAP = timedelta(minutes=30)

# Set this to stop the automatic recording -- for a demo, a test harness, or the
# exercise run, none of which are the firm working. Recording those would put
# fictional hours beside a real budget.
OFF = "SATC_NO_TIMELOG"

# COMMANDS THAT ONLY LOOK. Asking how long something took must not add to how
# long it took, and `spent` recorded itself the first time it ran -- 0.25 h of
# "work" for opening the report. Reading a report, listing engagements, checking
# a price: none of it is the return being prepared.
#
# A DENY-LIST WOULD LET THE NEXT REPORTING COMMAND FORGET, so
# `tests/test_timelog.py` asserts that EVERY subcommand appears here or is
# deliberately treated as work. A new command cannot be added without somebody
# deciding which it is.
#
# Where a command is genuinely both -- `sign` lists signatures and also records
# one -- it counts as work. Under-recording is the safer failure: the measured
# figure is already a floor and is presented as one, while over-recording
# inflates it with time spent looking.
REPORTING = frozenset({
    "spent", "season", "engagements", "doctor", "check", "ladder",
    "price", "hours", "procedures", "walkthrough", "demo", "sample",
    "payments",
})


@dataclass(frozen=True)
class Touch:
    """One moment the software was used on one engagement."""

    when: datetime
    what: str                 # the command, or what a person said they did
    hours: float | None = None    # set only on a stated entry
    note: str = ""

    @property
    def stated(self) -> bool:
        return self.hours is not None


@dataclass
class Sitting:
    """A run of touches close enough together to be one piece of work."""

    started: datetime
    ended: datetime
    touches: int
    what: list[str] = field(default_factory=list)

    def hours(self, *, floor: float) -> float:
        span = (self.ended - self.started).total_seconds() / 3600
        return max(span, floor)


@dataclass
class Spent:
    """What was measured, what was stated, and never the two added up."""

    measured: float
    stated: float
    sittings: list[Sitting]
    stated_entries: list[Touch]
    touches: int

    @property
    def examined_nothing(self) -> bool:
        """No rows at all. Different from "no time spent", and said differently."""
        return self.touches == 0


def _path(store: Path, ref: str) -> Path:
    return Path(store) / ref / LOG


def record(store: Path, ref: str, what: str, *, when: datetime | None = None) -> None:
    """Append one automatic touch. Never raises -- see below.

    NOTHING HERE MAY BREAK A COMMAND. This is bookkeeping that runs beside real
    work: rendering a pack, sending an invoice. A failure to write a time row
    must not stop a document reaching a client, so every error is swallowed. The
    cost is that time can be silently missing, which `spent()` reports as a low
    measured figure rather than pretending -- and a low floor is the honest
    failure for a floor to have.
    """
    if os.environ.get(OFF) or what in REPORTING:
        return
    try:
        path = _path(store, ref)
        if not path.parent.is_dir():
            return                     # no engagement here; nothing to attach to
        row = {"when": (when or datetime.now()).isoformat(timespec="seconds"),
               "what": what}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:                  # noqa: BLE001 - see the docstring
        return


def add(store: Path, ref: str, hours: float, what: str, *,
        when: datetime | None = None) -> None:
    """Record work the software could not see. The one manual entry.

    This one RAISES. `record` is bookkeeping beside real work and must never
    interrupt it; this is somebody deliberately writing down two hours in Drake,
    and losing that silently would be the worst of both worlds.
    """
    hours = float(hours)
    if hours <= 0:
        raise ValueError(f"{hours} hours is not a piece of work.")
    if not what.strip():
        raise ValueError(
            "stated time needs to say what it was. A number with no work "
            "against it cannot be checked by anybody later, including you.")
    # THE FIFTH SEAM. `what` is free text a person types, and free text is where
    # identification numbers get in -- "called the client about SSN ...". This
    # file lives in the engagement folder, which is in OneDrive and in every
    # backup of it. `record()` needs no guard: it writes command names.
    #
    # Found by writing the test first and watching it not raise. The interview
    # answers, the close-out record, the pre-send gate and the browser's
    # unfinished sitting were the other four.
    tins.refuse({"what": what}, "this time entry")
    path = _path(store, ref)
    if not path.parent.is_dir():
        raise FileNotFoundError(f"no engagement {ref} under {store}")
    row = {"when": (when or datetime.now()).isoformat(timespec="seconds"),
           "what": what.strip(), "hours": hours}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def touches(store: Path, ref: str) -> list[Touch]:
    """Every row, oldest first. A row we cannot parse is skipped, not guessed."""
    path = _path(store, ref)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        # A LOG WE CANNOT READ IS NOT A LOG OF NOTHING, but there is nothing to
        # be done about it here and a report is not worth a traceback. It comes
        # back empty and `Spent.examined_nothing` says so, which is the same
        # sentence a genuinely empty engagement gets -- honest, if unhelpful.
        # Found by the test that makes the log path a directory.
        return []
    out: list[Touch] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            when = datetime.fromisoformat(row["when"])
        except (ValueError, KeyError, TypeError):
            continue                   # a corrupt row loses one touch, not the file
        out.append(Touch(when=when, what=str(row.get("what", "")),
                         hours=row.get("hours"), note=str(row.get("note", ""))))
    return sorted(out, key=lambda t: t.when)


def spent(store: Path, ref: str, *, floor: float = 0.25,
          gap: timedelta = IDLE_GAP) -> Spent:
    """What the software saw, and what a person said, kept apart."""
    rows = touches(store, ref)
    automatic = [t for t in rows if not t.stated]
    said = [t for t in rows if t.stated]

    sittings: list[Sitting] = []
    for touch in automatic:
        if sittings and touch.when - sittings[-1].ended <= gap:
            current = sittings[-1]
            current.ended = touch.when
            current.touches += 1
            if touch.what not in current.what:
                current.what.append(touch.what)
        else:
            sittings.append(Sitting(started=touch.when, ended=touch.when,
                                    touches=1, what=[touch.what]))

    return Spent(
        measured=round(sum(s.hours(floor=floor) for s in sittings), 2),
        stated=round(sum(t.hours or 0.0 for t in said), 2),
        sittings=sittings,
        stated_entries=said,
        touches=len(rows),
    )
