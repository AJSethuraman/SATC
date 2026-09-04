"""Client-comms screen (Flask) tests — picking, prefilling, and not sending.

The pure merging rules are guarded in ``tests/test_comms.py``; this file guards
the thin view: that the screen lists the library, prefills a real client from
state, surfaces what it couldn't fill, and never acquires a send path.
"""

from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import STATE
from satc.comms import library


@pytest.fixture()
def client():
    return create_app().test_client()


@pytest.fixture(scope="module")
def demo_client_id():
    """A client that actually exists in the store (the seeded sample practice)."""
    choices = STATE.client_choices()
    assert choices, "the seeded store should hold at least one client"
    return choices[0][0]


def test_screen_lists_every_template(client):
    resp = client.get("/comms")
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    for tpl in library().templates:
        assert tpl.name in body, f"{tpl.key} is missing from the screen"


def test_nav_carries_a_comms_entry(client):
    assert b"Client comms" in client.get("/").data


def test_screen_offers_the_practice_clients(client, demo_client_id):
    assert demo_client_id.encode() in client.get("/comms").data


def test_no_draft_until_a_client_and_template_are_chosen(client):
    """Template alone must not render a draft addressed to nobody."""
    resp = client.get("/comms", query_string={"template": "document_request"})
    assert resp.status_code == 200
    assert b"Copy the draft" not in resp.data


def test_drafting_for_a_real_client_prefills_from_state(client, demo_client_id):
    resp = client.get("/comms", query_string={
        "client": demo_client_id, "template": "document_request"})
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert "Copy the draft" in body
    assert STATE.name(demo_client_id) in body
    assert "Prefilled from their record" in body


def test_the_interview_invite_now_arrives_finished(client, demo_client_id):
    """It used to hand back three blanks — meeting place, times, and nothing
    else to do. Standing firm wording comes from config and the judgement
    wording is drafted, so the owner edits rather than composes."""
    resp = client.get("/comms", query_string={
        "client": demo_client_id, "template": "interview_invite"})
    body = resp.data.decode("utf-8")
    assert "a phone call or our office" in body      # standing firm wording
    assert "Copy the draft" in body


def test_a_genuine_unknown_fact_is_still_marked(client, demo_client_id):
    """The guarantee that did NOT change: a fact nothing supplies stays
    visibly blank. An invoice number is not something a model may invent."""
    resp = client.get("/comms", query_string={
        "client": demo_client_id, "template": "invoice_cover"})
    body = resp.data.decode("utf-8")
    assert "fill in ]]" in body
    assert "Invoice number" in body


def test_preparer_typed_values_are_merged_in(client, demo_client_id):
    resp = client.post("/comms", data={
        "client": demo_client_id, "template": "interview_invite",
        "fill_proposed_times": "Tuesday 10am or Thursday 2pm",
        "fill_meeting_place": "our office",
    })
    body = resp.data.decode("utf-8")
    assert "Tuesday 10am or Thursday 2pm" in body
    assert "[[ Proposed meeting times: fill in ]]" not in body


def test_a_letter_offers_no_mail_buttons(client, demo_client_id):
    """A printed cover letter isn't an email — don't pretend it is."""
    resp = client.get("/comms", query_string={
        "client": demo_client_id, "template": "cover_letter"})
    body = resp.data.decode("utf-8")
    assert "Copy the draft" in body
    assert "Open in your mail app" not in body


def test_an_unknown_template_does_not_500(client, demo_client_id):
    resp = client.get("/comms", query_string={
        "client": demo_client_id, "template": "no_such_template"})
    assert resp.status_code == 200
    assert b"Copy the draft" not in resp.data


def test_client_shortcut_redirects_into_the_screen(client, demo_client_id):
    resp = client.get(f"/clients/{demo_client_id}/comms")
    assert resp.status_code == 302
    assert "/comms" in resp.headers["Location"]
    assert demo_client_id in resp.headers["Location"]


