"""AUTONOMY — the ladder, the digest, and the one screen that can widen it.

Three routes, and nothing here decides anything a human did not:

  GET  /autonomy               the ladder — every (template, client) pair,
                                its rung, its streak, why
  GET  /autonomy/digest        today's digest, or a past day's (?day=)
  POST /autonomy/precondition  record that a precondition was met

READ FROM ENGINE STATE, NEVER FROM MODEL PROSE. Every number on these two
screens is counted by :mod:`satc.autonomy.digest` from recorded facts this
view gathers and hands over; nothing here composes a sentence a model wrote,
and nothing here is generated. See ``tests/test_digest.py`` for the AST test
that makes that a checked claim rather than an intention.

WHAT THIS FILE DOES NOT DO. It does not compute a streak, a rung, or a gate —
those live in :mod:`satc.autonomy.ladder` and :mod:`satc.autonomy.preconditions`
and this view calls them, the same discipline
:mod:`satc.app.billing_views` holds toward :mod:`satc.billing`. It records
nothing except a precondition confirmation, and even that goes through
:func:`satc.autonomy.preconditions.record_precondition`, which refuses a
non-human actor before this file ever sees the result.

A STOPGAP PERSISTENCE SEAM, NAMED AS SUCH. ``satc.persistence.store.SATCStore``
already has ``save_approvals``/``load_approvals`` (charter §11's ledger). It
has nothing yet for precondition confirmations (charter §3) — that seam has
not been built. Rather than reach into ``store.py`` to add it (out of scope
for this slice) or silently drop every confirmation the owner records, this
file keeps a small JSON ledger next to the store's own database. It is real,
durable, and actor-gated the same way the approval ledger is; it is NOT where
this belongs long-term. See the closing report on this slice for exactly what
to replace it with.

WHAT IS HONESTLY MISSING FOR "actions proposed" AND THE DRILL, on a day other
than today: neither has a historical record anywhere in this codebase (see
``satc.autonomy.digest``'s module docstring). This view supplies both LIVE,
for today only, and an empty sequence otherwise — never a fabricated count
for a day nobody recorded one for.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from flask import Blueprint, redirect, render_template, request, url_for

from satc.app.state import STATE, acting_actor
from satc.autonomy.approval import REASON_CODES
from satc.autonomy.digest import Digest, Proposed, Scoreboard, digest_for, week_for
from satc.autonomy.ladder import load_autonomy_policy
from satc.autonomy.preconditions import (
    ALL_PRECONDITIONS,
    PreconditionError,
    PreconditionRecord,
    record_precondition,
)
from satc.autonomy.traps import DrillResult, run_drill
from satc.models.actor import ActorRefused

bp = Blueprint("autonomy", __name__)

# The charter's own table (§3), duplicated here ONLY for display — the
# authority for which three keys exist, and their order, stays
# satc.autonomy.preconditions.ALL_PRECONDITIONS. A key this dict does not
# cover is a bug the ladder screen would rather show plainly (the raw key)
# than hide behind a KeyError.
_PRECONDITION_LABELS = {
    "offsite_backup": "Off-disk backup, verified restorable",
    "tailnet_lock": "Tailnet Lock enabled",
    "mfa": "MFA on the mail account and the tax accounts",
}

_PRECONDITIONS_FILE = "autonomy_preconditions.json"

_RECORD_INSTEAD = ("open Autonomy in the local app and record it there — a "
                   "precondition is the owner's own attestation, and only "
                   "the owner can make it")


# --- the stopgap precondition ledger (see the module docstring) -------------

def _preconditions_path() -> Path:
    return Path(STATE.store.dir) / _PRECONDITIONS_FILE


def load_preconditions() -> list[PreconditionRecord]:
    """Every recorded precondition confirmation, oldest first.

    Never raises on a row it finds odd — a hand-edited or half-written JSON
    file is a support problem, not a reason for this screen to 500 (principle
    10). A row that cannot be read is skipped rather than believed.
    """
    path = _preconditions_path()
    if not path.exists():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(rows, list):
        return []
    out: list[PreconditionRecord] = []
    for row in rows:
        try:
            out.append(PreconditionRecord(
                key=row["key"], confirmed_on=date.fromisoformat(row["confirmed_on"]),
                confirmed_by=row["confirmed_by"], note=row.get("note", "")))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out, key=lambda r: (r.confirmed_on, r.key))


def _save_preconditions(records: list[PreconditionRecord]) -> None:
    rows = [{"key": r.key, "confirmed_on": r.confirmed_on.isoformat(),
            "confirmed_by": r.confirmed_by, "note": r.note} for r in records]
    _preconditions_path().write_text(
        json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")


def _record_precondition(record: PreconditionRecord) -> bool:
    """Merge one confirmation into the ledger. Returns whether it was new.

    Idempotent on ``record_id`` (principle 8): confirming the same
    precondition again today — a reload, a double click — lands on the same
    id and changes nothing, rather than piling up duplicate rows for one
    day's single fact.
    """
    existing = load_preconditions()
    if record.record_id in {r.record_id for r in existing}:
        return False
    _save_preconditions(existing + [record])
    return True


# --- gathering the facts (see the module docstring's honesty note) ----------

def _todays_proposed(today: date) -> list[Proposed]:
    """Client-facing drafts on offer right now, stamped with today's date.

    Best-effort and deliberately defensive: a bug anywhere in the ordinary
    Today queue must not take the autonomy screens down with it. Reading zero
    proposed actions is an honest, if disappointing, answer; a 500 here is
    not (principle 10).
    """
    try:
        from satc.actions import build_queue
        from satc.app.today_views import working_tax_year

        received = STATE.received_documents()
        requested = STATE.requested_items()
        year = working_tax_year(list(received) + list(requested), today)
        jobs = STATE.jobs()
        queue = build_queue(
            clients=[cid for cid, _ in STATE.client_choices()],
            requested=requested, received=received,
            engaged_clients=[e.client_id for e in jobs], jobs=jobs,
            invoices=STATE.store.load_invoices(), payments=STATE.store.load_payments(),
            tax_year=year, today=today)
        return [Proposed(day=today, template_key=a.template_key, client_id=a.client_id)
                for a in queue.actions if a.has_draft]
    except Exception:  # noqa: BLE001 - "unknown" reads honestly; a 500 does not
        return []


def _todays_drill(today: date) -> list[DrillResult]:
    """Tonight's trap drill, run live.

    ``run_drill`` is pure, deterministic given ``today``, and touches no
    store (see ``satc/autonomy/traps.py``'s own docstring) — safe to run on a
    page view, and it never raises: every way it could fail to run is itself
    recorded as a miss. Only reached for ``today`` — see the module docstring
    on why a past day gets none.
    """
    return [run_drill(today=today)]


def _gathered(day: date):
    """Everything a digest or the ladder needs, for one day."""
    approvals = list(STATE.store.load_approvals())
    preconditions = load_preconditions()
    policy = load_autonomy_policy()
    is_today = day == date.today()
    actions = _todays_proposed(day) if is_today else []
    drills = _todays_drill(day) if is_today else []
    return approvals, preconditions, policy, actions, drills


# --- the ladder ---------------------------------------------------------------

def _ladder_screen(*, error: str = "", note: str = ""):
    today = date.today()
    approvals, preconditions, policy, actions, drills = _gathered(today)
    digest = digest_for(today, approvals=approvals, drill_results=drills,
                        actions=actions, preconditions=preconditions, policy=policy)
    return render_template(
        "autonomy.html", title="Autonomy", digest=digest, policy=policy,
        preconditions=preconditions, precondition_keys=ALL_PRECONDITIONS,
        precondition_labels=_PRECONDITION_LABELS,
        ever_decided=bool(approvals), today=today, error=error, note=note)


@bp.route("/autonomy")
def ladder():
    return _ladder_screen()


@bp.route("/autonomy/precondition", methods=["POST"])
def record_precondition_route():
    """Record that the owner checked one of the three things and it held.

    The actor is derived from request context, never accepted from the form
    (principle 6) — ``acting_actor()`` is the same call every other write in
    this app makes, and ``record_precondition`` refuses anything that is not
    the owner before this file ever sees a result to save.
    """
    key = (request.form.get("key") or "").strip()
    note = (request.form.get("note") or "").strip()
    try:
        record = record_precondition(actor=acting_actor(), key=key,
                                     confirmed_on=date.today(), note=note)
    except (ActorRefused, PreconditionError) as exc:
        return _ladder_screen(error=str(exc))

    if not _record_precondition(record):
        return _ladder_screen(note=(
            f"Already recorded today for {_PRECONDITION_LABELS.get(key, key)}. "
            f"Nothing was counted twice."))
    return redirect(url_for("autonomy.ladder"))


# --- the digest -----------------------------------------------------------

def _bad_day_screen(raw_day: str):
    approvals = list(STATE.store.load_approvals())
    return render_template(
        "autonomy_digest.html", title="Autonomy digest", day=date.today(),
        digest=None, scoreboard=None, is_today=True, reason_codes=REASON_CODES,
        error=f"{raw_day!r} is not a date. Write it as YYYY-MM-DD.",
        ever_decided=bool(approvals))


@bp.route("/autonomy/digest")
def digest_view():
    raw_day = (request.args.get("day") or "").strip()
    if raw_day:
        try:
            day = date.fromisoformat(raw_day)
        except ValueError:
            return _bad_day_screen(raw_day)
    else:
        day = date.today()

    approvals, preconditions, policy, actions, drills = _gathered(day)
    digest: Digest = digest_for(day, approvals=approvals, drill_results=drills,
                                actions=actions, preconditions=preconditions, policy=policy)
    scoreboard: Scoreboard = week_for(day, approvals=approvals, drill_results=drills,
                                      actions=actions, preconditions=preconditions,
                                      policy=policy)
    return render_template(
        "autonomy_digest.html", title="Autonomy digest", day=day, digest=digest,
        scoreboard=scoreboard, error="", ever_decided=bool(approvals),
        is_today=(day == date.today()), reason_codes=REASON_CODES)
