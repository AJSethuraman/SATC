"""Who owes us a document this morning, longest wait first.

THE OTHER HALF OF A PROMISE ALREADY MADE. The business engagement letter says
*"We will tell you what we need and when, and we will chase it."* Telling them
is built: intake opens a ``Requested`` row for every ask and the organizer email
carries the list. The chasing was one number on a workbook dashboard --
``COUNTIF(status, "Requested")`` in :mod:`satc.workbook.dashboards`. A count is
not a chase. It does not say whose, or since when, or which of the five forms a
single request named are still missing.

The shape is deliberately ``client-documents/signing.py:waiting`` -- the morning
screen for who owes a SIGNATURE -- because the two lists are read at the same
desk at the same hour: longest wait first, nothing chased on the day it was
asked for, and a sweep that reports what it examined rather than printing "ok".

De-identified in, name out. The register is keyed on ``client_id`` and holds no
PII; a person cannot chase a handle, so the display label is resolved through
the vault the way :func:`satc.intake.service.existing_client_index` does. Nothing
here reads or prints a TIN, masked or otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from satc.intake import matching

# The register status that means "asked for, not here yet". The other statuses
# in `DocStatus` are all arrivals or exclusions; only this one is a debt.
OUTSTANDING = "Requested"


@dataclass(slots=True)
class Waiting:
    """One outstanding request, as the firm reads it on the morning list."""

    client_id: str
    client: str                 # vault display label; never a TIN
    document_id: str
    doc_type: str
    asked_for: str              # the prose the client was actually sent
    tax_year: int
    since: date | None          # when we asked, or None if the row carries no date
    arrived: frozenset[str] = frozenset()
    awaiting: frozenset[str] = frozenset()

    def waiting_days(self, today: date | None = None) -> int | None:
        """How long this has been out, or None when the request carries no date.

        None is the answer, not zero. See the sort in :func:`waiting`.
        """
        if self.since is None:
            return None
        return max((today or date.today()) - self.since, timedelta(0)).days

    @property
    def is_bundle(self) -> bool:
        """True when this one request names several forms."""
        return matching.is_bundle(self.doc_type, self.asked_for)

    @property
    def named(self) -> int:
        """How many forms this request names. 1 for an ordinary request."""
        return max(len(matching.families(f"{self.doc_type} {self.asked_for}")), 1)

    @property
    def part_way(self) -> str:
        """"2 of 5 here" for a bundle part-way in; empty for anything else."""
        if not self.is_bundle or not self.arrived:
            return ""
        return f"{len(self.arrived)} of {self.named} here"

    @property
    def here(self) -> str:
        """Which named forms have turned up, as the firm reads them."""
        return matching.names(self.arrived)

    @property
    def still_missing(self) -> str:
        """Which named forms have not. Empty on an ordinary single-form request."""
        return matching.names(self.awaiting)


@dataclass(slots=True)
class Sweep:
    """The morning list AND what it had to look at to produce it.

    S2 in `docs/SOFTWARE-TENETS.md`: a check must report its denominator, because
    "nothing outstanding" and "nothing examined" are the same sentence otherwise
    and only one of them is good news. Every count here is taken from the same
    walk that built ``rows`` -- a `len()` computed beside the loop agrees until
    somebody adds a `continue`.
    """

    rows: list[Waiting]
    documents: int = 0          # register rows read, whatever their status
    clients: int = 0            # clients whose register was read
    engagements: int = 0        # intake engagements on file
    opened_today: int = 0       # outstanding, but asked for today -- not a chase yet

    @property
    def examined_nothing(self) -> bool:
        """Nothing was looked at, which is a different report from "all clear"."""
        return self.documents == 0 and self.engagements == 0


def waiting(store, *, today: date | None = None) -> Sweep:
    """Every outstanding document request, longest wait first.

    A request naming several forms stays open until all of them arrive (see
    ``service.reconcile_received``), so it carries which have and which have
    not: "still waiting on the 1099-B" is the line that gets a document into
    the office; "still outstanding" is the line that gets skimmed past.
    """
    # Imported here, not at module scope: `service` pulls in the whole
    # ingest classifier, and the morning list is one of the two things a
    # preparer runs from a cold terminal.
    from satc.intake.service import outstanding_parts

    mart = store.load_mart()
    names = store.names()
    labels = {pc.client_id: pc.display_label for pc in mart.public_clients}
    engagements = len(store.load_intake_engagements())

    rows: list[Waiting] = []
    seen_clients: set[str] = set()
    documents = 0
    opened_today = 0
    for rec in mart.documents:
        documents += 1
        seen_clients.add(rec.client_id)
        if rec.status != OUTSTANDING:
            continue
        row = Waiting(
            client_id=rec.client_id,
            # The vault's name, then the mart's de-identified label, then the
            # handle itself. Never the TIN: `PublicClient` carries `tin_last4`
            # and `tin_masked` right beside `display_label`, and neither belongs
            # on a screen whose whole job is to be left open on a desk.
            client=names.get(rec.client_id) or labels.get(rec.client_id, "") or rec.client_id,
            document_id=rec.document_id,
            doc_type=str(rec.doc_type),
            asked_for=rec.note or str(rec.doc_type),
            tax_year=rec.tax_year,
            since=rec.as_of,
            arrived=frozenset(rec.parts),
            awaiting=frozenset(outstanding_parts(rec)),
        )
        # NOT A CHASE ON THE MORNING YOU ASKED. The same rule
        # `signing.mark_sent` records for a pack built today: without it,
        # "outstanding" only means "asked for and not back yet", which on the
        # day of the ask is noise -- and a morning list that is mostly noise is
        # a morning list nobody opens. Held back rather than hidden: the count
        # is reported, so the sweep still adds up to the register.
        if row.waiting_days(today) == 0:
            opened_today += 1
            continue
        rows.append(row)

    # WHERE A REQUEST WITH NO DATE GOES, and why it is the top of the list
    # rather than the bottom. A missing date is not a wait of zero; it is a wait
    # nobody can measure, and it may well be the oldest thing here. Sorting it
    # last would assert the one thing we know we do not know -- that it is the
    # newest -- and would bury the request most likely to have been forgotten
    # underneath every request somebody dated properly. So it goes first, marked
    # as unknown, where a person puts a date on it.
    rows.sort(key=lambda w: (w.waiting_days(today) is not None,
                             -(w.waiting_days(today) or 0)))
    return Sweep(rows=rows, documents=documents, clients=len(seen_clients),
                 engagements=engagements, opened_today=opened_today)
