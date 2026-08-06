"""THE NIGHTLY TRAP DRILL — docs/AUTONOMY-CHARTER.md section 7.

Every night, run the whole engine against a SYNTHETIC practice invented for
exactly this purpose, seeded with the shape of real defects this project has
shipped (docs/BRIEFING.md section 6, and the charter itself). Each trap
declares one correct behaviour — always a refusal or a visible flag, never
silence — and a miss demotes the capability that trap guards.

WHY THIS EXISTS RATHER THAN TRUSTING THE ORDINARY TEST SUITE: principle 12.
``pytest`` proves these rules hold *today, on this branch*. The drill proves
they still hold *tonight, against the code actually running* — which is the
thing a streak cannot tell you on its own, because a streak is a check that
has only ever passed (charter section 10, principle 12). Somebody has to be
the part that can fail.

WHAT A TRAP IS. Two halves that must agree:

* An entry in ``configs/autonomy/traps.yaml`` — key, the capability it
  guards, why it exists, and which shipped defect it is shaped like. Owner-
  readable, the same as ``firm_policy.yaml``.
* A check function in :data:`_CHECKS`, keyed identically. The synthetic
  scenario and the assertion are bespoke code; nothing about a defect this
  specific can be expressed as data alone.

:func:`run_drill` refuses to let the two drift apart silently: a key in the
config with no matching function is a MISS (not a pass, not a skip), and
:data:`_CHECKS` is exercised (see ``tests/test_traps.py``) to prove the
reverse never happens undetected either.

TRIPWIRES FAIL TOWARD THE CLICK. If the config will not load, if the
synthetic practice will not build, or if a check function raises anything —
that is a MISS, exactly like a trap whose defect is genuinely present.
:func:`run_drill` itself never raises for any of these; it always returns a
:class:`DrillResult` with ``ran=True``; a nightly job that could not check
anything still SAYS SO, loudly, rather than leaving a gap in the digest that
reads as "nothing to report."

THE DRILL WRITES NOTHING TO THE REAL PRACTICE. Every fact a trap needs is
built fresh, in memory, by :func:`_build_synthetic_practice`, and every id in
it carries the ``SATC-DRILL-`` prefix so it can never be mistaken for a real
client. Nothing here imports :mod:`satc.persistence`, opens a
:class:`~satc.persistence.store.SATCStore`, or touches
:data:`satc.app.state.STATE` — see
``tests/test_traps.py::test_the_drill_never_touches_the_store`` for the
version of that claim a test can actually fail.

WHAT "DEMOTES" MEANS HERE. This module has no streak ledger to write to —
that record does not exist yet (charter section 11). A :class:`DrillResult`
names which capabilities a miss demotes; wiring that into an actual streak
store is the next piece, built against this seam.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable

from satc.billing.invoice import Invoice
from satc.billing.payment import Method, Payment
from satc.comms.library import CommsTemplate
from satc.config import CONFIG_ROOT, ConfigError, read_yaml
from satc.models.evidence import RequestedItem

TRAPS_FILE = "traps.yaml"

# The sentinel capability demoted when the drill cannot even read its own
# config. Not a real functional area — a signal that NOTHING was actually
# checked tonight, which is worse than any single trap missing.
_CONFIG_CAPABILITY = "autonomy.drill"


# --- the result shape -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrapResult:
    """One trap's verdict for one drill run."""

    key: str
    capability: str
    expected: str
    observed: str
    passed: bool
    why: str
    """One line, in the owner's language, auditable without opening anything
    — the same discipline as :class:`~satc.actions.propose.ProposedAction.why`
    (principle 13)."""


@dataclass(frozen=True, slots=True)
class DrillResult:
    """Everything one night's drill found."""

    ran: bool
    """Whether the drill actually executed. Always ``True`` by construction —
    :func:`run_drill` never raises, so a caller can never mistake "the drill
    itself never ran" for "every trap happened to pass". A cron job that
    failed to invoke this function at all is the one case this field cannot
    speak to, which is exactly why the CLI drill command's exit code (not
    this field) is what a scheduler should watch."""

    today: date
    traps: tuple[TrapResult, ...]
    misses: tuple[str, ...]
    """Keys of every trap that did not pass, in declared order."""

    demotions: tuple[str, ...]
    """Capabilities a miss demotes, deduplicated and sorted. One trap missing
    demotes exactly the capability it guards — never its neighbours."""


