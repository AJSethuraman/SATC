"""Where a Run's time went: seconds per stage, by the wall clock.

The firm, 30 Sep 2026: a Run on about 17,000 loans x 70 columns took 578 s on the bank's laptop, against about
22 s on ours. Nothing said which part. So each stage of book.run is timed, shown on Record ("Where the time went")
and in the Run's lines, and handed to a `progress(stage)` callback as it starts, for the launcher to show.

One clock per Run, set for the length of it (`running`). The code that does the work says where a stage starts
(`mark`) and adds what is worth knowing about it (`note`: the extract's kind and size, the shuffle test's workers);
with no clock running both do nothing, so the engine and the tabs can be called alone as before. A stage marked
twice (the engine's first pass and its second) adds up under one name, in the order first seen.
"""

from __future__ import annotations

import contextvars
import time
from contextlib import contextmanager
from typing import Callable


def no_progress(stage: str) -> None:
    """The default `progress`: nothing to tell."""


class Clock:
    def __init__(self, progress: Callable[[str], None] | None = None):
        self.progress = progress or no_progress
        self.seconds: dict[str, float] = {}           # stage -> seconds, in the order first started
        self.notes: dict[str, str] = {}               # stage -> what it worked on, in words
        self.facts: dict[str, object] = {}            # the same as numbers, for tests and the audit file
        self._stage: str | None = None
        self._at = 0.0
        self.started = time.perf_counter()

    def mark(self, stage: str) -> None:
        """`stage` starts now; the one before it, if any, ends."""
        now = time.perf_counter()
        self._close(now)
        self._stage, self._at = stage, now
        self.seconds.setdefault(stage, 0.0)
        try:
            self.progress(stage)
        except Exception:                             # noqa: BLE001 - a broken display never stops a Run
            pass

    def stop(self) -> None:
        self._close(time.perf_counter())
        self._stage = None

    def _close(self, now: float) -> None:
        if self._stage is not None:
            self.seconds[self._stage] += now - self._at

    def note(self, words: str | None = None, stage: str | None = None, **facts) -> None:
        """What the stage (the current one unless named) worked on: words for Record, facts as numbers."""
        stage = stage or self._stage
        if stage is not None and words:
            self.notes[stage] = words
        self.facts.update(facts)

    def total(self) -> float:
        return sum(self.seconds.values())

    def rows(self) -> list[tuple[str, float]]:
        return list(self.seconds.items())

    def biggest(self, k: int = 3) -> list[tuple[str, float]]:
        return sorted(self.seconds.items(), key=lambda kv: -kv[1])[:k]


_now: contextvars.ContextVar[Clock | None] = contextvars.ContextVar("pocketbook_clock", default=None)


@contextmanager
def running(clock: Clock):
    token = _now.set(clock)
    try:
        yield clock
    finally:
        clock.stop()
        _now.reset(token)


def current() -> Clock | None:
    return _now.get()


def mark(stage: str) -> None:
    c = _now.get()
    if c is not None:
        c.mark(stage)


def note(words: str | None = None, stage: str | None = None, **facts) -> None:
    c = _now.get()
    if c is not None:
        c.note(words, stage, **facts)


def took(seconds: float) -> str:
    """A time as the analyst reads it: 0.4 s, 9.8 s, 42 s, 9 min 38 s."""
    if seconds < 10:
        return f"{seconds:.1f} s"
    if seconds < 60:
        return f"{seconds:.0f} s"
    m, s = divmod(int(round(seconds)), 60)
    return f"{m} min {s} s"


def took_line(clock: Clock, k: int = 3) -> str:
    """The Run's line: "Took 9 min 38 s: the shuffle test 7 min 2 s, reading the extract 1 min 4 s, ..."."""
    big = [f"{name[0].lower() + name[1:]} {took(s)}" for name, s in clock.biggest(k) if s > 0]
    return f"Took {took(clock.total())}" + (": " + ", ".join(big) + "." if big else ".")
