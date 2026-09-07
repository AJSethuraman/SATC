"""Who owes us a document this morning, longest wait first.

THE OTHER HALF OF A PROMISE ALREADY MADE. The business engagement letter says
*"We will tell you what we need and when, and we will chase it."* Telling them
is built: intake opens a ``RequestedItem`` for every ask and the organizer email
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

PORTED FROM ``parked/satc-system-pre-schema-port``, where this was written
against ``DocumentRecord`` and a ``"Requested"`` status string. That model is
gone: an ASK and an ARRIVAL are now two records (:mod:`satc.models.evidence`),
so the register this walks is ``store.load_requested_items()``. Every change
from the parked original is marked with a comment saying which schema fact
forced it -- the reasoning is the part worth keeping.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from satc.intake import matching

# NO `OUTSTANDING` CONSTANT ANY MORE. The parked module defined
# ``OUTSTANDING = "Requested"`` because `DocStatus` spanned four unrelated
# lifecycles and only one of its values was a debt. `RequestedItem` is nothing
# but asks, and it already answers the question itself: `is_open`. A second
# spelling of the same status string here is a second place to get it wrong.


@dataclass(slots=True)
class Waiting:
    """One outstanding request, as the firm reads it on the morning list."""

    client_id: str
    client: str                 # vault display label; never a TIN
    request_id: str             # was `document_id`: the PK is the ASK, not the paper
    doc_type: str
    asked_for: str              # the prose the client was actually sent
    tax_year: int
    since: date | None          # when we asked, or None if the row carries no date
    arrived: frozenset[str] = frozenset()
    awaiting: frozenset[str] = frozenset()

    def waiting_days(self, today: date | None = None) -> int | None:
        """How long this has been out, or None when the request carries no date.

        None is the answer, not zero. See the sort in :func:`waiting`.

        NOT ``RequestedItem.days_waiting``, which is the same arithmetic without
        the two things this screen needs: an optional ``today`` (the CLI and the
        template both call it bare) and the clamp below. A request dated
        tomorrow -- a typo, or a pack scheduled ahead -- has waited no time at
        all, and a negative number in a "longest wait first" column reads as a
        bug in the list rather than a bug in the date.
        """
        if self.since is None:
            return None
        return max((today or date.today()) - self.since, timedelta(0)).days

    @property
    def needs_every_part(self) -> bool:
        """True when this stays open until every form it names has arrived.

        WAS ``is_bundle``, AND THE RENAME IS THE POINT. `matching.is_bundle`
        answers "does this name more than one form", which was the only question
        the parked code knew about. It is the wrong question here: the standing
        core-income ask sent to every 1040 client names five forms and ends "and
        any other income forms received", so it requires none of them in
        particular. Chasing its missing parts would put a permanent entry on
        this list for a 1099-B and a 1099-G that do not exist -- a worse failure
        than the one the list fixes. `matching.needs_every_part` reads the
        request's own wording for the admission that its list is partial.
        """
        return matching.needs_every_part(self.doc_type, self.asked_for)

    @property
    def named(self) -> int:
        """How many forms this request names. 1 for an ordinary request."""
        return max(len(matching.families(f"{self.doc_type} {self.asked_for}")), 1)

    @property
    def part_way(self) -> str:
        """"2 of 5 here" for a bundle part-way in; empty for anything else."""
        if not self.needs_every_part or not self.arrived:
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
    requests: int = 0           # register rows read, whatever their status
    clients: int = 0            # clients whose register was read
    jobs: int = 0               # work instances on file
    opened_today: int = 0       # outstanding, but asked for today -- not a chase yet

    # TWO FIELDS RENAMED, BECAUSE THE OLD NAMES NOW POINT AT REAL, DIFFERENT
    # THINGS. `documents` counted `DocumentRecord` rows, which were asks and
    # arrivals in one table; a `ReceivedDocument` is now its own record and
    # calling a count of asks "documents" would name the wrong register. And
    # `engagements` counted `load_intake_engagements()`, which is today's
    # `Job` -- while `Engagement` still exists as a different record (the
    # contract, with the fee on it). Keeping either name would read correctly
    # and mean something else.

    @property
    def examined_nothing(self) -> bool:
        """Nothing was looked at, which is a different report from "all clear"."""
        return self.requests == 0 and self.jobs == 0


def waiting(store, *, today: date | None = None) -> Sweep:
    """Every outstanding document request, longest wait first.

    A request naming several forms stays open until all of them arrive (see
    ``service.reconcile_received``), so it carries which have and which have
    not: "still waiting on the 1099-B" is the line that gets a document into
    the office; "still outstanding" is the line that gets skimmed past.
    """
    # The parked version imported `satc.intake.service` inside this function to
    # keep the ingest classifier out of a cold terminal's start-up. It no longer
    # needs to: `RequestedItem.outstanding_parts` answers the same question on
    # the record itself, so nothing here reaches into the service layer at all.
    mart = store.load_mart()
    names = store.names()
    labels = {pc.client_id: pc.display_label for pc in mart.public_clients}
    jobs = len(store.load_jobs())

    rows: list[Waiting] = []
    seen_clients: set[str] = set()
    requests = 0
    opened_today = 0
    for item in store.load_requested_items():
        requests += 1
        seen_clients.add(item.client_id)
        # `is_open`, not a status string. A request that was satisfied, marked
        # not-applicable with a reason, or withdrawn is not a debt.
        if not item.is_open:
            continue
        row = Waiting(
            client_id=item.client_id,
            # The vault's name, then the mart's de-identified label, then the
            # handle itself. Never the TIN: `PublicClient` carries `tin_last4`
            # and `tin_masked` right beside `display_label`, and neither belongs
            # on a screen whose whole job is to be left open on a desk.
            client=names.get(item.client_id) or labels.get(item.client_id, "") or item.client_id,
            request_id=item.request_id,
            doc_type=str(item.doc_type),
            # `request_text`, not `note` -- and it is load-bearing rather than a
            # comment now: reconciliation matches an arrival against this prose.
            asked_for=item.request_text or str(item.doc_type),
            tax_year=item.tax_year,
            since=item.requested_at,
            arrived=frozenset(item.parts or ()),
            # Already empty for a single-form request AND for an open-ended
            # checklist -- see `needs_every_part` above.
            awaiting=frozenset(item.outstanding_parts),
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
    return Sweep(rows=rows, requests=requests, clients=len(seen_clients),
                 jobs=jobs, opened_today=opened_today)
