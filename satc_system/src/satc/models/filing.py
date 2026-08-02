"""FILING — transmitted is not filed, and filed is not accepted.

``PipelineStatus`` collapsed three different authorities into one column:

* what the OWNER does next (an internal stage),
* what the CLIENT is told (deliberately coarser),
* whether the IRS actually has it (Drake's ACK letter).

It also called transmission ``"Filed"``, which IRS Pub 1345 contradicts —
*"an electronically filed return isn't considered filed until the IRS
acknowledges acceptance."* A client told "filed" on the day of transmission has
been told something untrue, and the difference is exactly the window in which a
rejection has to be fixed.

So: :class:`~satc.models.work.Job` owns the internal stage,
:attr:`Filing.ack_code` owns the filing truth, and **a return may have many
filings** — the original, the fix after a rejection, the retransmission after
the perfection period. A single status field could not represent two attempts.

SATC never computes an ack. The owner reads the letter off Drake and keys it;
everything downstream (deadlines, the client message, the retransmission clock)
is derived from that one keyed fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from satc.models.actor import Actor

ReturnVersion = Literal["original", "superseding", "amended"]

# Drake's acknowledgement letters, keyed by the owner from the EF database.
# Source: Drake KB 10783.
AckCode = Literal["P", "A", "a", "R", "B", "D", "E", "S", "T", "X", ""]

_ACK_MEANING = {
    "P": "pending — transmitted, no answer yet",
    "A": "accepted",
    "a": "extension accepted",
    "R": "rejected",
    "B": "bad transmission",
    "D": "duplicate — the IRS already has this return",
    "E": "imperfect",
    "S": "suspended",
    "T": "transmitted to Drake",
    "X": "transmission error",
}

# Acks that mean the IRS has the return and is done with it.
_ACCEPTED = {"A", "a"}
# A rejection the owner must act on. B and X are TRANSPORT failures, not IRS
# rejections, and must not start the 24-hour taxpayer-notification clock.
_REJECTED = {"R"}
_TRANSPORT_FAILURE = {"B", "X"}


@dataclass(slots=True)
class Filing:
    """ONE transmission event for a return. PK = ``filing_id``.

    A return has many of these. That is the entire reason this entity exists.
    """

    filing_id: str
    return_key: str
    client_id: str
    transmitted_at: datetime | None = None
    transmitted_by: Actor | None = None
    submission_id: str = ""
    """The IRS Submission ID, which Pub 1345 requires be associated with the
    signed Form 8879."""

    ack_code: AckCode = ""
    ack_date: date | None = None

    # On rejection, recorded VERBATIM: the client notice has to quote them.
    reject_rule_id: str = ""
    reject_element: str = ""
    reject_message: str = ""

    attempt: int = 1
    note: str = ""

    # -- what the ack actually means -----------------------------------------

    @property
    def is_accepted(self) -> bool:
        return self.ack_code in _ACCEPTED

    @property
    def is_rejected(self) -> bool:
        return self.ack_code in _REJECTED

    @property
    def is_transport_failure(self) -> bool:
        """B and X never happened as far as the IRS is concerned.

        Kept distinct from a rejection because a transport failure does NOT
        start the 24-hour clock to notify the taxpayer — there is nothing to
        tell them yet.
        """
        return self.ack_code in _TRANSPORT_FAILURE

    @property
    def is_duplicate(self) -> bool:
        """``D`` hard-blocks any resend: the IRS already has this return."""
        return self.ack_code == "D"

    @property
    def is_pending(self) -> bool:
        return self.ack_code in ("P", "T")

    @property
    def is_filed(self) -> bool:
        """Filed means ACCEPTED. Not transmitted, not sent, not "green in Drake".

        Pub 1345: a return isn't filed until the IRS acknowledges acceptance.
        """
        return self.is_accepted

    def ack_meaning(self) -> str:
        return _ACK_MEANING.get(self.ack_code, "not yet transmitted")

    def notify_taxpayer_by(self) -> datetime | None:
        """Pub 1345: tell the taxpayer within 24 HOURS of a rejection.

        The loudest alarm in the system, and deliberately not derived for a
        transport failure — there is nothing to notify about.
        """
        from datetime import timedelta

        if not self.is_rejected or self.transmitted_at is None:
            return None
        return (self.ack_date and datetime.combine(self.ack_date, datetime.min.time())
                or self.transmitted_at) + timedelta(hours=24)

    def client_notice_text(self) -> str:
        """What the client must be told, quoting the IRS verbatim."""
        if not self.is_rejected:
            return ""
        parts = [p for p in (self.reject_rule_id, self.reject_element) if p]
        detail = f" ({', '.join(parts)})" if parts else ""
        return (f"The IRS rejected this return{detail}. "
                f"{self.reject_message}".strip())


@dataclass(slots=True)
class Return:
    """A prepared return. PK = ``return_key``.

    ``version`` exists because an amended return is not a status on the
    original — it is a different document with its own filing chain.
    """

    return_key: str
    client_id: str
    tax_year: int
    return_type: str
    jurisdiction: str
    version: ReturnVersion = "original"
    amends_return_key: str = ""
    residency: str = "NA"
    refund_amount: object = None
    balance_due_amount: object = None
    note: str = ""
    filings: list[Filing] = field(default_factory=list)

    @property
    def latest_filing(self) -> Filing | None:
        return self.filings[-1] if self.filings else None

    @property
    def is_filed(self) -> bool:
        """Accepted by the IRS — the only thing that counts as filed."""
        return any(f.is_accepted for f in self.filings)

    @property
    def is_transmitted(self) -> bool:
        return any(f.transmitted_at is not None for f in self.filings)

    @property
    def needs_attention(self) -> bool:
        """Rejected and not since accepted."""
        latest = self.latest_filing
        return latest is not None and (latest.is_rejected or latest.is_transport_failure)

    def filing_status_line(self) -> str:
        """One honest sentence — never "Filed" on the day of transmission."""
        latest = self.latest_filing
        if latest is None:
            return "Not transmitted."
        if latest.is_accepted:
            when = f" on {latest.ack_date:%b %d, %Y}" if latest.ack_date else ""
            return f"Accepted by the IRS{when}."
        if latest.is_rejected:
            return f"REJECTED — {latest.ack_meaning()}. Attempt {latest.attempt}."
        if latest.is_duplicate:
            return "Duplicate — the IRS already has this return. Do not resend."
        if latest.is_transport_failure:
            return f"Transmission failed ({latest.ack_code}) — never reached the IRS."
        return "Transmitted — awaiting IRS acknowledgement."


def status_line_for(filings) -> str:
    """An honest one-line filing status for a return, from its filings.

    The replacement for ``ReturnRecord.status``. Derived rather than stored,
    because the truth lives in the ack the owner keyed off Drake — storing a
    second copy is how a dashboard ends up saying "Filed" about a return the
    IRS rejected.
    """
    ordered = sorted(filings, key=lambda f: (f.attempt, f.filing_id))
    if not ordered:
        return "Not transmitted"
    latest = ordered[-1]
    if latest.is_accepted:
        return "Accepted"
    if latest.is_rejected:
        return "Rejected"
    if latest.is_duplicate:
        return "Duplicate"
    if latest.is_transport_failure:
        return "Transmission failed"
    return "Awaiting IRS"