def test_outlook_route_hands_back_text_it_did_not_send(client, demo_client_id):
    """On a box without Outlook COM this must degrade to copyable text, not fail."""
    resp = client.post("/comms/outlook", data={
        "client": demo_client_id, "template": "document_request"})
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert "Open it yourself" in body or "Sent to Outlook" in body


def test_outlook_route_guards_a_missing_selection(client):
    resp = client.post("/comms/outlook", data={"client": "", "template": ""})
    assert resp.status_code == 302


# --- the draft is about the invoice the row named ----------------------------
#
# The Today queue titles a row "Invoice 2026-9001 unpaid — $450.00" and hands
# that number over in the link. A draft that resolves its figures from whichever
# invoice happens to be newest puts a different number and a different amount in
# front of the CLIENT — principle 1, on the one path where nobody would catch it.


def _two_issued_invoices(client_id, *, other_client="ZZ-OTHER"):
    """Two issued bills for one client, and one belonging to somebody else."""
    from datetime import date

    from satc.billing.invoice import Invoice

    older = Invoice(invoice_id="2026-9001", client_id=client_id, tax_year=2025)
    older.add("return_1040")                                   # $450.00
    older.issue(on=date(2026, 1, 10))

    newer = Invoice(invoice_id="2026-9002", client_id=client_id, tax_year=2025)
    newer.add("return_1040")
    newer.add("schedule_e_rental")                             # $635.00 together
    newer.issue(on=date(2026, 2, 20))

    theirs = Invoice(invoice_id="2026-9003", client_id=other_client, tax_year=2025)
    theirs.add("return_1040")
    theirs.issue(on=date(2026, 2, 25))
    return [older, newer, theirs]


def _with_invoices(monkeypatch, invoices):
    def load(client_id: str = ""):
        return [i for i in invoices if not client_id or i.client_id == client_id]

    monkeypatch.setattr(STATE.store, "load_invoices", load)


def _draft(client, client_id, **extra):
    resp = client.get("/comms", query_string={
        "client": client_id, "template": "invoice_cover", "tax_year": 2025, **extra})
    assert resp.status_code == 200
    return resp.data.decode("utf-8")


def test_the_draft_quotes_the_invoice_the_row_named_not_the_newest(
        client, demo_client_id, monkeypatch):
    older, newer, _ = _two_issued_invoices(demo_client_id)
    _with_invoices(monkeypatch, [older, newer])

    body = _draft(client, demo_client_id, invoice=older.invoice_id)
    assert f"${older.total:,.2f}" in body
    assert f"${newer.total:,.2f}" not in body, (
        "the row said 2026-9001; the client must not read 2026-9002's amount")


def test_with_no_invoice_named_the_newest_is_still_what_a_cold_start_gets(
        client, demo_client_id, monkeypatch):
    """The only thing a preparer arriving at /comms has said is the client and
    the year, so the behaviour every existing caller relies on is untouched."""
    older, newer, _ = _two_issued_invoices(demo_client_id)
    _with_invoices(monkeypatch, [older, newer])

    body = _draft(client, demo_client_id)
    assert f"${newer.total:,.2f}" in body


def test_an_invoice_that_is_not_on_file_refuses_instead_of_quoting_another(
        client, demo_client_id, monkeypatch):
    """Refuse rather than default (principle 5). A covering email quoting the
    wrong bill is worse than no draft, and unlike a missing draft nobody would
    ever notice it."""
    older, newer, _ = _two_issued_invoices(demo_client_id)
    _with_invoices(monkeypatch, [older, newer])

    body = _draft(client, demo_client_id, invoice="2026-0000")
    assert "No invoice 2026-0000 is on file" in body
    assert "Copy the draft" not in body
    assert f"${newer.total:,.2f}" not in body


def test_another_clients_invoice_is_refused_rather_than_merged(
        client, demo_client_id, monkeypatch):
    older, newer, theirs = _two_issued_invoices(demo_client_id)
    _with_invoices(monkeypatch, [older, newer, theirs])

    body = _draft(client, demo_client_id, invoice=theirs.invoice_id)
    assert "does not belong to" in body
    assert "Copy the draft" not in body


