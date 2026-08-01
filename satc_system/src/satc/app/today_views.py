"""TODAY — the practice's front door.

One screen answering one question: *what needs me right now, and what is already
done except the decision?*

Thin by design. Everything shown here is computed by :mod:`satc.actions` from
plain records; this module gathers those records and hands them over. No rule
about what is urgent lives in this file, and none should.

Routes:
  GET /today            - the queue, grouped by how much it hurts to leave
  GET /today/dismiss    - hide one action for this session (never destructive)
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, redirect, render_template, request, session, url_for

from satc.actions import build_queue
from satc.app.state import STATE

bp = Blueprint("today", __name__)

_DISMISSED = "today_dismissed"

def working_tax_year(rows, today: date) -> int:
    """The year the practice is actually working on.

    Derived from the register — the most recent year with documents on file —
    rather than hardcoded, because a constant here goes stale silently and every
    deadline then reads as wildly overdue. Falls back to the year most of a
    filing season is spent on (the one that closed last December) when the
    practice is empty.

    Principle 3: computed, never stored.
    """
    years = [r.tax_year for r in rows if getattr(r, "tax_year", None)]
    return max(years) if years else today.year - 1


def _obligations(tax_year: int):
    """Materialise every client's duties for the year, from the clock.

    Profiles are not yet persisted, so each client gets a DEFAULT profile built
    from what the mart already knows: their entity type, filing federally. That
    understates a client with payroll or a state filing — which is the honest
    failure direction, because it produces no work rather than fictional work
    (principle 2: facts are recorded, never inferred).
    """
    from satc.config import ConfigError
    from satc.obligations.profile import ObligationProfile, materialise

    out = []
    for pc in STATE.mart.public_clients:
        profile = ObligationProfile(client_id=pc.client_id,
                                    entity_type=pc.entity_type or "INDIVIDUAL")
        try:
            out.extend(materialise(profile, tax_year))
        except ConfigError:
            # An unsourced jurisdiction refuses rather than guessing. That is the
            # designed behaviour, and it must not take the whole screen down.
            continue
    return out


def _dismissed() -> set[str]:
    return set(session.get(_DISMISSED, []))


@bp.route("/today")
def today():
    as_of = date.today()
    requested = STATE.requested_items()
    received = STATE.received_documents()
    asked_year = request.args.get("tax_year", "")
    year = (int(asked_year) if asked_year.strip().isdigit()
            else working_tax_year(list(received) + list(requested), as_of))

    queue = build_queue(
        clients=[cid for cid, _ in STATE.client_choices()],
        requested=requested, received=received,
        obligations=_obligations(year),
        engaged_clients=[e.client_id for e in STATE.intake_engagements()],
        tax_year=year, today=as_of)

    hidden = _dismissed()
    visible = [a for a in queue.actions if a.action_id not in hidden]
    queue.actions = visible

    return render_template(
        "today.html", title="Today", queue=queue, tax_year=year, as_of=as_of,
        hidden_count=len(hidden), names={cid: name for cid, name in STATE.client_choices()})


@bp.route("/today/dismiss", methods=["POST"])
def dismiss():
    """Hide an action for this session.

    Deliberately session-scoped and non-destructive: it hides a row, it does not
    resolve anything. The underlying fact — an unsigned 8879, a missing 1099 —
    is untouched, and the action returns next session because the reason it
    existed has not gone away.
    """
    action_id = (request.form.get("action_id") or "").strip()
    if action_id:
        session[_DISMISSED] = sorted(_dismissed() | {action_id})
        session.modified = True
    return redirect(url_for("today.today", tax_year=request.form.get("tax_year", "")))


@bp.route("/today/restore", methods=["POST"])
def restore():
    session.pop(_DISMISSED, None)
    session.modified = True
    return redirect(url_for("today.today", tax_year=request.form.get("tax_year", "")))
