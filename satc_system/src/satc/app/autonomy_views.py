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

PRECONDITION CONFIRMATIONS LIVE IN THE STORE.
``satc.persistence.store.SATCStore.save_preconditions``/``load_preconditions``
is the record now — the same durability and the same idempotent-on-record_id
discipline as ``save_approvals``/``load_approvals`` (charter §11's ledger).

An earlier build of this slice kept a small JSON file
(``autonomy_preconditions.json``) next to the store's own database instead.
That was a real bug, not a style complaint: ``satc reset`` deletes the
database files in that directory and nothing else, so a fresh reset started
with zero clients, zero approvals, and every precondition still "confirmed
and current" — the one gate that exists to hold a freshly-wiped practice back
was the one thing a wipe could not touch. See the "Finding 3" section of
``tests/test_traps.py`` for the reset case made into a test that can fail
(that file, not one named for this module, because it is the only test file
this slice is permitted to touch).

A store that finds the old JSON file still sitting on disk imports it ONCE
(see :func:`_import_legacy_preconditions_once`) and renames it out of the way
so it is never read again — never silently dropped, and never silently
trusted forever: a file this code cannot parse is renamed to say so rather
than being ignored.

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


# --- the precondition ledger (see the module docstring) ---------------------

def _legacy_preconditions_path() -> Path:
    """Where an earlier build of this slice wrote confirmations, outside the
    store. Only ever read from here, once, to migrate off it — see
    :func:`_import_legacy_preconditions_once`."""
    return Path(STATE.store.dir) / _PRECONDITIONS_FILE


def _import_legacy_preconditions_once() -> None:
    """Migrate the pre-store JSON ledger into the store, exactly once.

    Called at the top of every :func:`load_preconditions` — cheap, because
    after the first successful run (or the first unreadable one) the file is
    renamed and :meth:`Path.exists` on the original name is ``False`` forever
    after, so every later call is a single stat and nothing more.

    NEVER SILENTLY IGNORED, NEVER SILENTLY TRUSTED. A file that parses is
    imported into the store (idempotent on ``record_id``, so importing it
    twice is harmless) and renamed to ``.json.imported`` so it cannot be
    re-read. A file that does NOT parse is left on disk, renamed to
    ``.json.unreadable`` — visible, named for what is wrong with it, and
    never treated as a source of facts nobody could actually check.
    """
    path = _legacy_preconditions_path()
    if not path.exists():
        return
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        path.replace(path.with_suffix(".json.unreadable"))
        return
    if not isinstance(rows, list):
        # Parsed, but not the shape a ledger has. Naming it "imported" would say
        # a migration happened when nothing was read at all.
        path.replace(path.with_suffix(".json.unreadable"))
        return

    records: list[PreconditionRecord] = []
    dropped = 0
    for row in rows:
        try:
            records.append(PreconditionRecord(
                key=row["key"], confirmed_on=date.fromisoformat(row["confirmed_on"]),
                confirmed_by=row["confirmed_by"], note=row.get("note", "")))
        except (KeyError, TypeError, ValueError):
            dropped += 1
    if records:
        STATE.store.save_preconditions(records)

    # THE FILENAME IS THE RECORD OF WHAT HAPPENED, so it may not overstate it.
    # Every unusable row used to be skipped in silence and the file renamed
    # ".imported" regardless — which says a clean migration happened, about a
    # file that had rows nobody could read. These are confirmations that gate
    # everything; losing one quietly is the opposite of what a gate is for.
    #
    # A partial import keeps its rows ON DISK under a name that says so, so the
    # ones that were dropped can still be looked at. It is not re-read: it no
    # longer ends in .json.
    suffix = ".json.imported" if not dropped else ".json.partly-imported"
    path.replace(path.with_suffix(suffix))


def load_preconditions() -> list[PreconditionRecord]:
    """Every recorded precondition confirmation, oldest first.

    Reads from the store — never raises on a row it finds odd (principle
    10); a row this app cannot make sense of is skipped by
    :meth:`~satc.persistence.store.SATCStore.load_preconditions` rather than
    believed or allowed to take the whole screen down.
    """
    _import_legacy_preconditions_once()
    return sorted(STATE.store.load_preconditions(), key=lambda r: (r.confirmed_on, r.key))


def _record_precondition(record: PreconditionRecord) -> bool:
    """Save one confirmation to the store. Returns whether it was new.

    Idempotent on ``record_id`` (principle 8): confirming the same
    precondition again today — a reload, a double click — lands on the same
    id and changes nothing, rather than piling up duplicate rows for one
    day's single fact.
    """
    existing = load_preconditions()
    if record.record_id in {r.record_id for r in existing}:
        return False
    STATE.store.save_preconditions([record])
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
