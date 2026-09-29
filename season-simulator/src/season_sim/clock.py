"""One frozen instant per simulated day, and a seeded uuid4.

`time_machine.travel(..., tick=False)` patches the C-level `date.today()` and
`datetime.now()`, so `from datetime import date` call sites see the simulated
day too -- which is what lets the real routes run unmodified.

14:00 UTC is morning on the US east coast; a fixed UTC instant avoids needing
tzdata on Windows. Every write stamp the code makes that day (an arrival's
`obtained_at`, a job's `created_at`, a signature's `recorded`, an invoice
date, the time log) carries that instant.

Timings inside the simulator use `time.perf_counter`, which time-machine does
not freeze.
"""

from __future__ import annotations

import random
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

import time_machine

SENTINEL = date(2031, 6, 15)     # the clock-leak audit's "wrong" clock


def instant(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 14, 0, tzinfo=timezone.utc)


@contextmanager
def frozen(d: date):
    with time_machine.travel(instant(d), tick=False):
        yield


def days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def is_weekday(d: date) -> bool:
    return d.weekday() < 5


def on_or_after_weekday(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def add_business_days(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def seed_uuid4(seed: int) -> None:
    """`uuid.uuid4` from a seeded generator (ids.py:75-79 is the only caller)."""
    rng = random.Random(seed * 7919 + 17)

    def seeded() -> uuid.UUID:
        return uuid.UUID(int=rng.getrandbits(128), version=4)

    uuid.uuid4 = seeded                                        # type: ignore[assignment]


def spoken(d: date) -> str:
    """'April 10, 2027' -- the shape the letters and `signing._past` read."""
    return f"{d:%B} {d.day}, {d.year}"


def leaks(right: dict, wrong: dict) -> list[str]:
    """The reads whose answer moved when only the machine clock moved.

    `right` is every read taken with the clock frozen on the simulated day;
    `wrong` is the same reads with the clock on SENTINEL and `today=` passed
    explicitly. Anything that differs read the machine clock somewhere
    `today=` does not reach.
    """
    return sorted(k for k in right if right[k] != wrong.get(k))