# --- synthetic practice ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SyntheticPractice:
    """A tiny in-memory practice, invented fresh for one drill run.

    Nothing here is ever handed to a store or saved anywhere. Every id carries
    the ``SATC-DRILL-`` prefix so it can never collide with, or be mistaken
    for, a real client — see :func:`_build_synthetic_practice`.
    """

    today: date

    # -- zero_line_invoice ----------------------------------------------------
    zero_line_invoice: Invoice

    # -- stale_chase_date -------------------------------------------------------
    chase_requested: tuple[RequestedItem, ...]
    chase_client_id: str
    chase_tax_year: int

    # -- cross_client_merge -----------------------------------------------------
    cross_client_template: CommsTemplate
    cross_client_alice_values: dict[str, str]
    cross_client_bob_values: dict[str, str]
    cross_client_leaked_value: str

    # -- duplicate_payment --------------------------------------------------------
    duplicate_payment: Payment
    duplicate_payment_replay: Payment

    # -- stale_cheque_matches_future_invoice ---------------------------------------
    predating_invoice: Invoice
    predating_payment: Payment


def _build_synthetic_practice(today: date) -> SyntheticPractice:
    """Invent the whole practice fresh, from nothing on disk.

    This is the one place in the module that could accidentally reach for a
    real store or a real client id, which is exactly why it is kept small,
    kept in one place, and read closely: every fact every trap needs is built
    right here, once, and handed to every check as plain data.
    """
    zero_line = Invoice(invoice_id="SATC-DRILL-0000", client_id="SATC-DRILL-ZERO",
                        tax_year=today.year)

    chase_client = "SATC-DRILL-CHASE"
    chase_requested = (
        RequestedItem(request_id="SATC-DRILL-REQ-0001", client_id=chase_client,
                     tax_year=today.year, doc_type="W-2", blocking="blocking",
                     status="outstanding", requested_at=today - timedelta(days=20)),
    )

    cross_client_template = CommsTemplate(
        key="_drill_cross_client", name="Drill: cross-client merge check",
        kind="email", description="",
        subject="An update for {client_name}",
        body="Hi {client_name}, your balance due is {balance_due}.")

    dup_kwargs = dict(client_id="SATC-DRILL-PAY", amount=Decimal("450.00"),
                      received_on=today, method=Method.CHECK,
                      reference="drill-check-0001")
    # TWO separately-constructed objects, on purpose — this is what "the same
    # deposit read a second time" actually looks like: nobody hands the
    # engine the SAME Python object twice, they hand it the same FACTS twice.
    duplicate_payment = Payment(**dup_kwargs)
    duplicate_payment_replay = Payment(**dup_kwargs)

    predating_invoice = Invoice(invoice_id="SATC-DRILL-1999", client_id="SATC-DRILL-STALE",
                                tax_year=today.year)
    predating_invoice.add("return_1040")
    predating_invoice.issue(on=today)
    predating_payment = Payment(
        client_id="SATC-DRILL-STALE", amount=predating_invoice.total,
        # A quarter-century before the invoice existed — deliberately computed
        # off `today` rather than hardcoded to a literal 1999, so the trap
        # keeps working whenever the drill is actually run.
        received_on=today - timedelta(days=365 * 25),
        method=Method.CHECK, reference="")

    return SyntheticPractice(
        today=today,
        zero_line_invoice=zero_line,
        chase_requested=chase_requested, chase_client_id=chase_client,
        chase_tax_year=today.year,
        cross_client_template=cross_client_template,
        cross_client_alice_values={"client_name": "Alice", "balance_due": "$500"},
        cross_client_bob_values={"client_name": "Bob"},
        cross_client_leaked_value="$500",
        duplicate_payment=duplicate_payment,
        duplicate_payment_replay=duplicate_payment_replay,
        predating_invoice=predating_invoice, predating_payment=predating_payment)


# --- the individual checks ---------------------------------------------------
#
# Each returns (passed, expected, observed, why). Local imports throughout —
# deliberately, not for import-cost reasons: a check that resolves the
# function it is testing FRESH on every call is a check a test can actually
# mutation-test, by monkeypatching the module attribute the function lives on
# rather than a name this module bound for itself at import time. See
# tests/test_traps.py's mutation table.

CheckResult = tuple[bool, str, str, str]


def _check_zero_line_invoice(practice: SyntheticPractice) -> CheckResult:
    from satc.billing.invoice import BillingError

    expected = "issuing an invoice with no lines on it is refused"
    inv = practice.zero_line_invoice
    try:
        inv.issue(on=practice.today)
    except BillingError as exc:
        return True, expected, f"refused: {exc}", "the guard held — nothing went out."
    return False, expected, (
        f"issued anyway as {inv.invoice_id}, total ${inv.total:,.2f}"
    ), (
        f"Invoice {inv.invoice_id} for client {inv.client_id} was issued with no "
        f"lines on it — a bill for $0.00 against work that was done, and it would "
        f"sit in the register looking ordinary."
    )


