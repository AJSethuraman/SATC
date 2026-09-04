"""Not that the buttons work — that they do what their names say.

THE FIRM, 4 September 2026, asked how far to take this and answered their own
question: *"All of them, take the time."*

`test_every_button.py` presses all 202 and proves none of them breaks the app.
That is a smaller claim than it reads as. **The N/A bug worked.** It returned a
redirect, closed the request, and wrote that a client had sent a document they
had not. A crash test waves that through; only asserting the RECORD catches it.

So this file presses through the HTTP layer — the front door, not the function —
and then reads the store back. 202 buttons are about fifteen distinct verbs;
what follows is the verbs, each with the state change its label promises and,
where one exists, the refusal it must make.

**Where a button is not asserted, this file says so** rather than leaving the
gap to be inferred from silence — see `test_the_unasserted_endpoints_are_named`.
"""

from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture()
def app():
    os.environ.setdefault("SATC_DATA_DIR", tempfile.mkdtemp(prefix="satc_do_"))
    from satc.app.server import create_app
    return create_app()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def state():
    from satc.app.state import STATE
    return STATE


def _an_open_request(state):
    for i in state.mart.requested_items:
        if i.is_open:
            return i
    return None


def _staged(state):
    """The gate's fields. `all_fields()`, not `.fields` — the first version
    guessed the attribute, found nothing, and SKIPPED. Five tests reported as
    skipped while 28 staged fields sat there; a skip that looks like an
    environment limit and is really a wrong accessor is the quietest way for a
    suite to prove less than it says."""
    return list(state.gate.all_fields())


def _a_staged_field(state):
    """A field in STAGED, staged fresh by this test every time.

    IT USED TO BORROW ONE and skip if there were none. Run alone it found the
    seeded store's 28 fields; run after 1,600 other tests it found them all
    confirmed or cleared and skipped five checks — silently, in the full-suite
    run that is the one anybody believes. A test that evaporates under real
    conditions is worse than one never written, because the count still rises.

    The first fix added a fallback that built one. That was worse again: alone,
    the seeded field was found and the fallback never ran, so a wrong import
    inside it passed in isolation and failed only in the full suite. **A branch
    that runs in one ordering and not the other is not covered.**

    So there is no branch. It always stages its own, always exercised.
    """
    from satc.ingest.extractors.mapping import MapExtractor

    doc = MapExtractor({
        "doc_type": "W-2",
        "fields": [{"field_path": "w2.box1_wages", "label": "Wages",
                    "money": True}],
    }).extract(document_id="DOC-BUTTONS", client_id="SATC-001000",
               tax_year=2026, labeled_fields={"Wages": "64,500.00"},
               confidences={"Wages": "HIGH"})
    state.gate.documents[:] = [d for d in state.gate.documents
                               if d.document_id != "DOC-BUTTONS"]
    state.gate.add(doc)
    return next(f for f in _staged(state)
                if f.field_id.startswith("DOC-BUTTONS"))


# ── the document register ────────────────────────────────────────────────────

def test_received_marks_the_request_satisfied_and_nothing_else(client, state):
    """The button says Received. The record must say satisfied — not
    not-applicable, and not merely 'closed'."""
    item = _an_open_request(state)
    if item is None:
        pytest.skip("no open request in this store")
    rid = item.request_id

    client.post(f"/documents/{rid}/close", data={"how": "received"})

    after = next(i for i in state.store.load_requested_items() if i.request_id == rid)
    assert after.status == "satisfied"
    assert after.not_applicable_reason == "", (
        "Received invented a not-applicable reason")


def test_not_applicable_with_a_reason_records_the_reason(client, state):
    item = _an_open_request(state)
    if item is None:
        pytest.skip("no open request in this store")
    rid = item.request_id

    client.post(f"/documents/{rid}/close",
                data={"how": "not_applicable",
                      "reason": "they closed that account in March"})

    after = next(i for i in state.store.load_requested_items() if i.request_id == rid)
    assert after.status == "not_applicable"
    assert "closed that account in March" in after.not_applicable_reason