def test_the_outlook_route_refuses_the_wrong_invoice_too(
        client, demo_client_id, monkeypatch):
    """This route opens a compose window aimed at the client, so it is the last
    place a draft built from the wrong bill may survive."""
    older, newer, _ = _two_issued_invoices(demo_client_id)
    _with_invoices(monkeypatch, [older, newer])

    resp = client.post("/comms/outlook", data={
        "client": demo_client_id, "template": "invoice_cover",
        "tax_year": "2025", "invoice": "2026-0000"})
    body = resp.data.decode("utf-8")
    assert "No invoice 2026-0000 is on file" in body
    assert "Sent to Outlook" not in body


# --- the letter is THIS engagement's, not the same letter for everybody ------
#
# The fan-out derives what an engagement agreed — the scope its answers priced,
# the asks still in scope, a fee only when somebody agreed a rate plan. Nothing
# merged it, so the engagement letter took its scope and its fee from standing
# wording and read the same for a $275 Schedule C and a $5,500 partnership.
# These guard the seam that closes it: `comms_views._context` layering
# `intake.service.letter_facts_for_job` OVER `build_context`.

ENGAGED = "SATC-001000"          # the seeded practice's individual client
YEAR = 2025


def _job(*, workflow_key="personal_schedule_c", answers=None, client_id=ENGAGED,
         tax_year=YEAR):
    """A real engagement job, derived the way intake derives one."""
    from datetime import date

    from satc.intake.fanout import fan_out
    from satc.intake.workflows import load_workflow

    return fan_out(load_workflow(workflow_key), answers or {"newSatcClient": "no"},
                   client_id=client_id, tax_year=tax_year,
                   today=date(tax_year + 1, 1, 15)).job


def _with_jobs(monkeypatch, jobs):
    monkeypatch.setattr(STATE.store, "load_jobs", lambda: list(jobs))


def _with_agreed_plan(monkeypatch, *, client_id=ENGAGED, tax_year=YEAR,
                      key="standard"):
    """A rate plan somebody actually agreed, on the mart the facts read."""
    from satc.models.work import Engagement

    mart = STATE.store.load_mart()
    mart.engagements = list(mart.engagements) + [
        Engagement(client_id=client_id, tax_year=tax_year, rate_plan_key=key,
                   rate_plan_basis="agreed at intake")]
    monkeypatch.setattr(STATE.store, "load_mart", lambda: mart)


def _letter(client, client_id=ENGAGED, tax_year=YEAR, **extra):
    resp = client.get("/comms", query_string={
        "client": client_id, "template": "engagement_letter",
        "tax_year": tax_year, **extra})
    assert resp.status_code == 200
    return resp.data.decode("utf-8")


def _standing_scope_wording():
    """Every sentence the model may pick for the scope slot."""
    from satc.comms.wording import wording

    return [v.text for v in wording()["scope_of_services"].variants]


def test_the_letter_names_the_services_this_engagement_quoted(client, monkeypatch):
    """The scope in the letter is the scope these answers PRICED.

    Same answers, one derivation: a letter cannot promise work the invoice does
    not charge for. Before the seam existed this slot was model-drafted wording
    that reads identically for every client in the practice."""
    _with_jobs(monkeypatch, [_job()])
    body = _letter(client)

    assert "Self-employment income and expenses" in body
    for standing in _standing_scope_wording():
        assert standing not in body, "the scope came from wording, not the engagement"


def test_a_fallback_rate_plan_leaves_the_fee_visibly_unfilled(client, monkeypatch):
    """A fallback plan is the practice default applying because nobody priced
    this client. Stating a fee derived from it claims a term of a contract
    nobody negotiated — so the slot is marked, never guessed (principle 1)."""
    _with_jobs(monkeypatch, [_job()])                     # no agreed plan on file
    body = _letter(client)

    assert "Fee for the work described above: [[ Fee: fill in ]]" in body
    assert "$275.00" not in body, "a fallback plan is not an agreement to pay it"


