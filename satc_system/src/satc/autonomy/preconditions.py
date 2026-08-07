"""THE PRECONDITIONS GATE — charter §3.

Three things have to be true of the *machine*, not the ladder, before any
streak anywhere is allowed to mean anything: an off-disk backup that has
actually been proven restorable, Tailnet Lock pinning what may reach the
machine holding the identity vault, and MFA on the mail and tax accounts —
because the first thing autonomy would eventually touch is the outbox.

Each is a **recorded fact** — principle 2, asserted is not recorded — with a
date and who recorded it, never an inference from "well, it's probably still
backed up". :func:`record_precondition` refuses a model outright: a model
cannot confirm that a human checked the backup drive.

Each is re-confirmed on a cadence (firm policy, not law — see
``configs/firm_policy.yaml``'s ``autonomy:`` section). The distinction the rest
of this module exists to make:

* **Never recorded at all** is the harder case. Nothing has ever been true
  here, so :func:`gate_status` reports it as fully missing and the ladder
  (``satc.autonomy.ladder``) holds every pair at rung zero regardless of how
  clean the approval record is — charter §3's "streaks() returns every pair at
  rung zero with the reason named, and no amount of clean approvals moves
  them."
* **Recorded, then gone stale** is softer. The practice did the work once; the
  cadence just caught up with it. This *freezes* — no pair may newly reach
  ``earned`` — but it does not wipe out what already accrued. "A lapsed
  confirmation freezes accrual and demotes nothing" (charter §3), on purpose:
  a paperwork lapse is not a correction, and punishing it like one would train
  the owner to resent the gate rather than keep it current.

This module owns recording, reading, and that missing/lapsed distinction. It
does not know what a streak is — that is ``ladder.py``'s job, and it consumes
this module's :class:`PreconditionGate` rather than reaching into the records
itself, so the two modules stay independently testable.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, Sequence

from satc.models.actor import Actor, require_human

PreconditionKey = Literal["offsite_backup", "tailnet_lock", "mfa"]

# Closed set — charter §3's table, in the order it appears there. Not
# extensible by a config file: widening what gates autonomy is a doctrine
# decision, not a preference (principle 6a applied to the gate's own shape).
ALL_PRECONDITIONS: tuple[PreconditionKey, ...] = ("offsite_backup", "tailnet_lock", "mfa")

_LABEL = {
    "offsite_backup": "off-disk backup, verified restorable",
    "tailnet_lock": "Tailnet Lock",
    "mfa": "MFA on the mail account and the tax accounts",
}


class PreconditionError(Exception):
    """A precondition was recorded in a way that would not hold up as evidence."""


def precondition_id(*, key: str, confirmed_on: date, confirmed_by: str) -> str:
    """An id derived from WHAT WAS CONFIRMED, never from when the row was written.

    ``confirmed_on`` is content here, not a timestamp of the write — the same
    shape as :func:`satc.models.deliverable.deliverable_id`. Recording the same
    re-confirmation twice (a double click, the owner checking whether they
    already did today's) lands on the same id and is a no-op. Principle 8.
    """
    raw = "|".join([str(key), confirmed_on.isoformat(), confirmed_by.strip().lower()])
    return "pcn_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class PreconditionRecord:
    """One confirmation: this precondition held, on this date, per this person."""

    key: PreconditionKey
    confirmed_on: date
    confirmed_by: str
    """The actor HANDLE, not the Actor — a stored fact, not a live object graph
    (same reasoning as :attr:`~satc.models.deliverable.Deliverable.delivered_by`)."""
    note: str = ""

    @property
    def record_id(self) -> str:
        return precondition_id(key=self.key, confirmed_on=self.confirmed_on,
                               confirmed_by=self.confirmed_by)


def record_precondition(*, actor: Actor, key: PreconditionKey, confirmed_on: date,
                        note: str = "") -> PreconditionRecord:
    """Record that a human checked one of the three things and it held.

    Refuses a model outright (principle 6, 9): "the backup restored cleanly" is
    exactly the kind of claim nobody could check later from the file alone if a
    model were allowed to assert it, and it is the one fact everything else in
    this package is gated on.
    """
    require_human(actor, "confirm an autonomy precondition", instead=(
        "propose it and let the owner verify the backup, the Tailnet Lock "
        "setting, or MFA themselves and record it"))
    if key not in ALL_PRECONDITIONS:
        raise PreconditionError(
            f"{key!r} is not one of the autonomy preconditions "
            f"({', '.join(ALL_PRECONDITIONS)}). The ladder does not gate on "
            f"anything outside that list.")
    return PreconditionRecord(key=key, confirmed_on=confirmed_on,
                              confirmed_by=actor.handle, note=note.strip())


def _latest(records: Sequence[PreconditionRecord], key: str,
            as_of: date | None = None) -> PreconditionRecord | None:
    """The most recent confirmation of one precondition AS OF a given day.

    ``as_of`` is not optional in spirit. Without it the gate answered a question
    about last March using a confirmation recorded this morning: tick "backup
    done" today and every past day retroactively reported the gate as holding,
    so a digest for a day the practice was NOT compliant would say it was. A
    record that improves the past is not a record.
    """
    mine = [r for r in records
            if r.key == key and (as_of is None or r.confirmed_on <= as_of)]
    return max(mine, key=lambda r: r.confirmed_on) if mine else None


@dataclass(frozen=True, slots=True)
class PreconditionGate:
    """What the three preconditions currently say, and why."""

    holds: bool
    missing: tuple[PreconditionKey, ...]
    """Never confirmed even once. The harder case — see module docstring."""
    lapsed: tuple[PreconditionKey, ...]
    """Confirmed before, but the confirmation has aged past the cadence."""
    why: str
    """One line, in the owner's language, naming which precondition and why —
    principle 13. Never just "gated: false"."""

    frozen_since: date | None = None
    """The day accrual stopped, when a confirmation has lapsed.

    Charter §3 says a lapse FREEZES ACCRUAL AND DEMOTES NOTHING. Those are two
    different things and reading them as one produced a real bug: a pair that
    had already reached ``earned`` fell back to ``draft_only`` the day a backup
    confirmation went stale, which is a demotion for a paperwork lapse — exactly
    what the charter says would train the owner to resent the gate.

    Freezing needs a DATE, not a flag: approvals after this day do not count,
    and everything up to it stands. Without the date the only implementable
    reading of "frozen" is "blocked", which is the demotion."""


def gate_status(records: Sequence[PreconditionRecord], *, cadence_days: int,
                today: date | None = None) -> PreconditionGate:
    """Where the gate stands right now, from the recorded facts alone.

    Computed, never stored (principle 3) — there is no "gate open" flag
    anywhere; every call re-derives it from whatever confirmations are on
    file, so a re-confirmation recorded five minutes ago is reflected
    immediately and a cadence quietly expiring overnight is caught the next
    time anyone asks, with no sweep job required to notice it.
    """
    as_of = today or date.today()
    missing: list[PreconditionKey] = []
    lapsed: list[PreconditionKey] = []
    for key in ALL_PRECONDITIONS:
        latest = _latest(records, key, as_of)
        if latest is None:
            missing.append(key)
            continue
        if (as_of - latest.confirmed_on).days > cadence_days:
            lapsed.append(key)

    holds = not missing and not lapsed
    if holds:
        why = "All three autonomy preconditions are confirmed and current."
    else:
        bits = []
        if missing:
            bits.append("never recorded — " + "; ".join(_LABEL[k] for k in missing))
        if lapsed:
            bits.append("re-confirmation lapsed — " + "; ".join(_LABEL[k] for k in lapsed))
        why = "Autonomy preconditions not met: " + "; ".join(bits) + "."
    # The day accrual stopped: the earliest lapse, because the first one to go
    # stale is when the practice stopped meeting the bar. Approvals after it do
    # not count; everything up to it stands (charter section 3).
    frozen_since = None
    if lapsed:
        stale = [_latest(records, k, as_of) for k in lapsed]
        dates = [r.confirmed_on for r in stale if r is not None]
        if dates:
            frozen_since = min(dates) + timedelta(days=cadence_days)
    return PreconditionGate(holds=holds, missing=tuple(missing), lapsed=tuple(lapsed),
                            why=why, frozen_since=frozen_since)