def _check_stale_chase_date(practice: SyntheticPractice) -> CheckResult:
    from satc.actions.propose import chase_outstanding

    requested_at = practice.chase_requested[0].requested_at
    expected_days = (practice.today - requested_at).days
    expected = (
        f"a chase generated against {practice.today.isoformat()} reports the "
        f"document as {expected_days} days outstanding — computed against TODAY, "
        f"never a cached or hardcoded date"
    )
    action = chase_outstanding(
        practice.chase_requested, client_id=practice.chase_client_id,
        tax_year=practice.chase_tax_year, today=practice.today)
    if action is None:
        return False, expected, "no chase was proposed at all", (
            f"A document outstanding {expected_days} days — well past the "
            f"3-day default — produced no chase. Either the day count is being "
            f"read off the wrong clock, or the request is being compared "
            f"against the wrong date entirely."
        )
    observed = action.why
    if str(expected_days) not in observed:
        return False, expected, observed, (
            f"The chase's own wording does not name {expected_days} days — the "
            f"number {practice.today.isoformat()} actually implies. A chase "
            f"whose day-count does not move with the calendar is a chase whose "
            f"date has gone stale."
        )
    return True, expected, observed, "the day-count tracks the date the drill actually ran on."


def _check_cross_client_merge(practice: SyntheticPractice) -> CheckResult:
    from satc.comms.render import render

    expected = (
        "rendering Bob's draft after Alice's carries none of Alice's facts, and "
        "marks Bob's own missing field unfilled rather than reusing Alice's value"
    )
    render(practice.cross_client_template, practice.cross_client_alice_values)
    bob = render(practice.cross_client_template, practice.cross_client_bob_values)
    leaked = practice.cross_client_leaked_value
    observed = f"Bob's subject: {bob.subject!r}; body: {bob.body!r}; unfilled: {bob.unfilled}"
    if leaked in bob.subject or leaked in bob.body:
        return False, expected, observed, (
            f"Bob's rendered draft contains {leaked!r} — a fact that was only "
            f"ever true of Alice. Two clients rendered back to back must never "
            f"share state; this is the merge that puts one client's fact in "
            f"another client's letter."
        )
    if "balance_due" not in bob.unfilled:
        return False, expected, observed, (
            "Bob supplied no balance_due, but the render did not mark it "
            "unfilled — the slot was filled from somewhere other than Bob's own "
            "facts."
        )
    return True, expected, observed, "each client's draft carried only its own facts."


def _check_duplicate_payment(practice: SyntheticPractice) -> CheckResult:
    from satc.billing.payment import merge

    expected = "a payment that arrives a second time merges into the existing record, adding nothing new"
    ledger, added = merge([practice.duplicate_payment], [practice.duplicate_payment_replay])
    observed = f"{len(added)} new payment(s) recorded; ledger now holds {len(ledger)}"
    if added:
        amount = practice.duplicate_payment.amount
        return False, expected, observed, (
            f"The same ${amount} check, read a second time with identical "
            f"client, amount, date, method and reference, was recorded as new "
            f"money. That double-counts revenue that was never actually "
            f"received twice."
        )
    return True, expected, observed, "the replay was recognised and folded in as a no-op."


def _check_stale_cheque_matches_future_invoice(practice: SyntheticPractice) -> CheckResult:
    from satc.billing.payment import reconcile

    expected = "a payment dated before any open invoice existed is never auto-matched to one"
    match = reconcile(practice.predating_payment, [practice.predating_invoice])
    observed = (
        f"basis={match.basis.value}, resolved={match.is_resolved}, "
        f"candidates={match.candidates}"
    )
    if match.is_resolved:
        payment = practice.predating_payment
        invoice = practice.predating_invoice
        return False, expected, observed, (
            f"${payment.amount} dated {payment.received_on} was matched to "
            f"invoice {match.invoice_id}, issued {invoice.issued_on} — decades "
            f"after the money supposedly arrived. Nobody decided this; the "
            f"amount happened to line up."
        )
    return True, expected, observed, "the mismatched dates were refused rather than matched on amount alone."


_CHECKS: dict[str, Callable[[SyntheticPractice], CheckResult]] = {
    "zero_line_invoice": _check_zero_line_invoice,
    "stale_chase_date": _check_stale_chase_date,
    "cross_client_merge": _check_cross_client_merge,
    "duplicate_payment": _check_duplicate_payment,
    "stale_cheque_matches_future_invoice": _check_stale_cheque_matches_future_invoice,
}


