"""Client-intake & engagement screens (Flask blueprint).

Registered by :func:`satc.app.server.create_app`. Routes here drive the
new-client / interview flow and the engagement (requested-vs-received) view,
backed by :data:`satc.app.state.STATE`.

Screens (built out by the UI workstream):
  GET  /clients/new                  - choose person/business, create a client
  GET  /intake/new                   - pick a client + workflow, answer the interview
  POST /intake/new                   - generate the engagement (opens Requested docs)
  GET  /engagements                  - list generated engagements
  GET  /engagements/<id>             - tasks grouped by category, risk flags, requests
  POST /engagements/<id>/tasks/<tid> - toggle a task complete
"""

from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, url_for

from satc.app.state import STATE

bp = Blueprint("intake", __name__)


@bp.route("/engagements")
def engagements():
    return render_template("engagements.html", title="Engagements",
                           engagements=STATE.intake_engagements())
