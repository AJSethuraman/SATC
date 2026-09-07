"""The fact that something went OUT to the client.

This is the one fact the practice was not recording, and its absence was load
bearing in three separate places: :func:`satc.work.stage.derive_stage` refuses
to conclude ``delivered``, the turnaround SLA cannot be measured, and
``unbilled_work`` cannot tell a finished job from a delivered one. Each of those
refusals was correct — "every task is ticked" and "the return went to the
client" are different facts, and inferring the second from the first guesses at
the step that matters most.

WHAT DOES NOT BELONG HERE, because it already has a home:

* The signed 8879 coming BACK is a :class:`~satc.models.evidence.ReceivedDocument`
  with provenance — inbound evidence, chased like any other document.
* Transmission and acknowledgement are :class:`~satc.models.filing.Filing`.
  IRS Pub 1345: transmitted is not filed and filed is not accepted.

So this covers only the outbound half, and covers it the same way the inbound
half is covered: WHAT went, to WHOM, WHEN, HOW, and on whose say-so. 26 CFR
§1.6695-2(b)(4)(i)(C) requires a preparer to record how, when and from whom a
document was obtained; nothing obliges the mirror record for what was sent, but
the reason for the inbound rule — that "we have it" is worthless without "how do
we know" — applies identically outbound.

RECORDING DELIVERY IS NOT DELIVERING. Nothing here sends anything; SATC has no
SMTP and this does not change that (principle 9). This records that the owner
did it, which is exactly why it takes a human actor and refuses a model.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Literal

from satc.models.actor import Actor

DeliverableKind = Literal[
    "return_for_review",     # the draft return, for the client to read
    "authorization_form",    # the 8879 going out for signature
    "signed_copy",           # their copy of what was filed
    "organizer",             # the questionnaire / document request pack
    "letter",                # engagement letter, planning memo
    "workpapers",            # supporting schedules, at the client's request
]

Channel = Literal["portal", "email", "mail", "hand", "fax"]

_KIND_WORDS = {
    "return_for_review": "the draft return for review",
    "authorization_form": "the e-file authorization for signature",
    "signed_copy": "their copy of the filed return",
    "organizer": "the organizer",
    "letter": "a letter",
    "workpapers": "the workpapers",
}


class DeliveryError(Exception):
    """A delivery was recorded in a way that would not be defensible later."""


def deliverable_id(*, client_id: str, tax_year: int, kind: str,
                   return_key: str, delivered_on: date) -> str:
    """An id derived from WHAT WAS DELIVERED, never from when it was keyed in.

    Recording the same delivery twice — a double-click, a re-import, the owner
    checking whether they already did it — lands on the same id and is a no-op
    rather than a second delivery. Principle 8.
    """
    raw = "|".join([client_id.strip().lower(), str(int(tax_year)), str(kind),
                    return_key.strip().lower(), delivered_on.isoformat()])
    return "dlv_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class Deliverable:
    """Something the practice sent to a client, and how we know."""

    client_id: str
    tax_year: int
    kind: DeliverableKind
    delivered_on: date
    channel: Channel = "portal"
    delivered_by: str = ""
    """The actor HANDLE, not the Actor — this is a stored fact, and a stored
    object graph is how provenance quietly stops round-tripping."""

    return_key: str = ""
    """Which return this was about, when it was about one. Empty for an
    organizer or a letter, which belong to a client-year rather than a return."""

    note: str = ""

    @property
    def deliverable_id(self) -> str:
        return deliverable_id(client_id=self.client_id, tax_year=self.tax_year,
                              kind=self.kind, return_key=self.return_key,
                              delivered_on=self.delivered_on)

    @property
    def is_the_return(self) -> bool:
        """Whether this is the delivery that moves a job past preparation.

        An organizer going out is not the return going out, and only one of
        them should ever make a job read as delivered.
        """
        return self.kind in ("return_for_review", "signed_copy")

    def describe(self) -> str:
        """One line, in the owner's language, for a screen or an audit."""
        how = {"portal": "via the portal", "email": "by email", "mail": "by post",
               "hand": "by hand", "fax": "by fax"}[self.channel]
        return (f"Sent {_KIND_WORDS.get(self.kind, self.kind)} {how} on "
                f"{self.delivered_on:%b %d, %Y}")


def record_delivery(*, actor: Actor, client_id: str, tax_year: int,
                    kind: DeliverableKind, delivered_on: date,
                    channel: Channel = "portal", return_key: str = "",
                    note: str = "") -> Deliverable:
    """Record that something went to the client. Refuses a model outright.

    Delivery is the step a whole engagement pivots on — it stops the prep clock,
    starts the signature chase, and makes the work billable. A model asserting
    it happened would be asserting the one thing nobody could check afterwards
    from the file alone (principles 6 and 9).
    """
    from satc.models.actor import require_human

    require_human(actor, "record that work was delivered",
                  instead="propose it and let the owner confirm they sent it")
    if kind in ("return_for_review", "signed_copy") and not return_key.strip():
        raise DeliveryError(
            "Recording a return as delivered needs to say WHICH return. Without "
            "it nothing can tell whether the 2025 federal or the state went out, "
            "and the job it belongs to cannot be moved.")
    return Deliverable(
        client_id=client_id, tax_year=int(tax_year), kind=kind,
        delivered_on=delivered_on, channel=channel,
        delivered_by=actor.handle, return_key=return_key.strip(),
        note=note.strip())


def delivery_of(deliverables, *, client_id: str, tax_year: int,
                return_key: str = "") -> Deliverable | None:
    """The delivery that put THIS return in the client's hands, if any.

    The earliest one, not the latest: a return re-sent in June was still
    delivered in April, and the turnaround promise was kept or missed then.
    """
    mine = [d for d in deliverables
            if d.client_id == client_id and d.tax_year == tax_year
            and d.is_the_return
            and (not return_key or d.return_key == return_key)]
    return min(mine, key=lambda d: d.delivered_on) if mine else None


def merge(existing, arriving) -> tuple[list[Deliverable], list[Deliverable]]:
    """Fold new deliveries in, ignoring ones already recorded. Principle 8."""
    ledger = list(existing)
    seen = {d.deliverable_id for d in ledger}
    added: list[Deliverable] = []
    for item in arriving:
        if item.deliverable_id in seen:
            continue
        seen.add(item.deliverable_id)
        ledger.append(item)
        added.append(item)
    return ledger, added