# --- config -------------------------------------------------------------------


def _load_declared_traps(config_root: Path | None) -> list[dict[str, str]]:
    """Read ``configs/autonomy/traps.yaml``. Raises on anything short of a
    clean list of (key, capability) pairs — refuse rather than default
    (principle 5): a trap silently missing its capability cannot be demoted
    correctly, and a demotion aimed at nothing is worse than an obvious error.
    """
    path = (config_root or CONFIG_ROOT) / "autonomy" / TRAPS_FILE
    data = read_yaml(path)
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must be a mapping")
    entries = data.get("traps")
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{path} declares no traps")

    declared: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ConfigError(f"A trap entry in {path} is not a mapping: {entry!r}")
        key = str(entry.get("key", "")).strip()
        capability = str(entry.get("capability", "")).strip()
        if not key or not capability:
            raise ConfigError(
                f"A trap in {path} is missing a key or a capability: {entry!r}")
        if key in seen:
            raise ConfigError(f"Duplicate trap key {key!r} in {path}")
        seen.add(key)
        summary = " ".join(str(entry.get("summary", "")).split())
        declared.append({"key": key, "capability": capability, "summary": summary})
    return declared


# --- the drill ------------------------------------------------------------------


def run_drill(*, today: date, config_root: Path | None = None) -> DrillResult:
    """Run every declared trap against a fresh synthetic practice.

    Never raises. Every way a trap could fail to even run — the config will
    not load, the synthetic practice will not build, an individual check
    raises — is caught here and turned into a MISS, never a skip (charter
    section 7: tripwires fail toward the click).
    """
    try:
        declared = _load_declared_traps(config_root)
    except Exception as exc:  # noqa: BLE001 - this IS the "cannot run" path
        # Nothing below can be checked without knowing what to check. One row,
        # naming the one thing broken, rather than a result that looks empty
        # (and therefore looks clean) because nothing could be loaded.
        result = TrapResult(
            key="_config", capability=_CONFIG_CAPABILITY,
            expected="configs/autonomy/traps.yaml declares at least one trap",
            observed=f"could not load: {exc}", passed=False,
            why=(f"The drill's own config would not load, so NOTHING was "
                 f"actually checked tonight: {exc}"))
        return DrillResult(ran=True, today=today, traps=(result,),
                           misses=(result.key,), demotions=(_CONFIG_CAPABILITY,))

    try:
        practice = _build_synthetic_practice(today)
    except Exception as exc:  # noqa: BLE001 - this IS the "cannot run" path
        traps = tuple(
            TrapResult(
                key=d["key"], capability=d["capability"],
                expected=d["summary"] or "the trap runs and passes",
                observed=f"the synthetic practice would not build: {exc}",
                passed=False,
                why=(f"{d['key']} could not be checked — the drill's own "
                     f"synthetic practice failed to build ({exc}). A tripwire "
                     f"that cannot run is a miss, not a skip."))
            for d in declared)
        demotions = tuple(sorted({t.capability for t in traps}))
        return DrillResult(ran=True, today=today, traps=traps,
                           misses=tuple(t.key for t in traps), demotions=demotions)

    traps: list[TrapResult] = []
    for d in declared:
        check = _CHECKS.get(d["key"])
        if check is None:
            traps.append(TrapResult(
                key=d["key"], capability=d["capability"],
                expected=d["summary"] or "a check exists for this trap",
                observed="no check function is registered for this key",
                passed=False,
                why=(f"configs/autonomy/traps.yaml declares {d['key']!r} but "
                     f"satc/autonomy/traps.py has no matching check function. "
                     f"A trap the engine cannot run is a miss, not a pass.")))
            continue
        try:
            passed, expected, observed, why = check(practice)
        except Exception as exc:  # noqa: BLE001 - this IS the "cannot run" path
            traps.append(TrapResult(
                key=d["key"], capability=d["capability"],
                expected=d["summary"] or "the trap runs and passes",
                observed=f"the check raised: {exc}", passed=False,
                why=(f"{d['key']} could not run ({exc}). A tripwire that "
                     f"cannot run counts as a miss, never a skip.")))
            continue
        traps.append(TrapResult(key=d["key"], capability=d["capability"],
                                expected=expected, observed=observed,
                                passed=passed, why=why))

    misses = tuple(t.key for t in traps if not t.passed)
    demotions = tuple(sorted({t.capability for t in traps if not t.passed}))
    return DrillResult(ran=True, today=today, traps=tuple(traps),
                       misses=misses, demotions=demotions)
