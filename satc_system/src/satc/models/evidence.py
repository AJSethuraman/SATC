"""EVIDENCE — what we asked for, and what actually arrived.

These two entities replace half of a single ``DocumentRecord`` whose one
``DocStatus`` enum spanned four unrelated lifecycles::

    Requested → Received → Sent → Signed → N/A

A row could not be both *a thing we asked for* and *a thing we sent*, "N/A"
carried no reason, and there were no provenance fields at all. Splitting is not
tidiness — it is the difference between a register and a record:

* **RequestedItem** is an ASK. It can be outstanding, satisfied, expected-late,
  or not-applicable **with a reason**, and it knows whether it BLOCKS. IRS Pub
  1345 forbids originating an e-filed return before the W-2, W-2G and 1099-R
  are in hand, so "blocking" is a rule, not a preference.

* **ReceivedDocument** is an ARRIVAL, and it carries how it got here.
  26 CFR §1.6695-2(b)(4)(i)(C) requires "a record of how and when the
  information ... was obtained by the tax return preparer, including the
  identity of any person furnishing the information." A document with unknown
  provenance is a compliance defect, not a shrug.

Deliverable and Authorization are the other half of the split and are
deliberately **not here yet** — an 8879 out for signature is an Authorization,
not a RequestedItem, and modelling it properly needs the signature lifecycle
that comes with Filing. Until then those rows stay in the old register.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from satc.models.actor import Actor

# Whether an item stops work, and at which point.
BlockingClass = Literal["blocking", "expected_late", "non_blocking"]
"""``blocking`` — prep cannot start (a W-2 by IRS rule).
``expected_late`` — a K-1 or consolidated 1099-B. Does NOT block prep starting;
DOES block transmission. Modelling this as a third state is what lets a real
practice begin work on a file that is 95% complete instead of waiting.
``non_blocking`` — useful, not load-bearing."""

RequestStatus = Literal["outstanding", "satisfied", "not_applicable", "withdrawn"]

# How a document reached the practice. Required by §1.6695-2(b)(4)(i)(C).
ObtainedHow = Literal[
    "furnished_by_client", "furnished_by_third_party", "downloaded_by_preparer",
    "prior_year_carryforward", "unknown",
]


@dataclass(slots=True)
class RequestedItem:
    """Something the practice asked a client for. PK = ``request_id``."""

    request_id: str
    client_id: str
    tax_year: int
    doc_type: str
    request_text: str = ""
    """The exact ask, in the words the client reads.

    Load-bearing, not a comment: reconciliation matches an arriving document
    against BOTH the type and this prose, so a received "W-2" can satisfy a
    "core income documents" bundle."""

    blocking: BlockingClass = "non_blocking"
    status: RequestStatus = "outstanding"
    not_applicable_reason: str = ""
    """Why it does not apply — "they closed that account in March".

    A bare "N/A" is how a real answer becomes indistinguishable from a shrug.
    The engine refuses the status without a reason."""

    requested_at: date | None = None
    satisfied_by_document_id: str = ""
    task_id: str = ""
    follow_up_round: int = 0

    parts: set[str] = field(default_factory=set)
    """Which form families named by this request have ARRIVED so far.

    Only meaningful when the request names more than one form. A request
    reading *"Upload Forms 1099-INT, 1099-DIV and brokerage statements"* is
    three asks wearing one row, and before this field existed the first
    document to match any of it closed the whole thing: the 1099-DIV arrived,
    the request went satisfied, and the 1099-INT that came next found nothing
    open to satisfy. Nobody was asked for the brokerage statement again.
    Found in a live run, 31 August 2026.

    Held here rather than derived from the received documents because the
    question "what are we still waiting on" has to survive a restart, and
    because a document can be received against a request without our being
    able to say which of its named forms it was.
    """

    @property
    def is_open(self) -> bool:
        return self.status == "outstanding"

    @property
    def needs_every_part(self) -> bool:
        """True when this may close only once every form it names has arrived.

        NOT the same question as "does it name several forms". A standing
        checklist that ends "and any other income forms received" names five and
        requires none of them in particular -- see `matching.needs_every_part`.
        """
        from satc.intake import matching
        return matching.needs_every_part(str(self.doc_type), self.request_text)

    @property
    def outstanding_parts(self) -> set[str]:
        """The named forms that have NOT arrived. Empty for a single-form request."""
        from satc.intake import matching
        if not self.needs_every_part:
            return set()
        return matching.outstanding((str(self.doc_type), self.request_text),
                                    self.parts or set())

    @property
    def blocks_prep(self) -> bool:
        return self.is_open and self.blocking == "blocking"

    @property
    def blocks_transmission(self) -> bool:
        """Expected-late items don't stop prep, but they do stop filing."""
        return self.is_open and self.blocking in ("blocking", "expected_late")

    def days_waiting(self, today: date) -> int | None:
        return None if self.requested_at is None else (today - self.requested_at).days


@dataclass(slots=True)
class ReceivedDocument:
    """A document that arrived, and how. PK = ``document_id`` (a content hash)."""

    document_id: str
    client_id: str
    tax_year: int
    doc_type: str
    obtained_how: ObtainedHow = "unknown"
    obtained_at: datetime | None = None
    furnished_by: str = ""
    """WHO provided it — required verbatim by §1.6695-2(b)(4)(i)(C)."""

    channel: str = ""
    """Email, portal, paper, in person. Part of the same required record."""

    satisfies_request_id: str = ""
    classified_by: Actor | None = None
    """What decided this document's TYPE.

    An Actor and not a bare string, because a vision-rung classification is a
    model's opinion. A model-classified arrival may not close a client request
    on its own — see ``satc.intake.service.reconcile_received``."""

    display_name: str = ""
    """The original filename, for the local UI only. Never exported: filenames
    routinely carry the client's own name."""

    source_path: str = ""
    note: str = ""

    @property
    def is_model_classified(self) -> bool:
        return self.classified_by is not None and self.classified_by.is_model

    @property
    def has_known_provenance(self) -> bool:
        """Whether the §1.6695-2 record is actually complete for this document."""
        return self.obtained_how != "unknown" and bool(self.obtained_at)


class EvidenceError(Exception):
    """An evidence record was asked to enter a state it may not."""


def mark_not_applicable(item: RequestedItem, reason: str) -> RequestedItem:
    """Close a request as not applicable — with a reason, always.

    Refuses without one (doctrine rule 3 names the fix). "Still waiting on the
    1099-INT" resolving into "they closed that account in March" is the whole
    value: the answer is the record that the gap was considered, not missed.
    """
    if not (reason or "").strip():
        raise EvidenceError(
            f"Cannot mark {item.doc_type!r} not applicable without a reason. "
            f"Record what the client actually said — a bare N/A is "
            f"indistinguishable from never having asked.")
    item.status = "not_applicable"
    item.not_applicable_reason = reason.strip()
    return item


def satisfy(item: RequestedItem, document: ReceivedDocument) -> RequestedItem:
    """Close a request against the document that satisfied it."""
    item.status = "satisfied"
    item.satisfied_by_document_id = document.document_id
    document.satisfies_request_id = item.request_id
    return item