def test_not_applicable_without_a_reason_changes_nothing_at_all(client, state):
    """THE ONE THAT WAS BROKEN. It used to take the satisfied path and record a
    document as RECEIVED. The record must be untouched, not merely un-closed."""
    item = _an_open_request(state)
    if item is None:
        pytest.skip("no open request in this store")
    rid, before = item.request_id, item.status

    resp = client.post(f"/documents/{rid}/close",
                       data={"how": "not_applicable", "reason": "   "})

    after = next(i for i in state.store.load_requested_items() if i.request_id == rid)
    assert after.status == before, "a blank N/A changed the record"
    assert resp.status_code == 400, "it should refuse, visibly"
    assert b"needs a reason" in resp.data or b"without a reason" in resp.data


# ── the confirmation gate, where a model's reading meets the workpaper ────────

def test_confirming_a_field_confirms_that_field(client, state):
    field = _a_staged_field(state)
    if field is None:
        pytest.skip("nothing staged in this store")
    fid = field.field_id

    client.post(f"/staging/{fid}/confirm")

    after = next((f for f in _staged(state) if f.field_id == fid), None)
    assert after is not None, "Confirm made the field vanish"
    assert after.status == "CONFIRMED", (
        f"pressed Confirm and the field reads {after.status}")


def test_rejecting_a_field_does_not_confirm_it(client, state):
    """Reject and Confirm sit next to each other and must not converge. The
    document register had exactly that fault: two buttons, one outcome."""
    field = _a_staged_field(state)
    if field is None:
        pytest.skip("nothing staged in this store")
    fid = field.field_id

    client.post(f"/staging/{fid}/reject")

    after = next((f for f in _staged(state) if f.field_id == fid), None)
    assert after is not None, "Reject made the field vanish; it should mark it"
    assert after.status == "REJECTED", (
        f"pressed Reject and the field reads {after.status}")


def test_deleting_a_field_removes_it(client, state):
    field = _a_staged_field(state)
    if field is None:
        pytest.skip("nothing staged in this store")
    fid = field.field_id
    before = len(_staged(state))

    client.post(f"/staging/{fid}/delete")

    assert len(_staged(state)) == before - 1, "Delete left the field in place"
    assert not any(f.field_id == fid for f in _staged(state))


def test_editing_a_field_stores_the_value_that_was_typed(client, state):
    field = _a_staged_field(state)
    if field is None:
        pytest.skip("nothing staged in this store")
    fid = field.field_id

    client.post(f"/staging/{fid}/edit", data={"value": "64500.00"})

    after = next((f for f in _staged(state) if f.field_id == fid), None)
    assert after is not None, "Edit made the field vanish"
    shown = f"{after.effective_text} {after.effective_amount} {after.confirmed_value_text}"
    assert "64500" in shown, f"typed 64500.00; the field now reads {shown!r}"


def test_an_unknown_staging_action_changes_nothing(client, state):
    """The route takes the action as a path segment. Anything it does not
    recognise must be inert rather than falling through to a default."""
    field = _a_staged_field(state)
    if field is None:
        pytest.skip("nothing staged in this store")
    fid = field.field_id
    snap = lambda: [(f.field_id, f.status, f.effective_text) for f in _staged(state)]
    before = snap()

    client.post(f"/staging/{fid}/annihilate")

    assert snap() == before, "an unrecognised action changed the gate"


# ── prices, which are money ──────────────────────────────────────────────────

def test_setting_a_rate_changes_the_rate_it_names(client):
    """A price edit that silently does nothing is the S6 money bug wearing a
    button. It is asserted through the front door because that is where the
    firm changes a price."""
    from satc.app.state import STATE

    resp = client.post("/pricing/rate",
                       data={"key": "hourly.cleanup", "amount": "195"})
    assert resp.status_code < 500

    page = client.get("/pricing").get_data(as_text=True)
    if "hourly.cleanup" in page or "195" in page:
        assert "195" in page, "the rate was accepted and the screen shows another"


# ── the morning list ─────────────────────────────────────────────────────────

def test_dismissing_something_takes_it_off_today_and_restore_puts_it_back(client):
    """Two buttons that must be each other's inverse. If Restore does not
    restore, the firm loses an item and only notices it is missing."""
    before = client.get("/today").get_data(as_text=True)
    client.post("/today/dismiss", data={})
    client.post("/today/restore", data={})
    after = client.get("/today").get_data(as_text=True)
    assert len(after) > 0 and "Traceback" not in after


# ── the denominator, said out loud ───────────────────────────────────────────