def test_an_agreed_rate_plan_states_the_fee_and_says_it_is_an_estimate(
        client, monkeypatch):
    """The other half: with a plan on file the fee appears — carrying what it
    is. A quote total rendered as a bare number is one a client holds us to."""
    _with_jobs(monkeypatch, [_job()])
    _with_agreed_plan(monkeypatch)
    body = _letter(client)

    assert "$275.00 (estimate — not a bill)" in body
    assert "[[ Fee: fill in ]]" not in body


def test_an_incomplete_quote_states_no_fee_even_on_an_agreed_plan(
        client, monkeypatch):
    """Both conditions, not either. `personal_1040_core` here prices the federal
    return and cannot price the state one, so the total is not the whole price —
    and a bare figure carrying that omission reads as the full fee."""
    _with_jobs(monkeypatch, [_job(workflow_key="personal_1040_core")])
    _with_agreed_plan(monkeypatch)
    body = _letter(client)

    assert "Fee for the work described above: [[ Fee: fill in ]]" in body
    assert "State tax return — fee to be agreed" in body, "the work is still in scope"


def test_an_invoice_total_is_never_the_fee_this_engagement_agreed(
        client, monkeypatch):
    """`fee_amount_text` is one merge name for two facts. `build_context` fills
    it from an ISSUED INVOICE — money owed for work already done — and on the
    one document a client signs that reads as the fee we agreed."""
    older, newer, _ = _two_issued_invoices(ENGAGED)
    _with_invoices(monkeypatch, [older, newer])
    _with_jobs(monkeypatch, [_job()])                     # fallback plan: no fee
    body = _letter(client)

    assert f"${newer.total:,.2f}" not in body, "a bill stood where the agreed fee goes"
    assert "Fee for the work described above: [[ Fee: fill in ]]" in body


def test_the_covering_email_still_quotes_the_bill_it_is_about(
        client, monkeypatch):
    """The other path, deliberately left open. An invoice total is exactly what
    the covering note's fee slot means, so guarding the letter must not empty
    the email."""
    older, newer, _ = _two_issued_invoices(ENGAGED)
    _with_invoices(monkeypatch, [older, newer])
    _with_jobs(monkeypatch, [_job()])

    body = _draft(client, ENGAGED)
    assert f"${newer.total:,.2f}" in body


def test_a_document_out_of_scope_is_not_requested_in_the_letter(
        client, monkeypatch):
    """One call must not say two things. A task somebody started is KEPT on the
    job when an answer changes — but asking the client for a document the same
    plan reports as out of scope contradicts itself in front of the one person
    who cannot see the plan."""
    job = _job(workflow_key="personal_1040_core",
               answers={"newSatcClient": "no", "marketplaceInsurance": "yes"})
    started = [t for t in job.tasks
               if t.template_id == "personal-1040-marketplace-1095a"]
    assert started, "the 1095-A ask should be on the job these answers built"
    started[0].status = "in_progress"                     # somebody started it
    # The client says no Marketplace coverage this year. The started task stays
    # on the job — nobody's work is deleted by an answer changing.
    job.intake_answers = dict(job.intake_answers, marketplaceInsurance="no")
    _with_jobs(monkeypatch, [job])

    body = _letter(client)
    assert "Upload Forms W-2" in body, "the asks still in scope are still asked"
    assert "1095-A" not in body, "the letter asked for a document it took out of scope"


def test_an_ask_the_practice_switched_off_is_not_asked_for_either(client, monkeypatch):
    """The same contradiction, in the branch where the plan can name NOTHING.

    The practice can disable a request in the questionnaire editor after an
    engagement was generated. The task stays on the job — history is not deleted
    by a config edit — so the generic prefill still lists it while the plan says
    it is out of scope. An empty ask list must therefore render as a marked
    blank, not fall back to the list the plan just contradicted."""
    job = _job()                       # generated while the ask was still asked
    assert any(t.audience == "client" for t in job.tasks)

    monkeypatch.setattr(
        "satc.intake.workflows._OVERRIDE_PROVIDER",
        lambda key: {"tasks": {"schedule-c-gross-receipts-summary": {"disabled": True}}})
    _with_jobs(monkeypatch, [job])

    body = _letter(client)
    assert "[[ Requested items: fill in ]]" in body
    assert "gross receipts summary" not in body, \
        "the letter asked for a document the practice switched off"


