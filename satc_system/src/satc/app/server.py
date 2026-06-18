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

from flask import Flask, redirect, render_template, request, send_file, url_for

from satc.app.intake_views import bp as intake_bp
from satc.app.state import DOC_FLOW, STATE
from satc.ingest import load_classifier
from satc.persistence import export_mart_to_excel


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.register_blueprint(intake_bp)

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
            classifier = load_classifier()
            for name in sorted(os.listdir(folder))[:50]:
                path = Path(folder) / name
                if not path.is_file():
                    continue
                c = classifier.classify_path(path)
                found.append({"name": name, "type": c.label, "method": c.method,
                              "confidence": c.confidence, "extractable": c.extractable})
        elif folder:
            # Demo fallback: show the synthetic documents as if found in the folder.
            found = [{"name": f"{d.document_id}.pdf", "type": str(d.doc_type),
                      "method": "filename", "confidence": "LOW", "extractable": True}
                     for d in STATE.documents()]
        return render_template("intake.html", title="Intake", folder=folder, found=found)

    @app.route("/intake/run", methods=["POST"])
    def intake_run():
        STATE.run_intake(request.form.get("folder", ""))
        return redirect(url_for("staging"))

    @app.route("/sort", methods=["GET", "POST"])
    def sort():
        folder = request.form.get("folder") or request.args.get("folder") or ""
        plan = STATE.sort_folder(folder, apply=False) if folder and Path(folder).is_dir() else None
        return render_template("sort.html", title="Sort & re-label", folder=folder, plan=plan)

    @app.route("/sort/apply", methods=["POST"])
    def sort_apply():
        folder = request.form.get("folder", "")
        plan = STATE.sort_folder(folder, apply=True)
        return render_template("sort.html", title="Sort & re-label", folder=folder, plan=plan)

    @app.route("/staging")
    def staging():
        return render_template("staging.html", title="Staging & confirmation",
                               fields=STATE.gate.all_fields(), summary=STATE.gate.summary(),
                               intake=STATE.intake_summary)

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

    @app.route("/staging/post", methods=["POST"])
    def staging_post():
        STATE.post_confirmed()
        return redirect(url_for("client", client_id="SATC-001000"))

    @app.route("/documents")
    def documents():
        return render_template("documents.html", title="Documents",
                               documents=STATE.documents(), flow=DOC_FLOW)

    @app.route("/documents/<document_id>/<status>", methods=["POST"])
    def documents_status(document_id: str, status: str):
        STATE.set_document_status(document_id, status)
        return redirect(url_for("documents"))

    @app.route("/setup")
    def setup():
        from satc.doctor import run_checks
        return render_template("setup.html", title="Setup", checks=run_checks())

    @app.route("/export")
    def export():
        out = Path(STATE.store.dir) / "SATC_DataMart_export.xlsx"
        export_mart_to_excel(STATE.store, out)
        return send_file(out, as_attachment=True, download_name="SATC_DataMart.xlsx")

    @app.route("/clients/<client_id>")
    def client(client_id: str):
        rets = [r for r in STATE.returns() if r.client_id == client_id]
        ret_keys = {r.return_key for r in rets}
        lines = sorted((li for li in STATE.mart.line_items if li.return_key in ret_keys),
                       key=lambda li: (li.schedule, li.line_code))
        docs = [d for d in STATE.documents() if d.client_id == client_id]
        eng = next((e for e in STATE.mart.engagements if e.client_id == client_id), None)
        return render_template("client.html", title=STATE.name(client_id),
                               client_id=client_id, returns=rets, docs=docs, engagement=eng,
                               lines=lines, posted=STATE.posted_summary)

    return app


def _pick_port(preferred: int) -> int:
    """Return ``preferred`` if free, else an open port — so launch never fails."""
    import socket

    for candidate in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", candidate))
                return s.getsockname()[1]
            except OSError:
                continue
    return preferred


def main() -> None:
    app = create_app()
    port = _pick_port(int(os.environ.get("SATC_PORT", "5050")))
    url = f"http://127.0.0.1:{port}"

    # Open the browser for the user a moment after the server starts.
    if os.environ.get("SATC_NO_BROWSER", "").strip().lower() not in {"1", "true", "yes"}:
        import threading
        import webbrowser

        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    print(f"\n  SATC is running.  Open:  {url}\n  (Leave this window open; press Ctrl+C to stop.)\n")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
