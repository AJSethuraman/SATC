"""The fact the whole autonomy ladder stands on: did the owner send this unchanged?

Charter §11 names the gap plainly — today the Today queue's dismissal lives in
``session[_DISMISSED]``, gone when the cookie clears, carrying no actor and no
date. Nothing anywhere records "the owner read this draft and sent it as
written." Every later thing this ladder does (streaks, rungs, the digest) is
computed from that record, so it has to exist first, and it has to be a real
recorded fact — same shape as :mod:`satc.models.deliverable`: what, when, who
(derived, never claimed), an id derived from what the thing IS, and durable.

WHAT THIS DOES NOT DO, on purpose:

* No streak, no rung, no template classification. Those are DERIVED from the
  approvals this module records — computed, never stored (principle 3) — and
  are somebody else's slice to build on top of this one.
* No send path of any kind. Recording a decision is not making one, and it is
  not transmitting one (principle 9). This module has no SMTP, no HTTP client,
  no mail library, full stop — the codebase-wide rule is
  ``tests/test_comms_app.py::test_the_comms_area_has_no_send_path``, which AST-
  walks ``satc.comms`` and must keep passing; it does not (yet) walk this
  package, so that guarantee here rests on there being nothing to walk.

ZERO EDITS IS A HASH COMPARISON, NOT A JUDGEMENT (charter §4). ``Approval``
stores the hash of what SATC rendered and the hash of what the owner says they
sent; :attr:`Approval.outcome` is *computed* by comparing them, never trusted
from whichever function built the record. Calling :func:`record_approval` does
not manufacture an approval if the two hashes disagree — it refuses, and names
:func:`record_correction` as the right next step. The system does not grade
its own homework.

WHAT SATC CAN AND CANNOT ACTUALLY OBSERVE HERE, said out loud: nothing watches
the mail client (principle 11a — this machine holds the vault and stays off
the network; it has no way to see what left an outbox it does not touch). So
"what was sent" is never independently verified — it is the owner's own
report, typed or pasted back into SATC, or simply asserted by the "I sent this
exactly as drafted" click, which is what an approval with no separate
``sent_text`` MEANS. That is not a weaker fact than any other in this codebase:
it is the same trust boundary as :func:`~satc.models.deliverable.record_delivery`,
which also cannot check the mail was actually dropped in a box — only a human
can attest that they did the thing, and the actor gate is what makes that
attestation worth recording.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Literal

from satc.models.actor import Actor, require_human

Outcome = Literal["approval", "correction"]

# The five reason codes (charter §6), and nothing else. A correction is
# recorded against a KEY from this dict — never free text as the primary
# record (principle 6a applied to the owner's own input, so a digest can count
# them). The values are the charter's own "Means" column, kept here so a
# refusal can name all five without a second source of truth to drift from it.
REASON_CODES: dict[str, str] = {
    "wrong_fact": "it stated something untrue",
    "wrong_judgment": "the facts were right, the call was wrong",
    "should_not_have_flagged": "nothing needed doing",
    "gave_up": "incomplete or abandoned",
    "missing_capability": "the right idea, but SATC cannot do it",
}


class ApprovalError(Exception):
    """A decision was recorded in a way that would not be defensible later."""


def hash_text(text: str | None) -> str:
    """The identity of a piece of rendered or sent text.

    Deliberately NOT stripped, case-folded, or whitespace-collapsed. Charter §4
    is explicit that a changed comma is a correction, so normalising anything
    here would launder away exactly the edits this record exists to catch.
    """
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def approval_id(*, template_key: str, client_id: str, decided_on: date,
                rendered_hash: str, sent_hash: str, sequence: int = 0) -> str:
    """An id derived from WHAT WAS DECIDED, never from when it was keyed in.

    Recording the same decision twice — a double-click, a page reload, the
    owner checking whether they already logged it — lands on the same id and
    is a no-op rather than a second decision (principle 8).

    WHAT IS DELIBERATELY NOT IN HERE, mirroring ``payment_id`` and
    ``PriceChange.change_id``: WHO decided (``decided_by``) and the REASON
    given for a correction are not part of WHICH decision it is. A row can be
    re-saved with a corrected reason code — the owner reclassifying why they
    made the same edit to the same draft on the same day — and that replaces
    the row rather than filing a second, contradictory decision about one
    event. Nor is ``note`` in here, for the same reason payment notes and price
    notes are not: commentary is not identity.

    WHAT ``sequence`` IS FOR, exactly as in ``payment_id``: two genuinely
    separate decisions can be identical in every recorded respect — the same
    template sent to the same client twice in one day, approved unchanged both
    times, nothing to tell them apart. Nothing in the decision itself can
    distinguish them, so the practice has to say. Left at 0, the ordinary case.
    """
    raw = "|".join([
        template_key.strip(), client_id.strip(), decided_on.isoformat(),
        rendered_hash, sent_hash, str(int(sequence)),
    ])
    return "apr_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class Approval:
    """One decision the owner made about one rendered draft. A fact, not a status.

    ``outcome`` is not a field — see the property below. Storing it as data
    would be exactly the "status that lies the moment anything else changes"
    principle 3 warns about: nobody could then tell whether it was recorded
    honestly or asserted by whichever function happened to call the
    constructor.
    """

    template_key: str
    client_id: str
    decided_on: date
    decided_by: str
    """The actor HANDLE, not the Actor — a stored fact, not an object graph.
    Same choice as ``Deliverable.delivered_by``: a stored Actor is how
    provenance quietly stops round-tripping."""

    rendered_hash: str
    """What SATC rendered — ``hash_text`` of the subject+body it produced."""

    sent_hash: str
    """What the owner reports having sent. Equal to ``rendered_hash`` for an
    approval; different for a correction. See the module docstring for what
    SATC can and cannot actually verify about this value."""

    reason: str = ""
    """A key from :data:`REASON_CODES`. Empty for an approval — a correction
    is the only outcome that carries one, and :func:`record_correction` is the
    only path that can set it."""

    note: str = ""
    sequence: int = 0

    @property
    def approval_id(self) -> str:
        return approval_id(template_key=self.template_key, client_id=self.client_id,
                           decided_on=self.decided_on, rendered_hash=self.rendered_hash,
                           sent_hash=self.sent_hash, sequence=self.sequence)

    @property
    def outcome(self) -> Outcome:
        """Computed by comparing the two hashes. Never asserted, never stored.

        This is the whole point of charter §4: "the system does not grade its
        own homework." Whichever function built this record, whatever the
        owner clicked, the outcome is what the bytes actually say.
        """
        return "approval" if self.rendered_hash == self.sent_hash else "correction"

    @property
    def is_correction(self) -> bool:
        return self.outcome == "correction"

    @property
    def pair(self) -> tuple[str, str]:
        """The (template_key, client_id) pair the charter's ladder is keyed on.

        Charter §4: "A pair is (template_key, client_id). Not a template
        alone: a letter that is right for a retired couple may be wrong for a
        partnership, and the evidence is about the pair."
        """
        return (self.template_key, self.client_id)

    def as_another_one(self, existing) -> "Approval":
        """This decision again, recorded as a genuinely separate one.

        For the case ``approval_id`` cannot resolve on its own: the same
        template, the same client, the same day, the same rendered and sent
        text — and the owner has confirmed this is a second, distinct
        decision rather than the first one being re-saved. Mirrors
        ``Payment.as_another_one`` exactly, including WHY it exists: nothing
        recorded here can tell two such decisions apart, so a human has to.
        """
        taken = {a.approval_id for a in existing}
        candidate = self
        while candidate.approval_id in taken:
            candidate = Approval(
                template_key=candidate.template_key, client_id=candidate.client_id,
                decided_on=candidate.decided_on, decided_by=candidate.decided_by,
                rendered_hash=candidate.rendered_hash, sent_hash=candidate.sent_hash,
                reason=candidate.reason, note=candidate.note,
                sequence=candidate.sequence + 1)
        return candidate


# --- recording a decision (the only door in) --------------------------------


def record_approval(*, actor: Actor, template_key: str, client_id: str,
                    rendered_text: str, sent_text: str | None = None,
                    decided_on: date | None = None, note: str = "") -> Approval:
    """Record that the owner sent a draft exactly as SATC rendered it.

    Refuses a model outright — a "the owner approved this" fact recorded by
    anything other than the owner is the one fabrication this whole ladder
    cannot survive (principle 6, charter §11).

    ``sent_text`` is optional and almost always omitted: an approval IS the
    claim "what I sent equals what you rendered", so when it is not given the
    sent hash is taken to be the rendered hash. If it IS given and disagrees,
    this refuses rather than quietly recording a correction under an
    approval's name — a correction needs a reason from the finite five, which
    this function has no way to collect, so the caller is sent to the one that
    can (principle 5, principle 10).
    """
    require_human(actor, "record that a draft was approved and sent unchanged",
                 instead="propose it and let the owner record what actually happened")
    key = template_key.strip()
    client = client_id.strip()
    if not key:
        raise ApprovalError(
            "An approval has to name WHICH template was reviewed — nothing "
            "else can tell one client-facing letter from another.")
    if not client:
        raise ApprovalError(
            "An approval has to name WHICH client the draft was for — the "
            "ladder counts streaks per (template, client) pair, never a "
            "template alone.")

    rendered_hash = hash_text(rendered_text)
    sent_hash = rendered_hash if sent_text is None else hash_text(sent_text)
    if sent_hash != rendered_hash:
        raise ApprovalError(
            "What was sent does not match what SATC rendered — that is a "
            "correction, not an approval, however small the difference. Call "
            "record_correction with one of the five reasons: "
            + ", ".join(sorted(REASON_CODES)) + ".")

    return Approval(template_key=key, client_id=client,
                    decided_on=decided_on or date.today(), decided_by=actor.handle,
                    rendered_hash=rendered_hash, sent_hash=sent_hash, note=note.strip())


def record_correction(*, actor: Actor, template_key: str, client_id: str,
                      rendered_text: str, sent_text: str, reason: str,
                      decided_on: date | None = None, note: str = "") -> Approval:
    """Record that the owner changed a draft before sending it, and why.

    Refuses a model outright, for the same reason as :func:`record_approval`.

    ``reason`` must be a key from :data:`REASON_CODES` — the finite five
    (charter §6). A free-text explanation is welcome in ``note`` but never
    stands in for the code: it cannot be counted, and this ladder exists to be
    counted (principle 6a).
    """
    require_human(actor, "record a correction to a draft",
                 instead="propose it and let the owner record what actually happened")
    key = template_key.strip()
    client = client_id.strip()
    if not key:
        raise ApprovalError(
            "A correction has to name WHICH template was reviewed — nothing "
            "else can tell one client-facing letter from another.")
    if not client:
        raise ApprovalError(
            "A correction has to name WHICH client the draft was for — the "
            "ladder counts streaks per (template, client) pair, never a "
            "template alone.")
    if reason not in REASON_CODES:
        raise ApprovalError(
            f"{reason!r} is not one of the five reasons a correction can be "
            f"recorded for: {', '.join(sorted(REASON_CODES))}. Pick one of "
            f"those — a correction is never recorded as free text alone.")

    rendered_hash = hash_text(rendered_text)
    sent_hash = hash_text(sent_text)
    if sent_hash == rendered_hash:
        raise ApprovalError(
            "What you say was sent is byte-identical to what SATC rendered — "
            "there is nothing to correct here. If it went out unchanged, call "
            "record_approval instead.")

    return Approval(template_key=key, client_id=client,
                    decided_on=decided_on or date.today(), decided_by=actor.handle,
                    rendered_hash=rendered_hash, sent_hash=sent_hash,
                    reason=reason, note=note.strip())


# --- reading the record back -------------------------------------------------
#
# Pure functions over a list the caller already loaded (the same shape as
# satc.models.deliverable.delivery_of and satc.billing.payment's ledger
# functions) — this module knows nothing about SQLite. See
# satc.persistence.store.save_approvals / load_approvals for the store side.


def approvals_for(approvals, pair: tuple[str, str]) -> list[Approval]:
    """Every recorded decision for one (template_key, client_id) pair, oldest first.

    Oldest first because the ladder reads this as a timeline: a streak is
    "how many *consecutive* approvals since the last correction", and that
    question can only be answered in time order.
    """
    template_key, client_id = pair
    mine = [a for a in approvals if a.pair == (template_key, client_id)]
    return sorted(mine, key=lambda a: (a.decided_on, a.approval_id))


def all_approvals(approvals) -> list[Approval]:
    """The whole record, oldest first, then stably ordered within a day."""
    return sorted(approvals,
                  key=lambda a: (a.decided_on, a.template_key, a.client_id, a.approval_id))


def merge(existing, arriving) -> tuple[list[Approval], list[Approval]]:
    """Fold newly-recorded decisions into a ledger, ignoring ones already there.

    Returns ``(ledger, newly_added)``. Principle 8: recording the same
    decision twice — replaying a page, re-importing an export of this table —
    is a no-op rather than a duplicate, because the id is derived from what
    the decision IS.
    """
    ledger = list(existing)
    seen = {a.approval_id for a in ledger}
    added: list[Approval] = []
    for item in arriving:
        if item.approval_id in seen:
            continue
        seen.add(item.approval_id)
        ledger.append(item)
        added.append(item)
    return ledger, added
