"""Is this file ready to work on? — the guard the three-way blocking split buys.

*"Do not start work on a return until you are sure all the information has been
provided"* is the most-repeated advice in tax practice, and it is wrong as
stated. The real-world version, from a practitioner's own client letter, is:

    "I won't work on a file until data is complete besides a late K-1 or
     brokerage statement."

Those are different rules, and the difference is the whole product. A file that
is complete except a K-1 that cannot exist until September is *ready to prep* and
*not ready to file*. A single "complete?" boolean cannot say that, which is why
:class:`~satc.models.evidence.RequestedItem` carries a blocking CLASS rather than
a flag.

So there are two thresholds, and readiness is **recorded, not just computed** —
what was outstanding, what was waived and why, and that a human decided to
proceed anyway. That record is the §1.6695-2(d) "normal office procedures ...
routinely followed" evidence, and a silent bypass destroys it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from satc.models.actor import Actor, require_human
from satc.models.evidence import RequestedItem


@dataclass(slots=True)
class Readiness:
    """Whether a file can be worked, filed, or neither — and what is in the way."""

    client_id: str
    tax_year: int
    blocking_open: list[RequestedItem] = field(default_factory=list)
    expected_late_open: list[RequestedItem] = field(default_factory=list)
    other_open: list[RequestedItem] = field(default_factory=list)
    not_applicable: list[RequestedItem] = field(default_factory=list)

    @property
    def can_start_prep(self) -> bool:
        """Blocking items are in. Expected-late ones may still be outstanding."""
        return not self.blocking_open

    @property
    def can_transmit(self) -> bool:
        """Everything that blocks a filing is in.

        Pub 1345: the ERO must hold the W-2, W-2G and 1099-R (or a Form 4852)
        before originating. An expected-late K-1 blocks here even though it did
        not block prep.
        """
        return not self.blocking_open and not self.expected_late_open

    @property
    def open_count(self) -> int:
        return len(self.blocking_open) + len(self.expected_late_open) + len(self.other_open)

    def why_not_prep(self) -> str:
        if self.can_start_prep:
            return ""
        names = ", ".join(i.doc_type for i in self.blocking_open)
        return (f"{names} {'is' if len(self.blocking_open) == 1 else 'are'} still "
                f"outstanding, and {'it blocks' if len(self.blocking_open) == 1 else 'they block'} "
                f"starting prep.")

    def why_not_transmit(self) -> str:
        if self.can_transmit:
            return ""
        waiting = self.blocking_open + self.expected_late_open
        names = ", ".join(i.doc_type for i in waiting)
        return (f"{names} must be in hand before this return can be transmitted "
                f"(IRS Pub 1345).")

    def summary_line(self) -> str:
        if self.can_transmit:
            return "Everything is in — ready to prep and ready to file."
        if self.can_start_prep:
            late = ", ".join(i.doc_type for i in self.expected_late_open)
            return f"Ready to prep. Still waiting on {late} before it can be filed."
        return self.why_not_prep()


def assess(items, *, client_id: str, tax_year: int) -> Readiness:
    """Sort a client's requests into what blocks what. Reads only."""
    mine = [i for i in items
            if i.client_id == client_id and i.tax_year == tax_year]
    out = Readiness(client_id=client_id, tax_year=tax_year)
    for item in mine:
        if item.status == "not_applicable":
            out.not_applicable.append(item)
        elif not item.is_open:
            continue
        elif item.blocking == "blocking":
            out.blocking_open.append(item)
        elif item.blocking == "expected_late":
            out.expected_late_open.append(item)
        else:
            out.other_open.append(item)
    return out


@dataclass(slots=True)
class ReadinessDecision:
    """A human's recorded decision to proceed — the §1.6695-2(d) evidence.

    Computing readiness is not the point; *recording that someone looked and
    decided* is. An override with a reason and a timestamp preserves the
    "normal office procedures ... reasonably designed and routinely followed"
    defence. A silent bypass destroys it, which is why this cannot be created
    without a reason and cannot be created by a model.
    """

    client_id: str
    tax_year: int
    decided_by: Actor
    decided_at: datetime
    proceeded_despite: tuple[str, ...] = ()
    reason: str = ""

    @property
    def was_override(self) -> bool:
        return bool(self.proceeded_despite)


def decide_to_proceed(readiness: Readiness, *, actor: Actor, reason: str = "",
                      now: datetime | None = None) -> ReadinessDecision:
    """Record that the owner started work, and on what basis.

    Refuses a model outright, and refuses a human who is overriding a blocking
    item without saying why (doctrine rule 3 — the message names the fix).
    """
    require_human(actor, "decide a file is ready to work",
                  instead="surface what is outstanding and let the owner decide")

    outstanding = tuple(i.doc_type for i in readiness.blocking_open)
    if outstanding and not (reason or "").strip():
        raise ValueError(
            f"Starting prep with {', '.join(outstanding)} still outstanding needs a "
            f"reason. Record why — that note is the evidence your procedures were "
            f"followed, and a silent override is worse than not overriding.")
    return ReadinessDecision(
        client_id=readiness.client_id, tax_year=readiness.tax_year,
        decided_by=actor, decided_at=now or datetime.now(),
        proceeded_despite=outstanding, reason=reason.strip())


def blocking_class_for(doc_type: str, blocking_docs=()) -> str:
    """Classify a request against a rule's blocking list.

    ``blocking_docs`` comes from the obligation rule (cited to Pub 1345 in
    ``configs/obligations/federal.yaml``), so what blocks is config, not code.
    Expected-late is a judgement about the DOCUMENT — a K-1 or a consolidated
    1099-B genuinely cannot exist early in the season.
    """
    normalised = (doc_type or "").strip().upper()
    if any(normalised == str(b).strip().upper() for b in blocking_docs):
        return "blocking"
    if normalised.startswith("K-1") or normalised in ("1099-B", "1099-CONSOLIDATED"):
        return "expected_late"
    return "non_blocking"