def test_two_engagements_produce_two_different_letters(client, monkeypatch):
    """The whole point. The scope and the asks are this client's answers."""
    _with_jobs(monkeypatch, [_job(), _job(client_id="SATC-003000",
                                          workflow_key="business_partnership_tax",
                                          tax_year=2024)])
    mine = _letter(client)
    theirs = _letter(client, client_id="SATC-003000", tax_year=2024)

    assert "Self-employment income and expenses" in mine
    assert "Partnership return, including partner K-1s" in theirs
    assert "Self-employment income and expenses" not in theirs


def test_a_different_years_engagement_does_not_state_this_years_terms(
        client, monkeypatch):
    """Terms belong to the year that agreed them. The newest job on file is the
    right prefill for who a client is and the wrong source for what was agreed
    about some other year — and the screen says so rather than leaving standing
    wording looking like an agreement."""
    _with_jobs(monkeypatch, [_job(tax_year=2024)])
    body = _letter(client, tax_year=2025)

    assert "Self-employment income and expenses" not in body
    assert "is for 2024, not 2025" in body


def test_the_outlook_route_states_the_same_fee_the_screen_does(
        client, monkeypatch):
    """Both doors into a draft go through one seam. This route opens a compose
    window aimed at the client, so it is the last place a bill may stand in for
    an agreed fee."""
    older, newer, _ = _two_issued_invoices(ENGAGED)
    _with_invoices(monkeypatch, [older, newer])
    _with_jobs(monkeypatch, [_job()])

    resp = client.post("/comms/outlook", data={
        "client": ENGAGED, "template": "engagement_letter", "tax_year": str(YEAR)})
    body = resp.data.decode("utf-8")
    assert "Self-employment income and expenses" in body
    assert f"${newer.total:,.2f}" not in body
    assert "[[ Fee: fill in ]]" in body


def test_drafting_still_sends_nothing(client, monkeypatch):
    """Principle 9 survives the seam: the letter now states a fee and a scope,
    and it is still a draft nobody transmitted."""
    _with_jobs(monkeypatch, [_job()])
    _with_agreed_plan(monkeypatch)
    body = _letter(client)

    assert "DRAFT engagement letter for preparer review" in body
    assert "Copy the draft" in body


def test_no_module_anywhere_has_a_send_path():
    """The hard rule: sending stays a human act in the mail client.

    Parsed rather than grepped, so a module stays free to *say* "no SMTP" in its
    docstring while this proves it never imports or calls one.

    THE SCOPE IS THE WHOLE PACKAGE, and it was not. This walked satc/comms and
    satc/app/comms_views only — so the guarantee held exactly where somebody had
    already thought about it, and nowhere else. Three separate reviewers of the
    new satc/autonomy package found the gap the same way: one PLANTED a working
    smtplib send path in satc/autonomy/approval.py and this test still passed.

    A no-send invariant scoped to one directory is not an invariant, it is a
    convention in that directory — the same "guarded on one path" shape this
    project keeps producing. It now walks every module under satc/, so a send
    path added anywhere, including a package that does not exist yet, fails
    here.

    ``docs/AUTONOMY-CHARTER.md`` §10 names THIS test as the standing guarantee
    and requires that retiring it be an explicit, named act in the same commit
    that amends principle 9. That only means anything if it covers the code.
    """
    import ast
    from pathlib import Path

    import satc

    banned_modules = {"smtplib", "ssl"}
    banned_calls = {"sendmail", "send_message", "starttls", "SMTP", "SMTP_SSL"}

    root = Path(satc.__file__).parent
    files = sorted(root.rglob("*.py"))
    assert len(files) > 100, (
        f"only {len(files)} modules found under {root} — this test is worthless "
        f"if it silently stops finding the package")

    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in banned_modules, path.name
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in banned_modules, path.name
            elif isinstance(node, ast.Call):
                func = node.func
                name = getattr(func, "attr", None) or getattr(func, "id", None)
                assert name not in banned_calls, f"{path.name} calls {name}"
