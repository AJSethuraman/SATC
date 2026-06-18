"""SATC prototype web app (Flask).

A local, hand-holding GUI that opens in the browser. Run it with:

    pip install -e .[app]
    python -m satc.app          # opens http://127.0.0.1:5050

Screens: Dashboard, Intake (point it at a folder), Staging (confirm what was
read), Documents (mark Received/Sent/Signed — the missing-docs tracker), and a
per-client engagement view. Backed by :data:`satc.app.state.STATE`.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

from satc.app.state import DOC_FLOW, STATE


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.context_processor
    def inject_globals():
        return {"state": STATE, "outstanding": len(STATE.outstanding())}

    @app.route("/")
    def dashboard():
        return render_template("dashboard.html", title="Dashboard",
                               pipeline=STATE.pipeline_counts(), returns=STATE.returns())

    @app.route("/intake", methods=["GET", "POST"])
    def intake():
        folder = request.form.get("folder") or request.args.get("folder") or ""
        found: list[dict] = []
        if folder and Path(folder).is_dir():
            for name in sorted(os.listdir(folder))[:50]:
                found.append({"name": name, "type": _guess_type(name)})
        elif folder:
            # Demo fallback: show the synthetic documents as if found in the folder.
            found = [{"name": f"{d.document_id}.pdf", "type": str(d.doc_type)}
                     for d in STATE.documents()]
        return render_template("intake.html", title="Intake", folder=folder, found=found)

    @app.route("/staging")
    def staging():
        return render_template("staging.html", title="Staging & confirmation",
                               fields=STATE.gate.all_fields(), summary=STATE.gate.summary())

    @app.route("/staging/auto", methods=["POST"])
    def staging_auto():
        STATE.auto_confirm()
        return redirect(url_for("staging"))

    @app.route("/staging/<path:field_id>/<action>", methods=["POST"])
    def staging_action(field_id: str, action: str):
        if action == "confirm":
            STATE.confirm_field(field_id)
        elif action == "reject":
            STATE.reject_field(field_id)
        return redirect(url_for("staging"))

    @app.route("/documents")
    def documents():
        return render_template("documents.html", title="Documents",
                               documents=STATE.documents(), flow=DOC_FLOW)

    @app.route("/documents/<document_id>/<status>", methods=["POST"])
    def documents_status(document_id: str, status: str):
        STATE.set_document_status(document_id, status)
        return redirect(url_for("documents"))

    @app.route("/clients/<client_id>")
    def client(client_id: str):
        rets = [r for r in STATE.returns() if r.client_id == client_id]
        docs = [d for d in STATE.documents() if d.client_id == client_id]
        eng = next((e for e in STATE.mart.engagements if e.client_id == client_id), None)
        return render_template("client.html", title=STATE.name(client_id),
                               client_id=client_id, returns=rets, docs=docs, engagement=eng)

    return app


def _guess_type(filename: str) -> str:
    f = filename.lower()
    for needle, label in [("w2", "W-2"), ("w-2", "W-2"), ("1099int", "1099-INT"),
                          ("1099div", "1099-DIV"), ("1099", "1099"), ("k1", "K-1"),
                          ("k-1", "K-1"), ("8879", "Form 8879"), ("organizer", "Organizer"),
                          ("1040", "Prior-year 1040")]:
        if needle in f:
            return label
    return "Unclassified"


def main() -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=int(os.environ.get("SATC_PORT", "5050")), debug=False)


if __name__ == "__main__":
    main()
