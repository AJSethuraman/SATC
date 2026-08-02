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
from urllib.parse import urlparse

from flask import Flask, Response, redirect, render_template, request, send_file, url_for

from satc.app.billing_views import bp as billing_bp
from satc.app.comms_views import bp as comms_bp
from satc.app.intake_views import bp as intake_bp
from satc.app.state import STATE
from satc.app.today_views import bp as today_bp
from satc.app.withholding_views import bp as withholding_bp
from satc.app.work_views import bp as work_bp
from satc.app.workflow_views import bp as workflow_bp
from satc.ingest import load_classifier
from satc.persistence import export_mart_to_excel


_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _resolve_secret_key() -> bytes:
    """Per-install random Flask secret (persisted, 0600), overridable via env.

    Replaces the old hardcoded ``satc-local-dev-key`` so signed session cookies
    can't be forged with a publicly-known key.
    """
    env = os.environ.get("SATC_SECRET_KEY")
    if env:
        return env.encode("utf-8")
    path = Path(STATE.store.dir) / "flask_secret.key"
    if path.exists():
        return path.read_bytes()
    key = os.urandom(32)
    try:
        path.write_bytes(key)
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = _resolve_secret_key()
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    app.register_blueprint(intake_bp)
    app.register_blueprint(workflow_bp)
    app.register_blueprint(withholding_bp)
    app.register_blueprint(comms_bp)
    app.register_blueprint(today_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(work_bp)

    @app.before_request
    def _local_only_guard():
        # H2 — reject non-loopback Host headers (blocks DNS-rebinding, which would
        # otherwise let a page the preparer visits read /clients, /export, /source).
        if (request.host or "").split(":")[0] not in _LOCAL_HOSTS:
            return "Bad Host", 400
        # H3 — CSRF: reject a state-changing request a browser marks as cross-origin.
        # Local tools and the JSON API send no Origin/Referer and are allowed; a
        # cross-site attacker's browser always sends a foreign Origin.
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            src = request.headers.get("Origin") or request.headers.get("Referer")
            if src and urlparse(src).hostname not in _LOCAL_HOSTS:
                return "Cross-origin request blocked", 403
        return None

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
        client = request.values.get("client", "")
        tax_year = request.values.get("tax_year", "")
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
            found = [{"name": d.display_name or f"{d.document_id}.pdf",
                      "type": str(d.doc_type), "method": "filename",
                      "confidence": "LOW", "extractable": True}
                     for d in STATE.received_documents()]
        return render_template("intake.html", title="Intake", folder=folder, found=found,
                               client=client, tax_year=tax_year)

    @app.route("/intake/run", methods=["POST"])
    def intake_run():
        folder = request.form.get("folder", "")
        client = request.values.get("client", "")
        tax_year = request.values.get("tax_year", "")
        STATE.run_intake(folder, client_id=client or "SATC-001000",
                         tax_year=int(tax_year) if tax_year.strip().isdigit() else 2024)
        return redirect(url_for("staging"))

    @app.route("/sort", methods=["GET", "POST"])
    def sort():
        folder = request.form.get("folder") or request.args.get("folder") or ""
        client = request.values.get("client", "")
        tax_year = request.values.get("tax_year", "")
        plan = (STATE.sort_folder(folder, apply=False, client_id=client, tax_year=tax_year)
                if folder and Path(folder).is_dir() else None)
        return render_template("sort.html", title="Sort & re-label", folder=folder, plan=plan,
                               client=client, tax_year=tax_year, clients=STATE.client_choices())

    @app.route("/sort/apply", methods=["POST"])
    def sort_apply():
        folder = request.form.get("folder", "")
        client = request.values.get("client", "")
        tax_year = request.values.get("tax_year", "")
        plan = STATE.sort_folder(folder, apply=True, client_id=client, tax_year=tax_year)
        return render_template("sort.html", title="Sort & re-label", folder=folder, plan=plan,
                               client=client, tax_year=tax_year, clients=STATE.client_choices())

    @app.route("/staging")
    def staging():
        return render_template("staging.html", title="Staging & confirmation",
                               documents=STATE.gate.documents, summary=STATE.gate.summary(),
                               intake=STATE.intake_summary)

    @app.route("/source")
    def source_file():
        """Serve an original source file — but only ones read in the last intake."""
        path = request.args.get("path", "")
        if path not in STATE.intake_sources or not Path(path).is_file():
            return Response("Source file not available.", status=404, mimetype="text/plain")
        return send_file(path)

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
        elif action == "unconfirm":
            STATE.unconfirm_field(field_id)
        elif action == "delete":
            STATE.delete_field(field_id)
        elif action == "edit":
            STATE.edit_field(field_id, request.form.get("value", ""))
        return redirect(url_for("staging"))

    @app.route("/sample/clear", methods=["POST"])
    def clear_sample():
        removed = STATE.clear_sample_data()
        return redirect(request.form.get("next") or request.referrer or url_for("dashboard"))

    @app.route("/staging/post", methods=["POST"])
    def staging_post():
        summary = STATE.post_confirmed()
        return redirect(url_for("client", client_id=summary["client_id"]))

    @app.route("/documents")
    def documents():
        """The register, now honestly two registers: asked for, and arrived."""
        return render_template("documents.html", title="Documents",
                               requested=STATE.requested_items(),
                               received=STATE.received_documents())

    @app.route("/documents/<request_id>/close", methods=["POST"])
    def close_request(request_id: str):
        """Close an open request — satisfied, or N/A with the client's reason."""
        STATE.close_request(request_id, reason=request.form.get("reason", "").strip())
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

    # --- JSON API: withholding compute (localhost, stateless, no PII) ---
    # Lets a same-machine agent POST figures and get a projection back while the
    # app is running. No client data is read or written here.
    @app.route("/api/withholding/estimate", methods=["POST"])
    def api_withholding_estimate():
        from satc.api import tools
        return tools.estimate_withholding(request.get_json(force=True, silent=True) or {})

    @app.route("/api/withholding/read-paystub", methods=["POST"])
    def api_read_paystub():
        from satc.api import tools
        payload = request.get_json(force=True, silent=True) or {}
        return tools.read_paystub(payload.get("text", ""))

    @app.route("/api/withholding/meta")
    def api_withholding_meta():
        # Read-first "scorecard": what an estimate accepts. Drawn from the models
        # so it can never drift from what the estimator actually validates.
        from typing import get_args

        from satc.withholding.models import FilingStatus, PayFrequency

        return {
            "filing_statuses": list(get_args(FilingStatus)),
            "pay_frequencies": list(get_args(PayFrequency)),
            "default_tax_year": 2025,
            "fields": {
                "filing_status": "required; one of filing_statuses",
                "tax_year": "optional; defaults to the current published year. "
                "2026 is a not-yet-published fixture that falls back to 2025 with a note.",
                "jobs": "list, one entry per job (taxpayer + spouse / second jobs). Each job: "
                "pay_frequency, gross_pay_per_period, federal_tax_withheld_per_period, "
                "ytd_taxable_wages, ytd_federal_tax_withheld, pay_periods_remaining (optional).",
                "other_income": "optional dict (interest, dividends, self-employment, etc.)",
                "deductions": "optional dict (standard vs. itemized)",
                "prior_year_tax": "optional; enables safe-harbor guidance",
            },
        }

    @app.route("/clients")
    def clients_index():
        return render_template("clients_index.html", title="Clients",
                               clients=STATE.client_choices())

    @app.route("/clients/<client_id>")
    def client(client_id: str):
        rets = [r for r in STATE.returns() if r.client_id == client_id]
        ret_keys = {r.return_key for r in rets}
        lines = sorted((li for li in STATE.mart.line_items if li.return_key in ret_keys),
                       key=lambda li: (li.schedule, li.line_code))
        docs = [d for d in STATE.received_documents() if d.client_id == client_id]
        eng = next((e for e in STATE.mart.engagements if e.client_id == client_id), None)
        return render_template("client.html", title=STATE.name(client_id),
                               client_id=client_id, returns=rets, docs=docs, engagement=eng,
                               lines=lines, posted=STATE.posted_summary)

    @app.route("/clients/<client_id>/drake")
    def drake_entry(client_id: str):
        """A printable Drake keying worksheet from the client's posted figures."""
        rets = [r for r in STATE.returns() if r.client_id == client_id]
        ret_keys = {r.return_key for r in rets}
        lines = sorted((li for li in STATE.mart.line_items if li.return_key in ret_keys),
                       key=lambda li: (li.schedule, li.line_code))
        return render_template("drake_worksheet.html", title=STATE.name(client_id),
                               client_id=client_id, public_client=STATE.public_client(client_id),
                               returns=rets, lines=lines,
                               tax_year=(rets[0].tax_year if rets else ""))

    @app.route("/clients/<client_id>/delivery-email", methods=["POST"])
    def delivery_email(client_id: str):
        """Pop an Outlook draft telling the client their return is ready."""
        from satc.intake.email_draft import mailto_url, open_outlook_draft
        name = STATE.name(client_id)
        to = STATE.client_email(client_id)
        years = sorted({r.tax_year for r in STATE.returns() if r.client_id == client_id})
        yr = f"{years[-1]} " if years else ""
        subject = f"Your {yr}tax return is ready - {name}"
        body = "\n".join([
            f"Hi {name},", "",
            f"Your {yr}tax return is prepared and ready for your review. Please look it over, and "
            "once everything looks right we'll send the e-file authorization (Form 8879) for your "
            "signature.", "",
            "Let us know if you have any questions.", "",
            "Thank you,", "SAT-C LLP",
        ])
        result = open_outlook_draft(to=to, subject=subject, body=body)
        return render_template("draft_result.html", title=STATE.name(client_id), result=result,
                               what="delivery email", to=to, subject=subject, body=body,
                               mailto=mailto_url(to=to, subject=subject, body=body),
                               back_url=url_for("client", client_id=client_id),
                               attachment_url="", attachment_name="")

    @app.route("/clients/<client_id>/discard", methods=["POST"])
    def discard_client(client_id: str):
        """Delete a just-added client (the cancel/undo for adding someone)."""
        STATE.delete_client(client_id)
        return redirect(url_for("intake.engagements"))

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
    # Single-threaded: the store's SQLite connections are shared with
    # check_same_thread=False and aren't safe under concurrent request threads.
    # A local single-user app doesn't need threaded serving. (L9)
    app.run(host="127.0.0.1", port=port, debug=False, threaded=False)


if __name__ == "__main__":
    main()