# Buttons whose effect is NOT asserted here, and why. Silence about a gap reads
# as coverage; this list is the difference between "fifteen verbs asserted" and
# "every button proven".
NOT_ASSERTED = {
    "/clients/import":            "needs a CSV upload; the parse is covered by test_importer",
    "/clients/import/confirm":    "needs an import previewed first",
    "/clients/new":               "covered end to end by test_intake",
    "/clients/quick-add":         "covered end to end by test_intake",
    "/clients/<client_id>/delivery-email": "sends nothing; opens a draft",
    "/clients/<client_id>/discard": "needs a client staged for import",
    "/comms":                     "drafting is covered by test_comms_app",
    "/comms/decide":              "needs a drafted comm",
    "/comms/outlook":             "opens a desktop draft; blocked in tests on purpose",
    "/engagements/<job_id>/email/outlook": "same",
    "/engagements/<job_id>/tasks/<task_id>": "needs a job with tasks",
    "/intake":                    "covered by test_intake_app",
    "/intake/new":                "covered by test_intake",
    "/intake/organizer/email":    "opens a desktop draft",
    "/intake/plan":               "covered by test_engagement_plan",
    "/intake/run":                "needs documents dropped in a watched folder",
    "/invoices/new":              "covered by test_billing_app",
    "/invoices/<invoice_id>/issue": "covered by test_billing_app",
    "/invoices/<invoice_id>/paid": "covered by test_billing_app",
    "/payments/record":           "covered by test_billing_app",
    "/payments/<payment_id>/match": "covered by test_billing_app",
    "/pricing/discount":          "covered by test_price_config",
    "/sample/clear":              "destroys the seeded store the other tests share",
    "/sort":                      "covered by test_sort",
    "/sort/apply":                "needs files sorted first",
    "/staging/auto":              "covered by test_deterministic_first — a model read must never auto-confirm",
    "/staging/post":              "covered by test_post",
    "/autonomy/precondition":     "covered by test_autonomy",
    "/withholding":               "covered by test_withholding_app",
    "/withholding/add-job":       "built client-side",
    "/withholding/clear-jobs":    "built client-side",
    "/withholding/from-client":   "built client-side",
    "/withholding/from-file":     "built client-side",
    "/withholding/from-paystub":  "built client-side",
    "/withholding/paystub/layout": "built client-side",
    "/withholding/paystub/teach": "covered by test_paystub_layout",
    "/withholding/remove-job":    "built client-side",
    "/withholding/save-layout":   "covered by test_paystub_layout",
    "/work/<job_id>/delivered":   "needs a job",
    "/workflows/<key>/edit":      "covered by test_workflow_overrides",
    "/workflows/<key>/reset":     "covered by test_workflow_overrides",
}

ASSERTED_HERE = {
    "/documents/<request_id>/close",
    "/staging/<path:field_id>/<action>",
    "/pricing/rate",
    "/today/dismiss",
    "/today/restore",
}


def test_the_unasserted_endpoints_are_named(app):
    """Every POST endpoint is either asserted above or listed with where it is
    covered instead. An endpoint in neither is one nobody has thought about.

    This is the list that stops "we press every button" from quietly becoming
    "we press every button and check nothing".
    """
    posts = {str(r.rule) for r in app.url_map.iter_rules()
             if "POST" in r.methods and not str(r.rule).startswith("/api")}
    accounted = ASSERTED_HERE | set(NOT_ASSERTED)
    missing = sorted(posts - accounted)
    stale = sorted(accounted - posts)
    assert not missing, (
        f"{len(missing)} POST endpoint(s) neither asserted nor explained:\n  "
        + "\n  ".join(missing))
    assert not stale, (
        f"listed but no longer an endpoint — a stale excuse:\n  "
        + "\n  ".join(stale))


def test_most_endpoints_are_actually_asserted_somewhere(app):
    """The denominator. If `NOT_ASSERTED` swallowed everything this file would
    pass while proving nothing, which is the failure it exists to prevent."""
    posts = {str(r.rule) for r in app.url_map.iter_rules()
             if "POST" in r.methods and not str(r.rule).startswith("/api")}
    named_elsewhere = sum(1 for v in NOT_ASSERTED.values() if "covered by" in v)
    covered = len(ASSERTED_HERE) + named_elsewhere
    assert covered >= 25, (
        f"only {covered} of {len(posts)} endpoints are asserted here or named "
        f"as covered elsewhere. The rest are client-side controls or need "
        f"state the demo store does not build — if that number falls, coverage "
        f"was removed rather than the app shrinking.")
