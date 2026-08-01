"""The prior-year omission diff — the junior's most valuable instinct.

Tick-and-tie proves that every figure on a return traces to a document. It is
structurally incapable of catching the document that never arrived: you cannot
tie out a 1099-INT nobody sent. That gap is where real money hides, and the way
a good staff accountant closes it is embarrassingly simple —

    *"Last year you had a 1099-INT from Fidelity. This year we have nothing."*

That single question catches a closed account the client forgot to mention, a
brokerage that changed custodian, a K-1 that is late rather than gone, and the
consolidated 1099 that silently lost a page. It requires no judgment and no
model: it is a set difference between two years of the document register, which
is exactly the kind of grind doctrine rule 8 says to remove from the human.

What it is NOT: a claim that a missing document is *wrong*. People genuinely
close accounts. Every omission is a QUESTION to ask, never a finding — which is
why the report separates what changed from what it means, and why nothing here
writes anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Register statuses that mean the document is actually in hand. "Requested"
# deliberately is not one — asking for something is not receiving it.
IN_HAND = {"Received", "Signed"}
OUTSTANDING = {"Requested"}


@dataclass(frozen=True, slots=True)
class DocumentKind:
    """A document type as the diff reasons about it, with its human detail.

    Keyed on ``doc_type`` because that is what the register and the classifier
    agree on. ``detail`` carries the prose (the payer, the account) so the
    question the owner asks the client is specific — "your 1099-INT" is a worse
    question than "your 1099-INT from Fidelity".
    """

    doc_type: str
    detail: str = ""

    def __str__(self) -> str:
        return f"{self.doc_type} — {self.detail}" if self.detail else self.doc_type


@dataclass(slots=True)
class OmissionReport:
    """What changed between two years of a client's document register."""

    client_id: str
    prior_year: int
    current_year: int
    missing: list[DocumentKind] = field(default_factory=list)
    """In hand last year, nothing this year — not even requested. THE ALARM."""

    outstanding: list[DocumentKind] = field(default_factory=list)
    """Asked for this year and still not in. Chasing, not detective work."""

    new_this_year: list[DocumentKind] = field(default_factory=list)
    """Arrived this year with no prior-year counterpart — a new account, or a
    life event nobody mentioned. Worth a glance, not an alarm."""

    carried: list[DocumentKind] = field(default_factory=list)
    """Present both years. The boring majority, and the denominator that makes
    the other numbers mean something."""

    @property
    def has_questions(self) -> bool:
        return bool(self.missing or self.outstanding)

    @property
    def prior_year_count(self) -> int:
        return len(self.missing) + len(self.carried)

    def summary_line(self) -> str:
        """One sentence for a dashboard row."""
        if not self.prior_year_count:
            return f"No {self.prior_year} documents on file to compare against."
        if not self.has_questions:
            return (f"Everything from {self.prior_year} has a {self.current_year} "
                    f"counterpart ({len(self.carried)} documents).")
        bits = []
        if self.missing:
            bits.append(f"{len(self.missing)} not seen this year")
        if self.outstanding:
            bits.append(f"{len(self.outstanding)} still outstanding")
        return f"{' · '.join(bits)} of {self.prior_year_count} on file for {self.prior_year}."


def _kinds(documents, *, statuses: set[str] | None = None) -> dict[str, DocumentKind]:
    """Index documents by type, keeping the first detail seen for each."""
    out: dict[str, DocumentKind] = {}
    for doc in documents:
        if statuses is not None and str(getattr(doc, "status", "")) not in statuses:
            continue
        doc_type = (getattr(doc, "doc_type", "") or "").strip()
        if not doc_type or doc_type in out:
            continue
        out[doc_type] = DocumentKind(doc_type, (getattr(doc, "note", "") or "").strip())
    return out


def omission_diff(documents, *, client_id: str, prior_year: int,
                  current_year: int) -> OmissionReport:
    """Compare two years of one client's document register.

    ``documents`` may be the whole register; it is narrowed here. Nothing is
    written — this is a question generator, not a decision.
    """
    mine = [d for d in documents if getattr(d, "client_id", None) == client_id]
    prior = _kinds([d for d in mine if getattr(d, "tax_year", None) == prior_year],
                   statuses=IN_HAND)
    current_all = [d for d in mine if getattr(d, "tax_year", None) == current_year]
    current_in_hand = _kinds(current_all, statuses=IN_HAND)
    current_outstanding = _kinds(current_all, statuses=OUTSTANDING)

    # A prior-year document is "missing" only if this year has NO trace of it —
    # neither received nor even requested. Something already on the chase list is
    # a different problem with a different message.
    missing = [k for t, k in prior.items()
               if t not in current_in_hand and t not in current_outstanding]
    outstanding = [k for t, k in current_outstanding.items() if t in prior]
    carried = [k for t, k in prior.items() if t in current_in_hand]
    new_this_year = [k for t, k in current_in_hand.items() if t not in prior]

    key = lambda k: k.doc_type  # noqa: E731
    return OmissionReport(
        client_id=client_id, prior_year=prior_year, current_year=current_year,
        missing=sorted(missing, key=key), outstanding=sorted(outstanding, key=key),
        new_this_year=sorted(new_this_year, key=key), carried=sorted(carried, key=key))


def opening_request_list(documents, *, client_id: str, prior_year: int) -> list[DocumentKind]:
    """Last year's documents, as this year's expected list.

    The other half of rollover: rather than asking a returning client to answer
    an interview from scratch, start from what they actually sent last year. The
    research called this the single highest-leverage automated-junior move, and
    it is the same set the diff measures against.
    """
    return sorted(_kinds([d for d in documents
                          if getattr(d, "client_id", None) == client_id
                          and getattr(d, "tax_year", None) == prior_year],
                         statuses=IN_HAND).values(), key=lambda k: k.doc_type)


def as_questions(report: OmissionReport) -> list[str]:
    """The report as plain questions to put to the client.

    Phrased as questions on purpose. A missing document is not a finding — people
    close accounts, sell rentals, change jobs. The value is in asking, and the
    answer ("I closed that account in March") is itself the record that the gap
    was considered rather than missed.
    """
    lines: list[str] = []
    for kind in report.missing:
        detail = f" ({kind.detail})" if kind.detail else ""
        lines.append(
            f"Last year we had your {kind.doc_type}{detail}. We have nothing for "
            f"{report.current_year} — is that still expected, or has it ended?")
    for kind in report.outstanding:
        lines.append(
            f"We asked for your {kind.doc_type} for {report.current_year} and "
            f"haven't received it yet.")
    return lines
